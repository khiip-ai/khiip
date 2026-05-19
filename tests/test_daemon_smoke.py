"""Smoke tests for the FastAPI daemon: lifespan + health + auth + captures + recall."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from khiip.daemon import _compose_embed_text, create_app
from khiip.extractors.base import CaptureData, ExtractorRegistry

from .conftest import StubEmbedder, StubHealthyXExtractor

# ─────────────────────────────────────────────────────────────────────
# Stub extractor — deterministic, no network
# ─────────────────────────────────────────────────────────────────────


class StubExtractor:
    """Stub extractor for offline daemon tests. Supports https://stub.test/ URLs."""

    source: str = "stub"

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    def supports(self, url: str) -> bool:
        return url.startswith("https://stub.test/")

    def extract(self, url: str) -> CaptureData:
        if self._fail:
            raise ValueError(f"stub configured to fail for {url}")
        now = datetime.now(timezone.utc)
        return CaptureData(
            source="stub",
            source_url=url,
            recorded_at=now,
            valid_from=now,
            title="Stub capture title",
            description="Stub capture description",
            author="stub-author",
            body_markdown="Stub body content.",
            extracted_payload={"raw": "stub"},
        )


def _app_with_stub(*, fail: bool = False, embedder: StubEmbedder | None = None):
    """Create a fresh daemon app with stubbed extractor + embedder pre-registered."""
    app = create_app()
    registry = ExtractorRegistry()
    registry.register(StubExtractor(fail=fail))
    app.state.extractors = registry
    app.state.embedder = embedder or StubEmbedder()
    return app


# ─────────────────────────────────────────────────────────────────────
# Health + auth
# ─────────────────────────────────────────────────────────────────────


def _bare_app():
    """create_app() with embedder + X extractor stubbed — keeps /health hermetic.

    XExtractor.health_check() would hit fxtwitter on every /health call
    (flake risk on offline CI). Replace with StubHealthyXExtractor which
    keeps the source name "x" + HealthCheckable contract but does no network.
    WebExtractor is left as default — it doesn't implement HealthCheckable
    so /health doesn't probe it anyway.
    """
    from khiip.extractors import WebExtractor

    app = create_app()
    app.state.embedder = StubEmbedder()

    registry = ExtractorRegistry()
    registry.register(StubHealthyXExtractor())
    registry.register(WebExtractor())
    app.state.extractors = registry
    return app


def test_health_no_auth_required(isolated_paths):
    """GET /health works without Authorization header."""
    app = _bare_app()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert data["schema_version"] >= 1


def test_meta_requires_auth(isolated_paths):
    """GET /api/v1/meta without auth returns 401."""
    app = _bare_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/meta")
        assert response.status_code == 401


def test_meta_with_valid_auth_returns_200(isolated_paths):
    """GET /api/v1/meta with the daemon's generated key returns 200."""
    app = _bare_app()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key

        response = client.get("/api/v1/meta", headers={"Authorization": f"Bearer {api_key}"})
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "schema_version" in data
        assert "extractors" in data
        # default registry registers XExtractor
        assert "x" in data["extractors"]
        # embedder block reports the stub injected by _bare_app
        assert data["embedder"]["model"] == "stub-embedder-v1"


def test_meta_with_invalid_auth_returns_401(isolated_paths):
    """GET /api/v1/meta with a wrong key returns 401."""
    app = _bare_app()
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/meta", headers={"Authorization": "Bearer khiip_wrong_key_value"}
        )
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────
# POST /api/v1/captures
# ─────────────────────────────────────────────────────────────────────


def test_post_capture_creates_capture(isolated_paths):
    """POST /api/v1/captures with a supported URL returns 201 + Capture + writes vault file."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key

        response = client.post(
            "/api/v1/captures",
            json={"url": "https://stub.test/example/1"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["source"] == "stub"
        assert data["title"] == "Stub capture title"
        assert data["author"] == "stub-author"
        assert data["vault_path"].startswith("captures/stub/")
        assert data["archived"] is False

        # Vault file written
        vault_file = isolated_paths["vault_dir"] / data["vault_path"]
        assert vault_file.exists()
        body = vault_file.read_text()
        assert "Stub body content." in body
        assert f'id: "{data["id"]}"' in body


def test_post_capture_dedups_by_url(isolated_paths):
    """Posting the same URL twice returns the original capture (dedup)."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key
        headers = {"Authorization": f"Bearer {api_key}"}

        r1 = client.post(
            "/api/v1/captures", json={"url": "https://stub.test/example/dedup"}, headers=headers
        )
        assert r1.status_code == 201
        id1 = r1.json()["id"]

        r2 = client.post(
            "/api/v1/captures", json={"url": "https://stub.test/example/dedup"}, headers=headers
        )
        # Dedup path: returns existing capture (FastAPI keeps the route's 201 status).
        assert r2.status_code in (200, 201)
        assert r2.json()["id"] == id1


