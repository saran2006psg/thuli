"""
tests/test_multi_matcher.py
────────────────────────────
Unit and API tests for the multi-item jewellery grid-crop search.

Covers:
  - generate_grid_crops geometry (2×2, 3×3, overlap, bounds clamping)
  - MultiItemMatcher with 2-item image (two distinct products matched)
  - MultiItemMatcher with 3-item image (three products)
  - Duplicate matches across overlapping crops (keep highest similarity)
  - UNKNOWN crop (ignored in matches list)
  - No valid matches at all (empty matches list)
  - Single-item image (matched as a normal single product)
  - Exact product_id matching / deduplication key
  - POST /api/match/multi endpoint (200 response, schema, empty image guard)
  - Invalid params (overlap out of range, rows/cols out of range)
"""

import io
import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.retrieval.multi_matcher import MultiItemMatcher, generate_grid_crops

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rgb_image(w: int = 400, h: int = 300, color=(180, 120, 60)) -> Image.Image:
    return Image.new("RGB", (w, h), color=color)


def _make_candidate(product_id: str, category: str, similarity: float, rank: int = 1) -> Dict:
    return {
        "rank": rank,
        "product_id": product_id,
        "product_name": f"Test {category}",
        "category": category,
        "subcategory": category,
        "image_path": f"data/catalogue/jewelry_dataset/{category}/{product_id.lower()}.jpg",
        "similarity": similarity,
    }


def _make_match_result(product_id: str, category: str, similarity: float) -> Dict[str, Any]:
    """Simulate matcher.match() returning a MATCH for a given product."""
    return {
        "status": "success",
        "decision": "MATCH" if similarity >= 0.75 else "UNKNOWN",
        "threshold": 0.75,
        "best_similarity": similarity,
        "query_time_ms": 55.0,
        "top_k": 5,
        "results": [
            _make_candidate(product_id, category, similarity, rank=1),
            _make_candidate("JW_000099", "earring", 0.65, rank=2),
            _make_candidate("JW_000098", "necklace", 0.60, rank=3),
        ],
    }


def _make_unknown_result() -> Dict[str, Any]:
    """Simulate matcher.match() returning UNKNOWN."""
    return {
        "status": "success",
        "decision": "UNKNOWN",
        "threshold": 0.75,
        "best_similarity": 0.52,
        "query_time_ms": 48.0,
        "top_k": 5,
        "results": [_make_candidate("JW_000001", "ring", 0.52, rank=1)],
    }


