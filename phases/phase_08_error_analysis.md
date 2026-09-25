# Phase 8 — Error Analysis and Improvement

## 1. Executive Summary

Phase 8 executes empirical error analysis and an isolated algorithmic experiment on the **Thuli Jewellery Retrieval Engine**. 

Following the completion of the Phase 7 Baseline Evaluation on 39 real-world stumper images, we analyzed the root causes of all 14 baseline failure modes. We formulated an empirical hypothesis regarding foreground isolation and implemented **Experiment 01: Saliency-Aware Jewellery Object Cropping** in an isolated sandbox (`experiments/experiment_01/`) to preserve baseline integrity.

```
Baseline (64.1% Top-1) 
   ──► Failure Pattern Analysis (Clutter & Distance interference) 
   ──► Hypothesis (Saliency Cropping eliminates background tokens) 
   ──► Experiment 01 Implementation 
   ──► Benchmark on 39 Stumper Images (41.03% Top-1, 111.5 ms) 
   ──► Decision: REJECT Experiment 01 (Keep Baseline Untouched)
```

---

## 2. Baseline Performance Review (Phase 7)

- **Catalogue Size**: 6,165 items (512-dimensional CLIP ViT-B/32 embeddings indexed in FAISS `IndexFlatIP`)
- **Stumper Dataset**: 39 real-world test images covering 12 capture conditions
- **Match Threshold**: $\tau = 0.75$ (strict threshold enforcement: any score $< 0.75$ yields `UNKNOWN` and is counted as a miss)
- **Top-1 Accuracy**: **64.10%** (25 hits, 14 misses)
- **Top-5 Accuracy**: **76.92%** (30 hits, 9 misses)
- **Median Latency**: **73.64 ms**
- **P95 Latency**: **95.87 ms**

---

## 3. Baseline Failure Pattern Analysis

Analysis of `evaluation/results.csv` identified 14 failure cases categorized by capture condition:

| Condition | Total Test Cases | Failures | Failure Rate | Representative Images | Primary Failure Mode |
|---|---|---|---|---|---|
| **Clutter** | 6 | 3 | 50.0% | `id01`, `id04`, `id23` | Tabletop artifacts confuse global CLIP pooling |
| **Bad Lighting** | 5 | 3 | 60.0% | `id09`, `id10`, `id11` | Low dynamic range depresses similarity |
| **Motion Blur** | 6 | 3 | 50.0% | `id03`, `id08`, `id36` | Blurred loops make bracelets look like necklaces |
| **Distance** | 3 | 2 | 66.7% | `id14`, `id34` | Jewellery occupies $<15\%$ of frame; background dominates |
| **Occlusion** | 3 | 2 | 66.7% | `id18`, `id38` | Partial obscuration lowers similarity below 0.75 |
| **Noise** | 1 | 1 | 100.0% | `id05` | Sensor noise causes sub-threshold rejection ($0.7165$) |

### Key Failure Modes
1. **Distant & Small Framing**: In distance test cases (`id14`, `id34`), the item of interest represents a minor fraction of the camera frame. The $224 \times 224$ ViT patch tokens are dominated by desk, fabric, or hand surfaces.
2. **Sub-Threshold Rejections (`UNKNOWN`)**: In cases like `id14` (similarity $0.7438$), `id09` ($0.7463$), and `id05` ($0.7165$), the predicted class was correct, but background noise suppressed cosine similarity slightly below $\tau = 0.75$.

---

## 4. Experiment 01: Saliency-Aware Jewellery Object Cropping

### Hypothesis
> *If we automatically isolate and crop the salient jewellery item before passing it to CLIP ViT-B/32, extraneous background pixels (tables, fingers, distance padding) will be eliminated, boosting cosine similarity on distant and cluttered images and converting sub-threshold misses into confirmed matches.*

### Architecture & Implementation
- Located in `experiments/experiment_01/cropper.py`.
- Computes **Spectral Residual Saliency** (`cv2.saliency.StaticSaliencySpectralResidual_create()`).
- Applies Otsu thresholding and morphological closing to isolate the primary foreground object contour.
- Adds an adaptive $15\%$ padding margin for structural context.
- Falls back to the uncropped image if the detected region is degenerate ($<4\%$ or $>95\%$ of image area).
- Preserves the production `JewelleryMatcher` and FAISS index with zero baseline modifications.

---

## 5. Experimental Results & Direct Comparison

The 39 stumper images were run through `experiments/experiment_01/eval_experiment.py`.

### Overall System Benchmark

