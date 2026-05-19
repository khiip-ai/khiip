"""Filesystem writer: capture → markdown file with bitemporal frontmatter.

Per v0 spec D3 + D6 + D8:
- Per-source subfolders under `captures/`: x/ web/ pdf/ youtube/
- ULID-prefixed filename: `{ULID}-{slug}.md`
- Frontmatter is YAML; body is markdown
- Bitemporal: both `recorded_at` (when Khiip fetched) and `valid_from` (when data was true)

This module writes; reading is done by `khiip.storage.db` for the index.
The vault markdown is canonical — the SQLite DB can be rebuilt from these files.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

# Maximum slug length (filesystem-friendly; URL-safe)
SLUG_MAX_LEN = 60


def slugify(text: str, *, max_len: int = SLUG_MAX_LEN) -> str:
    """Convert text to a filesystem-safe slug.

    Lowercases, replaces non-alphanumeric with `-`, collapses runs, trims.
    Returns 'untitled' if input produces an empty slug.
    """
    if not text:
        return "untitled"
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    s = s[:max_len].rstrip("-")
    return s or "untitled"


def capture_filename(capture_id: str, title: str | None) -> str:
    """Return `{ULID}-{slug}.md` filename."""
    slug = slugify(title or "untitled")
    return f"{capture_id}-{slug}.md"


def capture_subfolder(source: str) -> str:
    """Map source name to the per-source vault subfolder.

    Per v0 spec D3 — per-source subfolders, each independently configurable.
    """
    return f"captures/{source}/"


def _format_frontmatter(meta: dict) -> str:
    """Render a YAML frontmatter block from a dict.

    Keeps values quoted (string-safe) and stable-ordered. No external YAML
    dependency — simple keys/values only at v0.
    """
    lines = ["---"]
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, datetime):
            lines.append(f"{key}: {value.isoformat()}")
        elif isinstance(value, str):
            # Quote strings that could be ambiguous
            escaped = value.replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def write_capture(
    *,
    vault_root: Path,
    capture_id: str,
    source: str,
    url: str,
    title: str | None,
    description: str | None,
    body: str,
    recorded_at: datetime,
    valid_from: datetime,
    author: str | None = None,
    extra_frontmatter: dict | None = None,
) -> Path:
    """Write a capture's markdown file to the vault and return the path.

    Returns the relative path from `vault_root`.
    """
    subfolder = capture_subfolder(source)
    folder = vault_root / subfolder
    folder.mkdir(parents=True, exist_ok=True)

    filename = capture_filename(capture_id, title)
    path = folder / filename

    meta = {
        "id": capture_id,
        "url": url,
        "source": source,
        "title": title,
        "description": description,
        "author": author,
        "recorded_at": recorded_at,
        "valid_from": valid_from,
        "schema_version": "0.1",
    }
    if extra_frontmatter:
        meta.update(extra_frontmatter)

    content = _format_frontmatter(meta) + "\n" + (body or "")
    path.write_text(content, encoding="utf-8")
    return path.relative_to(vault_root)


__all__ = [
    "SLUG_MAX_LEN",
    "capture_filename",
    "capture_subfolder",
    "slugify",
    "write_capture",
]
