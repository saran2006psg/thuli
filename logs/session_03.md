# Session 03 — Phase 3: FAISS Retrieval & Indexing

**Date:** 2026-09-24  
**Phase:** 3 — FAISS Retrieval & Indexing  
**Goal:** Build and benchmark an exact vector retrieval engine using FAISS (`faiss-cpu`) to query the 6,157 catalogue embeddings in sub-millisecond latency.

---

## What Was Done

### 1. Vector Search Architecture
- Installed and pinned `faiss-cpu==1.15.1` in [`requirements.txt`](file:///d:/PL/thuli/requirements.txt).
- Selected **`faiss.IndexFlatIP`** (Inner Product / Exact Cosine Similarity) as the baseline retrieval index (Decision **D-007**).
- Implemented `FAISSIndex` wrapper in [`app/retrieval/index.py`](file:///d:/PL/thuli/app/retrieval/index.py) supporting:
  - Vector addition with shape/type validation (`float32`, dimension=512)
  - Search across single `(D,)`, `(1, D)`, or batch `(M, D)` queries
  - Boundary checks for $1 \le \text{top\_k} \le N$
  - Index persistence via `save()` and `load()`
  - Product ID mapping helper `get_product_ids()`

### 2. Index Construction & Artifacts
- Implemented [`scripts/build_index.py`](file:///d:/PL/thuli/scripts/build_index.py) to ingest `catalogue_embeddings.npy` (6,157 x 512) and save the FAISS binary.
- Verified exact self-retrieval sanity test during index creation.
- Saved artifact:
  - `artifacts/indexes/catalogue.faiss` (Size: 12.03 MB).

### 3. Verification & Testing
- Implemented unit and integration test suite in [`tests/test_index.py`](file:///d:/PL/thuli/tests/test_index.py) covering 18 test cases.
- Executed full combined test suite across Phases 1, 2, and 3:
  - `pytest tests/test_catalogue.py tests/test_embeddings.py tests/test_index.py -v` $\to$ **37/37 PASSED (100%)**.

### 4. Search Latency Benchmark
- Implemented [`scripts/benchmark_index.py`](file:///d:/PL/thuli/scripts/benchmark_index.py) to isolate and measure FAISS search latency on 500 single-query retrievals ($K=5$) on CPU.
- **Measured Results:**
  - **Median Latency ($p_{50}$):** `0.5187 ms`
  - **Mean Latency:** `0.5406 ms`
  - **$p_{95}$ Latency:** `0.7350 ms`
  - **$p_{99}$ Latency:** `0.8373 ms`
  - **Throughput:** `1,849.9 QPS`

---

## Files Created / Modified

| File | Purpose |
|---|---|
| [`app/retrieval/index.py`](file:///d:/PL/thuli/app/retrieval/index.py) | `FAISSIndex` wrapper class and product ID mapping helper |
| [`scripts/build_index.py`](file:///d:/PL/thuli/scripts/build_index.py) | Offline script to construct and persist `catalogue.faiss` |
| [`scripts/benchmark_index.py`](file:///d:/PL/thuli/scripts/benchmark_index.py) | Latency benchmark measuring isolated FAISS query execution |
| [`tests/test_index.py`](file:///d:/PL/thuli/tests/test_index.py) | 18 unit, boundary, self-retrieval, and persistence tests |
| `artifacts/indexes/catalogue.faiss` | Persisted FAISS IndexFlatIP binary (12.03 MB) |
| [`phases/phase_03_faiss.md`](file:///d:/PL/thuli/phases/phase_03_faiss.md) | Phase 3 detailed report and measured benchmark tables |
| [`DECISIONS.md`](file:///d:/PL/thuli/DECISIONS.md) | Added Decision **D-007** (FAISS IndexFlatIP) |
| [`phases/README.md`](file:///d:/PL/thuli/phases/README.md) | Updated roadmap with Phase 3 completion |
| [`requirements.txt`](file:///d:/PL/thuli/requirements.txt) | Enabled `faiss-cpu>=1.8.0` |
| [`app/config.py`](file:///d:/PL/thuli/app/config.py) | Exposed `FAISS_INDEX_PATH` and `FAISS_INDEX_TYPE` |
| [`.env`](file:///d:/PL/thuli/.env) | Configured `FAISS_INDEX_PATH=artifacts/indexes/catalogue.faiss` |

---

## Issues Encountered & Resolved

1. **Windows cp1252 Unicode Error in `build_index.py`:**
   - *Issue:* Unicode symbol `≈` triggered `UnicodeEncodeError` when printed to standard output.
   - *Fix:* Replaced `≈` with ASCII `~` in all status print statements.

---

## Next Steps

1. **Phase 4: Baseline Matcher Pipeline**
   - Implement `app/retrieval/matcher.py` connecting Preprocessor $\to$ Encoder $\to$ FAISS Index.
   - Implement metadata resolution from `data/catalogue.csv`.
   - Formulate initial confidence score calculation.
   - Prepare validation framework for similarity threshold calibration.
