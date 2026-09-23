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

## Open Items

- [ ] **D-005** — Vision encoder selection (Phase 2). CLIP vs ResNet50 vs DINOv2. Will be decided after baseline embedding quality is measured.
- [ ] **D-006** — FAISS index type (Phase 3). Start with `IndexFlatIP` (exact cosine), upgrade to `IndexIVFFlat` only if latency is unacceptable.
- [ ] **D-007** — Similarity threshold τ (Phase 4). Will be determined experimentally using validation data, not guessed.
