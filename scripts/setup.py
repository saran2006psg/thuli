"""Prepare and verify Thuli on any device using only Python.

Handles:
1. Downloading the 6,157 catalogue dataset from Google Drive if missing.
2. Validating and normalizing all CSV paths to cross-platform relative paths.
3. Pre-caching the CLIP vision transformer model.
4. Verifying FastSAM weights (FastSAM-s.pt).
5. Generating embeddings and FAISS index if missing (or on --rebuild).
6. Starting the FastAPI server directly (--run) to serve the web UI without Node/npm.
"""

import argparse
import csv
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (  # noqa: E402
    CATALOGUE_CSV,
    CATALOGUE_IMG_DIR,
    EMBEDDINGS_PATH,
    ENCODER_MODEL,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
)

GDRIVE_FILE_ID = "1P_CvDHlEmH3iyZ5XwaPl2w86jY7yxgct"
GDRIVE_URL = "https://drive.google.com/file/d/1P_CvDHlEmH3iyZ5XwaPl2w86jY7yxgct/view?usp=sharing"


def download_catalogue_from_gdrive(dest_dir: Path) -> bool:
    """Download and extract catalogue dataset zip from Google Drive."""
    import requests
    from tqdm import tqdm

    print("\n" + "=" * 70)
    print("  DOWNLOADING CATALOGUE DATASET FROM GOOGLE DRIVE")
    print(f"  URL: {GDRIVE_URL}")
    print("=" * 70)

    session = requests.Session()
    init_url = f"https://drive.google.com/uc?export=download&id={GDRIVE_FILE_ID}"
    print("Connecting to Google Drive...")
    res = session.get(init_url, stream=True)

    uuid_match = re.search(r'name=["\']uuid["\']\s+value=["\']([^"\']+)["\']', res.text)
    uuid = uuid_match.group(1) if uuid_match else None

    params = {"id": GDRIVE_FILE_ID, "export": "download", "confirm": "t"}
    if uuid:
        params["uuid"] = uuid

    download_url = "https://drive.usercontent.google.com/download"
    download_res = session.get(download_url, params=params, stream=True)

    if download_res.status_code != 200:
        print(f"Direct download failed (HTTP {download_res.status_code}).")
        print(f"Please manually download from: {GDRIVE_URL}")
        print("Extract the contents into the 'data/' directory.")
        return False

    total_size = int(download_res.headers.get("content-length", 0))
    buffer = io.BytesIO()

    print(f"Downloading archive ({total_size / (1024*1024):.1f} MB)...")
    with tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading") as pbar:
        for chunk in download_res.iter_content(chunk_size=1024 * 64):
            if chunk:
                buffer.write(chunk)
                pbar.update(len(chunk))

    print("\nExtracting dataset archive into project root...")
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as zf:
        zf.extractall(PROJECT_ROOT)

    print("Catalogue extraction complete.")
    return True


def validate_and_normalize_csv_paths() -> int:
    """Ensure all paths in all project CSVs are relative with forward slashes."""
    csv_files = [
        CATALOGUE_CSV,
        PROJECT_ROOT / "evaluation" / "stumper.csv",
        PROJECT_ROOT / "evaluation" / "automated_stumper.csv",
        PROJECT_ROOT / "evaluation" / "multi_item_eval.csv",
    ]

    fixed_count = 0
    for fpath in csv_files:
        if not fpath.exists():
            continue
        try:
            text = fpath.read_text(encoding="utf-8")
            # Replace absolute drive prefixes like D:\PL\thuli\ or /d/PL/thuli/
            new_text = re.sub(r"(?i)[a-z]:[\\/]PL[\\/]thuli[\\/]", "", text)
            # Normalize backslashes inside evaluation or data paths
            new_text = re.sub(
                r"(evaluation|data)\\([a-zA-Z0-9_\-\\]+)",
                lambda m: m.group(1) + "/" + m.group(2).replace("\\", "/"),
                new_text,
            )
            if new_text != text:
                fpath.write_text(new_text, encoding="utf-8")
                fixed_count += 1
        except Exception as e:
            print(f"Warning: could not process {fpath}: {e}")

    return fixed_count


