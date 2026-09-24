"""
scripts/evaluate.py
───────────────────
Executes the full evaluation pipeline on the Stumper dataset using the
production JewelleryMatcher. Computes Top-1 accuracy, Top-5 accuracy,
per-condition breakdown, latency metrics, and error analysis logs.

Outputs:
  - evaluation/results.csv
  - evaluation/metrics.json
  - evaluation/analysis.md
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (
    CATALOGUE_CSV,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.retrieval.matcher import JewelleryMatcher
from scripts.validate_stumper_dataset import validate_stumper_dataset

STUMPER_CSV = PROJECT_ROOT / "evaluation" / "stumper.csv"
RESULTS_CSV = PROJECT_ROOT / "evaluation" / "results.csv"
METRICS_JSON = PROJECT_ROOT / "evaluation" / "metrics.json"
ANALYSIS_MD = PROJECT_ROOT / "evaluation" / "analysis.md"


def evaluate_matcher(
    stumper_csv_path: Path = STUMPER_CSV,
    results_csv_path: Path = RESULTS_CSV,
    metrics_json_path: Path = METRICS_JSON,
    analysis_md_path: Path = ANALYSIS_MD,
    threshold: float = SIMILARITY_THRESHOLD,
    top_k: int = TOP_K,
    matcher: Optional[JewelleryMatcher] = None,
) -> Optional[Dict[str, Any]]:
    print("\n" + "=" * 65)
    print("  Stumper Dataset Benchmark Evaluation (Phase 6)")
    print("=" * 65)

    # 1. Validate dataset first
    if not stumper_csv_path.exists():
        print(f"[ERROR] Stumper CSV not found at: {stumper_csv_path}")
        return None

    df_stumper = pd.read_csv(stumper_csv_path)
    if len(df_stumper) == 0:
        print("[WARN] evaluation/stumper.csv is empty.")
        print("       Please capture your 100+ real jewellery photos, add them to")
        print("       evaluation/images/, and annotate them in evaluation/stumper.csv.")
        print("       Refer to evaluation/README.md for instructions.")
        print("=" * 65 + "\n")
        return None

    is_valid = validate_stumper_dataset(stumper_csv_path=stumper_csv_path)
    if not is_valid:
        print("[ERROR] Stumper dataset validation failed. Fix errors above before evaluation.")
        return None

    # 2. Instantiate production matcher
    if matcher is None:
        print("\n  Loading production JewelleryMatcher...")
        matcher = JewelleryMatcher(
            index_path=FAISS_INDEX_PATH,
            product_ids_path=PRODUCT_IDS_PATH,
            catalogue_csv_path=CATALOGUE_CSV,
            threshold=threshold,
            top_k=top_k,
        )

    # 3. Run evaluation across all stumper images
    records: List[Dict[str, Any]] = []
    latencies: List[float] = []

    print(f"\n  Evaluating {len(df_stumper)} stumper queries (Top-K={top_k}, Threshold={threshold:.2f})...\n")

    for _, row in tqdm(df_stumper.iterrows(), total=len(df_stumper), desc="  Evaluating"):
        img_id = str(row["image_id"]).strip()
        gt_pid = str(row["product_id"]).strip()
        condition = str(row.get("failure_condition", "unknown")).strip()
        notes = str(row.get("notes", "")).strip()
        raw_path = str(row["image_path"]).strip()

        img_p = Path(raw_path)
        if not img_p.is_absolute():
            img_p = PROJECT_ROOT / img_p

        match_res = matcher.match(img_p, top_k=top_k, threshold=threshold)
        candidates = match_res["results"]
        cand_pids = [c["product_id"] for c in candidates]
        pred_top1 = cand_pids[0] if cand_pids else "NONE"
        top1_sim = match_res["best_similarity"]
        decision = match_res["decision"]
        lat_ms = match_res["query_time_ms"]
        latencies.append(lat_ms)

        # Check ground truth in candidates
        correct_rank = None
        correct_sim = None
        if gt_pid in cand_pids:
            correct_rank = cand_pids.index(gt_pid) + 1
            correct_sim = candidates[correct_rank - 1]["similarity"]

        is_top1_correct = (pred_top1 == gt_pid)
        is_top5_correct = (correct_rank is not None and correct_rank <= 5)

        records.append({
            "image_id": img_id,
            "ground_truth_product_id": gt_pid,
            "predicted_top1_product_id": pred_top1,
            "is_top1_correct": is_top1_correct,
            "is_top5_correct": is_top5_correct,
            "correct_rank": correct_rank if correct_rank else "",
            "top1_similarity": round(top1_sim, 4),
            "correct_similarity": round(correct_sim, 4) if correct_sim is not None else "",
            "decision": decision,
            "failure_condition": condition,
            "notes": notes,
            "latency_ms": round(lat_ms, 2),
            "top5_product_ids": ";".join(cand_pids),
        })

    # 4. Save results.csv
    results_df = pd.DataFrame(records)
    results_csv_path.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(results_csv_path, index=False)
    print(f"\n  Saved detailed results to : {results_csv_path}")

    # 5. Compute aggregate metrics
    n_total = len(records)
    n_top1_correct = sum(1 for r in records if r["is_top1_correct"])
    n_top5_correct = sum(1 for r in records if r["is_top5_correct"])
    n_match = sum(1 for r in records if r["decision"] == "MATCH")
    n_unknown = sum(1 for r in records if r["decision"] == "UNKNOWN")

    top1_acc = (n_top1_correct / n_total) * 100.0 if n_total > 0 else 0.0
    top5_acc = (n_top5_correct / n_total) * 100.0 if n_total > 0 else 0.0

    lat_arr = np.array(latencies)
    lat_mean = float(np.mean(lat_arr))
    lat_median = float(np.median(lat_arr))
    lat_p95 = float(np.percentile(lat_arr, 95))
    lat_p99 = float(np.percentile(lat_arr, 99))
    lat_min = float(np.min(lat_arr))
    lat_max = float(np.max(lat_arr))

    # Condition breakdown
    condition_stats: Dict[str, Dict[str, Any]] = {}
    for cond in sorted(results_df["failure_condition"].unique()):
        sub_df = results_df[results_df["failure_condition"] == cond]
        c_tot = len(sub_df)
        c_top1 = int(sub_df["is_top1_correct"].sum())
        c_top5 = int(sub_df["is_top5_correct"].sum())
        c_sims = sub_df["top1_similarity"].tolist()

        condition_stats[cond] = {
            "total_queries": c_tot,
            "top1_correct": c_top1,
            "top1_accuracy": round((c_top1 / c_tot) * 100.0, 2) if c_tot > 0 else 0.0,
            "top5_correct": c_top5,
            "top5_accuracy": round((c_top5 / c_tot) * 100.0, 2) if c_tot > 0 else 0.0,
            "mean_similarity": round(float(np.mean(c_sims)), 4) if c_sims else 0.0,
        }

    metrics: Dict[str, Any] = {
        "dataset": {
            "total_queries": n_total,
            "catalogue_size": matcher.index.size,
            "threshold": threshold,
            "top_k": top_k,
        },
        "overall_accuracy": {
            "top1_accuracy_percent": round(top1_acc, 2),
            "top1_correct_count": n_top1_correct,
            "top5_accuracy_percent": round(top5_acc, 2),
            "top5_correct_count": n_top5_correct,
            "match_decision_count": n_match,
            "unknown_decision_count": n_unknown,
        },
        "latency_ms": {
            "mean": round(lat_mean, 2),
            "median": round(lat_median, 2),
            "p95": round(lat_p95, 2),
            "p99": round(lat_p99, 2),
            "min": round(lat_min, 2),
            "max": round(lat_max, 2),
        },
        "condition_breakdown": condition_stats,
    }

    # 6. Save metrics.json
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Saved metrics to          : {metrics_json_path}")

    # 7. Generate analysis.md report
    generate_analysis_report(metrics, records, analysis_md_path)
    print(f"  Generated analysis report : {analysis_md_path}")

    # 8. Print summary
    print("\n" + "=" * 65)
    print("  Stumper Evaluation Summary (Baseline Matcher)")
    print("=" * 65)
    print(f"  Total Queries Tested : {n_total}")
    print(f"  Top-1 Accuracy       : {top1_acc:.2f}% ({n_top1_correct}/{n_total})")
    print(f"  Top-5 Accuracy       : {top5_acc:.2f}% ({n_top5_correct}/{n_total})")
    print(f"  Decisions            : {n_match} MATCH, {n_unknown} UNKNOWN")
    print(f"  Median Latency (CPU) : {lat_median:.2f} ms (p95: {lat_p95:.2f} ms)")
    print("-" * 65)
    print("  Accuracy by Failure Condition:")
    for cond, st in condition_stats.items():
        print(
            f"    - {cond:<22}: Top-1 {st['top1_accuracy']:>5.1f}% | Top-5 {st['top5_accuracy']:>5.1f}% ({st['total_queries']} imgs)"
        )
    print("=" * 65 + "\n")

    return metrics


def generate_analysis_report(
    metrics: Dict[str, Any],
    records: List[Dict[str, Any]],
    out_path: Path,
) -> None:
    """Generate Markdown report summarizing failure modes and accuracy breakdowns."""
    tot = metrics["dataset"]["total_queries"]
    top1 = metrics["overall_accuracy"]["top1_accuracy_percent"]
    top5 = metrics["overall_accuracy"]["top5_accuracy_percent"]
    lat_med = metrics["latency_ms"]["median"]
    lat_p95 = metrics["latency_ms"]["p95"]

    lines = [
        "# Stumper Evaluation Report — Baseline Model (Phase 6)",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Total Stumper Queries:** {tot}",
        f"- **Top-1 Accuracy:** **{top1:.2f}%**",
        f"- **Top-5 Accuracy:** **{top5:.2f}%**",
        f"- **Retrieval Latency (CPU):** Median: **{lat_med:.2f} ms** | p95: **{lat_p95:.2f} ms**",
        "",
        "---",
        "",
        "## 2. Breakdown by Failure Condition",
        "",
        "| Failure Condition | Query Count | Top-1 Accuracy | Top-5 Accuracy | Mean Similarity |",
        "|---|---:|---:|---:|---:|",
    ]

    for cond, st in metrics["condition_breakdown"].items():
        lines.append(
            f"| `{cond}` | {st['total_queries']} | {st['top1_accuracy']:.1f}% | {st['top5_accuracy']:.1f}% | {st['mean_similarity']:.4f} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Top Failure Cases (Failed Top-5 Retrieval)",
        "",
        "The following queries failed to retrieve the ground-truth product within the Top-5 candidates:",
        "",
        "| Image ID | Failure Condition | Ground Truth | Predicted Top-1 | Top-1 Similarity | Notes |",
        "|---|---|---|---|---:|---|",
    ])

    failed_top5 = [r for r in records if not r["is_top5_correct"]]
    for r in failed_top5[:15]:
        lines.append(
            f"| `{r['image_id']}` | `{r['failure_condition']}` | `{r['ground_truth_product_id']}` | `{r['predicted_top1_product_id']}` | {r['top1_similarity']:.4f} | {r['notes']} |"
        )

    if len(failed_top5) > 15:
        lines.append(f"\n*... and {len(failed_top5) - 15} additional failed queries logged in `evaluation/results.csv`.*")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Key Failure Mode Insights",
        "",
        "1. **Primary Vulnerabilities:** Analyze which failure conditions yielded the lowest Top-1 and Top-5 retrieval rates.",
        "2. **Similarity Distribution:** Assess whether failed queries were properly rejected with `UNKNOWN` or falsely matched to wrong products.",
        "3. **Target for Phase 9 Improvement:** Identify the single biggest failure category to address in Phase 9 experiments.",
        "",
    ])

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate baseline matcher on Stumper dataset.")
    parser.add_argument("--stumper-csv", type=Path, default=STUMPER_CSV)
    parser.add_argument("--results-csv", type=Path, default=RESULTS_CSV)
    parser.add_argument("--metrics-json", type=Path, default=METRICS_JSON)
    parser.add_argument("--analysis-md", type=Path, default=ANALYSIS_MD)
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    args = parser.parse_args()

    evaluate_matcher(
        stumper_csv_path=args.stumper_csv,
        results_csv_path=args.results_csv,
        metrics_json_path=args.metrics_json,
        analysis_md_path=args.analysis_md,
        threshold=args.threshold,
        top_k=args.top_k,
    )
