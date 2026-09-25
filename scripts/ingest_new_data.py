"""
ingest_new_data.py - Scans new_data/jewellery-dataset/processed/, copies images
to evaluation/images/ with sequential IDs, and appends entries to stumper.csv.
"""

import argparse, csv, os, re, shutil, sys
from pathlib import Path

PROJECT_ROOT = Path(r"d:\PL\thuli")
SOURCE_BASE  = PROJECT_ROOT / "new_data" / "jewellery-dataset" / "processed"
DATASET_CSV  = PROJECT_ROOT / "new_data" / "jewellery-dataset" / "dataset.csv"
EVAL_IMAGES  = PROJECT_ROOT / "evaluation" / "images"
STUMPER_CSV  = PROJECT_ROOT / "evaluation" / "stumper.csv"

def load_stumper_csv(path):
    rows, stems = [], set()
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
                if row.get("notes"):
                    stems.add(row["notes"].strip())
    return rows, stems

def next_id(existing_rows):
    max_id = 0
    for row in existing_rows:
        m = re.match(r"id(\d+)", row.get("image_id", ""))
        if m:
            max_id = max(max_id, int(m.group(1)))
    return max_id + 1

def main(dry_run=False):
    print(f"{'[DRY RUN] ' if dry_run else ''}Ingesting from: {SOURCE_BASE}\n")
    EVAL_IMAGES.mkdir(parents=True, exist_ok=True)

    existing_rows, already_ingested = load_stumper_csv(STUMPER_CSV)
    counter = next_id(existing_rows)
    new_rows, skipped, copied = [], 0, 0

    for product_dir in sorted(SOURCE_BASE.iterdir()):
        if not product_dir.is_dir():
            continue
        product_id = product_dir.name
        for scenario_dir in sorted(product_dir.iterdir()):
            if not scenario_dir.is_dir():
                continue
            failure_condition = scenario_dir.name
            for img_file in sorted(scenario_dir.iterdir()):
                if img_file.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                uuid_stem = img_file.stem
                if uuid_stem in already_ingested:
                    print(f"  SKIP: {img_file.name}")
                    skipped += 1
                    continue
                new_id   = f"id{counter:02d}"
                new_name = f"{new_id}.jpeg"
                dest     = EVAL_IMAGES / new_name
                print(f"  {'WOULD COPY' if dry_run else 'COPY'}: {img_file.name} -> {new_name}  [{product_id} | {failure_condition}]")
                if not dry_run:
                    shutil.copy2(img_file, dest)
                new_rows.append({"image_id": new_id, "product_id": product_id, "failure_condition": failure_condition, "notes": uuid_stem, "image_path": str(dest)})
                counter += 1
                copied += 1

    if not dry_run and new_rows:
        all_rows = existing_rows + new_rows
        fieldnames = ["image_id", "product_id", "failure_condition", "notes", "image_path"]
        with open(STUMPER_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\nUpdated stumper.csv ({len(all_rows)} total rows)")
    elif dry_run:
        print(f"\n[DRY RUN] Would write {len(existing_rows)+len(new_rows)} rows to stumper.csv")
    else:
        print("\nNo new images — stumper.csv unchanged.")
    print(f"\nSummary: {copied} copied, {skipped} skipped")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    main(dry_run=args.dry_run)
