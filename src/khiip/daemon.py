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

import hashlib
import os

import httpx
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, status
from ulid import ULID

from khiip.auth import verify_bearer
from khiip.config import (
    CONFIG_DIR,
    KhiipConfig,
    auth_key_fingerprint,
    ensure_auth,
    load_config,
)
from khiip.embeddings import Embedder, MiniLMEmbedder
from khiip.extractors import ExtractorRegistry, PdfExtractor, WebExtractor, XExtractor
from khiip.extractors.base import CaptureData
from khiip.extractors.resilience import (
    ExtractorError,
    HealthCheckable,
    HealthStatus,
)
from khiip.models import (
    Capture,
    CaptureCreate,
    ExtractorHealth,
    HealthResponse,
    RecallHit,
    RecallResponse,
)
from khiip.storage import captures as storage_captures
from khiip.storage import db as storage_db
from khiip.storage import embeddings_store
from khiip.storage import filesystem as storage_fs
from khiip.version import __version__

logger = logging.getLogger("khiip.daemon")


def _build_default_registry() -> ExtractorRegistry:
    """Build the default extractor registry. Factored for test override.

    Order matters: registry.find() returns the FIRST extractor whose
    supports(url) is True. Domain-specific extractors must register
    BEFORE WebExtractor's catch-all http(s) handler.
    """
    registry = ExtractorRegistry()
    registry.register(XExtractor())  # x.com / twitter.com
    registry.register(PdfExtractor())  # *.pdf URLs — before WebExtractor's http(s) catch-all
    registry.register(WebExtractor())  # generic http(s) fallback — keep last
    return registry


def _build_default_embedder() -> Embedder:
    """Build the default embedder (MiniLM-L6 ONNX). Factored for test override."""
    return MiniLMEmbedder()


