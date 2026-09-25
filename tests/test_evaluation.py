"""
tests/test_evaluation.py
─────────────────────────
Tests for Phase 7 evaluation engine and API endpoints.
"""

import io
import json
import csv
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_dummy_match_result(category: str, similarity: float = 0.82) -> dict:
    """Build a mock matcher.match() response."""
    candidates = []
    for i, (cat, sim) in enumerate([
        (category, similarity),
        ("necklace", 0.72),
        ("bracelet", 0.68),
        ("earring",  0.61),
        ("ring",     0.55),
    ], start=1):
        candidates.append({
            "rank": i,
            "product_id": f"JW_{i:06d}",
            "product_name": f"Test {cat}",
            "category": cat,
            "subcategory": cat,
            "image_path": "",
            "similarity": sim,
        })
    return {
        "status": "success",
        "decision": "MATCH" if similarity >= 0.75 else "UNKNOWN",
        "threshold": 0.75,
        "best_similarity": similarity,
        "query_time_ms": 210.0,
        "top_k": 5,
        "results": candidates,
    }


# ── Unit tests for runner ──────────────────────────────────────────────────────

class TestEvaluationRunner:
    """Tests for app.evaluation.runner functions."""

    def test_runner_imports(self):
        from app.evaluation.runner import run_evaluation, write_results
        assert callable(run_evaluation)
        assert callable(write_results)

    def test_gt_rank_found(self):
        from app.evaluation.runner import _gt_rank
        candidates = [
            {"rank": 1, "category": "ring"},
            {"rank": 2, "category": "bracelet"},
            {"rank": 3, "category": "necklace"},
        ]
        assert _gt_rank(candidates, "bracelet") == 2

    def test_gt_rank_not_found(self):
        from app.evaluation.runner import _gt_rank
        candidates = [{"rank": 1, "category": "ring"}]
        assert _gt_rank(candidates, "earring") is None

    def test_run_evaluation_structure(self, tmp_path):
        """run_evaluation returns correctly structured dict with mocked matcher."""
        # Create a tiny stumper CSV with one valid image
        eval_dir = tmp_path / "evaluation" / "images"
        eval_dir.mkdir(parents=True)

        # Write a tiny dummy JPEG
        img = Image.new("RGB", (64, 64), color=(180, 120, 60))
        img_path = eval_dir / "id01.jpeg"
        img.save(img_path, format="JPEG")

        stumper_csv = tmp_path / "evaluation" / "stumper.csv"
        with open(stumper_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["image_id", "product_id", "failure_condition", "notes", "image_path"]
            )
            writer.writeheader()
            writer.writerow({
                "image_id": "id01",
                "product_id": "ring",
                "failure_condition": "clutter",
                "notes": "test",
                "image_path": str(img_path),
            })

        mock_matcher = MagicMock()
        mock_matcher.match.return_value = make_dummy_match_result("ring", 0.82)

        from app.evaluation import runner as R
        orig_csv = R.STUMPER_CSV
        R.STUMPER_CSV = stumper_csv
        try:
            report = R.run_evaluation(mock_matcher)
        finally:
            R.STUMPER_CSV = orig_csv

        assert "metrics" in report
        assert "rows" in report
        m = report["metrics"]
        assert m["total_images"] == 1
        assert m["valid_images"] == 1
        assert 0.0 <= m["top1_accuracy"] <= 1.0
        assert 0.0 <= m["top5_accuracy"] <= 1.0
        assert "per_condition" in m
        assert "dataset_progress" in m
        assert "worst_failures" in m

    def test_write_results(self, tmp_path):
        from app.evaluation import runner as R

        metrics = {
            "run_at": "2026-01-01T00:00:00+00:00",
            "total_images": 2,
            "valid_images": 2,
            "top1_accuracy": 0.5,
            "top5_accuracy": 1.0,
            "match_count": 1,
            "unknown_count": 1,
            "mean_latency_ms": 200.0,
            "median_latency_ms": 200.0,
            "p95_latency_ms": 210.0,
            "per_condition": {
                "clutter": {"total": 2, "top1_accuracy": 0.5, "top5_accuracy": 1.0}
            },
            "dataset_progress": {"current": 2, "target": 100, "pct": 2.0},
            "worst_failures": [],
        }
        rows = [
            {
                "image_id": "id01", "ground_truth": "ring",
                "failure_condition": "clutter", "decision": "MATCH",
                "top1_category": "ring", "top1_similarity": 0.82,
                "gt_rank": 1, "top1_correct": 1, "top5_correct": 1,
                "latency_ms": 200.0, "error": "",
            }
        ]

        orig_res = R.RESULTS_CSV
        orig_met = R.METRICS_JSON
        orig_ana = R.ANALYSIS_MD
        R.RESULTS_CSV  = tmp_path / "results.csv"
        R.METRICS_JSON = tmp_path / "metrics.json"
        R.ANALYSIS_MD  = tmp_path / "analysis.md"
        try:
            R.write_results(metrics, rows)
        finally:
            R.RESULTS_CSV  = orig_res
            R.METRICS_JSON = orig_met
            R.ANALYSIS_MD  = orig_ana

        assert (tmp_path / "results.csv").exists()
        assert (tmp_path / "metrics.json").exists()
        assert (tmp_path / "analysis.md").exists()

        with open(tmp_path / "metrics.json") as f:
            loaded = json.load(f)
        assert loaded["top1_accuracy"] == 0.5

        with open(tmp_path / "results.csv") as f:
            csv_rows = list(csv.DictReader(f))
        assert len(csv_rows) == 1
        assert csv_rows[0]["image_id"] == "id01"


