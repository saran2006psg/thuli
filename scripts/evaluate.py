"""
scripts/evaluate.py
────────────────────
Phase 7 — Baseline Evaluation Engine.

Runs the production JewelleryMatcher against every image in
evaluation/stumper.csv, computes Top-1 / Top-5 accuracy, per-condition
breakdowns, latency stats, and writes:
  - evaluation/results.csv
  - evaluation/metrics.json
  - evaluation/analysis.md

Usage:
    python scripts/evaluate.py [--stumper-csv PATH] [--threshold 0.75] [--top-k 5]
"""

import argparse
import csv
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (
    CATALOGUE_CSV,
    ENCODER_MODEL,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.retrieval.matcher import JewelleryMatcher

STUMPER_CSV   = PROJECT_ROOT / "evaluation" / "stumper.csv"
RESULTS_CSV   = PROJECT_ROOT / "evaluation" / "results.csv"
METRICS_JSON  = PROJECT_ROOT / "evaluation" / "metrics.json"
ANALYSIS_MD   = PROJECT_ROOT / "evaluation" / "analysis.md"


# ── helpers ───────────────────────────────────────────────────────────────────

def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = (pct / 100) * (len(sorted_v) - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_v):
        return sorted_v[lo]
    return sorted_v[lo] + (idx - lo) * (sorted_v[hi] - sorted_v[lo])


def _load_stumper_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("image_id")]


def _find_correct_rank(results: List[Dict], ground_truth: str) -> Optional[int]:
    """Return 1-based rank of ground_truth in results, or None if absent."""
    for item in results:
        if item.get("product_id") == ground_truth:
            return item["rank"]
    return None


def _compute_overall(rows: List[Dict]) -> Dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {}

    latencies       = [r["latency_ms"] for r in rows]
    top1_correct    = sum(1 for r in rows if r["correct_rank"] == 1)
    top5_correct    = sum(1 for r in rows if r["correct_rank"] is not None)
    match_count     = sum(1 for r in rows if r["decision"] == "MATCH")
    unknown_count   = sum(1 for r in rows if r["decision"] == "UNKNOWN")

    rank_dist: Dict[str, int] = {"rank_1": 0, "rank_2": 0, "rank_3": 0, "rank_4": 0, "rank_5": 0, "not_in_top5": 0}
    for r in rows:
        cr = r["correct_rank"]
        if cr is None:
            rank_dist["not_in_top5"] += 1
        else:
            rank_dist[f"rank_{cr}"] = rank_dist.get(f"rank_{cr}", 0) + 1

    return {
        "total_images":             n,
        "top1_correct_count":       top1_correct,
        "top5_correct_count":       top5_correct,
        "top1_accuracy_percent":    round(top1_correct / n * 100, 2),
        "top5_accuracy_percent":    round(top5_correct / n * 100, 2),
        "match_decision_count":     match_count,
        "unknown_decision_count":   unknown_count,
        "mean_latency_ms":          round(float(np.mean(latencies)), 3),
        "median_latency_ms":        round(float(np.median(latencies)), 3),
        "p95_latency_ms":           round(_percentile(latencies, 95), 3),
        "correct_rank_distribution": rank_dist,
    }


def _compute_conditions(rows: List[Dict]) -> Dict[str, Any]:
    groups: Dict[str, List[Dict]] = defaultdict(list)
    for r in rows:
        groups[r["failure_condition"]].append(r)

    breakdown: Dict[str, Any] = {}
    for cond, items in sorted(groups.items()):
        n = len(items)
        lats = [i["latency_ms"] for i in items]
        sims = [i["top1_similarity"] for i in items]
        top1 = sum(1 for i in items if i["correct_rank"] == 1)
        top5 = sum(1 for i in items if i["correct_rank"] is not None)
        breakdown[cond] = {
            "total_queries":       n,
            "top1_correct":        top1,
            "top5_correct":        top5,
            "top1_accuracy_pct":   round(top1 / n * 100, 2),
            "top5_accuracy_pct":   round(top5 / n * 100, 2),
            "mean_similarity":     round(float(np.mean(sims)), 4),
            "mean_latency_ms":     round(float(np.mean(lats)), 3),
            "match_count":         sum(1 for i in items if i["decision"] == "MATCH"),
            "unknown_count":       sum(1 for i in items if i["decision"] == "UNKNOWN"),
        }
    return breakdown


