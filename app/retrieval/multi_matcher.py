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


def get_contour_proposals(image: Image.Image, total_area: float) -> List[Tuple[int, int, int, int]]:
    """Fast contour-based proposal fallback when SAM under-segments high-contrast items."""
    try:
        import cv2
        import numpy as np
        cv_img = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
        boxes = []
        for thresh_fn in [
            lambda g: cv2.threshold(g, 240, 255, cv2.THRESH_BINARY_INV)[1],
            lambda g: cv2.threshold(g, 25, 255, cv2.THRESH_BINARY)[1],
        ]:
            mask = thresh_fn(gray)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                area = w * h
                if (total_area * 0.03) <= area <= (total_area * 0.65):
                    boxes.append((x, y, x + w, y + h))
        return boxes
    except Exception:
        return []


def generate_sam_crops(
    image: Image.Image,
    max_regions: int = 10,
    pad_ratio: float = 0.10,
    min_area_pct: float = 0.02,
    max_area_pct: float = 0.65,
) -> List[Dict[str, Any]]:
    """
    Produce candidate regions using Segment Anything (SAM):
      1. Uses FastSAM with sensitive confidence (0.15) to segment all distinct pieces.
      2. Prevents full-scene/canvas boxes (> 65% area) from suppressing individual items.
      3. Uses contour proposal fallback if SAM finds fewer than 2 distinct objects.
      4. Automatically proposes left/right regions if the image is wide (aspect ratio >= 1.35).
      5. Expands bounding boxes with safe padding so complete items are visible.
    """
    import io
    import base64
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
            conf=0.15,
            iou=0.6,
            verbose=False,
        )

        if results and len(results) > 0 and results[0].boxes is not None:
            for b in results[0].boxes:
                xyxy = b.xyxy[0].tolist()
                x0, y0, x1, y1 = [int(v) for v in xyxy]
                bw = x1 - x0
                bh = y1 - y0
                area = bw * bh
                if (total_area * min_area_pct) <= area <= (total_area * max_area_pct):
                    raw_boxes.append((x0, y0, x1, y1, area))
    except Exception:
        pass

    # 2. If SAM found fewer than 2 distinct items, supplement with contour proposals
    if len(raw_boxes) < 2:
        c_boxes = get_contour_proposals(image, total_area)
        for cb in c_boxes:
            area = (cb[2] - cb[0]) * (cb[3] - cb[1])
            raw_boxes.append((cb[0], cb[1], cb[2], cb[3], area))

    # 3. If still fewer than 2 boxes and image is wide (>= 1.35), add left and right halves
    if len(raw_boxes) < 2 and (W / max(1, H)) >= 1.35:
        mid_x = W // 2
        pad_split = int(W * 0.05)
        raw_boxes.append((0, 0, min(W, mid_x + pad_split), H, mid_x * H))
        raw_boxes.append((max(0, mid_x - pad_split), 0, W, H, mid_x * H))

    # 4. Filter containment and overlapping sub-boxes
    raw_boxes.sort(key=lambda x: x[4], reverse=True)
    filtered_boxes: List[Tuple[int, int, int, int]] = []
    for b in raw_boxes:
        candidate_box = (int(b[0]), int(b[1]), int(b[2]), int(b[3]))
        suppressed = False
        for eb in filtered_boxes:
            if compute_iou(candidate_box, eb) > 0.45 or compute_containment(candidate_box, eb) > 0.65:
                suppressed = True
                break
        if not suppressed:
            filtered_boxes.append(candidate_box)

    # Sort detected items from left-to-right (x0) for intuitive ordering
    filtered_boxes.sort(key=lambda b: b[0])

    # 5. Build crops
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

        # Create quick base64 thumbnail for UI preview
        crop_buf = io.BytesIO()
        crop_img.save(crop_buf, format="JPEG", quality=80)
        crop_data_url = f"data:image/jpeg;base64,{base64.b64encode(crop_buf.getvalue()).decode('utf-8')}"

        crops_dict.append({
            "crop": crop_img,
            "region": padded_box,
            "crop_id": f"item_{idx + 1}",
            "crop_image_url": crop_data_url,
            "row": 0,
            "col": idx,
        })

    # If no distinct objects detected, fall back to full image
    if not crops_dict:
        full_box = (0, 0, W, H)
        crop_img = image.crop(full_box).convert("RGB")
        crop_buf = io.BytesIO()
        crop_img.save(crop_buf, format="JPEG", quality=80)
        crop_data_url = f"data:image/jpeg;base64,{base64.b64encode(crop_buf.getvalue()).decode('utf-8')}"
        crops_dict.append({
            "crop": crop_img,
            "region": full_box,
            "crop_id": "item_1",
            "crop_image_url": crop_data_url,
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

            top1_id    = top1.get("product_id")
            prod_id    = top1_id if decision == "MATCH" else None
            crop_url   = crop_info.get("crop_image_url", "")

            # Meta for top1 candidate
            top1_meta = self.matcher.catalogue_lookup.get(top1_id, {}) if top1_id else {}
            top1_img = top1_meta.get("image_path", "")

            crop_entry = {
                "crop_id"        : crop_id,
                "region"         : list(region),
                "decision"       : decision,
                "product_id"     : prod_id,
                "top1_product_id": top1_id,
                "product_name"   : top1.get("product_name", top1_id or "Unknown"),
                "category"       : top1.get("category", ""),
                "subcategory"    : top1.get("subcategory", ""),
                "similarity"     : similarity,
                "image_path"     : top1_img,
                "image_url"      : "/" + top1_img.replace("\\", "/") if top1_img else "",
                "crop_image_url" : crop_url,
                "top5"           : candidates,
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
                        "crop_image_url" : crop_url,
                        "region"         : list(region),
                        "top5"           : candidates,
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
            "status"          : "success",
            "mode"            : "multi",
            "strategy"        : use_strategy,
            "total_crops"     : len(crops),
            "matched_count"   : len(sorted_matches),
            "query_time_ms"   : round(t_elapsed_ms, 3),
            "grid"            : {
                "rows"    : self.rows,
                "cols"    : self.cols,
                "overlap" : self.overlap,
                "strategy": use_strategy,
            },
            "crop_results"    : crop_results,
            "matches"         : sorted_matches,
        }


