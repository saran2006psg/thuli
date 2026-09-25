# Session Log 09 — Phase 9: Final Validation & Comparative Benchmark

**Date:** 2026-09-25  
**Focus:** Final Validation of Baseline vs Phase 8 Improvement across Stumper (39 images) and Unseen Holdout (24 images)  
**Status:** Completed & Tested (Decision: REJECT Improvement, Baseline Retained as Production Standard)

---

## 1. Objectives
1. Perform fair, side-by-side comparative benchmarking of the **Baseline JewelleryMatcher** vs the **Phase 8 Saliency-Cropping Matcher**.
2. Measure Top-1 accuracy, Top-5 accuracy, MATCH/UNKNOWN counts, Median latency, and P95 latency on the exact 39 primary stumper images.
3. Measure per-condition performance across all 10 canonical failure conditions:
   `Normal`, `Bad Lighting`, `Bright Lighting`, `Odd Angle`, `Occlusion`, `Clutter`, `Motion Blur`, `Reflection`, `Hand/Wrist`, `Distance`.
4. Generate a 24-image unseen holdout test set (`evaluation/unseen_images/` & `evaluation/unseen_stumper.csv`) across all 4 categories with simulated optical capture conditions.
5. Benchmark both systems on the unseen holdout set to test generalizability.
6. Generate required comparison files:
   - `evaluation/final_comparison.csv`
   - `evaluation/final_metrics.json`
   - `evaluation/final_analysis.md`
   - `phases/phase_09_final_validation.md`
   - `logs/session_09.md`
7. Ensure all unit tests pass with `python -m pytest -q`.

---

## 2. Work Done & Execution Details

### A. Unseen Dataset Generation (`scripts/prepare_unseen_dataset.py`)
- Selected 24 unseen items from `data/catalogue.csv` (6 rings, 6 bracelets, 6 necklaces, 6 earrings).
- Applied realistic photometric/geometric transformations covering all 10 canonical failure conditions.
- Stored images in `evaluation/unseen_images/` and metadata in `evaluation/unseen_stumper.csv`.

### B. Final Validation Runner (`scripts/run_final_validation.py`)
- Evaluated both systems on:
  1. The 39 primary stumper queries.
  2. The 24 unseen holdout queries.
- Persisted per-query comparisons in `evaluation/final_comparison.csv`.
- Persisted JSON metrics summary in `evaluation/final_metrics.json`.

### C. Empirical Comparison Summary

#### 1. Primary Stumper Benchmark (39 Images)
- **Baseline Top-1**: **64.10%** | **Improved Top-1**: **41.03%** ($\Delta = -23.07\%$)
- **Baseline Top-5**: **76.92%** | **Improved Top-5**: **69.23%** ($\Delta = -7.69\%$)
- **Baseline MATCH / UNKNOWN**: **34 / 5** | **Improved**: **33 / 6**
- **Baseline Median Latency**: **70.60 ms** | **Improved**: **72.31 ms**
- **Baseline P95 Latency**: **98.71 ms** | **Improved**: **99.57 ms**

#### 2. Unseen Holdout Generalization Benchmark (24 Images)
- **Baseline Top-1**: **95.83%** | **Improved Top-1**: **75.00%** ($\Delta = -20.83\%$)
- **Baseline Top-5**: **95.83%** | **Improved Top-5**: **79.17%** ($\Delta = -16.66\%$)
- **Baseline Median Latency**: **77.07 ms** | **Improved**: **69.70 ms**

---

## 3. Core Questions Addressed in `evaluation/final_analysis.md`
- **Did the improvement increase Top-1 / Top-5 accuracy?** No, it degraded both significantly (-23% Top-1, -7.7% Top-5).
- **Which conditions improved?** Bad Lighting Top-5 gained +20%; compact rings like `id14`, `id04`, `id09` gained up to +12.9% similarity.
- **Which conditions degraded?** Hand/Wrist (-50%), Odd Angle (-66.7%), Clutter (-33.3%), Motion Blur (-16.7%), Occlusion (-33.3%). Loop jewellery topology was severed by saliency masks.
- **Did latency increase?** Marginally (+1.7 ms median), well within SLA.
- **Did it generalize?** No, unseen holdout Top-1 dropped from 95.83% to 75.00%.
- **Should we keep or reject?** **REJECT**. Baseline retained as production standard.

---

## 4. Test Suite Execution
- Added unit tests in `tests/test_evaluation.py` for final validation artifacts.
- Ran `python -m pytest -q`: All tests passed.
