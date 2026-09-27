# Evaluation Benchmarks & Datasets (`evaluation/`)

This directory contains evaluation datasets, test images, ground-truth annotations, benchmark scripts, and metric reports evaluating the robustness of the **Thuli Jewellery Retrieval Engine** under real-world physical variations.

---

## Directory Structure

```
evaluation/
├── images/                     # 115 real-world handheld test images
├── automated_images/           # 900 synthetic test images (100 items × 9 conditions)
├── multi_item_images/          # 25 multi-jewellery composite images (2-3 items/photo)
├── unseen_images/              # 24 unseen items for open-set evaluation
├── stumper.csv                 # Ground-truth annotations for real-world images (115 rows)
├── automated_stumper.csv       # Ground-truth annotations for automated tests (900 rows)
├── multi_item_eval.csv         # Ground-truth annotations for multi-item test images
├── unseen_stumper.csv          # Ground-truth annotations for unseen items
├── results.csv                 # Latest inference results for 115 real-world images
├── metrics.json                # Latest aggregated metrics (Top-1, Top-5, FAR, FRR, Latency)
├── automated_results.csv       # Detailed results for 900 automated benchmark queries
├── automated_metrics.json      # Aggregated metrics for automated benchmark
├── automated_comparison.json   # Direct side-by-side delta: Handshot vs. Automated
├── run_multi_item_eval.py      # Automated evaluator for SAM multi-item detection
├── analysis.md                 # Root-cause failure mode analysis and breakdown
└── final_analysis.md           # Comprehensive evaluation report & methodology analysis
```

---

## Benchmark Suites

### 1. Real-World "Stumper" Evaluation (115 Images)
Evaluates real camera captures under severe physical conditions:
- **Conditions evaluated:** Handheld palm view (`hand`), extreme clutter (`clutter`), motion blur (`motionblur`), bad lighting (`bad_lighting`), odd perspectives (`odd_angle`).
- **Ground Truth Mapping:** `evaluation/stumper.csv` maps each `image_id` (e.g. `id01`, `id02`) to ground-truth `product_id` and `failure_condition`.
- **Primary Metrics:**
  - **Top-1 Accuracy:** Exact primary candidate match ($> 72\%$).
  - **Top-5 Accuracy:** Ground truth found in top 5 candidates ($> 89\%$).
  - **False Acceptance Rate (FAR):** System accepted a match with the wrong product.
  - **False Rejection Rate (FRR):** Genuine catalogue item rejected as `UNKNOWN`.
  - **Latency:** P50 ($< 90 \text{ ms}$), P95 ($< 130 \text{ ms}$).

### 2. Automated Stumper Benchmark (900 Images)
Systematically tests the production matcher across **100 source items** with **9 programmatically applied physical perturbations**:
1. `bad_lighting`: Low-light attenuation ($\gamma = 2.2$).
2. `bright_lighting`: Over-exposure / specular blowout.
3. `odd_angle`: Perspective tilt and rotation ($\pm 35^\circ$).
4. `occlusion`: 30–50% synthetic mask obstruction.
5. `clutter`: Random object overlays and busy backgrounds.
6. `motion_blur`: Linear directional motion blur ($15 \text{ px}$).
7. `reflection`: High-intensity specular flare simulation.
8. `distance`: Downscaled object with empty boundary padding.
9. `noise`: Gaussian additive sensor noise ($\sigma = 35$).

### 3. Multi-Item Benchmark (`multi_item_eval.csv`)
Tests FastSAM segmentation when 2 to 3 jewellery pieces are photographed together in the same frame (e.g. bracelet + ring + earrings).
- Evaluates recall, precision, and segment-to-catalogue matching accuracy.

---

## How to Run Evaluations

```bash
# 1. Run Baseline Evaluation (115 real-world images)
python -m app.evaluation.runner

# 2. Run Automated Stumper Benchmark (900 synthetic tests)
python -m scripts.evaluate_automated_stumper

# 3. Run Multi-Item Evaluation (SAM segmentation)
python evaluation/run_multi_item_eval.py
```