def test_post_capture_unsupported_url_returns_400(isolated_paths):
    """A URL no extractor supports returns 400."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key

        response = client.post(
            "/api/v1/captures",
            json={"url": "https://nowhere.example/article"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response.status_code == 400
        assert "no extractor" in response.json()["detail"].lower()


def test_post_capture_extractor_value_error_returns_400(isolated_paths):
    """ValueError raised by the extractor surfaces as 400."""
    app = _app_with_stub(fail=True)
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key

        response = client.post(
            "/api/v1/captures",
            json={"url": "https://stub.test/example/fail"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response.status_code == 400


def test_post_capture_requires_auth(isolated_paths):
    """POST /api/v1/captures without auth returns 401."""
    app = _app_with_stub()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/captures", json={"url": "https://stub.test/example/auth"}
        )
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────
# GET /api/v1/captures/{id} + GET /api/v1/captures
# ─────────────────────────────────────────────────────────────────────


def test_get_capture_by_id_returns_capture(isolated_paths):
    """Created capture is retrievable by its ULID."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key
        headers = {"Authorization": f"Bearer {api_key}"}

        create = client.post(
            "/api/v1/captures", json={"url": "https://stub.test/example/getbyid"}, headers=headers
        )
        capture_id = create.json()["id"]

        get = client.get(f"/api/v1/captures/{capture_id}", headers=headers)
        assert get.status_code == 200
        assert get.json()["id"] == capture_id


def test_get_capture_by_id_404_when_missing(isolated_paths):
    """Unknown capture ID returns 404."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key

        response = client.get(
            "/api/v1/captures/01HXXXXNOTHING", headers={"Authorization": f"Bearer {api_key}"}
        )
        assert response.status_code == 404


def test_list_captures_returns_newest_first(isolated_paths):
    """GET /api/v1/captures returns captures newest-first; source filter works."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key
        headers = {"Authorization": f"Bearer {api_key}"}

        for i in range(3):
            r = client.post(
                "/api/v1/captures",
                json={"url": f"https://stub.test/example/list/{i}"},
                headers=headers,
            )
            assert r.status_code == 201

        listing = client.get("/api/v1/captures", headers=headers)
        assert listing.status_code == 200
        items = listing.json()
        assert len(items) == 3
        assert all(item["source"] == "stub" for item in items)

        filtered = client.get("/api/v1/captures?source=x", headers=headers)
        assert filtered.status_code == 200
        assert filtered.json() == []


# ─────────────────────────────────────────────────────────────────────
# Embeddings + GET /api/v1/recall
# ─────────────────────────────────────────────────────────────────────


class TopicExtractor:
    """Extractor whose body text is controlled per URL — drives recall tests."""

    source: str = "topic"

    def __init__(self, bodies: dict[str, tuple[str, str]]) -> None:
        # bodies: {url_suffix: (title, body)}
        self._bodies = bodies

    def supports(self, url: str) -> bool:
        return url.startswith("https://topic.test/")

    def extract(self, url: str):
        suffix = url.removeprefix("https://topic.test/")
        title, body = self._bodies[suffix]
        now = datetime.now(timezone.utc)
        return CaptureData(
            source=self.source,
            source_url=url,
            recorded_at=now,
            valid_from=now,
            title=title,
            description=None,
            author="topic-author",
            body_markdown=body,
        )


def _app_with_topic_extractor(bodies, embedder=None):
    app = create_app()
    registry = ExtractorRegistry()
    registry.register(TopicExtractor(bodies))
    app.state.extractors = registry
    app.state.embedder = embedder or StubEmbedder()
    return app


