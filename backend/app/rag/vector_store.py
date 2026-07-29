"""Vector index for retrieval. Uses FAISS if installed (real ANN index,
same as production); otherwise falls back to an exact numpy cosine-search
index with an identical interface, so the rest of the app doesn't care
which backend is active.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

try:
    import faiss  # type: ignore

    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


@dataclass
class ChunkRecord:
    document_id: int
    filename: str
    chunk_text: str


class VectorStore:
    """One instance per user, so retrieval never crosses account/RBAC
    boundaries -- a query only ever searches documents that user owns.
    """

    def __init__(self, dim: int):
        self.dim = dim
        self.records: list[ChunkRecord] = []
        if HAS_FAISS:
            self._index = faiss.IndexFlatIP(dim)
        else:
            self._matrix = np.zeros((0, dim), dtype=np.float32)

    def add(self, vectors: np.ndarray, records: list[ChunkRecord]) -> None:
        if vectors.shape[0] == 0:
            return
        self.records.extend(records)
        if HAS_FAISS:
            self._index.add(vectors)
        else:
            self._matrix = np.vstack([self._matrix, vectors])

    def search(self, query_vector: np.ndarray, k: int = 4) -> list[tuple[ChunkRecord, float]]:
        if not self.records:
            return []
        k = min(k, len(self.records))
        if HAS_FAISS:
            scores, idxs = self._index.search(query_vector.reshape(1, -1), k)
            pairs = list(zip(idxs[0], scores[0]))
        else:
            scores = self._matrix @ query_vector
            top_idx = np.argsort(-scores)[:k]
            pairs = [(int(i), float(scores[i])) for i in top_idx]

        return [(self.records[i], float(s)) for i, s in pairs if i >= 0]

    def remove_document(self, document_id: int) -> None:
        """Rebuild the index without the given document's chunks. Simple
        approach appropriate for demo scale; a production system would use
        FAISS's id-based removal or a soft-delete + periodic compaction.
        """
        keep = [(r, v) for r, v in zip(self.records, self._all_vectors()) if r.document_id != document_id]
        self.records = [r for r, _ in keep]
        vectors = np.array([v for _, v in keep], dtype=np.float32) if keep else np.zeros((0, self.dim), dtype=np.float32)
        if HAS_FAISS:
            self._index = faiss.IndexFlatIP(self.dim)
            if len(vectors):
                self._index.add(vectors)
        else:
            self._matrix = vectors

    def _all_vectors(self) -> np.ndarray:
        if HAS_FAISS:
            return self._index.reconstruct_n(0, self._index.ntotal)
        return self._matrix


# Per-user in-memory stores. Demo-scale: rebuilt from DB on process restart
# would be the production equivalent of a persisted FAISS index.
_stores: dict[int, VectorStore] = {}


def get_store_for_user(user_id: int, dim: int) -> VectorStore:
    if user_id not in _stores:
        _stores[user_id] = VectorStore(dim)
    return _stores[user_id]
