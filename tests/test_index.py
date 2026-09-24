"""
tests/test_index.py
───────────────────
Unit and integration tests for Phase 3:
  - FAISSIndex initialization, adding, and size tracking
  - Search output shapes, score ordering, and bounds
  - Self-retrieval exact match (score ≈ 1.0)
  - Index persistence (save and load consistency)
  - Dimension and Top-K boundary validation
  - Product ID mapping helper
  - Integration check with artifacts/indexes/catalogue.faiss
"""

import json
from pathlib import Path
import tempfile

import numpy as np
import pytest

from app.config import (
    EMBEDDINGS_PATH,
    EMBEDDING_DIM,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
)
from app.retrieval.index import FAISSIndex, get_product_ids


def generate_normalized_vectors(n: int, dim: int = 512, seed: int = 42) -> np.ndarray:
    """Helper to generate synthetic L2-normalized float32 vectors."""
    rng = np.random.RandomState(seed)
    vecs = rng.randn(n, dim).astype(np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-12, None)


class TestFAISSIndexUnit:
    """Unit tests using synthetic normalized embeddings (fast & isolated)."""

    def test_index_initialization(self):
        index = FAISSIndex(dimension=512)
        assert index.dimension == 512
        assert index.size == 0

    def test_invalid_dimension_init(self):
        with pytest.raises(ValueError):
            FAISSIndex(dimension=0)
        with pytest.raises(ValueError):
            FAISSIndex(dimension=-5)

    def test_add_embeddings(self):
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(20, dim=512)
        index.add(vecs)
        assert index.size == 20

    def test_from_embeddings_factory(self):
        vecs = generate_normalized_vectors(15, dim=512)
        index = FAISSIndex.from_embeddings(vecs)
        assert index.size == 15
        assert index.dimension == 512

    def test_search_output_shapes_and_types(self):
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(30, dim=512)
        index.add(vecs)

        # Single query (1, 512)
        query_1 = vecs[0:1]
        scores, indices = index.search(query_1, top_k=5)
        assert scores.shape == (1, 5)
        assert indices.shape == (1, 5)
        assert scores.dtype == np.float32
        assert indices.dtype == np.int64

        # 1D vector (512,)
        query_1d = vecs[0]
        scores_1d, indices_1d = index.search(query_1d, top_k=5)
        assert scores_1d.shape == (1, 5)
        assert indices_1d.shape == (1, 5)

        # Batch query (3, 512)
        query_batch = vecs[0:3]
        scores_b, indices_b = index.search(query_batch, top_k=5)
        assert scores_b.shape == (3, 5)
        assert indices_b.shape == (3, 5)

    def test_search_single_helper(self):
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(20, dim=512)
        index.add(vecs)

        results = index.search_single(vecs[0], top_k=3)
        assert len(results) == 3
        assert isinstance(results[0], dict)
        assert "index" in results[0] and "score" in results[0]
        assert results[0]["index"] == 0
        assert pytest.approx(results[0]["score"], rel=1e-4) == 1.0

    def test_self_retrieval(self):
        """Querying with an exact catalogue vector must return that vector as Top-1 with score ≈ 1.0."""
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(25, dim=512)
        index.add(vecs)

        for target_idx in [0, 7, 14, 24]:
            q = vecs[target_idx : target_idx + 1]
            scores, indices = index.search(q, top_k=5)
            assert indices[0][0] == target_idx, f"Expected top-1 index {target_idx}, got {indices[0][0]}"
            assert np.isclose(scores[0][0], 1.0, atol=1e-4), f"Expected score ≈ 1.0, got {scores[0][0]}"

    def test_score_ordering(self):
        """Scores returned by FAISS must be in descending order."""
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(50, dim=512)
        index.add(vecs)

        query = generate_normalized_vectors(1, dim=512, seed=99)
        scores, _ = index.search(query, top_k=10)

        for i in range(len(scores[0]) - 1):
            assert scores[0][i] >= scores[0][i + 1] - 1e-6, "Scores are not descending!"

    def test_score_bounds(self):
        """Cosine similarity scores for normalized vectors must lie within [-1.0, 1.0]."""
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(30, dim=512)
        index.add(vecs)

        query = generate_normalized_vectors(5, dim=512, seed=123)
        scores, _ = index.search(query, top_k=5)

        assert (scores >= -1.0001).all() and (scores <= 1.0001).all(), "Scores out of cosine bounds [-1, 1]!"

    def test_top_k_variations(self):
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(20, dim=512)
        index.add(vecs)

        for k in [1, 3, 10, 20]:
            scores, indices = index.search(vecs[0:1], top_k=k)
            assert scores.shape == (1, k)
            assert indices.shape == (1, k)

    def test_save_and_load_persistence(self):
        """Index saved to disk and reloaded must produce identical size and search results."""
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(40, dim=512)
        index.add(vecs)

        query = vecs[5:6]
        orig_scores, orig_indices = index.search(query, top_k=5)

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "test.faiss"
            index.save(save_path)
            assert save_path.exists()

            loaded_index = FAISSIndex.load(save_path)
            assert loaded_index.size == index.size
            assert loaded_index.dimension == index.dimension

            loaded_scores, loaded_indices = loaded_index.search(query, top_k=5)
            np.testing.assert_array_equal(orig_indices, loaded_indices)
            np.testing.assert_allclose(orig_scores, loaded_scores, atol=1e-6)

    def test_invalid_embedding_dimension(self):
        index = FAISSIndex(dimension=512)
        wrong_dim_vecs = np.random.randn(5, 768).astype(np.float32)
        with pytest.raises(ValueError):
            index.add(wrong_dim_vecs)

    def test_invalid_query_dimension(self):
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(10, dim=512)
        index.add(vecs)

        wrong_query = np.random.randn(1, 768).astype(np.float32)
        with pytest.raises(ValueError):
            index.search(wrong_query, top_k=5)

    def test_invalid_top_k(self):
        index = FAISSIndex(dimension=512)
        vecs = generate_normalized_vectors(10, dim=512)
        index.add(vecs)

        with pytest.raises(ValueError):
            index.search(vecs[0:1], top_k=0)
        with pytest.raises(ValueError):
            index.search(vecs[0:1], top_k=-1)
        with pytest.raises(ValueError):
            index.search(vecs[0:1], top_k=11)  # exceeds index size

    def test_search_empty_index(self):
        index = FAISSIndex(dimension=512)
        query = generate_normalized_vectors(1, dim=512)
        with pytest.raises(ValueError):
            index.search(query, top_k=5)


