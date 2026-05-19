"""Embedders: pluggable text → vector models for semantic recall.

Authority: v0 spec D4 (tiered fallback embedding model architecture).

v0 ships MiniLMEmbedder (ONNX bundled, ~80MB) as the default. Tests
inject StubEmbedder via `app.state.embedder` before lifespan runs.
"""

from khiip.embeddings.base import Embedder
from khiip.embeddings.minilm import MINILM_DIMENSION, MINILM_MODEL_NAME, MiniLMEmbedder

__all__ = ["MINILM_DIMENSION", "MINILM_MODEL_NAME", "Embedder", "MiniLMEmbedder"]
