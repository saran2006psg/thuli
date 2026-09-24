"""
scripts/validate_stumper_dataset.py
───────────────────────────────────
Validates the integrity of the Stumper evaluation dataset:
  - Verifies evaluation/stumper.csv schema and required columns
  - Checks for duplicate image_id entries
  - Verifies that every image file exists on disk and is readable with PIL
  - Verifies that every ground-truth product_id exists in data/catalogue.csv
  - Validates that failure_condition belongs to the standard taxonomy
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import CATALOGUE_CSV

STUMPER_CSV = PROJECT_ROOT / "evaluation" / "stumper.csv"
STUMPER_IMG_DIR = PROJECT_ROOT / "evaluation" / "images"

ALLOWED_CONDITIONS: Set[str] = {
    "bad_lighting",
    "unusual_angle",
    "occlusion",
    "cluttered_background",
    "motion_blur",
    "reflection",
    "hand_wrist_visible",
    "distance_scale",
    "multiple_items",
    "clean_control",
}

REQUIRED_COLUMNS: Set[str] = {
    "image_id",
    "product_id",
    "failure_condition",
    "image_path",
}


def validate_stumper_dataset(
    stumper_csv_path: Path = STUMPER_CSV,
    catalogue_csv_path: Path = CATALOGUE_CSV,
    allow_empty: bool = False,
) -> bool:
    print("\n" + "=" * 65)
    print("  Stumper Dataset Integrity Validation (Phase 6)")
    print("=" * 65)

    if not catalogue_csv_path.exists():
        print(f"[ERROR] Catalogue CSV not found: {catalogue_csv_path}")
        return False

    cat_df = pd.read_csv(catalogue_csv_path)
    valid_product_ids = set(cat_df["product_id"].astype(str))
    print(f"  Loaded catalogue     : {len(valid_product_ids):,} valid product IDs")

    if not stumper_csv_path.exists():
        print(f"[ERROR] Stumper CSV not found: {stumper_csv_path}")
        return False

    with open(stumper_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = set(reader.fieldnames or [])
        rows = list(reader)

    missing_cols = REQUIRED_COLUMNS - fieldnames
    if missing_cols:
        print(f"[ERROR] Stumper CSV is missing required columns: {missing_cols}")
        return False

    total_entries = len(rows)
    print(f"  Stumper entries      : {total_entries}")

    if total_entries == 0:
        if allow_empty:
            print("[INFO] Stumper CSV is currently empty template. Ready for photos.")
            print("=" * 65 + "\n")
            return True
        else:
            print("[WARN] Stumper CSV is currently empty. Add your captured photos to evaluate.")
            print("=" * 65 + "\n")
            return False

    errors: List[str] = []
    seen_image_ids: Set[str] = set()
    condition_counts: Dict[str, int] = {}

    for i, row in enumerate(rows, start=1):
        img_id = row.get("image_id", "").strip()
        prod_id = row.get("product_id", "").strip()
        condition = row.get("failure_condition", "").strip()
        raw_path = row.get("image_path", "").strip()

        # 1. Check image_id
        if not img_id:
            errors.append(f"Row {i}: Missing image_id")
        elif img_id in seen_image_ids:
            errors.append(f"Row {i}: Duplicate image_id '{img_id}'")
        seen_image_ids.add(img_id)

        # 2. Check product_id exists in catalogue
        if not prod_id:
            errors.append(f"Row {i} ({img_id}): Missing product_id")
        elif prod_id not in valid_product_ids:
            errors.append(f"Row {i} ({img_id}): product_id '{prod_id}' not found in catalogue.csv")

        # 3. Check failure_condition
        if not condition:
            errors.append(f"Row {i} ({img_id}): Missing failure_condition")
        elif condition not in ALLOWED_CONDITIONS:
            errors.append(
                f"Row {i} ({img_id}): Invalid failure_condition '{condition}'. Allowed: {sorted(ALLOWED_CONDITIONS)}"
            )
        else:
            condition_counts[condition] = condition_counts.get(condition, 0) + 1

        # 4. Check image file existence and PIL readability
        if not raw_path:
            errors.append(f"Row {i} ({img_id}): Missing image_path")
        else:
            p = Path(raw_path)
            if not p.is_absolute():
                p = PROJECT_ROOT / p

            if not p.exists():
                errors.append(f"Row {i} ({img_id}): Image file does not exist at '{p}'")
            else:
                try:
                    with Image.open(p) as img:
                        img.verify()
                except Exception as e:
                    errors.append(f"Row {i} ({img_id}): Corrupt image file '{p}': {e}")

    # Summary report
    print("\n  Condition Breakdown:")
    for cond, count in sorted(condition_counts.items()):
        print(f"    - {cond:<22}: {count:>4} images")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} validation error(s):")
        for err in errors[:15]:
            print(f"  [!] {err}")
        if len(errors) > 15:
            print(f"  ... and {len(errors) - 15} more errors.")
        print("=" * 65 + "\n")
        return False
    else:
        print(f"\n[OK] Stumper dataset is 100% valid ({total_entries} photos ready for evaluation).")
        print("=" * 65 + "\n")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Stumper evaluation dataset.")
    parser.add_argument("--stumper-csv", type=Path, default=STUMPER_CSV)
    parser.add_argument("--catalogue-csv", type=Path, default=CATALOGUE_CSV)
    parser.add_argument("--allow-empty", action="store_true", help="Allow empty template without failing")
    args = parser.parse_args()

    is_valid = validate_stumper_dataset(
        stumper_csv_path=args.stumper_csv,
        catalogue_csv_path=args.catalogue_csv,
        allow_empty=args.allow_empty,
    )
    sys.exit(0 if is_valid else 1)
