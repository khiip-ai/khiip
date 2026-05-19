"""Pydantic models for the Khiip API surface.

These model the data flowing through `/api/v1/*` endpoints. Storage-layer
representations (rows in `captures`, `graph_edges`) are mapped to/from these
models in `khiip.storage`.

Authority for edge_type enum: ADR-0008 (Khiip-designed 5+1 canonical
vocabulary). Authority for evidence_span + confidence + vocab_match: ADR-0005
Option Δ.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

# ADR-0008 canonical edge vocabulary (5 typed + RELATES escape)
EdgeType = Literal[
    "SUPPORTS",
    "CONTRADICTS",
    "SUPERSEDES",
    "ELABORATES",
    "REFERENCES",
    "RELATES",
]

CANONICAL_EDGE_TYPES: tuple[str, ...] = (
    "SUPPORTS",
    "CONTRADICTS",
    "SUPERSEDES",
    "ELABORATES",
    "REFERENCES",
    "RELATES",
)


# Plain-English templates per ADR-0008 + ADR-0005 Option Δ Promise #3
EDGE_TEMPLATES: dict[str, str] = {
    "SUPPORTS":    "Khiip detected: {source} backs up {target}",
    "CONTRADICTS": "Khiip detected: {source} disagrees with {target}",
    "SUPERSEDES":  "Khiip detected: {source} replaces {target} (newer)",
    "ELABORATES":  "Khiip detected: {source} adds detail to {target}",
    "REFERENCES":  "Khiip detected: {source} mentions {target}",
    "RELATES":     "Khiip detected: {source} relates to {target}",  # extracted_text appended at render
}


# ───────────────────────────────────────────────────────────────────────────
# Capture
# ───────────────────────────────────────────────────────────────────────────


class CaptureCreate(BaseModel):
    """Request body for POST /api/v1/captures."""

    model_config = ConfigDict(extra="forbid")

    url: HttpUrl
    source_hint: str | None = Field(
        default=None,
        description="Optional source-type hint (x | web | pdf | youtube). Daemon will auto-detect if omitted.",
    )
    instruction: str | None = Field(
        default=None,
        description="Optional natural-language capture instruction (e.g. 'TLDR' / 'review later').",
    )


class Capture(BaseModel):
    """A captured artifact."""

    model_config = ConfigDict(extra="forbid")

    id: str  # ULID
    url: HttpUrl
    source: str
    vault_path: str
    title: str | None = None
    description: str | None = None
    author: str | None = None
    recorded_at: datetime
    valid_from: datetime
    archived: bool = False
    superseded_by: str | None = None


# ───────────────────────────────────────────────────────────────────────────
# Edge
# ───────────────────────────────────────────────────────────────────────────


class EdgeCreate(BaseModel):
    """Request body for POST /api/v1/edges."""

    model_config = ConfigDict(extra="forbid")

    source_capture_id: str
    target_capture_id: str | None = None
    edge_type: str  # canonical when vocab_match=True, freeform when False
    vocab_match: bool = True
    evidence_span: str = Field(..., min_length=1, description="REQUIRED per ADR-0005 Option Δ.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="REQUIRED per ADR-0005 Option Δ.")
    valid_from: datetime | None = None
    metadata: dict | None = None


class Edge(BaseModel):
    """A capture-to-capture typed edge."""

    model_config = ConfigDict(extra="forbid")

    id: int
    source_capture_id: str
    target_capture_id: str | None
    edge_type: str
    vocab_match: bool
    evidence_span: str
    confidence: float
    recorded_at: datetime
    valid_from: datetime
    valid_to: datetime | None
    overrides: int | None


# ───────────────────────────────────────────────────────────────────────────
# Recall
# ───────────────────────────────────────────────────────────────────────────


class RecallHit(BaseModel):
    """A single recall result: capture + cosine similarity score."""

    model_config = ConfigDict(extra="forbid")

    capture: Capture
    score: float = Field(..., ge=-1.0, le=1.0, description="Cosine similarity in [-1.0, 1.0].")


class RecallResponse(BaseModel):
    """Response body for GET /api/v1/recall."""

    model_config = ConfigDict(extra="forbid")

    query: str
    embedder_model: str
    embedder_dimension: int
    results: list[RecallHit]


# ───────────────────────────────────────────────────────────────────────────
# Health
# ───────────────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    schema_version: int
    db_path: str


__all__ = [
    "CANONICAL_EDGE_TYPES",
    "EDGE_TEMPLATES",
    "Capture",
    "CaptureCreate",
    "Edge",
    "EdgeCreate",
    "EdgeType",
    "HealthResponse",
    "RecallHit",
    "RecallResponse",
]
