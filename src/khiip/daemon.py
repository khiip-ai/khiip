"""Khiip FastAPI daemon.

Entrypoint: `khiipd serve` (via cli.py) → `uvicorn khiip.daemon:app …`

The daemon:
- Listens on `127.0.0.1:8478` by default (Tailscale-bind opt-in for power users)
- Auto-generates API key on first launch (~/.config/khiip/auth.toml mode 600)
- Validates Bearer token on every request except /health, /openapi.json, /docs, /redoc
- Initializes SQLite schema on first launch (~/.local/share/khiip/index.db)
- Dispatches POST /api/v1/captures through the ExtractorRegistry (X live in v0 Week 1)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status
from ulid import ULID

from khiip.auth import verify_bearer
from khiip.config import KhiipConfig, auth_key_fingerprint, ensure_auth, load_config
from khiip.extractors import ExtractorRegistry, XExtractor
from khiip.models import Capture, CaptureCreate, HealthResponse
from khiip.storage import captures as storage_captures
from khiip.storage import db as storage_db
from khiip.storage import filesystem as storage_fs
from khiip.version import __version__

logger = logging.getLogger("khiip.daemon")


def _build_default_registry() -> ExtractorRegistry:
    """Build the default extractor registry. Factored for test override."""
    registry = ExtractorRegistry()
    registry.register(XExtractor())
    return registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Daemon startup + shutdown hooks.

    Startup:
    - Load config from ~/.config/khiip/config.toml
    - Ensure API key (auto-generate if missing)
    - Open SQLite connection + initialize schema
    - Ensure vault directory exists
    - Register extractors (XExtractor for v0 Week 1) unless tests pre-populated one
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

    cfg.vault_path.mkdir(parents=True, exist_ok=True)
    logger.info("vault ready at %s", cfg.vault_path)

    # Tests may pre-populate app.state.extractors via dependency-override-style
    # assignment before triggering lifespan; respect that.
    if not hasattr(app.state, "extractors"):
        app.state.extractors = _build_default_registry()
    logger.info("extractors registered: %d", len(app.state.extractors))

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
                "vault_path": str(app.state.config.vault_path),
            },
            "extractors": [ex.source for ex in app.state.extractors],
        }

    @app.post(
        "/api/v1/captures",
        tags=["captures"],
        response_model=Capture,
        status_code=status.HTTP_201_CREATED,
    )
    def create_capture(
        body: CaptureCreate,
        _auth: Annotated[str, Depends(verify_bearer)],
    ) -> Capture:
        """POST /api/v1/captures — capture a URL.

        Pipeline (per v0 spec D3 + D6):
        1. Dedup by SHA-256 url_hash — return existing un-superseded capture if present
        2. Dispatch to first matching extractor (400 if none supports the URL)
        3. Extract via platform API (502 on upstream failure)
        4. Write markdown to vault (canonical) + insert SQLite row (index)
        5. Return Capture model
        """
        url_str = str(body.url)
        url_hash = storage_captures.hash_url(url_str)
        conn = app.state.db

        existing = storage_captures.find_capture_by_url_hash(conn, url_hash)
        if existing is not None:
            return existing

        registry: ExtractorRegistry = app.state.extractors
        extractor = registry.find(url_str)
        if extractor is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"no extractor registered for URL: {url_str}",
            )

        try:
            capture_data = extractor.extract(url_str)
        except httpx.HTTPError as exc:
            logger.warning("extractor upstream failure for %s: %s", url_str, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"upstream fetch failed: {exc}",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        capture_id = str(ULID())
        vault_root = app.state.config.vault_path

        vault_rel = storage_fs.write_capture(
            vault_root=vault_root,
            capture_id=capture_id,
            source=capture_data.source,
            url=url_str,
            title=capture_data.title,
            description=capture_data.description,
            body=capture_data.body_markdown,
            recorded_at=capture_data.recorded_at,
            valid_from=capture_data.valid_from,
            author=capture_data.author,
        )

        with storage_db.transaction(conn):
            storage_captures.insert_capture(
                conn,
                capture_id=capture_id,
                url=url_str,
                url_hash=url_hash,
                capture_data=capture_data,
                vault_path=str(vault_rel),
            )

        stored = storage_captures.find_capture_by_id(conn, capture_id)
        assert stored is not None  # just inserted
        return stored

    @app.get("/api/v1/captures/{capture_id}", tags=["captures"], response_model=Capture)
    def get_capture(
        capture_id: str,
        _auth: Annotated[str, Depends(verify_bearer)],
    ) -> Capture:
        """GET /api/v1/captures/{id} — fetch a single capture by ULID."""
        capture = storage_captures.find_capture_by_id(app.state.db, capture_id)
        if capture is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"capture not found: {capture_id}",
            )
        return capture

    @app.get("/api/v1/captures", tags=["captures"], response_model=list[Capture])
    def list_captures(
        _auth: Annotated[str, Depends(verify_bearer)],
        source: str | None = Query(default=None, description="Filter by source (x | web | pdf | youtube)."),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[Capture]:
        """GET /api/v1/captures — list captures, newest first."""
        return storage_captures.list_captures(
            app.state.db, source=source, limit=limit, offset=offset
        )

    return app


# Module-level app for `uvicorn khiip.daemon:app`
app = create_app()
