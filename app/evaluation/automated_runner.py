"""
app/evaluation/automated_runner.py
───────────────────────────────────
Automated Stumper Evaluation Engine.
Evaluates the 900 realistically generated images against the production JewelleryMatcher,
computes category-level and product-level accuracies, latency percentiles, condition breakdowns,
and generates side-by-side comparison against the hand-shot stumper benchmark.
"""

import csv
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Input paths
AUTOMATED_CSV = PROJECT_ROOT / "evaluation" / "automated_stumper.csv"
HANDSHOT_METRICS_JSON = PROJECT_ROOT / "evaluation" / "metrics.json"

# Output persistence paths
RESULTS_CSV = PROJECT_ROOT / "evaluation" / "automated_results.csv"
METRICS_JSON = PROJECT_ROOT / "evaluation" / "automated_metrics.json"
COMPARISON_JSON = PROJECT_ROOT / "evaluation" / "automated_comparison.json"


def load_automated_stumper() -> List[Dict[str, str]]:
    """Load the automated stumper manifest."""
    if not AUTOMATED_CSV.exists():
        raise FileNotFoundError(f"Automated stumper manifest not found: {AUTOMATED_CSV}")
    rows = []
    with open(AUTOMATED_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def run_automated_evaluation(matcher: Any, progress_callback=None) -> Dict[str, Any]:
    """
    Run all automated stumper images through the existing matcher
    WITHOUT modifying CLIP, FAISS, threshold (0.75), or margin logic.
    """
    stumper_rows = load_automated_stumper()
    if not stumper_rows:
        raise ValueError("automated_stumper.csv is empty.")

    total_images = len(stumper_rows)
    print(f"Starting automated evaluation on {total_images} images...")

    result_rows: List[Dict[str, Any]] = []
    latencies: List[float] = []

    for i, row in enumerate(stumper_rows, start=1):
        img_path = Path(row["generated_image_path"].strip())
        if not img_path.exists():
            continue

        gt_product_id = row["product_id"].strip()
        gt_category = row["category"].strip().lower()
        condition = row["failure_condition"].strip()
        image_id = row["image_id"].strip()
        prod_name = row.get("product_name", gt_product_id)

        try:
            # Query existing matcher with identical parameters
            match_result = matcher.match(image_input=img_path, top_k=5)
        except Exception as e:
            result_rows.append({
                "image_id": image_id,
                "product_id": gt_product_id,
                "product_name": prod_name,
                "category": gt_category,
                "failure_condition": condition,
                "decision": "ERROR",
                "best_similarity": 0.0,
                "top1_product_id": "",
                "top1_category": "",
                "top1_similarity": 0.0,
                "top1_category_correct": 0,
                "top5_category_correct": 0,
                "top1_product_correct": 0,
                "top5_product_correct": 0,
                "gt_category_rank": -1,
                "gt_product_rank": -1,
                "latency_ms": 0.0,
                "error": str(e),
                "generated_image_path": str(img_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            })
            continue

        latency = match_result["query_time_ms"]
        latencies.append(latency)

        candidates = match_result.get("results", [])
        top1 = candidates[0] if candidates else {}
        top1_cat = top1.get("category", "").lower()
        top1_pid = top1.get("product_id", "")
        top1_sim = top1.get("similarity", 0.0)

        is_match = match_result["decision"] == "MATCH"

        # 1. Category-level accuracy (comparable with hand-shot)
        top1_category_correct = int(top1_cat == gt_category and is_match)
        top5_category_correct = int(any(
            c.get("category", "").lower() == gt_category for c in candidates
        ) and is_match)

        # 2. Exact product-level accuracy (strict catalogue identification)
        top1_product_correct = int(top1_pid == gt_product_id and is_match)
        top5_product_correct = int(any(
            c.get("product_id", "") == gt_product_id for c in candidates
        ) and is_match)

        # Ranks
        gt_category_rank = -1
        gt_product_rank = -1
        for rank, c in enumerate(candidates, start=1):
            if gt_category_rank == -1 and c.get("category", "").lower() == gt_category:
                gt_category_rank = rank
            if gt_product_rank == -1 and c.get("product_id", "") == gt_product_id:
                gt_product_rank = rank

        result_rows.append({
            "image_id": image_id,
            "product_id": gt_product_id,
            "product_name": prod_name,
            "category": gt_category,
            "failure_condition": condition,
            "decision": match_result["decision"],
            "best_similarity": round(match_result["best_similarity"], 4),
            "top1_product_id": top1_pid,
            "top1_category": top1_cat,
            "top1_similarity": round(top1_sim, 4),
            "top1_category_correct": top1_category_correct,
            "top5_category_correct": top5_category_correct,
            "top1_product_correct": top1_product_correct,
            "top5_product_correct": top5_product_correct,
            "gt_category_rank": gt_category_rank,
            "gt_product_rank": gt_product_rank,
            "latency_ms": round(latency, 2),
            "error": "",
            "generated_image_path": str(img_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        })

        if i % 100 == 0 or i == total_images:
            print(f"  Evaluated {i}/{total_images} images...")
            if progress_callback:
                progress_callback(i, total_images)

    valid = [r for r in result_rows if r["decision"] != "ERROR"]
    n = len(valid)

    # ── Metric Aggregation ───────────────────────────────────────────────────
    # Category level
    top1_cat_correct_count = sum(r["top1_category_correct"] for r in valid)
    top5_cat_correct_count = sum(r["top5_category_correct"] for r in valid)
    top1_cat_acc = round(top1_cat_correct_count / n, 4) if n else 0.0
    top5_cat_acc = round(top5_cat_correct_count / n, 4) if n else 0.0

    # Product level
    top1_prod_correct_count = sum(r["top1_product_correct"] for r in valid)
    top5_prod_correct_count = sum(r["top5_product_correct"] for r in valid)
    top1_prod_acc = round(top1_prod_correct_count / n, 4) if n else 0.0
    top5_prod_acc = round(top5_prod_correct_count / n, 4) if n else 0.0

    # Decision counts
    match_count = sum(1 for r in valid if r["decision"] == "MATCH")
    unknown_count = sum(1 for r in valid if r["decision"] == "UNKNOWN")
    unknown_rate = round(unknown_count / n, 4) if n else 0.0

    # Wrong matches (category level)
    wrong_matches_count = sum(1 for r in valid if r["decision"] == "MATCH" and r["top1_category_correct"] == 0)
    failure_count = wrong_matches_count + unknown_count
    failure_rate = round(failure_count / n, 4) if n else 0.0

    # Product level failures
    wrong_prod_matches_count = sum(1 for r in valid if r["decision"] == "MATCH" and r["top1_product_correct"] == 0)
    product_failure_rate = round((wrong_prod_matches_count + unknown_count) / n, 4) if n else 0.0

    # Latencies
    lat_median = round(statistics.median(latencies), 2) if latencies else 0.0
    lat_mean = round(statistics.mean(latencies), 2) if latencies else 0.0
    lat_p95 = round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0

    # Per-condition metrics
    conditions: Dict[str, Dict[str, Any]] = {}
    for r in valid:
        c = r["failure_condition"]
        if c not in conditions:
            conditions[c] = {
                "total": 0,
                "top1_category_correct": 0,
                "top5_category_correct": 0,
                "top1_product_correct": 0,
                "top5_product_correct": 0,
                "match_count": 0,
                "unknown_count": 0,
                "wrong_matches_count": 0,
                "latencies": [],
            }
        conditions[c]["total"] += 1
        conditions[c]["top1_category_correct"] += r["top1_category_correct"]
        conditions[c]["top5_category_correct"] += r["top5_category_correct"]
        conditions[c]["top1_product_correct"] += r["top1_product_correct"]
        conditions[c]["top5_product_correct"] += r["top5_product_correct"]
        if r["decision"] == "MATCH":
            conditions[c]["match_count"] += 1
            if r["top1_category_correct"] == 0:
                conditions[c]["wrong_matches_count"] += 1
        else:
            conditions[c]["unknown_count"] += 1
        conditions[c]["latencies"].append(r["latency_ms"])

    per_condition: Dict[str, Dict[str, Any]] = {}
    for c, data in sorted(conditions.items()):
        c_n = data["total"]
        c_fails = data["wrong_matches_count"] + data["unknown_count"]
        per_condition[c] = {
            "total": c_n,
            "top1_accuracy": round(data["top1_category_correct"] / c_n, 4) if c_n else 0.0,
            "top5_accuracy": round(data["top5_category_correct"] / c_n, 4) if c_n else 0.0,
            "top1_product_accuracy": round(data["top1_product_correct"] / c_n, 4) if c_n else 0.0,
            "top5_product_accuracy": round(data["top5_product_correct"] / c_n, 4) if c_n else 0.0,
            "match_count": data["match_count"],
            "unknown_count": data["unknown_count"],
            "wrong_matches_count": data["wrong_matches_count"],
            "failure_rate": round(c_fails / c_n, 4) if c_n else 0.0,
            "median_latency_ms": round(statistics.median(data["latencies"]), 2) if data["latencies"] else 0.0,
        }

    # Identify representative failed examples for UI display
    failed_examples = [
        r for r in valid
        if r["top1_category_correct"] == 0 or r["decision"] == "UNKNOWN"
    ][:30]

    automated_metrics = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "source_images_count": 100,
        "total_images": total_images,
        "valid_images": n,
        "top1_accuracy": top1_cat_acc,
        "top5_accuracy": top5_cat_acc,
        "top1_product_accuracy": top1_prod_acc,
        "top5_product_accuracy": top5_prod_acc,
        "top1_correct_count": top1_cat_correct_count,
        "top5_correct_count": top5_cat_correct_count,
        "match_count": match_count,
        "unknown_count": unknown_count,
        "unknown_rate": unknown_rate,
        "wrong_matches_count": wrong_matches_count,
        "failure_count": failure_count,
        "failure_rate": failure_rate,
        "product_failure_rate": product_failure_rate,
        "mean_latency_ms": lat_mean,
        "median_latency_ms": lat_median,
        "p95_latency_ms": lat_p95,
        "per_condition": per_condition,
        "failed_examples": failed_examples,
    }

    # ── Load Hand-shot Metrics & Build Comparison ────────────────────────────
    comparison = build_comparison(automated_metrics)

    return {
        "metrics": automated_metrics,
        "comparison": comparison,
        "rows": result_rows,
    }


def build_comparison(automated: Dict[str, Any]) -> Dict[str, Any]:
    """Build side-by-side comparison between Hand-shot and Automated stumper."""
    handshot = {}
    if HANDSHOT_METRICS_JSON.exists():
        try:
            with open(HANDSHOT_METRICS_JSON, "r", encoding="utf-8") as f:
                handshot = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load handshot metrics: {e}")

    hs_total = handshot.get("total_images", 111)
    hs_top1 = handshot.get("top1_accuracy", 0.7207)
    hs_top5 = handshot.get("top5_accuracy", 0.8919)
    hs_unknown = handshot.get("unknown_count", 8)
    hs_unknown_rate = round(hs_unknown / hs_total, 4) if hs_total else 0.0721
    hs_wrong = handshot.get("wrong_matches_count", 23)
    hs_failure_rate = round((hs_wrong + hs_unknown) / hs_total, 4) if hs_total else 0.2793
    hs_median_lat = handshot.get("median_latency_ms", 106.6)
    hs_p95_lat = handshot.get("p95_latency_ms", 136.73)

    auto_top1 = automated["top1_accuracy"]
    auto_top5 = automated["top5_accuracy"]
    auto_unknown = automated["unknown_count"]
    auto_unknown_rate = automated["unknown_rate"]
    auto_failure_rate = automated["failure_rate"]
    auto_median_lat = automated["median_latency_ms"]
    auto_p95_lat = automated["p95_latency_ms"]

    # Does automated stumper defeat the matcher at a higher rate?
    defeated_higher = auto_failure_rate > hs_failure_rate
    diff_failure = round((auto_failure_rate - hs_failure_rate) * 100.0, 2)
    diff_top1 = round((auto_top1 - hs_top1) * 100.0, 2)
    diff_top5 = round((auto_top5 - hs_top5) * 100.0, 2)

    return {
        "handshot": {
            "name": "Hand-Shot Stumper (Real Phone Photos)",
            "total_images": hs_total,
            "top1_accuracy": hs_top1,
            "top5_accuracy": hs_top5,
            "failure_rate": hs_failure_rate,
            "unknown_count": hs_unknown,
            "unknown_rate": hs_unknown_rate,
            "wrong_matches_count": hs_wrong,
            "median_latency_ms": hs_median_lat,
            "p95_latency_ms": hs_p95_lat,
        },
        "automated": {
            "name": "Automated Stumper (100 Catalogue Items × 9 Realistic Variations)",
            "total_images": automated["total_images"],
            "source_images_count": automated["source_images_count"],
            "top1_accuracy": auto_top1,
            "top5_accuracy": auto_top5,
            "top1_product_accuracy": automated.get("top1_product_accuracy", 0.0),
            "top5_product_accuracy": automated.get("top5_product_accuracy", 0.0),
            "failure_rate": auto_failure_rate,
            "unknown_count": auto_unknown,
            "unknown_rate": auto_unknown_rate,
            "wrong_matches_count": automated["wrong_matches_count"],
            "median_latency_ms": auto_median_lat,
            "p95_latency_ms": auto_p95_lat,
        },
        "delta": {
            "top1_pct": diff_top1,
            "top5_pct": diff_top5,
            "failure_rate_pct": diff_failure,
            "defeated_higher": defeated_higher,
        },
        "summary": (
            f"Automated stumper {'DEFEATED' if defeated_higher else 'DID NOT DEFEAT'} the matcher at a higher rate. "
            f"Failure Rate: Automated {auto_failure_rate * 100:.1f}% vs Hand-Shot {hs_failure_rate * 100:.1f}% "
            f"({'+' if diff_failure > 0 else ''}{diff_failure}% difference). "
            f"Top-1 Accuracy: Automated {auto_top1 * 100:.1f}% vs Hand-Shot {hs_top1 * 100:.1f}%."
        ),
    }


def write_automated_results(report: Dict[str, Any]) -> None:
    """Persist results.csv, metrics.json, and comparison.json."""
    metrics = report["metrics"]
    comparison = report["comparison"]
    rows = report["rows"]

    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)

    # 1. Write CSV
    if rows:
        fieldnames = [
            "image_id",
            "product_id",
            "product_name",
            "category",
            "failure_condition",
            "decision",
            "best_similarity",
            "top1_product_id",
            "top1_category",
            "top1_similarity",
            "top1_category_correct",
            "top5_category_correct",
            "top1_product_correct",
            "top5_product_correct",
            "gt_category_rank",
            "gt_product_rank",
            "latency_ms",
            "error",
            "generated_image_path",
        ]
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # 2. Write Metrics JSON
    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # 3. Write Comparison JSON
    with open(COMPARISON_JSON, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print(f"\nPersisted Automated Stumper outputs:")
    print(f"  - Results CSV     : {RESULTS_CSV}")
    print(f"  - Metrics JSON    : {METRICS_JSON}")
    print(f"  - Comparison JSON : {COMPARISON_JSON}")