def _mock_matcher(side_effects: List[Dict]) -> MagicMock:
    """Build a mock JewelleryMatcher whose .match() returns items from side_effects in order."""
    m = MagicMock()
    m.match.side_effect = side_effects
    m.catalogue_lookup = {
        "JW_000001": {"category": "ring", "image_path": "data/catalogue/jewelry_dataset/ring/jw_000001.jpg"},
        "JW_000002": {"category": "bracelet", "image_path": "data/catalogue/jewelry_dataset/bracelet/jw_000002.jpg"},
        "JW_000003": {"category": "necklace", "image_path": "data/catalogue/jewelry_dataset/necklace/jw_000003.jpg"},
    }
    return m


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: generate_grid_crops
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateGridCrops:

    def test_2x2_produces_four_crops(self):
        img = _rgb_image(400, 300)
        crops = generate_grid_crops(img, rows=2, cols=2, overlap=0.0)
        assert len(crops) == 4

    def test_3x3_produces_nine_crops(self):
        img = _rgb_image(600, 600)
        crops = generate_grid_crops(img, rows=3, cols=3, overlap=0.0)
        assert len(crops) == 9

    def test_crop_ids_unique(self):
        img = _rgb_image(400, 300)
        crops = generate_grid_crops(img, rows=2, cols=2)
        ids = [c["crop_id"] for c in crops]
        assert len(set(ids)) == 4
        assert "r0c0" in ids
        assert "r1c1" in ids

    def test_no_overlap_covers_full_image(self):
        """With no overlap, every pixel of a 400×300 image is covered at least once."""
        img = _rgb_image(400, 300)
        crops = generate_grid_crops(img, rows=2, cols=2, overlap=0.0)
        # Check that x1-x0 boundaries together cover full width in each row
        row0_cols = [c for c in crops if c["row"] == 0]
        total_x_span = max(c["region"][2] for c in row0_cols) - min(c["region"][0] for c in row0_cols)
        assert total_x_span == 400

    def test_overlap_expands_crops(self):
        """With 20% overlap each crop should be wider than without overlap."""
        img = _rgb_image(400, 300)
        crops_no = generate_grid_crops(img, rows=2, cols=2, overlap=0.0)
        crops_ov = generate_grid_crops(img, rows=2, cols=2, overlap=0.20)
        # r0c0 crop width with overlap should be > without overlap
        w_no = crops_no[0]["region"][2] - crops_no[0]["region"][0]
        w_ov = crops_ov[0]["region"][2] - crops_ov[0]["region"][0]
        assert w_ov > w_no

    def test_regions_clamped_to_image_bounds(self):
        img = _rgb_image(100, 100)
        crops = generate_grid_crops(img, rows=2, cols=2, overlap=0.40)
        for c in crops:
            x0, y0, x1, y1 = c["region"]
            assert x0 >= 0
            assert y0 >= 0
            assert x1 <= 100
            assert y1 <= 100

    def test_each_crop_is_pil_image(self):
        img = _rgb_image(200, 200)
        crops = generate_grid_crops(img, rows=2, cols=2)
        for c in crops:
            assert isinstance(c["crop"], Image.Image)
            assert c["crop"].mode == "RGB"

    def test_invalid_overlap_raises(self):
        img = _rgb_image(200, 200)
        with pytest.raises(ValueError, match="overlap"):
            generate_grid_crops(img, rows=2, cols=2, overlap=0.5)
        with pytest.raises(ValueError, match="overlap"):
            generate_grid_crops(img, rows=2, cols=2, overlap=-0.1)

    def test_invalid_rows_cols_raises(self):
        img = _rgb_image(200, 200)
        with pytest.raises(ValueError):
            generate_grid_crops(img, rows=0, cols=2)
        with pytest.raises(ValueError):
            generate_grid_crops(img, rows=2, cols=0)

    def test_1x1_grid_returns_whole_image(self):
        """A 1×1 grid with no overlap should return crop == original dimensions."""
        img = _rgb_image(300, 200)
        crops = generate_grid_crops(img, rows=1, cols=1, overlap=0.0)
        assert len(crops) == 1
        x0, y0, x1, y1 = crops[0]["region"]
        assert x0 == 0 and y0 == 0 and x1 == 300 and y1 == 200


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: MultiItemMatcher
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiItemMatcher:

    def test_two_item_image_returns_two_unique_matches(self):
        """2×2 grid: crop r0c0 → JW_000001, r1c0 → JW_000002, others UNKNOWN."""
        side_effects = [
            _make_match_result("JW_000001", "ring", 0.89),      # r0c0
            _make_unknown_result(),                               # r0c1
            _make_match_result("JW_000002", "bracelet", 0.86),  # r1c0
            _make_unknown_result(),                               # r1c1
        ]
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, overlap=0.0, strategy="grid")
        result = multi.match_multi(_rgb_image(400, 300))

        assert result["status"] == "success"
        assert result["mode"] == "multi"
        assert result["total_crops"] == 4
        assert result["matched_count"] == 2

        pids = [m["product_id"] for m in result["matches"]]
        assert "JW_000001" in pids
        assert "JW_000002" in pids
        # Sorted descending by similarity
        assert result["matches"][0]["similarity"] >= result["matches"][1]["similarity"]

    def test_three_item_image_returns_three_unique_matches(self):
        """2×2 grid: three distinct products, one crop UNKNOWN."""
        side_effects = [
            _make_match_result("JW_000001", "ring", 0.89),
            _make_match_result("JW_000002", "bracelet", 0.82),
            _make_match_result("JW_000003", "necklace", 0.78),
            _make_unknown_result(),
        ]
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(600, 400))

        assert result["matched_count"] == 3
        pids = {m["product_id"] for m in result["matches"]}
        assert pids == {"JW_000001", "JW_000002", "JW_000003"}

    def test_duplicate_match_keeps_highest_similarity(self):
        """Same product appears in two overlapping crops → keep highest score."""
        side_effects = [
            _make_match_result("JW_000001", "ring", 0.84),   # r0c0
            _make_match_result("JW_000001", "ring", 0.91),   # r0c1 — higher
            _make_unknown_result(),
            _make_unknown_result(),
        ]
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(400, 300))

        assert result["matched_count"] == 1
        assert result["matches"][0]["product_id"] == "JW_000001"
        assert result["matches"][0]["similarity"] == pytest.approx(0.91)
        assert result["matches"][0]["source_crop_id"] == "r0c1"

    def test_unknown_crops_are_ignored(self):
        """All crops UNKNOWN → empty matches list."""
        side_effects = [_make_unknown_result()] * 4
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(300, 300))

        assert result["matched_count"] == 0
        assert result["matches"] == []
        assert result["total_crops"] == 4

    def test_no_valid_matches_returns_empty_list(self):
        """Edge case: every crop falls below threshold."""
        side_effects = [_make_unknown_result()] * 4
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(100, 100))

        assert result["status"] == "success"
        assert result["matches"] == []

    def test_single_item_image_returns_one_match(self):
        """1×1 grid behaves like single-item search."""
        side_effects = [_make_match_result("JW_000001", "ring", 0.88)]
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=1, cols=1, overlap=0.0, strategy="grid")
        result = multi.match_multi(_rgb_image(300, 300))

        assert result["matched_count"] == 1
        assert result["matches"][0]["product_id"] == "JW_000001"

    def test_exact_product_id_matching_and_deduplication_key(self):
        """Deduplication uses exact product_id string (case-sensitive)."""
        side_effects = [
            _make_match_result("JW_000001", "ring", 0.80),
            _make_match_result("JW_000001", "ring", 0.85),  # same id, higher sim
            _make_match_result("JW_000002", "bracelet", 0.77),
            _make_unknown_result(),
        ]
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(400, 400))

        assert result["matched_count"] == 2
        sims = {m["product_id"]: m["similarity"] for m in result["matches"]}
        assert sims["JW_000001"] == pytest.approx(0.85)   # kept higher
        assert sims["JW_000002"] == pytest.approx(0.77)

    def test_result_schema_keys(self):
        """Match result contains all required top-level keys."""
        side_effects = [_make_match_result("JW_000001", "ring", 0.88)] + [_make_unknown_result()] * 3
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(300, 300))

        required_keys = {
            "status", "mode", "total_crops", "matched_count",
            "query_time_ms", "grid", "crop_results", "matches",
        }
        assert required_keys.issubset(result.keys())

    def test_match_entry_schema(self):
        """Each entry in matches[] has all required fields."""
        side_effects = [_make_match_result("JW_000001", "ring", 0.88)] + [_make_unknown_result()] * 3
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(300, 300))

        m = result["matches"][0]
        for key in ("rank", "product_id", "product_name", "category", "similarity",
                    "image_path", "source_crop_id", "region"):
            assert key in m, f"Missing key '{key}' in match entry"

    def test_crop_result_schema(self):
        """Each entry in crop_results[] has required fields."""
        side_effects = [_make_match_result("JW_000001", "ring", 0.88)] + [_make_unknown_result()] * 3
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(300, 300))

        for cr in result["crop_results"]:
            for key in ("crop_id", "region", "decision", "product_id", "similarity", "top5"):
                assert key in cr

    def test_matches_sorted_descending_by_similarity(self):
        """matches[] must always be sorted highest similarity first."""
        side_effects = [
            _make_match_result("JW_000003", "necklace", 0.78),
            _make_match_result("JW_000001", "ring", 0.89),
            _make_match_result("JW_000002", "bracelet", 0.84),
            _make_unknown_result(),
        ]
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(400, 300))

        sims = [m["similarity"] for m in result["matches"]]
        assert sims == sorted(sims, reverse=True)

    def test_grid_metadata_in_response(self):
        """Response includes grid configuration metadata."""
        side_effects = [_make_unknown_result()] * 9
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=3, cols=3, overlap=0.20, strategy="grid")
        result = multi.match_multi(_rgb_image(300, 300))

        assert result["grid"]["rows"] == 3
        assert result["grid"]["cols"] == 3
        assert result["grid"]["overlap"] == 0.20
        assert result["total_crops"] == 9

    def test_query_time_ms_is_positive_float(self):
        side_effects = [_make_unknown_result()] * 4
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(_rgb_image(200, 200))
        assert isinstance(result["query_time_ms"], float)
        assert result["query_time_ms"] > 0.0

    def test_accepts_path_input(self, tmp_path):
        """match_multi should accept a filepath as image_input."""
        img_path = tmp_path / "test.jpeg"
        _rgb_image(200, 200).save(img_path, format="JPEG")

        side_effects = [_make_unknown_result()] * 4
        matcher = _mock_matcher(side_effects)
        multi = MultiItemMatcher(matcher, rows=2, cols=2, strategy="grid")
        result = multi.match_multi(img_path)
        assert result["status"] == "success"


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: SAM crops
# ─────────────────────────────────────────────────────────────────────────────

