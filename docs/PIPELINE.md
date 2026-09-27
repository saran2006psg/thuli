# Data Ingestion & Retrieval Pipelines

This document describes the two operational pipelines in the Thuli system:
1. **Offline Pipeline:** Catalogue ingestion, batch feature extraction, and FAISS index construction.
2. **Online Query Pipeline:** Real-time query preprocessing, vector search, multi-item segmentation, and response formatting.

---

## 1. Offline Pipeline (Catalogue Indexing)

The offline pipeline transforms raw product imagery into indexed searchable vectors.

```
Raw Product Images
(data/catalogue/jewelry_dataset/*)
       │
       ▼
[ scripts.build_catalogue_csv ]
       │  • Validates image readable & size > 1KB
       │  • Extracts product_id & category
       ▼
data/catalogue.csv (6,157 items)
       │
       ▼
[ scripts.generate_embeddings ]
       │  • Loads sentence-transformers/clip-ViT-B-32
       │  • Batch inference (batch size: 64)
       │  • L2 unit-norm normalization
       ▼
artifacts/embeddings/
  ├── catalogue_embeddings.npy  (6157 x 512, float32)
  └── product_ids.json          (ordered ID array)
       │
       ▼
[ scripts.build_index ]
       │  • Initializes faiss.IndexFlatIP(512)
       │  • Adds 6,157 vectors
       │  • Writes binary index to disk
       ▼
artifacts/indexes/catalogue.faiss
```

### Steps to Run Offline Pipeline:
```bash
# Step 1: Re-scan directory and build catalogue.csv
python -m scripts.build_catalogue_csv

# Step 2: Compute CLIP embeddings for all 6,157 catalogue items
python -m scripts.generate_embeddings

# Step 3: Build the FAISS vector index
python -m scripts.build_index
```

---

## 2. Online Inference Pipeline (Real-Time Search)

### A. Single-Item Query Flow (`POST /api/match`)

1. **Upload & Ingestion:**
   Client sends an image file via multipart form data (`file`), accompanied by optional `top_k` and `threshold`.
2. **Decoding & Sanitation:**
   FastAPI reads bytes into an in-memory buffer. PIL decodes the image, verifies valid dimensions, and converts the color profile to RGB.
3. **Inference & Embedding:**
   The PIL image is fed into `CLIPEncoder.encode_image()`. The model produces a 512-dimensional embedding vector, immediately L2-normalized:
   ```python
   vec = model.encode(image, convert_to_numpy=True)
   norm = np.linalg.norm(vec)
   if norm > 0:
       vec = vec / norm
   ```
4. **FAISS Search:**
   `FaissIndex.search(query_vector, top_k)` performs an exact inner product search against the pre-loaded in-memory FAISS index. It returns:
   - Vector indices: $[i_1, i_2, \dots, i_k]$
   - Similarity scores: $[s_1, s_2, \dots, s_k]$ (range $[-1.0, 1.0]$, typically $[0.5, 0.99]$)
5. **Threshold & Verdict:**
   If $s_1 \ge \tau$ (default $\tau = 0.75$), `decision = "MATCH"`.
   If $s_1 < \tau$, `decision = "UNKNOWN"`.
6. **Metadata Hydration:**
   Each index $i_k$ is mapped to its `product_id` via `product_ids.json`, and enriched with title, category, and image URL from the in-memory `catalogue_lookup` dictionary.
7. **Response Serialization:**
   Results are serialized to JSON and returned to the client in $\approx 80\text{--}110 \text{ ms}$ total roundtrip time.

---

### B. Multi-Item Query Flow (`POST /api/match/multi`)

1. **Segmentation:**
   The user's query photo is passed to `MultiItemMatcher`. FastSAM (`FastSAM-s.pt`) segments distinct foreground objects.
2. **Bounding Box Filtering:**
   - Drops noisy background dust or tiny segments ($< 1\%$ total image area).
   - Drops frame-filling background contours ($> 95\%$ total area).
   - Applies $15\%$ safety padding around each remaining bounding box.
3. **Per-Segment Embedding & Retrieval:**
   Each bounding box is cropped and queried independently through `JewelleryMatcher`.
4. **Deduplication:**
   If multiple overlapping segments match the same `product_id`, the duplicate with the lower similarity score is pruned, retaining only the single best detection.
5. **Consolidated Response:**
   Returns both individual segment crops and the deduplicated list of identified jewellery products.
