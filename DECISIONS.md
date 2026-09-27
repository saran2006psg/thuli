# DECISIONS.md — PS2: Stump the Model (Jewellery Image Retrieval)

Record of every significant technical decision made during the project.
Each entry follows the format: **Context → Decision → Reason → Alternatives Rejected**.

---

## Phase 1 — Catalogue Setup

### D-001 · Data Source: HuggingFace `ashraq/fashion-product-images-small`

**Date:** 2026-09-23
**Status:** Active

**Context:**
Phase 1 requires ≥5,000 jewellery catalogue images from a public source. Options considered:
1. HuggingFace `ashraq/fashion-product-images-small` — 44k Myntra fashion products, includes jewellery subcategories, no credentials required.
2. Kaggle jewellery-specific datasets — requires API key, varying quality.
3. Web scraping (Amazon/Etsy) — no credentials, but rate limits, legal grey areas, non-reproducible.

**Decision:**
Use HuggingFace as primary source with Kaggle as optional fallback.
Filter to jewellery-related subcategories from the 44k fashion dataset.

**Reason:**
- Reproducible: pinned dataset name and split.
- No credentials for basic usage.
- `datasets` library streams efficiently without full download.
- Filtering by known keywords gives a clean jewellery-only subset.

**Alternatives rejected:**
- Web scraping: reproducibility risk; terms-of-service considerations.
- Kaggle-only: credentials barrier for clean-machine verification.

---

### D-002 · Image Format: JPEG at 95 quality

**Date:** 2026-09-23
**Status:** Active

**Context:**
Raw source images arrive as PIL Images (HF) or mixed formats (Kaggle).
Need a uniform format for downstream embedding generation.

**Decision:**
Convert and save all images as JPEG at quality=95.

**Reason:**
- Uniform format simplifies preprocessing pipeline.
- JPEG at 95 preserves visual quality with reasonable file size.
- PNG would double disk usage without benefit for embedding generation.

**Alternatives rejected:**
- PNG: larger files, no benefit for embedding tasks.
- WebP: lower library support on Windows without special builds.

---

### D-003 · Deduplication Strategy: Perceptual Hash (pHash)

**Date:** 2026-09-23
**Status:** Active

**Context:**
Fashion product datasets often contain near-identical product images (same item, slightly different crop/lighting). Exact file-hash deduplication would miss these.

**Decision:**
Use `imagehash.phash()` for near-duplicate detection. If `imagehash` is unavailable, fall back to MD5 of a 16×16 downsampled grayscale image.

**Reason:**
- pHash is robust to minor JPEG recompression and minor crop differences.
- Prevents two identical-looking products from appearing separately in the catalogue, which would inflate retrieval accuracy.

**Alternatives rejected:**
- MD5 exact hash: misses visually identical but byte-different images.
- No deduplication: risks inflated Top-5 accuracy from near-duplicates.

---

### D-004 · Product ID Scheme: `JW_NNNNNN`

**Date:** 2026-09-23
**Status:** Active

**Context:**
Source datasets use inconsistent ID schemes (numeric, alphanumeric, UUID-style).
Need a stable, human-readable ID for use as ground truth throughout the project.

**Decision:**
Reassign sequential IDs in format `JW_000001` … `JW_NNNNNN` during the cleaning step. Source ID is preserved in `source_url` field for traceability.

**Reason:**
- Human-readable and easily sortable.
- Stable — not affected by source dataset changes.
- Unique by construction.

**Alternatives rejected:**
- Preserving source IDs: inconsistent across different data sources.
- UUID: unnecessarily long, not human-readable.

---

---

## Phase 2 — Image Embedding

### D-005 · Vision Encoder: CLIP `openai/clip-vit-base-patch32`

**Date:** 2026-09-24
**Status:** Active

**Context:**
Need a vision backbone to extract dense visual representations from 6,157 jewellery images.
Candidates:
1. CLIP (`openai/clip-vit-base-patch32`) — 512-dim multimodal representation.
2. DINOv2 (`facebook/dinov2-base`) — 768-dim self-supervised representation.
3. ResNet50 (ImageNet-1k) — 2048-dim supervised classification features.

**Decision:**
Adopt CLIP ViT-B/32 as the baseline vision encoder.

**Reason:**
- Zero-shot visual semantic capability captures fine-grained attributes (metal finish, gemstone color, silhouette, gemstone cuts).
- Compact 512-dimensional output keeps memory usage low (~12 MB for 6,157 items) and enables ultra-fast retrieval (<2ms).
- Standard across visual retrieval benchmarks.

**Alternatives rejected:**
- ResNet50 ImageNet: overfits to 1,000 ImageNet categories, lacks fine-grained jewellery material perception.
- DINOv2-Large: higher latency and memory overhead on CPU for initial baseline.

---

