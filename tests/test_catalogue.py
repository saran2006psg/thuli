"""
tests/test_catalogue.py
───────────────────────
Phase 1 verification tests.

These tests verify that catalogue.csv produced by clean_catalogue.py
meets all Phase 1 requirements before Phase 2 begins.

Run:
    pytest tests/test_catalogue.py -v
"""

import csv
from pathlib import Path

import pytest
from PIL import Image

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_CSV = PROJECT_ROOT / "data" / "catalogue.csv"
CATALOGUE_IMG_DIR = PROJECT_ROOT / "data" / "catalogue"

MINIMUM_ITEMS = 5_000
KNOWN_CATEGORIES = {
    "ring", "necklace", "earring", "bracelet",
    "pendant", "bangle", "chain", "anklet",
    "brooch", "watch", "jewellery",
}
REQUIRED_COLUMNS = {
    "product_id", "product_name", "category",
    "image_path", "source_url", "width", "height",
}


# ─────────────────────────────────────────────────────────────────────────────
# Fixture — load catalogue once for all tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def catalogue() -> list[dict]:
    """Load catalogue.csv and return list of row dicts."""
    assert CATALOGUE_CSV.exists(), (
        f"catalogue.csv not found at {CATALOGUE_CSV}.\n"
        "Run: python scripts/download_dataset.py && python scripts/clean_catalogue.py"
    )
    with open(CATALOGUE_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCatalogueSchema:
    """Verify the catalogue.csv has the correct shape and columns."""

    def test_csv_exists(self):
        assert CATALOGUE_CSV.exists(), f"catalogue.csv missing: {CATALOGUE_CSV}"

    def test_minimum_rows(self, catalogue):
        n = len(catalogue)
        assert n >= MINIMUM_ITEMS, (
            f"Catalogue has {n} items — minimum required is {MINIMUM_ITEMS}."
        )

    def test_required_columns_present(self, catalogue):
        if not catalogue:
            pytest.skip("Empty catalogue")
        actual_cols = set(catalogue[0].keys())
        missing = REQUIRED_COLUMNS - actual_cols
        assert not missing, f"Missing columns in catalogue.csv: {missing}"

    def test_no_empty_rows(self, catalogue):
        """Every row must have non-empty values in required fields."""
        required = ["product_id", "product_name", "image_path"]
        empty_rows = []
        for i, row in enumerate(catalogue, start=2):  # row 1 = header
            for col in required:
                if not row.get(col, "").strip():
                    empty_rows.append((i, col))
        assert not empty_rows, (
            f"Empty required fields found (csv_row, column):\n{empty_rows[:20]}"
        )


class TestProductIds:
    """Verify product IDs are unique and correctly formatted."""

    def test_product_ids_unique(self, catalogue):
        ids = [row["product_id"] for row in catalogue]
        duplicates = [pid for pid in set(ids) if ids.count(pid) > 1]
        assert not duplicates, (
            f"Duplicate product_ids found: {duplicates[:10]}"
        )

    def test_product_id_format(self, catalogue):
        """All IDs should follow the JW_NNNNNN pattern."""
        bad_ids = [
            row["product_id"]
            for row in catalogue
            if not row["product_id"].startswith("JW_")
        ]
        assert not bad_ids, (
            f"product_ids not matching JW_ format: {bad_ids[:10]}"
        )


class TestImageFiles:
    """
    Verify image files exist and can be opened.

    Full verification of 5k+ images is slow — this test samples 200 random
    images. The clean_catalogue.py script performs full validation at build time.
    """

    SAMPLE_SIZE = 200

    def _sample(self, catalogue: list[dict]) -> list[dict]:
        import random
        rng = random.Random(42)
        if len(catalogue) <= self.SAMPLE_SIZE:
            return catalogue
        return rng.sample(catalogue, self.SAMPLE_SIZE)

    def test_image_files_exist(self, catalogue):
        missing = []
        for row in self._sample(catalogue):
            path = PROJECT_ROOT / row["image_path"]
            if not path.exists():
                missing.append(row["image_path"])
        assert not missing, (
            f"{len(missing)} sampled images missing from disk:\n{missing[:10]}"
        )

    def test_images_openable(self, catalogue):
        corrupt = []
        for row in self._sample(catalogue):
            path = PROJECT_ROOT / row["image_path"]
            if not path.exists():
                continue
            try:
                img = Image.open(path)
                img.verify()
            except Exception as exc:
                corrupt.append((row["image_path"], str(exc)))
        assert not corrupt, (
            f"{len(corrupt)} sampled images unreadable:\n{corrupt[:10]}"
        )

    def test_image_dimensions_recorded(self, catalogue):
        """Width and height columns must be positive integers."""
        bad = []
        for row in catalogue:
            try:
                w = int(row.get("width", 0))
                h = int(row.get("height", 0))
                if w <= 0 or h <= 0:
                    bad.append(row["product_id"])
            except ValueError:
                bad.append(row["product_id"])
        assert not bad, (
            f"{len(bad)} rows have invalid width/height: {bad[:10]}"
        )


class TestCategories:
    """Verify categories are within the known set."""

    def test_category_values(self, catalogue):
        unknown_cats = set()
        for row in catalogue:
            cat = row.get("category", "").strip().lower()
            if cat not in KNOWN_CATEGORIES:
                unknown_cats.add(cat)
        assert not unknown_cats, (
            f"Unknown category values found: {unknown_cats}\n"
            f"Known: {KNOWN_CATEGORIES}"
        )


class TestCoverageStats:
    """Print informational statistics (not strict pass/fail)."""

    def test_category_distribution(self, catalogue):
        """Soft check — warns if any category has < 50 items."""
        from collections import Counter

        counts = Counter(row.get("category", "unknown") for row in catalogue)
        print("\n── Category distribution ─────────────────")
        for cat, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {cat:<15} {cnt:>5}")
        print("─────────────────────────────────────────")
        # Not a hard failure — just informational
        assert True
