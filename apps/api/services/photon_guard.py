# photon_guard.py — Photon AI safety layer: input screening, output filtering, quality scoring
from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

from config import get_settings

log = structlog.get_logger()

# ── Prompt injection patterns ────────────────────────────────────────────────

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you\s+are", re.IGNORECASE),
    re.compile(r"new\s+instruction[s]?\s*:", re.IGNORECASE),
    re.compile(r"\bsystem\s*:\s*", re.IGNORECASE),
    re.compile(r"\bassistant\s*:\s*", re.IGNORECASE),
    re.compile(r"<\|?(?:im_start|system|endoftext)\|?>", re.IGNORECASE),
    re.compile(r"(?:[A-Za-z0-9+/]{40,}={0,2})", re.IGNORECASE),  # base64 obfuscation
]

# ── PII patterns ─────────────────────────────────────────────────────────────

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}


class PhotonGuardClient:
    """AI safety layer — calls remote Photon endpoint when configured, runs local heuristics otherwise."""

    def __init__(self) -> None:
        settings = get_settings()
        self._endpoint = settings.photon_endpoint.rstrip("/") if settings.photon_endpoint else ""
        self._api_key = settings.photon_api_key
        self._enabled = bool(self._endpoint and self._api_key)

        if self._enabled:
            log.info("photon_guard.backend", backend="remote", endpoint=self._endpoint)
        else:
            log.info("photon_guard.backend", backend="local_passthrough")

    # ── Public API ──────────────────────────────────────────────────────────

    async def screen_input(self, text: str) -> dict[str, Any]:
        """Detect prompt injection patterns in user input.

        Returns: {"safe": bool, "reason": str}
        """
        if self._enabled:
            return await self._remote_call("screen_input", {"text": text})
        return self._local_screen_input(text)

    async def screen_output(self, text: str) -> dict[str, Any]:
        """Filter PII and dangerous content from model output.

        Returns: {"safe": bool, "filtered": str}
        """
        if self._enabled:
            return await self._remote_call("screen_output", {"text": text})
        return self._local_screen_output(text)

    async def score_quality(self, prompt: str, response: str) -> float:
        """Score response quality on a 0.0–1.0 rubric.

        Evaluates relevance, specificity, and safety.
        """
        if self._enabled:
            result = await self._remote_call("score_quality", {"prompt": prompt, "response": response})
            return float(result.get("score", 1.0))
        return self._local_score_quality(prompt, response)

    # ── Remote Photon calls ─────────────────────────────────────────────────

    async def _remote_call(self, handler_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to the remote Photon endpoint."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._endpoint}/{handler_name}",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            log.warning("photon_guard.remote_call.failed", handler=handler_name, error=str(exc))
            # Graceful fallback to local heuristics on remote failure
            if handler_name == "screen_input":
                return self._local_screen_input(payload["text"])
            if handler_name == "screen_output":
                return self._local_screen_output(payload["text"])
            if handler_name == "score_quality":
                return {"score": self._local_score_quality(payload["prompt"], payload["response"])}
            return {"safe": True, "filtered": payload.get("text", ""), "score": 1.0}

    # ── Local heuristic implementations ─────────────────────────────────────

    @staticmethod
    def _local_screen_input(text: str) -> dict[str, Any]:
        """Regex + heuristic check for prompt injection."""
        for pattern in _INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return {"safe": False, "reason": f"Potential prompt injection detected: '{match.group()}'"}
        return {"safe": True, "reason": ""}

    @staticmethod
    def _local_screen_output(text: str) -> dict[str, Any]:
        """Strip PII patterns from output text."""
        filtered = text
        found_pii = False
        for pii_type, pattern in _PII_PATTERNS.items():
            if pattern.search(filtered):
                found_pii = True
                filtered = pattern.sub(f"[{pii_type.upper()}_REDACTED]", filtered)
        return {"safe": not found_pii, "filtered": filtered}

    @staticmethod
    def _local_score_quality(prompt: str, response: str) -> float:
        """Simple rubric scoring: relevance, specificity, safety."""
        score = 0.0

        # Relevance: do key words from the prompt appear in the response?
        prompt_words = set(prompt.lower().split())
        response_lower = response.lower()
        overlap = sum(1 for w in prompt_words if w in response_lower and len(w) > 3)
        relevance = min(overlap / max(len(prompt_words), 1), 1.0)
        score += relevance * 0.4

        # Specificity: does the response contain concrete numbers/data?
        has_numbers = bool(re.search(r"\$?\d+[\d,.]*%?", response))
        has_detail = len(response) > 80
        specificity = (0.5 if has_numbers else 0.0) + (0.5 if has_detail else 0.0)
        score += specificity * 0.3

        # Safety: no PII leakage in output
        pii_free = all(not p.search(response) for p in _PII_PATTERNS.values())
        score += (1.0 if pii_free else 0.3) * 0.3

        return round(min(score, 1.0), 2)


# Module-level singleton
_client: PhotonGuardClient | None = None


def get_photon_guard() -> PhotonGuardClient:
    """Return the shared PhotonGuardClient instance (FastAPI dependency)."""
    global _client
    if _client is None:
        _client = PhotonGuardClient()
    return _client
