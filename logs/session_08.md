# Session Log 08 — Phase 8: Error Analysis & Improvement Experiment

**Date:** 2026-09-25  
**Focus:** Error Analysis on Baseline Failures, Experiment 01 (Saliency Object Cropping), Empirical Comparison, and Production Decision  
**Status:** Completed & Tested (67/67 tests passing, Decision: REJECT Experiment 01, Baseline Intact)

---

## 1. Objectives
1. Perform quantitative and qualitative error analysis on all 14 baseline failure cases from `evaluation/results.csv`.
2. Identify the primary failure modes (clutter, distance, sub-threshold rejections).
3. Design and implement ONE empirical improvement in an isolated sandbox (`experiments/experiment_01/`) without mutating the baseline architecture.
4. Benchmark the improvement against the exact 39 stumper dataset images.
5. Compare Top-1 accuracy, Top-5 accuracy, Median latency, P95 latency, and per-condition breakdown.
6. Make a data-driven Keep/Reject decision based on empirical evidence.
7. Ensure all existing tests pass (`pytest tests/`).

---

## 2. Work Done & Implementation Details

### A. Failure Case Analysis
- Analyzed `evaluation/results.csv` (14 failures across 39 images, 64.10% baseline Top-1 accuracy).
- Identified that in 7 of 14 failure cases (`clutter`, `distance`, `occlusion`), the jewellery piece represented a small fraction of the frame, allowing background tokens to dominate the CLIP ViT-B/32 patch embeddings.
- In `id14` (distance ring) and `id09` (bad lighting ring), similarity was just below the 0.75 threshold (0.7438 and 0.7463), resulting in `UNKNOWN` misses.

### B. Experiment 01: Saliency-Aware Jewellery Object Cropping
- Implemented `experiments/experiment_01/cropper.py`:
  - Uses OpenCV Spectral Residual Saliency (`cv2.saliency.StaticSaliencySpectralResidual_create()`).
  - Applies Otsu thresholding + morphological filtering to detect the primary salient object.
  - Adds a 15% context margin.
  - Gracefully falls back to the full image if the detected box is degenerate (<4% or >95% area).
- Implemented `experiments/experiment_01/eval_experiment.py`:
  - Evaluates all 39 stumper images with the cropper enabled using the existing `JewelleryMatcher`.
  - Persists `results_exp01.csv` and `metrics_exp01.json`.

### C. Empirical Comparison

| Metric | Baseline (Phase 7) | Experiment 01 (Phase 8) | Change |
|---|---|---|---|
| **Top-1 Accuracy** | **64.10%** (25/39) | **41.03%** (16/39) | -23.07% |
| **Top-5 Accuracy** | **76.92%** (30/39) | **69.23%** (27/39) | -7.69% |
| **Median Latency** | **73.64 ms** | **111.53 ms** | +37.89 ms |
| **P95 Latency** | **95.87 ms** | **193.62 ms** | +97.75 ms |

### D. Key Insights & Keep/Reject Decision
- **Success on Isolated Compact Items**: For rings with distance or clutter (`id04`, `id09`, `id14`), cropping increased cosine similarity significantly (+5.5% to +12.9%), converting `UNKNOWN` misses to confirmed `MATCH` hits.
- **Degradation on Elongated/Loop Items**: For bracelets and necklaces (`id21`, `id24`, `id25`, `id26`, `id29`, `id30`, `id33`, `id35`), saliency thresholding broke the continuous loop geometry, causing CLIP to misidentify links as rings or earrings.
- **Decision**: **REJECT Experiment 01**. Baseline remains production standard.

---

## 3. Verification & Test Suite
- Executed `python -m pytest`:
  - **67 passed in 43.34s**
  - Confirmed 0 regressions across API, catalogue, embeddings, evaluation, index, and matcher modules.

---

## 4. Deliverables Created
1. `phases/phase_08_error_analysis.md`: Complete error analysis and experimental comparison report.
2. `experiments/experiment_01/cropper.py`: Saliency object cropper implementation.
3. `experiments/experiment_01/eval_experiment.py`: Benchmark evaluation runner.
4. `experiments/experiment_01/results_exp01.csv`: 39-image query results for Experiment 01.
5. `experiments/experiment_01/metrics_exp01.json`: Experiment 01 metrics JSON.
6. `logs/session_08.md`: This session log.