def _compose_embed_text(data: CaptureData) -> str:
    """Compose the text we feed to the embedder per capture.

    Locked 2026-05-19: title + description + body. fastembed truncates at the
    model's max sequence length (256 tokens for MiniLM-L6) internally; we don't
    truncate upstream so a future swap to a larger-context embedder picks up
    the trailing content automatically.
    """
    parts: list[str] = []
    if data.title:
        parts.append(data.title)
    if data.description:
        parts.append(data.description)
    if data.body_markdown:
        parts.append(data.body_markdown)
    return "\n\n".join(parts)


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

    if os.environ.get("KHIIP_HOME"):
        logger.warning("=" * 64)
        logger.warning("KHIIP_HOME override in effect — dev/test mode")
        logger.warning("  config:  %s", CONFIG_DIR)
        logger.warning("  data:    %s", cfg.db_path.parent)
        logger.warning("  vault:   %s", cfg.vault_path)
        logger.warning("Production users should not set KHIIP_HOME.")
        logger.warning("GUI clients (Obsidian, Claude Desktop) do NOT see this override.")
        logger.warning("=" * 64)

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

    # Same injection pattern for the embedder — tests inject StubEmbedder
    # before TestClient(app) triggers lifespan.
    if not hasattr(app.state, "embedder"):
        app.state.embedder = _build_default_embedder()
    embedder: Embedder = app.state.embedder
    try:
        embedder.warmup()
        logger.info("embedder ready: %s (dim=%d)", embedder.model_name, embedder.dimension)
    except Exception:
        logger.exception("embedder warmup failed; recall will return empty until resolved")

    # Load existing embeddings into memory once at startup; subsequent inserts
    # append to this list, so /api/v1/recall never re-hits SQLite for the corpus.
    # ADR-0007 Probe 3 sized SQLite at 50K rows; this cache keeps the hot path
    # at numpy stack + cosine on the in-memory matrix.
    app.state.embedding_records = embeddings_store.load_all_vectors(
        conn, model=embedder.model_name
    )
    logger.info("embedding cache loaded: %d records", len(app.state.embedding_records))

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
        """Liveness probe. No auth required.

        Surfaces per-extractor health for sources that implement
        `HealthCheckable`. Each implementor uses its own short-timeout probe
        so /health doesn't block on a hung upstream. Overall status is
        "degraded" iff any extractor reports ok=False.
        """
        sv = storage_db.schema_version(app.state.db) if hasattr(app.state, "db") else 0
        db_path = str(app.state.config.db_path) if hasattr(app.state, "config") else ""

        extractor_healths: list[ExtractorHealth] = []
        if hasattr(app.state, "extractors"):
            for extractor in app.state.extractors:
                if isinstance(extractor, HealthCheckable):
                    try:
                        status_obj: HealthStatus = extractor.health_check()
                        extractor_healths.append(
                            ExtractorHealth(
                                source=status_obj.source,
                                ok=status_obj.ok,
                                degraded_reason=status_obj.degraded_reason,
                                fallback_count=status_obj.fallback_count,
                            )
                        )
                    except Exception as exc:  # pragma: no cover — defensive
                        logger.exception("health_check raised for %s", extractor.source)
                        extractor_healths.append(
                            ExtractorHealth(
                                source=extractor.source,
                                ok=False,
                                degraded_reason=f"health_check exception: {type(exc).__name__}",
                            )
                        )

        overall = "degraded" if any(not h.ok for h in extractor_healths) else "ok"
        return HealthResponse(
            status=overall,
            version=__version__,
            schema_version=sv,
            db_path=db_path,
            extractors=extractor_healths,
        )

    # ─────────────────────────────────────────────────────────────────
    # /api/v1 — all routes below require Bearer auth
    # ─────────────────────────────────────────────────────────────────

    @app.get("/api/v1/meta", tags=["meta"])
    def meta(_auth: Annotated[str, Depends(verify_bearer)]) -> dict:
        """Authenticated meta endpoint — confirms key + reports daemon state."""
        embedder: Embedder = app.state.embedder
        return {
            "version": __version__,
            "schema_version": storage_db.schema_version(app.state.db),
            "config": {
                "host": app.state.config.host,
                "port": app.state.config.port,
                "vault_path": str(app.state.config.vault_path),
            },
            "extractors": [ex.source for ex in app.state.extractors],
            "embedder": {
                "model": embedder.model_name,
                "dimension": embedder.dimension,
            },
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
        except ExtractorError as exc:
            logger.warning(
                "extractor fallback chain exhausted for %s: %s", url_str, exc.reason
            )
            headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"all upstream sources failed: {exc.reason}",
                headers=headers,
            ) from exc
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

        # Embed the capture for semantic recall. Capture is sacred — if the
        # embedder fails, we log + continue; the capture still lands and
        # remains backfillable via a future `khiipd embed --backfill` command.
        embedder: Embedder = app.state.embedder
        embed_text = _compose_embed_text(capture_data)
        if embed_text:
            try:
                vector = embedder.embed(embed_text)
                # content_sha256 is write-only today; reserved for a future
                # passive-tracking pipeline (decay-cadence refresh + velocity-spike
                # trigger) that re-embeds a capture only when its upstream body
                # has actually changed, leaving engagement-only updates alone.
                with storage_db.transaction(conn):
                    embeddings_store.insert_embedding(
                        conn,
                        capture_id=capture_id,
                        model=embedder.model_name,
                        dimension=embedder.dimension,
                        vector=vector,
                        content_sha256=hashlib.sha256(embed_text.encode("utf-8")).hexdigest(),
                    )
                # Keep the in-memory recall cache in sync with the persisted row.
                # Single-method list.append is GIL-atomic; concurrent POSTs cannot
                # corrupt the list (a parallel recall may miss the new record by
                # one request, which is acceptable).
                app.state.embedding_records.append(
                    embeddings_store.EmbeddingRecord(
                        capture_id=capture_id,
                        vector=np.asarray(vector, dtype=np.float32),
                    )
                )
            except Exception:
                logger.exception(
                    "embedding failed for capture %s; capture preserved, recall will skip it",
                    capture_id,
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

    @app.get("/api/v1/recall", tags=["recall"], response_model=RecallResponse)
    def recall(
        _auth: Annotated[str, Depends(verify_bearer)],
        q: str = Query(..., min_length=1, description="Natural-language recall query."),
        limit: int = Query(default=10, ge=1, le=100),
    ) -> RecallResponse:
        """GET /api/v1/recall — semantic top-k over embedded captures.

        Pipeline:
        1. Embed query with the daemon's configured embedder
        2. Load all stored vectors matching that embedder's model
        3. Cosine top-k
        4. Hydrate Capture rows + return with scores

        Captures without embeddings (embedder failed at capture time, or stored
        under a different model than the current one) are silently excluded —
        a future `khiipd embed --backfill` command will repair the gap.
        """
        embedder: Embedder = app.state.embedder
        conn = app.state.db

        records = app.state.embedding_records
        if not records:
            return RecallResponse(
                query=q,
                embedder_model=embedder.model_name,
                embedder_dimension=embedder.dimension,
                results=[],
            )

        try:
            query_vector = embedder.embed(q)
        except Exception as exc:
            logger.exception("embedder failed on recall query")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="embedder unavailable",
            ) from exc

        ranked = embeddings_store.cosine_topk(query_vector, records, limit=limit)

        hit_ids = [capture_id for capture_id, _ in ranked]
        captures_by_id = storage_captures.find_captures_by_ids(conn, hit_ids)
        hits: list[RecallHit] = []
        for capture_id, score in ranked:
            capture = captures_by_id.get(capture_id)
            if capture is None:  # embedding outlived its capture (cascade deletes guard this)
                continue
            hits.append(RecallHit(capture=capture, score=score))

        return RecallResponse(
            query=q,
            embedder_model=embedder.model_name,
            embedder_dimension=embedder.dimension,
            results=hits,
        )

    return app


# Module-level app for `uvicorn khiip.daemon:app`
app = create_app()
