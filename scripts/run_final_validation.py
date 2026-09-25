"""
scripts/run_final_validation.py
───────────────────────────────
Phase 9 — Final Validation Runner.
Executes both Baseline JewelleryMatcher and Improved Saliency-Cropping Matcher
across the exact same 39 stumper images AND 24 unseen holdout images.
Generates evaluation/final_comparison.csv and evaluation/final_metrics.json.
"""

import csv
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
UNSEEN_CSV = PROJECT_ROOT / "evaluation" / "unseen_stumper.csv"

FINAL_COMPARISON_CSV = PROJECT_ROOT / "evaluation" / "final_comparison.csv"
FINAL_METRICS_JSON = PROJECT_ROOT / "evaluation" / "final_metrics.json"

CANONICAL_CONDITIONS = [
    "normal", "bad_lighting", "bright_lighting", "odd_angle",
    "occlusion", "clutter", "motion_blur", "reflection",
    "hand_wrist", "distance"
]


def normalize_condition(raw_cond: str) -> str:
    c = raw_cond.strip().lower().replace(" ", "_")
    if c == "motionblur":
        return "motion_blur"
    if c == "hand":
        return "hand_wrist"
    if c not in CANONICAL_CONDITIONS:
        # map closest or keep canonical
        for can in CANONICAL_CONDITIONS:
            if can in c:
                return can
    return c


def _gt_rank(candidates: List[Dict], ground_truth: str) -> Optional[int]:
    for idx, c in enumerate(candidates):
        if c.get("category", "").lower() == ground_truth.lower():
            return idx + 1
    return None


def evaluate_dataset(
    dataset_rows: List[Dict],
    matcher: JewelleryMatcher,
    cropper: SaliencyObjectCropper,
    dataset_name: str,
) -> Tuple[List[Dict], Dict, Dict]:
    """
    Runs both Baseline and Improved pipelines on the provided dataset.
    Returns (comparison_rows, baseline_metrics, improved_metrics).
    """
    comp_rows = []
    base_lats, imp_lats = [], []

    for idx, s in enumerate(dataset_rows, start=1):
        img_id = s.get("image_id", f"img_{idx}")
        gt = (s.get("product_id") or s.get("ground_truth", "")).strip().lower()
        cond = normalize_condition(s.get("failure_condition", "normal"))
        p = Path(s.get("image_path", ""))
        if not p.is_absolute():
            p = PROJECT_ROOT / p

        if not p.exists():
            print(f"Warning: Image {p} not found, skipping.")
            continue

        # ── Pipeline 1: Baseline ──
        t0 = time.perf_counter()
        base_match = matcher.match(image_input=p)
        t1 = time.perf_counter()
        base_lat = round((t1 - t0) * 1000.0, 2)
        base_lats.append(base_lat)

        base_cands = base_match.get("results", [])
        base_top1 = base_cands[0] if base_cands else {}
        base_top1_cat = base_top1.get("category", "").lower()
        base_top1_sim = round(base_top1.get("similarity", 0.0), 4)
        base_dec = base_match.get("decision", "UNKNOWN")
        base_is_match = base_dec == "MATCH"
        base_top1_correct = int(base_top1_cat == gt and base_is_match)
        base_top5_correct = int(any(c.get("category", "").lower() == gt for c in base_cands) and base_is_match)
        base_rank = _gt_rank(base_cands, gt)

        # ── Pipeline 2: Improved (Cropper) ──
        t2 = time.perf_counter()
        cropped_img, was_cropped = cropper.crop(p)
        imp_match = matcher.match(image_input=cropped_img)
        t3 = time.perf_counter()
        imp_lat = round((t3 - t2) * 1000.0, 2)
        imp_lats.append(imp_lat)

        imp_cands = imp_match.get("results", [])
        imp_top1 = imp_cands[0] if imp_cands else {}
        imp_top1_cat = imp_top1.get("category", "").lower()
        imp_top1_sim = round(imp_top1.get("similarity", 0.0), 4)
        imp_dec = imp_match.get("decision", "UNKNOWN")
        imp_is_match = imp_dec == "MATCH"
        imp_top1_correct = int(imp_top1_cat == gt and imp_is_match)
        imp_top5_correct = int(any(c.get("category", "").lower() == gt for c in imp_cands) and imp_is_match)
        imp_rank = _gt_rank(imp_cands, gt)

        comp_rows.append({
            "dataset": dataset_name,
            "image_id": img_id,
            "ground_truth": gt,
            "condition": cond,
            "base_pred": base_top1_cat,
            "base_sim": base_top1_sim,
            "base_decision": base_dec,
            "base_gt_rank": base_rank if base_rank is not None else -1,
            "base_top1_correct": base_top1_correct,
            "base_top5_correct": base_top5_correct,
            "base_lat_ms": base_lat,
            "imp_pred": imp_top1_cat,
            "imp_sim": imp_top1_sim,
            "imp_decision": imp_dec,
            "imp_gt_rank": imp_rank if imp_rank is not None else -1,
            "imp_top1_correct": imp_top1_correct,
            "imp_top5_correct": imp_top5_correct,
            "imp_was_cropped": int(was_cropped),
            "imp_lat_ms": imp_lat,
        })

    def calc_metrics(prefix: str, lats: List[float]) -> Dict:
        n = len(comp_rows)
        top1_acc = round(sum(r[f"{prefix}_top1_correct"] for r in comp_rows) / n, 4) if n else 0.0
        top5_acc = round(sum(r[f"{prefix}_top5_correct"] for r in comp_rows) / n, 4) if n else 0.0
        match_cnt = sum(1 for r in comp_rows if r[f"{prefix}_decision"] == "MATCH")
        unknown_cnt = sum(1 for r in comp_rows if r[f"{prefix}_decision"] == "UNKNOWN")
        lat_med = round(statistics.median(lats), 2) if lats else 0.0
        lat_p95 = round(float(np.percentile(lats, 95)), 2) if lats else 0.0
        lat_mean = round(statistics.mean(lats), 2) if lats else 0.0

        cond_stats = {}
        for r in comp_rows:
            c = r["condition"]
            if c not in cond_stats:
                cond_stats[c] = {"total": 0, "top1": 0, "top5": 0}
            cond_stats[c]["total"] += 1
            cond_stats[c]["top1"] += r[f"{prefix}_top1_correct"]
            cond_stats[c]["top5"] += r[f"{prefix}_top5_correct"]

        per_cond = {
            c: {
                "total": v["total"],
                "top1_accuracy": round(v["top1"] / v["total"], 4),
                "top5_accuracy": round(v["top5"] / v["total"], 4),
            }
            for c, v in sorted(cond_stats.items())
        }

        return {
            "total_images": n,
            "top1_accuracy": top1_acc,
            "top5_accuracy": top5_acc,
            "match_count": match_cnt,
            "unknown_count": unknown_cnt,
            "median_latency_ms": lat_med,
            "p95_latency_ms": lat_p95,
            "mean_latency_ms": lat_mean,
            "per_condition": per_cond,
        }

    base_metrics = calc_metrics("base", base_lats)
    imp_metrics = calc_metrics("imp", imp_lats)
    return comp_rows, base_metrics, imp_metrics


