"""
scripts/clean_catalogue.py
──────────────────────────
Phase 1 — Catalogue Cleaning

Reads data/raw_catalogue.csv, validates every image, removes broken /
duplicate / too-small entries, assigns stable product IDs, and writes
the clean data/catalogue.csv manifest.

Cleaning pipeline:
  1. Validate image file exists
  2. Open image with PIL (catches corrupt/truncated files)
  3. Reject images smaller than IMAGE_MIN_DIMENSION in any axis
  4. Reject near-blank images (all-white / all-black by mean pixel value)
  5. Perceptual-hash deduplication (imagehash) — keep first occurrence
  6. Reassign stable sequential IDs (JW_000001 …)
  7. Write clean catalogue.csv
  8. Write rejected.csv with reasons

Outputs:
  data/catalogue.csv   — clean manifest (≥5,000 rows expected)
  data/rejected.csv    — removed entries with rejection reason

Usage:
  python scripts/clean_catalogue.py
"""

import csv
import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageStat
from tqdm import tqdm

# ── Load .env ────────────────────────────────────────────────────────────────
load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = PROJECT_ROOT / os.getenv("RAW_CATALOGUE_CSV", "data/raw_catalogue.csv")
CLEAN_CSV = PROJECT_ROOT / os.getenv("CATALOGUE_CSV", "data/catalogue.csv")
REJECTED_CSV = PROJECT_ROOT / os.getenv("REJECTED_CSV", "data/rejected.csv")

# ── Thresholds ─────────────────────────────────────────────────────────────────
IMAGE_MIN_DIM = int(os.getenv("IMAGE_MIN_DIMENSION", "64"))
CATALOGUE_MIN_SIZE = int(os.getenv("CATALOGUE_MIN_SIZE", "5000"))

