"""
scripts/evaluate_automated_stumper.py
──────────────────────────────────────
CLI Runner for Automated Stumper Evaluation.
Loads the 900 generated images, executes them against JewelleryMatcher,
prints comparative summary, and persists all metrics & comparison files.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.routes import get_matcher
from app.evaluation.automated_runner import (
    run_automated_evaluation,
    write_automated_results,
)


def main():
    print("=" * 75)
    print("  RUNNING AUTOMATED STUMPER EVALUATION BENCHMARK")
    print("=" * 75)
    
    # 1. Initialize production matcher (unchanged)
    print("Initializing production JewelleryMatcher...")
    matcher = get_matcher()
    print("Matcher ready. FAISS index size:", matcher.index.size)
    print("Decision threshold:", matcher.default_threshold)
    print("-" * 75)

    # 2. Run evaluation
    report = run_automated_evaluation(matcher)
    metrics = report["metrics"]
    comp = report["comparison"]

    # 3. Persist outputs
    write_automated_results(report)

    # 4. Print Comparative Table
    print("\n" + "=" * 75)
    print("  BENCHMARK RESULTS: HAND-SHOT vs AUTOMATED STUMPER")
    print("=" * 75)
    print(f"{'Metric':<25} | {'Hand-Shot (111)':<18} | {'Automated (900)':<18} | {'Delta':<10}")
    print("-" * 75)

    hs = comp["handshot"]
    au = comp["automated"]
    dl = comp["delta"]

    print(f"{'Top-1 Accuracy':<25} | {hs['top1_accuracy']*100:>16.2f}% | {au['top1_accuracy']*100:>16.2f}% | {dl['top1_pct']:>+8.2f}%")
    print(f"{'Top-5 Accuracy':<25} | {hs['top5_accuracy']*100:>16.2f}% | {au['top5_accuracy']*100:>16.2f}% | {dl['top5_pct']:>+8.2f}%")
    print(f"{'Failure Rate':<25} | {hs['failure_rate']*100:>16.2f}% | {au['failure_rate']*100:>16.2f}% | {dl['failure_rate_pct']:>+8.2f}%")
    print(f"{'UNKNOWN Verdicts':<25} | {hs['unknown_count']:>11} ({hs['unknown_rate']*100:.1f}%) | {au['unknown_count']:>11} ({au['unknown_rate']*100:.1f}%) |")
    print(f"{'Median Latency (ms)':<25} | {hs['median_latency_ms']:>16.2f}ms | {au['median_latency_ms']:>16.2f}ms |")
    print(f"{'P95 Latency (ms)':<25} | {hs['p95_latency_ms']:>16.2f}ms | {au['p95_latency_ms']:>16.2f}ms |")
    print("-" * 75)
    print(f"Product-ID Retrieval Top-1: {au.get('top1_product_accuracy', 0)*100:.2f}%")
    print(f"Product-ID Retrieval Top-5: {au.get('top5_product_accuracy', 0)*100:.2f}%")
    print("-" * 75)
    print("Verdict:")
    print(" ", comp["summary"])
    print("=" * 75)

    # 5. Print Condition Breakdown
    print("\nPER-CONDITION BREAKDOWN (AUTOMATED STUMPER):")
    print(f"{'Condition':<18} | {'Total':<6} | {'Top-1 Acc':<10} | {'Top-5 Acc':<10} | {'Product Top-1':<13} | {'Failures':<8}")
    print("-" * 75)
    for cond, cd in metrics["per_condition"].items():
        print(f"{cond:<18} | {cd['total']:<6} | {cd['top1_accuracy']*100:>8.1f}% | {cd['top5_accuracy']*100:>8.1f}% | {cd['top1_product_accuracy']*100:>11.1f}% | {cd['wrong_matches_count'] + cd['unknown_count']:<8}")
    print("=" * 75)


if __name__ == "__main__":
    main()
