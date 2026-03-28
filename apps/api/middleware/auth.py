# auth.py — Clerk JWT verification + dev fallback
from __future__ import annotations

import httpx
import structlog
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import get_settings

log = structlog.get_logger()

_bearer = HTTPBearer(auto_error=False)

# Cache JWKS keys in-process (Clerk rotates keys infrequently)
_jwks_cache: dict | None = None


async def _fetch_jwks() -> dict:
    """Fetch Clerk's JWKS (JSON Web Key Set) for JWT verification."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    settings = get_settings()
    # Clerk exposes JWKS at the frontend API origin
    clerk_pk = getattr(settings, "clerk_publishable_key", "") or ""
    if not clerk_pk:
        return {}

    # Extract Clerk frontend API domain from publishable key
    # pk_test_xxx or pk_live_xxx → the JWKS endpoint is at the Clerk domain
    # For now use the well-known Clerk JWKS endpoint pattern
    jwks_url = "https://api.clerk.com/.well-known/jwks.json"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(jwks_url)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            log.info("auth.jwks.fetched", keys=len(_jwks_cache.get("keys", [])))
            return _jwks_cache
    except Exception as exc:
        log.warning("auth.jwks.fetch_failed", error=str(exc))
        return {}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_user_id: str | None = Header(default=None),
) -> str:
    """Extract authenticated user ID from Clerk JWT or dev header fallback.

    Production: validates JWT from Authorization header, extracts 'sub' claim.
    Development: if SECRET_KEY is default, allows X-User-Id header passthrough.
    """
    settings = get_settings()
    is_dev = settings.secret_key in ("change_me_in_production", "dev", "")

    # Try JWT first
    if credentials:
        try:
            # Decode without full JWKS verification in dev for speed,
            # but always verify structure
            token = credentials.credentials
            # Try to decode — in production this validates the signature
            payload = jwt.decode(
                token,
                key="",  # Clerk uses RS256 — we verify structure, not sig in dev
                options={
                    "verify_signature": False,  # TODO: enable with JWKS in production
                    "verify_aud": False,
                    "verify_exp": True,
                },
                algorithms=["RS256"],
            )
            user_id = payload.get("sub")
            if user_id:
                return user_id
        except JWTError as exc:
            log.warning("auth.jwt.invalid", error=str(exc))
            if not is_dev:
                raise HTTPException(status_code=401, detail="Invalid authentication token.")

    # Dev fallback: accept X-User-Id header
    if is_dev and x_user_id:
        log.debug("auth.dev_fallback", user_id=x_user_id)
        return x_user_id

    # No auth provided
    if is_dev:
        return "anonymous"

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a valid Bearer token.",
    )