class TestProductIDMapping:
    """Tests for the get_product_ids helper function."""

    def test_product_id_mapping_success(self):
        product_ids = ["JW_000001", "JW_000002", "JW_000003", "JW_000004"]
        indices = np.array([[0, 2], [1, 3]])
        mapped = get_product_ids(indices, product_ids)
        assert mapped == ["JW_000001", "JW_000003", "JW_000002", "JW_000004"]

    def test_product_id_mapping_out_of_bounds(self):
        product_ids = ["JW_000001", "JW_000002"]
        with pytest.raises(IndexError):
            get_product_ids([5], product_ids)


class TestProductionCatalogueIndexArtifact:
    """Integration checks on artifacts/indexes/catalogue.faiss if built."""

    @pytest.mark.skipif(not FAISS_INDEX_PATH.exists(), reason="Catalogue FAISS index not yet built")
    def test_catalogue_index_properties(self):
        index = FAISSIndex.load(FAISS_INDEX_PATH)
        assert index.dimension == EMBEDDING_DIM
        assert index.size == 6157

        if EMBEDDINGS_PATH.exists() and PRODUCT_IDS_PATH.exists():
            embeddings = np.load(EMBEDDINGS_PATH)
            with open(PRODUCT_IDS_PATH, "r", encoding="utf-8") as f:
                product_ids = json.load(f)

            assert len(product_ids) == index.size

            # Test self-retrieval for sample catalogue items
            sample_query = embeddings[0:1]
            scores, indices = index.search(sample_query, top_k=5)
            assert indices[0][0] == 0
            assert np.isclose(scores[0][0], 1.0, atol=1e-4)
            assert product_ids[indices[0][0]] == "JW_000001"
