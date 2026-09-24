"""
tests/test_matcher.py
─────────────────────
Unit and integration tests for Phase 4 Baseline Matcher Pipeline:
  - Matcher initialization and artifact loading
  - Full image retrieval pipeline execution
  - Top-5 schema, ranking, and descending score ordering
  - Metadata resolution from catalogue.csv
  - Decision logic (MATCH vs UNKNOWN based on threshold)
  - Self-retrieval sanity test on real catalogue image
  - Error handling for invalid/corrupt images and missing files
  - Dynamic top_k and threshold parameter overrides
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
import pytest

from app.config import (
    CATALOGUE_CSV,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.retrieval.matcher import JewelleryMatcher


@pytest.fixture(scope="module")
def shared_matcher():
    """Load production matcher once for read-only tests to keep test suite fast."""
    if not (FAISS_INDEX_PATH.exists() and PRODUCT_IDS_PATH.exists() and CATALOGUE_CSV.exists()):
        pytest.skip("Production artifacts not ready for matcher integration tests.")
    return JewelleryMatcher(
        index_path=FAISS_INDEX_PATH,
        product_ids_path=PRODUCT_IDS_PATH,
        catalogue_csv_path=CATALOGUE_CSV,
        threshold=SIMILARITY_THRESHOLD,
        top_k=TOP_K,
    )


class TestMatcherInitialization:
    """Tests for matcher initialization and dependency validation."""

    def test_matcher_init_success(self, shared_matcher):
        assert shared_matcher is not None
        assert shared_matcher.index.size >= 6157
        assert len(shared_matcher.product_ids) >= 6157
        assert len(shared_matcher.catalogue_lookup) >= 6157
        assert shared_matcher.default_threshold == SIMILARITY_THRESHOLD
        assert shared_matcher.default_top_k == TOP_K

    def test_missing_faiss_index(self):
        with pytest.raises(FileNotFoundError):
            JewelleryMatcher(index_path=Path("non_existent.faiss"))

    def test_missing_product_ids(self):
        with pytest.raises(FileNotFoundError):
            JewelleryMatcher(product_ids_path=Path("non_existent.json"))

    def test_missing_catalogue_csv(self):
        with pytest.raises(FileNotFoundError):
            JewelleryMatcher(catalogue_csv_path=Path("non_existent.csv"))


class TestMatcherPipeline:
    """Tests for end-to-end matching query execution."""

    def test_match_with_synthetic_pil_image(self, shared_matcher):
        img = Image.new("RGB", (224, 224), color=(210, 160, 40))
        result = shared_matcher.match(img)

        assert result["status"] == "success"
        assert result["decision"] in ["MATCH", "UNKNOWN"]
        assert isinstance(result["query_time_ms"], float)
        assert result["query_time_ms"] > 0
        assert result["top_k"] == 5
        assert len(result["results"]) == 5

        # Check candidate structure
        for rank, item in enumerate(result["results"], start=1):
            assert item["rank"] == rank
            assert item["product_id"].startswith("JW_")
            assert isinstance(item["product_name"], str)
            assert isinstance(item["category"], str)
            assert isinstance(item["similarity"], float)
            assert -1.0 <= item["similarity"] <= 1.0

    def test_results_descending_score_ordering(self, shared_matcher):
        img = Image.new("RGB", (224, 224), color=(180, 50, 100))
        result = shared_matcher.match(img, top_k=5)
        sims = [r["similarity"] for r in result["results"]]

        for i in range(len(sims) - 1):
            assert sims[i] >= sims[i + 1] - 1e-6, "Results must be sorted descending by similarity!"

    def test_metadata_resolution(self, shared_matcher):
        img = Image.new("RGB", (224, 224), color=(50, 150, 200))
        result = shared_matcher.match(img, top_k=3)

        for item in result["results"]:
            pid = item["product_id"]
            meta = shared_matcher.catalogue_lookup[pid]
            assert item["product_name"] == meta["product_name"]
            assert item["category"] == meta["category"]
            assert item["image_path"] == meta["image_path"]

    def test_decision_logic_match_vs_unknown(self, shared_matcher):
        img = Image.new("RGB", (224, 224), color=(200, 180, 50))

        # Force MATCH with very low threshold
        res_match = shared_matcher.match(img, threshold=-1.0)
        assert res_match["decision"] == "MATCH"
        assert res_match["threshold"] == -1.0

        # Force UNKNOWN with unattainable threshold
        res_unknown = shared_matcher.match(img, threshold=1.1)
        assert res_unknown["decision"] == "UNKNOWN"
        assert res_unknown["threshold"] == 1.1

    def test_top_k_override(self, shared_matcher):
        img = Image.new("RGB", (224, 224), color=(100, 100, 100))
        for k in [1, 3, 7]:
            res = shared_matcher.match(img, top_k=k)
            assert len(res["results"]) == k
            assert res["top_k"] == k

    def test_self_retrieval_catalogue_image(self, shared_matcher):
        """Querying a real catalogue image must retrieve itself as top-1 with similarity ≈ 1.0."""
        # Query the first catalogue product
        df = pd.read_csv(CATALOGUE_CSV)
        first_row = df.iloc[0]
        target_pid = first_row["product_id"]
        img_path = Path(first_row["image_path"])

        if not img_path.is_absolute():
            img_path = Path(__file__).resolve().parent.parent / img_path

        assert img_path.exists(), f"Sample image not found: {img_path}"

        result = shared_matcher.match(img_path, top_k=5, threshold=0.75)

        assert result["decision"] == "MATCH"
        top1 = result["results"][0]
        assert top1["product_id"] == target_pid
        assert pytest.approx(top1["similarity"], rel=1e-3) == 1.0


class TestMatcherErrorHandling:
    """Tests for input validation and error handling."""

    def test_non_existent_image_file(self, shared_matcher):
        with pytest.raises(FileNotFoundError):
            shared_matcher.match("non_existent_query_image_12345.jpg")

    def test_corrupt_or_invalid_image(self, shared_matcher):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"NOT_A_VALID_JPEG_HEADER_CORRUPT_DATA")
            tmp_path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                shared_matcher.match(tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_unsupported_input_type(self, shared_matcher):
        with pytest.raises(TypeError):
            shared_matcher.match(12345)