### D-006 · Vector Normalization: Unit L2 Norm for Inner Product Cosine Equivalence

**Date:** 2026-09-24
**Status:** Active

**Context:**
Cosine similarity measures angular distance between embeddings independent of scale.

**Decision:**
Apply unit L2 normalization ($\|v\|_2 = 1.0$) immediately upon extraction.

**Reason:**
- For normalized vectors, cosine similarity $\cos(\theta) = u \cdot v$ equals inner product.
- Allows using `faiss.IndexFlatIP` (fastest exact inner-product search) without computing norms at query time.

---

## Phase 3 — FAISS Retrieval & Indexing

### D-007 · FAISS Index Type: `faiss.IndexFlatIP` (Exact Exhaustive Cosine Search)

**Date:** 2026-09-24
**Status:** Active

**Context:**
Need a vector retrieval layer to search 6,157 dense 512-dimensional embeddings.
Candidates considered:
1. `faiss.IndexFlatIP` (Flat Inner Product) — Exhaustive exact cosine similarity search.
2. `faiss.IndexIVFFlat` (Inverted File) — Partitioning-based approximate nearest neighbour search.
3. `faiss.IndexHNSWFlat` (Hierarchical Navigable Small World) — Graph-based approximate search.
4. `faiss.IndexPQ` (Product Quantization) — Compressed lossy vector search.

**Decision:**
Use `faiss.IndexFlatIP` as the retrieval index for the baseline system.

**Reason:**
- **Exact & Lossless:** Guarantees 100% recall with no approximation errors.
- **Inner Product = Cosine Similarity:** Embeddings are L2-normalized, making inner product strictly equivalent to cosine similarity.
- **Blazing Fast on Current Scale:** At $N = 6,157$, measured search latency is **0.5187 ms (median)** and **0.7350 ms (p95)** on CPU, comfortably below the $< 2\text{ ms}$ retrieval target.
- **Low Memory Footprint:** Index size is only 12.03 MB on disk and in RAM.

**Alternatives considered for future scaling:**
- `IndexIVFFlat` / `IndexHNSWFlat` / `IndexPQ`: Not rejected permanently, but deferred. If the catalogue scales to the optional 100k+ challenge dataset in later phases, an approximate indexing scheme (such as HNSW or IVF) will be evaluated and compared against this exact baseline.

---

---

## Phase 4 — Baseline Matcher Pipeline

### D-008 · Decision Rule: Geometric Cosine Similarity Match vs Unknown

**Date:** 2026-09-24
**Status:** Active

**Context:**
The matcher needs a clear decision rule to determine whether a query image depicts a known catalogue product (`MATCH`) or an out-of-catalogue/dissimilar object (`UNKNOWN`).

**Decision:**
Use the Top-1 inner-product score (cosine similarity $s \in [-1, 1]$) against a configurable decision threshold $\tau$:
$$\text{decision} = \begin{cases} \text{"MATCH"}, & \text{if } s_{\text{top1}} \ge \tau \\ \text{"UNKNOWN"}, & \text{if } s_{\text{top1}} < \tau \end{cases}$$

**Reason:**
- For unit L2-normalized embeddings, inner product represents exact cosine similarity.
- Directly measures visual angular proximity to the closest catalogue item.
- Preserves raw similarity metric without inventing uncalibrated probabilities.

---

### D-009 · Baseline Threshold Setting ($\tau = 0.75$)

**Date:** 2026-09-24
**Status:** Active (Temporary Baseline)

**Context:**
A default similarity threshold is required to run the baseline retrieval pipeline before stumper evaluation datasets are gathered.

**Decision:**
Adopt $\tau = 0.75$ as a clearly documented uncalibrated baseline setting, exposed via `.env` and runtime parameter overrides.

**Reason:**
- Allows full pipeline integration and testing before formal calibration.
- Full calibration of $\tau$ will be performed empirically on the 100+ stumper dataset and out-of-catalogue unknown sets in Phase 8 and Phase 10.

---

## Phase 5 — API Layer

### D-010 · FastAPI Architecture & Thread-Safe Lifespan Singleton

**Date:** 2026-09-25
**Status:** Active

**Context:**
The visual search API requires low-latency retrieval while preventing concurrent race conditions when dynamically adding new products or running evaluations. Loading CLIP ViT-B/32 on every HTTP request would incur 500ms+ overhead.

**Decision:**
Implement a thread-safe double-checked singleton lock for `JewelleryMatcher` in `app/api/routes.py` with an async pre-warming lifespan in `app/main.py`.

**Reason:**
- Keeps memory footprint lean (~12MB index + ~350MB model in RAM).
- Zero cold-start latency on `/api/match` (median query latency 70.60ms).
- Thread-safe mutation during live catalogue additions.

---

## Phase 7 & 8 — Evaluation & Error Analysis

