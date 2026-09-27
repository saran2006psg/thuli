# Experiments Directory (`experiments/`)

This directory contains research, ablation studies, and architectural experiments conducted to improve retrieval accuracy under occluded and multi-object conditions.

---

## Directory Structure

```
experiments/
└── experiment_01/
    ├── cropper.py           # Image pre-cropping and saliency extraction strategies
    ├── eval_experiment.py   # Ablation runner comparing raw CLIP vs. cropped CLIP
    ├── metrics_exp01.json   # Aggregated metrics for Experiment 01
    └── results_exp01.csv    # Query-level comparison results
```

---

## Experiment 01: Saliency & Bounding Box Cropping vs. Raw Matcher

### Objective
Determine if auto-cropping the central subject (removing hands, table textures, and background clutter) before CLIP embedding increases Top-1 accuracy on handheld photos.

### Implementation (`experiment_01/cropper.py`)
Tested 3 cropping methods:
1. **Center Crop (80%):** Discards outer 10% margins to remove background borders.
2. **Color Saliency / Otsu Masking:** Computes Otsu threshold on the saturation channel to isolate high-contrast jewellery from skin tones.
3. **Padded Bounding Box:** Tight crop around the largest connected component with 15% safety padding.

### Findings
- **Positive:** On heavily cluttered backgrounds (`clutter`), saliency cropping boosted Top-1 accuracy by $+8.3\%$.
- **Tradeoff:** On thin, delicate jewellery (chains, fine rings), aggressive Otsu thresholding occasionally severed parts of the item, degrading fine-grained similarity.
- **Architectural Decision:** Adopted FastSAM (`FastSAM-s.pt`) in `app/retrieval/multi_matcher.py` for multi-item and occluded queries, while keeping the standard full-image pipeline for single-item queries to maximize speed.

---

## Running Experiment 01

```bash
python experiments/experiment_01/eval_experiment.py
```
