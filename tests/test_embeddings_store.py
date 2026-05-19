"""Unit tests for storage/embeddings_store.py — BLOB round-trip + cosine_topk."""

from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from khiip.storage import db as storage_db
from khiip.storage import embeddings_store
from khiip.storage.embeddings_store import EmbeddingRecord


@pytest.fixture
def conn(tmp_path):
    """A fresh SQLite DB with schema applied + one parent capture row for FK."""
    db = storage_db.connect(tmp_path / "index.db")
    storage_db.init_schema(db)
    # Insert one capture row so the FK from embeddings.capture_id resolves
    db.execute(
        """
        INSERT INTO captures
            (id, url, url_hash, source, vault_path, recorded_at, valid_from)
        VALUES ('cap1', 'https://example.test/1', 'h1', 'web',
                'captures/web/cap1.md', '2026-05-19T00:00:00+00:00',
                '2026-05-19T00:00:00+00:00')
        """
    )
    db.execute(
        """
        INSERT INTO captures
            (id, url, url_hash, source, vault_path, recorded_at, valid_from)
        VALUES ('cap2', 'https://example.test/2', 'h2', 'web',
                'captures/web/cap2.md', '2026-05-19T00:00:00+00:00',
                '2026-05-19T00:00:00+00:00')
        """
    )
    db.execute(
        """
        INSERT INTO captures
            (id, url, url_hash, source, vault_path, recorded_at, valid_from)
        VALUES ('cap3', 'https://example.test/3', 'h3', 'web',
                'captures/web/cap3.md', '2026-05-19T00:00:00+00:00',
                '2026-05-19T00:00:00+00:00')
        """
    )
    yield db
    db.close()


def test_insert_then_find_round_trips_vector(conn: sqlite3.Connection):
    vector = [0.1, 0.2, -0.3, 0.4]
    embeddings_store.insert_embedding(
        conn,
        capture_id="cap1",
        model="test-model",
        dimension=4,
        vector=vector,
        content_sha256="abc",
    )
    row = embeddings_store.find_embedding_by_capture_id(conn, "cap1")
    assert row is not None
    assert row["capture_id"] == "cap1"
    assert row["model"] == "test-model"
    assert row["dimension"] == 4
    np.testing.assert_allclose(row["vector"], vector, atol=1e-6)


def test_insert_dimension_mismatch_raises(conn: sqlite3.Connection):
    with pytest.raises(ValueError, match="dimension"):
        embeddings_store.insert_embedding(
            conn,
            capture_id="cap1",
            model="test-model",
            dimension=4,
            vector=[0.1, 0.2],  # length 2 != dimension 4
            content_sha256="abc",
        )


def test_insert_or_replace_updates_existing_row(conn: sqlite3.Connection):
    embeddings_store.insert_embedding(
        conn, capture_id="cap1", model="m", dimension=2, vector=[1.0, 0.0], content_sha256="a"
    )
    embeddings_store.insert_embedding(
        conn, capture_id="cap1", model="m", dimension=2, vector=[0.0, 1.0], content_sha256="b"
    )
    row = embeddings_store.find_embedding_by_capture_id(conn, "cap1")
    assert row is not None
    np.testing.assert_allclose(row["vector"], [0.0, 1.0], atol=1e-6)
    assert row["content_sha256"] == "b"


def test_find_returns_none_for_missing_capture(conn: sqlite3.Connection):
    assert embeddings_store.find_embedding_by_capture_id(conn, "nope") is None


def test_load_all_vectors_filters_by_model(conn: sqlite3.Connection):
    embeddings_store.insert_embedding(
        conn, capture_id="cap1", model="m1", dimension=2, vector=[1.0, 0.0], content_sha256="a"
    )
    embeddings_store.insert_embedding(
        conn, capture_id="cap2", model="m2", dimension=2, vector=[0.0, 1.0], content_sha256="b"
    )
    only_m1 = embeddings_store.load_all_vectors(conn, model="m1")
    assert len(only_m1) == 1
    assert only_m1[0].capture_id == "cap1"

    only_m2 = embeddings_store.load_all_vectors(conn, model="m2")
    assert len(only_m2) == 1
    assert only_m2[0].capture_id == "cap2"


def test_cosine_topk_ranks_by_similarity():
    records = [
        EmbeddingRecord(capture_id="a", vector=np.asarray([1.0, 0.0, 0.0], dtype=np.float32)),
        EmbeddingRecord(capture_id="b", vector=np.asarray([0.0, 1.0, 0.0], dtype=np.float32)),
        EmbeddingRecord(capture_id="c", vector=np.asarray([0.5, 0.5, 0.0], dtype=np.float32)),
    ]
    # Query parallel to record `a` — a > c > b
    results = embeddings_store.cosine_topk([1.0, 0.0, 0.0], records, limit=3)
    assert [cap_id for cap_id, _ in results] == ["a", "c", "b"]
    assert results[0][1] == pytest.approx(1.0)
    assert results[1][1] > results[2][1]


def test_cosine_topk_limits_results():
    records = [
        EmbeddingRecord(capture_id=str(i), vector=np.asarray([float(i), 0.0], dtype=np.float32))
        for i in range(1, 6)
    ]
    results = embeddings_store.cosine_topk([1.0, 0.0], records, limit=2)
    assert len(results) == 2


def test_cosine_topk_empty_inputs():
    assert embeddings_store.cosine_topk([1.0, 0.0], [], limit=5) == []
    records = [EmbeddingRecord(capture_id="a", vector=np.asarray([1.0, 0.0], dtype=np.float32))]
    assert embeddings_store.cosine_topk([1.0, 0.0], records, limit=0) == []


def test_cosine_topk_zero_query_returns_empty():
    records = [EmbeddingRecord(capture_id="a", vector=np.asarray([1.0, 0.0], dtype=np.float32))]
    assert embeddings_store.cosine_topk([0.0, 0.0], records, limit=5) == []


def test_cosine_topk_skips_degenerate_record_vectors():
    records = [
        EmbeddingRecord(capture_id="zero", vector=np.asarray([0.0, 0.0], dtype=np.float32)),
        EmbeddingRecord(capture_id="ok", vector=np.asarray([1.0, 0.0], dtype=np.float32)),
    ]
    results = embeddings_store.cosine_topk([1.0, 0.0], records, limit=5)
    # Only the non-zero vector should make it into results
    assert [cap_id for cap_id, _ in results] == ["ok"]


def test_load_all_vectors_cascade_deleted_on_capture_delete(conn: sqlite3.Connection):
    """Schema declares ON DELETE CASCADE on embeddings.capture_id — verify it fires."""
    embeddings_store.insert_embedding(
        conn, capture_id="cap1", model="m", dimension=2, vector=[1.0, 0.0], content_sha256="a"
    )
    assert embeddings_store.find_embedding_by_capture_id(conn, "cap1") is not None

    conn.execute("DELETE FROM captures WHERE id = 'cap1'")
    assert embeddings_store.find_embedding_by_capture_id(conn, "cap1") is None
