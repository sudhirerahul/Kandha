# sanitize.py — Input sanitization utilities for request models
from __future__ import annotations

import re
import uuid

from pydantic import field_validator


_NULL_BYTE = re.compile(r"\x00")
_MAX_MESSAGE_LENGTH = 10_000  # characters
_MAX_FIELD_LENGTH = 500


def strip_null_bytes(v: str) -> str:
    """Remove null bytes from strings."""
    return _NULL_BYTE.sub("", v) if isinstance(v, str) else v


def validate_uuid(v: str) -> str:
    """Validate that a string is a valid UUID."""
    try:
        uuid.UUID(v)
        return v
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid UUID: {v}")


def enforce_max_length(v: str, max_len: int = _MAX_FIELD_LENGTH) -> str:
    """Truncate strings that exceed max length."""
    if isinstance(v, str) and len(v) > max_len:
        return v[:max_len]
    return v


class SanitizedMessageMixin:
    """Mixin for Pydantic models with a 'content' field that needs sanitization."""

    @field_validator("content", mode="before")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Content must be a string.")
        v = strip_null_bytes(v)
        if len(v) > _MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message exceeds {_MAX_MESSAGE_LENGTH} character limit.")
        return v.strip()
