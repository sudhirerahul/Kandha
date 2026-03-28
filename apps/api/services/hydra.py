# hydra.py — HydraDB persistent memory client with Redis fallback
#
# HydraDB stores per-session conversation memory across turns so the agent
# never loses context. When HYDRA_BASE_URL is not configured, we fall back to
# Redis LISTs using the session_id as the key.
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
import redis.asyncio as aioredis
import structlog

from config import get_settings

log = structlog.get_logger()

_REDIS_TTL = 60 * 60 * 24 * 7  # 7 days
_MAX_HISTORY = 40  # max stored turns to prevent unbounded growth


class MemoryClient:
    """Unified memory interface — uses HydraDB when available, Redis otherwise."""

    def __init__(self) -> None:
        settings = get_settings()
        self._hydra_url = settings.hydra_base_url.rstrip("/") if settings.hydra_base_url else None
        self._hydra_key = settings.hydra_api_key
        self._tenant_id = settings.hydra_tenant_id
        self._redis_url = settings.redis_url
        self._using_hydra = bool(self._hydra_url and self._hydra_key)

        if self._using_hydra:
            log.info("memory.backend", backend="hydradb", url=self._hydra_url)
        else:
            log.info("memory.backend", backend="redis_fallback", url=self._redis_url)

    # ── Public API ──────────────────────────────────────────────────────────

    async def create_session(self, session_id: str, metadata: dict[str, Any] | None = None) -> str:
        """Initialise a new memory session. Returns the hydra_session_id."""
        if self._using_hydra:
            return await self._hydra_create(session_id, metadata or {})
        return session_id  # Redis uses session_id directly as key

    async def append_turn(self, session_id: str, role: str, content: str) -> None:
        """Append a single conversation turn to the session memory."""
        turn = {"role": role, "content": content}
        if self._using_hydra:
            await self._hydra_append(session_id, turn)
        else:
            await self._redis_append(session_id, turn)

    async def get_history(self, session_id: str) -> list[dict[str, str]]:
        """Return the full conversation history as a list of {role, content} dicts."""
        if self._using_hydra:
            return await self._hydra_get(session_id)
        return await self._redis_get(session_id)

    async def clear_session(self, session_id: str) -> None:
        """Delete all memory for a session."""
        if self._using_hydra:
            await self._hydra_clear(session_id)
        else:
            async with aioredis.from_url(self._redis_url) as r:
                await r.delete(f"mem:{session_id}")

    # ── HydraDB backend (real API: api.hydradb.com) ────────────────────────

    def _hydra_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._hydra_key}", "Content-Type": "application/json"}

    async def _hydra_create(self, session_id: str, metadata: dict[str, Any]) -> str:
        """Seed a new session in HydraDB via POST /memory/add with a system init entry."""
        headers = self._hydra_headers()
        user_id = metadata.get("user_id", session_id)
        payload = {
            "tenant_id": self._tenant_id,
            "user_id": session_id,
            "content": "session_init",
            "metadata": {
                "role": "system",
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **metadata,
            },
            "infer": True,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(f"{self._hydra_url}/memory/add", headers=headers, json=payload)
                resp.raise_for_status()
                log.info("hydra.session_created", session_id=session_id)
            except httpx.HTTPStatusError as exc:
                log.error("hydra.create_failed", session_id=session_id, status=exc.response.status_code)
                raise
        return session_id

    async def _hydra_append(self, session_id: str, turn: dict[str, str]) -> None:
        """Append a conversation turn via POST /memory/add."""
        headers = self._hydra_headers()
        payload = {
            "tenant_id": self._tenant_id,
            "user_id": session_id,
            "content": turn["content"],
            "metadata": {
                "role": turn["role"],
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "infer": True,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(f"{self._hydra_url}/memory/add", headers=headers, json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                log.error("hydra.append_failed", session_id=session_id, status=exc.response.status_code)
                raise

    async def _hydra_get(self, session_id: str) -> list[dict[str, str]]:
        """Recall conversation history via POST /memory/recall."""
        headers = self._hydra_headers()
        payload = {
            "tenant_id": self._tenant_id,
            "user_id": session_id,
            "query": "conversation history",
            "top_k": _MAX_HISTORY,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(f"{self._hydra_url}/memory/recall", headers=headers, json=payload)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                log.error("hydra.get_failed", session_id=session_id, status=exc.response.status_code)
                raise

        results = resp.json().get("results", [])
        history: list[dict[str, str]] = []
        for item in results:
            meta = item.get("metadata", {})
            role = meta.get("role", "assistant")
            content = item.get("content", "")
            # Skip the session_init seed entry
            if role == "system" and content == "session_init":
                continue
            history.append({"role": role, "content": content})
        return history

    async def _hydra_clear(self, session_id: str) -> None:
        """Delete all memory for a session via DELETE /memory."""
        headers = self._hydra_headers()
        payload = {
            "tenant_id": self._tenant_id,
            "user_id": session_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.request(
                    "DELETE", f"{self._hydra_url}/memory", headers=headers, json=payload,
                )
                resp.raise_for_status()
                log.info("hydra.session_cleared", session_id=session_id)
            except httpx.HTTPStatusError as exc:
                log.error("hydra.clear_failed", session_id=session_id, status=exc.response.status_code)
                raise

    # ── Redis fallback backend ───────────────────────────────────────────────

    async def _redis_append(self, session_id: str, turn: dict[str, str]) -> None:
        key = f"mem:{session_id}"
        async with aioredis.from_url(self._redis_url) as r:
            await r.rpush(key, json.dumps(turn))
            await r.ltrim(key, -_MAX_HISTORY, -1)
            await r.expire(key, _REDIS_TTL)

    async def _redis_get(self, session_id: str) -> list[dict[str, str]]:
        key = f"mem:{session_id}"
        async with aioredis.from_url(self._redis_url) as r:
            raw: list[bytes] = await r.lrange(key, 0, -1)
        return [json.loads(item) for item in raw]


_client: MemoryClient | None = None


def get_memory_client() -> MemoryClient:
    """Return the shared MemoryClient instance (FastAPI dependency)."""
    global _client
    if _client is None:
        _client = MemoryClient()
    return _client
