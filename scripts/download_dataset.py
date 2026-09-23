"""
scripts/download_dataset.py
───────────────────────────
Phase 1 — Data Acquisition

Downloads a public jewellery catalogue from either:
  (A) HuggingFace Datasets  [default, no credentials needed]
  (B) Kaggle API            [requires ~/.kaggle/kaggle.json]

Outputs:
  data/raw_catalogue.csv   — raw manifest before cleaning
  data/catalogue/          — downloaded image files

Usage:
  python scripts/download_dataset.py
  python scripts/download_dataset.py --source huggingface
  python scripts/download_dataset.py --source kaggle
"""

import argparse
import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

# ── Load .env ────────────────────────────────────────────────────────────────
load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / os.getenv("CATALOGUE_IMG_DIR", "data/catalogue")
RAW_CSV = PROJECT_ROOT / os.getenv("RAW_CATALOGUE_CSV", "data/raw_catalogue.csv")

# Jewellery-related category keywords (HuggingFace source filtering)
JEWELLERY_KEYWORDS = {
    "jewellery", "jewelry", "jewel",
    "ring", "rings",
    "necklace", "necklaces",
    "earring", "earrings",
    "bracelet", "bracelets",
    "pendant", "pendants",
    "bangle", "bangles",
    "chain", "chains",
    "anklet", "anklets",
    "brooch", "brooches",
    "watches",           # often grouped with jewellery
}

CATEGORY_MAP = {
    "ring": "ring", "rings": "ring",
    "necklace": "necklace", "necklaces": "necklace",
    "earring": "earring", "earrings": "earring",
    "bracelet": "bracelet", "bracelets": "bracelet",
    "pendant": "pendant", "pendants": "pendant",
    "bangle": "bangle", "bangles": "bangle",
    "chain": "chain", "chains": "chain",
    "anklet": "anklet", "anklets": "anklet",
    "brooch": "brooch", "brooches": "brooch",
    "watches": "watch",
    "jewellery": "jewellery",
    "jewelry": "jewellery",
}


# ─────────────────────────────────────────────────────────────────────────────
# Source A — HuggingFace
# ─────────────────────────────────────────────────────────────────────────────