### D-011 · Stumper Protocol & 10-Condition Taxonomy

**Date:** 2026-09-26
**Status:** Active

**Context:**
Academic image retrieval evaluations frequently rely on synthetic augmentations (Gaussian blur, color jitter), which fail to model the non-Lambertian reflections, sensor noise, hand occlusions, and perspective distortions of handheld consumer jewellery photography.

**Decision:**
Collect and curate 111 authentic smartphone photographs mapped directly to catalogue product IDs and classified across a strict 10-condition failure taxonomy (`normal`, `bad_lighting`, `bright_lighting`, `odd_angle`, `occlusion`, `clutter`, `motion_blur`, `reflection`, `hand_wrist`, `distance`).

**Reason:**
- Exposes true real-world retrieval performance (72.07% Top-1) vs synthetic inflation (94.67% Top-1).
- Provides granular per-condition attribution to guide diagnostic engineering.

---

### D-012 · Rejection of Saliency-Aware Cropping (The Honest 70% System)

**Date:** 2026-09-26
**Status:** Active (Definitive Rejection)

**Context:**
In Phase 8, error analysis showed that background clutter and distance caused token dilution in ViT patches. We built Experiment 01 (`experiments/experiment_01/cropper.py`) using Spectral Residual Saliency and Otsu thresholding to tightly crop the jewellery item before CLIP embedding.

**Decision:**
Strictly REJECT Experiment 01 and retain the uncropped baseline `JewelleryMatcher` as the production standard.

**Reason:**
- While cropping helped compact rings (+6.4% on `id14`, +12.9% on `id04`), it catastrophically fragmented continuous-loop items (necklaces and bracelets).
- Saliency severed thin chain perimeters, causing CLIP to misclassify isolated bracelet segments as rings/earrings.
- Empirical results showed severe degradation: Top-1 dropped from 64.10% to 41.03% on the stumper benchmark, and from 95.83% to 75.00% on unseen holdouts.
- Retaining a clean-eyed 70% baseline with known error bounds is vastly superior to adopting a fragile heuristic that breaks macro-geometry.

---

### D-013 · Decision Threshold Calibration ($\tau = 0.75$) with Sub-Threshold Penalty

**Date:** 2026-09-26
**Status:** Active

**Context:**
In luxury e-commerce and appraisal visual search, returning a confident wrong product ($200 silver ring instead of $4,500 diamond ring) is a critical failure. The system must reject ambiguous matches as `UNKNOWN`.

**Decision:**
Calibrate decision threshold to $\tau = 0.75$. Queries with similarity $< 0.75$ are strictly classified as `UNKNOWN` and counted as misses during evaluation, even if the top predicted ID matches ground truth.

**Reason:**
- Maintains a balanced False Acceptance Rate (20.72%) and False Rejection Rate (7.21%) on hard real-world stumpers.
- Prevents hallucinated matches for out-of-catalogue or severely degraded images.
- Enforces engineering honesty: high confidence is reserved for true visual matches.

---

### D-014 · Automated Adversarial Stumper Generation (Defeating Matcher at a Higher Rate)

**Date:** 2026-09-27
**Status:** Active

**Context:**
Academic benchmarks often simulate failure using naive digital augmentations (mild blur, minor contrast shifts). In early automated tests, the matcher achieved 94.67% accuracy, creating a false impression of robustness. To truly stress-test the model, we needed programmatic generators that challenge the matcher more severely than manual phone photography.

**Decision:**
Upgrade the automated stumper generator (`scripts/generate_automated_stumper.py`) to synthesize 9 physically grounded adversarial conditions:
1. Distance with severe scale reduction (18-28%) inducing ViT patch token dilution.
2. Direct central occlusion (35-50% area coverage) that severs closed loop silhouettes.
3. Multi-directional camera shake (35-53px kernels) destroying high-frequency prongs and facets.
4. Specular flash bloom (255 RGB blowout) obliterating center stones.
5. Oblique perspective foreshortening (45-75 degrees) with rotational distortion.
6. Non-linear low-light gamma collapse and shadow clipping.
7. High-entropy textured surface clutter (wood grain, cloth, distractor coins/keys).
8. Glass case double-reflections and specular glare streaks.
9. ISO 12800 chromatic noise and blocky JPEG quantization.

**Reason:**
- Empirically demonstrated that the automated generator **defeats the matcher at a higher rate** than the hand-shot benchmark:
  - Automated Failure Rate: **47.78%** vs Hand-Shot **27.43%** (+20.35% higher failure rate).
  - Automated Top-1 Accuracy: **52.22%** vs Hand-Shot **72.57%** (-20.35% drop).
  - Automated Top-5 Accuracy: **60.00%** vs Hand-Shot **89.38%** (-29.38% drop).
- Proves that automated programmatic testing can systematically expose architectural blindspots without human shooting bias.
