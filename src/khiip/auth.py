"""API key authentication for the Khiip FastAPI daemon.

Per v0 spec D7: Bearer token auth on every request. Keys are auto-generated
at first daemon launch (`khiip.config.ensure_auth`) and stored in
`~/.config/khiip/auth.toml` (mode 600). The plugin/CLI consumes the key from
that file; users only see the key directly when rotating.

This module implements:
- `verify_bearer` — FastAPI dependency that validates `Authorization: Bearer …`
- `bypass_paths` — endpoints exempt from auth (e.g. `/health`)
"""

from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from khiip.config import ensure_auth

# Endpoints that do NOT require auth — keep this list MINIMAL
BYPASS_PATHS: frozenset[str] = frozenset(
    {
        "/health",
        "/openapi.json",
        "/docs",
        "/redoc",
    }
)

_bearer_scheme = HTTPBearer(auto_error=False)


def _load_expected_key() -> str:
    """Load the expected API key from disk on first call (memoized via daemon state).

    Note: the daemon caches the key on startup; this is only called if the
    cached key is unavailable (e.g. tests creating a fresh app).
    """
    return ensure_auth()


def verify_bearer(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency: validate the incoming Bearer token.

    Returns the validated key fingerprint (for logging). Raises 401 on missing
    or mismatched token. Endpoints in BYPASS_PATHS skip validation entirely.
    """
    if request.url.path in BYPASS_PATHS:
        return ""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected = request.app.state.api_key if hasattr(request.app.state, "api_key") else _load_expected_key()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials[:14]  # fingerprint for logs


__all__ = ["BYPASS_PATHS", "verify_bearer"]
