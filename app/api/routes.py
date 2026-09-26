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
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from app.collector import STUMPER_CONDITIONS, get_collector, normalize_condition
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

# Global singleton matcher instance & thread-safe lock
_matcher: Optional[JewelleryMatcher] = None
_matcher_lock = threading.Lock()


def get_matcher() -> JewelleryMatcher:
    """Lazy-load and cache the JewelleryMatcher instance thread-safely."""
    global _matcher
    if _matcher is None:
        with _matcher_lock:
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


# ── Multi-item match endpoint ─────────────────────────────────────────────────

from app.retrieval.multi_matcher import MultiItemMatcher, generate_grid_crops  # noqa: E402


@router.post("/match/multi")
async def match_multi_image(
    file: UploadFile = File(..., description="Query photograph containing 2–3 jewellery items"),
    top_k: int = Form(TOP_K, description="Per-crop top-K candidates"),
    threshold: float = Form(SIMILARITY_THRESHOLD, description="Per-crop similarity threshold"),
    rows: int = Form(2, description="Grid rows (default 2, used when strategy='grid')"),
    cols: int = Form(2, description="Grid columns (default 2, used when strategy='grid')"),
    overlap: float = Form(0.18, description="Fractional overlap between crops (0–0.5)"),
    strategy: str = Form("sam", description="Region proposal strategy: 'sam' or 'grid'"),
) -> Dict[str, Any]:
    """
    Multi-item jewellery search using SAM (Segment Anything Model).

    Segments distinct jewellery items using SAM and runs the existing
    CLIP + FAISS matcher on each. Returns one unique MATCH per product_id
    (highest similarity wins when the same product appears in multiple segments).
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Please upload an image file.",
        )
    if overlap < 0.0 or overlap >= 0.5:
        raise HTTPException(status_code=400, detail="overlap must be in [0, 0.5)")
    if rows < 1 or rows > 6:
        raise HTTPException(status_code=400, detail="rows must be in [1, 6]")
    if cols < 1 or cols > 6:
        raise HTTPException(status_code=400, detail="cols must be in [1, 6]")
    if strategy not in ("sam", "adaptive", "grid"):
        raise HTTPException(status_code=400, detail="strategy must be 'sam' or 'grid'")

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        pil_image = Image.open(io.BytesIO(contents))
        pil_image.load()
        pil_image = pil_image.convert("RGB")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode image: {e}")

    try:
        matcher = get_matcher()
        multi = MultiItemMatcher(
            matcher=matcher,
            rows=rows,
            cols=cols,
            overlap=overlap,
            strategy=strategy,
        )
        result = multi.match_multi(
            image_input=pil_image,
            top_k=top_k,
            threshold=threshold,
            strategy=strategy,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-item matching error: {e}")



@router.get("/catalogue/next-id")
def get_next_product_id() -> Dict[str, str]:
    """Return the next recommended sequential product ID."""
    matcher = get_matcher()
    return {"next_product_id": matcher.get_next_product_id()}


@router.get("/catalogue/products")
def list_catalogue_products(
    q: Optional[str] = Query(None, description="Search query by Product ID or name"),
    category: Optional[str] = Query(None, description="Jewellery category filter"),
    status: Optional[str] = Query("all", description="Collection status: all, in_progress, completed, uncollected"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    List catalogue products with search, category filtering, pagination,
    and stumper collection progress (e.g. 7/10 conditions).
    """
    matcher = get_matcher()
    collector = get_collector()
    stumper_counts = collector.get_all_product_counts()

    # Normalize category filter
    norm_cat_filter = category.strip().lower() if category and category.strip() and category.strip().lower() != "all" else None
    query_str = q.strip().lower() if q and q.strip() else None

    # Collect matching products
    matched = []
    # Reverse order so newly added items show first
    all_pids = list(reversed(matcher.product_ids))

    for pid in all_pids:
        meta = matcher.catalogue_lookup.get(pid, {})
        cat = meta.get("category", "").lower()
        subcat = meta.get("subcategory", "").lower()
        pname = meta.get("product_name", "").lower()

        # Category filter
        if norm_cat_filter:
            # Handle plural/singular matching (e.g. earrings vs earring)
            is_match = (
                norm_cat_filter in cat
                or cat in norm_cat_filter
                or norm_cat_filter in subcat
                or subcat in norm_cat_filter
            )
            if not is_match:
                continue

        # Search filter
        if query_str:
            if query_str not in pid.lower() and query_str not in pname:
                continue

        # Stumper stats
        s_info = stumper_counts.get(pid, {"count": 0, "conditions": []})
        s_count = s_info["count"]
        s_conditions = s_info["conditions"]
        is_completed = s_count >= len(STUMPER_CONDITIONS)
        is_in_progress = 1 <= s_count < len(STUMPER_CONDITIONS)
        is_uncollected = s_count == 0

        # Status filter
        if status == "completed" and not is_completed:
            continue
        elif status == "in_progress" and not is_in_progress:
            continue
        elif status == "uncollected" and not is_uncollected:
            continue

        img_path = meta.get("image_path", "")
        img_url = "/" + img_path.replace("\\", "/") if img_path else ""

        matched.append({
            "product_id": pid,
            "product_name": meta.get("product_name", pid),
            "category": meta.get("category", "jewellery"),
            "subcategory": meta.get("subcategory", "jewellery"),
            "image_path": img_path,
            "image_url": img_url,
            "stumper_count": s_count,
            "stumper_total": len(STUMPER_CONDITIONS),
            "progress_percent": round((s_count / len(STUMPER_CONDITIONS)) * 100),
            "is_complete": is_completed,
            "conditions_completed": s_conditions,
        })

    # Sort: products with stumpers first, then by product ID
    if status == "all" and not query_str:
        matched.sort(key=lambda x: (x["stumper_count"] > 0, x["stumper_count"]), reverse=True)

    total_count = len(matched)
    paginated = matched[offset : offset + limit]

    return {
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "products": paginated,
    }


