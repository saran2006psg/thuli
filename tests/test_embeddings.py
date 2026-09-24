"""
tests/test_embeddings.py
────────────────────────
Unit and integration tests for Phase 2:
  - JewelleryEncoder model inference & normalization
  - Catalogue embeddings matrix integrity (shape, norms, NaNs)
  - Product ID mapping alignment with data/catalogue.csv
"""

import json
import os
from pathlib import Path

# Prevent transformers from attempting to import TensorFlow
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
import pandas as pd
from PIL import Image
import pytest

from app.config import (
    CATALOGUE_CSV,
    EMBEDDINGS_PATH,
    EMBEDDING_DIM,
    ENCODER_MODEL,
    PRODUCT_IDS_PATH,
)
from app.retrieval.encoder import JewelleryEncoder


class TestJewelleryEncoder:
    """Tests for the JewelleryEncoder wrapper class."""

    @pytest.fixture(scope="class")
    def encoder(self):
        return JewelleryEncoder(model_name=ENCODER_MODEL, device="cpu")

    def test_encoder_initialization(self, encoder):
        assert encoder is not None
        assert encoder.embedding_dim == EMBEDDING_DIM

    def test_encode_single_image(self, encoder):
        img = Image.new("RGB", (224, 224), color=(200, 150, 50))
        vec = encoder.encode_image(img)

        assert isinstance(vec, np.ndarray)
        assert vec.shape == (EMBEDDING_DIM,)
        assert vec.dtype == np.float32
        assert not np.isnan(vec).any()
        assert not np.isinf(vec).any()

        # Check L2 normalization
        norm = np.linalg.norm(vec)
        assert pytest.approx(norm, rel=1e-3) == 1.0

    def test_encode_batch(self, encoder):
        imgs = [
            Image.new("RGB", (200, 200), color=(255, 0, 0)),
            Image.new("RGB", (150, 150), color=(0, 255, 0)),
            Image.new("RGB", (100, 100), color=(0, 0, 255)),
        ]
        mat = encoder.encode_batch(imgs)

        assert isinstance(mat, np.ndarray)
        assert mat.shape == (3, EMBEDDING_DIM)
        assert mat.dtype == np.float32
        assert not np.isnan(mat).any()

        norms = np.linalg.norm(mat, axis=1)
        for norm in norms:
            assert pytest.approx(norm, rel=1e-3) == 1.0


class TestCatalogueEmbeddingsArtifacts:
    """Tests verifying generated embedding artifacts on disk."""

    def test_embeddings_file_exists(self):
        assert EMBEDDINGS_PATH.exists(), f"Missing embeddings file: {EMBEDDINGS_PATH}"

    def test_product_ids_file_exists(self):
        assert PRODUCT_IDS_PATH.exists(), f"Missing product IDs file: {PRODUCT_IDS_PATH}"

    def test_embeddings_properties(self):
        embs = np.load(EMBEDDINGS_PATH)
        assert isinstance(embs, np.ndarray)
        assert embs.ndim == 2
        assert embs.shape[1] == EMBEDDING_DIM
        assert embs.dtype == np.float32
        assert not np.isnan(embs).any(), "Embeddings contain NaN values!"
        assert not np.isinf(embs).any(), "Embeddings contain Inf values!"

    def test_l2_normalization_all_rows(self):
        embs = np.load(EMBEDDINGS_PATH)
        norms = np.linalg.norm(embs, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-3), "Not all embeddings are unit-normalized!"

    def test_product_ids_alignment(self):
        embs = np.load(EMBEDDINGS_PATH)
        with open(PRODUCT_IDS_PATH, "r", encoding="utf-8") as f:
            ids = json.load(f)

        assert len(ids) == len(embs), "Length mismatch between product_ids and embeddings matrix!"
        assert len(ids) == len(set(ids)), "Duplicate product_ids in mapping!"

        if CATALOGUE_CSV.exists():
            df = pd.read_csv(CATALOGUE_CSV)
            assert len(ids) == len(df), f"Embeddings count ({len(ids)}) != catalogue rows ({len(df)})"
            assert ids == df["product_id"].tolist(), "Product IDs order does not match catalogue.csv!"