# ── API endpoint tests ─────────────────────────────────────────────────────────

class TestEvaluationAPI:
    """Tests for /api/evaluation/* endpoints."""

    def test_evaluation_results_404_when_no_file(self, tmp_path):
        """GET /api/evaluation/results returns 404 when metrics.json doesn't exist."""
        import app.api.routes as routes
        orig = routes.METRICS_JSON
        routes.METRICS_JSON = tmp_path / "nonexistent_metrics.json"
        try:
            res = client.get("/api/evaluation/results")
            assert res.status_code == 404
        finally:
            routes.METRICS_JSON = orig

    def test_evaluation_results_ok_when_file_exists(self, tmp_path):
        """GET /api/evaluation/results returns 200 with metrics when file exists."""
        import app.api.routes as routes

        metrics = {
            "run_at": "2026-01-01T00:00:00+00:00",
            "total_images": 5,
            "valid_images": 5,
            "top1_accuracy": 0.6,
            "top5_accuracy": 0.8,
            "match_count": 3,
            "unknown_count": 2,
            "mean_latency_ms": 200.0,
            "median_latency_ms": 190.0,
            "p95_latency_ms": 220.0,
            "per_condition": {},
            "dataset_progress": {"current": 5, "target": 100, "pct": 5.0},
            "worst_failures": [],
        }
        metrics_path = tmp_path / "metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(metrics, f)

        orig = routes.METRICS_JSON
        routes.METRICS_JSON = metrics_path
        try:
            res = client.get("/api/evaluation/results")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "ok"
            assert data["metrics"]["top1_accuracy"] == 0.6
        finally:
            routes.METRICS_JSON = orig

    def test_evaluation_run_endpoint(self):
        """POST /api/evaluation/run triggers evaluation and returns metrics dict."""
        import app.api.routes as routes
        from app.evaluation.runner import run_evaluation, write_results

        fake_metrics = {
            "run_at": "2026-01-01T00:00:00+00:00",
            "total_images": 39,
            "valid_images": 39,
            "top1_accuracy": 0.75,
            "top5_accuracy": 0.92,
            "match_count": 20,
            "unknown_count": 19,
            "mean_latency_ms": 210.0,
            "median_latency_ms": 200.0,
            "p95_latency_ms": 250.0,
            "per_condition": {
                "clutter": {"total": 6, "top1_accuracy": 0.67, "top5_accuracy": 1.0}
            },
            "dataset_progress": {"current": 39, "target": 100, "pct": 39.0},
            "worst_failures": [],
        }
        fake_rows = []

        with patch("app.api.routes.run_evaluation", return_value={"metrics": fake_metrics, "rows": fake_rows}):
            with patch("app.api.routes.write_results"):
                res = client.post("/api/evaluation/run")

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "metrics" in data
        assert data["metrics"]["total_images"] == 39

    def test_evaluation_download_404_when_no_file(self, tmp_path):
        """GET /api/evaluation/download returns 404 when results CSV doesn't exist."""
        import app.api.routes as routes
        orig = routes.RESULTS_CSV
        routes.RESULTS_CSV = tmp_path / "nonexistent_results.csv"
        try:
            res = client.get("/api/evaluation/download")
            assert res.status_code == 404
        finally:
            routes.RESULTS_CSV = orig