def _write_results_csv(rows: List[Dict], path: Path) -> None:
    fieldnames = [
        "image_id", "ground_truth", "predicted_top1_product_id",
        "top5_product_ids", "top1_similarity", "decision",
        "failure_condition", "correct_rank", "latency_ms",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "image_id":                r["image_id"],
                "ground_truth":            r["ground_truth"],
                "predicted_top1_product_id": r["predicted_top1"],
                "top5_product_ids":        "|".join(r["top5"]),
                "top1_similarity":         r["top1_similarity"],
                "decision":                r["decision"],
                "failure_condition":       r["failure_condition"],
                "correct_rank":            r["correct_rank"] if r["correct_rank"] is not None else "",
                "latency_ms":              r["latency_ms"],
            })


def _write_analysis_md(rows: List[Dict], overall: Dict, cond_breakdown: Dict, path: Path) -> None:
    n = overall.get("total_images", 0)
    lines = []
    lines.append("# Phase 7 — Baseline Evaluation Analysis\n")
    lines.append("_Auto-generated by scripts/evaluate.py. Do not edit manually._\n")
    lines.append("")
    lines.append("## Overall Results\n")
    lines.append(f"- **Total images evaluated:** {n}")
    lines.append(f"- **Top-1 Accuracy:** {overall.get('top1_accuracy_percent', 0):.2f}%  ({overall.get('top1_correct_count')}/{n} correct)")
    lines.append(f"- **Top-5 Accuracy:** {overall.get('top5_accuracy_percent', 0):.2f}%  ({overall.get('top5_correct_count')}/{n} correct)")
    lines.append(f"- **MATCH decisions:** {overall.get('match_decision_count')} / {n}")
    lines.append(f"- **UNKNOWN decisions:** {overall.get('unknown_decision_count')} / {n}")
    lines.append(f"- **Mean latency:** {overall.get('mean_latency_ms'):.1f} ms")
    lines.append(f"- **Median latency:** {overall.get('median_latency_ms'):.1f} ms")
    lines.append(f"- **P95 latency:** {overall.get('p95_latency_ms'):.1f} ms")
    lines.append("")

    lines.append("## Breakdown by Failure Condition\n")
    lines.append("| Condition | Images | Top-1 | Top-5 | Avg Sim | Avg Latency |")
    lines.append("|-----------|--------|-------|-------|---------|-------------|")
    for cond, cd in sorted(cond_breakdown.items()):
        lines.append(f"| {cond} | {cd['total_queries']} | {cd['top1_accuracy_pct']:.0f}% | {cd['top5_accuracy_pct']:.0f}% | {cd['mean_similarity']:.3f} | {cd['mean_latency_ms']:.0f} ms |")
    lines.append("")

    lines.append("## Rank Distribution\n")
    rd = overall.get("correct_rank_distribution", {})
    for k, v in rd.items():
        pct = round(v / n * 100, 1) if n else 0
        lines.append(f"- **{k.replace('_', ' ').title()}:** {v} ({pct}%)")
    lines.append("")

    # Failures
    failed = [r for r in rows if r["correct_rank"] != 1]
    lines.append(f"## Top Failure Cases ({len(failed)} images)\n")
    if failed:
        lines.append("| image_id | condition | ground_truth | predicted | similarity | rank | decision |")
        lines.append("|----------|-----------|--------------|-----------|------------|------|----------|")
        failed_sorted = sorted(failed, key=lambda r: r["top1_similarity"])
        for r in failed_sorted[:20]:
            rank_str = str(r["correct_rank"]) if r["correct_rank"] else "—"
            lines.append(f"| {r['image_id']} | {r['failure_condition']} | {r['ground_truth']} | {r['predicted_top1']} | {r['top1_similarity']:.3f} | {rank_str} | {r['decision']} |")
    lines.append("")

    # Observed patterns
    lines.append("## Observed Failure Patterns\n")
    worst_conds = sorted(cond_breakdown.items(), key=lambda x: x[1]["top1_accuracy_pct"])
    if worst_conds:
        lines.append(f"- **Hardest condition:** {worst_conds[0][0]} ({worst_conds[0][1]['top1_accuracy_pct']:.0f}% Top-1 accuracy)")
    unknown_heavy = [(c, d) for c, d in cond_breakdown.items() if d["unknown_count"] > 0]
    if unknown_heavy:
        unk_sorted = sorted(unknown_heavy, key=lambda x: x[1]["unknown_count"], reverse=True)
        lines.append(f"- **Most UNKNOWN decisions:** {unk_sorted[0][0]} ({unk_sorted[0][1]['unknown_count']} UNKNOWN)")
    low_sim = [r for r in rows if r["top1_similarity"] < 0.60]
    if low_sim:
        lines.append(f"- **{len(low_sim)} images** scored below 0.60 similarity — embeddings dominated by background/noise.")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


# ── main entry point ──────────────────────────────────────────────────────────

