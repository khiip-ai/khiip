"""SQLite connection + migration management.

Khiip uses a single SQLite database at `~/.local/share/khiip/index.db` as the
index + graph layer. The vault markdown (per-capture .md files) is canonical;
this database can be rebuilt from vault if needed.

Schema authority: ADR-0007 (custom SQLite graph layer), ADR-0008 (5+1 canonical
edge vocabulary), ADR-0005 (Option Δ hybrid edge typing).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "khiip" / "index.db"

CURRENT_SCHEMA_VERSION = 1


def _read_schema_sql() -> str:
    """Load schema.sql from the package resources."""
    return (resources.files("khiip.storage") / "schema.sql").read_text()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with Khiip's standard pragmas.

    Creates parent directory if missing. Enables WAL mode + foreign keys.

    `check_same_thread=False` permits cross-thread access — required because
    FastAPI runs handlers in a thread pool and shares the connection across
    threads. WAL mode provides safe concurrent reads + single-writer
    semantics; application-layer locking handles write serialization.
    """
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        path,
        isolation_level=None,  # autocommit; explicit BEGIN for tx
        check_same_thread=False,  # see docstring; required for FastAPI thread pool
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> int:
    """Apply the schema if not already present. Returns the schema version after init."""
    conn.executescript(_read_schema_sql())
    row = conn.execute(
        "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
    ).fetchone()
    return int(row["version"]) if row else 0


def schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version (0 if not initialized)."""
    try:
        row = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        return int(row["version"]) if row else 0
    except sqlite3.OperationalError:
        return 0  # table doesn't exist yet


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Explicit transaction context manager. Rolls back on exception."""
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
