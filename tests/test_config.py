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
    """No config file → defaults (host 127.0.0.1, port 8478, default vault dir)."""
    cfg = load_config(config_path=isolated_paths["config_dir"] / "config.toml")
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8478
    # vault_path defaults to ~/khiip-vault/ (monkeypatched in isolated_paths)
    assert cfg.vault_path == isolated_paths["vault_dir"]


# ─────────────────────────────────────────────────────────────────────
# Per-extractor opt-in credentials — youtube_api_key resolution
# ─────────────────────────────────────────────────────────────────────


def test_load_config_youtube_api_key_none_when_unset(isolated_paths, monkeypatch):
    """No env var + no config.toml → youtube_api_key is None (2-source chain)."""
    monkeypatch.delenv("KHIIP_YOUTUBE_API_KEY", raising=False)
    cfg = load_config(config_path=isolated_paths["config_dir"] / "config.toml")
    assert cfg.youtube_api_key is None


def test_load_config_youtube_api_key_from_env_var(isolated_paths, monkeypatch):
    """KHIIP_YOUTUBE_API_KEY env var populates the dataclass field."""
    monkeypatch.setenv("KHIIP_YOUTUBE_API_KEY", "AIza_from_env")
    cfg = load_config(config_path=isolated_paths["config_dir"] / "config.toml")
    assert cfg.youtube_api_key == "AIza_from_env"


def test_load_config_youtube_api_key_from_config_toml(isolated_paths, monkeypatch):
    """[extractors.youtube] api_key in config.toml populates the dataclass field."""
    monkeypatch.delenv("KHIIP_YOUTUBE_API_KEY", raising=False)
    config_path = isolated_paths["config_dir"] / "config.toml"
    config_path.write_text(
        "[extractors.youtube]\napi_key = \"AIza_from_file\"\n"
    )
    cfg = load_config(config_path=config_path)
    assert cfg.youtube_api_key == "AIza_from_file"


def test_load_config_youtube_api_key_env_wins_over_config_toml(isolated_paths, monkeypatch):
    """Env var precedence: both set → env var value wins."""
    monkeypatch.setenv("KHIIP_YOUTUBE_API_KEY", "AIza_from_env")
    config_path = isolated_paths["config_dir"] / "config.toml"
    config_path.write_text(
        "[extractors.youtube]\napi_key = \"AIza_from_file\"\n"
    )
    cfg = load_config(config_path=config_path)
    assert cfg.youtube_api_key == "AIza_from_env"


def test_load_config_youtube_api_key_empty_string_treated_as_none(isolated_paths, monkeypatch):
    """Empty-string env var falls back to config.toml (which is also missing → None)."""
    monkeypatch.setenv("KHIIP_YOUTUBE_API_KEY", "")
    cfg = load_config(config_path=isolated_paths["config_dir"] / "config.toml")
    assert cfg.youtube_api_key is None
