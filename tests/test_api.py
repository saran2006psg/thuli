"""
tests/test_api.py
─────────────────
Tests for FastAPI application endpoints:
  - GET  /api/health
  - GET  /api/stats
  - GET  /api/samples
  - POST /api/match (file upload, top_k, threshold)
  - GET  / (frontend index.html)
  - Error responses for invalid payloads
"""

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app.config import CATALOGUE_CSV, FAISS_INDEX_PATH
from app.main import app

client = TestClient(app)


def create_test_image_bytes(color=(220, 180, 60), size=(200, 200)) -> bytes:
    """Generate in-memory JPEG bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestAPIEndpoints:
    """Tests verifying FastAPI web endpoints."""

    def test_health_endpoint(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["index_size"] >= 6157
        assert data["dimension"] == 512

    def test_stats_endpoint(self):
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] >= 6157
        assert "earring" in data["categories"]
        assert "benchmarks" in data

    def test_samples_endpoint(self):
        response = client.get("/api/samples")
        assert response.status_code == 200
        samples = response.json()
        assert len(samples) >= 4
        for s in samples:
            assert "product_id" in s
            assert "image_path" in s
            assert "category" in s

    def test_serve_frontend_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "Thuli" in response.text
        assert "html" in response.headers.get("content-type", "")

    def test_match_endpoint_success(self):
        img_bytes = create_test_image_bytes()
        files = {"file": ("test_jewel.jpg", img_bytes, "image/jpeg")}
        data = {"top_k": "5", "threshold": "0.75"}

        response = client.post("/api/match", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["status"] == "success"
        assert res["decision"] in ["MATCH", "UNKNOWN"]
        assert len(res["results"]) == 5
        assert res["top_k"] == 5

        # Verify candidate keys
        top1 = res["results"][0]
        assert "product_id" in top1
        assert "product_name" in top1
        assert "category" in top1
        assert "similarity" in top1
        assert "image_url" in top1

    def test_match_endpoint_invalid_file_type(self):
        files = {"file": ("test.txt", b"plain text", "text/plain")}
        response = client.post("/api/match", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_match_endpoint_corrupt_image(self):
        files = {"file": ("corrupt.jpg", b"corrupted bytes", "image/jpeg")}
        response = client.post("/api/match", files=files)
        assert response.status_code == 400
        assert "Failed to decode" in response.json()["detail"]

    def test_add_catalogue_endpoint(self):
        # Create a mock image
        img = Image.new("RGB", (100, 100), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        files = {"file": ("blue_gem.jpg", buf, "image/jpeg")}
        data = {
            "category": "ring",
            "product_name": "Test Sapphire Ring",
            "subcategory": "cocktail_ring",
        }
        response = client.post("/api/catalogue/add", files=files, data=data)
        assert response.status_code == 200
        res = response.json()
        assert res["status"] == "success"
        assert res["product_id"].startswith("JW_")
        assert res["product_name"] == "Test Sapphire Ring"
        assert res["category"] == "ring"
        assert res["catalogue_size"] >= 6157
        assert "image_url" in res

