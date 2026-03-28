# guard.py — Deployable Photon class for Kandha AI safety layer
# Deploy: lep photon run -n kandha-guard -m guard.py
#
# This file is deployed separately to LeptonAI and is NOT imported by FastAPI.
# The FastAPI client (services/photon_guard.py) calls these handlers via HTTP.
from __future__ import annotations

import re
from typing import Any

try:
    from leptonai.photon import Photon
except ImportError:
    # Allow loading outside LeptonAI runtime (tests, linting, etc.)
    class Photon:  # type: ignore[no-redef]
        """Stub for local development — replaced by leptonai.photon.Photon at deploy time."""
        @staticmethod
        def handler(path: str = ""):  # noqa: ARG004
            def decorator(func):  # type: ignore[no-untyped-def]
                return func
            return decorator


# ── Patterns (duplicated from services/photon_guard.py for standalone deployment) ──

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
    re.compile(r"(?:[A-Za-z0-9+/]{40,}={0,2})", re.IGNORECASE),
]

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}


class KandhaGuard(Photon):
    """LeptonAI Photon providing AI safety screening for Kandha."""

    @Photon.handler(path="screen_input")
    def screen_input(self, text: str) -> dict[str, Any]:
        """Detect prompt injection patterns in user input."""
        for pattern in _INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return {"safe": False, "reason": f"Potential prompt injection detected: '{match.group()}'"}
        return {"safe": True, "reason": ""}

    @Photon.handler(path="screen_output")
    def screen_output(self, text: str) -> dict[str, Any]:
        """Filter PII and dangerous content from model output."""
        filtered = text
        found_pii = False
        for pii_type, pattern in _PII_PATTERNS.items():
            if pattern.search(filtered):
                found_pii = True
                filtered = pattern.sub(f"[{pii_type.upper()}_REDACTED]", filtered)
        return {"safe": not found_pii, "filtered": filtered}

    @Photon.handler(path="score_quality")
    def score_quality(self, prompt: str, response: str) -> dict[str, float]:
        """Score response quality on a 0.0-1.0 rubric."""
        score = 0.0

        # Relevance
        prompt_words = set(prompt.lower().split())
        response_lower = response.lower()
        overlap = sum(1 for w in prompt_words if w in response_lower and len(w) > 3)
        relevance = min(overlap / max(len(prompt_words), 1), 1.0)
        score += relevance * 0.4

        # Specificity
        has_numbers = bool(re.search(r"\$?\d+[\d,.]*%?", response))
        has_detail = len(response) > 80
        specificity = (0.5 if has_numbers else 0.0) + (0.5 if has_detail else 0.0)
        score += specificity * 0.3

        # Safety
        pii_free = all(not p.search(response) for p in _PII_PATTERNS.values())
        score += (1.0 if pii_free else 0.3) * 0.3

        return {"score": round(min(score, 1.0), 2)}
