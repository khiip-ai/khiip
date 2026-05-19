"""Pytest configuration: per-test isolated config + DB directories + StubEmbedder."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from khiip import config as khiip_config
from khiip.storage import db as storage_db


class StubEmbedder:
    """Deterministic offline embedder for tests.

    Token-bag projection: each whitespace-split token contributes +1 to the
    bin `md5(token) mod dimension`. Properties relied on by tests:

    - Identical text → identical vector
    - Texts sharing tokens → non-orthogonal vectors (cosine > 0)
    - Texts with no shared tokens → orthogonal (cosine ≈ 0)
    - No network, no model load, microsecond inference
    - Deterministic across processes (md5, not Python's salted hash())
    """

    model_name: str = "stub-embedder-v1"

    def __init__(self, dimension: int = 16) -> None:
        self.dimension = dimension

    def warmup(self) -> None:
        return None

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        for token in text.lower().split():
            idx = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dimension
            vec[idx] += 1.0
        return vec

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


@pytest.fixture
def stub_embedder() -> StubEmbedder:
    """A fresh StubEmbedder. Inject before TestClient(app) triggers lifespan."""
    return StubEmbedder()


@pytest.fixture
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect ~/.config/khiip and ~/.local/share/khiip into a tmp dir.

    Prevents tests from polluting the real user config/data and from reading
    a pre-existing API key on the developer's machine.
    """
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    vault_dir = tmp_path / "vault"

    config_dir.mkdir()
    data_dir.mkdir()
    # vault_dir is created by daemon lifespan; don't pre-create

    monkeypatch.setattr(khiip_config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(khiip_config, "DATA_DIR", data_dir)
    monkeypatch.setattr(khiip_config, "CONFIG_PATH", config_dir / "config.toml")
    monkeypatch.setattr(khiip_config, "AUTH_PATH", config_dir / "auth.toml")
    monkeypatch.setattr(khiip_config, "DB_PATH", data_dir / "index.db")
    monkeypatch.setattr(khiip_config, "DEFAULT_VAULT_PATH", vault_dir)
    monkeypatch.setattr(storage_db, "DEFAULT_DB_PATH", data_dir / "index.db")

    return {
        "config_dir": config_dir,
        "data_dir": data_dir,
        "vault_dir": vault_dir,
        "auth_path": config_dir / "auth.toml",
        "db_path": data_dir / "index.db",
    }