@router.get("/catalogue/products/{product_id}")
def get_catalogue_product(product_id: str) -> Dict[str, Any]:
    """Retrieve full product metadata and its 10-condition stumper collection details."""
    matcher = get_matcher()
    clean_pid = product_id.strip()
    if clean_pid not in matcher.catalogue_lookup:
        raise HTTPException(status_code=404, detail=f"Product ID '{clean_pid}' not found in catalogue.")

    meta = matcher.catalogue_lookup[clean_pid]
    collector = get_collector()
    stumpers = collector.get_product_stumpers(clean_pid)

    img_path = meta.get("image_path", "")
    img_url = "/" + img_path.replace("\\", "/") if img_path else ""

    return {
        "product": {
            "product_id": clean_pid,
            "product_name": meta.get("product_name", clean_pid),
            "category": meta.get("category", "jewellery"),
            "subcategory": meta.get("subcategory", "jewellery"),
            "image_path": img_path,
            "image_url": img_url,
            "width": meta.get("width"),
            "height": meta.get("height"),
        },
        "collection": stumpers,
    }


@router.post("/catalogue/create")
@router.post("/catalogue/add")
async def create_catalogue_item(
    file: UploadFile = File(..., description="Original/clean jewellery photo"),
    category: Optional[str] = Form(None, description="Jewellery category/type"),
    jewellery_type: Optional[str] = Form(None, description="Jewellery type alias"),
    product_name: Optional[str] = Form(None, description="Product title/name"),
    product_id: Optional[str] = Form(None, description="Optional custom Product ID"),
    subcategory: Optional[str] = Form(None, description="Optional subcategory"),
) -> Dict[str, Any]:
    """
    Create a new product with an original photo, compute CLIP embedding,
    add to FAISS index, update catalogue.csv, and immediately make it searchable.
    """
    cat = (jewellery_type or category or "other").strip().lower()
    # Normalize category names to match dataset
    cat_aliases = {
        "earrings": "earring",
        "rings": "ring",
        "necklaces": "necklace",
        "bracelets": "bracelet",
        "pendants": "pendant",
        "chains": "chain",
        "anklets": "anklet",
    }
    cat = cat_aliases.get(cat, cat)

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
        raise HTTPException(status_code=400, detail=f"Failed to decode uploaded image: {e}")

    try:
        matcher = get_matcher()
        item = matcher.add_catalogue_item(
            image_input=pil_image,
            category=cat,
            product_name=product_name,
            subcategory=subcategory,
            product_id=product_id,
        )
        return item
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create catalogue item: {e}")


# ── Stumper Collection Endpoints ─────────────────────────────────────────────

@router.get("/stumper/conditions")
def get_stumper_conditions() -> List[Dict[str, Any]]:
    """Return all 10 stumper conditions with names, icons, and guidelines."""
    return STUMPER_CONDITIONS


