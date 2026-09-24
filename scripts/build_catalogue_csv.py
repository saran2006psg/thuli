"""
scripts/build_catalogue_csv.py
──────────────────────────────
Builds clean data/catalogue.csv from data/catalogue/jewelry_dataset/
Validates each image, extracts dimensions, assigns unique JW_NNNNNN product IDs.
"""

import csv
import sys
from pathlib import Path
from PIL import Image
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import CATALOGUE_CSV

DATASET_DIR = PROJECT_ROOT / "data" / "catalogue" / "jewelry_dataset"
CATEGORIES = ["bracelet", "earring", "necklace", "ring"]

def build_catalogue():
    print("\n" + "=" * 60)
    print("  Building Catalogue CSV from jewelry_dataset")
    print("=" * 60)

    if not DATASET_DIR.exists():
        print(f"[ERROR] Dataset directory not found: {DATASET_DIR}")
        sys.exit(1)

    records = []
    product_idx = 1

    for category in CATEGORIES:
        cat_dir = DATASET_DIR / category
        if not cat_dir.exists():
            print(f"[WARN] Category folder not found: {cat_dir}")
            continue

        files = sorted(list(cat_dir.glob("*.jpg")) + list(cat_dir.glob("*.jpeg")) + list(cat_dir.glob("*.png")))
        print(f"  Found {len(files):>5} images in '{category}'")

        for fpath in tqdm(files, desc=f"  Processing {category:<10}"):
            try:
                with Image.open(fpath) as img:
                    width, height = img.size
                    img.verify()  # Check for corruption
            except Exception as e:
                print(f"  [SKIP] Corrupt image {fpath.name}: {e}")
                continue

            product_id = f"JW_{product_idx:06d}"
            # Relative path from project root
            rel_path = fpath.relative_to(PROJECT_ROOT).as_posix()
            
            name = fpath.stem.replace("_", " ").title()

            records.append({
                "product_id": product_id,
                "product_name": name,
                "category": category,
                "subcategory": category,
                "image_path": rel_path,
                "source_url": "https://huggingface.co/datasets/sidd707/jewelry-design-dataset",
                "width": width,
                "height": height,
            })
            product_idx += 1

    print(f"\n  Total valid images: {len(records):,}")

    CATALOGUE_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["product_id", "product_name", "category", "subcategory", "image_path", "source_url", "width", "height"]
    
    with open(CATALOGUE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"  Successfully wrote : {CATALOGUE_CSV}")
    print("=" * 60)

if __name__ == "__main__":
    build_catalogue()
