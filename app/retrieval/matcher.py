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
    PROJECT_ROOT,
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
        self.index_path = Path(index_path)
        self.product_ids_path = Path(product_ids_path)
        self.catalogue_csv_path = Path(catalogue_csv_path)

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

    def get_next_product_id(self) -> str:
        """Return the next recommended unique sequential product ID."""
        all_known_pids = set(self.product_ids) | set(self.catalogue_lookup.keys())
        max_num = 0
        for pid in all_known_pids:
            if pid.startswith("JW_"):
                try:
                    num = int(pid[3:])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        next_num = max_num + 1 if max_num > 0 else len(self.product_ids) + 1
        while f"JW_{next_num:06d}" in all_known_pids:
            next_num += 1
        return f"JW_{next_num:06d}"

    def add_catalogue_item(
        self,
        image_input: Union[str, Path, Image.Image],
        category: str,
        product_name: Optional[str] = None,
        subcategory: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dynamically add a new jewellery item to the catalogue, extract its CLIP
        embedding, index it into FAISS, and persist metadata and indexes to disk.

        Args:
            image_input: PIL Image, filepath string, or Path.
            category: Category name (e.g. 'ring', 'necklace', 'earring', 'bracelet', 'pendant').
            product_name: Optional product name/title.
            subcategory: Optional subcategory descriptor.
            product_id: Optional custom Product ID (auto-generated if omitted).

        Returns:
            Dictionary containing the created item metadata and updated catalogue size.
        """
        # 1. Preprocess and validate image
        pil_img = load_and_preprocess_image(image_input)

        # 2. Determine unique product_id (custom or next sequential unique e.g. JW_006158)
        if product_id and product_id.strip():
            clean_pid = product_id.strip()
            if clean_pid in self.catalogue_lookup or clean_pid in self.product_ids:
                raise ValueError(f"Product ID '{clean_pid}' already exists in catalogue.")
            product_id = clean_pid
        else:
            product_id = self.get_next_product_id()

        # 3. Save image into category folder
        norm_cat = category.strip().lower() if category else "jewellery"
        target_dir = PROJECT_ROOT / "data" / "catalogue" / "jewelry_dataset" / norm_cat
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / f"{product_id.lower()}.jpg"
        pil_img.save(target_file, format="JPEG", quality=95)
        relative_path = str(target_file.relative_to(PROJECT_ROOT)).replace("\\", "/")

        # 4. Extract 512-d normalized embedding vector
        embedding = self.encoder.encode_image(pil_img)

        # 5. Add vector to FAISS index & persist
        self.index.add(embedding.reshape(1, -1))
        self.index.save(self.index_path)

        # 6. Append to product_ids & persist
        self.product_ids.append(product_id)
        with open(self.product_ids_path, "w", encoding="utf-8") as f:
            json.dump(self.product_ids, f, indent=2)

        # 7. Append to catalogue_embeddings.npy if it exists
        if EMBEDDINGS_PATH.exists():
            try:
                old_embs = np.load(EMBEDDINGS_PATH)
                new_embs = np.vstack([old_embs, embedding.reshape(1, -1)])
                np.save(EMBEDDINGS_PATH, new_embs.astype(np.float32))
            except Exception as e:
                print(f"[WARN] Failed to update embeddings.npy: {e}")

        # 8. Update catalogue.csv and self.catalogue_lookup
        prod_title = product_name.strip() if product_name and product_name.strip() else f"{norm_cat.capitalize()} {product_id}"
        row_dict = {
            "product_id": product_id,
            "product_name": prod_title,
            "category": norm_cat,
            "subcategory": subcategory.strip() if subcategory else norm_cat,
            "image_path": relative_path,
            "source_url": "user_upload",
            "width": str(pil_img.width),
            "height": str(pil_img.height),
        }

        # Append to CSV
        file_exists = self.catalogue_csv_path.exists()
        with open(self.catalogue_csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["product_id", "product_name", "category", "subcategory", "image_path", "source_url", "width", "height"]
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_dict)

        self.catalogue_lookup[product_id] = row_dict

        return {
            "status": "success",
            "product_id": product_id,
            "product_name": prod_title,
            "category": norm_cat,
            "subcategory": row_dict["subcategory"],
            "image_path": relative_path,
            "image_url": "/" + relative_path,
            "catalogue_size": self.index.size,
            "width": pil_img.width,
            "height": pil_img.height,
        }

