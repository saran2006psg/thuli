"""
tests/test_data_collection.py
─────────────────────────────
Comprehensive tests for Data Collection & Stumper Pipeline:
  - 10 conditions API verification
  - Next sequential product ID generation
  - Creating new catalogue item with dynamic CLIP embedding & FAISS indexing
  - Stumper photo capture (camera / upload simulation)
  - Duplicate product ID prevention
  - Stumper progress calculation (e.g. 1/10, 2/10)
  - Dataset statistics (by condition, by type)
  - Immediate visual searchability of the newly created item
"""

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.collector import STUMPER_CONDITIONS
from app.config import CATALOGUE_CSV, FAISS_INDEX_PATH
from app.main import app

client = TestClient(app)


def make_test_image_bytes(color=(210, 160, 45), size=(150, 150)) -> bytes:
    """Generate in-memory RGB JPEG image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


class TestDataCollectionPipeline:
    """Test suite for full data collection and stumper workflow."""

    def test_get_stumper_conditions(self):
        """Verify the 10 failure conditions are correctly configured."""
        resp = client.get("/api/stumper/conditions")
        assert resp.status_code == 200
        conditions = resp.json()
        assert len(conditions) == 10
        expected_ids = {
            "normal", "bad_lighting", "bright_lighting", "odd_angle",
            "occlusion", "clutter", "motion_blur", "reflection",
            "hand_wrist", "distance",
        }
        actual_ids = {c["id"] for c in conditions}
        assert actual_ids == expected_ids
        for c in conditions:
            assert "name" in c
            assert "description" in c
            assert "icon" in c

    def test_next_product_id_format(self):
        """Verify next product ID generator returns standard JW_XXXXXX format."""
        resp = client.get("/api/catalogue/next-id")
        assert resp.status_code == 200
        data = resp.json()
        assert "next_product_id" in data
        assert data["next_product_id"].startswith("JW_")
        assert len(data["next_product_id"]) == 9

    def test_create_product_and_stumper_flow(self):
        """
        Complete end-to-end flow:
        1. Fetch next ID
        2. Create product with clean reference photo (CLIP embed + FAISS index + CSV update)
        3. Verify product appears in /api/catalogue/products
        4. Upload 2 stumper conditions (normal and bad_lighting)
        5. Verify product progress is 2/10
        6. Verify dataset statistics include the uploaded stumpers
        7. Search with the same image in Visual Search (/api/match) and verify the product is retrieved!
        """
        # Step 1: Get next ID
        next_resp = client.get("/api/catalogue/next-id")
        next_id = next_resp.json()["next_product_id"]

        # Step 2: Create Product
        clean_img_bytes = make_test_image_bytes(color=(235, 175, 40))
        create_resp = client.post(
            "/api/catalogue/create",
            files={"file": ("reference.jpg", clean_img_bytes, "image/jpeg")},
            data={
                "product_id": next_id,
                "jewellery_type": "Ring",
                "product_name": f"Royal Gold Ring {next_id}",
            },
        )
        assert create_resp.status_code == 200, create_resp.text
        created_data = create_resp.json()
        assert created_data["status"] == "success"
        prod_id = created_data["product_id"]
        assert prod_id == next_id

        # Step 3: Verify product exists in catalogue products list
        list_resp = client.get(f"/api/catalogue/products?q={prod_id}")
        assert list_resp.status_code == 200
        products_list = list_resp.json()["products"]
        assert any(p["product_id"] == prod_id for p in products_list)

        # Step 4: Upload Stumper Photo 1 — Normal
        stump1_bytes = make_test_image_bytes(color=(220, 170, 30))
        s1_resp = client.post(
            "/api/stumper/upload",
            files={"file": ("stump_normal.jpg", stump1_bytes, "image/jpeg")},
            data={
                "product_id": prod_id,
                "failure_condition": "normal",
                "notes": "Handheld reference photo in ambient light",
                "jewellery_type": "ring",
            },
        )
        assert s1_resp.status_code == 200, s1_resp.text
        s1_data = s1_resp.json()
        assert s1_data["status"] == "success"
        assert s1_data["progress"]["completed_count"] >= 1
        assert "normal" in s1_data["progress"]["completed_conditions"]

        # Step 5: Upload Stumper Photo 2 — Bad Lighting
        stump2_bytes = make_test_image_bytes(color=(80, 60, 20))
        s2_resp = client.post(
            "/api/stumper/upload",
            files={"file": ("stump_bad_lighting.jpg", stump2_bytes, "image/jpeg")},
            data={
                "product_id": prod_id,
                "failure_condition": "bad_lighting",
                "notes": "Dim hallway with harsh shadow",
                "jewellery_type": "ring",
            },
        )
        assert s2_resp.status_code == 200, s2_resp.text
        s2_data = s2_resp.json()
        assert s2_data["progress"]["completed_count"] >= 2
        assert "bad_lighting" in s2_data["progress"]["completed_conditions"]

        # Step 6: Query product stumper details
        det_resp = client.get(f"/api/stumper/product/{prod_id}")
        assert det_resp.status_code == 200
        det_data = det_resp.json()
        assert det_data["completed_count"] >= 2
        assert det_data["percent"] >= 20
        assert "normal" in det_data["stumpers"]
        assert "bad_lighting" in det_data["stumpers"]

        # Step 7: Check dataset stats
        stats_resp = client.get("/api/stumper/dataset")
        assert stats_resp.status_code == 200
        ds_stats = stats_resp.json()
        assert ds_stats["total_stumper_photos"] >= 2
        assert ds_stats["products_with_stumpers"] >= 1

        # Step 8: Visual Search Verification
        # Searching with the clean reference image MUST return the newly created product in candidate results!
        search_resp = client.post(
            "/api/match",
            files={"file": ("query.jpg", clean_img_bytes, "image/jpeg")},
            data={"top_k": 5, "threshold": 0.50},
        )
        assert search_resp.status_code == 200, search_resp.text
        search_data = search_resp.json()
        assert search_data["status"] == "success"
        candidate_ids = [c["product_id"] for c in search_data["results"]]
        assert prod_id in candidate_ids, f"Expected {prod_id} in {candidate_ids}"
        # Top 1 should have high similarity with itself
        top_match = next(c for c in search_data["results"] if c["product_id"] == prod_id)
        assert top_match["similarity"] > 0.90

    def test_duplicate_product_id_rejected(self):
        """Verify attempting to recreate an existing product ID raises a 400 error."""
        existing_pid = "JW_000001"
        img_bytes = make_test_image_bytes()
        resp = client.post(
            "/api/catalogue/create",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")},
            data={
                "product_id": existing_pid,
                "jewellery_type": "ring",
            },
        )
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_invalid_condition_rejected(self):
        """Verify invalid condition string is rejected with a 400 error."""
        img_bytes = make_test_image_bytes()
        resp = client.post(
            "/api/stumper/upload",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")},
            data={
                "product_id": "JW_000001",
                "failure_condition": "super_impossible_condition",
            },
        )
        assert resp.status_code == 400
        assert "Invalid condition" in resp.json()["detail"]
