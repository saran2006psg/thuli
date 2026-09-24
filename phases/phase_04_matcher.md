# Phase 4 — Baseline Matcher Pipeline

## 1. Objective

Build and verify the complete end-to-end image-to-product retrieval pipeline connecting:
$$\text{Query Image} \longrightarrow \text{Preprocessing} \longrightarrow \text{CLIP Vision Encoder} \longrightarrow \text{512-d Embedding} \longrightarrow \text{FAISS IndexFlatIP} \longrightarrow \text{Metadata Resolution} \longrightarrow \text{Decision (MATCH / UNKNOWN)}$$

---

## 2. Pipeline Architecture

```
                      QUERY PIPELINE
                      
                    [ Query Image ]
                          │
                          ▼
            [ Preprocessing (app/preprocessing/image.py) ]
              - RGB conversion
              - Verification & format validation
                          │
                          ▼
            [ Vision Encoder (app/retrieval/encoder.py) ]
              - CLIP ViT-B/32 forward pass
              - Unit L2 Normalization (||v||_2 = 1.0)
                          │ (1, 512) float32 vector
                          ▼
            [ FAISS Vector Index (app/retrieval/index.py) ]
              - catalogue.faiss (IndexFlatIP, 6,157 items)
              - Top-K Inner-Product Cosine Similarity Search
                          │ (scores, indices)
                          ▼
            [ Metadata Lookup & Ranking (app/retrieval/matcher.py) ]
              - Map integer vector index -> product_ids.json
              - Join product metadata from catalogue.csv
              - Rank candidates 1 .. K by descending similarity
                          │
                          ▼
            [ Decision Logic (MATCH vs UNKNOWN) ]
              - If top-1 similarity >= threshold -> "MATCH"
              - If top-1 similarity < threshold  -> "UNKNOWN"
```

---

## 3. Implementation Details

### 3.1 Matcher Class (`app/retrieval/matcher.py`)
- **Class:** `JewelleryMatcher`
- **Inputs:** PIL Image, image filepath string, or `Path` object.
- **Configurable Parameters:**
  - `top_k` (Default: `5`, configurable via `.env` or query-time argument).
  - `threshold` (Default: `0.75`, configurable via `.env` or query-time argument).
- **Error Handling:**
  - `FileNotFoundError` on non-existent query image paths.
  - `ValueError` on corrupt, empty, or unreadable image bytes.
  - `TypeError` on invalid input types.
  - Informative missing-artifact exceptions if FAISS index, product IDs, or catalogue CSV are missing.

### 3.2 Decision Boundary & Similarity Representation
- **Similarity Metric:** Raw cosine similarity in range $[-1.0, 1.0]$.
- **Note on Calibration:** The baseline threshold is set to $\tau = 0.75$ by default. As per design guidelines, this threshold is an uncalibrated starting point and will be systematically calibrated on the stumper evaluation dataset in Phase 8/10. Cosine similarity is presented as a geometric similarity score, not an uncalibrated probability percentage.

---

## 4. Example Matcher Output

Querying catalogue image [`data/catalogue/jewelry_dataset/bracelet/bracelet_00000.jpg`](file:///d:/PL/thuli/data/catalogue/jewelry_dataset/bracelet/bracelet_00000.jpg):

```json
{
  "status": "success",
  "decision": "MATCH",
  "threshold": 0.75,
  "best_similarity": 1.0,
  "query_time_ms": 197.486,
  "top_k": 5,
  "results": [
    {
      "rank": 1,
      "product_id": "JW_000001",
      "product_name": "Bracelet 00000",
      "category": "bracelet",
      "subcategory": "bracelet",
      "image_path": "data/catalogue/jewelry_dataset/bracelet/bracelet_00000.jpg",
      "similarity": 1.0,
      "width": 500,
      "height": 473
    },
    {
      "rank": 2,
      "product_id": "JW_005871",
      "product_name": "Necklace 01684",
      "category": "necklace",
      "subcategory": "necklace",
      "image_path": "data/catalogue/jewelry_dataset/necklace/necklace_01684.jpg",
      "similarity": 0.867044,
      "width": 262,
      "height": 262
    },
    {
      "rank": 3,
      "product_id": "JW_000654",
      "product_name": "Bracelet 00653",
      "category": "bracelet",
      "subcategory": "bracelet",
      "image_path": "data/catalogue/jewelry_dataset/bracelet/bracelet_00653.jpg",
      "similarity": 0.863255,
      "width": 262,
      "height": 262
    },
    {
      "rank": 4,
      "product_id": "JW_000731",
      "product_name": "Bracelet 00730",
      "category": "bracelet",
      "subcategory": "bracelet",
      "image_path": "data/catalogue/jewelry_dataset/bracelet/bracelet_00730.jpg",
      "similarity": 0.862679,
      "width": 262,
      "height": 262
    },
    {
      "rank": 5,
      "product_id": "JW_000121",
      "product_name": "Bracelet 00120",
      "category": "bracelet",
      "subcategory": "bracelet",
      "image_path": "data/catalogue/jewelry_dataset/bracelet/bracelet_00120.jpg",
      "similarity": 0.862291,
      "width": 256,
      "height": 256
    }
  ]
}
```

---

## 5. Verification & Tests

Automated test suite in [`tests/test_matcher.py`](file:///d:/PL/thuli/tests/test_matcher.py) covers:
1. Matcher initialization and artifact integrity checks
2. End-to-end retrieval with PIL images and filepaths
3. Top-5 candidate schema, ranks ($1 \dots 5$), and descending score ordering
4. Full metadata resolution against `catalogue.csv`
5. Decision logic (`MATCH` when $s \ge \tau$, `UNKNOWN` when $s < \tau$)
6. Exact self-retrieval ($s = 1.000000$ and product ID match)
7. Error handling on non-existent files, corrupted images, and invalid types
8. Dynamic query-time `top_k` and `threshold` overrides

**Test Results:** **13 / 13 Phase 4 tests PASSED** (Total project suite: **50 / 50 PASSED**).

---

## 6. What Phase 5 Will Do

Phase 5 will package this verified matching engine into a production-grade FastAPI web service:
- `POST /match`: Accepts image file upload (multipart/form-data)
- Validates payload and returns structured Top-5 results with similarity scores and decision
- `GET /health`: Healthcheck endpoint reporting index size and encoder status
