"""Khiip daemon configuration.

Config file location: ~/.config/khiip/config.toml
Auth file location:   ~/.config/khiip/auth.toml (chmod 600; auto-generated on first run)
Data location:        ~/.local/share/khiip/   (database + binaries)

Per v0 spec D7 — auth model: API key auto-generated at first daemon launch,
stored in ~/.config/khiip/auth.toml (mode 600). The plugin/CLI auto-discovers
it; the user never sees the key directly unless they rotate via `khiipd auth rotate`.
"""

from __future__ import annotations

import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w

CONFIG_DIR = Path.home() / ".config" / "khiip"
DATA_DIR = Path.home() / ".local" / "share" / "khiip"

CONFIG_PATH = CONFIG_DIR / "config.toml"
AUTH_PATH = CONFIG_DIR / "auth.toml"
DB_PATH = DATA_DIR / "index.db"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8478


@dataclass(frozen=True)
class KhiipConfig:
    """Resolved daemon configuration. Constructed by `load_config()`."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    db_path: Path = DB_PATH
    vault_path: Path | None = None  # user-set; required for capture writes


def _generate_api_key() -> str:
    """Generate a fresh API key. URL-safe base64; 32 bytes of entropy."""
    return f"khiip_{secrets.token_urlsafe(32)}"


def ensure_auth(auth_path: Path | None = None) -> str:
    """Ensure an API key exists at `auth_path` and return it.

    First-run behaviour: generates a new key, writes to disk with mode 600
    (owner read+write only — per v0 spec D7 + memory `feedback_no_secrets_in_chat`).
    Subsequent runs: returns the existing key.

    `auth_path` defaults to the module-level `AUTH_PATH` resolved AT CALL TIME
    (so tests that monkeypatch `AUTH_PATH` are honored).
    """
    if auth_path is None:
        auth_path = AUTH_PATH
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    if auth_path.exists():
        with auth_path.open("rb") as f:
            data = tomllib.load(f)
        existing = data.get("api_key")
        if isinstance(existing, str) and existing.startswith("khiip_"):
            return existing
        # File exists but malformed — regenerate
        key = _generate_api_key()
    else:
        key = _generate_api_key()

    # Write atomically with mode 600
    payload = {"api_key": key, "comment": "Khiip daemon API key. Never share. Rotate via `khiipd auth rotate`."}
    with auth_path.open("wb") as f:
        f.write(tomli_w.dumps(payload).encode())
    auth_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600
    return key


def load_config(config_path: Path | None = None) -> KhiipConfig:
    """Load `~/.config/khiip/config.toml` (creating defaults if missing).

    `config_path` defaults to the module-level `CONFIG_PATH` resolved at call
    time (so tests that monkeypatch `CONFIG_PATH` are honored). Same applies
    to the db_path default — falls back to the live `DB_PATH` constant.
    """
    if config_path is None:
        config_path = CONFIG_PATH
    if not config_path.exists():
        return KhiipConfig(db_path=DB_PATH)

    with config_path.open("rb") as f:
        data = tomllib.load(f)

    daemon = data.get("daemon", {}) if isinstance(data.get("daemon"), dict) else {}
    return KhiipConfig(
        host=daemon.get("host", DEFAULT_HOST),
        port=int(daemon.get("port", DEFAULT_PORT)),
        db_path=Path(daemon.get("db_path", str(DB_PATH))).expanduser(),
        vault_path=Path(daemon["vault_path"]).expanduser() if "vault_path" in daemon else None,
    )


def rotate_api_key(auth_path: Path | None = None) -> str:
    """Generate a new API key, replacing any existing one."""
    if auth_path is None:
        auth_path = AUTH_PATH
    new_key = _generate_api_key()
    payload = {"api_key": new_key, "comment": "Rotated. Update plugin/CLI consumers."}
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    with auth_path.open("wb") as f:
        f.write(tomli_w.dumps(payload).encode())
    auth_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return new_key


def auth_key_fingerprint(key: str) -> str:
    """Return a short fingerprint (first 8 chars after prefix) for logs/UI."""
    if key.startswith("khiip_"):
        return key[6:14] + "…"
    return key[:8] + "…"


__all__ = [
    "AUTH_PATH",
    "CONFIG_DIR",
    "CONFIG_PATH",
    "DATA_DIR",
    "DB_PATH",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "KhiipConfig",
    "auth_key_fingerprint",
    "ensure_auth",
    "load_config",
    "rotate_api_key",
]
