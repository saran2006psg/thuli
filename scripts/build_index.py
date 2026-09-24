"""
scripts/build_index.py
──────────────────────
Builds and persists the FAISS IndexFlatIP vector index from
artifacts/embeddings/catalogue_embeddings.npy and validates
alignment with artifacts/embeddings/product_ids.json.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (
    EMBEDDINGS_PATH,
    EMBEDDING_DIM,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
)
from app.retrieval.index import FAISSIndex


def build_catalogue_index(
    embeddings_path: Path = EMBEDDINGS_PATH,
    product_ids_path: Path = PRODUCT_IDS_PATH,
    index_out_path: Path = FAISS_INDEX_PATH,
) -> None:
    print("\n" + "=" * 60)
    print("  Phase 3: Building FAISS Catalogue Index")
    print("=" * 60)

    # 1. Load and validate embeddings
    if not embeddings_path.exists():
        print(f"[ERROR] Embeddings file not found: {embeddings_path}")
        print("        Run: python scripts/generate_embeddings.py first.")
        sys.exit(1)

    print(f"  Loading embeddings   : {embeddings_path}")
    embeddings = np.load(embeddings_path)
    print(f"  Embedding shape      : {embeddings.shape}")
    print(f"  Embedding dtype      : {embeddings.dtype}")

    if embeddings.ndim != 2:
        print(f"[ERROR] Expected 2D embeddings matrix, got {embeddings.shape}")
        sys.exit(1)

    n_vectors, dim = embeddings.shape

    if dim != EMBEDDING_DIM:
        print(f"[ERROR] Dimension mismatch: expected {EMBEDDING_DIM}, got {dim}")
        sys.exit(1)

    # 2. Check normalization
    norms = np.linalg.norm(embeddings, axis=1)
    min_norm, max_norm = norms.min(), norms.max()
    print(f"  L2 Norm range        : [{min_norm:.4f}, {max_norm:.4f}]")
    if not np.allclose(norms, 1.0, atol=1e-3):
        print("[WARN] Some embeddings are not unit-normalized (L2 != 1.0).")

    # 3. Load product IDs
    if not product_ids_path.exists():
        print(f"[ERROR] Product IDs file not found: {product_ids_path}")
        sys.exit(1)

    print(f"  Loading product IDs  : {product_ids_path}")
    with open(product_ids_path, "r", encoding="utf-8") as f:
        product_ids = json.load(f)

    print(f"  Total product IDs    : {len(product_ids):,}")

    if len(product_ids) != n_vectors:
        print(
            f"[ERROR] Count mismatch: {len(product_ids)} product IDs != {n_vectors} embedding rows!"
        )
        sys.exit(1)

    # 4. Build FAISS IndexFlatIP
    print(f"\n  Building FAISS IndexFlatIP (dim={dim})...")
    start_time = time.time()
    faiss_index = FAISSIndex(dimension=dim)
    faiss_index.add(embeddings)
    elapsed = time.time() - start_time

    print(f"  Added vectors        : {faiss_index.size:,} in {elapsed:.3f}s")

    if faiss_index.size != n_vectors:
        print(f"[ERROR] Index size mismatch: {faiss_index.size} != {n_vectors}")
        sys.exit(1)

    # 5. Sanity self-retrieval test
    print("\n  Running sanity self-retrieval test (query = vector 0)...")
    sample_query = embeddings[0:1]
    scores, indices = faiss_index.search(sample_query, top_k=5)
    top1_idx = indices[0][0]
    top1_score = scores[0][0]
    top1_pid = product_ids[top1_idx]

    print(f"  Top-1 match index    : {top1_idx} (Product ID: {top1_pid})")
    print(f"  Top-1 cosine score   : {top1_score:.6f}")

    if top1_idx != 0 or not np.isclose(top1_score, 1.0, atol=1e-4):
        print("[WARN] Sanity self-retrieval did not return exact top-1 match!")
    else:
        print("  Sanity check         : PASSED (exact self-match with score ~ 1.0)")

    # 6. Save index to disk
    print(f"\n  Saving index to      : {index_out_path}")
    faiss_index.save(index_out_path)
    file_size_mb = index_out_path.stat().st_size / (1024 * 1024)
    print(f"  Index file size      : {file_size_mb:.2f} MB")

    # 7. Test reloading from disk
    print("  Testing reload from disk...")
    reloaded_index = FAISSIndex.load(index_out_path)
    assert reloaded_index.size == n_vectors, "Reloaded index size mismatch!"
    assert reloaded_index.dimension == dim, "Reloaded index dimension mismatch!"
    print("  Reload test          : PASSED")

    print("\n" + "=" * 60)
    print("  FAISS Index Build Summary")
    print("=" * 60)
    print(f"  Indexed vectors      : {faiss_index.size:,}")
    print(f"  Vector dimension     : {faiss_index.dimension}")
    print(f"  Index type           : IndexFlatIP (Exact Cosine Similarity)")
    print(f"  Artifact path        : {index_out_path}")
    print("=" * 60)
    print("\n[OK] Phase 3 FAISS index successfully built and saved.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build FAISS index for catalogue.")
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_PATH)
    parser.add_argument("--product-ids", type=Path, default=PRODUCT_IDS_PATH)
    parser.add_argument("--out", type=Path, default=FAISS_INDEX_PATH)
    args = parser.parse_args()

    build_catalogue_index(
        embeddings_path=args.embeddings,
        product_ids_path=args.product_ids,
        index_out_path=args.out,
    )
