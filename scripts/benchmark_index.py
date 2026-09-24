ṇḥ"""
scripts/benchmark_index.py
──────────────────────────
Benchmarks isolated FAISS search latency (IndexFlatIP) on catalogue embeddings.
Measures single-query retrieval time across multiple iterations (mean, median, p95, min, max).
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import EMBEDDINGS_PATH, FAISS_INDEX_PATH
from app.retrieval.index import FAISSIndex


def benchmark_faiss_search(
    index_path: Path = FAISS_INDEX_PATH,
    embeddings_path: Path = EMBEDDINGS_PATH,
    num_queries: int = 200,
    top_k: int = 5,
    warmup_queries: int = 20,
) -> Dict[str, float]:
    print("\n" + "=" * 60)
    print("  FAISS Search Latency Benchmark (Phase 3)")
    print("=" * 60)

    if not index_path.exists():
        print(f"[ERROR] FAISS index not found: {index_path}")
        print("        Run: python scripts/build_index.py first.")
        sys.exit(1)

    if not embeddings_path.exists():
        print(f"[ERROR] Embeddings file not found: {embeddings_path}")
        sys.exit(1)

    print(f"  Loading index        : {index_path}")
    index = FAISSIndex.load(index_path)
    print(f"  Indexed vectors      : {index.size:,} (Dim: {index.dimension})")

    embeddings = np.load(embeddings_path)
    n_vectors = len(embeddings)

    # Select query vectors
    rng = np.random.RandomState(42)
    query_indices = rng.choice(n_vectors, size=min(num_queries, n_vectors), replace=False)
    query_vectors = embeddings[query_indices]

    # Warmup runs
    print(f"  Warming up ({warmup_queries} queries)...")
    for i in range(min(warmup_queries, len(query_vectors))):
        q = query_vectors[i : i + 1]
        _ = index.search(q, top_k=top_k)

    # Timed benchmark runs
    latencies_ms: List[float] = []
    print(f"  Benchmarking {len(query_vectors)} single-query searches (K={top_k})...")

    for i in range(len(query_vectors)):
        q = query_vectors[i : i + 1]
        t0 = time.perf_counter()
        _ = index.search(q, top_k=top_k)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    latencies_arr = np.array(latencies_ms)
    mean_lat = float(np.mean(latencies_arr))
    median_lat = float(np.median(latencies_arr))
    p95_lat = float(np.percentile(latencies_arr, 95))
    p99_lat = float(np.percentile(latencies_arr, 99))
    min_lat = float(np.min(latencies_arr))
    max_lat = float(np.max(latencies_arr))
    qps = float(1000.0 / mean_lat) if mean_lat > 0 else 0.0

    print("\n" + "=" * 60)
    print("  Benchmark Results (FAISS-only Search)")
    print("=" * 60)
    print(f"  Index Type           : IndexFlatIP (Exact Cosine)")
    print(f"  Indexed Dataset Size : {index.size:,} vectors")
    print(f"  Dimension            : {index.dimension}")
    print(f"  Number of Queries    : {len(query_vectors)}")
    print(f"  Top-K                : {top_k}")
    print(f"  --------------------------------------------------")
    print(f"  Mean Latency         : {mean_lat:.4f} ms")
    print(f"  Median Latency (p50) : {median_lat:.4f} ms")
    print(f"  p95 Latency          : {p95_lat:.4f} ms")
    print(f"  p99 Latency          : {p99_lat:.4f} ms")
    print(f"  Min Latency          : {min_lat:.4f} ms")
    print(f"  Max Latency          : {max_lat:.4f} ms")
    print(f"  Throughput (QPS)     : {qps:,.1f} queries/sec")
    print("=" * 60 + "\n")

    return {
        "mean_ms": mean_lat,
        "median_ms": median_lat,
        "p95_ms": p95_lat,
        "p99_ms": p99_lat,
        "min_ms": min_lat,
        "max_ms": max_lat,
        "qps": qps,
        "num_queries": len(query_vectors),
        "top_k": top_k,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark FAISS search latency.")
    parser.add_argument("--index", type=Path, default=FAISS_INDEX_PATH)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_PATH)
    parser.add_argument("--queries", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    benchmark_faiss_search(
        index_path=args.index,
        embeddings_path=args.embeddings,
        num_queries=args.queries,
        top_k=args.top_k,
    )
