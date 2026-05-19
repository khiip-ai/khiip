"""Tests for khiip.storage — SQLite schema + filesystem writer."""

from __future__ import annotations

from datetime import datetime, timezone

from ulid import ULID

from khiip.storage import db as storage_db
from khiip.storage.filesystem import capture_filename, slugify, write_capture


def test_init_schema_creates_tables(isolated_paths):
    """init_schema creates all tables + reports version 1."""
    conn = storage_db.connect(isolated_paths["db_path"])
    version = storage_db.init_schema(conn)
    assert version == 1

    # Verify expected tables exist
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = {row["name"] for row in rows}
    expected = {"schema_version", "captures", "embeddings", "graph_edges", "api_keys"}
    assert expected.issubset(table_names), f"missing tables: {expected - table_names}"

    conn.close()


def test_schema_version_zero_before_init(isolated_paths):
    """schema_version returns 0 on a fresh DB before init."""
    conn = storage_db.connect(isolated_paths["db_path"])
    assert storage_db.schema_version(conn) == 0
    conn.close()


def test_graph_edges_canonical_constraint_accepts_canonical(isolated_paths):
    """vocab_match=1 + canonical edge_type → insert succeeds."""
    conn = storage_db.connect(isolated_paths["db_path"])
    storage_db.init_schema(conn)
    now = datetime.now(timezone.utc).isoformat()

    # Insert two captures first
    cap_a = str(ULID())
    cap_b = str(ULID())
    for cap_id in (cap_a, cap_b):
        conn.execute(
            "INSERT INTO captures(id, url, url_hash, source, vault_path, recorded_at, valid_from) "
            "VALUES (?, ?, ?, 'web', 'captures/web/x.md', ?, ?)",
            (cap_id, f"https://example.com/{cap_id}", f"hash_{cap_id}", now, now),
        )

    # Each canonical edge_type should be accepted with vocab_match=1
    for edge_type in ("SUPPORTS", "CONTRADICTS", "SUPERSEDES", "ELABORATES", "REFERENCES", "RELATES"):
        conn.execute(
            "INSERT INTO graph_edges(source_capture_id, target_capture_id, edge_type, vocab_match, "
            "evidence_span, confidence, recorded_at, valid_from) "
            "VALUES (?, ?, ?, 1, ?, 0.9, ?, ?)",
            (cap_a, cap_b, edge_type, f"evidence for {edge_type}", now, now),
        )

    count = conn.execute("SELECT COUNT(*) AS c FROM graph_edges").fetchone()["c"]
    assert count == 6
    conn.close()


def test_graph_edges_canonical_constraint_rejects_unknown(isolated_paths):
    """vocab_match=1 + non-canonical edge_type → CHECK constraint blocks."""
    import sqlite3

    conn = storage_db.connect(isolated_paths["db_path"])
    storage_db.init_schema(conn)
    now = datetime.now(timezone.utc).isoformat()

    cap_a = str(ULID())
    conn.execute(
        "INSERT INTO captures(id, url, url_hash, source, vault_path, recorded_at, valid_from) "
        "VALUES (?, ?, ?, 'web', 'captures/web/x.md', ?, ?)",
        (cap_a, "https://example.com/a", "hash_a", now, now),
    )

    try:
        conn.execute(
            "INSERT INTO graph_edges(source_capture_id, edge_type, vocab_match, "
            "evidence_span, confidence, recorded_at, valid_from) "
            "VALUES (?, 'NOT_A_REAL_EDGE', 1, 'evidence', 0.8, ?, ?)",
            (cap_a, now, now),
        )
    except sqlite3.IntegrityError:
        pass  # expected
    else:
        raise AssertionError("expected CHECK constraint to reject non-canonical edge_type")

    conn.close()


def test_graph_edges_emergent_accepts_any_label(isolated_paths):
    """vocab_match=0 + any label → insert succeeds (emergent escape)."""
    conn = storage_db.connect(isolated_paths["db_path"])
    storage_db.init_schema(conn)
    now = datetime.now(timezone.utc).isoformat()

    cap_a = str(ULID())
    conn.execute(
        "INSERT INTO captures(id, url, url_hash, source, vault_path, recorded_at, valid_from) "
        "VALUES (?, ?, ?, 'web', 'captures/web/x.md', ?, ?)",
        (cap_a, "https://example.com/a", "hash_a", now, now),
    )

    conn.execute(
        "INSERT INTO graph_edges(source_capture_id, edge_type, vocab_match, "
        "evidence_span, confidence, recorded_at, valid_from) "
        "VALUES (?, 'NOVEL_EMERGENT_RELATION', 0, 'evidence', 0.6, ?, ?)",
        (cap_a, now, now),
    )

    count = conn.execute("SELECT COUNT(*) AS c FROM graph_edges WHERE vocab_match=0").fetchone()["c"]
    assert count == 1
    conn.close()


def test_graph_edges_confidence_range_enforced(isolated_paths):
    """confidence must be in [0.0, 1.0]; out-of-range rejected."""
    import sqlite3

    conn = storage_db.connect(isolated_paths["db_path"])
    storage_db.init_schema(conn)
    now = datetime.now(timezone.utc).isoformat()

    cap_a = str(ULID())
    conn.execute(
        "INSERT INTO captures(id, url, url_hash, source, vault_path, recorded_at, valid_from) "
        "VALUES (?, ?, ?, 'web', 'captures/web/x.md', ?, ?)",
        (cap_a, "https://example.com/a", "hash_a", now, now),
    )

    try:
        conn.execute(
            "INSERT INTO graph_edges(source_capture_id, edge_type, vocab_match, "
            "evidence_span, confidence, recorded_at, valid_from) "
            "VALUES (?, 'SUPPORTS', 1, 'evidence', 1.5, ?, ?)",
            (cap_a, now, now),
        )
    except sqlite3.IntegrityError:
        pass  # expected
    else:
        raise AssertionError("expected CHECK constraint to reject confidence > 1.0")

    conn.close()


def test_slugify_handles_edge_cases():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("") == "untitled"
    assert slugify("   ") == "untitled"
    assert slugify("a" * 100, max_len=20) == "a" * 20
    assert slugify("Multi---dashes  collapse") == "multi-dashes-collapse"


def test_capture_filename_format():
    name = capture_filename("01HXXXX", "Hello World")
    assert name == "01HXXXX-hello-world.md"


def test_write_capture_creates_file_with_frontmatter(tmp_path):
    """write_capture produces a markdown file with bitemporal frontmatter + body."""
    now = datetime.now(timezone.utc)
    capture_id = str(ULID())
    rel_path = write_capture(
        vault_root=tmp_path,
        capture_id=capture_id,
        source="x",
        url="https://x.com/example/status/123",
        title="Example tweet about Khiip",
        description=None,
        body="This is the captured body.",
        recorded_at=now,
        valid_from=now,
    )

    abs_path = tmp_path / rel_path
    assert abs_path.exists()
    content = abs_path.read_text()
    assert content.startswith("---\n")
    assert f'id: "{capture_id}"' in content
    assert "recorded_at:" in content
    assert "valid_from:" in content
    assert "This is the captured body." in content
    # File should be under captures/x/
    assert str(rel_path).startswith("captures/x/")