# Blank image detection: mean pixel value (0–255) outside this range → reject
BLANK_MEAN_LOW = 5       # almost pure black
BLANK_MEAN_HIGH = 250    # almost pure white

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def file_md5(path: Path) -> str:
    """Compute MD5 hash of a file (for exact deduplication)."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def perceptual_hash(img: Image.Image) -> str:
    """
    Compute perceptual hash of a PIL image for near-duplicate detection.
    Falls back to a simple MD5 of resized bytes if imagehash is unavailable.
    """
    try:
        import imagehash

        return str(imagehash.phash(img))
    except ImportError:
        # Fallback: resize to 16×16 and hash raw bytes
        small = img.resize((16, 16)).convert("L")
        return hashlib.md5(small.tobytes()).hexdigest()


def is_blank(img: Image.Image) -> bool:
    """Return True if image appears nearly all-white or all-black."""
    stat = ImageStat.Stat(img.convert("L"))
    mean = stat.mean[0]
    return mean < BLANK_MEAN_LOW or mean > BLANK_MEAN_HIGH


def validate_image(rel_path: str) -> tuple[bool, str, int, int, Image.Image | None]:
    """
    Validate an image entry.

    Returns:
        (ok, reason, width, height, pil_image)
    """
    abs_path = PROJECT_ROOT / rel_path

    # 1. File exists
    if not abs_path.exists():
        return False, "file_not_found", 0, 0, None

    # 2. Can be opened
    try:
        img = Image.open(abs_path)
        img.verify()           # catches truncated/corrupt headers
        img = Image.open(abs_path)  # reopen after verify
        img = img.convert("RGB")
    except Exception as exc:
        return False, f"corrupt_image:{exc}", 0, 0, None

    w, h = img.size

    # 3. Minimum dimension
    if w < IMAGE_MIN_DIM or h < IMAGE_MIN_DIM:
        return False, f"too_small:{w}x{h}", w, h, None

    # 4. Near-blank
    if is_blank(img):
        return False, "blank_image", w, h, None

    return True, "", w, h, img


# ─────────────────────────────────────────────────────────────────────────────
# Main cleaning pipeline
# ─────────────────────────────────────────────────────────────────────────────

def clean_catalogue() -> None:
    # ── Load raw CSV ──────────────────────────────────────────────────────────
    if not RAW_CSV.exists():
        print(f"[ERROR] Raw catalogue not found: {RAW_CSV}")
        print("        Run: python scripts/download_dataset.py  first.")
        sys.exit(1)

    with open(RAW_CSV, newline="", encoding="utf-8") as f:
        raw_rows = list(csv.DictReader(f))

    total_raw = len(raw_rows)
    print(f"\n[Clean] Loaded {total_raw} raw entries from {RAW_CSV}")

    # ── Validation + deduplication pass ───────────────────────────────────────
    seen_hashes: set[str] = set()
    clean_records: list[dict] = []
    rejected_records: list[dict] = []

    stats = {
        "file_not_found": 0,
        "corrupt_image": 0,
        "too_small": 0,
        "blank_image": 0,
        "duplicate": 0,
        "accepted": 0,
    }

    for row in tqdm(raw_rows, desc="Validating images", unit="img"):
        rel_path = row.get("image_path", "")
        ok, reason, w, h = validate_image(rel_path)[:4]
        img_obj = validate_image(rel_path)[4]

        if not ok:
            # Determine stats bucket
            bucket = reason.split(":")[0]
            if bucket in stats:
                stats[bucket] += 1
            rejected_records.append(
                {
                    "product_id": row.get("product_id", ""),
                    "image_path": rel_path,
                    "reason": reason,
                }
            )
            continue

        # ── Perceptual deduplication ──────────────────────────────────────────
        phash = perceptual_hash(img_obj)
        if phash in seen_hashes:
            stats["duplicate"] += 1
            rejected_records.append(
                {
                    "product_id": row.get("product_id", ""),
                    "image_path": rel_path,
                    "reason": "duplicate_phash",
                }
            )
            continue

        seen_hashes.add(phash)
        stats["accepted"] += 1

        clean_records.append(
            {
                "product_id": row.get("product_id", ""),
                "product_name": row.get("product_name", ""),
                "category": row.get("category", "jewellery"),
                "image_path": rel_path,
                "source_url": row.get("source_url", ""),
                "width": w,
                "height": h,
            }
        )

    # ── Reassign stable sequential IDs ────────────────────────────────────────
    # Even if source IDs look stable, force a clean monotonic sequence.
    for new_idx, record in enumerate(clean_records, start=1):
        record["product_id"] = f"JW_{new_idx:06d}"

    # ── Write clean catalogue.csv ─────────────────────────────────────────────
    CLEAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    clean_fieldnames = [
        "product_id",
        "product_name",
        "category",
        "image_path",
        "source_url",
        "width",
        "height",
    ]
    with open(CLEAN_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=clean_fieldnames)
        writer.writeheader()
        writer.writerows(clean_records)

    # ── Write rejected.csv ────────────────────────────────────────────────────
    REJECTED_CSV.parent.mkdir(parents=True, exist_ok=True)
    rejected_fieldnames = ["product_id", "image_path", "reason"]
    with open(REJECTED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rejected_fieldnames)
        writer.writeheader()
        writer.writerows(rejected_records)

    # -- Summary ---------------------------------------------------------------
    print("\n" + "=" * 55)
    print("  Catalogue Cleaning Summary")
    print("=" * 55)
    print(f"  Raw entries          : {total_raw:>6}")
    print(f"  - File not found     : {stats['file_not_found']:>6}")
    print(f"  - Corrupt / unreadable: {stats['corrupt_image']:>5}")
    print(f"  - Too small (<{IMAGE_MIN_DIM}px)   : {stats['too_small']:>6}")
    print(f"  - Blank image        : {stats['blank_image']:>6}")
    print(f"  - Duplicate          : {stats['duplicate']:>6}")
    print(f"  ------------------------------")
    print(f"  Clean entries        : {stats['accepted']:>6}")
    print("=" * 55)
    print(f"\n  catalogue.csv  ->  {CLEAN_CSV}")
    print(f"  rejected.csv   ->  {REJECTED_CSV}")

    # -- Final check -----------------------------------------------------------
    if stats["accepted"] < CATALOGUE_MIN_SIZE:
        print(
            f"\n[WARN] Only {stats['accepted']} clean items -- "
            f"need {CATALOGUE_MIN_SIZE}+.\n"
            "       Consider:\n"
            "         1. Using a larger source dataset.\n"
            "         2. Lowering IMAGE_MIN_DIMENSION in .env.\n"
            "         3. Running download_dataset.py with a different --source."
        )
        sys.exit(2)   # non-zero exit so CI catches it
    else:
        print(
            f"\n[OK] {stats['accepted']} clean jewellery items ready.\n"
            "     Minimum requirement (5,000) met.\n"
            "\nNext step: python scripts/generate_embeddings.py  (Phase 2)"
        )


if __name__ == "__main__":
    clean_catalogue()
