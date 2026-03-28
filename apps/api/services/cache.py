# cache.py — Redis prompt cache for inference optimization
from __future__ import annotations

import hashlib
import json

import structlog
from redis.asyncio import Redis

from config import get_settings

log = structlog.get_logger()


class PromptCache:
    """SHA256-keyed Redis cache for non-streaming LLM responses."""

    TTL: int = 3600  # 1 hour

    def __init__(self) -> None:
        settings = get_settings()
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)

    def _hash(self, messages: list[dict[str, str]]) -> str:
        """Return a deterministic SHA256 hex digest for a message list."""
        serialized = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode()).hexdigest()

    async def get(self, messages: list[dict[str, str]]) -> str | None:
        """Check cache for a stored response. Returns None on miss or error."""
        key = f"llm_cache:{self._hash(messages)}"
        try:
            value = await self._redis.get(key)
            if value is not None:
                log.info("prompt_cache.hit", key=key)
                return value
            log.debug("prompt_cache.miss", key=key)
            return None
        except Exception:
            log.warning("prompt_cache.get_error", key=key, exc_info=True)
            return None

    async def set(self, messages: list[dict[str, str]], response: str) -> None:
        """Store a response in cache. Silently ignores errors."""
        key = f"llm_cache:{self._hash(messages)}"
        try:
            await self._redis.set(key, response, ex=self.TTL)
            log.debug("prompt_cache.stored", key=key, ttl=self.TTL)
        except Exception:
            log.warning("prompt_cache.set_error", key=key, exc_info=True)


_cache: PromptCache | None = None


def get_prompt_cache() -> PromptCache:
    """Return the shared PromptCache instance."""
    global _cache
    if _cache is None:
        _cache = PromptCache()
    return _cache
