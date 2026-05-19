"""Khiip CLI — `khiipd` entry point.

Commands:
- `khiipd serve`              Run the FastAPI daemon (default: 127.0.0.1:8478)
- `khiipd capture <url>`      Capture a URL via the running daemon
- `khiipd recall <query>`     Semantic recall against the embedded corpus
- `khiipd auth show`          Print the current API key fingerprint
- `khiipd auth rotate`        Generate a new API key (invalidates the old one)
- `khiipd version`            Print the package version

Distribution per ADR-0002 D1: this CLI ships in the PyInstaller binary +
Docker Compose option.
"""

from __future__ import annotations

import argparse
import sys

import httpx
import uvicorn

from khiip.config import DEFAULT_HOST, DEFAULT_PORT, auth_key_fingerprint, ensure_auth, rotate_api_key
from khiip.version import __version__


def _daemon_base_url(args: argparse.Namespace) -> str:
    return f"http://{args.host}:{args.port}"


def _bearer_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ensure_auth()}"}


def _print_connect_error(args: argparse.Namespace) -> None:
    base = _daemon_base_url(args)
    print(f"error: cannot reach daemon at {base}", file=sys.stderr)
    print(f"hint:  start it with `khiipd serve` (or check --host/--port)", file=sys.stderr)


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


def _cmd_capture(args: argparse.Namespace) -> int:
    """POST a URL to the running daemon's /api/v1/captures."""
    payload: dict = {"url": args.url}
    if args.source_hint:
        payload["source_hint"] = args.source_hint

    try:
        resp = httpx.post(
            f"{_daemon_base_url(args)}/api/v1/captures",
            json=payload,
            headers=_bearer_headers(),
            timeout=args.timeout,
        )
    except httpx.ConnectError:
        _print_connect_error(args)
        return 2

    if resp.status_code in (200, 201):
        cap = resp.json()
        print(f"✓ captured: {cap.get('title') or '(no title)'}")
        print(f"  id:     {cap['id']}")
        print(f"  source: {cap['source']}")
        print(f"  url:    {cap['url']}")
        print(f"  vault:  {cap['vault_path']}")
        return 0
    if resp.status_code == 401:
        print("error: 401 — API key mismatch; try `khiipd auth show`", file=sys.stderr)
        return 3
    detail = ""
    try:
        detail = resp.json().get("detail", "")
    except Exception:
        detail = resp.text[:200]
    print(f"error: {resp.status_code} — {detail}", file=sys.stderr)
    return 4


def _cmd_recall(args: argparse.Namespace) -> int:
    """GET /api/v1/recall against the running daemon."""
    try:
        resp = httpx.get(
            f"{_daemon_base_url(args)}/api/v1/recall",
            params={"q": args.query, "limit": args.limit},
            headers=_bearer_headers(),
            timeout=args.timeout,
        )
    except httpx.ConnectError:
        _print_connect_error(args)
        return 2

    if resp.status_code == 401:
        print("error: 401 — API key mismatch; try `khiipd auth show`", file=sys.stderr)
        return 3
    if resp.status_code != 200:
        print(f"error: {resp.status_code} — {resp.text[:200]}", file=sys.stderr)
        return 4

    data = resp.json()
    results = data.get("results", [])
    print(f"query:    {data['query']}")
    print(f"embedder: {data['embedder_model']} (dim={data['embedder_dimension']})")
    if not results:
        print("(no results — capture some URLs first via `khiipd capture <url>`)")
        return 0
    print()
    for hit in results:
        cap = hit["capture"]
        title = cap.get("title") or "(no title)"
        print(f"  {hit['score']:.4f}  {title[:60]}")
        print(f"          {cap['url']}")
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

    # capture
    capture = sub.add_parser("capture", help="Capture a URL via the running daemon")
    capture.add_argument("url", help="URL to capture (e.g. https://x.com/jack/status/20)")
    capture.add_argument("--source-hint", help="Optional source hint (x | web | pdf | youtube)")
    capture.add_argument("--host", default=DEFAULT_HOST, help=f"daemon host (default: {DEFAULT_HOST})")
    capture.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"daemon port (default: {DEFAULT_PORT})")
    capture.add_argument("--timeout", type=float, default=30.0, help="request timeout in seconds (default: 30)")
    capture.set_defaults(func=_cmd_capture)

    # recall
    recall = sub.add_parser("recall", help="Semantic recall against the embedded corpus")
    recall.add_argument("query", help="Natural-language recall query (quote if multi-word)")
    recall.add_argument("--limit", type=int, default=10, help="max results (default: 10)")
    recall.add_argument("--host", default=DEFAULT_HOST, help=f"daemon host (default: {DEFAULT_HOST})")
    recall.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"daemon port (default: {DEFAULT_PORT})")
    recall.add_argument("--timeout", type=float, default=30.0, help="request timeout in seconds (default: 30)")
    recall.set_defaults(func=_cmd_recall)

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
