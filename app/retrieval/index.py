"""
app/retrieval/index.py
──────────────────────
FAISS index wrapper for exact cosine-similarity vector retrieval (IndexFlatIP).
Manages index construction, persistence, validation, and Top-K search.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import faiss
import numpy as np

from app.config import EMBEDDING_DIM, FAISS_INDEX_PATH


class FAISSIndex:
    """
    Wrapper for FAISS IndexFlatIP (Inner Product).

    Since all catalogue embeddings and query embeddings are unit L2-normalized
    (||v||_2 = 1.0), the inner product (dot product) is mathematically equivalent
    to cosine similarity:
        dot_product(a, b) = ||a|| * ||b|| * cos(theta) = cos(theta)
    """

    def __init__(self, dimension: int = EMBEDDING_DIM):
        """
        Initialize an empty FAISS IndexFlatIP with the specified dimension.

        Args:
            dimension: Dimensionality of vector embeddings (e.g., 512 for CLIP ViT-B/32).
        """
        if dimension <= 0:
            raise ValueError(f"Dimension must be a positive integer, got {dimension}")

        self._dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)

    @property
    def dimension(self) -> int:
        """Embedding dimension expected by the index."""
        return self.index.d

    @property
    def size(self) -> int:
        """Total number of vectors stored in the index (ntotal)."""
        return self.index.ntotal

    def add(self, embeddings: np.ndarray) -> None:
        """
        Add a matrix of embeddings to the index.

        Args:
            embeddings: 2D numpy array of shape (N, dimension).

        Raises:
            ValueError: If embeddings are not 2D or dimension does not match.
        """
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.asarray(embeddings)

        if embeddings.ndim != 2:
            raise ValueError(
                f"Expected 2D array of embeddings (N, {self.dimension}), got shape {embeddings.shape}"
            )

        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, got {embeddings.shape[1]}"
            )

        if embeddings.shape[0] == 0:
            return

        # Ensure float32 dtype and C-contiguous memory layout
        float_embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)
        self.index.add(float_embeddings)

    @classmethod
    def from_embeddings(cls, embeddings: np.ndarray) -> "FAISSIndex":
        """
        Factory method to create and populate an index from an embedding matrix.

        Args:
            embeddings: 2D numpy array of shape (N, dimension).

        Returns:
            Populated FAISSIndex instance.
        """
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.asarray(embeddings)

        if embeddings.ndim != 2:
            raise ValueError(f"Expected 2D array of shape (N, D), got {embeddings.shape}")

        dim = embeddings.shape[1]
        instance = cls(dimension=dim)
        instance.add(embeddings)
        return instance

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Perform Top-K nearest neighbour search for one or more query vectors.

        Args:
            query_embedding: Query vector array of shape (D,), (1, D), or (M, D).
            top_k: Number of nearest neighbours to retrieve (must be 1 <= top_k <= index.size).

        Returns:
            Tuple of (scores, indices):
                - scores: np.ndarray of shape (M, top_k), cosine similarity scores in descending order.
                - indices: np.ndarray of shape (M, top_k), integer row indices in the index.

        Raises:
            ValueError: If query shape/dimension is invalid or top_k is out of valid bounds.
        """
        if self.size == 0:
            raise ValueError("Cannot search an empty FAISS index (size=0)")

        if top_k <= 0:
            raise ValueError(f"top_k must be a positive integer, got {top_k}")

        if top_k > self.size:
            raise ValueError(
                f"Requested top_k={top_k} exceeds index size ({self.size} vectors)"
            )

        if not isinstance(query_embedding, np.ndarray):
            query_embedding = np.asarray(query_embedding)

        # Handle 1D vector (D,) -> reshape to (1, D)
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        elif query_embedding.ndim != 2:
            raise ValueError(
                f"Expected query shape (D,), (1, D), or (M, D), got shape {query_embedding.shape}"
            )

        if query_embedding.shape[1] != self.dimension:
            raise ValueError(
                f"Query dimension mismatch: expected {self.dimension}, got {query_embedding.shape[1]}"
            )

        queries = np.ascontiguousarray(query_embedding, dtype=np.float32)
        scores, indices = self.index.search(queries, top_k)

        return scores.astype(np.float32), indices.astype(np.int64)

    def search_single(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> List[Dict[str, Union[int, float]]]:
        """
        Convenience method to search a single query vector and return list of result dicts.

        Args:
            query_embedding: Vector of shape (D,) or (1, D).
            top_k: Number of neighbours to retrieve.

        Returns:
            List of dicts: [{"index": int, "score": float}, ...]
        """
        scores, indices = self.search(query_embedding, top_k=top_k)
        results = []
        for idx, score in zip(indices[0], scores[0]):
            results.append({"index": int(idx), "score": float(score)})
        return results

    def save(self, path: Union[str, Path] = FAISS_INDEX_PATH) -> None:
        """
        Persist the FAISS index to disk.

        Args:
            path: Destination file path (e.g., artifacts/indexes/catalogue.faiss).
        """
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(save_path))

    @classmethod
    def load(cls, path: Union[str, Path] = FAISS_INDEX_PATH) -> "FAISSIndex":
        """
        Load a persisted FAISS index from disk without rebuilding.

        Args:
            path: Path to the .faiss file.

        Returns:
            Loaded FAISSIndex instance.
        """
        load_path = Path(path)
        if not load_path.exists():
            raise FileNotFoundError(f"FAISS index file not found: {load_path}")

        raw_index = faiss.read_index(str(load_path))
        instance = cls.__new__(cls)
        instance.index = raw_index
        instance._dimension = raw_index.d
        return instance


def get_product_ids(
    indices: Union[List[int], np.ndarray],
    product_ids: List[str],
) -> List[str]:
    """
    Helper function to map integer FAISS indices to product ID strings.

    Args:
        indices: 1D array or list of integer vector positions.
        product_ids: List of product ID strings (from product_ids.json).

    Returns:
        List of product ID strings corresponding to the given indices.
    """
    if isinstance(indices, np.ndarray):
        indices = indices.flatten().tolist()

    mapped_ids = []
    num_products = len(product_ids)

    for idx in indices:
        if 0 <= idx < num_products:
            mapped_ids.append(product_ids[idx])
        else:
            raise IndexError(
                f"FAISS index {idx} out of range for product_ids mapping of size {num_products}"
            )

    return mapped_ids
