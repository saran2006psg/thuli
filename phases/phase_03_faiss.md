# Phase 3 — FAISS Retrieval & Indexing

## 1. Objective

Build an exact, high-performance vector retrieval index using FAISS (`faiss-cpu`) to query the 6,157 catalogue jewellery embeddings in sub-millisecond latency.

---

## 2. Input Artifacts

| Artifact | Properties | Source |
|---|---|---|
| `artifacts/embeddings/catalogue_embeddings.npy` | Shape: `(6157, 512)`, `float32`, Unit L2-normalized ($\|v\|_2 = 1.0$) | Phase 2 CLIP ViT-B/32 Encoder |
| `artifacts/embeddings/product_ids.json` | 6,157 sequential product IDs (`JW_000001` to `JW_006157`) | Phase 1 & 2 Mapping |

---

## 3. FAISS Index Choice & Similarity Metric

### Why `faiss.IndexFlatIP`?
- **Exact Inner Product:** Because all vectors are pre-normalized to unit L2 norm, the inner product is mathematically identical to cosine similarity:
  $$\text{InnerProduct}(u, v) = u \cdot v = \|u\|_2 \|v\|_2 \cos(\theta) = \cos(\theta)$$
- **Zero Loss / 100% Recall:** Unlike approximate nearest neighbour methods (IVF, HNSW, PQ), `IndexFlatIP` performs exhaustive search, guaranteeing exact Top-$K$ nearest neighbours.
- **Scale Suitability:** At $N = 6,157$ vectors and $D = 512$, the index occupies only ~12 MB in memory and searches in $\approx 0.5\text{ ms}$ on CPU, making approximate quantization unnecessary for the baseline.

---

## 4. Index Construction & Persistence

- **Offline Indexing Script:** [`scripts/build_index.py`](file:///d:/PL/thuli/scripts/build_index.py) loads `catalogue_embeddings.npy`, verifies unit norms and product ID alignment, constructs `faiss.IndexFlatIP(512)`, and writes the index to disk.
- **Output Artifact:** `artifacts/indexes/catalogue.faiss` (Size: 12.03 MB).
- **Runtime Persistence:** `FAISSIndex.load("artifacts/indexes/catalogue.faiss")` loads the index in $\approx 5\text{ ms}$ without rebuilding.

---

## 5. Search API & Validation

The `FAISSIndex` class in [`app/retrieval/index.py`](file:///d:/PL/thuli/app/retrieval/index.py) provides:
- `search(query_embedding, top_k=5)`: Accepts `(D,)`, `(1, D)`, or batch `(M, D)` queries, validates dimensionality ($D = 512$) and bounds ($1 \le \text{top\_k} \le N$), returning `(scores, indices)`.
- `search_single(query_embedding, top_k=5)`: Convenience method returning `[{"index": int, "score": float}, ...]`.
- `get_product_ids(indices, product_ids)`: Maps integer matrix positions to corresponding `JW_NNNNNN` product IDs.

---

## 6. Testing & Verification

Automated test suite in [`tests/test_index.py`](file:///d:/PL/thuli/tests/test_index.py) covers:
1. Index initialization and empty size
2. Vector ingestion and size tracking
3. Search output shapes (`(1, K)` and batch `(M, K)`)
4. Single-query search helper
5. **Self-retrieval sanity test:** Querying vector $i$ returns top-1 index $i$ with score $\approx 1.000000$
6. **Score ordering:** Returned scores are strictly monotonically descending ($s_1 \ge s_2 \ge s_3 \ge \dots$)
7. **Score bounds:** Cosine similarity scores lie in $[-1.0, 1.0]$
8. **Top-$K$ flexibility:** Verified for $K \in \{1, 3, 5, 10, 20\}$
9. **Persistence test:** Save/load cycle verified for identical search outputs on synthetic vectors
10. **Validation errors:** Rejection of mismatched dimensions, invalid $K \le 0$, $K > N$, and search on empty index
11. **Product ID mapping:** Validated index-to-ID alignment and out-of-bounds protection
12. **Production artifact check:** Verified properties of `artifacts/indexes/catalogue.faiss`

**Test Results:** **18 / 18 Phase 3 tests PASSED**.

---

## 7. Performance Benchmark (Measured Results)

Benchmarked isolated FAISS search using [`scripts/benchmark_index.py`](file:///d:/PL/thuli/scripts/benchmark_index.py) across 500 single-query retrievals ($K=5$) on the actual development machine (Windows CPU, Python 3.12.6):

| Metric | Measured Value |
|---|---|
| **Indexed Dataset** | 6,157 vectors (512-dim) |
| **Index Type** | `faiss.IndexFlatIP` |
| **Number of Queries** | 500 single queries ($K=5$) |
| **Median Latency ($p_{50}$)** | **0.5187 ms** |
| **Mean Latency** | **0.5406 ms** |
| **$p_{95}$ Latency** | **0.7350 ms** |
| **$p_{99}$ Latency** | **0.8373 ms** |
| **Min Latency** | **0.3876 ms** |
| **Max Latency** | **1.6954 ms** |
| **Throughput (QPS)** | **1,849.9 queries/sec** |

*Note: This benchmark measures pure FAISS search latency in isolation. Full end-to-end latency (including image loading and CLIP encoding) will be benchmarked in Phase 6.*

---

## 8. Limitations & What Phase 4 Will Do

- **Scope of Phase 3:** Provides raw nearest-neighbour vector retrieval only (returns integer indices + cosine scores).
- **Not Included in Phase 3:** Does not apply match/unknown thresholds, does not format product metadata, and does not execute query image preprocessing.
- **Phase 4 (Baseline Matcher):** Will integrate Query Preprocessing $\to$ CLIP Encoder $\to$ FAISS Retrieval $\to$ Metadata Lookup $\to$ Calibrated Threshold $\to$ `MATCH` / `UNKNOWN` decision.