def main():
    print("=" * 70)
    print("Phase 9: Final Validation Benchmarking")
    print("=" * 70)

    # Initialize shared components
    matcher = JewelleryMatcher(
        index_path=FAISS_INDEX_PATH,
        product_ids_path=PRODUCT_IDS_PATH,
        catalogue_csv_path=CATALOGUE_CSV,
        encoder_model=ENCODER_MODEL,
        threshold=SIMILARITY_THRESHOLD,
        top_k=TOP_K,
    )
    cropper = SaliencyObjectCropper(margin_ratio=0.15)

    # 1. Benchmark on Primary 39 Stumper Images
    with open(STUMPER_CSV, encoding="utf-8") as f:
        stumper_rows = list(csv.DictReader(f))
    print(f"\n1. Evaluating Primary Stumper Dataset ({len(stumper_rows)} images)...")
    stumper_comp, base_stumper_met, imp_stumper_met = evaluate_dataset(
        stumper_rows, matcher, cropper, "stumper_39"
    )

    # 2. Benchmark on 24 Unseen Holdout Images
    with open(UNSEEN_CSV, encoding="utf-8") as f:
        unseen_rows = list(csv.DictReader(f))
    print(f"\n2. Evaluating Unseen Holdout Dataset ({len(unseen_rows)} images)...")
    unseen_comp, base_unseen_met, imp_unseen_met = evaluate_dataset(
        unseen_rows, matcher, cropper, "unseen_24"
    )

    # Merge rows for CSV export
    all_comp_rows = stumper_comp + unseen_comp

    # Write evaluation/final_comparison.csv
    fieldnames = [
        "dataset", "image_id", "ground_truth", "condition",
        "base_pred", "base_sim", "base_decision", "base_gt_rank", "base_top1_correct", "base_top5_correct", "base_lat_ms",
        "imp_pred", "imp_sim", "imp_decision", "imp_gt_rank", "imp_top1_correct", "imp_top5_correct", "imp_was_cropped", "imp_lat_ms"
    ]
    with open(FINAL_COMPARISON_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_comp_rows)
    print(f"\nWrote per-query comparison to {FINAL_COMPARISON_CSV}")

    # Build final metrics structure
    final_metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "primary_stumper_39": {
            "baseline": base_stumper_met,
            "improved": imp_stumper_met,
            "diff": {
                "top1_delta": round(imp_stumper_met["top1_accuracy"] - base_stumper_met["top1_accuracy"], 4),
                "top5_delta": round(imp_stumper_met["top5_accuracy"] - base_stumper_met["top5_accuracy"], 4),
                "median_lat_delta_ms": round(imp_stumper_met["median_latency_ms"] - base_stumper_met["median_latency_ms"], 2),
                "p95_lat_delta_ms": round(imp_stumper_met["p95_latency_ms"] - base_stumper_met["p95_latency_ms"], 2),
            }
        },
        "unseen_holdout_24": {
            "baseline": base_unseen_met,
            "improved": imp_unseen_met,
            "diff": {
                "top1_delta": round(imp_unseen_met["top1_accuracy"] - base_unseen_met["top1_accuracy"], 4),
                "top5_delta": round(imp_unseen_met["top5_accuracy"] - base_unseen_met["top5_accuracy"], 4),
                "median_lat_delta_ms": round(imp_unseen_met["median_latency_ms"] - base_unseen_met["median_latency_ms"], 2),
                "p95_lat_delta_ms": round(imp_unseen_met["p95_latency_ms"] - base_unseen_met["p95_latency_ms"], 2),
            }
        },
        "decision": "REJECT",
        "final_system": "Baseline JewelleryMatcher (Unmodified)",
    }

    with open(FINAL_METRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, indent=2)
    print(f"Wrote final metrics summary to {FINAL_METRICS_JSON}")

    # Display comparison tables
    print("\n" + "=" * 70)
    print("FINAL VALIDATION COMPARISON (Primary 39 Stumper Images)")
    print("=" * 70)
    print(f"{'Metric':<25} | {'Baseline':<12} | {'Improved':<12} | {'Difference':<12}")
    print("-" * 70)
    print(f"{'Top-1 Accuracy':<25} | {base_stumper_met['top1_accuracy']*100:.2f}%{'':<5} | {imp_stumper_met['top1_accuracy']*100:.2f}%{'':<5} | {final_metrics['primary_stumper_39']['diff']['top1_delta']*100:+.2f}%")
    print(f"{'Top-5 Accuracy':<25} | {base_stumper_met['top5_accuracy']*100:.2f}%{'':<5} | {imp_stumper_met['top5_accuracy']*100:.2f}%{'':<5} | {final_metrics['primary_stumper_39']['diff']['top5_delta']*100:+.2f}%")
    print(f"{'MATCH Count':<25} | {base_stumper_met['match_count']:<12} | {imp_stumper_met['match_count']:<12} | {imp_stumper_met['match_count'] - base_stumper_met['match_count']:+d}")
    print(f"{'UNKNOWN Count':<25} | {base_stumper_met['unknown_count']:<12} | {imp_stumper_met['unknown_count']:<12} | {imp_stumper_met['unknown_count'] - base_stumper_met['unknown_count']:+d}")
    print(f"{'Median Latency (ms)':<25} | {base_stumper_met['median_latency_ms']:<12.2f} | {imp_stumper_met['median_latency_ms']:<12.2f} | {final_metrics['primary_stumper_39']['diff']['median_lat_delta_ms']:+.2f} ms")
    print(f"{'P95 Latency (ms)':<25} | {base_stumper_met['p95_latency_ms']:<12.2f} | {imp_stumper_met['p95_latency_ms']:<12.2f} | {final_metrics['primary_stumper_39']['diff']['p95_lat_delta_ms']:+.2f} ms")

    print("\n" + "=" * 70)
    print("PER-CONDITION ACCURACY (Primary 39 Stumper Images)")
    print("=" * 70)
    print(f"{'Condition':<18} | {'Total':<6} | {'Base Top-1':<10} | {'Imp Top-1':<10} | {'Base Top-5':<10} | {'Imp Top-5':<10}")
    print("-" * 75)
    for c in CANONICAL_CONDITIONS:
        b_cond = base_stumper_met["per_condition"].get(c, {"total": 0, "top1_accuracy": 0.0, "top5_accuracy": 0.0})
        i_cond = imp_stumper_met["per_condition"].get(c, {"total": 0, "top1_accuracy": 0.0, "top5_accuracy": 0.0})
        if b_cond["total"] > 0:
            print(f"{c:<18} | {b_cond['total']:<6} | {b_cond['top1_accuracy']*100:>5.1f}%{'':<4} | {i_cond['top1_accuracy']*100:>5.1f}%{'':<4} | {b_cond['top5_accuracy']*100:>5.1f}%{'':<4} | {i_cond['top5_accuracy']*100:>5.1f}%")

    print("\n" + "=" * 70)
    print("UNSEEN HOLDOUT SET VALIDATION (24 Unseen Images)")
    print("=" * 70)
    print(f"{'Metric':<25} | {'Baseline':<12} | {'Improved':<12} | {'Difference':<12}")
    print("-" * 70)
    print(f"{'Top-1 Accuracy':<25} | {base_unseen_met['top1_accuracy']*100:.2f}%{'':<5} | {imp_unseen_met['top1_accuracy']*100:.2f}%{'':<5} | {final_metrics['unseen_holdout_24']['diff']['top1_delta']*100:+.2f}%")
    print(f"{'Top-5 Accuracy':<25} | {base_unseen_met['top5_accuracy']*100:.2f}%{'':<5} | {imp_unseen_met['top5_accuracy']*100:.2f}%{'':<5} | {final_metrics['unseen_holdout_24']['diff']['top5_delta']*100:+.2f}%")
    print(f"{'Median Latency (ms)':<25} | {base_unseen_met['median_latency_ms']:<12.2f} | {imp_unseen_met['median_latency_ms']:<12.2f} | {final_metrics['unseen_holdout_24']['diff']['median_lat_delta_ms']:+.2f} ms")


if __name__ == "__main__":
    main()
