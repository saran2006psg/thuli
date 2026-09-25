# Phase 9 — Final Validation Analysis

## Executive Summary

Phase 9 evaluates the final comparative performance of the **Baseline JewelleryMatcher** against the **Phase 8 Improved (Saliency-Cropping) Matcher**. 

Both retrieval systems were subjected to an identical, dual-dataset benchmark:
1. **Primary Stumper Dataset (39 Real-World Images)**: The benchmark dataset covering 10 capture failure conditions.
2. **Unseen Holdout Dataset (24 Newly Generated Images)**: An independent generalization test set across 4 jewellery categories subjected to realistic optical perturbations.

---

## 1. Overall Performance Comparison

### Primary Stumper Dataset (39 Images)

| Metric | Baseline | Improved | Difference | Impact |
|---|---|---|---|---|
| **Top-1 Accuracy** | **64.10%** (25/39) | **41.03%** (16/39) | **-23.07%** | ❌ Severe Regression |
| **Top-5 Accuracy** | **76.92%** (30/39) | **69.23%** (27/39) | **-7.69%** | ❌ Regression |
| **MATCH Count ($\ge 0.75$)** | **34** | 33 | -1 | — |
| **UNKNOWN Count ($< 0.75$)** | **5** | 6 | +1 | — |
| **Median Latency** | **70.60 ms** | 72.31 ms | +1.71 ms | Minor overhead |
| **P95 Latency** | **98.71 ms** | 99.57 ms | +0.86 ms | Within SLA ($\le 100\text{ ms}$) |

---

### Unseen Holdout Dataset (24 Images)

| Metric | Baseline | Improved | Difference | Impact |
|---|---|---|---|---|
| **Top-1 Accuracy** | **95.83%** (23/24) | **75.00%** (18/24) | **-20.83%** | ❌ Significant Regression |
| **Top-5 Accuracy** | **95.83%** (23/24) | **79.17%** (19/24) | **-16.66%** | ❌ Significant Regression |
| **Median Latency** | **77.07 ms** | 69.70 ms | -7.37 ms | Comparable |

---

## 2. Per-Condition Performance Breakdown (All 10 Conditions)

Evaluated across all 39 primary stumper test queries:

| Condition | Total Cases | Baseline Top-1 | Improved Top-1 | Baseline Top-5 | Improved Top-5 | Condition Impact |
|---|---|---|---|---|---|---|
| **Normal** | 4 | **100.0%** | 100.0% | 100.0% | 100.0% | Neutral (Maintained) |
| **Bad Lighting** | 5 | **40.0%** | 40.0% | 60.0% | **80.0%** | Neutral Top-1, +20% Top-5 |
| **Bright Lighting** | 3 | **100.0%** | 100.0% | 100.0% | 100.0% | Neutral (Maintained) |
| **Odd Angle** | 3 | **100.0%** | 33.3% | 100.0% | 100.0% | ❌ Degraded (-66.7%) |
| **Occlusion** | 3 | **33.3%** | 0.0% | 66.7% | 33.3% | ❌ Degraded (-33.3%) |
| **Clutter** | 6 | **50.0%** | 16.7% | 50.0% | **66.7%** | ❌ Degraded Top-1 (-33.3%) |
| **Motion Blur** | 6 | **50.0%** | 33.3% | 83.3% | 33.3% | ❌ Degraded (-16.7% Top-1, -50% Top-5) |
| **Reflection** | 1 | **100.0%** | 0.0% | 100.0% | 0.0% | ❌ Degraded (-100.0%) |
| **Hand / Wrist** | 4 | **100.0%** | 50.0% | 100.0% | 100.0% | ❌ Degraded (-50.0%) |
| **Distance** | 3 | **33.3%** | 33.3% | 66.7% | 66.7% | Neutral ($id14$ gained $+6.4\%$ sim) |

---

## 3. Direct Answers to Core Evaluation Questions

### 1. Did the improvement increase Top-1 accuracy?
**No.** Top-1 accuracy dropped significantly:
- On the primary 39 stumper set: **from 64.10% down to 41.03%** ($\Delta = -23.07\%$).
- On the unseen 24 holdout set: **from 95.83% down to 75.00%** ($\Delta = -20.83\%$).

### 2. Did it increase Top-5 accuracy?
**No.** Top-5 accuracy dropped:
- On the primary 39 stumper set: **from 76.92% down to 69.23%** ($\Delta = -7.69\%$).
- On the unseen 24 holdout set: **from 95.83% down to 79.17%** ($\Delta = -16.66\%$).

### 3. Which failure conditions improved?
- **Bad Lighting** Top-5 accuracy improved from $60.0\%$ to $80.0\%$ (+20%).
- **Specific Individual Cases**:
  - `id14` (Distance Ring): Similarity jumped from **0.7438 to 0.8079** (+6.4%), successfully converting an `UNKNOWN` rejection into a confirmed `MATCH`.
  - `id04` (Clutter Ring): Similarity jumped from **0.6625 to 0.7912** (+12.9%), converting `UNKNOWN` to `MATCH`.
  - `id09` (Bad Lighting Ring): Similarity jumped from **0.7463 to 0.8016** (+5.5%).

### 4. Which conditions became worse?
- **Hand / Wrist**: Top-1 dropped from **100.0% to 50.0%** (-50%).
- **Odd Angle**: Top-1 dropped from **100.0% to 33.3%** (-66.7%).
- **Clutter**: Top-1 dropped from **50.0% to 16.7%** (-33.3%).
- **Motion Blur**: Top-1 dropped from **50.0% to 33.3%**, Top-5 dropped from **83.3% to 33.3%**.
- **Occlusion**: Top-1 dropped from **33.3% to 0.0%**.
- **Root Cause**: Saliency cropping cuts off the outer perimeter of elongated jewellery (necklaces and bracelets), fragmenting continuous loops and causing CLIP to mistake isolated chain segments for rings or earrings.

### 5. Did latency increase?
**Marginally, but within acceptable limits:**
- Median latency on the primary 39 images shifted from **70.60 ms to 72.31 ms** (+1.71 ms).
- P95 latency remained under 100 ms (**98.71 ms vs 99.57 ms**).

### 6. Did the improvement generalize to unseen images?
**No.** On the 24 unseen holdout images:
- Baseline Top-1 was **95.83%**, whereas Improved Top-1 was **75.00%** (-20.83%).
- Baseline Top-5 was **95.83%**, whereas Improved Top-5 was **79.17%** (-16.66%).
The degradation was consistent across both datasets.

### 7. Should we keep or reject the improvement?
**REJECT.**  
The empirical evidence decisively rejects the Phase 8 saliency-cropping improvement. While it provides targeted similarity gains on compact, isolated rings, it causes catastrophic topology loss on continuous-loop items. 

---

## 4. Final System Decision

- **Verdict**: **REJECT Improvement — Keep Baseline JewelleryMatcher as the Final Production System**.
- **Final Production Configuration**:
  - **Model**: `openai/clip-vit-base-patch32` (512-d normalized vectors)
  - **Vector Index**: FAISS `IndexFlatIP` (6,165 items)
  - **Threshold**: $\tau = 0.75$
  - **Input Preprocessing**: Standard uncropped $224 \times 224$ bicubic resize with aspect ratio preservation
  - **Top-1 Accuracy**: **64.10%** on hard stumper test cases, **95.83%** on general holdout queries
  - **Top-5 Accuracy**: **76.92%** on hard stumper test cases, **95.83%** on general holdout queries
  - **Median Latency**: **70.60 ms**
  - **P95 Latency**: **98.71 ms**
