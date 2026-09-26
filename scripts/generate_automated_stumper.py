"""
scripts/generate_automated_stumper.py
──────────────────────────────────────
Automated Stumper Dataset Generator.
Selects exactly 100 random unique items from the catalogue and applies 9 realistic
transformations (PIL + OpenCV) to stress-test the vision matcher without synthetic bias:

1. bad_lighting     - low ambient illumination, soft shadow
2. bright_lighting  - harsh overhead glare / flash clipping
3. odd_angle        - perspective tilt and subtle rotation
4. occlusion        - realistic foreground obstruction (finger/tag/holder)
5. clutter          - contextual background fabric / table distractor
6. motion_blur      - linear directional hand-tremor blur
7. reflection       - specular display glass reflection sheen
8. distance         - zoomed-out perspective with environmental canvas
9. noise            - camera sensor noise + JPEG compression artifacts

Outputs:
- evaluation/automated_images/*.jpg (900 generated images)
- evaluation/automated_stumper.csv  (manifest linking to ground truth product_id & category)
"""

import csv
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_CSV = PROJECT_ROOT / "data" / "catalogue.csv"
OUTPUT_DIR = PROJECT_ROOT / "evaluation" / "automated_images"
MANIFEST_CSV = PROJECT_ROOT / "evaluation" / "automated_stumper.csv"

# Fixed seed for deterministic, scientifically reproducible generation
RANDOM_SEED = 42


# ── Realistic Transformation Functions ────────────────────────────────────────

