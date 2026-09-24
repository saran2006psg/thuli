"""
scripts/run_matcher.py
──────────────────────
CLI tool to test the JewelleryMatcher pipeline on an image or catalogue sample.
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (
    CATALOGUE_CSV,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.retrieval.matcher import JewelleryMatcher


def run_matcher(
    image_path: Path,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> None:
    print("\n" + "=" * 65)
    print("  Jewellery Matcher Pipeline (Phase 4)")
    print("=" * 65)
    print(f"  Query Image          : {image_path}")
    print(f"  Top-K Candidates     : {top_k}")
    print(f"  Similarity Threshold : {threshold}")
    print("=" * 65)

    matcher = JewelleryMatcher(
        index_path=FAISS_INDEX_PATH,
        product_ids_path=PRODUCT_IDS_PATH,
        catalogue_csv_path=CATALOGUE_CSV,
        threshold=threshold,
        top_k=top_k,
    )

    result = matcher.match(image_path, top_k=top_k, threshold=threshold)

    print(f"\n  Decision             : [{result['decision']}]")
    print(f"  Best Similarity      : {result['best_similarity']:.4f}")
    print(f"  Threshold            : {result['threshold']:.4f}")
    print(f"  Latency              : {result['query_time_ms']:.2f} ms")
    print("\n  Top Retrieved Candidates:")
    print("  " + "-" * 60)

    for item in result["results"]:
        print(
            f"  #{item['rank']:<2} | ID: {item['product_id']:<10} | Sim: {item['similarity']:.4f} | "
            f"Category: {item['category']:<10} | Name: {item['product_name']}"
        )

    print("  " + "-" * 60)
    print("\n" + json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the Jewellery Matcher with an image.")
    parser.add_argument("--image", type=Path, required=True, help="Path to query image")
    parser.add_argument("--top-k", type=int, default=TOP_K, help="Number of nearest candidates")
    parser.add_argument("--threshold", type=float, default=SIMILARITY_THRESHOLD, help="Match threshold")
    args = parser.parse_args()

    run_matcher(
        image_path=args.image,
        top_k=args.top_k,
        threshold=args.threshold,
    )
