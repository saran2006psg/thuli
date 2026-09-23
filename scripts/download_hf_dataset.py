"""
scripts/download_hf_dataset.py
──────────────────────────────
Downloads a HuggingFace dataset and saves images into data/sources/<folder>/images/
Handles two repo formats:
  (A) Standard datasets (image column) — uses load_dataset()
  (B) Zip-based repos (single dataset.zip file) — downloads + extracts directly

Usage:
    python scripts/download_hf_dataset.py
    python scripts/download_hf_dataset.py --dataset sidd707/jewelry-design-dataset --folder jewelry_hf
    python scripts/download_hf_dataset.py --dataset <other/dataset> --split train
"""

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from tqdm import tqdm

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = PROJECT_ROOT / "data" / "sources"
SUPPORTED_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


# ─────────────────────────────────────────────────────────────────────────────
# Field auto-detection helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_image_field(sample: dict) -> str | None:
    for key, val in sample.items():
        if isinstance(val, Image.Image):
            return key
    for key in ("image", "img", "photo", "picture", "thumbnail"):
        if key in sample:
            return key
    return None


def get_name_field(sample: dict) -> str | None:
    for key in ("title", "name", "product_name", "label", "caption", "description", "text"):
        if key in sample and sample[key]:
            return key
    return None


def get_category_field(sample: dict) -> str | None:
    for key in ("category", "label", "class", "type", "style", "subCategory", "sub_category"):
        if key in sample:
            return key
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Method A — Standard HuggingFace datasets (load_dataset)
# ─────────────────────────────────────────────────────────────────────────────

def download_via_load_dataset(dataset_name: str, split: str, dest_dir: Path, info_path: Path) -> int:
    from datasets import load_dataset

    print("[1/4] Loading dataset info (streaming)...")
    ds_stream = load_dataset(dataset_name, split=split, streaming=True)
    first = next(iter(ds_stream))
    print(f"       Fields : {list(first.keys())}")

    img_field = get_image_field(first)
    name_field = get_name_field(first)
    cat_field = get_category_field(first)
    print(f"       Image  : {img_field} | Name: {name_field} | Category: {cat_field}")

    if img_field is None:
        raise ValueError(f"No image field found. Fields: {list(first.keys())}")

    print("\n[2/4] Loading full dataset...")
    ds = load_dataset(dataset_name, split=split)
    total = len(ds)
    print(f"       {total} items found.")

    print(f"\n[3/4] Saving images to {dest_dir} ...")
    saved = 0
    skipped = 0
    for idx, row in enumerate(tqdm(ds, desc="Saving", unit="img")):
        img_val = row.get(img_field)
        if not isinstance(img_val, Image.Image):
            skipped += 1
            continue
        out_path = dest_dir / f"img_{idx:06d}.jpg"
        try:
            img_val.convert("RGB").save(out_path, format="JPEG", quality=95)
            saved += 1
        except Exception as exc:
            tqdm.write(f"  [SKIP] row {idx}: {exc}")
            skipped += 1

    # Write source_info
    info = {
        "source_name": dataset_name.replace("/", "_"),
        "source_url": f"https://huggingface.co/datasets/{dataset_name}",
        "description": f"Downloaded via load_dataset: {dataset_name} (split={split})",
        "original_fields": list(first.keys()),
        "image_field_used": img_field,
        "saved_images": saved,
        "skipped": skipped,
    }
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    return saved


# ─────────────────────────────────────────────────────────────────────────────
# Method B — Zip-based repos (direct file download)
# ─────────────────────────────────────────────────────────────────────────────

