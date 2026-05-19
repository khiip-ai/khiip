"""Embedder Protocol: pluggable text → vector for semantic recall.

Per v0 spec D4 (tiered fallback) + ADR-0007 P1 (reversibility):
- v0 default: MiniLMEmbedder (ONNX bundled, ~80MB, 384-dim)
- v0.5 planned: OllamaEmbedder (best quality if user has Ollama)
- v0.5 planned: ByokEmbedder (OpenAI / Anthropic / Gemini)
- Fallback: BM25 keyword (no embedder; daemon flags `embeddings_disabled`)

Production code resolves the concrete impl via `_build_default_embedder()`
in daemon.py. Tests inject a `StubEmbedder` before lifespan runs.

Embed vectors flow as `list[float]` across the Protocol boundary (pure
Python; no numpy in the contract). Storage + cosine search convert to
numpy internally.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Per-text embedding model. Vectors are returned as plain Python floats."""

    #: Identifier persisted to `embeddings.model` column; gates load_all_vectors()
    #: filtering. Switching embedder requires backfill/migration.
    model_name: str

    #: Vector length; must match `embeddings.dimension` for stored rows.
    dimension: int

    def warmup(self) -> None:
        """Load model into memory if not already loaded. Idempotent.

        Called once at daemon startup in lifespan. May download model
        weights on first call (~80MB for MiniLM). Tests typically stub
        this to no-op.
        """
        ...

    def embed(self, text: str) -> list[float]:
        """Embed a single text. Length == self.dimension."""
        ...

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in one call (often faster due to batching)."""
        ...


__all__ = ["Embedder"]
