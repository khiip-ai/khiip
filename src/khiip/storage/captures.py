"""Capture CRUD helpers — SQLite read/write for the `captures` table.

The vault markdown file is canonical; this table is the searchable index.
Per ADR-0007 + v0 spec: the database can be rebuilt from vault if needed.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any

from khiip.extractors.base import CaptureData
from khiip.models import Capture


def hash_url(url: str) -> str:
    """SHA-256 hash of the URL for fast dedup lookup."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def find_capture_by_url_hash(conn: sqlite3.Connection, url_hash: str) -> Capture | None:
    """Return the most-recent un-superseded capture for a given url_hash, or None."""
    row = conn.execute(
        "SELECT * FROM captures WHERE url_hash = ? AND superseded_by IS NULL "
        "ORDER BY recorded_at DESC LIMIT 1",
        (url_hash,),
    ).fetchone()
    return _row_to_capture(row) if row else None


def find_capture_by_id(conn: sqlite3.Connection, capture_id: str) -> Capture | None:
    """Return the capture with the given ULID, or None."""
    row = conn.execute("SELECT * FROM captures WHERE id = ?", (capture_id,)).fetchone()
    return _row_to_capture(row) if row else None


def list_captures(
    conn: sqlite3.Connection,
    *,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Capture]:
    """Return captures ordered by recorded_at DESC, optionally filtered by source."""
    if source:
        rows = conn.execute(
            "SELECT * FROM captures WHERE source = ? AND archived = 0 "
            "ORDER BY recorded_at DESC LIMIT ? OFFSET ?",
            (source, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM captures WHERE archived = 0 "
            "ORDER BY recorded_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [_row_to_capture(row) for row in rows]


def insert_capture(
    conn: sqlite3.Connection,
    *,
    capture_id: str,
    url: str,
    url_hash: str,
    capture_data: CaptureData,
    vault_path: str,
) -> None:
    """Insert a row in the `captures` table. Caller is responsible for transaction handling."""
    body = capture_data.body_markdown or ""
    content_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()

    conn.execute(
        """
        INSERT INTO captures
            (id, url, url_hash, source, vault_path,
             recorded_at, valid_from,
             title, description, author, content_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            capture_id,
            url,
            url_hash,
            capture_data.source,
            vault_path,
            _iso(capture_data.recorded_at),
            _iso(capture_data.valid_from),
            capture_data.title,
            capture_data.description,
            capture_data.author,
            content_sha256,
        ),
    )


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────


def _iso(dt: datetime) -> str:
    """Normalize datetime to ISO 8601 UTC for SQLite TEXT storage."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _row_to_capture(row: Any) -> Capture:
    """Convert a sqlite3.Row to a Capture pydantic model."""
    return Capture(
        id=row["id"],
        url=row["url"],
        source=row["source"],
        vault_path=row["vault_path"],
        title=row["title"],
        description=row["description"],
        author=row["author"],
        recorded_at=_parse_iso(row["recorded_at"]),
        valid_from=_parse_iso(row["valid_from"]),
        archived=bool(row["archived"]),
        superseded_by=row["superseded_by"],
    )


def _parse_iso(value: str) -> datetime:
    """Parse ISO 8601 string back to datetime."""
    return datetime.fromisoformat(value)


__all__ = [
    "find_capture_by_id",
    "find_capture_by_url_hash",
    "hash_url",
    "insert_capture",
    "list_captures",
]
