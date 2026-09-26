"""
app/evaluation/runner.py
─────────────────────────
Phase 7 Evaluation Engine.
Runs all stumper images through JewelleryMatcher, computes metrics,
and writes results.csv + metrics.json + analysis.md.
"""

import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STUMPER_CSV  = PROJECT_ROOT / "evaluation" / "stumper.csv"
RESULTS_CSV  = PROJECT_ROOT / "evaluation" / "results.csv"
METRICS_JSON = PROJECT_ROOT / "evaluation" / "metrics.json"
ANALYSIS_MD  = PROJECT_ROOT / "evaluation" / "analysis.md"


def _load_stumper() -> List[Dict[str, str]]:
    rows = []
    with open(STUMPER_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def _gt_rank(results: List[Dict], ground_truth_category: str) -> Optional[int]:
    """Return 1-based rank of first result matching ground_truth category, or None."""
    for r in results:
        if r.get("category", "").lower() == ground_truth_category.lower():
            return r["rank"]
    return None


def run_evaluation(matcher: Any) -> Dict[str, Any]:
    """Run all stumper images through matcher and return full evaluation report."""
    stumper_rows = _load_stumper()
    if not stumper_rows:
        raise ValueError("stumper.csv is empty.")

    result_rows: List[Dict] = []
    latencies: List[float] = []

    for row in stumper_rows:
        img_path = Path(row["image_path"].strip())
        if not img_path.exists():
            continue

        ground_truth = row["product_id"].strip().lower()
        condition    = row["failure_condition"].strip()
        image_id     = row["image_id"].strip()

        try:
            match_result = matcher.match(image_input=img_path, top_k=5)
        except Exception as e:
            result_rows.append({
                "image_id": image_id,
                "ground_truth": ground_truth,
                "failure_condition": condition,
                "decision": "ERROR",
                "top1_category": "",
                "top1_similarity": 0.0,
                "gt_rank": -1,
                "top1_correct": 0,
                "top5_correct": 0,
                "latency_ms": 0.0,
                "error": str(e),
            })
            continue

        latency = match_result["query_time_ms"]
        latencies.append(latency)

        candidates = match_result["results"]
        top1     = candidates[0] if candidates else {}
        top1_cat = top1.get("category", "").lower()
        top1_sim = top1.get("similarity", 0.0)

        is_match = match_result["decision"] == "MATCH"
        top1_correct = int(top1_cat == ground_truth and is_match)
        top5_correct = int(any(
            c.get("category", "").lower() == ground_truth for c in candidates
        ) and is_match)
        gt_rank = _gt_rank(candidates, ground_truth)

        result_rows.append({
            "image_id": image_id,
            "ground_truth": ground_truth,
            "failure_condition": condition,
            "decision": match_result["decision"],
            "top1_category": top1_cat,
            "top1_similarity": round(top1_sim, 4),
            "gt_rank": gt_rank if gt_rank is not None else -1,
            "top1_correct": top1_correct,
            "top5_correct": top5_correct,
            "latency_ms": round(latency, 2),
            "error": "",
        })

    valid = [r for r in result_rows if r["decision"] != "ERROR"]
    n = len(valid)

    top1_correct_count = sum(r["top1_correct"] for r in valid)
    top5_correct_count = sum(r["top5_correct"] for r in valid)
    top1_acc = round(top1_correct_count / n, 4) if n else 0.0
    top5_acc = round(top5_correct_count / n, 4) if n else 0.0
    match_count   = sum(1 for r in valid if r["decision"] == "MATCH")
    unknown_count = sum(1 for r in valid if r["decision"] == "UNKNOWN")
    wrong_matches_count = sum(1 for r in valid if r["decision"] == "MATCH" and r["top1_correct"] == 0)

    # Verification Metrics:
    # False Acceptance Rate (FAR): proportion of queries falsely accepted as MATCH (wrong match)
    false_acceptance_rate = round(wrong_matches_count / n, 4) if n else 0.0
    far_pct = round(false_acceptance_rate * 100.0, 2)

    # False Rejection Rate (FRR): proportion of queries rejected as UNKNOWN
    false_rejection_rate = round(unknown_count / n, 4) if n else 0.0
    frr_pct = round(false_rejection_rate * 100.0, 2)

    lat_median = round(statistics.median(latencies), 2) if latencies else 0.0
    lat_mean   = round(statistics.mean(latencies), 2)   if latencies else 0.0
    lat_p95    = round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0

    conditions: Dict[str, Dict] = {}
    for r in valid:
        cond = r["failure_condition"]
        if cond not in conditions:
            conditions[cond] = {"total": 0, "top1": 0, "top5": 0}
        conditions[cond]["total"] += 1
        conditions[cond]["top1"]  += r["top1_correct"]
        conditions[cond]["top5"]  += r["top5_correct"]

    per_condition = {
        cond: {
            "total": v["total"],
            "top1_accuracy": round(v["top1"] / v["total"], 4),
            "top5_accuracy": round(v["top5"] / v["total"], 4),
        }
        for cond, v in conditions.items()
    }

    failures = sorted(
        [r for r in valid if r["top1_correct"] == 0],
        key=lambda x: x["top1_similarity"],
    )[:10]

    metrics = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total_images": len(result_rows),
        "valid_images": n,
        "top1_accuracy": top1_acc,
        "top5_accuracy": top5_acc,
        "top1_correct_count": top1_correct_count,
        "top5_correct_count": top5_correct_count,
        "match_count": match_count,
        "unknown_count": unknown_count,
        "wrong_matches_count": wrong_matches_count,
        "false_acceptance_rate": false_acceptance_rate,
        "far_pct": far_pct,
        "false_rejection_rate": false_rejection_rate,
        "frr_pct": frr_pct,
        "mean_latency_ms": lat_mean,
        "median_latency_ms": lat_median,
        "p95_latency_ms": lat_p95,
        "per_condition": per_condition,
        "dataset_progress": {
            "current": len(stumper_rows),
            "target": 100,
            "pct": round(len(stumper_rows) / 100 * 100, 1),
        },
        "worst_failures": [
            {k: v for k, v in r.items() if k != "error"}
            for r in failures
        ],
        "all_results": [
            {k: v for k, v in r.items() if k != "error"}
            for r in valid
        ],
    }

    return {"metrics": metrics, "rows": result_rows}


