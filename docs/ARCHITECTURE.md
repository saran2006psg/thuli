# System Architecture & Technical Design

This document details the architectural principles, machine learning models, vector index algorithms, and runtime components powering the **Thuli Jewellery Retrieval Engine**.

---

## 1. Architectural Philosophy

Jewellery retrieval presents unique computer vision challenges:
- **Fine-grained visual distinctions:** A ring with a 1-carat diamond and 4 prongs looks almost identical to a 1-carat diamond ring with 6 prongs.
- **Physical environmental noise:** Query images taken on mobile phones suffer from skin tone interference (handheld photos), background clutter, harsh reflections on polished gold/silver, motion blur, and uneven lighting.
- **Zero-latency requirement:** Visual search must respond in sub-second time ($< 150 \text{ ms}$) on standard commodity CPU hardware without requiring expensive GPU clusters.

To satisfy these constraints, Thuli employs a **hybrid two-stage architecture**:
1. **Dense Semantic Embeddings:** Pre-trained Vision Transformer (`CLIP ViT-B/32`) extracts deep geometric and stylistic visual representations.
2. **Exact Vector Index:** FAISS `IndexFlatIP` provides $100\%$ exact nearest-neighbor search with zero recall approximation loss.
3. **Region Proposal Segmentation (FastSAM):** In multi-item mode, a lightweight Segment Anything Model isolates individual jewellery pieces into padded crops before vector embedding.

---

## 2. Core Machine Learning Models

### Vision Encoder: CLIP ViT-B/32
- **Model:** `sentence-transformers/clip-ViT-B-32` (or OpenAI CLIP ViT-B/32)
- **Input:** $224 \times 224 \times 3$ RGB image tensor.
- **Output:** $512$-dimensional dense feature vector.
- **L2 Normalization:**
  $$\hat{\mathbf{v}} = \frac{\mathbf{v}}{\|\mathbf{v}\|_2} = \frac{\mathbf{v}}{\sqrt{\sum_{i=1}^{512} v_i^2}}$$
  With unit-length vectors ($\|\hat{\mathbf{v}}\|_2 = 1.0$), Cosine Similarity between query $\mathbf{q}$ and catalogue item $\mathbf{c}$ reduces strictly to their Inner (Dot) Product:
  $$\text{Cosine Similarity}(\mathbf{q}, \mathbf{c}) = \frac{\mathbf{q} \cdot \mathbf{c}}{\|\mathbf{q}\|_2 \|\mathbf{c}\|_2} = \hat{\mathbf{q}} \cdot \hat{\mathbf{c}}$$

### Segmentation: FastSAM-s (`FastSAM-s.pt`)
- **Architecture:** Lightweight CNN-based Segment Anything Model built on YOLOv8x.
- **Speed:** $40 \text{ ms}$ inference on CPU (vs. $2000 \text{ ms}$ for original SAM ViT-H).
- **Function in Thuli:**
  When a user uploads a photo with multiple items (e.g. bracelet + earrings):
  1. FastSAM segments all distinct foreground objects.
  2. The system filters out segments that are too small ($< 1\%$ frame area) or too large ($> 95\%$ frame area).
  3. Bounding boxes are expanded by $15\%$ context margin to avoid cutting off delicate filigree edges.
  4. Each crop is passed through the CLIP &rarr; FAISS pipeline.
  5. If FastSAM is unavailable, the system automatically falls back to an adaptive overlapping 2x2 grid tile strategy.

---

## 3. Vector Database: FAISS `IndexFlatIP`

### Why `IndexFlatIP`?
At $N = 6,157$ items, approximate nearest neighbor (ANN) indices like `IVF-Flat` or `HNSW` are **unnecessary and detrimental**:
- Memory footprint for 6,157 vectors &times; 512 dimensions &times; 4 bytes (float32) is only **12.6 MB**.
- FAISS `IndexFlatIP` computes the exact matrix multiplication $\mathbf{q} \cdot \mathbf{C}^T$ across all 6,157 vectors using AVX2 SIMD instructions in **$0.4 \text{ ms}$** on CPU.
- **Recall is 100%:** No true matches are missed due to quantization or cluster partitioning error.

---

## 4. Decision Logic & Confidence Thresholding

A key business requirement in jewellery catalogue search is **avoiding false acceptance** (recommending the wrong expensive jewellery piece when the user uploads an item not present in the catalogue).

Thuli implements an explicit confidence gate:
$$\text{Decision}(\text{sim}) = \begin{cases} \text{MATCH} & \text{if } \text{sim} \ge \tau \\ \text{UNKNOWN} & \text{if } \text{sim} < \tau \end{cases}$$
where default threshold $\tau = 0.75$.

- If $\text{sim} \ge 0.75$: The top candidates are confirmed matches.
- If $\text{sim} < 0.75$: The system informs the user that the item could not be verified with sufficient confidence in the current catalogue, mitigating False Acceptance Rate (FAR).
- The threshold $\tau$ can be dynamically tuned by the client via request parameters.

---

## 5. End-to-End Component Diagram

```
[ User Browser ]
       │
       ▼ (HTTP POST /api/match)
[ FastAPI Router (app/api/routes.py) ]
       │
       ▼
[ JewelleryMatcher (app/retrieval/matcher.py) ]
  ├── 1. Preprocess: PIL Image.open() ──> convert('RGB')
  ├── 2. Encode: CLIPEncoder.encode_image() ──> 512-d unit vector
  ├── 3. Search: FaissIndex.search(query_vec, top_k=5) ──> indices, scores
  ├── 4. Threshold: Check score >= 0.75 ──> MATCH or UNKNOWN
  └── 5. Metadata: Hydrate product_name, category, image_url from catalogue lookup
       │
       ▼ (JSON Response)
[ React Client ]
```
