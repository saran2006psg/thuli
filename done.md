# Project Status & Work Completed — PS2: Stump the Model

**Project:** Jewellery Image Retrieval System ("Stump the Model")  
- **Current Status:** **Phase 1, Phase 2, Phase 3 & Phase 4 Complete**  
- **All Tests Passing:** **50 / 50 (100%)**

---

## 1. Executive Summary

We have built the complete end-to-end vector retrieval and matching pipeline for the jewellery retrieval engine:
1. **Phase 1 (Catalogue Setup):** Standardized, cleaned, and verified **6,157 jewellery images** across 4 categories into a structured catalogue with unique IDs and metadata.
2. **Phase 2 (Image Embedding):** Integrated a pretrained vision encoder (**CLIP ViT-B/32**), batch-extracted **512-dimensional L2-normalized embeddings** for all 6,157 items, and stored persistent artifacts on disk.
3. **Phase 3 (FAISS Retrieval & Indexing):** Built an exact inner-product vector index (**`faiss.IndexFlatIP`**), persisted `artifacts/indexes/catalogue.faiss` (12.03 MB), implemented Top-$K$ retrieval with product ID mapping, and achieved **0.5187 ms median latency** on CPU.
4. **Phase 4 (Baseline Matcher Pipeline):** Built [`app/retrieval/matcher.py`](file:///d:/PL/thuli/app/retrieval/matcher.py) (`JewelleryMatcher`) connecting query preprocessing $\to$ CLIP encoding $\to$ FAISS search $\to$ Top-5 metadata resolution $\to$ MATCH / UNKNOWN decision logic.

---

## 2. Dataset & Catalogue Summary

- **Source:** `sidd707/jewelry-design-dataset`
- **Total Validated Images:** **6,157**
- **Image Directory:** [`data/catalogue/jewelry_dataset/`](file:///d:/PL/thuli/data/catalogue/jewelry_dataset)
- **Catalogue Metadata:** [`data/catalogue.csv`](file:///d:/PL/thuli/data/catalogue.csv)

### Category Distribution
| Category | Image Count | Image Format | Naming Pattern |
|---|---|---|---|
| **Earrings** | 3,298 | JPEG | `earring_00000.jpg` – `earring_03297.jpg` |
| **Necklaces** | 1,738 | JPEG | `necklace_00000.jpg` – `necklace_01737.jpg` |
| **Bracelets** | 888 | JPEG | `bracelet_00000.jpg` – `bracelet_00887.jpg` |
| **Rings** | 233 | JPEG | `ring_00000.jpg` – `ring_00232.jpg` |
| **Total** | **6,157** | **JPEG (q=95)** | **Unique sequential IDs: `JW_000001` – `JW_006157`** |

---

## 3. Phase 1 — Catalogue Setup (Completed)

- **Standardized Schema:** `product_id`, `product_name`, `category`, `subcategory`, `image_path`, `source_url`, `width`, `height`.
- **Validation:** Every single image file verified with PIL (`img.verify()`), checked for dimension consistency, corruptions, and zero empty values.
- **Tests:** [`tests/test_catalogue.py`](file:///d:/PL/thuli/tests/test_catalogue.py) — **11/11 tests PASSED**.

---

## 4. Phase 2 — Image Embedding (Completed)

- **Vision Encoder:** **CLIP ViT-B/32** (`openai/clip-vit-base-patch32`) in [`app/retrieval/encoder.py`](file:///d:/PL/thuli/app/retrieval/encoder.py).
- **L2-Normalization:** Strict unit normalization ($\|v\|_2 = 1.0$) ensures dot product directly calculates cosine similarity.
- **Batch Processing:** [`scripts/generate_embeddings.py`](file:///d:/PL/thuli/scripts/generate_embeddings.py) embedded all 6,157 images.
- **Artifacts Saved:**
  - `artifacts/embeddings/catalogue_embeddings.npy` — Matrix of shape `(6157, 512)`, `float32` (~12.6 MB).
  - `artifacts/embeddings/product_ids.json` — 1-to-1 ordered mapping of 6,157 product IDs.
- **Storage & Memory Optimization:** Hugging Face and PyTorch caches mapped to `D:` drive (`D:/.cache/huggingface`, `D:/.cache/torch`) with 160+ GB free space.
- **Tests:** [`tests/test_embeddings.py`](file:///d:/PL/thuli/tests/test_embeddings.py) — **8/8 tests PASSED**.

---

## 5. Phase 3 — FAISS Retrieval & Indexing (Completed)

- **Vector Index:** **`faiss.IndexFlatIP`** in [`app/retrieval/index.py`](file:///d:/PL/thuli/app/retrieval/index.py) (Decision **D-007**).
- **Exact Exhaustive Search:** 100% recall lossless search over all 6,157 normalized 512-d embeddings.
- **Artifacts Saved:**
  - `artifacts/indexes/catalogue.faiss` — Persisted FAISS binary (12.03 MB).
- **Top-$K$ Search & Mapping:** Returns sorted cosine similarity scores, vector indices, and mapped `JW_NNNNNN` product IDs.
- **Measured FAISS Search Latency (500 queries, $K=5$, CPU):**
  - **Median Latency ($p_{50}$):** `0.5187 ms`
  - **Mean Latency:** `0.5406 ms`
  - **$p_{95}$ Latency:** `0.7350 ms`
  - **$p_{99}$ Latency:** `0.8373 ms`
  - **Throughput:** `1,849.9 queries/sec`
- **Tests:** [`tests/test_index.py`](file:///d:/PL/thuli/tests/test_index.py) — **18/18 tests PASSED**.

---

## 6. Phase 4 — Baseline Matcher Pipeline (Completed)

- **Matcher Class:** **`JewelleryMatcher`** in [`app/retrieval/matcher.py`](file:///d:/PL/thuli/app/retrieval/matcher.py).
- **Pipeline Flow:** Query Image $\to$ Preprocessing $\to$ CLIP ViT-B/32 $\to$ FAISS IndexFlatIP $\to$ Top-$K$ Metadata Resolution $\to$ Decision Logic.
- **Decision Logic:** `best_similarity >= threshold -> "MATCH"` else `"UNKNOWN"`.
- **Default Baseline Parameters:** $\tau = 0.75$, $K = 5$ (configurable via `.env` or query-time arguments).
- **CLI Runner:** [`scripts/run_matcher.py`](file:///d:/PL/thuli/scripts/run_matcher.py) (measured single-query CPU latency $\approx 197\text{ ms}$ including PIL loading & CLIP inference).
- **Tests:** [`tests/test_matcher.py`](file:///d:/PL/thuli/tests/test_matcher.py) — **13/13 tests PASSED**.

---

## 7. Architectural Decisions (DECISIONS.md)

| ID | Title | Decision |
|---|---|---|
| **D-001** | Data Source | `sidd707/jewelry-design-dataset` (6,157 real jewellery items) |
| **D-002** | Image Format | Uniform JPEG at quality=95 for optimal quality/size balance |
| **D-003** | Deduplication | Perceptual hashing (pHash) for visual near-duplicate rejection |
| **D-004** | Product ID Scheme | Sequential, stable `JW_NNNNNN` IDs |
| **D-005** | Vision Encoder | CLIP ViT-B/32 (512-dim zero-shot semantic representation) |
| **D-006** | Normalization | Unit L2-norm for instant inner-product cosine similarity in FAISS |
| **D-007** | FAISS Index Type | `faiss.IndexFlatIP` exact cosine index (sub-millisecond retrieval on 6k items) |
| **D-008** | Decision Rule | Top-1 cosine score thresholding for MATCH vs UNKNOWN |
| **D-009** | Baseline Threshold | Uncalibrated baseline $\tau = 0.75$ (to be calibrated on stumper set in Phase 8/10) |

---

## 8. Verification & Test Suite Summary

Command:
```bash
python -m pytest tests/test_catalogue.py tests/test_embeddings.py tests/test_index.py tests/test_matcher.py -v
```

Output:
```
============================= 50 passed in 34.54s =============================
```
- **Phase 1 Tests:** 11 / 11 PASSED
- **Phase 2 Tests:** 8 / 8 PASSED
- **Phase 3 Tests:** 18 / 18 PASSED
- **Phase 4 Tests:** 13 / 13 PASSED
- **Total:** **50 / 50 PASSED (100%)**

---

## 9. Repository Layout & Key Files Directory

```
thuli/
├── app/
│   ├── config.py                     # Central configuration & typed env settings
│   ├── main.py                       # FastAPI application stub (Phase 5)
│   ├── api/routes.py                 # /match API router stub (Phase 5)
│   ├── preprocessing/image.py        # Image transformations & validation
│   └── retrieval/
│       ├── encoder.py                # CLIP JewelleryEncoder wrapper (Phase 2)
│       ├── index.py                  # FAISSIndex wrapper & ID mapping (Phase 3)
│       └── matcher.py                # JewelleryMatcher pipeline (Phase 4)
├── artifacts/
│   ├── embeddings/
│   │   ├── catalogue_embeddings.npy  # 6,157 x 512 float32 embedding matrix
│   │   └── product_ids.json          # 6,157 product IDs mapping
│   └── indexes/
│       └── catalogue.faiss           # Persisted FAISS IndexFlatIP (12.03 MB)
├── data/
│   ├── catalogue.csv                 # 6,157 validated rows
│   └── catalogue/
│       └── jewelry_dataset/          # 6,157 JPEG images (bracelet, earring, necklace, ring)
├── phases/
│   ├── README.md                     # Roadmap index
│   ├── phase_02_embedding.md         # Phase 2 specification & checklist
│   ├── phase_03_faiss.md             # Phase 3 specification & benchmark results
│   └── phase_04_matcher.md           # Phase 4 specification & example outputs
├── logs/
│   ├── session_01.md                 # AI session log: Phase 1
│   ├── session_02.md                 # AI session log: Phase 2
│   ├── session_03.md                 # AI session log: Phase 3
│   └── session_04.md                 # AI session log: Phase 4
├── scripts/
│   ├── build_catalogue_csv.py        # Validates images & builds catalogue.csv
│   ├── generate_embeddings.py        # Batch embedding extraction
│   ├── build_index.py                # Constructs & saves catalogue.faiss
│   ├── benchmark_index.py            # Latency benchmark for FAISS search
│   └── run_matcher.py                # CLI runner for image queries
├── tests/
│   ├── test_catalogue.py             # 11 Phase 1 tests
│   ├── test_embeddings.py            # 8 Phase 2 tests
│   ├── test_index.py                 # 18 Phase 3 tests
│   └── test_matcher.py               # 13 Phase 4 tests
├── DECISIONS.md                      # Technical decision log (D-001 to D-009)
├── done.md                           # Project status & completed work summary
└── requirements.txt                  # Python dependencies
```

---

## 10. What's Next: Phase 5 (FastAPI Application)

1. **Implement `app/api/routes.py`**:
   - `POST /match`: Accepts image file upload (`UploadFile`), returns Top-$K$ candidate list, similarity scores, and `MATCH`/`UNKNOWN` decision.
   - `GET /health`: Returns service health, index size (6,157), and model status.
2. **Implement `app/main.py`**: FastAPI app assembly with CORS middleware and error handlers.
3. **Write Unit Tests (`tests/test_api.py`)**: Test HTTP multipart upload, valid image response schema, invalid file rejection (400), and healthcheck.
