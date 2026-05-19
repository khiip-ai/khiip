"""Smoke tests for the FastAPI daemon: lifespan + health + auth."""

from __future__ import annotations

from fastapi.testclient import TestClient

from khiip.daemon import create_app


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
        # Trigger lifespan to bootstrap auth
        client.get("/health")
        api_key = app.state.api_key

        response = client.get("/api/v1/meta", headers={"Authorization": f"Bearer {api_key}"})
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "schema_version" in data


def test_meta_with_invalid_auth_returns_401(isolated_paths):
    """GET /api/v1/meta with a wrong key returns 401."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/meta", headers={"Authorization": "Bearer khiip_wrong_key_value"}
        )
        assert response.status_code == 401


def test_captures_post_returns_501_in_week1_scaffold(isolated_paths):
    """POST /api/v1/captures returns 501 (not yet implemented in v0 Week 1)."""
    app = create_app()
    with TestClient(app) as client:
        client.get("/health")
        api_key = app.state.api_key

        response = client.post(
            "/api/v1/captures",
            json={"url": "https://example.com/article"},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert response.status_code == 501
