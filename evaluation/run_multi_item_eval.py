"""
evaluation/run_multi_item_eval.py
──────────────────────────────────
Synthetic evaluation of the multi-item grid-crop search.

Generates 25 synthetic "multi-item" test images by compositing 2–3 catalogue
product images side-by-side on a white canvas, then runs MultiItemMatcher and
reports:
  - num_images
  - total expected items
  - correctly_identified (product_id exact match)
  - missed items
  - wrong_matches (accepted but wrong product)
  - unknown_results
  - duplicate_matches (same product found in multiple crops)
  - mean/median latency

Run from project root:
    python evaluation/run_multi_item_eval.py
"""

import csv
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval.matcher import JewelleryMatcher
from app.retrieval.multi_matcher import MultiItemMatcher
from app.config import (
    CATALOGUE_CSV, FAISS_INDEX_PATH, PRODUCT_IDS_PATH,
    ENCODER_MODEL, SIMILARITY_THRESHOLD, TOP_K,
)

EVAL_DIR = PROJECT_ROOT / "evaluation" / "multi_item_images"
EVAL_CSV = PROJECT_ROOT / "evaluation" / "multi_item_eval.csv"
REPORT_MD = PROJECT_ROOT / "evaluation" / "multi_item_results.md"

EVAL_DIR.mkdir(parents=True, exist_ok=True)

ROWS, COLS, OVERLAP = 2, 2, 0.18
CANVAS_W, CANVAS_H = 600, 300  # composited image dimensions

RANDOM_SEED = 42

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_catalogue_samples(matcher: JewelleryMatcher, n: int = 60) -> List[Dict]:
    """Return up to n catalogue items that have a readable image on disk."""
    samples = []
    for pid, meta in matcher.catalogue_lookup.items():
        img_path = PROJECT_ROOT / meta.get("image_path", "")
        if img_path.exists():
            samples.append({"product_id": pid, "category": meta.get("category", ""), "image_path": img_path})
        if len(samples) >= n:
            break
    return samples


def _composite(images: List[Image.Image], canvas_w: int, canvas_h: int) -> Image.Image:
    """
    Place *images* horizontally on a white canvas of size (canvas_w × canvas_h).
    Each image is resized to fit its horizontal slot.
    """
    n = len(images)
    slot_w = canvas_w // n
    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(255, 255, 255))
    for i, img in enumerate(images):
        # Resize keeping aspect ratio, pad to slot
        thumb = img.copy().convert("RGB")
        thumb.thumbnail((slot_w - 10, canvas_h - 10))
        x = i * slot_w + (slot_w - thumb.width) // 2
        y = (canvas_h - thumb.height) // 2
        canvas.paste(thumb, (x, y))
    return canvas


def _build_test_set(samples: List[Dict], n_images: int = 25) -> List[Dict]:
    """
    Generate a balanced mix of 12 two-item and 13 three-item test images.
    Returns list of {image_path, expected_product_ids, n_items}.
    """
    rng = random.Random(RANDOM_SEED)
    test_set = []
    shuffled = samples[:]
    rng.shuffle(shuffled)

    idx = 0
    for i in range(n_images):
        n_items = 2 if i < 12 else 3
        chosen = shuffled[idx: idx + n_items]
        idx = (idx + n_items) % len(shuffled)

        product_images = []
        for item in chosen:
            try:
                img = Image.open(item["image_path"]).convert("RGB")
                product_images.append(img)
            except Exception:
                product_images.append(Image.new("RGB", (100, 100), color=(200, 180, 160)))

        canvas = _composite(product_images, CANVAS_W, CANVAS_H)
        img_fname = EVAL_DIR / f"multi_{i+1:03d}.jpeg"
        canvas.save(img_fname, format="JPEG", quality=90)

        test_set.append({
            "image_path": str(img_fname),
            "expected_product_ids": [c["product_id"] for c in chosen],
            "n_items": n_items,
        })
    return test_set


# ── Evaluation loop ────────────────────────────────────────────────────────────

