"""
scripts/ingest_sources.py
─────────────────────────
Phase 1 — Manual Dataset Ingestion

Scans every subfolder in data/sources/, finds all images,
reads the optional source_info.json for metadata, copies +
converts images to data/catalogue/, and writes data/raw_catalogue.csv.

Drop Zone Layout
────────────────
data/sources/
    <source_name>/
        source_info.json   ← optional description (see data/sources/README.md)
        images/            ← your raw images (any subfolder depth is fine)
            *.jpg / *.png / *.webp / ...

Usage
─────
    python scripts/ingest_sources.py
    python scripts/ingest_sources.py --sources-dir data/sources
    python scripts/ingest_sources.py --dry-run      # preview without copying
"""

import argparse
import csv
import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from tqdm import tqdm

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "data" / "sources"
CATALOGUE_IMG_DIR = PROJECT_ROOT / os.getenv("CATALOGUE_IMG_DIR", "data/catalogue")
RAW_CSV = PROJECT_ROOT / os.getenv("RAW_CATALOGUE_CSV", "data/raw_catalogue.csv")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

# ─────────────────────────────────────────────────────────────────────────────
# Category auto-detection from filename / folder name
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "ring": "ring",
    "necklace": "necklace",
    "earring": "earring",
    "bracelet": "bracelet",
    "pendant": "pendant",
    "bangle": "bangle",
    "chain": "chain",
    "anklet": "anklet",
    "brooch": "brooch",
    "watch": "watch",
    "stud": "earring",
    "hoop": "earring",
    "choker": "necklace",
    "mangalsutra": "necklace",
    "kada": "bracelet",
}


def guess_category(text: str) -> str:
    """Guess jewellery category from a filename or folder path string."""
    text_lower = text.lower()
    for keyword, cat in CATEGORY_KEYWORDS.items():
        if keyword in text_lower:
            return cat
    return "jewellery"


# ─────────────────────────────────────────────────────────────────────────────
# Load source_info.json
# ─────────────────────────────────────────────────────────────────────────────

