"""Prepare a fresh checkout for local use.

This downloads the vision model once and verifies the prebuilt catalogue
artifacts. It does not rebuild embeddings or indexes unless requested.
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (  # noqa: E402
    CATALOGUE_CSV,
    ENCODER_MODEL,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
)


def download_model(model_name: str) -> None:
    from transformers import CLIPModel, CLIPProcessor

    print(f"Downloading/checking model: {model_name}")
    CLIPProcessor.from_pretrained(model_name, use_fast=True)
    CLIPModel.from_pretrained(model_name, low_cpu_mem_usage=False)
    print("Model is ready.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Thuli on a new machine.")
    parser.add_argument("--model", default=ENCODER_MODEL, help="Hugging Face model name")
    parser.add_argument("--rebuild", action="store_true", help="Regenerate embeddings and rebuild the FAISS index")
    parser.add_argument("--skip-model", action="store_true", help="Skip the model download")
    args = parser.parse_args()

    required = {
        "catalogue CSV": CATALOGUE_CSV,
        "FAISS index": FAISS_INDEX_PATH,
        "product ID mapping": PRODUCT_IDS_PATH,
    }
    missing = [(name, path) for name, path in required.items() if not path.exists()]
    if missing and not args.rebuild:
        print("Missing runtime artifacts:")
        for name, path in missing:
            print(f"  - {name}: {path}")
        print("Copy the prepared artifacts into this checkout, or run with --rebuild.")
        return 1

    if not args.skip_model:
        try:
            download_model(args.model)
        except Exception as exc:
            print(f"Model setup failed: {exc}", file=sys.stderr)
            print("Check internet access, then rerun. The model is cached after a successful download.", file=sys.stderr)
            return 1

    if args.rebuild:
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

    print("\nSetup complete. Start the API with:")
    print("  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("Open http://localhost:8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())