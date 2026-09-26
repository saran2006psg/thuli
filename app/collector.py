"""
app/collector.py
────────────────
Data Collection & Stumper Management Module.

Handles:
  - Phone camera / device upload storage for 10 failure conditions
  - Metadata tracking in data/collected_stumpers.json & CSV
  - Automatic synchronization with evaluation/stumper.csv
  - Progress calculation per product (e.g. 7/10 conditions)
  - Dataset-wide statistics (by condition, by jewellery type)
"""

import csv
import json
import os
import re
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from app.config import PROJECT_ROOT

# Storage Directories & Files - Stumper images are stored directly in evaluation/images as idXX.jpeg
EVAL_IMAGES_DIR = PROJECT_ROOT / "evaluation" / "images"
COLLECTED_DIR = EVAL_IMAGES_DIR  # Kept for backward compatibility
COLLECTED_JSON = PROJECT_ROOT / "data" / "collected_stumpers.json"
COLLECTED_CSV = PROJECT_ROOT / "data" / "collected_stumpers.csv"
EVAL_STUMPER_CSV = PROJECT_ROOT / "evaluation" / "stumper.csv"
UNSEEN_STUMPER_CSV = PROJECT_ROOT / "evaluation" / "unseen_stumper.csv"

_collector_lock = threading.Lock()

# 10 Stumper Conditions with display metadata & guidelines
STUMPER_CONDITIONS = [
    {
        "id": "normal",
        "name": "Normal",
        "icon": "☀️",
        "description": "Clear reference photo under clean, balanced ambient lighting.",
    },
    {
        "id": "bad_lighting",
        "name": "Bad Lighting",
        "icon": "💡",
        "description": "Underexposed, dim room, harsh shadows, or uneven low light.",
    },
    {
        "id": "bright_lighting",
        "name": "Bright Lighting",
        "icon": "⚡",
        "description": "Overexposed, harsh direct sunlight or high-intensity phone flash glare.",
    },
    {
        "id": "odd_angle",
        "name": "Odd Angle",
        "icon": "📐",
        "description": "Extreme tilt, steep top-down, side-profile, or diagonal perspective.",
    },
    {
        "id": "occlusion",
        "name": "Occlusion",
        "icon": "🙈",
        "description": "Partially covered by fingers, jewellery tag, cloth, or case rim.",
    },
    {
        "id": "clutter",
        "name": "Clutter",
        "icon": "📦",
        "description": "Placed next to keys, coins, patterned textiles, or busy background.",
    },
    {
        "id": "motion_blur",
        "name": "Motion Blur",
        "icon": "💨",
        "description": "Intentional slight hand movement or camera shake while snapping.",
    },
    {
        "id": "reflection",
        "name": "Reflection",
        "icon": "✨",
        "description": "Glass showcase reflection, mirror backdrop, or shiny metallic specular flare.",
    },
    {
        "id": "hand_wrist",
        "name": "Hand/Wrist",
        "icon": "✋",
        "description": "Held in palm, worn on finger/wrist, or worn against skin.",
    },
    {
        "id": "distance",
        "name": "Distance",
        "icon": "📏",
        "description": "Shot from afar (item occupies < 15% of frame, un-cropped).",
    },
]

CONDITION_MAP = {c["id"]: c for c in STUMPER_CONDITIONS}

# Normalization for condition aliases
ALIAS_MAP = {
    "hand": "hand_wrist",
    "hand/wrist": "hand_wrist",
    "motionblur": "motion_blur",
    "motion_blur": "motion_blur",
    "badlighting": "bad_lighting",
    "bad_lighting": "bad_lighting",
    "brightlighting": "bright_lighting",
    "bright_lighting": "bright_lighting",
    "oddangle": "odd_angle",
    "odd_angle": "odd_angle",
}


def normalize_condition(cond: str) -> str:
    """Normalize input condition string to standard condition id."""
    raw = cond.strip().lower().replace(" ", "_").replace("-", "_")
    if raw in CONDITION_MAP:
        return raw
    if raw in ALIAS_MAP:
        return ALIAS_MAP[raw]
    # Check if name matches
    for cid, cinfo in CONDITION_MAP.items():
        if cinfo["name"].lower() == cond.strip().lower():
            return cid
    return raw


