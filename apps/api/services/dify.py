# dify.py — Dify workflow client for bill analysis and migration orchestration
#
# Dify is used as the orchestration layer for complex multi-step reasoning.
# The bill analysis workflow (DIFY_WORKFLOW_ID_ANALYZE) takes raw spend data
# and returns a structured savings report. The migration workflow
# (DIFY_WORKFLOW_ID_MIGRATE) builds a full migration plan given architecture
# context.
#
# NOTE: If DIFY_WORKFLOW_ID_ANALYZE / DIFY_WORKFLOW_ID_MIGRATE are not set,
# or the API key is a dataset key (prefix "dataset-"), these methods return
# None and the caller falls back to direct GMI completion.
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx
import structlog

from config import get_settings

log = structlog.get_logger()


class DifyClient:
    """Async client for Dify workflow execution and streaming."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.dify_base_url.rstrip("/")
        self._api_key = settings.dify_api_key
        self._workflow_analyze = settings.dify_workflow_id_analyze
        self._workflow_migrate = settings.dify_workflow_id_migrate
        self._workflow_infra = settings.dify_workflow_id_infra

        # Detect dataset-only key — workflows require an app key (prefix "app-")
        self._functional = bool(
            self._api_key
            and not self._api_key.startswith("dataset-")
        )
        if not self._functional:
            log.warning(
                "dify.disabled",
                reason="API key is a dataset key or not set — workflow execution unavailable. "
                "Create an app key in Dify → Settings → API Keys.",
            )

    # ── Public API ──────────────────────────────────────────────────────────

    async def run_analyze_workflow(
        self, spend_data: dict[str, Any], user_id: str
    ) -> dict[str, Any] | None:
        """Run the cost analysis workflow. Returns structured output or None if not configured."""
        if not self._functional or not self._workflow_analyze:
            log.info("dify.analyze.skipped", reason="not_configured")
            return None

        return await self._run_workflow(
            workflow_id=self._workflow_analyze,
            inputs={"spend_data": json.dumps(spend_data)},
            user=user_id,
        )

    async def stream_migrate_workflow(
        self, context: dict[str, Any], user_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream the migration planning workflow. Yields text chunks."""
        if not self._functional or not self._workflow_migrate:
            log.info("dify.migrate.skipped", reason="not_configured")
            return

        async for chunk in self._stream_workflow(
            workflow_id=self._workflow_migrate,
            inputs={"context": json.dumps(context)},
            user=user_id,
        ):
            yield chunk

    async def run_infra_workflow(
        self, infra_config: dict[str, Any], user_id: str
    ) -> dict[str, Any] | None:
        """Run the infrastructure generation workflow. Returns structured output or None."""
        if not self._functional or not self._workflow_infra:
            log.info("dify.infra.skipped", reason="not_configured")
            return None

        return await self._run_workflow(
            workflow_id=self._workflow_infra,
            inputs={"infra_config": json.dumps(infra_config)},
            user=user_id,
        )

    async def stream_infra_workflow(
        self, infra_config: dict[str, Any], user_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream the infrastructure generation workflow. Yields text chunks."""
        if not self._functional or not self._workflow_infra:
            log.info("dify.infra.skipped", reason="not_configured")
            return

        async for chunk in self._stream_workflow(
            workflow_id=self._workflow_infra,
            inputs={"infra_config": json.dumps(infra_config)},
            user=user_id,
        ):
            yield chunk

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _run_workflow(
        self, workflow_id: str, inputs: dict[str, Any], user: str
    ) -> dict[str, Any] | None:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "workflow_id": workflow_id,
            "inputs": inputs,
            "response_mode": "blocking",
            "user": user,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    f"{self._base_url}/workflows/run",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json().get("data", {}).get("outputs", {})
            except httpx.HTTPStatusError as exc:
                log.error("dify.workflow.error", status=exc.response.status_code, body=exc.response.text)
                return None

    async def _stream_workflow(
        self, workflow_id: str, inputs: dict[str, Any], user: str
    ) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "workflow_id": workflow_id,
            "inputs": inputs,
            "response_mode": "streaming",
            "user": user,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/workflows/run",
                    headers=headers,
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            event = json.loads(line[6:])
                            event_type = event.get("event", "")
                            if event_type == "text_chunk":
                                text = event.get("data", {}).get("text", "")
                                if text:
                                    yield text
                            elif event_type == "workflow_finished":
                                log.info(
                                    "dify.stream.finished",
                                    workflow_id=workflow_id,
                                    status=event.get("data", {}).get("status"),
                                )
                        except (json.JSONDecodeError, KeyError):
                            continue
            except httpx.HTTPStatusError as exc:
                log.error("dify.stream.error", status=exc.response.status_code)


_client: DifyClient | None = None


def get_dify_client() -> DifyClient:
    """Return the shared DifyClient instance (FastAPI dependency)."""
    global _client
    if _client is None:
        _client = DifyClient()
    return _client
