"""Pluggable embedding backend. Defaults to a deterministic hashed
bag-of-words embedder (offline, no download) so the portal runs
out of the box. Set EMBEDDING_PROVIDER=huggingface to route through a real
sentence-transformers model if you have it installed / want the download.
"""
from __future__ import annotations

import os
import re

import numpy as np

EMBED_DIM = 256


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


class HashingEmbedder:
    """Feature-hashed bag-of-words -> fixed-size vector. No vocabulary to
    fit, no network call, dimension-stable across documents.
    """

    dim = EMBED_DIM

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for tok in _tokenize(text):
                idx = hash(tok) % self.dim
                vectors[i, idx] += 1.0
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


class HuggingFaceEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # optional dependency

        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def get_embedder():
    if os.getenv("EMBEDDING_PROVIDER", "hashing") == "huggingface":
        return HuggingFaceEmbedder()
    return HashingEmbedder()