def write_results(metrics: Dict, rows: List[Dict]) -> None:
    """Persist results.csv, metrics.json, and analysis.md."""
    fieldnames = [
        "image_id", "ground_truth", "failure_condition", "decision",
        "top1_category", "top1_similarity", "gt_rank",
        "top1_correct", "top5_correct", "latency_ms", "error",
    ]
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    pc = metrics["per_condition"]
    pc_table = "\n".join(
        f"| `{cond}` | {v['total']} | {v['top1_accuracy']*100:.1f}% | {v['top5_accuracy']*100:.1f}% |"
        for cond, v in sorted(pc.items())
    )
    failures = metrics["worst_failures"]
    fail_rows = "\n".join(
        f"| `{r['image_id']}` | `{r['ground_truth']}` | `{r['top1_category']}` | {r['top1_similarity']:.4f} | {r['gt_rank']} | `{r['failure_condition']}` |"
        for r in failures
    )
    md = f"""# Phase 7 — Baseline Evaluation Report

> Generated: {metrics['run_at']}
> Model: CLIP ViT-B/32 | Index: FAISS IndexFlatIP | Threshold: 0.75

## Summary

| Metric | Value |
|---|---|
| Total Images | {metrics['total_images']} |
| Valid Images | {metrics['valid_images']} |
| **Top-1 Accuracy** | **{metrics['top1_accuracy']*100:.1f}%** |
| **Top-5 Accuracy** | **{metrics['top5_accuracy']*100:.1f}%** |
| MATCH decisions | {metrics['match_count']} |
| UNKNOWN decisions | {metrics['unknown_count']} |
| Wrong Matches | {metrics.get('wrong_matches_count', 0)} |
| **False Acceptance Rate (FAR)** | **{metrics.get('far_pct', 0.0)}%** |
| **False Rejection Rate (FRR)** | **{metrics.get('frr_pct', 0.0)}%** |
| Mean Latency | {metrics['mean_latency_ms']} ms |
| Median Latency | {metrics['median_latency_ms']} ms |
| P95 Latency | {metrics['p95_latency_ms']} ms |

## Per-Condition Accuracy

| Condition | N | Top-1 | Top-5 |
|---|---|---|---|
{pc_table}

## Worst Failures (Top-10)

| Image | Ground Truth | Predicted | Similarity | GT Rank | Condition |
|---|---|---|---|---|---|
{fail_rows if fail_rows else '| — | All matched | — | — | — | — |'}

## Dataset Progress

- Current: {metrics['dataset_progress']['current']} / {metrics['dataset_progress']['target']} images
- Progress: {metrics['dataset_progress']['pct']}%
"""
    with open(ANALYSIS_MD, "w", encoding="utf-8") as f:
        f.write(md)
