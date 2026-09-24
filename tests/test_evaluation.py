"""
tests/test_evaluation.py
─────────────────────────
Tests for Phase 6 Stumper Dataset Validation & Evaluation Pipeline.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from PIL import Image

from app.config import CATALOGUE_CSV
from scripts.evaluate import evaluate_matcher
from scripts.validate_stumper_dataset import (
    ALLOWED_CONDITIONS,
    REQUIRED_COLUMNS,
    validate_stumper_dataset,
)


@pytest.fixture
def sample_catalogue_csv(tmp_path):
    cat_path = tmp_path / "catalogue.csv"
    df = pd.DataFrame({
        "product_id": ["JW_000001", "JW_000002", "JW_000003"],
        "product_name": ["Gold Ring", "Silver Necklace", "Diamond Earrings"],
        "category": ["ring", "necklace", "earrings"],
        "image_path": ["data/img1.jpg", "data/img2.jpg", "data/img3.jpg"],
    })
    df.to_csv(cat_path, index=False)
    return cat_path


@pytest.fixture
def sample_images(tmp_path):
    img_dir = tmp_path / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    img1 = img_dir / "stump_1.jpg"
    img2 = img_dir / "stump_2.jpg"
    img3 = img_dir / "stump_3.jpg"

    for img_p in [img1, img2, img3]:
        im = Image.new("RGB", (64, 64), color="gold")
        im.save(img_p)

    return {"img1": img1, "img2": img2, "img3": img3, "dir": img_dir}


class TestStumperValidation:
    """Test suite for validate_stumper_dataset.py."""

    def test_empty_template_handling(self, tmp_path, sample_catalogue_csv):
        csv_path = tmp_path / "stumper.csv"
        csv_path.write_text("image_id,product_id,failure_condition,notes,image_path\n", encoding="utf-8")

        # allow_empty=True -> True
        assert validate_stumper_dataset(csv_path, sample_catalogue_csv, allow_empty=True) is True
        # allow_empty=False -> False (no queries to evaluate)
        assert validate_stumper_dataset(csv_path, sample_catalogue_csv, allow_empty=False) is False

    def test_valid_stumper_dataset(self, tmp_path, sample_catalogue_csv, sample_images):
        csv_path = tmp_path / "stumper.csv"
        df = pd.DataFrame([
            {
                "image_id": "stump_0001",
                "product_id": "JW_000001",
                "failure_condition": "bad_lighting",
                "notes": "dim bedroom light",
                "image_path": str(sample_images["img1"]),
            },
            {
                "image_id": "stump_0002",
                "product_id": "JW_000002",
                "failure_condition": "occlusion",
                "notes": "partially covered",
                "image_path": str(sample_images["img2"]),
            },
        ])
        df.to_csv(csv_path, index=False)

        assert validate_stumper_dataset(csv_path, sample_catalogue_csv) is True

    def test_missing_required_columns(self, tmp_path, sample_catalogue_csv):
        csv_path = tmp_path / "stumper.csv"
        # Missing 'failure_condition'
        df = pd.DataFrame([
            {"image_id": "stump_0001", "product_id": "JW_000001", "image_path": "foo.jpg"}
        ])
        df.to_csv(csv_path, index=False)

        assert validate_stumper_dataset(csv_path, sample_catalogue_csv) is False

    def test_duplicate_image_id(self, tmp_path, sample_catalogue_csv, sample_images):
        csv_path = tmp_path / "stumper.csv"
        df = pd.DataFrame([
            {
                "image_id": "stump_0001",
                "product_id": "JW_000001",
                "failure_condition": "bad_lighting",
                "image_path": str(sample_images["img1"]),
            },
            {
                "image_id": "stump_0001",  # duplicate ID
                "product_id": "JW_000002",
                "failure_condition": "reflection",
                "image_path": str(sample_images["img2"]),
            },
        ])
        df.to_csv(csv_path, index=False)

        assert validate_stumper_dataset(csv_path, sample_catalogue_csv) is False

    def test_nonexistent_product_id(self, tmp_path, sample_catalogue_csv, sample_images):
        csv_path = tmp_path / "stumper.csv"
        df = pd.DataFrame([
            {
                "image_id": "stump_0001",
                "product_id": "JW_INVALID_999",  # not in catalogue
                "failure_condition": "bad_lighting",
                "image_path": str(sample_images["img1"]),
            }
        ])
        df.to_csv(csv_path, index=False)

        assert validate_stumper_dataset(csv_path, sample_catalogue_csv) is False

    def test_invalid_failure_condition(self, tmp_path, sample_catalogue_csv, sample_images):
        csv_path = tmp_path / "stumper.csv"
        df = pd.DataFrame([
            {
                "image_id": "stump_0001",
                "product_id": "JW_000001",
                "failure_condition": "made_up_condition_xyz",  # not in taxonomy
                "image_path": str(sample_images["img1"]),
            }
        ])
        df.to_csv(csv_path, index=False)

        assert validate_stumper_dataset(csv_path, sample_catalogue_csv) is False

    def test_missing_image_file(self, tmp_path, sample_catalogue_csv):
        csv_path = tmp_path / "stumper.csv"
        df = pd.DataFrame([
            {
                "image_id": "stump_0001",
                "product_id": "JW_000001",
                "failure_condition": "bad_lighting",
                "image_path": str(tmp_path / "non_existent.jpg"),
            }
        ])
        df.to_csv(csv_path, index=False)

        assert validate_stumper_dataset(csv_path, sample_catalogue_csv) is False


class TestEvaluationPipeline:
    """Test suite for evaluate.py execution and metrics computation."""

    def test_evaluate_matcher_with_mock(self, tmp_path, sample_catalogue_csv, sample_images, monkeypatch):
        stumper_csv = tmp_path / "stumper.csv"
        results_csv = tmp_path / "results.csv"
        metrics_json = tmp_path / "metrics.json"
        analysis_md = tmp_path / "analysis.md"

        df = pd.DataFrame([
            {
                "image_id": "stump_0001",
                "product_id": "JW_000001",
                "failure_condition": "bad_lighting",
                "notes": "dark photo",
                "image_path": str(sample_images["img1"]),
            },
            {
                "image_id": "stump_0002",
                "product_id": "JW_000002",
                "failure_condition": "occlusion",
                "notes": "hand covering half",
                "image_path": str(sample_images["img2"]),
            },
            {
                "image_id": "stump_0003",
                "product_id": "JW_000003",
                "failure_condition": "bad_lighting",
                "notes": "yellow tint",
                "image_path": str(sample_images["img3"]),
            },
        ])
        df.to_csv(stumper_csv, index=False)

        # Mock JewelleryMatcher
        mock_matcher = MagicMock()
        mock_matcher.index.size = 6157

        def mock_match(img_path, top_k=5, threshold=0.60):
            p = str(img_path)
            if "stump_1" in p:
                # Top-1 match (JW_000001)
                return {
                    "results": [
                        {"rank": 1, "product_id": "JW_000001", "similarity": 0.85},
                        {"rank": 2, "product_id": "JW_000002", "similarity": 0.62},
                    ],
                    "best_similarity": 0.85,
                    "decision": "MATCH",
                    "query_time_ms": 12.5,
                }
            elif "stump_2" in p:
                # Top-5 match at rank 2 (JW_000002)
                return {
                    "results": [
                        {"rank": 1, "product_id": "JW_000003", "similarity": 0.72},
                        {"rank": 2, "product_id": "JW_000002", "similarity": 0.68},
                    ],
                    "best_similarity": 0.72,
                    "decision": "MATCH",
                    "query_time_ms": 14.1,
                }
            else:
                # Miss (JW_000003 not in top results)
                return {
                    "results": [
                        {"rank": 1, "product_id": "JW_000001", "similarity": 0.45},
                        {"rank": 2, "product_id": "JW_000002", "similarity": 0.40},
                    ],
                    "best_similarity": 0.45,
                    "decision": "UNKNOWN",
                    "query_time_ms": 11.8,
                }

        mock_matcher.match.side_effect = mock_match

        metrics = evaluate_matcher(
            stumper_csv_path=stumper_csv,
            results_csv_path=results_csv,
            metrics_json_path=metrics_json,
            analysis_md_path=analysis_md,
            threshold=0.60,
            top_k=5,
            matcher=mock_matcher,
        )

        assert metrics is not None
        assert results_csv.exists()
        assert metrics_json.exists()
        assert analysis_md.exists()

        # Check results CSV
        res_df = pd.read_csv(results_csv)
        assert len(res_df) == 3
        assert "predicted_top1_product_id" in res_df.columns
        assert "top5_product_ids" in res_df.columns
        assert "decision" in res_df.columns
        assert "latency_ms" in res_df.columns
        assert "correct_rank" in res_df.columns

        # Check metrics values
        # stump 1: Top-1 correct
        # stump 2: Top-5 correct (rank 2)
        # stump 3: failed
        # Top-1 count = 1/3 (33.33%), Top-5 count = 2/3 (66.67%)
        assert metrics["overall_accuracy"]["top1_correct_count"] == 1
        assert metrics["overall_accuracy"]["top5_correct_count"] == 2
        assert pytest.approx(metrics["overall_accuracy"]["top1_accuracy_percent"], 0.1) == 33.33
        assert pytest.approx(metrics["overall_accuracy"]["top5_accuracy_percent"], 0.1) == 66.67

        # Decisions: 2 MATCH, 1 UNKNOWN
        assert metrics["overall_accuracy"]["match_decision_count"] == 2
        assert metrics["overall_accuracy"]["unknown_decision_count"] == 1

        # Check condition breakdown
        cond_breakdown = metrics["condition_breakdown"]
        assert "bad_lighting" in cond_breakdown
        assert cond_breakdown["bad_lighting"]["total_queries"] == 2
        assert cond_breakdown["bad_lighting"]["top1_correct"] == 1
        assert "occlusion" in cond_breakdown
        assert cond_breakdown["occlusion"]["total_queries"] == 1
        assert cond_breakdown["occlusion"]["top5_correct"] == 1

        # Check analysis.md contents
        analysis_text = analysis_md.read_text(encoding="utf-8")
        assert "Top-1 Accuracy:" in analysis_text
        assert "Breakdown by Failure Condition" in analysis_text
        assert "Top Failure Cases" in analysis_text
