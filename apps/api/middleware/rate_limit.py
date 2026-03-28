# rate_limit.py — Redis sliding-window rate limiter
from __future__ import annotations

import time

import redis.asyncio as aioredis
import structlog
from fastapi import HTTPException, Request

from config import get_settings

log = structlog.get_logger()

# Limits per endpoint group (requests per window)
_LIMITS: dict[str, tuple[int, int]] = {
    "default": (60, 60),   # 60 requests per 60 seconds
    "llm": (10, 60),       # 10 requests per 60 seconds (expensive LLM calls)
}

# Endpoints that use the stricter LLM limit
_LLM_PATHS = {
    "/api/v1/analyze/upload",
    "/api/v1/agent/sessions",  # session creation
    "/api/v1/infra/generate",
}


def _is_llm_path(path: str) -> bool:
    """Check if the path matches an LLM-rate-limited endpoint."""
    # Also match /agent/sessions/{id}/messages
    if "/agent/sessions/" in path and path.endswith("/messages"):
        return True
    return path in _LLM_PATHS


async def check_rate_limit(request: Request, user_id: str) -> None:
    """Check rate limit for the current user + endpoint. Raises 429 if exceeded."""
    settings = get_settings()

    group = "llm" if _is_llm_path(request.url.path) else "default"
    max_requests, window_seconds = _LIMITS[group]

    key = f"rl:{user_id}:{group}"
    now = time.time()
    window_start = now - window_seconds

    try:
        async with aioredis.from_url(settings.redis_url) as r:
            pipe = r.pipeline()
            # Remove entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries
            pipe.zcard(key)
            # Add current request
            pipe.zadd(key, {str(now): now})
            # Set expiry on the key
            pipe.expire(key, window_seconds + 1)
            results = await pipe.execute()

            current_count = results[1]

            if current_count >= max_requests:
                log.warning(
                    "rate_limit.exceeded",
                    user_id=user_id,
                    group=group,
                    count=current_count,
                    limit=max_requests,
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s.",
                    headers={"Retry-After": str(window_seconds)},
                )
    except HTTPException:
        raise
    except Exception as exc:
        # Redis down — don't block requests, just log
        log.warning("rate_limit.redis_error", error=str(exc))