def download_via_zip(dataset_name: str, dest_dir: Path, info_path: Path) -> int:
    from huggingface_hub import hf_hub_download, list_repo_files

    print("[1/4] Listing repo files...")
    all_files = list(list_repo_files(dataset_name, repo_type="dataset"))
    print(f"       Repo files: {all_files}")

    # Find zip files or direct image files
    zip_files = [f for f in all_files if f.endswith(".zip")]
    img_files = [f for f in all_files if Path(f).suffix.lower() in SUPPORTED_IMG_EXTS]

    if not zip_files and not img_files:
        raise ValueError(
            f"No zip or image files found in repo '{dataset_name}'.\n"
            f"Files: {all_files}"
        )

    tmp_dir = PROJECT_ROOT / ".hf_download_tmp"
    tmp_dir.mkdir(exist_ok=True)
    saved = 0

    if zip_files:
        for zip_name in zip_files:
            print(f"\n[2/4] Downloading {zip_name} ...")
            local_zip = hf_hub_download(
                repo_id=dataset_name,
                filename=zip_name,
                repo_type="dataset",
                local_dir=str(tmp_dir),
            )
            print(f"[3/4] Extracting {zip_name} ...")
            extract_dir = tmp_dir / Path(zip_name).stem
            with zipfile.ZipFile(local_zip, "r") as zf:
                zf.extractall(extract_dir)

            # Find all images inside extracted folder
            all_imgs = [
                p for p in extract_dir.rglob("*")
                if p.suffix.lower() in SUPPORTED_IMG_EXTS and p.is_file()
            ]
            print(f"       Found {len(all_imgs)} images inside zip.")

            print(f"[4/4] Copying to {dest_dir} ...")
            for img_path in tqdm(all_imgs, desc="Converting", unit="img"):
                out_path = dest_dir / f"img_{saved:06d}.jpg"
                try:
                    Image.open(img_path).convert("RGB").save(out_path, format="JPEG", quality=95)
                    saved += 1
                except Exception as exc:
                    tqdm.write(f"  [SKIP] {img_path.name}: {exc}")

    elif img_files:
        print(f"\n[2/4] Downloading {len(img_files)} image files directly ...")
        for img_name in tqdm(img_files, desc="Downloading", unit="img"):
            try:
                local_path = hf_hub_download(
                    repo_id=dataset_name,
                    filename=img_name,
                    repo_type="dataset",
                    local_dir=str(tmp_dir),
                )
                out_path = dest_dir / f"img_{saved:06d}.jpg"
                Image.open(local_path).convert("RGB").save(out_path, format="JPEG", quality=95)
                saved += 1
            except Exception as exc:
                tqdm.write(f"  [SKIP] {img_name}: {exc}")

    # Cleanup tmp
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Write source_info
    info = {
        "source_name": dataset_name.replace("/", "_"),
        "source_url": f"https://huggingface.co/datasets/{dataset_name}",
        "description": f"Downloaded via direct zip extraction: {dataset_name}",
        "repo_files": all_files,
        "saved_images": saved,
        "notes": "Used hf_hub_download (bypassed load_dataset due to custom script)",
    }
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)

    return saved


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def download_dataset(dataset_name: str, split: str, output_folder: str) -> None:
    dest_dir = SOURCES_DIR / output_folder / "images"
    dest_dir.mkdir(parents=True, exist_ok=True)
    info_path = SOURCES_DIR / output_folder / "source_info.json"

    print("=" * 60)
    print("  PS2 - Stump the Model  |  HF Dataset Downloader")
    print("=" * 60)
    print(f"  Dataset : {dataset_name}")
    print(f"  Output  : {dest_dir}")
    print()

    saved = 0
    method_used = "unknown"

    # Try Method A (standard datasets) first
    try:
        from datasets import load_dataset
        print("[INFO] Trying Method A: load_dataset() ...")
        saved = download_via_load_dataset(dataset_name, split, dest_dir, info_path)
        method_used = "load_dataset"
    except Exception as exc_a:
        print(f"[INFO] Method A failed: {exc_a}")
        print("[INFO] Trying Method B: direct zip download from Hub ...")
        try:
            saved = download_via_zip(dataset_name, dest_dir, info_path)
            method_used = "direct_zip"
        except Exception as exc_b:
            print(f"[ERROR] Method B also failed: {exc_b}")
            print()
            print("Manual fallback:")
            print(f"  1. Download the dataset manually from:")
            print(f"     https://huggingface.co/datasets/{dataset_name}")
            print(f"  2. Extract images to: data/sources/{output_folder}/images/")
            print(f"  3. Run: python scripts/ingest_sources.py")
            sys.exit(1)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"  Done!  (method: {method_used})")
    print(f"  Saved  : {saved} images")
    print(f"  Folder : data/sources/{output_folder}/")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  python scripts/ingest_sources.py     # build raw_catalogue.csv")
    print("  python scripts/clean_catalogue.py    # clean -> catalogue.csv")


def main():
    parser = argparse.ArgumentParser(description="Download a HuggingFace dataset into data/sources/")
    parser.add_argument("--dataset", default="sidd707/jewelry-design-dataset")
    parser.add_argument("--split", default="train")
    parser.add_argument("--folder", default=None)
    args = parser.parse_args()

    folder = args.folder or args.dataset.replace("/", "_").replace("-", "_")
    download_dataset(args.dataset, args.split, folder)


if __name__ == "__main__":
    main()
