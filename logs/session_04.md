# Session 04 — Phase 4: Baseline Matcher Pipeline

**Date:** 2026-09-24  
**Phase:** 4 — Baseline Matcher Pipeline  
**Goal:** Build the complete end-to-end image matching pipeline connecting image preprocessing, CLIP feature extraction, FAISS retrieval, metadata lookup, and MATCH/UNKNOWN decision logic.

---

## What Was Done

### 1. Preprocessing & Validation
- Implemented [`app/preprocessing/image.py`](file:///d:/PL/thuli/app/preprocessing/image.py) to validate and load images into RGB PIL format across both online queries and offline pipelines.
- Added input validation for non-existent files, corrupt image data, and unsupported types.

### 2. Matcher Architecture & Pipeline
- Implemented `JewelleryMatcher` in [`app/retrieval/matcher.py`](file:///d:/PL/thuli/app/retrieval/matcher.py):
  - Integrates `load_and_preprocess_image()` -> `JewelleryEncoder.encode_image()` -> `FAISSIndex.search()`.
  - Resolves integer indices to `JW_NNNNNN` product IDs via `product_ids.json`.
  - Performs full metadata lookups (product name, category, subcategory, image path, width, height) against `catalogue.csv`.
  - Ranks candidates 1 to $K$ by descending cosine similarity.
  - Implements decision logic: `best_similarity >= threshold -> "MATCH"` else `"UNKNOWN"`.
  - Supports dynamic query-time overrides for `top_k` and `threshold`.

### 3. CLI Demonstration Runner
- Built [`scripts/run_matcher.py`](file:///d:/PL/thuli/scripts/run_matcher.py) to execute image queries from the CLI and display structured match responses.
- Verified on a sample catalogue image with **197.49 ms** end-to-end query latency on CPU.

### 4. Verification & Testing
- Implemented [`tests/test_matcher.py`](file:///d:/PL/thuli/tests/test_matcher.py) covering 13 test cases:
  - Matcher initialization and missing artifact errors
  - Single and synthetic PIL image matching
  - Result schema and strictly descending score ordering
  - Metadata resolution accuracy
  - Threshold-driven `MATCH` and `UNKNOWN` decisions
  - Dynamic `top_k` overrides
  - Exact self-retrieval sanity test ($s = 1.000000$, `MATCH`)
  - Error handling for missing files, corrupt image bytes, and invalid types
- Ran complete combined test suite across Phases 1, 2, 3, and 4:
  - `pytest tests/test_catalogue.py tests/test_embeddings.py tests/test_index.py tests/test_matcher.py -v` -> **50/50 PASSED (100%)**.

---

## Files Created / Modified

| File | Purpose |
|---|---|
| [`app/preprocessing/image.py`](file:///d:/PL/thuli/app/preprocessing/image.py) | Image loading, RGB conversion, and corruption check utilities |
| [`app/retrieval/matcher.py`](file:///d:/PL/thuli/app/retrieval/matcher.py) | End-to-end `JewelleryMatcher` pipeline class |
| [`scripts/run_matcher.py`](file:///d:/PL/thuli/scripts/run_matcher.py) | CLI runner for querying the matcher on images |
| [`tests/test_matcher.py`](file:///d:/PL/thuli/tests/test_matcher.py) | 13 unit, integration, and error-handling tests |
| [`phases/phase_04_matcher.md`](file:///d:/PL/thuli/phases/phase_04_matcher.md) | Phase 4 specification, architecture diagrams, and example outputs |
| [`DECISIONS.md`](file:///d:/PL/thuli/DECISIONS.md) | Documented decisions **D-008** and **D-009** |
| [`phases/README.md`](file:///d:/PL/thuli/phases/README.md) | Updated roadmap with Phase 4 completion |
| [`done.md`](file:///d:/PL/thuli/done.md) | Updated project status and verified metrics |
| [`app/config.py`](file:///d:/PL/thuli/app/config.py) | Exposed `SIMILARITY_THRESHOLD` and `TOP_K` |
| [`.env`](file:///d:/PL/thuli/.env) | Configured baseline threshold $\tau = 0.75$ and $K = 5$ |

---

## Next Steps

1. **Phase 5: FastAPI Backend (`/match`)**
   - Implement `app/api/routes.py` with `POST /match` and `GET /health`.
   - Implement `app/main.py` FastAPI app with CORS and error handlers.
   - Write tests in `tests/test_api.py`.
