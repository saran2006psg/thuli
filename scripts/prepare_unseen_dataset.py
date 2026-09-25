"""
scripts/prepare_unseen_dataset.py
─────────────────────────────────
Generates a 24-image unseen test set (evaluation/unseen_stumper.csv & evaluation/unseen_images/)
derived from unseen catalogue products under simulated real-world capture conditions
(clutter, distance, bad lighting, odd angle, etc.) for Phase 9 Generalization Testing.
"""

import csv
import random
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_CSV = PROJECT_ROOT / "data" / "catalogue.csv"
UNSEEN_DIR = PROJECT_ROOT / "evaluation" / "unseen_images"
UNSEEN_CSV = PROJECT_ROOT / "evaluation" / "unseen_stumper.csv"

CONDITIONS = [
    "normal", "bad_lighting", "bright_lighting", "odd_angle",
    "occlusion", "clutter", "motion_blur", "reflection",
    "hand_wrist", "distance"
]


def apply_condition(img_bgr: np.ndarray, cond: str) -> np.ndarray:
    H, W = img_bgr.shape[:2]

    if cond == "bad_lighting":
        # Dim exposure and add subtle noise
        table = np.array([((i / 255.0) ** 1.8) * 90 for i in np.arange(0, 256)]).astype("uint8")
        return cv2.LUT(img_bgr, table)

    elif cond == "bright_lighting":
        # Overexpose with glare
        bright = cv2.convertScaleAbs(img_bgr, alpha=1.4, beta=50)
        return bright

    elif cond == "odd_angle":
        # Perspective tilt
        pts1 = np.float32([[0, 0], [W, 0], [0, H], [W, H]])
        pts2 = np.float32([[W * 0.15, H * 0.1], [W * 0.85, 0], [0, H * 0.9], [W, H]])
        M = cv2.getPerspectiveTransform(pts1, pts2)
        return cv2.warpPerspective(img_bgr, M, (W, H), borderMode=cv2.BORDER_REPLICATE)

    elif cond == "occlusion":
        # Add occluding object (e.g. finger/box across edge)
        res = img_bgr.copy()
        cv2.rectangle(res, (int(W * 0.5), int(H * 0.4)), (W, int(H * 0.9)), (40, 40, 50), -1)
        return res

    elif cond == "clutter":
        # Place object onto a textured tabletop background
        canvas = np.random.randint(80, 180, (H, W, 3), dtype="uint8")
        # Draw wooden/table lines
        for y in range(0, H, 20):
            cv2.line(canvas, (0, y), (W, y + 10), (70, 60, 50), 1)
        # Overlay item in center
        mask = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, alpha = cv2.threshold(mask, 240, 255, cv2.THRESH_BINARY_INV)
        alpha = cv2.GaussianBlur(alpha, (5, 5), 0)
        alpha_3 = cv2.merge([alpha, alpha, alpha]) / 255.0
        blended = (img_bgr * alpha_3 + canvas * (1.0 - alpha_3)).astype("uint8")
        return blended

    elif cond == "motion_blur":
        # Directional motion blur kernel
        size = 15
        kernel = np.zeros((size, size))
        kernel[int((size - 1) / 2), :] = np.ones(size)
        kernel = kernel / size
        return cv2.filter2D(img_bgr, -1, kernel)

    elif cond == "reflection":
        # Semi-transparent diagonal glare
        glare = np.zeros_like(img_bgr)
        cv2.line(glare, (0, H), (W, 0), (255, 255, 255), int(W * 0.25))
        glare = cv2.GaussianBlur(glare, (51, 51), 0)
        return cv2.addWeighted(img_bgr, 0.8, glare, 0.2, 0)

    elif cond == "hand_wrist":
        # Add skin-tone surface surround
        canvas = np.full((H, W, 3), (120, 150, 200), dtype="uint8") # Skin-tone BGR
        scaled = cv2.resize(img_bgr, (int(W * 0.7), int(H * 0.7)))
        sh, sw = scaled.shape[:2]
        oy, ox = (H - sh) // 2, (W - sw) // 2
        canvas[oy:oy+sh, ox:ox+sw] = scaled
        return canvas

    elif cond == "distance":
        # Distance framing (scale item down to 30% of canvas)
        canvas = np.full((H, W, 3), 220, dtype="uint8")
        scaled = cv2.resize(img_bgr, (int(W * 0.3), int(H * 0.3)))
        sh, sw = scaled.shape[:2]
        oy, ox = (H - sh) // 2, (W - sw) // 2
        canvas[oy:oy+sh, ox:ox+sw] = scaled
        return canvas

    else: # normal
        return img_bgr


def main():
    UNSEEN_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    with open(CATALOGUE_CSV, encoding="utf-8") as f:
        catalogue = list(csv.DictReader(f))

    # Pick 24 diverse catalogue items (6 per category)
    by_category = {}
    for r in catalogue:
        by_category.setdefault(r["category"].lower(), []).append(r)

    selected_items = []
    for cat in ["ring", "bracelet", "necklace", "earring"]:
        pool = by_category.get(cat, [])
        # sample 6 items from pool
        selected_items.extend(random.sample(pool, 6))

    rows = []
    # Distribute conditions across the 24 images
    for idx, item in enumerate(selected_items, start=1):
        cond = CONDITIONS[(idx - 1) % len(CONDITIONS)]
        img_id = f"unseen_{idx:02d}"
        orig_path = PROJECT_ROOT / item["image_path"]

        if not orig_path.exists():
            continue

        bgr = cv2.imread(str(orig_path))
        if bgr is None:
            continue

        processed_bgr = apply_condition(bgr, cond)
        out_filename = f"{img_id}.jpeg"
        out_path = UNSEEN_DIR / out_filename
        cv2.imwrite(str(out_path), processed_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

        rows.append({
            "image_id": img_id,
            "product_id": item["category"].lower(),
            "target_product_id": item["product_id"],
            "failure_condition": cond,
            "notes": f"Unseen test set {cond}",
            "image_path": str(out_path.relative_to(PROJECT_ROOT)),
        })

    with open(UNSEEN_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["image_id", "product_id", "target_product_id", "failure_condition", "notes", "image_path"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} unseen test images in {UNSEEN_DIR}")
    print(f"Metadata saved to {UNSEEN_CSV}")


if __name__ == "__main__":
    main()
