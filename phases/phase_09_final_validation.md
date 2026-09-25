# Phase 9 — Final Validation

## 1. Overview and Objectives

Phase 9 delivers the definitive comparative benchmark for the **Thuli Jewellery Retrieval Engine**, evaluating the **Baseline JewelleryMatcher** against the **Phase 8 Improved (Saliency-Cropping) Matcher**.

The primary objective is to prove empirically whether the Phase 8 improvement improves retrieval accuracy and generalizability without regressions, using:
1. The **exact same 39 stumper dataset images** covering 10 real-world capture conditions.
2. An independent **24-image unseen holdout test set** covering 4 categories and simulated optical perturbations.

---

## 2. Experimental Setup

Both systems operated under identical retrieval parameters:
- **Index**: 6,165 catalogue vectors in FAISS `IndexFlatIP` (512-d).
- **Vision Model**: `openai/clip-vit-base-patch32`.
- **Match Threshold**: $\tau = 0.75$.
- **Strict Decision Rule**: Any prediction with cosine similarity $< 0.75$ results in an `UNKNOWN` decision and is strictly scored as an incorrect retrieval ($0$).

```
                      ┌───────────────────────────────┐
                      │ 39 Stumper + 24 Unseen Images │
                      └──────────────┬────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
       ┌───────────────────────────┐   ┌───────────────────────────┐
       │   Baseline Matcher        │   │   Phase 8 Improved        │
       │   (Standard 224x224 RGB)  │   │   (Saliency Cropping)     │
       └─────────────┬─────────────┘   └─────────────┬─────────────┘
                     ▼                               ▼
       ┌───────────────────────────────────────────────────────────┐
       │              evaluation/final_comparison.csv              │
       │              evaluation/final_metrics.json                │
       └───────────────────────────────────────────────────────────┘
```

---

## 3. Measured Results & Side-by-Side Comparison

### A. Primary Stumper Dataset (39 Images)

| Metric | Baseline | Improved | Difference |
|---|---|---|---|
| **Top-1 Accuracy** | **64.10%** (25/39) | **41.03%** (16/39) | **-23.07%** |
| **Top-5 Accuracy** | **76.92%** (30/39) | **69.23%** (27/39) | **-7.69%** |
| **MATCH Count ($\ge 0.75$)** | **34** | 33 | -1 |
| **UNKNOWN Count ($< 0.75$)** | **5** | 6 | +1 |
| **Median Latency** | **70.60 ms** | 72.31 ms | +1.71 ms |
| **P95 Latency** | **98.71 ms** | 99.57 ms | +0.86 ms |

---

### B. Per-Condition Accuracy (All 10 Conditions)

| Condition | Cases | Base Top-1 | Imp Top-1 | Base Top-5 | Imp Top-5 | Note |
|---|---|---|---|---|---|---|
| **Normal** | 4 | **100.0%** | 100.0% | 100.0% | 100.0% | Retained |
| **Bad Lighting** | 5 | **40.0%** | 40.0% | 60.0% | **80.0%** | +20% Top-5 |
| **Bright Lighting** | 3 | **100.0%** | 100.0% | 100.0% | 100.0% | Retained |
| **Odd Angle** | 3 | **100.0%** | 33.3% | 100.0% | 100.0% | -66.7% Top-1 |
| **Occlusion** | 3 | **33.3%** | 0.0% | 66.7% | 33.3% | -33.3% Top-1 |
| **Clutter** | 6 | **50.0%** | 16.7% | 50.0% | **66.7%** | -33.3% Top-1 |
| **Motion Blur** | 6 | **50.0%** | 33.3% | 83.3% | 33.3% | -16.7% Top-1 |
| **Reflection** | 1 | **100.0%** | 0.0% | 100.0% | 0.0% | -100.0% Top-1 |
| **Hand / Wrist** | 4 | **100.0%** | 50.0% | 100.0% | 100.0% | -50.0% Top-1 |
| **Distance** | 3 | **33.3%** | 33.3% | 66.7% | 66.7% | Neutral ($id14$ $+6.4\%$ sim) |

---

### C. Unseen Holdout Generalization Benchmark (24 Images)

| Metric | Baseline | Improved | Difference |
|---|---|---|---|
| **Top-1 Accuracy** | **95.83%** (23/24) | **75.00%** (18/24) | **-20.83%** |
| **Top-5 Accuracy** | **95.83%** (23/24) | **79.17%** (19/24) | **-16.66%** |
| **Median Latency** | **77.07 ms** | 69.70 ms | -7.37 ms |

---

## 4. Evaluation Findings

1. **Top-1 Accuracy Decreased**: Dropped by $-23.07\%$ on known stumpers and $-20.83\%$ on unseen holdout queries.
2. **Top-5 Accuracy Decreased**: Dropped by $-7.69\%$ on known stumpers and $-16.66\%$ on unseen holdout queries.
3. **Specific Improvements**: Compact rings (`id14`, `id04`, `id09`) experienced significant cosine similarity boosts ($+5.5\%$ to $+12.9\%$), converting sub-threshold rejections into valid matches.
4. **Specific Regressions**: Loop jewellery (bracelets and necklaces) experienced catastrophic fragmentation when cropped by single-contour saliency, misidentifying chain segments as rings or earrings.
5. **Generalization Failed**: On the unseen dataset, the baseline proved significantly more robust ($95.83\%$ vs $75.00\%$).
6. **Latency Maintained**: Latency remained within SLA ($70.60\text{ ms}$ baseline vs $72.31\text{ ms}$ improved).

---

## 5. Final Production Verdict

### **Decision: REJECT the Improvement — Retain Baseline as Production System**

The Baseline JewelleryMatcher achieves superior general retrieval accuracy ($64.10\%$ stumper Top-1, $95.83\%$ holdout Top-1) and remains the final system in `app/retrieval/`. All experimental code remains archived in `experiments/experiment_01/` for future reference.