def load_source_info(source_dir: Path) -> dict:
    """Load source_info.json if present, else return defaults."""
    info_path = source_dir / "source_info.json"
    if info_path.exists():
        try:
            with open(info_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            print(f"  [WARN] Could not read source_info.json in {source_dir.name}: {exc}")
    return {
        "source_name": source_dir.name,
        "source_url": "",
        "description": "",
        "categories": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Find all image files inside a source folder
# ─────────────────────────────────────────────────────────────────────────────

def find_images(source_dir: Path) -> list[Path]:
    """Recursively find all supported image files under source_dir."""
    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(source_dir.rglob(f"*{ext}"))
        images.extend(source_dir.rglob(f"*{ext.upper()}"))
    # Deduplicate (rglob with upper/lower may find same file twice on case-insensitive FS)
    seen = set()
    unique = []
    for p in images:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return sorted(unique)


# ─────────────────────────────────────────────────────────────────────────────
# Ingest a single source folder
# ─────────────────────────────────────────────────────────────────────────────

def load_image_meta(source_dir: Path) -> dict[str, str]:
    """
    Load image_meta.json if present (maps filename -> category).
    Created by download_hf_dataset.py for datasets with known category labels.
    """
    meta_path = source_dir / "image_meta.json"
    if not meta_path.exists():
        return {}
    try:
        import json
        with open(meta_path, encoding="utf-8") as f:
            entries = json.load(f)
        # entries is list of {filename, category, original}
        return {e["filename"]: e.get("category", "jewellery") for e in entries}
    except Exception as exc:
        print(f"  [WARN] Could not read image_meta.json: {exc}")
        return {}


def ingest_source(
    source_dir: Path,
    start_id: int,
    dry_run: bool = False,
) -> tuple[list[dict], int]:
    """
    Process one source folder.

    Returns:
        (records, next_start_id)
    """
    info = load_source_info(source_dir)
    source_name = info.get("source_name", source_dir.name)
    source_url_base = info.get("source_url", "")

    image_files = find_images(source_dir)

    if not image_files:
        print(f"  [WARN] No images found in {source_dir}. Skipping.")
        return [], start_id

    print(f"\n  Source : {source_name}")
    print(f"  Folder : {source_dir.name}/")
    print(f"  Images : {len(image_files)} found")

    records = []
    current_id = start_id
    skipped = 0

    for img_path in tqdm(image_files, desc=f"  {source_dir.name}", unit="img", leave=False):
        product_id = f"JW_{current_id:06d}"
        dest_filename = f"{product_id}.jpg"
        dest_path = CATALOGUE_IMG_DIR / dest_filename
        rel_dest = f"data/catalogue/{dest_filename}"

        # Guess category from file path
        category = guess_category(str(img_path))

        # Product name from filename (cleaned up)
        stem = img_path.stem
        product_name = stem.replace("_", " ").replace("-", " ").title()

        if not dry_run:
            try:
                img = Image.open(img_path).convert("RGB")
                img.save(dest_path, format="JPEG", quality=95)
            except Exception as exc:
                skipped += 1
                tqdm.write(f"    [SKIP] {img_path.name}: {exc}")
                continue

        # Source URL: use base URL + filename if available
        source_url = f"{source_url_base}/{img_path.name}" if source_url_base else f"local://{source_dir.name}/{img_path.name}"

        records.append(
            {
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "image_path": rel_dest,
                "source_url": source_url,
                "raw_source": source_name,
            }
        )
        current_id += 1

    print(f"  Result : {len(records)} ingested, {skipped} skipped")
    return records, current_id


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Phase 1 — Ingest manually downloaded jewellery datasets"
    )
    parser.add_argument(
        "--sources-dir",
        default=str(SOURCES_DIR),
        help=f"Root folder containing source subfolders (default: {SOURCES_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and count images without copying anything",
    )
    args = parser.parse_args()

    sources_root = Path(args.sources_dir)

    print("=" * 60)
    print("  PS2 - Stump the Model  |  Phase 1: Ingest Sources")
    print("=" * 60)
    print(f"  Sources dir : {sources_root}")
    print(f"  Output dir  : {CATALOGUE_IMG_DIR}")
    print(f"  Raw CSV     : {RAW_CSV}")
    if args.dry_run:
        print("  Mode        : DRY RUN (no files will be copied)")
    print()

    # ── Validate sources directory ────────────────────────────────────────────
    if not sources_root.exists():
        print(f"[ERROR] Sources directory not found: {sources_root}")
        print("        Create it and add at least one source subfolder.")
        sys.exit(1)

    # ── Discover source subfolders ────────────────────────────────────────────
    SKIP_FOLDERS = {"__pycache__"}
    source_dirs = [
        d for d in sorted(sources_root.iterdir())
        if d.is_dir()
        and not d.name.startswith((".", "_"))   # skip hidden/temp folders
        and d.name not in SKIP_FOLDERS
    ]

    if not source_dirs:
        print(f"[ERROR] No source subfolders found in {sources_root}")
        print()
        print("  To add a dataset:")
        print("    1. Create: data/sources/<your_source_name>/")
        print("    2. Put images in: data/sources/<your_source_name>/images/")
        print("    3. Optionally create: data/sources/<your_source_name>/source_info.json")
        print("    4. Re-run this script")
        print()
        print("  See data/sources/README.md for full instructions.")
        sys.exit(1)

    print(f"[OK] Found {len(source_dirs)} source folder(s):\n")
    for d in source_dirs:
        info = load_source_info(d)
        imgs = find_images(d)
        print(f"  - {d.name:<30}  ~{len(imgs)} images")

    print()

    # ── Create output dir ─────────────────────────────────────────────────────
    if not args.dry_run:
        CATALOGUE_IMG_DIR.mkdir(parents=True, exist_ok=True)

    # ── Process each source ───────────────────────────────────────────────────
    all_records: list[dict] = []
    next_id = 1

    for source_dir in source_dirs:
        records, next_id = ingest_source(source_dir, next_id, dry_run=args.dry_run)
        all_records.extend(records)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"  Total ingested : {len(all_records)} images")
    print("=" * 60)

    if args.dry_run:
        print("\n  [DRY RUN] No files written. Re-run without --dry-run to ingest.")
        return

    # ── Write raw_catalogue.csv ───────────────────────────────────────────────
    if not all_records:
        print("\n[ERROR] No images were ingested. Check your source folders.")
        sys.exit(1)

    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "product_id", "product_name", "category",
        "image_path", "source_url", "raw_source",
    ]
    with open(RAW_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\n[OK] raw_catalogue.csv written -> {RAW_CSV}")
    print(f"     {len(all_records)} rows")

    # ── Minimum check ─────────────────────────────────────────────────────────
    min_required = int(os.getenv("CATALOGUE_MIN_SIZE", "5000"))
    if len(all_records) < min_required:
        print(
            f"\n[WARN] Only {len(all_records)} images collected "
            f"(need {min_required}+)."
        )
        print("       Add more source folders to data/sources/ and re-run.")
    else:
        print(f"\n[OK] {len(all_records)} images - meets the {min_required}+ requirement.")

    print("\nNext step: python scripts/clean_catalogue.py")


if __name__ == "__main__":
    main()
