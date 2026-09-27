# REST API Reference

The Thuli backend exposes a REST API powered by FastAPI.
Base URL: `http://localhost:8000` (or `http://localhost:5173/api` via Vite proxy).

Interactive documentation (Swagger UI) is available at:
`http://localhost:8000/docs`

---

## 1. Visual Retrieval Endpoints

### `POST /api/match`
Executes single-item visual search against the 6,157 item catalogue.

**Request:** `multipart/form-data`
- `file` *(required, binary)*: Image file (JPEG, PNG, WebP).
- `top_k` *(optional, integer, default: 5)*: Number of nearest candidates to return ($1 \le k \le 50$).
- `threshold` *(optional, float, default: 0.75)*: Decision cutoff threshold ($0.0 \le \tau \le 1.0$).

**Response:** `200 OK` (`application/json`)
```json
{
  "query_status": "success",
  "decision": "MATCH",
  "threshold": 0.75,
  "top_similarity": 0.8842,
  "matches": [
    {
      "rank": 1,
      "product_id": "ring_00123",
      "product_name": "Gold Solitaire Ring",
      "category": "ring",
      "similarity": 0.8842,
      "image_url": "/data/catalogue/jewelry_dataset/ring/ring_00123.jpg"
    }
  ],
  "latency_ms": 84.12
}
```

---

### `POST /api/match/multi`
Multi-item jewellery search using FastSAM segmentation.

**Request:** `multipart/form-data`
- `file` *(required, binary)*: Photo containing 2–3 jewellery items.
- `top_k` *(optional, integer, default: 5)*: Per-crop candidates.
- `threshold` *(optional, float, default: 0.75)*: Match confidence threshold.
- `strategy` *(optional, string, default: "sam")*: Region proposal (`"sam"` or `"grid"`).

**Response:** `200 OK` (`application/json`)
```json
{
  "query_status": "success",
  "strategy": "sam",
  "total_crops": 2,
  "matched_count": 2,
  "matches": [
    {
      "rank": 1,
      "product_id": "bracelet_00045",
      "product_name": "Silver Link Bracelet",
      "category": "bracelet",
      "similarity": 0.8234,
      "image_url": "/data/catalogue/jewelry_dataset/bracelet/bracelet_00045.jpg",
      "source_crop_id": "crop_0"
    }
  ],
  "crop_results": [
    {
      "crop_id": "crop_0",
      "box": [45, 120, 310, 480],
      "decision": "MATCH",
      "product_id": "bracelet_00045",
      "similarity": 0.8234
    }
  ],
  "latency_ms": 142.50
}
```

---

## 2. Catalogue & Metadata Endpoints

### `GET /api/stats`
Returns total catalogue item counts and breakdown by category.

**Response:**
```json
{
  "total_items": 6157,
  "categories": {
    "ring": 2500,
    "necklace": 1800,
    "earring": 1200,
    "bracelet": 657
  }
}
```

### `GET /api/samples`
Returns 8 curated sample items for instant one-click testing in the UI.

### `GET /api/catalogue/products`
Search catalogue items by product ID or name with pagination.
- Query params: `q` (optional string), `limit` (int, default: 20), `offset` (int, default: 0).

---

## 3. Evaluation & Benchmark Endpoints

### `POST /api/evaluation/run`
Triggers the Phase 7 evaluation benchmark across `evaluation/images/` in a background worker thread.
- **Response:** `{"status": "started", "message": "Evaluation started in background."}`

### `GET /api/evaluation/status`
Polls the execution state of the evaluation job.
- **Response:**
  ```json
  {
    "running": true,
    "progress": 42,
    "total": 115,
    "error": null,
    "last_completed_at": null
  }
  ```

### `GET /api/evaluation/results`
Returns latest metrics, accuracies, FAR, FRR, and query results.

### `GET /api/evaluation/download`
Downloads the raw results as a CSV spreadsheet.

### `POST /api/automated-stumper/run`
Runs the 900-image synthetic automated benchmark.

### `GET /api/automated-stumper/results`
Retrieves automated benchmark metrics and comparison data.