def apply_bad_lighting(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate underexposed ambient indoor room lighting."""
    factor = rng.uniform(0.38, 0.48)
    enhancer = ImageEnhance.Brightness(pil_img)
    dimmed = enhancer.enhance(factor)
    
    # Slight contrast adjustment
    contrast_enhancer = ImageEnhance.Contrast(dimmed)
    result = contrast_enhancer.enhance(0.90)
    
    # Convert to numpy to apply a soft subtle vignette gradient
    arr = np.array(result, dtype=np.float32)
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    center_y, center_x = h / 2.0, w / 2.0
    dist_from_center = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
    max_dist = np.sqrt(center_x ** 2 + center_y ** 2)
    vignette = 1.0 - 0.25 * (dist_from_center / max_dist)
    vignette = np.clip(vignette, 0.65, 1.0)
    
    for c in range(arr.shape[2] if arr.ndim == 3 else 1):
        if arr.ndim == 3:
            arr[:, :, c] *= vignette
        else:
            arr *= vignette
            
    return Image.fromarray(np.uint8(np.clip(arr, 0, 255)))


def apply_bright_lighting(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate harsh directional jewellery showcase lighting or flash blowout."""
    factor = rng.uniform(1.45, 1.65)
    enhancer = ImageEnhance.Brightness(pil_img)
    bright = enhancer.enhance(factor)
    
    # Slight highlight wash
    arr = np.array(bright, dtype=np.float32)
    # Clip near pure white highlights to simulate sensor saturation
    mask = arr > 220
    arr[mask] = np.minimum(255, arr[mask] * 1.08)
    return Image.fromarray(np.uint8(np.clip(arr, 0, 255)))


def apply_odd_angle(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate casual photo taken from an oblique, odd viewing angle."""
    img_np = np.array(pil_img)
    h, w = img_np.shape[:2]
    
    # Source corners
    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    
    # Slight perspective perturbation (10-18% delta on corners)
    dx1 = rng.uniform(0.08, 0.16) * w
    dy1 = rng.uniform(0.06, 0.14) * h
    dx2 = rng.uniform(0.08, 0.16) * w
    dy2 = rng.uniform(0.06, 0.14) * h
    
    dst_pts = np.float32([
        [dx1, dy1],
        [w - dx2, dy2 * 0.5],
        [w - dx1 * 0.5, h - dy1],
        [dx2 * 0.5, h - dy2]
    ])
    
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(
        img_np,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101
    )
    return Image.fromarray(warped)


def apply_occlusion(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate realistic partial occlusion (e.g. thumb/finger edge, display tag, box corner)."""
    img_np = np.array(pil_img).copy()
    h, w = img_np.shape[:2]
    
    # Finger/card-like patch on one of the edges/corners covering ~15-25%
    corner = rng.choice(["bottom_right", "bottom_left", "top_right", "center_edge"])
    
    # Realistic skin/cloth tone for finger/fabric (e.g. soft warm tan or velvet)
    color = (
        rng.randint(185, 215),  # R
        rng.randint(145, 175),  # G
        rng.randint(125, 155),  # B
    )
    
    overlay = img_np.copy()
    if corner == "bottom_right":
        center = (int(w * 0.85), int(h * 0.85))
        axes = (int(w * 0.35), int(h * 0.28))
        angle = rng.randint(-30, 30)
        cv2.ellipse(overlay, center, axes, angle, 0, 360, color, -1)
    elif corner == "bottom_left":
        center = (int(w * 0.15), int(h * 0.85))
        axes = (int(w * 0.35), int(h * 0.28))
        angle = rng.randint(-30, 30)
        cv2.ellipse(overlay, center, axes, angle, 0, 360, color, -1)
    elif corner == "top_right":
        center = (int(w * 0.82), int(h * 0.20))
        axes = (int(w * 0.30), int(h * 0.25))
        angle = rng.randint(-45, 45)
        cv2.ellipse(overlay, center, axes, angle, 0, 360, color, -1)
    else:
        # Side thumb hold
        center = (int(w * 0.05), int(h * 0.50))
        axes = (int(w * 0.28), int(h * 0.32))
        cv2.ellipse(overlay, center, axes, 0, 0, 360, color, -1)
        
    # Soft alpha blend for organic edge
    alpha = 0.92
    cv2.addWeighted(overlay, alpha, img_np, 1 - alpha, 0, img_np)
    
    return Image.fromarray(img_np)


def apply_clutter(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate jewellery resting on a textured or patterned surface with minor distractors."""
    img_np = np.array(pil_img).copy()
    h, w = img_np.shape[:2]
    
    # Generate subtle background texture (linen / velvet grain lines)
    texture = np.zeros((h, w, 3), dtype=np.uint8)
    base_col = (rng.randint(210, 235), rng.randint(200, 225), rng.randint(190, 215))
    texture[:] = base_col
    
    # Add random fabric line noise
    for _ in range(15):
        pt1 = (rng.randint(0, w), rng.randint(0, h))
        pt2 = (rng.randint(0, w), rng.randint(0, h))
        line_col = (rng.randint(160, 190), rng.randint(150, 180), rng.randint(140, 170))
        cv2.line(texture, pt1, pt2, line_col, thickness=rng.randint(1, 2))
        
    # Minor peripheral distractor object (e.g. key, coin, or fabric rim in a corner)
    distractor_pos = (rng.randint(int(w * 0.05), int(w * 0.25)), rng.randint(int(h * 0.05), int(h * 0.25)))
    distractor_rad = rng.randint(int(w * 0.08), int(w * 0.15))
    cv2.circle(img_np, distractor_pos, distractor_rad, (120, 110, 95), -1)
    cv2.circle(img_np, distractor_pos, distractor_rad, (180, 170, 150), 2)
    
    # Blend subtle grain into the background areas
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    is_bg = (gray > 230) | (gray < 25)
    img_np[is_bg] = cv2.addWeighted(img_np[is_bg], 0.70, texture[is_bg], 0.30, 0)
    
    return Image.fromarray(img_np)


def apply_motion_blur(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate camera shake / hand tremor motion blur."""
    img_np = np.array(pil_img)
    kernel_size = rng.choice([11, 13, 15])
    angle = rng.uniform(0, 180)
    
    # Create directional motion blur kernel
    kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
    radian = math.radians(angle)
    cx, cy = kernel_size // 2, kernel_size // 2
    
    for i in range(kernel_size):
        offset = i - cx
        x = int(round(cx + offset * math.cos(radian)))
        y = int(round(cy + offset * math.sin(radian)))
        if 0 <= x < kernel_size and 0 <= y < kernel_size:
            kernel[y, x] = 1.0
            
    kernel_sum = kernel.sum()
    if kernel_sum > 0:
        kernel /= kernel_sum
    else:
        kernel[cx, cy] = 1.0
        
    blurred = cv2.filter2D(img_np, -1, kernel)
    return Image.fromarray(blurred)


def apply_reflection(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate glass showcase reflection or ambient window specular sheen."""
    img_np = np.array(pil_img, dtype=np.float32)
    h, w = img_np.shape[:2]
    
    # Diagonal light sheen band
    sheen = np.zeros((h, w), dtype=np.float32)
    angle = rng.uniform(30, 60)
    radian = math.radians(angle)
    
    # Create a diagonal band across the image
    Y, X = np.ogrid[:h, :w]
    proj = X * math.cos(radian) + Y * math.sin(radian)
    mid_proj = (w * math.cos(radian) + h * math.sin(radian)) / 2.0
    band_width = max(w, h) * 0.25
    
    sheen = np.exp(-((proj - mid_proj) ** 2) / (2 * (band_width ** 2)))
    sheen = sheen * rng.uniform(70.0, 110.0)  # Sheen intensity
    
    for c in range(3):
        img_np[:, :, c] += sheen
        
    return Image.fromarray(np.uint8(np.clip(img_np, 0, 255)))


def apply_distance(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate jewellery photographed from a distance (occupying only ~40-50% of the frame)."""
    scale = rng.uniform(0.42, 0.52)
    orig_w, orig_h = pil_img.size
    new_w = max(1, int(orig_w * scale))
    new_h = max(1, int(orig_h * scale))
    
    downscaled = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Place onto a neutral retail display background canvas (e.g. linen / off-white counter)
    canvas = Image.new("RGB", (orig_w, orig_h), color=(240, 238, 233))
    
    # Random slight offset from exact center
    max_ox = orig_w - new_w
    max_oy = orig_h - new_h
    offset_x = rng.randint(int(max_ox * 0.3), int(max_ox * 0.7))
    offset_y = rng.randint(int(max_oy * 0.3), int(max_oy * 0.7))
    
    canvas.paste(downscaled, (offset_x, offset_y))
    return canvas


def apply_noise(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate high-ISO smartphone sensor grain and low-bandwidth JPEG compression."""
    img_np = np.array(pil_img, dtype=np.float32)
    
    # Add Gaussian sensor noise
    sigma = rng.uniform(16.0, 24.0)
    noise = np.random.normal(0, sigma, img_np.shape)
    noisy_img = np.clip(img_np + noise, 0, 255).astype(np.uint8)
    
    # Re-encode with realistic low JPEG quality (compression artifacts)
    quality = rng.randint(24, 34)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    bgr = cv2.cvtColor(noisy_img, cv2.COLOR_RGB2BGR)
    _, encimg = cv2.imencode(".jpg", bgr, encode_param)
    decimg = cv2.imdecode(encimg, cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(decimg, cv2.COLOR_BGR2RGB)
    
    return Image.fromarray(rgb)


VARIATION_DISPATCH = {
    "bad_lighting": apply_bad_lighting,
    "bright_lighting": apply_bright_lighting,
    "odd_angle": apply_odd_angle,
    "occlusion": apply_occlusion,
    "clutter": apply_clutter,
    "motion_blur": apply_motion_blur,
    "reflection": apply_reflection,
    "distance": apply_distance,
    "noise": apply_noise,
}


# ── Main Generator Logic ──────────────────────────────────────────────────────

def generate_automated_stumper(num_source_images: int = 100) -> List[Dict[str, str]]:
    """
    Selects 100 random distinct items from catalogue.csv,
    generates 9 realistic failure condition variations for each,
    saves the images, and creates the manifest CSV.
    """
    print("=" * 70)
    print("  AUTOMATED STUMPER DATASET GENERATION")
    print("=" * 70)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Read catalogue and filter valid existing images
    if not CATALOGUE_CSV.exists():
        raise FileNotFoundError(f"Catalogue not found at: {CATALOGUE_CSV}")
        
    catalogue_rows: List[Dict[str, str]] = []
    with open(CATALOGUE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_rel = row.get("image_path", "").strip()
            full_path = PROJECT_ROOT / img_rel
            if full_path.exists():
                catalogue_rows.append(row)
                
    total_valid = len(catalogue_rows)
    print(f"Found {total_valid} valid catalogue images.")
    if total_valid < num_source_images:
        raise ValueError(f"Insufficient images: need {num_source_images}, found {total_valid}")
        
    # 2. Deterministically select exactly 100 unique catalogue items
    rng = random.Random(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    
    selected_sources = rng.sample(catalogue_rows, num_source_images)
    print(f"Randomly selected {len(selected_sources)} unique catalogue items (seed={RANDOM_SEED}).")
    
    # 3. Generate 9 variations per image (Total: 900 images)
    generated_records: List[Dict[str, str]] = []
    condition_keys = list(VARIATION_DISPATCH.keys())
    
    count = 0
    for idx, source in enumerate(selected_sources, start=1):
        prod_id = source["product_id"]
        category = source.get("category", "unknown")
        prod_name = source.get("product_name", prod_id)
        source_rel_path = source["image_path"]
        source_full_path = PROJECT_ROOT / source_rel_path
        
        try:
            with Image.open(source_full_path) as orig:
                base_img = orig.convert("RGB")
        except Exception as e:
            print(f"  [WARN] Failed to open {source_full_path}: {e}")
            continue
            
        for cond in condition_keys:
            count += 1
            image_id = f"auto_{idx:03d}_{cond}"
            out_filename = f"{image_id}.jpg"
            out_path = OUTPUT_DIR / out_filename
            
            # Apply transformation
            transform_fn = VARIATION_DISPATCH[cond]
            # Use dedicated RNG instance per condition for reproducibility
            item_rng = random.Random(RANDOM_SEED + count * 31)
            transformed = transform_fn(base_img, item_rng)
            
            # Save generated JPEG
            transformed.save(out_path, format="JPEG", quality=90)
            
            # Record manifest row
            generated_records.append({
                "image_id": image_id,
                "product_id": prod_id,
                "category": category,
                "product_name": prod_name,
                "failure_condition": cond,
                "source_image_path": str(source_rel_path),
                "generated_image_path": str(out_path),
                "source_index": str(idx),
            })
            
        if idx % 20 == 0 or idx == num_source_images:
            print(f"  Processed {idx}/{num_source_images} source items ({count} images generated)...")
            
    # 4. Write manifest CSV
    fieldnames = [
        "image_id",
        "product_id",
        "category",
        "product_name",
        "failure_condition",
        "source_image_path",
        "generated_image_path",
        "source_index",
    ]
    with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(generated_records)
        
    print(f"\nSuccessfully generated {len(generated_records)} automated stumper images.")
    print(f"  - Images saved to : {OUTPUT_DIR}")
    print(f"  - Manifest CSV   : {MANIFEST_CSV}")
    print("=" * 70)
    
    return generated_records


if __name__ == "__main__":
    generate_automated_stumper(100)
