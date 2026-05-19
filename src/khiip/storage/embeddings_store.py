"""Embeddings storage — float32 BLOB packing + numpy cosine top-k search.

Schema authority: schema.sql `embeddings` table.

Vectors stored as raw little-endian float32 BLOB (matches schema comment).
v0 holds all vectors in memory at recall time and computes cosine with
numpy; ADR-0007 Probe 3 sized SQLite at 50K rows fine. When the corpus
crosses ~100K captures, swap to sqlite-vec or an external ANN index —
the Embedder + storage Protocol surface stays unchanged (P1 reversibility).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import numpy as np


def _vector_to_bytes(vector: list[float]) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def _bytes_to_vector(blob: bytes) -> np.ndarray:
    # `frombuffer` returns a read-only view of the SQLite-managed bytes;
    # copy so callers can normalize/mutate without surprises.
    return np.frombuffer(blob, dtype=np.float32).copy()


@dataclass
class EmbeddingRecord:
    """In-memory representation used by cosine_topk."""

    capture_id: str
    vector: np.ndarray


def insert_embedding(
    conn: sqlite3.Connection,
    *,
    capture_id: str,
    model: str,
    dimension: int,
    vector: list[float],
    content_sha256: str,
) -> None:
    """Insert (or replace) the embedding row for a capture."""
    if len(vector) != dimension:
        raise ValueError(
            f"vector length {len(vector)} does not match declared dimension {dimension}"
        )
    conn.execute(
        """
        INSERT OR REPLACE INTO embeddings
            (capture_id, model, dimension, vector, content_sha256)
        VALUES (?, ?, ?, ?, ?)
        """,
        (capture_id, model, dimension, _vector_to_bytes(vector), content_sha256),
    )


def find_embedding_by_capture_id(
    conn: sqlite3.Connection, capture_id: str
) -> dict | None:
    """Return the embedding row for a capture (vector as np.ndarray), or None."""
    row = conn.execute(
        "SELECT capture_id, model, dimension, vector, content_sha256 "
        "FROM embeddings WHERE capture_id = ?",
        (capture_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "capture_id": row["capture_id"],
        "model": row["model"],
        "dimension": int(row["dimension"]),
        "vector": _bytes_to_vector(row["vector"]),
        "content_sha256": row["content_sha256"],
    }


def load_all_vectors(conn: sqlite3.Connection, *, model: str) -> list[EmbeddingRecord]:
    """Load all embeddings for a given model into memory for cosine search."""
    rows = conn.execute(
        "SELECT capture_id, vector FROM embeddings WHERE model = ?",
        (model,),
    ).fetchall()
    return [
        EmbeddingRecord(
            capture_id=row["capture_id"],
            vector=_bytes_to_vector(row["vector"]),
        )
        for row in rows
    ]


def cosine_topk(
    query: list[float],
    records: list[EmbeddingRecord],
    *,
    limit: int,
) -> list[tuple[str, float]]:
    """Return [(capture_id, cosine_score), ...] sorted by score DESC, capped at limit.

    Both query and stored vectors are normalized inside this function — callers
    don't need to pre-normalize. Degenerate (all-zero) vectors are filtered out
    silently rather than producing NaN scores.
    """
    if not records or limit <= 0:
        return []

    q = np.asarray(query, dtype=np.float32)
    q_norm = float(np.linalg.norm(q))
    if q_norm == 0.0:
        return []
    q = q / q_norm

    matrix = np.stack([r.vector for r in records]).astype(np.float32, copy=False)
    norms = np.linalg.norm(matrix, axis=1)
    valid = norms > 0.0
    if not bool(valid.any()):
        return []

    safe_norms = np.where(norms == 0.0, 1.0, norms)
    matrix = matrix / safe_norms[:, None]
    scores = matrix @ q
    # float32 dot products can drift ±1e-7 outside [-1, 1] for near-identical vectors;
    # clamp so callers (e.g. Pydantic-bounded RecallHit.score) see a strict cosine range.
    scores = np.clip(scores, -1.0, 1.0)
    scores = np.where(valid, scores, -np.inf)

    n_valid = int(valid.sum())
    k = min(limit, n_valid)
    if k <= 0:
        return []

    if k < len(records):
        top_idx = np.argpartition(-scores, k - 1)[:k]
    else:
        top_idx = np.arange(len(records))
    top_idx = top_idx[np.argsort(-scores[top_idx])]
    return [(records[i].capture_id, float(scores[i])) for i in top_idx]


__all__ = [
    "EmbeddingRecord",
    "cosine_topk",
    "find_embedding_by_capture_id",
    "insert_embedding",
    "load_all_vectors",
]
