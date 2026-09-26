"""
app/retrieval/multi_matcher.py
──────────────────────────────
Multi-item jewellery search using overlapping grid crops.

Strategy:
  1. Divide the query image into an N×M grid of candidate regions with
     configurable overlap (default 2×2 grid, 18% overlap).
  2. Run the *existing* JewelleryMatcher independently on every crop.
  3. Collect only crops whose decision == "MATCH".
  4. Deduplicate: keep the highest-similarity result per product_id.
  5. Return sorted list of unique matched products.

No new ML model is added.  The existing CLIP + FAISS + threshold + margin
logic is completely unchanged.
"""

import time
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

from PIL import Image

from app.preprocessing.image import load_and_preprocess_image


# ── SAM and Grid generation ───────────────────────────────────────────────────

_SAM_MODEL = None


def get_sam_model():
    """Lazy-load the FastSAM model once in memory."""
    global _SAM_MODEL
    if _SAM_MODEL is None:
        from ultralytics import FastSAM
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _SAM_MODEL = FastSAM("FastSAM-s.pt")
    return _SAM_MODEL


def compute_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Compute Intersection-over-Union between two (x0, y0, x1, y1) bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    inter_area = max(0, xB - xA) * max(0, yB - yA)
    box_a_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    box_b_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return inter_area / float(box_a_area + box_b_area - inter_area + 1e-6)


def compute_containment(inner_box: Tuple[int, int, int, int], outer_box: Tuple[int, int, int, int]) -> float:
    """Compute the fraction of inner_box that is contained within outer_box."""
    xA = max(inner_box[0], outer_box[0])
    yA = max(inner_box[1], outer_box[1])
    xB = min(inner_box[2], outer_box[2])
    yB = min(inner_box[3], outer_box[3])
    inter_area = max(0, xB - xA) * max(0, yB - yA)
    inner_area = (inner_box[2] - inner_box[0]) * (inner_box[3] - inner_box[1])
    return inter_area / float(inner_area + 1e-6)


def generate_sam_crops(
    image: Image.Image,
    max_regions: int = 10,
    pad_ratio: float = 0.10,
    min_area_pct: float = 0.02,
) -> List[Dict[str, Any]]:
    """
    Produce candidate regions using Segment Anything (SAM):
      1. Uses FastSAM to segment all distinct jewellery items in the scene.
      2. Filters out tiny noise/fragments (< 2% image area).
      3. Applies Containment & IoU Suppression to eliminate sub-parts (links/clasps/charms)
         and keep only full distinct jewellery pieces.
      4. Expands bounding boxes with safe padding so complete items are visible.
      5. Only falls back to full image if no distinct objects are detected.
    """
    import torch

    W, H = image.size
    total_area = float(W * H)
    crops_dict: List[Dict[str, Any]] = []

    # 1. Run SAM
    raw_boxes = []
    try:
        model = get_sam_model()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        results = model(
            image,
            device=device,
            retina_masks=True,
            imgsz=640,
            conf=0.25,
            iou=0.7,
            verbose=False,
        )

        if results and len(results) > 0 and results[0].boxes is not None:
            for b in results[0].boxes:
                xyxy = b.xyxy[0].tolist()
                x0, y0, x1, y1 = xyxy
                bw = x1 - x0
                bh = y1 - y0
                area = bw * bh
                if area >= (total_area * min_area_pct) and area <= (total_area * 0.90):
                    raw_boxes.append((x0, y0, x1, y1, area))
    except Exception:
        pass

    # Sort largest objects first to keep full items and suppress smaller inner parts
    raw_boxes.sort(key=lambda x: x[4], reverse=True)

    # 2. Filter containment and overlapping sub-boxes
    filtered_boxes: List[Tuple[int, int, int, int]] = []
    for b in raw_boxes:
        candidate_box = (int(b[0]), int(b[1]), int(b[2]), int(b[3]))
        suppressed = False
        for eb in filtered_boxes:
            # If candidate is a sub-part of an existing box (containment > 60%) or high IoU (> 0.40)
            if compute_iou(candidate_box, eb) > 0.40 or compute_containment(candidate_box, eb) > 0.60:
                suppressed = True
                break
        if not suppressed:
            filtered_boxes.append(candidate_box)

    # Sort detected items from left-to-right (x0) for intuitive ordering
    filtered_boxes.sort(key=lambda b: b[0])

    # 3. Build crops
    for idx, box in enumerate(filtered_boxes[:max_regions]):
        x0, y0, x1, y1 = box
        bw = x1 - x0
        bh = y1 - y0
        px = int(bw * pad_ratio)
        py = int(bh * pad_ratio)
        bx0 = max(0, x0 - px)
        by0 = max(0, y0 - py)
        bx1 = min(W, x1 + px)
        by1 = min(H, y1 + py)
        padded_box = (bx0, by0, bx1, by1)

        crop_img = image.crop(padded_box).convert("RGB")
        crops_dict.append({
            "crop": crop_img,
            "region": padded_box,
            "crop_id": f"item_{idx + 1}",
            "row": 0,
            "col": idx,
        })

    # If SAM did not find any distinct objects, fall back to full image
    if not crops_dict:
        full_box = (0, 0, W, H)
        crops_dict.append({
            "crop": image.crop(full_box).convert("RGB"),
            "region": full_box,
            "crop_id": "item_1",
            "row": 0,
            "col": 0,
        })

    return crops_dict