def evaluate_matcher(
    stumper_csv_path: Path = STUMPER_CSV,
    results_csv_path: Path = RESULTS_CSV,
    metrics_json_path: Path = METRICS_JSON,
    analysis_md_path: Path = ANALYSIS_MD,
    threshold: float = SIMILARITY_THRESHOLD,
    top_k: int = TOP_K,
    matcher: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Core evaluation function.  Can receive an injected matcher (for tests) or
    will instantiate the production JewelleryMatcher automatically.
    """
    stumper_rows = _load_stumper_csv(stumper_csv_path)
    if not stumper_rows:
        print("[WARN] No entries found in stumper.csv.")
        return {}

    if matcher is None:
        print("Loading production JewelleryMatcher …")
        matcher = JewelleryMatcher(
            index_path=FAISS_INDEX_PATH,
            product_ids_path=PRODUCT_IDS_PATH,
            catalogue_csv_path=CATALOGUE_CSV,
            threshold=threshold,
            top_k=top_k,
        )
        print(f"  Index size: {matcher.index.size:,}  |  Threshold: {threshold}")

    rows_out: List[Dict] = []
    total = len(stumper_rows)

    for i, row in enumerate(stumper_rows, 1):
        img_id     = row["image_id"].strip()
        ground_truth = row["product_id"].strip()
        condition  = row.get("failure_condition", "").strip()
        img_path   = Path(row["image_path"].strip())

        print(f"  [{i:02d}/{total}] {img_id}  ({condition})", end="  ", flush=True)

        if not img_path.exists():
            print(f"SKIP — file not found: {img_path}")
            continue

        t0 = time.perf_counter()
        try:
            result = matcher.match(image_input=img_path, top_k=top_k, threshold=threshold)
        except Exception as e:
            print(f"ERROR — {e}")
            continue
        latency_ms = (time.perf_counter() - t0) * 1000.0

        results_list = result.get("results", [])
        predicted_top1 = results_list[0]["product_id"] if results_list else ""
        top5_ids   = [r["product_id"] for r in results_list]
        top1_sim   = result.get("best_similarity", 0.0)
        decision   = result.get("decision", "UNKNOWN")
        correct_rank = _find_correct_rank(results_list, ground_truth)

        status_str = "✓ TOP-1" if correct_rank == 1 else (f"rank-{correct_rank}" if correct_rank else "✗ MISS")
        print(f"{status_str}  sim={top1_sim:.3f}  {decision}  {latency_ms:.0f}ms")

        rows_out.append({
            "image_id":        img_id,
            "ground_truth":    ground_truth,
            "predicted_top1":  predicted_top1,
            "top5":            top5_ids,
            "top1_similarity": round(top1_sim, 4),
            "decision":        decision,
            "failure_condition": condition,
            "correct_rank":    correct_rank,
            "latency_ms":      round(latency_ms, 2),
        })

    overall        = _compute_overall(rows_out)
    cond_breakdown = _compute_conditions(rows_out)

    metrics = {
        "overall_accuracy": overall,
        "condition_breakdown": cond_breakdown,
        "threshold_used": threshold,
        "top_k_used": top_k,
    }

    # Write outputs
    _write_results_csv(rows_out, results_csv_path)
    metrics_json_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_json_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _write_analysis_md(rows_out, overall, cond_breakdown, analysis_md_path)

    print("\n" + "=" * 60)
    print(f"  Total evaluated : {overall.get('total_images', 0)}")
    print(f"  Top-1 accuracy  : {overall.get('top1_accuracy_percent', 0):.2f}%")
    print(f"  Top-5 accuracy  : {overall.get('top5_accuracy_percent', 0):.2f}%")
    print(f"  MATCH / UNKNOWN : {overall.get('match_decision_count')} / {overall.get('unknown_decision_count')}")
    print(f"  Median latency  : {overall.get('median_latency_ms', 0):.1f} ms")
    print(f"  P95 latency     : {overall.get('p95_latency_ms', 0):.1f} ms")
    print("=" * 60)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 7 — Baseline Evaluation")
    parser.add_argument("--stumper-csv",  type=Path, default=STUMPER_CSV)
    parser.add_argument("--results-csv",  type=Path, default=RESULTS_CSV)
    parser.add_argument("--metrics-json", type=Path, default=METRICS_JSON)
    parser.add_argument("--analysis-md",  type=Path, default=ANALYSIS_MD)
    parser.add_argument("--threshold",    type=float, default=SIMILARITY_THRESHOLD)
    parser.add_argument("--top-k",        type=int,   default=TOP_K)
    args = parser.parse_args()

    evaluate_matcher(
        stumper_csv_path=args.stumper_csv,
        results_csv_path=args.results_csv,
        metrics_json_path=args.metrics_json,
        analysis_md_path=args.analysis_md,
        threshold=args.threshold,
        top_k=args.top_k,
    )
