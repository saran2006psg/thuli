"""
app/retrieval/matcher.py
────────────────────────
Baseline Jewellery Matcher Pipeline (Phase 4).
Connects:
  Query Image -> Preprocessing -> Vision Encoder (CLIP) -> 512-d Embedding
  -> FAISS Retrieval -> Top-5 Candidates -> Metadata Resolution (catalogue.csv)
  -> Similarity Ranking -> MATCH / UNKNOWN Decision.
"""

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
from PIL import Image

from app.config import (
    CATALOGUE_CSV,
    EMBEDDINGS_PATH,
    ENCODER_MODEL,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.preprocessing.image import load_and_preprocess_image
from app.retrieval.encoder import JewelleryEncoder
from app.retrieval.index import FAISSIndex, get_product_ids


class JewelleryMatcher:
    """
    End-to-end jewellery image matching and retrieval engine.

    Pipeline:
      1. Preprocesses query image into clean RGB PIL format.
      2. Extracts L2-normalized 512-d feature vector using CLIP.
      3. Performs exact cosine similarity search in FAISS IndexFlatIP.
      4. Maps retrieved vector indices to product IDs and catalogue metadata.
      5. Applies decision logic:
         - best_similarity >= threshold -> "MATCH"
         - best_similarity < threshold  -> "UNKNOWN"
    """

    def __init__(
        self,
        index_path: Union[str, Path] = FAISS_INDEX_PATH,
        product_ids_path: Union[str, Path] = PRODUCT_IDS_PATH,
        catalogue_csv_path: Union[str, Path] = CATALOGUE_CSV,
        encoder_model: str = ENCODER_MODEL,
        threshold: float = SIMILARITY_THRESHOLD,
        top_k: int = TOP_K,
        device: Optional[str] = None,
        encoder: Optional[JewelleryEncoder] = None,
        index: Optional[FAISSIndex] = None,
    ):
        """
        Initialize the JewelleryMatcher.

        Args:
            index_path: Path to persisted FAISS index (.faiss).
            product_ids_path: Path to product IDs JSON file.
            catalogue_csv_path: Path to catalogue metadata CSV.
            encoder_model: Pretrained vision encoder name/checkpoint.
            threshold: Default similarity threshold for MATCH vs UNKNOWN.
            top_k: Default number of nearest neighbours to retrieve.
            device: 'cuda' or 'cpu' device for encoder.
            encoder: Optional pre-instantiated JewelleryEncoder (for fast test injection).
            index: Optional pre-instantiated FAISSIndex (for fast test injection).
        """
        self.default_threshold = float(threshold)
        self.default_top_k = int(top_k)

        # 1. Load or assign FAISS index
        if index is not None:
            self.index = index
        else:
            p_index = Path(index_path)
            if not p_index.exists():
                raise FileNotFoundError(f"FAISS index file not found at: {p_index}")
            self.index = FAISSIndex.load(p_index)

        # 2. Load product IDs
        p_ids = Path(product_ids_path)
        if not p_ids.exists():
            raise FileNotFoundError(f"Product IDs file not found at: {p_ids}")
        with open(p_ids, "r", encoding="utf-8") as f:
            self.product_ids: List[str] = json.load(f)

        if len(self.product_ids) != self.index.size:
            raise ValueError(
                f"Mismatch between product_ids count ({len(self.product_ids)}) and FAISS index size ({self.index.size})"
            )

        # 3. Load catalogue metadata
        p_csv = Path(catalogue_csv_path)
        if not p_csv.exists():
            raise FileNotFoundError(f"Catalogue CSV not found at: {p_csv}")

        self.catalogue_lookup: Dict[str, Dict[str, Any]] = {}
        with open(p_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                p_id = row.get("product_id")
                if p_id:
                    self.catalogue_lookup[p_id] = row

        # 4. Load or assign vision encoder
        if encoder is not None:
            self.encoder = encoder
        else:
            self.encoder = JewelleryEncoder(model_name=encoder_model, device=device)

    def match(
        self,
        image_input: Union[str, Path, Image.Image],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute full matching pipeline for a query image.

        Args:
            image_input: Filepath string, Path, or PIL Image.
            top_k: Optional override for number of top candidates (defaults to self.default_top_k).
            threshold: Optional override for decision threshold (defaults to self.default_threshold).

        Returns:
            Structured dictionary with decision, timing, and ranked candidates.
        """
        k = top_k if top_k is not None else self.default_top_k
        thresh = threshold if threshold is not None else self.default_threshold

        t_start = time.perf_counter()

        # Step 1: Preprocess image
        pil_img = load_and_preprocess_image(image_input)

        # Step 2: Encode to normalized 512-d vector
        query_embedding = self.encoder.encode_image(pil_img)

        # Step 3: Search FAISS index
        scores, indices = self.index.search(query_embedding, top_k=k)

        # Step 4: Map indices to product IDs and catalogue metadata
        candidate_results: List[Dict[str, Any]] = []
        for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), start=1):
            prod_id = self.product_ids[idx]
            meta = self.catalogue_lookup.get(prod_id, {})

            candidate_results.append({
                "rank": rank,
                "product_id": prod_id,
                "product_name": meta.get("product_name", prod_id),
                "category": meta.get("category", "unknown"),
                "subcategory": meta.get("subcategory", "unknown"),
                "image_path": meta.get("image_path", ""),
                "similarity": float(np.round(score, 6)),
                "width": int(meta["width"]) if meta.get("width") else None,
                "height": int(meta["height"]) if meta.get("height") else None,
            })

        # Step 5: Decision logic
        best_similarity = candidate_results[0]["similarity"] if candidate_results else 0.0
        decision = "MATCH" if best_similarity >= thresh else "UNKNOWN"

        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return {
            "status": "success",
            "decision": decision,
            "threshold": thresh,
            "best_similarity": best_similarity,
            "query_time_ms": float(np.round(t_elapsed_ms, 3)),
            "top_k": k,
            "results": candidate_results,
        }
