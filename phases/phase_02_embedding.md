# Phase 2 — Image Embedding

## 1. Overview & Objective

**Goal:** Convert every validated jewellery image in `data/catalogue/` (5,804 items) into a high-dimensional, normalized dense embedding vector.

These vectors will represent visual jewellery features (metal finish, gemstone color/shape, silhouette, texture) and serve as the foundation for FAISS nearest-neighbor retrieval in Phase 3.

---

## 2. Architecture & Design Decisions

### 2.1 Model Selection
- **Primary Model:** CLIP (`openai/clip-vit-base-patch32` or `openai/clip-vit-base-patch16`) / OpenCLIP / DINOv2 (`facebook/dinov2-base`).
  - *Why CLIP:* Trained on massive multimodal data; excellent at zero-shot semantic matching and fine-grained visual features.
  - *Embedding Dimension:* 512 (for ViT-B/32) or 768 (for ViT-B/16 / DINOv2).
- **Inference Mode:** Evaluation mode (`torch.no_grad()`), auto-detect GPU (`cuda`) with fallback to `cpu`.

### 2.2 Preprocessing Pipeline
1. Load image using `PIL.Image.open().convert("RGB")`.
2. Resize & Center Crop (224x224 standard for ViT).
3. Convert to tensor and apply standard normalization (mean/std).
4. Extract visual feature token (`pooler_output` / image projection).
5. **L2-Normalize:** Vector $\hat{v} = \frac{v}{\|v\|_2}$ so that cosine similarity equals standard dot product.

---

## 3. Step-by-Step Implementation Guide

### Step 1: Install Phase 2 Dependencies
Uncomment and install the required machine learning packages:
```bash
pip install torch torchvision transformers numpy
```

### Step 2: Configure Environment Settings
Update `.env` and `app/config.py` with embedding parameters:
- `ENCODER_MODEL=openai/clip-vit-base-patch32`
- `EMBEDDING_DIM=512`
- `BATCH_SIZE=64`
- `EMBEDDINGS_PATH=artifacts/embeddings/catalogue_embeddings.npy`
- `PRODUCT_IDS_PATH=artifacts/embeddings/product_ids.json`

### Step 3: Implement Encoder Module (`app/retrieval/encoder.py`)
Create a reusable class `JewelleryEncoder`:
- `__init__(model_name, device)`: Loads pretrained model and processor.
- `encode_image(image: Image | Path) -> np.ndarray`: Encodes a single image into a 1D normalized vector.
- `encode_batch(images: List[Image]) -> np.ndarray`: Encodes a list of images into a 2D matrix of shape `(B, D)`.

### Step 4: Build Batch Generation Script (`scripts/generate_embeddings.py`)
Script flow:
1. Load `data/catalogue.csv` (contains 5,804 records).
2. Validate that each `image_path` exists on disk.
3. Stream images in batches (default batch size: 32 or 64) with `tqdm` progress bar.
4. Pass batches through `JewelleryEncoder`.
5. Stack into single numpy matrix `(N, D)`.
6. Save:
   - Embeddings: `artifacts/embeddings/catalogue_embeddings.npy` (dtype: `float32`)
   - Product ID mapping: `artifacts/embeddings/product_ids.json` (list of `product_id` strings matching matrix rows)

### Step 5: Write Automated Tests (`tests/test_embeddings.py`)
Create unit & integrity tests:
- `test_embeddings_file_exists`: Verifies `.npy` and `.json` exist.
- `test_embeddings_shape`: Matrix shape is exactly `(len(catalogue), EMBEDDING_DIM)`.
- `test_no_nan_or_inf`: Zero `NaN` or `Inf` entries.
- `test_l2_normalized`: All vectors have L2 norm = $1.0 \pm 1e-4$.
- `test_product_ids_alignment`: `product_ids.json` length and order match `catalogue.csv` 1-to-1.

---

## 4. Expected Artifacts & Outputs

| Artifact | Format | Description |
|---|---|---|
| `artifacts/embeddings/catalogue_embeddings.npy` | NumPy Binary (`float32`) | Matrix of shape `(5804, 512)` containing normalized embeddings |
| `artifacts/embeddings/product_ids.json` | JSON Array | Array of 5,804 `product_id` strings (`JW_000001`, `JW_000002`, ...) |

---

## 5. Phase 2 Gate / Verification Checklist

Before moving to Phase 3 (FAISS Retrieval Indexing):
- [x] Dependencies installed (`torch`, `transformers`, etc.)
- [x] `scripts/generate_embeddings.py` completes without errors
- [x] `artifacts/embeddings/catalogue_embeddings.npy` created (size ~12.6 MB for 6,157 x 512-dim)
- [x] `artifacts/embeddings/product_ids.json` created
- [x] `pytest tests/test_embeddings.py -v` passes 100%
- [x] `logs/session_02.md` and `DECISIONS.md` updated with encoder choices
