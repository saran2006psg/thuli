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


# ── Realistic Adversarial Transformation Functions ────────────────────────────

def apply_bad_lighting(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate severe underexposure in dim indoor lighting with heavy shadow clipping."""
    factor = rng.uniform(0.18, 0.28)
    enhancer = ImageEnhance.Brightness(pil_img)
    dimmed = enhancer.enhance(factor)
    
    # Non-linear gamma compression (crushing midtones and shadows)
    arr = np.array(dimmed, dtype=np.float32) / 255.0
    gamma = rng.uniform(1.8, 2.3)
    arr = np.power(arr, gamma) * 255.0
    
    # Sensor noise & yellow/tungsten color cast
    arr[:, :, 0] *= rng.uniform(1.05, 1.15)  # Red boost
    arr[:, :, 2] *= rng.uniform(0.70, 0.85)  # Blue drop
    
    # Shadow clipping: dark pixels drop to black
    arr[arr < 35] = 0
    return Image.fromarray(np.uint8(np.clip(arr, 0, 255)))


def apply_bright_lighting(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate intense smartphone flash blowout and specular flare across jewellery facets."""
    arr = np.array(pil_img, dtype=np.float32)
    h, w = arr.shape[:2]
    
    # Global brightness boost
    arr = arr * rng.uniform(1.5, 1.8)
    
    # Intense localized specular flash blowout hotspot centered on the jewellery
    cx = int(w * rng.uniform(0.42, 0.58))
    cy = int(h * rng.uniform(0.42, 0.58))
    flare_radius = rng.uniform(w * 0.25, w * 0.40)
    
    Y, X = np.ogrid[:h, :w]
    dist_sq = (X - cx) ** 2 + (Y - cy) ** 2
    flare = np.exp(-dist_sq / (2 * (flare_radius ** 2)))
    flare = flare[:, :, np.newaxis] * rng.uniform(220.0, 320.0)
    arr = arr + flare
    
    return Image.fromarray(np.uint8(np.clip(arr, 0, 255)))


def apply_odd_angle(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate steep oblique perspective tilt (45-75 degrees) with rotation and foreshortening."""
    # Rotate first by an unusual angle (e.g. 50-75 degrees)
    rot_angle = rng.choice([-1, 1]) * rng.uniform(45, 75)
    rotated = pil_img.rotate(rot_angle, expand=False, fillcolor=(240, 238, 233))
    
    img_np = np.array(rotated)
    h, w = img_np.shape[:2]
    src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    
    # Steep perspective compression
    inset_top = rng.uniform(0.32, 0.42) * w
    drop_top = rng.uniform(0.28, 0.40) * h
    dst_pts = np.float32([[inset_top, drop_top], [w - inset_top, drop_top], [w, h], [0, h]])
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(img_np, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(240, 238, 233))
    return Image.fromarray(warped)


def apply_occlusion(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate realistic heavy occlusion (finger, velvet clamp, price tag) directly covering 35-50% of the central jewellery."""
    img_np = np.array(pil_img).copy()
    h, w = img_np.shape[:2]
    
    center_x = int(w * rng.uniform(0.45, 0.55))
    center_y = int(h * rng.uniform(0.45, 0.55))
    occlusion_style = rng.choice(["finger", "price_tag", "clamp_bar"])
    
    if occlusion_style == "finger":
        skin_color = (rng.randint(180, 215), rng.randint(130, 165), rng.randint(110, 140))
        angle = rng.randint(20, 70)
        axes = (int(w * rng.uniform(0.42, 0.55)), int(h * rng.uniform(0.22, 0.32)))
        cv2.ellipse(img_np, (center_x, center_y), axes, angle, 0, 360, skin_color, -1)
    elif occlusion_style == "price_tag":
        tag_w = int(w * rng.uniform(0.45, 0.60))
        tag_h = int(h * rng.uniform(0.32, 0.45))
        x1 = max(0, center_x - tag_w // 2)
        y1 = max(0, center_y - tag_h // 2)
        cv2.rectangle(img_np, (x1, y1), (x1 + tag_w, y1 + tag_h), (235, 230, 220), -1)
        cv2.rectangle(img_np, (x1, y1), (x1 + tag_w, y1 + tag_h), (120, 110, 100), 2)
        for bx in range(x1 + 10, x1 + tag_w - 10, 6):
            cv2.line(img_np, (bx, y1 + 10), (bx, y1 + tag_h - 10), (50, 45, 40), 2)
    else:
        clamp_color = (rng.randint(25, 45), rng.randint(20, 35), rng.randint(40, 65))
        axes = (int(w * 0.60), int(h * rng.uniform(0.25, 0.35)))
        cv2.ellipse(img_np, (center_x, center_y), axes, rng.randint(-30, 30), 0, 360, clamp_color, -1)
        
    return Image.fromarray(img_np)


def apply_clutter(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate high-entropy textured environment (wood desk grain, fabric, metallic distractors) intersecting the jewellery."""
    img_np = np.array(pil_img).copy()
    h, w = img_np.shape[:2]
    
    clutter_bg = np.zeros((h, w, 3), dtype=np.uint8)
    wood_base = (rng.randint(110, 140), rng.randint(80, 105), rng.randint(55, 75))
    clutter_bg[:] = wood_base
    
    for y in range(0, h, rng.randint(4, 8)):
        stripe_color = (int(wood_base[0] + rng.randint(-25, 25)), int(wood_base[1] + rng.randint(-20, 20)), int(wood_base[2] + rng.randint(-15, 15)))
        cv2.line(clutter_bg, (0, y), (w, y), stripe_color, thickness=rng.randint(2, 4))
        
    coin_pos = (int(w * rng.uniform(0.30, 0.70)), int(h * rng.uniform(0.25, 0.40)))
    cv2.circle(clutter_bg, coin_pos, int(w * 0.16), (180, 150, 80), -1)
    
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    is_bg = (gray > 220) | (gray < 25)
    img_np[is_bg] = clutter_bg[is_bg]
    return Image.fromarray(img_np)


def apply_motion_blur(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate severe handheld camera shake motion blur (kernel 35-53px)."""
    img_np = np.array(pil_img)
    kernel_size = rng.choice([35, 41, 47, 53])
    angle = rng.uniform(0, 180)
    
    kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
    radian = math.radians(angle)
    cx, cy = kernel_size // 2, kernel_size // 2
    for i in range(kernel_size):
        offset = i - cx
        x = int(round(cx + offset * math.cos(radian)))
        y = int(round(cy + offset * math.sin(radian)))
        if 0 <= x < kernel_size and 0 <= y < kernel_size:
            kernel[y, x] = 1.0
            
    kernel /= max(kernel.sum(), 1.0)
    blurred = cv2.filter2D(img_np, -1, kernel)
    return Image.fromarray(blurred)


def apply_reflection(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate display case glass reflection: mirrored double-ghosting plus specular streaks."""
    img_np = np.array(pil_img, dtype=np.float32)
    h, w = img_np.shape[:2]
    
    # Mirrored ghost
    flipped = cv2.flip(img_np, 1)
    shift_matrix = np.float32([[1, 0, rng.randint(30, 60)], [0, 1, rng.randint(20, 50)]])
    ghost = cv2.warpAffine(flipped, shift_matrix, (w, h), borderMode=cv2.BORDER_REFLECT)
    img_np = cv2.addWeighted(img_np, 0.55, ghost, 0.45, 0)
    
    # Bright specular reflections
    for _ in range(2):
        angle = rng.uniform(25, 45)
        rad = math.radians(angle)
        Y, X = np.ogrid[:h, :w]
        proj = X * math.cos(rad) + Y * math.sin(rad)
        band_center = (w * math.cos(rad) + h * math.sin(rad)) * rng.uniform(0.30, 0.70)
        band = np.exp(-((proj - band_center) ** 2) / (2 * (15.0 ** 2))) * rng.uniform(160.0, 220.0)
        for c in range(3):
            img_np[:, :, c] += band
            
    return Image.fromarray(np.uint8(np.clip(img_np, 0, 255)))


def apply_distance(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate severe distance capture: jewellery occupies only 18-28% of the frame."""
    scale = rng.uniform(0.18, 0.28)
    orig_w, orig_h = pil_img.size
    new_w = max(1, int(orig_w * scale))
    new_h = max(1, int(orig_h * scale))
    downscaled = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    canvas = np.zeros((orig_h, orig_w, 3), dtype=np.uint8)
    canvas[:] = (160, 150, 140)
    max_ox = orig_w - new_w
    max_oy = orig_h - new_h
    offset_x = rng.randint(int(max_ox * 0.2), int(max_ox * 0.8))
    offset_y = rng.randint(int(max_oy * 0.2), int(max_oy * 0.8))
    
    canvas_pil = Image.fromarray(canvas)
    canvas_pil.paste(downscaled, (offset_x, offset_y))
    return canvas_pil


def apply_noise(pil_img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate severe high-ISO sensor grain, dead pixels, and blocky low-bitrate JPEG artifacts."""
    img_np = np.array(pil_img, dtype=np.float32)
    sigma = rng.uniform(38.0, 55.0)
    noise = np.random.normal(0, sigma, img_np.shape)
    noisy_img = np.clip(img_np + noise, 0, 255).astype(np.uint8)
    
    sp_mask = np.random.rand(*noisy_img.shape[:2])
    noisy_img[sp_mask < 0.02] = 255
    noisy_img[sp_mask > 0.98] = 0
    
    h, w = noisy_img.shape[:2]
    small = cv2.resize(noisy_img, (w // 3, h // 3), interpolation=cv2.INTER_LINEAR)
    noisy_img = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    
    quality = rng.randint(8, 15)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    bgr = cv2.cvtColor(noisy_img, cv2.COLOR_RGB2BGR)
    _, encimg = cv2.imencode(".jpg", bgr, encode_param)
    decimg = cv2.imdecode(encimg, cv2.IMREAD_COLOR)
    return Image.fromarray(cv2.cvtColor(decimg, cv2.COLOR_BGR2RGB))


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
