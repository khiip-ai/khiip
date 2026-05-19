"""MiniLM-L6-v2 ONNX embedder via fastembed.

v0 spec D4 tier 1: bundled small model, semantic recall works out-of-box
without user config. ~80MB ONNX, 384-dim, ~30-50 ms/doc on CPU.

fastembed handles tokenizer + ONNX runtime; we wrap it behind the
`Embedder` Protocol so v0.5 can swap in Ollama / BYOK without touching
the daemon or storage layer.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("khiip.embeddings")

MINILM_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_DIMENSION = 384


class MiniLMEmbedder:
    """fastembed-backed MiniLM-L6-v2. Lazy-loads on first warmup() / embed()."""

    model_name: str = MINILM_MODEL_NAME
    dimension: int = MINILM_DIMENSION

    def __init__(self) -> None:
        self._model: Any | None = None

    def warmup(self) -> None:
        if self._model is not None:
            return
        # Import lazily — keeps test startup fast when StubEmbedder is injected,
        # and avoids paying the ONNX import cost in CLI subcommands that don't embed.
        from fastembed import TextEmbedding

        logger.info("loading fastembed model: %s", self.model_name)
        self._model = TextEmbedding(model_name=self.model_name)
        # Force one inference to materialize the ONNX session — moves the
        # cold-start cost off the first user request.
        list(self._model.embed(["warmup"]))
        logger.info("fastembed model ready (%s, dim=%d)", self.model_name, self.dimension)

    def embed(self, text: str) -> list[float]:
        if self._model is None:
            self.warmup()
        assert self._model is not None
        vecs = list(self._model.embed([text]))
        return vecs[0].tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is None:
            self.warmup()
        assert self._model is not None
        return [v.tolist() for v in self._model.embed(texts)]


__all__ = ["MINILM_DIMENSION", "MINILM_MODEL_NAME", "MiniLMEmbedder"]