from app.retrieval.multi_matcher import generate_sam_crops  # noqa: E402


class TestSAMCrops:

    def test_generates_at_least_full_image(self):
        img = _rgb_image(400, 300)
        crops = generate_sam_crops(img)
        assert len(crops) >= 1
        assert crops[0]["crop_id"] in ("item_1", "full")
        assert crops[0]["region"] == (0, 0, 400, 300)

    def test_sam_extracts_regions(self):
        img = _rgb_image(400, 300)
        crops = generate_sam_crops(img)
        assert isinstance(crops, list)
        for c in crops:
            assert "crop" in c
            assert "region" in c
            assert "crop_id" in c



# ─────────────────────────────────────────────────────────────────────────────
# API endpoint tests: POST /api/match/multi
# ─────────────────────────────────────────────────────────────────────────────

def _png_bytes(w: int = 300, h: int = 200) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(200, 160, 80)).save(buf, format="PNG")
    return buf.getvalue()


class TestMatchMultiEndpoint:

    def _post(self, img_bytes: bytes = None, **form_fields):
        data = {"rows": "2", "cols": "2", "overlap": "0.18", "strategy": "grid"}
        data.update({k: str(v) for k, v in form_fields.items()})
        img = img_bytes or _png_bytes()
        files = {"file": ("test.png", io.BytesIO(img), "image/png")}
        return client.post("/api/match/multi", data=data, files=files)

    def test_basic_200_response(self):
        res = self._post()
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "success"
        assert body["mode"] == "multi"

    def test_response_schema_keys(self):
        res = self._post()
        body = res.json()
        for key in ("total_crops", "matched_count", "query_time_ms", "grid",
                    "crop_results", "matches"):
            assert key in body, f"Missing key '{key}' in response"

    def test_total_crops_equals_rows_times_cols(self):
        res = client.post(
            "/api/match/multi",
            data={"rows": "3", "cols": "3", "overlap": "0.0", "strategy": "grid"},
            files={"file": ("t.png", io.BytesIO(_png_bytes()), "image/png")},
        )
        assert res.status_code == 200
        assert res.json()["total_crops"] == 9

    def test_empty_file_returns_400(self):
        files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}
        res = client.post(
            "/api/match/multi",
            data={"rows": "2", "cols": "2", "overlap": "0.18"},
            files=files,
        )
        assert res.status_code == 400

    def test_invalid_overlap_returns_400(self):
        res = self._post(overlap=0.6)
        assert res.status_code == 400

    def test_invalid_rows_returns_400(self):
        res = self._post(rows=0)
        assert res.status_code == 400

    def test_invalid_cols_returns_400(self):
        res = self._post(cols=7)
        assert res.status_code == 400

    def test_matches_is_list(self):
        body = self._post().json()
        assert isinstance(body["matches"], list)

    def test_crop_results_count_matches_grid(self):
        res = self._post()
        body = res.json()
        assert body["total_crops"] == len(body["crop_results"])

    def test_default_2x2_grid(self):
        """Explicit 2×2 grid should produce 4 crop_results."""
        res = self._post()
        body = res.json()
        assert body["grid"]["rows"] == 2
        assert body["grid"]["cols"] == 2
        assert body["total_crops"] == 4

    def test_sam_strategy_via_endpoint(self):
        """SAM strategy returns successful response with sam metadata."""
        files = {"file": ("t.png", io.BytesIO(_png_bytes(600, 200)), "image/png")}
        res = client.post(
            "/api/match/multi",
            data={"strategy": "sam"},
            files=files,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["strategy"] == "sam"
        assert body["total_crops"] >= 1

    def test_original_match_endpoint_unchanged(self):
        """Original /api/match endpoint still returns single-item result."""
        files = {"file": ("t.png", io.BytesIO(_png_bytes()), "image/png")}
        res = client.post(
            "/api/match",
            data={"top_k": "5", "threshold": "0.75"},
            files=files,
        )
        assert res.status_code == 200
        body = res.json()
        # Single-item endpoint has 'decision' and 'results', NOT 'matches' or 'mode'
        assert "decision" in body
        assert "results" in body
        assert "mode" not in body