@router.post("/stumper/upload")
async def upload_stumper_photo(
    file: UploadFile = File(..., description="Real phone photo for stumper condition"),
    product_id: str = Form(..., description="Target Product ID (e.g. JW_006158)"),
    failure_condition: str = Form(..., description="One of the 10 failure conditions"),
    notes: Optional[str] = Form(None, description="Optional photographer notes"),
    jewellery_type: Optional[str] = Form(None, description="Optional category/type"),
) -> Dict[str, Any]:
    """
    Save real stumper condition photo captured by phone camera or uploaded from device.
    Keeps photo strictly tied to product_id and updates dataset progress.
    """
    clean_pid = product_id.strip()
    if not clean_pid:
        raise HTTPException(status_code=400, detail="Product ID cannot be empty.")

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Must be an image (JPEG, PNG, WebP).",
        )

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded photo is empty.")

        pil_image = Image.open(io.BytesIO(contents))
        pil_image.load()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {e}")

    try:
        collector = get_collector()
        result = collector.save_stumper(
            product_id=clean_pid,
            failure_condition=failure_condition,
            image=pil_image,
            jewellery_type=jewellery_type,
            notes=notes,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save stumper photo: {e}")


@router.get("/stumper/product/{product_id}")
def get_product_stumper_details(product_id: str) -> Dict[str, Any]:
    """Get all 10 condition photos and completion status for a given product."""
    collector = get_collector()
    return collector.get_product_stumpers(product_id)


@router.get("/stumper/dataset")
def get_dataset_statistics() -> Dict[str, Any]:
    """
    Return dataset-level statistics: total products, total stumper photos,
    breakdown by condition, breakdown by jewellery type, and recent uploads.
    """
    matcher = get_matcher()
    collector = get_collector()
    return collector.get_dataset_stats(matcher.catalogue_lookup)


@router.delete("/stumper/{product_id}/{failure_condition}")
def delete_stumper_condition(product_id: str, failure_condition: str) -> Dict[str, Any]:
    """Delete a stumper photo so the user can retake it."""
    collector = get_collector()
    return collector.delete_stumper(product_id, failure_condition)


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
    if "all_results" not in metrics and RESULTS_CSV.exists():
        import csv
        with open(RESULTS_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                rows.append({
                    "image_id": row.get("image_id", ""),
                    "ground_truth": row.get("ground_truth", ""),
                    "failure_condition": row.get("failure_condition", ""),
                    "decision": row.get("decision", ""),
                    "top1_category": row.get("top1_category", ""),
                    "top1_similarity": float(row.get("top1_similarity", 0.0) or 0.0),
                    "gt_rank": int(row.get("gt_rank", -1) or -1),
                    "top1_correct": int(row.get("top1_correct", 0) or 0),
                    "top5_correct": int(row.get("top5_correct", 0) or 0),
                    "latency_ms": float(row.get("latency_ms", 0.0) or 0.0),
                })
            metrics["all_results"] = rows
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


# ── Automated Stumper Endpoints ──────────────────────────────────────────────

from app.evaluation.automated_runner import (
    METRICS_JSON as AUTO_METRICS_JSON,
    COMPARISON_JSON as AUTO_COMPARISON_JSON,
    RESULTS_CSV as AUTO_RESULTS_CSV,
    run_automated_evaluation,
    write_automated_results,
)


@router.get("/automated-stumper/results")
def get_automated_stumper_results() -> Dict[str, Any]:
    """Return metrics and hand-shot vs automated comparison for automated stumper."""
    if not AUTO_METRICS_JSON.exists():
        raise HTTPException(
            status_code=404,
            detail="Automated stumper metrics not found. Run evaluation first.",
        )
    with open(AUTO_METRICS_JSON, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    comparison = {}
    if AUTO_COMPARISON_JSON.exists():
        with open(AUTO_COMPARISON_JSON, "r", encoding="utf-8") as f:
            comparison = json.load(f)

    return {
        "status": "ok",
        "metrics": metrics,
        "comparison": comparison,
    }


@router.post("/automated-stumper/run")
def run_automated_stumper_endpoint() -> Dict[str, Any]:
    """Execute automated stumper evaluation on all 900 generated images."""
    try:
        matcher = get_matcher()
        report = run_automated_evaluation(matcher)
        write_automated_results(report)
        return {
            "status": "success",
            "metrics": report["metrics"],
            "comparison": report["comparison"],
            "total_evaluated": len(report["rows"]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automated evaluation failed: {e}")


@router.get("/automated-stumper/download")
def download_automated_results_csv():
    """Download automated stumper results CSV."""
    if not AUTO_RESULTS_CSV.exists():
        raise HTTPException(status_code=404, detail="No automated results CSV found.")
    return FileResponse(
        path=str(AUTO_RESULTS_CSV),
        media_type="text/csv",
        filename="automated_stumper_results.csv",
    )


