# Backend Application (`app/`)

This directory contains the production FastAPI backend application powering the **Thuli Jewellery Retrieval Engine**. It implements visual similarity search, multi-item visual segmentation, catalogue metadata management, and evaluation benchmark services.

---

## Directory Structure

```
app/
├── api/
│   ├── __init__.py
│   └── routes.py              # FastAPI REST endpoints & request handlers
├── preprocessing/
│   ├── __init__.py
│   └── image.py               # Image validation, RGB conversion, PIL utilities
├── retrieval/
│   ├── __init__.py
│   ├── encoder.py             # CLIP ViT-B/32 vision encoder (512-d normalized embeddings)
│   ├── index.py               # FAISS IndexFlatIP vector database wrapper
│   ├── matcher.py             # Single-item visual matcher (similarity scoring & top-K)
│   ├── multi_matcher.py       # FastSAM / grid segmentation for multi-item retrieval
│   └── ranking.py             # Ranking and post-retrieval utilities
├── evaluation/
│   ├── __init__.py
│   ├── runner.py              # Phase 7 evaluation engine (scans evaluation/images/)
│   └── automated_runner.py    # Automated stumper benchmark engine (900 tests)
├── collector.py               # Stumper data collection service
├── config.py                  # Environment config, paths, thresholds, and hyperparameters
└── main.py                    # Application entrypoint & static mount configurations
```

---

## Core Components

### 1. `main.py`
- Initializes the `FastAPI` instance.
- Configures CORS middleware for Vite frontend (`localhost:5173`) and local testing.
- Uses `lifespan` handler to pre-warm the `JewelleryMatcher` and FAISS index at startup to eliminate cold-start latency.
- Mounts static file directories:
  - `/data` &rarr; `data/` (catalogue product images)
  - `/evaluation/images` &rarr; `evaluation/images/` (test query images)
  - `/evaluation/automated_images` &rarr; `evaluation/automated_images/`
  - `/static` &rarr; `app/static/` (production frontend assets)

### 2. `config.py`
Centralized application settings and hyperparameters:
- `TOP_K`: Default top-K candidate count (default: `5`).
- `SIMILARITY_THRESHOLD`: Confidence decision threshold (default: `0.75`). Matches below this are rejected as `UNKNOWN`.
- File paths for catalogue images, embeddings (`.npy`), and FAISS index (`.bin`).
- Embedding dimension: `512` (CLIP ViT-B/32).

### 3. `api/routes.py`
Provides all REST API endpoints:
- `POST /api/match`: Single-item visual search (accepts multipart image, returns top-K with cosine similarity).
- `POST /api/match/multi`: Multi-jewellery search with FastSAM/grid segmentation and per-crop deduplication.
- `GET /api/stats`: Total items and category distribution.
- `GET /api/samples`: Curated sample catalogue items for quick demo search.
- `GET /api/catalogue/products`: Search and paginate catalogue items.
- `POST /api/evaluation/run`: Trigger evaluation benchmark in background thread.
- `GET /api/evaluation/status`: Poll progress of running evaluation.
- `GET /api/evaluation/results`: Retrieve evaluation accuracy, FAR, FRR, and latency metrics.
- `POST /api/automated-stumper/run`: Execute automated stumper test suite (900 synthetic tests).

### 4. `retrieval/`
- **`encoder.py` (`CLIPEncoder`)**:
  Wraps `sentence-transformers/clip-ViT-B-32` or OpenAI CLIP. Normalizes all output vectors using L2 norm ($\|v\|_2 = 1$), converting cosine similarity to simple dot products.
- **`index.py` (`FaissIndex`)**:
  Wraps FAISS `IndexFlatIP` (exact Inner Product search). In-memory, sub-millisecond retrieval across 6,157+ catalogue embeddings.
- **`matcher.py` (`JewelleryMatcher`)**:
  High-level retrieval pipeline. Given a query image:
  1. Validates and converts image to RGB.
  2. Generates 512-d L2-normalized embedding.
  3. Queries FAISS for top-$K$ candidates.
  4. Applies threshold check (`0.75`). If top similarity $< 0.75$, marks decision as `UNKNOWN`.
  5. Enriches candidates with metadata from `catalogue.csv`.
- **`multi_matcher.py` (`MultiItemMatcher`)**:
  Identifies multiple distinct jewellery items in a single query image:
  - Strategy `sam`: Uses FastSAM (`FastSAM-s.pt`) to detect jewellery item segments, crops them with padding, and runs each crop through `JewelleryMatcher`.
  - Strategy `grid`: Falls back to overlapping grid tiles if FastSAM is unavailable.
  - Deduplicates multiple detections of the same product ID (retaining highest confidence).

### 5. `evaluation/`
- **`runner.py`**: Executes real-world evaluation on test images in `evaluation/images/`, computes Top-1/Top-5 accuracy, False Acceptance Rate (FAR), False Rejection Rate (FRR), and latency percentiles (P50, P95).
- **`automated_runner.py`**: Evaluates 9 realistic physical perturbations (motion blur, lighting, occlusion, etc.) across 100 source items (900 tests).

---

## How to Run Backend

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run development server with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Swagger UI is available at: `http://localhost:8000/docs`
