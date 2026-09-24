"""
scripts/generate_embeddings.py
──────────────────────────────
Extracts dense embedding vectors for all catalogue images using the
pretrained vision encoder (CLIP), applies L2 normalization, and saves:
  - artifacts/embeddings/catalogue_embeddings.npy
  - artifacts/embeddings/product_ids.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List

# Prevent transformers from attempting to import TensorFlow
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
import pandas as pd
from tqdm import tqdm

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (
    BATCH_SIZE,
    CATALOGUE_CSV,
    EMBEDDINGS_PATH,
    ENCODER_MODEL,
    PRODUCT_IDS_PATH,
)
from app.retrieval.encoder import JewelleryEncoder


def generate_catalogue_embeddings(
    catalogue_csv: Path = CATALOGUE_CSV,
    embeddings_out: Path = EMBEDDINGS_PATH,
    product_ids_out: Path = PRODUCT_IDS_PATH,
    batch_size: int = BATCH_SIZE,
    model_name: str = ENCODER_MODEL,
) -> None:
    print("\n" + "=" * 60)
    print("  Phase 2: Catalogue Embedding Generation")
    print("=" * 60)

    if not catalogue_csv.exists():
        print(f"[ERROR] Catalogue CSV not found: {catalogue_csv}")
        sys.exit(1)

    df = pd.read_csv(catalogue_csv)
    total_records = len(df)
    print(f"  Loaded catalogue CSV : {catalogue_csv} ({total_records:,} rows)")

    if "product_id" not in df.columns or "image_path" not in df.columns:
        print("[ERROR] Catalogue CSV must contain 'product_id' and 'image_path' columns.")
        sys.exit(1)

    # Resolve image paths
    image_paths: List[Path] = []
    product_ids: List[str] = []

    missing_count = 0
    for _, row in df.iterrows():
        p_id = str(row["product_id"])
        raw_path = str(row["image_path"])
        p = Path(raw_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p

        if p.exists():
            image_paths.append(p)
            product_ids.append(p_id)
        else:
            missing_count += 1

    if missing_count > 0:
        print(f"[WARN] {missing_count} images listed in CSV were not found on disk!")

    valid_count = len(image_paths)
    print(f"  Valid images on disk : {valid_count:,}")
    if valid_count == 0:
        print("[ERROR] No valid images found to embed.")
        sys.exit(1)

    print(f"  Loading model        : {model_name}")
    start_time = time.time()
    encoder = JewelleryEncoder(model_name=model_name)
    print(f"  Model loaded on      : {encoder.device.upper()} (Dim: {encoder.embedding_dim})")

    # Ensure output directories exist
    embeddings_out.parent.mkdir(parents=True, exist_ok=True)
    product_ids_out.parent.mkdir(parents=True, exist_ok=True)

    # Process in batches
    embeddings_list: List[np.ndarray] = []
    print(f"\n  Extracting embeddings (Batch size: {batch_size})...")

    with tqdm(total=valid_count, unit="img", desc="  Embedding") as pbar:
        for i in range(0, valid_count, batch_size):
            batch_paths = image_paths[i : i + batch_size]
            batch_embs = encoder.encode_batch(batch_paths)
            embeddings_list.append(batch_embs)
            pbar.update(len(batch_paths))

    all_embeddings = np.vstack(embeddings_list).astype(np.float32)
    elapsed_time = time.time() - start_time

    print(f"\n  Saving embeddings to : {embeddings_out}")
    np.save(embeddings_out, all_embeddings)

    print(f"  Saving product IDs to: {product_ids_out}")
    with open(product_ids_out, "w", encoding="utf-8") as f:
        json.dump(product_ids, f, indent=2)

    # Final verification
    print("\n" + "=" * 60)
    print("  Embedding Generation Summary")
    print("=" * 60)
    print(f"  Total items embedded : {len(all_embeddings):,}")
    print(f"  Embedding shape      : {all_embeddings.shape}")
    print(f"  Embedding dtype      : {all_embeddings.dtype}")
    print(f"  Elapsed time         : {elapsed_time:.1f}s ({len(all_embeddings) / max(elapsed_time, 0.1):.1f} img/s)")
    print(f"  L2 Norm range        : [{np.linalg.norm(all_embeddings, axis=1).min():.4f}, {np.linalg.norm(all_embeddings, axis=1).max():.4f}]")
    print("=" * 60)
    print("\n[OK] Phase 2 complete. Ready for Phase 3 (FAISS Indexing).\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate embeddings for jewellery catalogue.")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Batch size for inference")
    parser.add_argument("--model", type=str, default=ENCODER_MODEL, help="Pretrained model name")
    args = parser.parse_args()

    generate_catalogue_embeddings(
        batch_size=args.batch_size,
        model_name=args.model,
    )
