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

# Prevent transformers / tensorflow / protobuf conflicts
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# -- Paths ---------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Keep downloads portable by default. Set HF_HOME/TORCH_HOME in .env when a
# shared or larger cache location is preferred.
MODEL_CACHE_DIR = Path(os.getenv("MODEL_CACHE_DIR", str(PROJECT_ROOT / ".cache")))
os.environ.setdefault("HF_HOME", str(Path(os.getenv("HF_HOME", MODEL_CACHE_DIR / "huggingface"))))
os.environ.setdefault("TORCH_HOME", str(Path(os.getenv("TORCH_HOME", MODEL_CACHE_DIR / "torch"))))

CATALOGUE_CSV = PROJECT_ROOT / os.getenv("CATALOGUE_CSV", "data/catalogue.csv")
CATALOGUE_IMG_DIR = PROJECT_ROOT / os.getenv("CATALOGUE_IMG_DIR", "data/catalogue")

# -- Phase 2: Embeddings -------------------------------------------------------
ENCODER_MODEL: str = os.getenv("ENCODER_MODEL", "openai/clip-vit-base-patch32")
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "512"))
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "64"))
EMBEDDINGS_PATH = PROJECT_ROOT / os.getenv("EMBEDDINGS_PATH", "artifacts/embeddings/catalogue_embeddings.npy")
PRODUCT_IDS_PATH = PROJECT_ROOT / os.getenv("PRODUCT_IDS_PATH", "artifacts/embeddings/product_ids.json")

# -- Phase 3: FAISS ------------------------------------------------------------
FAISS_INDEX_PATH = PROJECT_ROOT / os.getenv("FAISS_INDEX_PATH", "artifacts/indexes/catalogue.faiss")
FAISS_INDEX_TYPE: str = os.getenv("FAISS_INDEX_TYPE", "Flat")

# -- Phase 4: Matcher ----------------------------------------------------------
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
TOP_K: int = int(os.getenv("TOP_K", "5"))
