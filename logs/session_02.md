# Session 02 — Phase 2: Image Embedding

**Date:** 2026-09-24  
**Phase:** 2 — Image Embedding  
**Goal:** Extract L2-normalized dense embeddings for all 6,157 catalogue jewellery images using a pretrained vision backbone.

---

## What Was Done

### 1. Vision Model & Pipeline Architecture
- Selected **CLIP (`openai/clip-vit-base-patch32`)** as the baseline vision encoder (512-dimensional output).
- Implemented `JewelleryEncoder` in [`app/retrieval/encoder.py`](file:///d:/PL/thuli/app/retrieval/encoder.py) with batch inference support and L2-normalization ($\|v\|_2 = 1.0$).
- Configured model caching to the `D:` drive (`D:/.cache/huggingface` and `D:/.cache/torch`) to prevent disk space exhaustion on Windows `C:` drive.
- Resolved protobuf / tensorflow optional dependency conflicts by setting `USE_TF=0` and `USE_TORCH=1`.

### 2. Catalogue CSV & Embeddings Generation
- Generated [`data/catalogue.csv`](file:///d:/PL/thuli/data/catalogue.csv) containing **6,157 validated images**:
  - `bracelet`: 888 items
  - `earring`: 3,298 items
  - `necklace`: 1,738 items
  - `ring`: 233 items
- Executed batch embedding pipeline (`scripts/generate_embeddings.py`) across all 6,157 items.
- Saved generated artifacts:
  - `artifacts/embeddings/catalogue_embeddings.npy` (matrix shape: `6157 x 512`, dtype: `float32`)
  - `artifacts/embeddings/product_ids.json` (6,157 sequential product IDs `JW_000001` to `JW_006157`)

### 3. Verification & Automated Tests
- Created test suite in [`tests/test_embeddings.py`](file:///d:/PL/thuli/tests/test_embeddings.py).
- Ran all tests across Phase 1 and Phase 2:
  - `pytest tests/test_catalogue.py tests/test_embeddings.py -v` -> **19/19 PASSED (100%)**.

---

## Files Created / Modified

| File | Purpose |
|---|---|
| [`app/retrieval/encoder.py`](file:///d:/PL/thuli/app/retrieval/encoder.py) | CLIP vision encoder wrapper with batching & L2 normalization |
| [`scripts/generate_embeddings.py`](file:///d:/PL/thuli/scripts/generate_embeddings.py) | Batch extraction script for catalogue embeddings |
| [`scripts/build_catalogue_csv.py`](file:///d:/PL/thuli/scripts/build_catalogue_csv.py) | Builder for `data/catalogue.csv` from image folders |
| [`tests/test_embeddings.py`](file:///d:/PL/thuli/tests/test_embeddings.py) | Automated unit & artifact integrity tests |
| [`artifacts/embeddings/catalogue_embeddings.npy`](file:///d:/PL/thuli/artifacts/embeddings/catalogue_embeddings.npy) | Normalized matrix of 6,157 embeddings |
| [`artifacts/embeddings/product_ids.json`](file:///d:/PL/thuli/artifacts/embeddings/product_ids.json) | Product ID mapping array |
| [`DECISIONS.md`](file:///d:/PL/thuli/DECISIONS.md) | Documented decisions D-005 and D-006 |
| [`phases/phase_02_embedding.md`](file:///d:/PL/thuli/phases/phase_02_embedding.md) | Phase 2 specification |

---

## Next Steps

1. **Phase 3: FAISS Retrieval & Indexing**
   - Install `faiss-cpu`
   - Implement `app/retrieval/index.py` (build `IndexFlatIP`)
   - Implement `scripts/build_index.py`
   - Save `artifacts/indexes/catalogue.faiss`
   - Write tests in `tests/test_index.py`
