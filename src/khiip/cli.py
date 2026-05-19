"""Khiip CLI — `khiipd` entry point.

Commands:
- `khiipd serve`          Run the FastAPI daemon (default: 127.0.0.1:8478)
- `khiipd auth show`      Print the current API key fingerprint
- `khiipd auth rotate`    Generate a new API key (invalidates the old one)
- `khiipd version`        Print the package version

Distribution per ADR-0002 D1: this CLI ships in the PyInstaller binary +
Docker Compose option.
"""

from __future__ import annotations

import argparse
import sys

import uvicorn

from khiip.config import DEFAULT_HOST, DEFAULT_PORT, auth_key_fingerprint, ensure_auth, rotate_api_key
from khiip.version import __version__


def _cmd_serve(args: argparse.Namespace) -> int:
    """Run the FastAPI daemon."""
    print(f"khiip daemon v{__version__} starting on http://{args.host}:{args.port}")
    print(f"api key fingerprint: {auth_key_fingerprint(ensure_auth())}")
    uvicorn.run(
        "khiip.daemon:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
    )
    return 0


def _cmd_auth_show(_args: argparse.Namespace) -> int:
    """Show the API key fingerprint (never the full key)."""
    key = ensure_auth()
    print(f"api key fingerprint: {auth_key_fingerprint(key)}")
    print("(full key in ~/.config/khiip/auth.toml — never share)")
    return 0


def _cmd_auth_rotate(_args: argparse.Namespace) -> int:
    """Rotate the API key."""
    new_key = rotate_api_key()
    print(f"new api key fingerprint: {auth_key_fingerprint(new_key)}")
    print("(full key in ~/.config/khiip/auth.toml — update plugin/CLI consumers)")
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="khiipd",
        description="Khiip daemon — capture, store, recall substrate for LLM agents.",
    )
    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # serve
    serve = sub.add_parser("serve", help="Run the FastAPI daemon")
    serve.add_argument("--host", default=DEFAULT_HOST, help=f"bind address (default: {DEFAULT_HOST})")
    serve.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port (default: {DEFAULT_PORT})")
    serve.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    serve.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev only)")
    serve.set_defaults(func=_cmd_serve)

    # auth
    auth = sub.add_parser("auth", help="Manage the API key")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True, metavar="SUBCOMMAND")
    auth_show = auth_sub.add_parser("show", help="Show API key fingerprint")
    auth_show.set_defaults(func=_cmd_auth_show)
    auth_rotate = auth_sub.add_parser("rotate", help="Generate a new API key")
    auth_rotate.set_defaults(func=_cmd_auth_rotate)

    # version
    version = sub.add_parser("version", help="Print the package version")
    version.set_defaults(func=_cmd_version)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