def run_eval():
    print("[1/4] Loading matcher …")
    matcher = JewelleryMatcher(
        index_path=FAISS_INDEX_PATH,
        product_ids_path=PRODUCT_IDS_PATH,
        catalogue_csv_path=CATALOGUE_CSV,
        encoder_model=ENCODER_MODEL,
        threshold=SIMILARITY_THRESHOLD,
        top_k=TOP_K,
    )
    multi = MultiItemMatcher(matcher, rows=ROWS, cols=COLS, overlap=OVERLAP, strategy="sam")

    print("[2/4] Building synthetic test set …")
    samples = _load_catalogue_samples(matcher, n=80)
    if len(samples) < 3:
        print("ERROR: not enough catalogue images with readable files found.")
        return

    test_set = _build_test_set(samples, n_images=25)
    print(f"       Generated {len(test_set)} multi-item composite images in {EVAL_DIR}")

    print("[3/4] Running evaluation …")
    rows_out = []
    latencies = []

    total_expected = 0
    total_correct = 0
    total_missed = 0
    total_wrong = 0
    total_unknown_crops = 0
    total_duplicate_crops = 0

    for entry in test_set:
        expected_ids = set(entry["expected_product_ids"])
        total_expected += len(expected_ids)

        result = multi.match_multi(entry["image_path"])
        latencies.append(result["query_time_ms"])

        found_ids = {m["product_id"] for m in result["matches"]}
        correct = expected_ids & found_ids
        missed  = expected_ids - found_ids
        wrong   = found_ids - expected_ids

        # Count UNKNOWN crop decisions
        unknown_in_this = sum(1 for cr in result["crop_results"] if cr["decision"] == "UNKNOWN")
        # Count how many crops fired for duplicate product_ids
        matched_crop_pids = [cr["product_id"] for cr in result["crop_results"] if cr["decision"] == "MATCH"]
        dups_in_this = len(matched_crop_pids) - len(set(p for p in matched_crop_pids if p))

        total_correct       += len(correct)
        total_missed        += len(missed)
        total_wrong         += len(wrong)
        total_unknown_crops += unknown_in_this
        total_duplicate_crops += max(0, dups_in_this)

        rows_out.append({
            "image_path"         : entry["image_path"],
            "n_expected"         : len(expected_ids),
            "expected_ids"       : "|".join(sorted(expected_ids)),
            "found_ids"          : "|".join(sorted(found_ids)),
            "n_correct"          : len(correct),
            "n_missed"           : len(missed),
            "n_wrong"            : len(wrong),
            "n_unknown_crops"    : unknown_in_this,
            "n_duplicate_crops"  : max(0, dups_in_this),
            "latency_ms"         : round(result["query_time_ms"], 2),
        })

    # Persist CSV
    with open(EVAL_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows_out[0].keys())
        writer.writeheader()
        writer.writerows(rows_out)

    # Compute aggregate
    n_images = len(test_set)
    recall = total_correct / total_expected * 100 if total_expected else 0.0
    precision_denom = total_correct + total_wrong
    precision = total_correct / precision_denom * 100 if precision_denom else 0.0
    lat_mean   = round(statistics.mean(latencies), 2)
    lat_median = round(statistics.median(latencies), 2)
    lat_p95    = round(sorted(latencies)[int(len(latencies) * 0.95)], 2)

    metrics = {
        "n_images"             : n_images,
        "grid"                 : f"{ROWS}×{COLS}",
        "overlap_pct"          : OVERLAP * 100,
        "total_expected_items" : total_expected,
        "correctly_identified" : total_correct,
        "missed_items"         : total_missed,
        "wrong_matches"        : total_wrong,
        "unknown_crops_total"  : total_unknown_crops,
        "duplicate_crop_hits"  : total_duplicate_crops,
        "recall_pct"           : round(recall, 1),
        "precision_pct"        : round(precision, 1),
        "mean_latency_ms"      : lat_mean,
        "median_latency_ms"    : lat_median,
        "p95_latency_ms"       : lat_p95,
    }

    print("[4/4] Writing report …")

    md = f"""# Multi-Item Jewellery Search — Evaluation Report

> **Approach**: Overlapping grid crops ({ROWS}×{COLS}, {OVERLAP*100:.0f}% overlap) + existing CLIP ViT-B/32 FAISS matcher.
> No new ML model was trained or added.

## Configuration

| Parameter | Value |
|---|---|
| Grid | {ROWS} rows × {COLS} cols |
| Overlap | {OVERLAP*100:.0f}% |
| Threshold | {SIMILARITY_THRESHOLD} |
| Crops per image | {ROWS * COLS} |
| Top-K per crop | {TOP_K} |

## Summary

| Metric | Value |
|---|---|
| **Images evaluated** | **{n_images}** |
| **Total expected items** | **{total_expected}** |
| ✅ Correctly identified | {total_correct} |
| ❌ Missed items | {total_missed} |
| ⚠️ Wrong matches | {total_wrong} |
| 🔇 UNKNOWN crop results | {total_unknown_crops} |
| 🔁 Duplicate crop hits (deduplicated) | {total_duplicate_crops} |
| **Recall** | **{recall:.1f}%** |
| **Precision** | **{precision:.1f}%** |
| Mean latency | {lat_mean} ms |
| Median latency | {lat_median} ms |
| P95 latency | {lat_p95} ms |

## Notes

- **Recall** = correctly_identified / total_expected_items × 100
- **Precision** = correctly_identified / (correctly_identified + wrong_matches) × 100
- Composited test images are synthetic (side-by-side paste of catalogue images).
  Real-world performance will vary with occlusion, lighting, and pose variation.
- Duplicate hits (same product in ≥2 crops) are automatically deduplicated;
  only the highest-similarity crop is kept.
- UNKNOWN crop results are silently filtered; they do **not** appear in matches.

## Per-Image Results CSV

See `evaluation/multi_item_eval.csv` for the full row-by-row breakdown.
"""

    REPORT_MD.write_text(md, encoding="utf-8")
    print(f"\nReport saved -> {REPORT_MD}")
    print(f"CSV saved    -> {EVAL_CSV}")
    print()
    print("=== METRICS ===")
    for k, v in metrics.items():
        print(f"  {k:<30} {v}")


if __name__ == "__main__":
    run_eval()
