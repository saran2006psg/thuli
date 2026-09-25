"""
experiments/experiment_01/eval_experiment.py
─────────────────────────────────────────────
Runs Phase 8 Experiment 01: Saliency-Aware Jewellery Object Cropping.
Evaluates all 39 stumper images against the baseline matcher, measures metrics,
and saves results to results_exp01.csv and metrics_exp01.json.
"""

import csv
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from app.config import (
    CATALOGUE_CSV,
    ENCODER_MODEL,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
    PROJECT_ROOT,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.retrieval.matcher import JewelleryMatcher
from experiments.experiment_01.cropper import SaliencyObjectCropper

STUMPER_CSV = PROJECT_ROOT / "evaluation" / "stumper.csv"
EXP_DIR = PROJECT_ROOT / "experiments" / "experiment_01"
RESULTS_CSV = EXP_DIR / "results_exp01.csv"
METRICS_JSON = EXP_DIR / "metrics_exp01.json"


def _gt_rank(candidates: List[Dict], ground_truth: str) -> Optional[int]:
    for idx, c in enumerate(candidates):
        if c.get("category", "").lower() == ground_truth.lower():
            return idx + 1
    return None


def run_experiment() -> Dict:
    EXP_DIR.mkdir(parents=True, exist_ok=True)

    print("Initializing JewelleryMatcher...")
    matcher = JewelleryMatcher(
        index_path=FAISS_INDEX_PATH,
        product_ids_path=PRODUCT_IDS_PATH,
        catalogue_csv_path=CATALOGUE_CSV,
        encoder_model=ENCODER_MODEL,
        threshold=SIMILARITY_THRESHOLD,
        top_k=TOP_K,
    )
    cropper = SaliencyObjectCropper(margin_ratio=0.15)

    with open(STUMPER_CSV, encoding="utf-8") as f:
        stumper_rows = list(csv.DictReader(f))

    print(f"Loaded {len(stumper_rows)} stumper images for Experiment 01.\n")

    result_rows = []
    latencies = []
    crop_counts = 0

    for idx, s in enumerate(stumper_rows, start=1):
        img_id = s.get("image_id", f"img_{idx}")
        gt = (s.get("product_id") or s.get("ground_truth", "")).strip().lower()
        cond = s.get("failure_condition", "unknown").strip().lower()
        p = Path(s.get("image_path", ""))

        if not p.is_absolute():
            p = PROJECT_ROOT / p

        if not p.exists():
            print(f"Warning: Image not found: {p}")
            continue

        t0 = time.perf_counter()
        # 1. Preprocessing crop
        cropped_img, was_cropped = cropper.crop(p)
        if was_cropped:
            crop_counts += 1

        # 2. Retrieval matching
        match_res = matcher.match(cropped_img)
        t1 = time.perf_counter()
        total_lat = round((t1 - t0) * 1000.0, 2)
        latencies.append(total_lat)

        candidates = match_res.get("results", [])
        top1 = candidates[0] if candidates else {}
        top1_cat = top1.get("category", "").lower()
        top1_sim = top1.get("similarity", 0.0)

        is_match = match_res.get("decision") == "MATCH"
        top1_correct = int(top1_cat == gt and is_match)
        top5_correct = int(any(c.get("category", "").lower() == gt for c in candidates) and is_match)
        gt_rank = _gt_rank(candidates, gt)

        result_rows.append({
            "image_id": img_id,
            "ground_truth": gt,
            "failure_condition": cond,
            "decision": match_res.get("decision", "UNKNOWN"),
            "top1_category": top1_cat,
            "top1_similarity": round(top1_sim, 4),
            "gt_rank": gt_rank if gt_rank is not None else -1,
            "top1_correct": top1_correct,
            "top5_correct": top5_correct,
            "was_cropped": int(was_cropped),
            "latency_ms": total_lat,
        })

    n = len(result_rows)
    top1_acc = round(sum(r["top1_correct"] for r in result_rows) / n, 4) if n else 0.0
    top5_acc = round(sum(r["top5_correct"] for r in result_rows) / n, 4) if n else 0.0
    match_cnt = sum(1 for r in result_rows if r["decision"] == "MATCH")
    unknown_cnt = sum(1 for r in result_rows if r["decision"] == "UNKNOWN")

    lat_median = round(statistics.median(latencies), 2) if latencies else 0.0
    lat_mean = round(statistics.mean(latencies), 2) if latencies else 0.0
    lat_p95 = round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0

    # Per-condition breakdown
    conditions: Dict[str, Dict] = {}
    for r in result_rows:
        c = r["failure_condition"]
        if c not in conditions:
            conditions[c] = {"total": 0, "top1": 0, "top5": 0}
        conditions[c]["total"] += 1
        conditions[c]["top1"] += r["top1_correct"]
        conditions[c]["top5"] += r["top5_correct"]

    per_condition = {
        c: {
            "total": v["total"],
            "top1_accuracy": round(v["top1"] / v["total"], 4),
            "top5_accuracy": round(v["top5"] / v["total"], 4),
        }
        for c, v in conditions.items()
    }

    metrics = {
        "experiment": "experiment_01_saliency_cropping",
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total_images": n,
        "cropped_count": crop_counts,
        "cropped_pct": round(crop_counts / n * 100, 1) if n else 0.0,
        "top1_accuracy": top1_acc,
        "top5_accuracy": top5_acc,
        "match_count": match_cnt,
        "unknown_count": unknown_cnt,
        "mean_latency_ms": lat_mean,
        "median_latency_ms": lat_median,
        "p95_latency_ms": lat_p95,
        "per_condition": per_condition,
    }

    # Save CSV
    fieldnames = [
        "image_id", "ground_truth", "failure_condition", "decision",
        "top1_category", "top1_similarity", "gt_rank", "top1_correct",
        "top5_correct", "was_cropped", "latency_ms"
    ]
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result_rows)

    # Save JSON
    with open(METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("Experiment 01 Complete.")
    print(f"Top-1 Accuracy: {top1_acc * 100:.2f}%")
    print(f"Top-5 Accuracy: {top5_acc * 100:.2f}%")
    print(f"MATCH: {match_cnt}, UNKNOWN: {unknown_cnt}")
    print(f"Median Latency: {lat_median} ms | P95: {lat_p95} ms")
    print(f"Images Cropped: {crop_counts}/{n} ({metrics['cropped_pct']}%)")

    return metrics


if __name__ == "__main__":
    run_experiment()
