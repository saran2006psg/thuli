"""
app/api/routes.py
─────────────────
FastAPI API endpoints for jewellery retrieval and matching:
  - POST /match: Image upload & Top-K candidate retrieval
  - GET  /health: System health and index status
  - GET  /stats: Catalogue statistics and benchmark summary
  - GET  /samples: Sample catalogue products for quick UI testing
  - POST /evaluation/run: Trigger Phase 7 evaluation
  - GET  /evaluation/results: Retrieve latest evaluation metrics
"""

import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from app.config import (
    CATALOGUE_CSV,
    EMBEDDING_DIM,
    ENCODER_MODEL,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
    PROJECT_ROOT,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.retrieval.matcher import JewelleryMatcher

router = APIRouter()

# Global singleton matcher instance
_matcher: Optional[JewelleryMatcher] = None


def get_matcher() -> JewelleryMatcher:
    """Lazy-load and cache the JewelleryMatcher instance."""
    global _matcher
    if _matcher is None:
        _matcher = JewelleryMatcher(
            index_path=FAISS_INDEX_PATH,
            product_ids_path=PRODUCT_IDS_PATH,
            catalogue_csv_path=CATALOGUE_CSV,
            encoder_model=ENCODER_MODEL,
            threshold=SIMILARITY_THRESHOLD,
            top_k=TOP_K,
        )
    return _matcher


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Healthcheck endpoint returning system and index status."""
    try:
        matcher = get_matcher()
        return {
            "status": "healthy",
            "index_size": matcher.index.size,
            "dimension": matcher.index.dimension,
            "model": ENCODER_MODEL,
            "default_threshold": matcher.default_threshold,
            "default_top_k": matcher.default_top_k,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
        }


@router.get("/stats")
def get_stats() -> Dict[str, Any]:
    """Return catalogue distribution and FAISS benchmark metrics."""
    matcher = get_matcher()
    cat_counts: Dict[str, int] = {}
    for item in matcher.catalogue_lookup.values():
        c = item.get("category", "unknown")
        cat_counts[c] = cat_counts.get(c, 0) + 1

    return {
        "total_items": matcher.index.size,
        "embedding_dim": matcher.index.dimension,
        "categories": cat_counts,
        "benchmarks": {
            "faiss_median_latency_ms": 0.5187,
            "faiss_p95_latency_ms": 0.7350,
            "faiss_throughput_qps": 1849.9,
            "end_to_end_latency_ms": 197.5,
        },
    }


@router.get("/samples")
def get_sample_images() -> List[Dict[str, Any]]:
    """Return a curated set of sample catalogue items for quick UI testing."""
    matcher = get_matcher()
    samples = []
    seen_cats = set()

    # Grab 2 samples per category
    cat_targets = {"bracelet": 2, "earring": 2, "necklace": 2, "ring": 2}
    cat_collected = {c: 0 for c in cat_targets}

    for pid, meta in matcher.catalogue_lookup.items():
        cat = meta.get("category", "")
        if cat in cat_collected and cat_collected[cat] < cat_targets[cat]:
            samples.append({
                "product_id": pid,
                "product_name": meta.get("product_name", pid),
                "category": cat,
                "image_path": "/" + meta.get("image_path", "").replace("\\", "/"),
            })
            cat_collected[cat] += 1

        if all(cat_collected[c] >= cat_targets[c] for c in cat_targets):
            break

    return samples


@router.post("/match")
async def match_image(
    file: UploadFile = File(..., description="Query jewellery image file"),
    top_k: int = Form(TOP_K, description="Number of top candidates to retrieve"),
    threshold: float = Form(SIMILARITY_THRESHOLD, description="Similarity decision threshold"),
) -> Dict[str, Any]:
    """
    Accept an uploaded image, extract features, retrieve Top-K catalogue matches,
    and return structured match results with similarity scores.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Please upload an image file (JPEG, PNG, WebP).",
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        pil_image = Image.open(io.BytesIO(contents))
        pil_image.load()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to decode uploaded image: {e}",
        )

    try:
        matcher = get_matcher()
        result = matcher.match(
            image_input=pil_image,
            top_k=top_k,
            threshold=threshold,
        )

        # Normalize relative image paths to web URLs
        for item in result["results"]:
            if item.get("image_path"):
                item["image_url"] = "/" + item["image_path"].replace("\\", "/")

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal matching error: {e}",
        )


@router.post("/catalogue/add")
async def add_catalogue_item(
    file: UploadFile = File(..., description="Jewellery image file to add to catalogue"),
    category: str = Form(..., description="Product category (e.g. ring, necklace, earring, bracelet, pendant)"),
    product_name: Optional[str] = Form(None, description="Optional product name/title"),
    subcategory: Optional[str] = Form(None, description="Optional subcategory"),
) -> Dict[str, Any]:
    """
    Upload an image, add it to the catalogue, compute its CLIP embedding,
    and index it immediately into FAISS.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Please upload an image file (JPEG, PNG, WebP).",
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        pil_image = Image.open(io.BytesIO(contents))
        pil_image.load()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to decode uploaded image: {e}",
        )

    try:
        matcher = get_matcher()
        item = matcher.add_catalogue_item(
            image_input=pil_image,
            category=category,
            product_name=product_name,
            subcategory=subcategory,
        )
        return item
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add item to catalogue: {e}",
        )


# ── Phase 7: Evaluation Endpoints ────────────────────────────────────────────

from app.evaluation.runner import (
    METRICS_JSON, RESULTS_CSV, run_evaluation, write_results,
)


@router.post("/evaluation/run")
def run_evaluation_endpoint() -> Dict[str, Any]:
    """
    Trigger Phase 7 evaluation: run all stumper images through the matcher,
    compute metrics, and persist results.csv + metrics.json + analysis.md.
    """
    try:
        matcher = get_matcher()
        report  = run_evaluation(matcher)
        write_results(report["metrics"], report["rows"])
        return {
            "status": "success",
            "metrics": report["metrics"],
            "rows_evaluated": len(report["rows"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")


@router.get("/evaluation/results")
def get_evaluation_results() -> Dict[str, Any]:
    """Return the latest persisted evaluation metrics."""
    if not METRICS_JSON.exists():
        raise HTTPException(
            status_code=404,
            detail="No evaluation results found. Run /api/evaluation/run first.",
        )
    with open(METRICS_JSON, encoding="utf-8") as f:
        metrics = json.load(f)
    return {"status": "ok", "metrics": metrics}


@router.get("/evaluation/download")
def download_results_csv():
    """Download evaluation results as CSV."""
    if not RESULTS_CSV.exists():
        raise HTTPException(status_code=404, detail="No results CSV found.")
    return FileResponse(
        path=str(RESULTS_CSV),
        media_type="text/csv",
        filename="evaluation_results.csv",
    )

