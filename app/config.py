"""
app/config.py
─────────────
Central configuration — reads .env and exposes typed settings.
Populated incrementally as new phases are implemented.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

CATALOGUE_CSV = PROJECT_ROOT / os.getenv("CATALOGUE_CSV", "data/catalogue.csv")
CATALOGUE_IMG_DIR = PROJECT_ROOT / os.getenv("CATALOGUE_IMG_DIR", "data/catalogue")

# ── Phase 2+ (uncomment as phases are implemented) ────────────────────────────
# ENCODER_MODEL: str = os.getenv("ENCODER_MODEL", "openai/clip-vit-base-patch32")
# EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "512"))
# BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "64"))
# EMBEDDINGS_PATH = PROJECT_ROOT / os.getenv("EMBEDDINGS_PATH", "artifacts/embeddings/catalogue_embeddings.npy")
# PRODUCT_IDS_PATH = PROJECT_ROOT / os.getenv("PRODUCT_IDS_PATH", "artifacts/embeddings/product_ids.json")

# ── Phase 3+ ─────────────────────────────────────────────────────────────────
# FAISS_INDEX_PATH = PROJECT_ROOT / os.getenv("FAISS_INDEX_PATH", "artifacts/indexes/catalogue.faiss")
# FAISS_INDEX_TYPE: str = os.getenv("FAISS_INDEX_TYPE", "Flat")

# ── Phase 4+ ─────────────────────────────────────────────────────────────────
# SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
# TOP_K: int = int(os.getenv("TOP_K", "5"))
