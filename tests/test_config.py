"""Tests for khiip.config — API key bootstrap + rotation + permissions."""

from __future__ import annotations

import stat

from khiip.config import auth_key_fingerprint, ensure_auth, load_config, rotate_api_key


def test_ensure_auth_generates_key_on_first_run(isolated_paths):
    """First call creates a fresh key with khiip_ prefix + mode 600."""
    auth_path = isolated_paths["auth_path"]
    assert not auth_path.exists()

    key = ensure_auth(auth_path=auth_path)

    assert key.startswith("khiip_")
    assert len(key) > 20
    assert auth_path.exists()

    # Verify mode 600 (owner read+write only)
    mode = stat.S_IMODE(auth_path.stat().st_mode)
    assert mode == 0o600, f"expected mode 600, got {oct(mode)}"


def test_ensure_auth_returns_existing_key(isolated_paths):
    """Subsequent calls return the same key (no regeneration)."""
    auth_path = isolated_paths["auth_path"]
    key1 = ensure_auth(auth_path=auth_path)
    key2 = ensure_auth(auth_path=auth_path)
    assert key1 == key2


def test_rotate_api_key_changes_key(isolated_paths):
    """Rotation produces a different key + preserves mode 600."""
    auth_path = isolated_paths["auth_path"]
    original = ensure_auth(auth_path=auth_path)
    rotated = rotate_api_key(auth_path=auth_path)

    assert original != rotated
    assert rotated.startswith("khiip_")
    mode = stat.S_IMODE(auth_path.stat().st_mode)
    assert mode == 0o600


def test_fingerprint_truncates(isolated_paths):
    """Fingerprint is short + ends with ellipsis for log/UI display."""
    key = ensure_auth(auth_path=isolated_paths["auth_path"])
    fp = auth_key_fingerprint(key)
    assert len(fp) < len(key)
    assert fp.endswith("…")


def test_load_config_returns_defaults_when_missing(isolated_paths):
    """No config file → defaults (host 127.0.0.1, port 8478)."""
    cfg = load_config(config_path=isolated_paths["config_dir"] / "config.toml")
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8478
    assert cfg.vault_path is None