class StumperCollector:
    """Thread-safe manager for collected stumper photos & metadata."""

    def __init__(self):
        COLLECTED_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        """Create empty metadata storage if files do not exist."""
        if not COLLECTED_JSON.exists():
            with open(COLLECTED_JSON, "w", encoding="utf-8") as f:
                json.dump({"items": {}}, f, indent=2)

        if not COLLECTED_CSV.exists():
            with open(COLLECTED_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "image_id",
                    "product_id",
                    "jewellery_type",
                    "failure_condition",
                    "notes",
                    "image_path",
                    "created_at",
                ])

    def _load_json(self) -> Dict[str, Any]:
        """Load collected stumpers JSON dictionary."""
        try:
            with open(COLLECTED_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"items": {}}

    def _save_json(self, data: Dict[str, Any]):
        """Persist collected stumpers JSON dictionary."""
        with open(COLLECTED_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _sync_csv(self, items: Dict[str, Dict[str, Any]]):
        """Re-write collected_stumpers.csv to match items."""
        with open(COLLECTED_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "image_id",
                "product_id",
                "jewellery_type",
                "failure_condition",
                "notes",
                "image_path",
                "created_at",
            ])
            for item in items.values():
                writer.writerow([
                    item.get("image_id", ""),
                    item.get("product_id", ""),
                    item.get("jewellery_type", ""),
                    item.get("failure_condition", ""),
                    item.get("notes", ""),
                    item.get("image_path", ""),
                    item.get("created_at", ""),
                ])

    def _get_or_create_image_id(self, product_id: str, norm_cond: str) -> str:
        """
        Get existing image_id for this product and condition if available,
        otherwise find highest idXX and return next sequential idXX.
        """
        # 1. Check if already in collected items
        data = self._load_json()
        key = f"{product_id}::{norm_cond}"
        if key in data.get("items", {}) and data["items"][key].get("image_id"):
            return data["items"][key]["image_id"]

        # 2. Check if already in evaluation/stumper.csv
        if EVAL_STUMPER_CSV.exists():
            try:
                with open(EVAL_STUMPER_CSV, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if (row.get("notes") == product_id or row.get("product_id") == product_id) and row.get("failure_condition") == norm_cond:
                            if row.get("image_id"):
                                return row["image_id"]
            except Exception:
                pass

        # 3. Compute next sequential idXX
        max_num = 0
        pattern = re.compile(r"^id(\d+)", re.IGNORECASE)

        if EVAL_IMAGES_DIR.exists():
            for f in EVAL_IMAGES_DIR.iterdir():
                m = pattern.match(f.stem)
                if m:
                    try:
                        max_num = max(max_num, int(m.group(1)))
                    except ValueError:
                        pass

        if EVAL_STUMPER_CSV.exists():
            try:
                with open(EVAL_STUMPER_CSV, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        img_id = row.get("image_id", "")
                        m = pattern.match(img_id)
                        if m:
                            try:
                                max_num = max(max_num, int(m.group(1)))
                            except ValueError:
                                pass
            except Exception:
                pass

        for it in data.get("items", {}).values():
            img_id = it.get("image_id", "")
            m = pattern.match(img_id)
            if m:
                try:
                    max_num = max(max_num, int(m.group(1)))
                except ValueError:
                    pass

        next_num = max_num + 1
        return f"id{next_num:02d}"

    def _sync_to_eval_stumper_csv(self, item: Dict[str, Any]):
        """
        Synchronize collected photo with evaluation/stumper.csv so it becomes
        part of the evaluation arena test set.
        """
        if not EVAL_STUMPER_CSV.exists():
            return

        image_id = item["image_id"]
        product_id = item["product_id"]
        category = item.get("jewellery_type", "")
        condition = item["failure_condition"]
        notes = item.get("notes") or product_id
        abs_img_path = str(PROJECT_ROOT / item["image_path"])

        # Check existing rows to prevent duplicate image_ids
        existing_rows = []
        with open(EVAL_STUMPER_CSV, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or ["image_id", "product_id", "failure_condition", "notes", "image_path"]
            for r in reader:
                existing_rows.append(r)

        # Update if exists, else append
        updated = False
        for r in existing_rows:
            if r.get("image_id") == image_id:
                r["product_id"] = category or product_id
                r["failure_condition"] = condition
                r["notes"] = notes
                r["image_path"] = abs_img_path
                updated = True
                break

        if not updated:
            existing_rows.append({
                "image_id": image_id,
                "product_id": category or product_id,
                "failure_condition": condition,
                "notes": notes,
                "image_path": abs_img_path,
            })

        with open(EVAL_STUMPER_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)

    def _trigger_evaluation_update(self):
        """Re-run evaluation in background to update results.csv and metrics.json."""
        def _run():
            try:
                from app.api.routes import get_matcher
                from app.evaluation.runner import run_evaluation, write_results
                matcher = get_matcher()
                if matcher:
                    report = run_evaluation(matcher)
                    write_results(report["metrics"], report["rows"])
            except Exception as e:
                print(f"[WARN] Background evaluation update failed: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def save_stumper(
        self,
        product_id: str,
        failure_condition: str,
        image: Image.Image,
        jewellery_type: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save stumper image directly into evaluation/images/idXX.jpeg and record metadata.

        Args:
            product_id: Target catalogue product ID (e.g. JW_006158).
            failure_condition: One of the 10 failure conditions.
            image: PIL Image object.
            jewellery_type: Category (ring, necklace, etc.).
            notes: Optional user note.

        Returns:
            Dict of saved stumper record + updated product stats.
        """
        norm_cond = normalize_condition(failure_condition)
        if norm_cond not in CONDITION_MAP:
            valid_list = ", ".join(CONDITION_MAP.keys())
            raise ValueError(f"Invalid condition '{failure_condition}'. Must be one of: {valid_list}")

        clean_pid = product_id.strip()
        if not clean_pid:
            raise ValueError("Product ID cannot be empty.")

        with _collector_lock:
            EVAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

            # 1. Determine sequential image ID following evaluation scheme (e.g. id47)
            image_id = self._get_or_create_image_id(clean_pid, norm_cond)
            img_filename = f"{image_id}.jpeg"
            img_dest = EVAL_IMAGES_DIR / img_filename

            # Convert to RGB and save as high-quality JPEG
            rgb_img = image.convert("RGB")
            rgb_img.save(img_dest, format="JPEG", quality=92, optimize=True)

            rel_path = f"evaluation/images/{img_filename}".replace("\\", "/")
            web_url = f"/{rel_path}"
            created_at = datetime.now(timezone.utc).isoformat()

            record = {
                "image_id": image_id,
                "product_id": clean_pid,
                "jewellery_type": (jewellery_type or "").strip().lower(),
                "failure_condition": norm_cond,
                "condition_name": CONDITION_MAP[norm_cond]["name"],
                "notes": (notes or clean_pid).strip(),
                "image_path": rel_path,
                "image_url": web_url,
                "created_at": created_at,
                "width": rgb_img.width,
                "height": rgb_img.height,
            }

            # 2. Persist to JSON
            data = self._load_json()
            items = data.setdefault("items", {})
            key = f"{clean_pid}::{norm_cond}"
            items[key] = record
            self._save_json(data)

            # 3. Sync CSVs
            self._sync_csv(items)
            try:
                self._sync_to_eval_stumper_csv(record)
            except Exception as e:
                print(f"[WARN] Failed to sync to evaluation/stumper.csv: {e}")

            # 4. Update results.csv and metrics.json in background
            self._trigger_evaluation_update()

            # 5. Compute updated progress
            prod_stumpers = [it for it in items.values() if it["product_id"] == clean_pid]
            completed_conditions = [it["failure_condition"] for it in prod_stumpers]

            return {
                "status": "success",
                "item": record,
                "progress": {
                    "product_id": clean_pid,
                    "completed_count": len(completed_conditions),
                    "total_conditions": len(STUMPER_CONDITIONS),
                    "percent": round((len(completed_conditions) / len(STUMPER_CONDITIONS)) * 100),
                    "completed_conditions": completed_conditions,
                },
            }

    def get_product_stumpers(self, product_id: str) -> Dict[str, Any]:
        """
        Get all collected stumper photos and condition completion status for a product.
        """
        clean_pid = product_id.strip()
        data = self._load_json()
        items = data.get("items", {})

        stumpers_by_cond: Dict[str, Dict[str, Any]] = {}
        for it in items.values():
            if it.get("product_id") == clean_pid:
                cond = it.get("failure_condition")
                if cond:
                    stumpers_by_cond[cond] = it

        # Also merge any unseen stumper if available
        if UNSEEN_STUMPER_CSV.exists():
            try:
                with open(UNSEEN_STUMPER_CSV, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        target_pid = row.get("target_product_id", "").strip()
                        if target_pid == clean_pid:
                            cond = normalize_condition(row.get("failure_condition", ""))
                            if cond in CONDITION_MAP and cond not in stumpers_by_cond:
                                img_path = row.get("image_path", "").replace("\\", "/")
                                stumpers_by_cond[cond] = {
                                    "image_id": row.get("image_id", ""),
                                    "product_id": clean_pid,
                                    "failure_condition": cond,
                                    "condition_name": CONDITION_MAP[cond]["name"],
                                    "notes": row.get("notes", ""),
                                    "image_path": img_path,
                                    "image_url": "/" + img_path if not img_path.startswith("/") else img_path,
                                    "created_at": "pre-existing",
                                }
            except Exception:
                pass

        # Build list of 10 conditions with status
        condition_statuses = []
        for cond in STUMPER_CONDITIONS:
            cid = cond["id"]
            captured = cid in stumpers_by_cond
            record = stumpers_by_cond.get(cid)
            condition_statuses.append({
                **cond,
                "is_captured": captured,
                "record": record,
            })

        completed_count = len(stumpers_by_cond)
        total = len(STUMPER_CONDITIONS)

        return {
            "product_id": clean_pid,
            "completed_count": completed_count,
            "total_conditions": total,
            "percent": round((completed_count / total) * 100) if total else 0,
            "is_complete": completed_count >= total,
            "stumpers": stumpers_by_cond,
            "conditions": condition_statuses,
        }

    def delete_stumper(self, product_id: str, failure_condition: str) -> Dict[str, Any]:
        """Remove a stumper photo to allow retake."""
        clean_pid = product_id.strip()
        norm_cond = normalize_condition(failure_condition)
        key = f"{clean_pid}::{norm_cond}"

        with _collector_lock:
            data = self._load_json()
            items = data.get("items", {})
            if key in items:
                record = items.pop(key)
                self._save_json(data)
                self._sync_csv(items)

                # Delete physical file if present
                img_path = PROJECT_ROOT / record.get("image_path", "")
                if img_path.exists():
                    try:
                        img_path.unlink()
                    except Exception:
                        pass

                # Remove from evaluation/stumper.csv
                if EVAL_STUMPER_CSV.exists() and record.get("image_id"):
                    try:
                        rows = []
                        with open(EVAL_STUMPER_CSV, "r", newline="", encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            fieldnames = reader.fieldnames
                            for r in reader:
                                if r.get("image_id") != record.get("image_id"):
                                    rows.append(r)
                        with open(EVAL_STUMPER_CSV, "w", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            writer.writerows(rows)
                    except Exception as e:
                        print(f"[WARN] Failed to remove from stumper.csv: {e}")

                # Refresh evaluation results in background
                self._trigger_evaluation_update()

                return {"status": "deleted", "key": key}
            return {"status": "not_found", "key": key}

    def get_all_product_counts(self) -> Dict[str, Dict[str, Any]]:
        """
        Return mapping of product_id -> { count, conditions }
        for all products with at least 1 stumper photo.
        """
        data = self._load_json()
        counts: Dict[str, Dict[str, Any]] = {}
        for it in data.get("items", {}).values():
            pid = it.get("product_id")
            cond = it.get("failure_condition")
            if pid and cond:
                entry = counts.setdefault(pid, {"count": 0, "conditions": []})
                if cond not in entry["conditions"]:
                    entry["conditions"].append(cond)
                    entry["count"] += 1

        # Also merge unseen stumper
        if UNSEEN_STUMPER_CSV.exists():
            try:
                with open(UNSEEN_STUMPER_CSV, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        target_pid = row.get("target_product_id", "").strip()
                        cond = normalize_condition(row.get("failure_condition", ""))
                        if target_pid and cond in CONDITION_MAP:
                            entry = counts.setdefault(target_pid, {"count": 0, "conditions": []})
                            if cond not in entry["conditions"]:
                                entry["conditions"].append(cond)
                                entry["count"] += 1
            except Exception:
                pass

        return counts

    def get_dataset_stats(self, catalogue_lookup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return comprehensive dataset statistics:
          - Total products in catalogue
          - Total stumper photos collected
          - Counts per condition
          - Counts per jewellery type
          - Progress breakdown
          - Recent uploads
        """
        data = self._load_json()
        items = list(data.get("items", {}).values())

        # Merge unseen stumper rows
        if UNSEEN_STUMPER_CSV.exists():
            try:
                with open(UNSEEN_STUMPER_CSV, "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        target_pid = row.get("target_product_id", "").strip()
                        cond = normalize_condition(row.get("failure_condition", ""))
                        if target_pid and cond in CONDITION_MAP:
                            # check if not already in items
                            exists = any(it.get("product_id") == target_pid and it.get("failure_condition") == cond for it in items)
                            if not exists:
                                img_path = row.get("image_path", "").replace("\\", "/")
                                items.append({
                                    "image_id": row.get("image_id", ""),
                                    "product_id": target_pid,
                                    "jewellery_type": row.get("product_id", ""),
                                    "failure_condition": cond,
                                    "notes": row.get("notes", ""),
                                    "image_path": img_path,
                                    "image_url": "/" + img_path if not img_path.startswith("/") else img_path,
                                    "created_at": "pre-existing",
                                })
            except Exception:
                pass

        condition_counts: Dict[str, int] = {c["id"]: 0 for c in STUMPER_CONDITIONS}
        type_counts: Dict[str, int] = {}
        product_stumper_counts: Dict[str, set] = {}

        for it in items:
            c = it.get("failure_condition")
            if c in condition_counts:
                condition_counts[c] += 1

            t = it.get("jewellery_type", "").strip().lower()
            if not t and catalogue_lookup:
                meta = catalogue_lookup.get(it.get("product_id", ""), {})
                t = meta.get("category", "unknown").lower()
            t = t or "unknown"
            type_counts[t] = type_counts.get(t, 0) + 1

            pid = it.get("product_id")
            if pid and c:
                product_stumper_counts.setdefault(pid, set()).add(c)

        completed_products = sum(1 for s in product_stumper_counts.values() if len(s) >= len(STUMPER_CONDITIONS))
        in_progress_products = len(product_stumper_counts) - completed_products

        # Sort recent items by created_at descending
        sorted_recent = sorted(
            [it for it in items if it.get("created_at") != "pre-existing"],
            key=lambda x: x.get("created_at", ""),
            reverse=True,
        )[:24]

        total_cat = len(catalogue_lookup) if catalogue_lookup else 6157

        return {
            "total_products_catalogue": total_cat,
            "products_with_stumpers": len(product_stumper_counts),
            "completed_products_count": completed_products,
            "in_progress_products_count": in_progress_products,
            "total_stumper_photos": len(items),
            "by_condition": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "icon": c["icon"],
                    "count": condition_counts[c["id"]],
                }
                for c in STUMPER_CONDITIONS
            ],
            "by_jewellery_type": type_counts,
            "recent_uploads": sorted_recent,
        }


# Singleton collector instance
_collector_instance: Optional[StumperCollector] = None
_instance_lock = threading.Lock()


def get_collector() -> StumperCollector:
    """Return cached singleton instance of StumperCollector."""
    global _collector_instance
    if _collector_instance is None:
        with _instance_lock:
            if _collector_instance is None:
                _collector_instance = StumperCollector()
    return _collector_instance
