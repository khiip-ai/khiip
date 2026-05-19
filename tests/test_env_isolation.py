"""Unit tests for KHIIP_HOME + XDG path resolution in `khiip.config`.

Pure-unit: no subprocess, no network, no `Path.home()` invariant assertions.
Verifies the resolver functions directly, so the contract is enforced at the
code boundary — not by hoping out-of-process smokes notice when it regresses.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from khiip import config as khiip_config


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KHIIP_HOME", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)


# ─────────────────────────────────────────────────────────────────────
# Defaults — no env vars set
# ─────────────────────────────────────────────────────────────────────


def test_default_config_dir_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    assert khiip_config._resolve_config_dir() == Path.home() / ".config" / "khiip"


def test_default_data_dir_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    assert khiip_config._resolve_data_dir() == Path.home() / ".local" / "share" / "khiip"


def test_default_vault_path_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    assert khiip_config._resolve_vault_path() == Path.home() / "khiip-vault"


# ─────────────────────────────────────────────────────────────────────
# KHIIP_HOME — workspace override (highest precedence)
# ─────────────────────────────────────────────────────────────────────


def test_khiip_home_sets_all_three_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("KHIIP_HOME", str(tmp_path))
    assert khiip_config._resolve_config_dir() == tmp_path / "config"
    assert khiip_config._resolve_data_dir() == tmp_path / "data"
    assert khiip_config._resolve_vault_path() == tmp_path / "vault"


def test_khiip_home_overrides_xdg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KHIIP_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", "/this-should-be-ignored")
    monkeypatch.setenv("XDG_DATA_HOME", "/this-too")
    assert khiip_config._resolve_config_dir() == tmp_path / "config"
    assert khiip_config._resolve_data_dir() == tmp_path / "data"


def test_khiip_home_expands_tilde(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KHIIP_HOME", "~/khiip-smoke-sandbox")
    expected = (Path.home() / "khiip-smoke-sandbox").resolve()
    assert khiip_config._resolve_config_dir() == expected / "config"


def test_khiip_home_empty_string_treated_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("KHIIP_HOME", "")
    assert khiip_config._resolve_config_dir() == Path.home() / ".config" / "khiip"


# ─────────────────────────────────────────────────────────────────────
# XDG_* — middle precedence (only when KHIIP_HOME unset)
# ─────────────────────────────────────────────────────────────────────


def test_xdg_config_home_honored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert khiip_config._resolve_config_dir() == tmp_path / "khiip"


def test_xdg_data_home_honored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert khiip_config._resolve_data_dir() == tmp_path / "khiip"


def test_xdg_does_not_affect_vault_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Vault is user-data (lives in $HOME by convention), not XDG_DATA_HOME."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert khiip_config._resolve_vault_path() == Path.home() / "khiip-vault"


# ─────────────────────────────────────────────────────────────────────
# Precedence
# ─────────────────────────────────────────────────────────────────────


def test_precedence_khiip_home_beats_xdg(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    khiip = tmp_path / "khiip-home"
    xdg = tmp_path / "xdg-home"
    monkeypatch.setenv("KHIIP_HOME", str(khiip))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    assert khiip_config._resolve_config_dir() == khiip / "config"
    assert khiip_config._resolve_data_dir() == khiip / "data"


def test_resolve_root_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    assert khiip_config._resolve_root() is None


def test_resolve_root_returns_path_when_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("KHIIP_HOME", str(tmp_path))
    assert khiip_config._resolve_root() == tmp_path.resolve()