def test_post_capture_writes_embedding_row(isolated_paths):
    """A successful capture inserts a row into `embeddings` for the new capture."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key
        headers = {"Authorization": f"Bearer {api_key}"}

        response = client.post(
            "/api/v1/captures",
            json={"url": "https://stub.test/example/embed-row"},
            headers=headers,
        )
        assert response.status_code == 201
        capture_id = response.json()["id"]

        from khiip.storage import embeddings_store

        row = embeddings_store.find_embedding_by_capture_id(app.state.db, capture_id)
        assert row is not None
        assert row["model"] == "stub-embedder-v1"
        assert row["dimension"] == app.state.embedder.dimension
        assert row["vector"].shape == (app.state.embedder.dimension,)

        # In-memory recall cache stays in sync with the persisted row.
        cached_ids = [r.capture_id for r in app.state.embedding_records]
        assert capture_id in cached_ids


def test_recall_returns_topic_matched_capture_first(isolated_paths):
    """Recall ranks captures sharing query tokens above unrelated ones."""
    bodies = {
        "rust":   ("Rust ownership", "rust ownership borrow checker lifetime"),
        "python": ("Python decorators", "python decorators metaclass dunder"),
        "cooking": ("Pasta recipe", "tomato olive oil garlic basil pasta"),
    }
    app = _app_with_topic_extractor(bodies)
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key
        headers = {"Authorization": f"Bearer {api_key}"}

        ids = {}
        for slug in bodies:
            r = client.post(
                "/api/v1/captures",
                json={"url": f"https://topic.test/{slug}"},
                headers=headers,
            )
            assert r.status_code == 201, r.text
            ids[slug] = r.json()["id"]

        # Query overlapping with the rust body → rust should rank #1
        r = client.get(
            "/api/v1/recall",
            params={"q": "rust borrow checker", "limit": 3},
            headers=headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["embedder_model"] == "stub-embedder-v1"
        assert body["query"] == "rust borrow checker"
        assert len(body["results"]) >= 1
        top = body["results"][0]
        assert top["capture"]["id"] == ids["rust"]
        assert top["score"] > 0.0


def test_recall_empty_corpus_returns_no_results(isolated_paths):
    """With no captures, recall returns an empty results list (not 5xx)."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key

        r = client.get(
            "/api/v1/recall",
            params={"q": "anything"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["results"] == []
        assert body["embedder_model"] == "stub-embedder-v1"


def test_recall_requires_auth(isolated_paths):
    """GET /api/v1/recall without auth returns 401."""
    app = _app_with_stub()
    with TestClient(app) as client:
        r = client.get("/api/v1/recall", params={"q": "anything"})
        assert r.status_code == 401


def test_recall_rejects_empty_query(isolated_paths):
    """GET /api/v1/recall with empty q returns 422 (FastAPI validation)."""
    app = _app_with_stub()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key
        r = client.get(
            "/api/v1/recall",
            params={"q": ""},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 422


def test_capture_succeeds_when_embedding_fails(isolated_paths):
    """If embed() raises, capture still lands; no embedding row inserted."""

    class FailingEmbedder(StubEmbedder):
        def embed(self, text: str) -> list[float]:
            raise RuntimeError("simulated embedder failure")

    app = _app_with_stub(embedder=FailingEmbedder())
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key

        r = client.post(
            "/api/v1/captures",
            json={"url": "https://stub.test/example/embed-fail"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert r.status_code == 201, r.text
        capture_id = r.json()["id"]

        from khiip.storage import embeddings_store

        row = embeddings_store.find_embedding_by_capture_id(app.state.db, capture_id)
        assert row is None  # capture preserved, embedding skipped


# ─────────────────────────────────────────────────────────────────────
# _compose_embed_text — what text gets fed to the embedder per capture
# ─────────────────────────────────────────────────────────────────────


def _make_capture_data(*, title=None, description=None, body=""):
    """Minimal CaptureData factory for _compose_embed_text tests."""
    now = datetime.now(timezone.utc)
    return CaptureData(
        source="test",
        source_url="https://test.example/x",
        recorded_at=now,
        valid_from=now,
        title=title,
        description=description,
        body_markdown=body,
    )


def test_compose_embed_text_all_three_joined_by_double_newline():
    d = _make_capture_data(title="The Title", description="A description.", body="Body paragraph.")
    assert _compose_embed_text(d) == "The Title\n\nA description.\n\nBody paragraph."


def test_compose_embed_text_title_only():
    d = _make_capture_data(title="Just a title")
    assert _compose_embed_text(d) == "Just a title"


def test_compose_embed_text_description_only():
    d = _make_capture_data(description="Just a description")
    assert _compose_embed_text(d) == "Just a description"


def test_compose_embed_text_body_only():
    d = _make_capture_data(body="Just body content")
    assert _compose_embed_text(d) == "Just body content"


def test_compose_embed_text_title_and_body_skip_missing_description():
    d = _make_capture_data(title="T", body="B")
    assert _compose_embed_text(d) == "T\n\nB"


def test_compose_embed_text_all_empty_returns_empty():
    d = _make_capture_data()
    assert _compose_embed_text(d) == ""


def test_compose_embed_text_empty_string_treated_same_as_none():
    d = _make_capture_data(title="", description="", body="")
    assert _compose_embed_text(d) == ""


# ─────────────────────────────────────────────────────────────────────
# KHIIP_HOME override banner — lifespan logs warning when env is set
# ─────────────────────────────────────────────────────────────────────


def test_khiip_home_banner_emitted_when_env_is_set(
    isolated_paths, monkeypatch, caplog
):
    """Setting KHIIP_HOME must produce a visible startup warning banner."""
    import logging

    monkeypatch.setenv("KHIIP_HOME", str(isolated_paths["config_dir"].parent))
    app = _bare_app()
    with caplog.at_level(logging.WARNING, logger="khiip.daemon"):
        with TestClient(app) as client:
            client.get("/health")

    messages = [r.message for r in caplog.records]
    assert any("KHIIP_HOME override in effect" in m for m in messages)
    assert any("Production users should not set KHIIP_HOME" in m for m in messages)
    assert any("GUI clients (Obsidian, Claude Desktop)" in m for m in messages)


def test_khiip_home_banner_silent_when_env_unset(
    isolated_paths, monkeypatch, caplog
):
    """No banner should fire when KHIIP_HOME is not set."""
    import logging

    monkeypatch.delenv("KHIIP_HOME", raising=False)
    app = _bare_app()
    with caplog.at_level(logging.WARNING, logger="khiip.daemon"):
        with TestClient(app) as client:
            client.get("/health")

    messages = [r.message for r in caplog.records]
    assert not any("KHIIP_HOME override" in m for m in messages)
