"""Khiip FastAPI daemon.

Entrypoint: `khiipd serve` (via cli.py) → `uvicorn khiip.daemon:app …`

The daemon:
- Listens on `127.0.0.1:8478` by default (Tailscale-bind opt-in for power users)
- Auto-generates API key on first launch (~/.config/khiip/auth.toml mode 600)
- Validates Bearer token on every request except /health, /openapi.json, /docs, /redoc
- Initializes SQLite schema on first launch (~/.local/share/khiip/index.db)
- Exposes /api/v1/captures (POST/GET) + /api/v1/edges (POST/GET) + /api/v1/recall

v0 Week 1 scope: scaffold + health + auth + schema init. Extractors + capture
ingestion flow into Week 2+.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

from khiip.auth import verify_bearer
from khiip.config import KhiipConfig, auth_key_fingerprint, ensure_auth, load_config
from khiip.models import HealthResponse
from khiip.storage import db as storage_db
from khiip.version import __version__

logger = logging.getLogger("khiip.daemon")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Daemon startup + shutdown hooks.

    Startup:
    - Load config from ~/.config/khiip/config.toml
    - Ensure API key (auto-generate if missing)
    - Open SQLite connection + initialize schema
    Shutdown:
    - Close SQLite connection
    """
    cfg: KhiipConfig = load_config()
    app.state.config = cfg

    api_key = ensure_auth()
    app.state.api_key = api_key
    logger.info("api key ready (%s)", auth_key_fingerprint(api_key))

    conn = storage_db.connect(cfg.db_path)
    version_now = storage_db.init_schema(conn)
    app.state.db = conn
    logger.info("sqlite ready at %s (schema v%d)", cfg.db_path, version_now)

    try:
        yield
    finally:
        try:
            conn.close()
        except Exception:  # pragma: no cover
            logger.exception("error closing sqlite connection")


def create_app() -> FastAPI:
    """Create the FastAPI application.

    Factored for testability — tests can construct a fresh app per test.
    """
    app = FastAPI(
        title="Khiip Daemon",
        description="Capture, store, and recall substrate for LLM agents.",
        version=__version__,
        lifespan=lifespan,
    )

    # ─────────────────────────────────────────────────────────────────
    # Health (no auth required)
    # ─────────────────────────────────────────────────────────────────

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        """Liveness probe. No auth required."""
        sv = storage_db.schema_version(app.state.db) if hasattr(app.state, "db") else 0
        db_path = str(app.state.config.db_path) if hasattr(app.state, "config") else ""
        return HealthResponse(
            status="ok",
            version=__version__,
            schema_version=sv,
            db_path=db_path,
        )

    # ─────────────────────────────────────────────────────────────────
    # /api/v1 — all routes below require Bearer auth
    # ─────────────────────────────────────────────────────────────────

    @app.get("/api/v1/meta", tags=["meta"])
    def meta(_auth: Annotated[str, Depends(verify_bearer)]) -> dict:
        """Authenticated meta endpoint — confirms key + reports daemon state."""
        return {
            "version": __version__,
            "schema_version": storage_db.schema_version(app.state.db),
            "config": {
                "host": app.state.config.host,
                "port": app.state.config.port,
                "vault_path": str(app.state.config.vault_path) if app.state.config.vault_path else None,
            },
        }

    @app.post("/api/v1/captures", tags=["captures"], status_code=501)
    def create_capture(_auth: Annotated[str, Depends(verify_bearer)]) -> dict:
        """POST /api/v1/captures — capture a URL.

        NOT IMPLEMENTED in v0 Week 1 scaffold. Implementation lands in Week 2+
        (extractor dispatch + filesystem writer integration). Returns 501.
        """
        return {"detail": "capture ingestion not implemented in v0 Week 1 scaffold"}

    @app.get("/api/v1/captures", tags=["captures"], status_code=501)
    def list_captures(_auth: Annotated[str, Depends(verify_bearer)]) -> dict:
        """GET /api/v1/captures — list captures with optional filters.

        NOT IMPLEMENTED in v0 Week 1 scaffold. Implementation lands in Week 3+.
        """
        return {"detail": "capture listing not implemented in v0 Week 1 scaffold"}

    return app


# Module-level app for `uvicorn khiip.daemon:app`
app = create_app()
