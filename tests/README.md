# Test Suite (`tests/`)

This directory contains the unit, integration, and regression test suites for the **Thuli Jewellery Retrieval Engine**, executed with **pytest**.

---

## Directory Structure

```
tests/
├── test_api.py              # FastAPI endpoint tests (endpoints, health, search)
├── test_catalogue.py        # Catalogue data integrity, paths, and CSV parsing
├── test_data_collection.py   # Stumper data collection and file upload unit tests
├── test_embeddings.py       # CLIP embedding shape (512-d), L2-norm, and consistency
├── test_evaluation.py       # Evaluation metrics calculation (Top-1, Top-5, FAR, FRR)
├── test_index.py            # FAISS IndexFlatIP build, search, save, and reload
├── test_matcher.py          # Single-item visual matcher logic & thresholding
└── test_multi_matcher.py    # FastSAM / grid multi-item segmentation & deduplication
```

---

## Test Modules Breakdown

| Test File | Scope | What It Validates |
|---|---|---|
| `test_api.py` | API Layer | Status codes, multipart upload handling, JSON schema of `/api/match`, `/api/stats`, `/api/samples`. |
| `test_catalogue.py` | Data Layer | Verifies all 6,157 catalogue records exist on disk, no duplicate product IDs, valid image formats. |
| `test_data_collection.py` | Collector | Stumper photo saving, deletion, progress statistics, and metadata syncing. |
| `test_embeddings.py` | Vision Model | Output vector dimensionality is strictly 512, all vectors satisfy $\|v\|_2 \approx 1.0$, deterministic output on identical inputs. |
| `test_index.py` | Vector Index | FAISS exact inner product retrieval, index loading from disk, handling edge cases ($K > N$, empty queries). |
| `test_matcher.py` | Core Matcher | Top-$K$ candidate structure, score sorting in descending order, threshold logic ($< 0.75 \to \text{UNKNOWN}$). |
| `test_multi_matcher.py` | Segmentation | FastSAM model loading, bounding box cropping, overlapping crop deduplication, grid fallback. |
| `test_evaluation.py` | Benchmarks | Correct calculation of Top-1 / Top-5 accuracy, False Acceptance Rate (FAR), False Rejection Rate (FRR), and latency percentiles. |

---

## How to Run Tests

### Run all tests:
```bash
pytest tests/ -v
```

### Run a specific test suite:
```bash
pytest tests/test_matcher.py -v
pytest tests/test_multi_matcher.py -v
pytest tests/test_api.py -v
```

### Run tests with coverage report:
```bash
pytest --cov=app tests/
```
