"""Pytest configuration: per-test isolated config + DB directories."""

from __future__ import annotations

from pathlib import Path

import pytest

from khiip import config as khiip_config
from khiip.storage import db as storage_db


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
