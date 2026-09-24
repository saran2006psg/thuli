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

## Open Items

- [ ] **D-008** — Similarity threshold $\tau$ (Phase 4). Will be determined experimentally using validation data, not guessed.
- [ ] **D-009** — Confidence score formulation (Phase 4). Calibration of raw cosine similarity scores into match confidence.
