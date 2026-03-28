# gmi.py — GMI Cloud / Kimi K2 async streaming client (OpenAI-compatible API)
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import httpx
import structlog

from config import get_settings

log = structlog.get_logger()

_SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "system.md").read_text()


class GMIClient:
    """Thin async wrapper around GMI's OpenAI-compatible chat completions endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.gmi_base_url.rstrip("/")
        self._model = settings.gmi_model
        self._headers = {
            "Authorization": f"Bearer {settings.gmi_api_key}",
            "Content-Type": "application/json",
        }

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Stream text chunks from Kimi K2 via SSE.

        Yields individual text delta strings as they arrive.
        Raises httpx.HTTPStatusError on non-2xx responses.
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "system", "content": _SYSTEM_PROMPT}, *messages],
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                log.info("gmi.stream.started", model=self._model)

                async for raw_line in response.aiter_lines():
                    if not raw_line.startswith("data: "):
                        continue
                    payload_str = raw_line[6:]
                    if payload_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload_str)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

                log.info("gmi.stream.done", model=self._model)

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Non-streaming completion with prompt caching — returns the full response string."""
        from services.cache import get_prompt_cache

        estimated_tokens = len("".join(m["content"] for m in messages)) // 4
        log.info("gmi.complete.start", estimated_tokens=estimated_tokens)

        cache = get_prompt_cache()
        cached = await cache.get(messages)
        if cached is not None:
            log.info("gmi.complete.cache_hit", estimated_tokens=estimated_tokens)
            return cached

        chunks: list[str] = []
        async for chunk in self.stream_chat(messages, temperature=temperature, max_tokens=max_tokens):
            chunks.append(chunk)
        result = "".join(chunks)

        await cache.set(messages, result)
        return result


# Module-level singleton
_client: GMIClient | None = None


def get_gmi_client() -> GMIClient:
    """Return the shared GMIClient instance (FastAPI dependency)."""
    global _client
    if _client is None:
        _client = GMIClient()
    return _client