def download_huggingface(dataset_name: str, split: str = "train") -> list[dict]:
    """
    Stream the HuggingFace fashion-product dataset, filter to jewellery items,
    save images to DATA_DIR, and return a list of raw catalogue dicts.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        print("[ERROR] 'datasets' package not installed. Run: pip install datasets")
        sys.exit(1)

    print(f"\n[HF] Loading dataset '{dataset_name}' (split='{split}') …")
    ds = load_dataset(dataset_name, split=split)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    counter = 0

    print(f"[HF] Dataset has {len(ds)} total items. Filtering jewellery …")

    for row in tqdm(ds, desc="Filtering + saving", unit="item"):
        # ── Normalise category ────────────────────────────────────────────────
        raw_cat = str(row.get("productDisplayName", "") or "").lower()
        sub_cat = str(row.get("subCategory", "") or "").lower()
        master_cat = str(row.get("masterCategory", "") or "").lower()

        candidate_text = f"{raw_cat} {sub_cat} {master_cat}"

        matched_kw = next(
            (kw for kw in JEWELLERY_KEYWORDS if kw in candidate_text), None
        )
        if matched_kw is None:
            continue  # not a jewellery item

        category = CATEGORY_MAP.get(sub_cat.split()[0] if sub_cat else "", "jewellery")

        # ── Save image ────────────────────────────────────────────────────────
        counter += 1
        product_id = f"JW_{counter:06d}"
        img_filename = f"{product_id}.jpg"
        img_path = DATA_DIR / img_filename
        rel_img_path = f"data/catalogue/{img_filename}"

        try:
            img = row.get("image")  # PIL Image in this dataset
            if img is None:
                continue
            img = img.convert("RGB")
            img.save(img_path, format="JPEG", quality=95)
        except Exception as exc:
            print(f"  [WARN] Could not save image for row {counter}: {exc}")
            continue

        # ── Build record ──────────────────────────────────────────────────────
        source_id = row.get("id", "")
        records.append(
            {
                "product_id": product_id,
                "product_name": row.get("productDisplayName", ""),
                "category": category,
                "image_path": rel_img_path,
                "source_url": f"hf://{dataset_name}/{source_id}",
                "raw_sub_category": sub_cat,
            }
        )

    print(f"\n[HF] Collected {len(records)} jewellery items.")
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Source B — Kaggle
# ─────────────────────────────────────────────────────────────────────────────

def download_kaggle(dataset_slug: str) -> list[dict]:
    """
    Download a Kaggle dataset, move images to DATA_DIR, return raw records.
    Requires ~/.kaggle/kaggle.json (API credentials).
    """
    try:
        import kaggle  # noqa: F401 – triggers auth check
    except ImportError:
        print("[ERROR] 'kaggle' package not installed. Run: pip install kaggle")
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] Kaggle auth failed: {exc}")
        print("        Ensure ~/.kaggle/kaggle.json exists with your API key.")
        sys.exit(1)

    import shutil
    import zipfile

    tmp_dir = PROJECT_ROOT / ".kaggle_tmp"
    tmp_dir.mkdir(exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n[Kaggle] Downloading dataset '{dataset_slug}' …")
    os.system(
        f'kaggle datasets download -d "{dataset_slug}" -p "{tmp_dir}" --unzip'
    )

    # Find image files
    img_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    all_imgs = [
        p for p in tmp_dir.rglob("*") if p.suffix.lower() in img_extensions
    ]
    print(f"[Kaggle] Found {len(all_imgs)} image files.")

    records = []
    for idx, src_path in enumerate(tqdm(all_imgs, desc="Moving images", unit="img"), start=1):
        product_id = f"JW_{idx:06d}"
        img_filename = f"{product_id}.jpg"
        dest_path = DATA_DIR / img_filename

        try:
            from PIL import Image

            img = Image.open(src_path).convert("RGB")
            img.save(dest_path, format="JPEG", quality=95)
        except Exception as exc:
            print(f"  [WARN] Skip {src_path.name}: {exc}")
            continue

        records.append(
            {
                "product_id": product_id,
                "product_name": src_path.stem.replace("_", " ").title(),
                "category": "jewellery",
                "image_path": f"data/catalogue/{img_filename}",
                "source_url": f"kaggle://{dataset_slug}/{src_path.name}",
                "raw_sub_category": "",
            }
        )

    # Cleanup temp dir
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"\n[Kaggle] Collected {len(records)} items.")
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Write raw_catalogue.csv
# ─────────────────────────────────────────────────────────────────────────────

def write_raw_csv(records: list[dict]) -> None:
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "product_id",
        "product_name",
        "category",
        "image_path",
        "source_url",
        "raw_sub_category",
    ]
    with open(RAW_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"\n[OK] Raw catalogue written -> {RAW_CSV}  ({len(records)} rows)")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Phase 1 — Download jewellery catalogue")
    parser.add_argument(
        "--source",
        choices=["huggingface", "kaggle"],
        default=os.getenv("DATA_SOURCE", "huggingface"),
        help="Data source to use (default: huggingface)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  PS2 – Stump the Model  |  Phase 1: Data Acquisition")
    print("=" * 60)
    print(f"  Source      : {args.source}")
    print(f"  Images dir  : {DATA_DIR}")
    print(f"  Raw CSV     : {RAW_CSV}")
    print()

    if args.source == "huggingface":
        hf_dataset = os.getenv("HF_DATASET_NAME", "ashraq/fashion-product-images-small")
        hf_split = os.getenv("HF_SPLIT", "train")
        records = download_huggingface(hf_dataset, hf_split)
    else:
        kg_dataset = os.getenv("KAGGLE_DATASET", "PromptCloudHQ/all-products-from-katespadeny")
        records = download_kaggle(kg_dataset)

    if not records:
        print("[ERROR] No records collected. Check dataset name and credentials.")
        sys.exit(1)

    write_raw_csv(records)

    min_required = int(os.getenv("CATALOGUE_MIN_SIZE", "5000"))
    if len(records) < min_required:
        print(
            f"\n[WARN] Only {len(records)} items collected — "
            f"need at least {min_required}. "
            "Consider trying a different dataset or source."
        )
    else:
        print(
            f"\n[OK] {len(records)} items collected — "
            f"meets the {min_required}+ requirement. ✓"
        )

    print("\nNext step: python scripts/clean_catalogue.py")


if __name__ == "__main__":
    main()