def generate_grid_crops(
    image: Image.Image,
    rows: int = 2,
    cols: int = 2,
    overlap: float = 0.18,
) -> List[Dict[str, Any]]:
    """
    Produce overlapping rectangular crops from *image* using a rows×cols grid.
    """
    if overlap < 0.0 or overlap >= 0.5:
        raise ValueError(f"overlap must be in [0, 0.5), got {overlap}")
    if rows < 1 or cols < 1:
        raise ValueError(f"rows and cols must be >= 1, got rows={rows} cols={cols}")

    W, H = image.size
    cell_w = W / cols
    cell_h = H / rows

    pad_x = cell_w * overlap
    pad_y = cell_h * overlap

    crops = []
    for r in range(rows):
        for c in range(cols):
            x0 = max(0, int(c * cell_w - pad_x))
            y0 = max(0, int(r * cell_h - pad_y))
            x1 = min(W, int((c + 1) * cell_w + pad_x))
            y1 = min(H, int((r + 1) * cell_h + pad_y))

            crop_img = image.crop((x0, y0, x1, y1)).convert("RGB")
            crops.append({
                "crop": crop_img,
                "region": (x0, y0, x1, y1),
                "row": r,
                "col": c,
                "crop_id": f"r{r}c{c}",
            })
    return crops


# ── Multi-item matcher ─────────────────────────────────────────────────────────

class MultiItemMatcher:
    """
    Multi-item jewellery image search via SAM (Segment Anything Model).

    Segments individual jewellery items using SAM and runs the existing
    JewelleryMatcher on each item. Results are deduplicated by product_id,
    keeping the highest-similarity MATCH per product.
    """

    def __init__(
        self,
        matcher,               # JewelleryMatcher instance
        rows: int = 2,
        cols: int = 2,
        overlap: float = 0.18,
        strategy: str = "sam",
    ):
        """
        Args:
            matcher  : An initialised JewelleryMatcher.
            rows     : Grid rows for crop generation (used when strategy="grid").
            cols     : Grid columns for crop generation (used when strategy="grid").
            overlap  : Fractional overlap (0–0.5 exclusive).
            strategy : 'sam' (Segment Anything Model) or 'grid'.
        """
        self.matcher = matcher
        self.rows = rows
        self.cols = cols
        self.overlap = overlap
        self.strategy = strategy

    def match_multi(
        self,
        image_input: Union[str, Path, Image.Image],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run multi-item matching on an image.
        """
        t_start = time.perf_counter()

        pil_image = load_and_preprocess_image(image_input)

        use_strategy = strategy or self.strategy
        if use_strategy == "grid":
            crops = generate_grid_crops(
                pil_image,
                rows=self.rows,
                cols=self.cols,
                overlap=self.overlap,
            )
        else:
            crops = generate_sam_crops(
                pil_image,
                max_regions=10,
            )

        crop_results = []
        best_per_product: Dict[str, Dict[str, Any]] = {}

        for crop_info in crops:
            crop_img = crop_info["crop"]
            crop_id  = crop_info["crop_id"]
            region   = crop_info["region"]

            result = self.matcher.match(
                image_input=crop_img,
                top_k=top_k,
                threshold=threshold,
            )

            decision   = result["decision"]
            candidates = result["results"]
            similarity = result["best_similarity"]
            top1       = candidates[0] if candidates else {}
            prod_id    = top1.get("product_id") if decision == "MATCH" else None

            crop_entry = {
                "crop_id"   : crop_id,
                "region"    : list(region),
                "decision"  : decision,
                "product_id": prod_id,
                "similarity": similarity,
                "top5"      : candidates,
            }
            crop_results.append(crop_entry)

            if decision == "MATCH" and prod_id:
                existing = best_per_product.get(prod_id)
                if existing is None or similarity > existing["similarity"]:
                    meta = self.matcher.catalogue_lookup.get(prod_id, {})
                    img_path = meta.get("image_path", "")
                    best_per_product[prod_id] = {
                        "product_id"     : prod_id,
                        "product_name"   : top1.get("product_name", prod_id),
                        "category"       : top1.get("category", ""),
                        "subcategory"    : top1.get("subcategory", ""),
                        "similarity"     : similarity,
                        "image_path"     : img_path,
                        "image_url"      : "/" + img_path.replace("\\", "/") if img_path else "",
                        "source_crop_id" : crop_id,
                        "region"         : list(region),
                    }

        sorted_matches = sorted(
            best_per_product.values(),
            key=lambda x: x["similarity"],
            reverse=True,
        )
        for rank, m in enumerate(sorted_matches, start=1):
            m["rank"] = rank

        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return {
            "status"       : "success",
            "mode"         : "multi",
            "strategy"     : use_strategy,
            "total_crops"  : len(crops),
            "matched_count": len(sorted_matches),
            "query_time_ms": round(t_elapsed_ms, 3),
            "grid"         : {
                "rows"    : self.rows,
                "cols"    : self.cols,
                "overlap" : self.overlap,
                "strategy": use_strategy,
            },
            "crop_results" : crop_results,
            "matches"      : sorted_matches,
        }