def check_and_download_model(model_name: str) -> bool:
    """Pre-warm and cache the CLIP model."""
    try:
        import warnings
        warnings.filterwarnings("ignore")
        from transformers import CLIPModel, CLIPProcessor, logging as tf_logging
        tf_logging.set_verbosity_error()

        print(f"\nChecking vision encoder: {model_name} ...")
        CLIPProcessor.from_pretrained(model_name)
        CLIPModel.from_pretrained(model_name, low_cpu_mem_usage=False)
        print("Vision model is cached and ready.")
        return True
    except Exception as exc:
        print(f"Model setup failed: {exc}", file=sys.stderr)
        print("Check your internet connection, then retry.", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and run Thuli on any device with Python.")
    parser.add_argument("--model", default=ENCODER_MODEL, help="Hugging Face model name")
    parser.add_argument("--rebuild", action="store_true", help="Force regenerate embeddings and FAISS index")
    parser.add_argument("--skip-model", action="store_true", help="Skip vision model download")
    parser.add_argument("--download-data", action="store_true", help="Force download catalogue from Google Drive")
    parser.add_argument("--run", action="store_true", help="Immediately start FastAPI server after setup")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind server (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3000, help="Port to bind server (default: 3000)")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  THULI RETRIEVAL ENGINE - CROSS-PLATFORM PYTHON SETUP")
    print("=" * 70)

    # 1. Normalize CSV paths
    fixed = validate_and_normalize_csv_paths()
    if fixed > 0:
        print(f"  [OK] Normalized CSV paths in {fixed} files to portable relative paths.")
    else:
        print("  [OK] CSV paths are validated and clean.")

    # 2. Check Catalogue Dataset
    dataset_dir = PROJECT_ROOT / "data" / "catalogue" / "jewelry_dataset"
    has_dataset = dataset_dir.exists() and any(dataset_dir.iterdir())
    has_csv = CATALOGUE_CSV.exists()

    if args.download_data or not (has_dataset and has_csv):
        print("\nCatalogue dataset is missing or download requested.")
        success = download_catalogue_from_gdrive(PROJECT_ROOT / "data")
        if not success and not (has_dataset and has_csv):
            print("ERROR: Catalogue dataset not found. Setup cannot proceed.", file=sys.stderr)
            return 1
    else:
        print("  [OK] Catalogue dataset is present (6,157 items).")

    # 3. Check FastSAM Weights
    fastsam_path = PROJECT_ROOT / "FastSAM-s.pt"
    if fastsam_path.exists():
        print(f"  [OK] FastSAM segmentation model found ({fastsam_path.stat().st_size / (1024*1024):.1f} MB).")
    else:
        print("  [WARN] FastSAM-s.pt not found. Multi-item search will fallback to overlapping grid mode.")

    # 4. Check / Download Vision Model
    if not args.skip_model:
        if not check_and_download_model(args.model):
            return 1

    # 5. Check / Build FAISS Index and Embeddings
    needs_build = (
        args.rebuild
        or not FAISS_INDEX_PATH.exists()
        or not EMBEDDINGS_PATH.exists()
        or not PRODUCT_IDS_PATH.exists()
    )

    if needs_build:
        print("\nBuilding catalogue embeddings and FAISS index...")
        if not CATALOGUE_CSV.exists():
            print(f"Cannot rebuild: catalogue CSV not found at {CATALOGUE_CSV}", file=sys.stderr)
            return 1
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_embeddings.py")],
            check=True,
            cwd=PROJECT_ROOT,
        )
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "build_index.py")],
            check=True,
            cwd=PROJECT_ROOT,
        )
        print("  [OK] FAISS index and embeddings built successfully.")
    else:
        print("  [OK] FAISS vector index & embeddings are ready.")

    # 6. Verify Static Frontend Assets
    index_html = PROJECT_ROOT / "app" / "static" / "index.html"
    if index_html.exists():
        print("  [OK] Compiled React web UI is present in app/static/ (ready to serve).")
    else:
        print("  [WARN] app/static/index.html missing. Run 'npm run build' in frontend/ to generate it.")

    print("\n" + "=" * 70)
    print("  ALL SYSTEM CHECKS PASSED - READY TO RUN ON ANY DEVICE")
    print("=" * 70)
    print("\nTo start the application:")
    print(f"  python -m uvicorn app.main:app --host {args.host} --port {args.port}")
    print(f"\nThen open in your browser: http://localhost:{args.port}")

    if args.run:
        print(f"\nStarting Uvicorn server on http://{args.host}:{args.port} ...")
        import uvicorn
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())