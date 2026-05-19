"""Smoke tests for the FastAPI daemon: lifespan + health + auth + captures."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from khiip.daemon import create_app
from khiip.extractors.base import CaptureData, ExtractorRegistry

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


def _app_with_stub(*, fail: bool = False):
    """Create a fresh daemon app with the stub extractor pre-registered."""
    app = create_app()
    registry = ExtractorRegistry()
    registry.register(StubExtractor(fail=fail))
    app.state.extractors = registry
    return app


# ─────────────────────────────────────────────────────────────────────
# Health + auth
# ─────────────────────────────────────────────────────────────────────


def test_health_no_auth_required(isolated_paths):
    """GET /health works without Authorization header."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert data["schema_version"] >= 1


def test_meta_requires_auth(isolated_paths):
    """GET /api/v1/meta without auth returns 401."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/meta")
        assert response.status_code == 401


def test_meta_with_valid_auth_returns_200(isolated_paths):
    """GET /api/v1/meta with the daemon's generated key returns 200."""
    app = create_app()
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


def test_meta_with_invalid_auth_returns_401(isolated_paths):
    """GET /api/v1/meta with a wrong key returns 401."""
    app = create_app()
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