| Metric | Phase 7 Baseline | Phase 8 Experiment 01 | Delta ($\Delta$) | Status |
|---|---|---|---|---|
| **Top-1 Accuracy** | **64.10%** (25/39) | **41.03%** (16/39) | **-23.07%** | ❌ Severe Regression |
| **Top-5 Accuracy** | **76.92%** (30/39) | **69.23%** (27/39) | **-7.69%** | ❌ Regression |
| **MATCH Decisions** | 34 | 33 | -1 | — |
| **UNKNOWN Decisions** | 5 | 6 | +1 | — |
| **Median Latency** | **73.64 ms** | **111.53 ms** | **+37.89 ms** | ❌ +51.5% Latency |
| **P95 Latency** | **95.87 ms** | **193.62 ms** | **+97.75 ms** | ❌ +101.9% Latency |
| **Images Cropped** | 0 / 39 (0%) | 34 / 39 (87.2%) | — | — |

---

### Per-Condition Accuracy Comparison

| Condition | Test Cases | Baseline Top-1 | Exp 01 Top-1 | Baseline Top-5 | Exp 01 Top-5 | Impact |
|---|---|---|---|---|---|---|
| **Distance** | 3 | 33.3% | 33.3% | 100.0% | 66.7% | Neutral Top-1, lower Top-5 |
| **Clutter** | 6 | **50.0%** | 16.7% | 50.0% | 50.0% | ❌ Degraded |
| **Bad Lighting** | 5 | 40.0% | 40.0% | 80.0% | 80.0% | Neutral |
| **Hand / Wrist** | 3 | **100.0%** | 33.3% | 100.0% | 66.7% | ❌ Degraded |
| **Odd Angle** | 3 | **100.0%** | 33.3% | 100.0% | 66.7% | ❌ Degraded |
| **Occlusion** | 3 | **33.3%** | 0.0% | 66.7% | 66.7% | ❌ Degraded |
| **Motion Blur** | 6 | 50.0% | 33.3% | 66.7% | 50.0% | ❌ Degraded |
| **Normal** | 4 | **100.0%** | 100.0% | 100.0% | 100.0% | Preserved |
| **Bright Lighting** | 3 | **100.0%** | 100.0% | 100.0% | 100.0% | Preserved |

---

### Failure Breakdown & Forensic Analysis

#### Where the Improvement Succeeded (4 Cases):
1. **`id14` (Distance Ring)**: Similarity jumped from **0.7438 to 0.8079** (+6.4% gain), flipping verdict from `UNKNOWN` to `MATCH`.
2. **`id04` (Clutter Ring)**: Similarity jumped from **0.6625 to 0.7912** (+12.9% gain), flipping verdict from `UNKNOWN` to `MATCH`.
3. **`id09` (Bad Lighting Ring)**: Similarity jumped from **0.7463 to 0.8016** (+5.5% gain), converting miss to hit.
4. **`id36` (Motion Blur Necklace)**: Ground truth rank moved from #2 into Top-1.

#### Where the Improvement Failed (13 Cases):
- **Destruction of Global Topology in Loop Jewellery**: On elongated pieces (bracelets and necklaces like `id21`, `id24`, `id25`, `id26`, `id29`, `id30`, `id33`, `id35`), saliency thresholding split the continuous chain into disconnected fragments or tightly bounded a single gemstone/link.
- **Context Stripping**: Without the complete circular silhouette, CLIP ViT-B/32 mistook individual bracelet links for rings or earrings.
- **Latency Penalty**: Spectral residual computation + contour parsing added ~38 ms of median preprocessing overhead per image.

---

## 6. Engineering Decision: REJECT Experiment 01

| Criteria | Target | Result | Decision |
|---|---|---|---|
| **Top-1 Accuracy** | $> 64.1\%$ | $41.03\%$ | **FAIL** |
| **Top-5 Accuracy** | $\ge 76.92\%$ | $69.23\%$ | **FAIL** |
| **Latency** | $\le 100\text{ ms}$ | $111.5\text{ ms}$ | **FAIL** |
| **Baseline Integrity** | Zero regressions | Fully isolated | **PASS** |

### **Verdict: REJECT**
- **Experiment 01 is rejected** for production deployment.
- **Baseline implementation remains untouched** in `app/retrieval/` and `app/evaluation/`.
- Production system maintains **64.10% Top-1 accuracy**, **76.92% Top-5 accuracy**, and **73.64 ms median latency**.

---

## 7. Lessons Learned & Recommendations for Future Phases

1. **Category-Dependent Geometry**: Rings benefit significantly from tight cropping ($+6\%\text{ to }+13\%$ similarity boost), whereas necklaces and bracelets require full-frame topological context.
2. **Multi-Crop Ensembling**: Instead of replacing the full image with a single tight crop, a dual-embedding scheme (averaging full-frame embedding + center crop embedding) can preserve global context while boosting local detail.
3. **Dedicated Object Detection vs Saliency**: Saliency maps are prone to fragmentation on open-loop chains. A lightweight fine-tuned YOLO detector or bounding box model would prevent chain severance.
