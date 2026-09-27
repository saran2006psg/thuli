"""
app/evaluation/runner.py
─────────────────────────
Phase 7 Evaluation Engine.
Scans ALL images in evaluation/images/, runs them through JewelleryMatcher,
computes metrics, and writes results.csv + metrics.json + analysis.md.

Ground-truth is loaded from stumper.csv (keyed by image filename stem).
Images not listed in stumper.csv are still evaluated but labelled
failure_condition='unknown' and their category accuracy cannot be scored —
they are counted in total_images but excluded from accuracy numerator/denominator.
"""

import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

PROJECT_ROOT   = Path(__file__).resolve().parent.parent.parent
IMAGES_DIR     = PROJECT_ROOT / "evaluation" / "images"
STUMPER_CSV    = PROJECT_ROOT / "evaluation" / "stumper.csv"
RESULTS_CSV    = PROJECT_ROOT / "evaluation" / "results.csv"
METRICS_JSON   = PROJECT_ROOT / "evaluation" / "metrics.json"
ANALYSIS_MD    = PROJECT_ROOT / "evaluation" / "analysis.md"

# Supported image extensions
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _load_gt_lookup() -> Dict[str, Dict[str, str]]:
    """
    Load stumper.csv into a dict keyed by image_id (filename stem, e.g. 'id01').
    Returns: { image_id: { product_id, failure_condition, notes } }
    """
    lookup: Dict[str, Dict[str, str]] = {}
    if not STUMPER_CSV.exists():
        return lookup
    with open(STUMPER_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            img_id = row.get("image_id", "").strip()
            if img_id:
                lookup[img_id] = {
                    "product_id": row.get("product_id", "").strip().lower(),
                    "failure_condition": row.get("failure_condition", "unknown").strip(),
                    "notes": row.get("notes", "").strip(),
                }
    return lookup


def _gt_rank(results: List[Dict], ground_truth_category: str) -> Optional[int]:
    """Return 1-based rank of first result matching ground_truth category, or None."""
    for r in results:
        if r.get("category", "").lower() == ground_truth_category.lower():
            return r["rank"]
    return None


def run_evaluation(matcher: Any) -> Dict[str, Any]:
    """
    Scan evaluation/images/ for all images, run through matcher, return full report.
    Ground-truth labels come from stumper.csv lookup.
    """
    gt_lookup = _load_gt_lookup()

    # Collect all valid image files, sorted by stem name
    image_files: List[Path] = sorted(
        [p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTS],
        key=lambda p: p.stem,
    )

    if not image_files:
        raise ValueError(f"No images found in {IMAGES_DIR}. Check the path.")

    result_rows: List[Dict] = []
    latencies: List[float] = []

    for img_path in image_files:
        image_id = img_path.stem  # e.g. 'id01'

        # Skip obviously corrupt/empty files (< 1 KB)
        if img_path.stat().st_size < 1024:
            result_rows.append({
                "image_id": image_id,
                "ground_truth": gt_lookup.get(image_id, {}).get("product_id", "unknown"),
                "failure_condition": gt_lookup.get(image_id, {}).get("failure_condition", "unknown"),
                "decision": "SKIP",
                "top1_category": "",
                "top1_similarity": 0.0,
                "gt_rank": -1,
                "top1_correct": 0,
                "top5_correct": 0,
                "latency_ms": 0.0,
                "has_gt": 0,
                "error": "File too small / corrupt",
            })
            continue

        gt_info = gt_lookup.get(image_id, {})
        ground_truth = gt_info.get("product_id", "unknown")
        condition = gt_info.get("failure_condition", "unknown")
        has_gt = int(bool(gt_info))

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
                "has_gt": has_gt,
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

        # Only score accuracy when we have ground truth
        if has_gt:
            top1_correct = int(top1_cat == ground_truth and is_match)
            top5_correct = int(any(
                c.get("category", "").lower() == ground_truth for c in candidates
            ) and is_match)
            gt_rank = _gt_rank(candidates, ground_truth)
        else:
            top1_correct = 0
            top5_correct = 0
            gt_rank = None

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
            "has_gt": has_gt,
            "error": "",
        })

    # ── Aggregate metrics ──────────────────────────────────────────────────────
    valid        = [r for r in result_rows if r["decision"] not in ("ERROR", "SKIP")]
    scored       = [r for r in valid if r["has_gt"]]  # only rows with ground truth
    n_valid      = len(valid)
    n_scored     = len(scored)

    top1_correct_count  = sum(r["top1_correct"] for r in scored)
    top5_correct_count  = sum(r["top5_correct"] for r in scored)
    top1_acc = round(top1_correct_count / n_scored, 4) if n_scored else 0.0
    top5_acc = round(top5_correct_count / n_scored, 4) if n_scored else 0.0

    match_count         = sum(1 for r in valid if r["decision"] == "MATCH")
    unknown_count       = sum(1 for r in valid if r["decision"] == "UNKNOWN")
    wrong_matches_count = sum(
        1 for r in scored
        if r["decision"] == "MATCH" and r["top1_correct"] == 0
    )

    false_acceptance_rate = round(wrong_matches_count / n_scored, 4) if n_scored else 0.0
    far_pct = round(false_acceptance_rate * 100.0, 2)
    false_rejection_rate  = round(unknown_count / n_valid, 4) if n_valid else 0.0
    frr_pct = round(false_rejection_rate * 100.0, 2)

    lat_median = round(statistics.median(latencies), 2) if latencies else 0.0
    lat_mean   = round(statistics.mean(latencies), 2)   if latencies else 0.0
    lat_p95    = round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0

    # Per-condition breakdown (only scored rows)
    conditions: Dict[str, Dict] = {}
    for r in scored:
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
        [r for r in scored if r["top1_correct"] == 0],
        key=lambda x: x["top1_similarity"],
    )[:10]

    metrics = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total_images": len(result_rows),
        "valid_images": n_valid,
        "scored_images": n_scored,
        "skipped_images": sum(1 for r in result_rows if r["decision"] == "SKIP"),
        "error_images": sum(1 for r in result_rows if r["decision"] == "ERROR"),
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
            "current": len(result_rows),
            "target": 115,
            "pct": round(len(result_rows) / 115 * 100, 1),
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
        "top1_correct", "top5_correct", "latency_ms", "has_gt", "error",
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
    md = f"""# Phase 7 — Evaluation Report
## All Images in evaluation/images/

> Generated: {metrics['run_at']}
> Model: CLIP ViT-B/32 | Index: FAISS IndexFlatIP | Threshold: 0.75
> Source: All {metrics['total_images']} images scanned from evaluation/images/

## Summary

| Metric | Value |
|---|---|
| Total Images Scanned | {metrics['total_images']} |
| Valid (ran through matcher) | {metrics['valid_images']} |
| Scored (has ground truth) | {metrics['scored_images']} |
| Skipped (corrupt/tiny) | {metrics['skipped_images']} |
| Errors | {metrics['error_images']} |
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
{pc_table if pc_table else '| — | No labelled conditions | — | — |'}

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
