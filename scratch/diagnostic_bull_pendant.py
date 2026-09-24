"""
Diagnostic script to:
1. Find ground-truth product ID for the bull pendant image.
2. Crop the advertisement image to isolate the jewellery piece.
3. Run JewelleryMatcher on:
   A. Full advertisement image
   B. Cropped jewellery image
4. Print detailed comparison and diagnostics.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import numpy as np
import pandas as pd
from PIL import Image

from app.config import (
    CATALOGUE_CSV,
    FAISS_INDEX_PATH,
    PRODUCT_IDS_PATH,
    SIMILARITY_THRESHOLD,
    TOP_K,
)
from app.retrieval.matcher import JewelleryMatcher

USER_UPLOADED_DIR = Path(r"C:\Users\SARAN M\.gemini\antigravity-ide\brain\40e0c8fe-7358-4682-bf87-8b0d67629c2c\.user_uploaded")
IMG_CATALOGUE_SAMPLE = USER_UPLOADED_DIR / "media_1790263209690.png"
IMG_AD = USER_UPLOADED_DIR / "media_1790263218637.jpg"

matcher = JewelleryMatcher(
    index_path=FAISS_INDEX_PATH,
    product_ids_path=PRODUCT_IDS_PATH,
    catalogue_csv_path=CATALOGUE_CSV,
    threshold=SIMILARITY_THRESHOLD,
    top_k=TOP_K,
)

# 1. Identify the ground-truth product in the catalogue using the sample image
print("--- Finding Ground Truth Product in Catalogue ---")
res_sample = matcher.match(IMG_CATALOGUE_SAMPLE, top_k=5, threshold=0.5)
gt_product_id = res_sample["results"][0]["product_id"]
gt_similarity = res_sample["results"][0]["similarity"]
gt_metadata = res_sample["results"][0]

print(f"Top match for sample image:")
print(f"  Product ID   : {gt_product_id}")
print(f"  Similarity   : {gt_similarity:.4f}")
print(f"  Product Name : {gt_metadata.get('product_name')}")
print(f"  Category     : {gt_metadata.get('category')}")
print(f"  Image Path   : {gt_metadata.get('image_path')}")

# Also check top 3 for sample just to be sure
for i, c in enumerate(res_sample["results"][:3], 1):
    print(f"    #{i} {c['product_id']}: sim={c['similarity']:.4f} ({c['product_name']})")

# 2. Evaluate Experiment A: Full Advertisement Image
print("\n--- Experiment A: Full Advertisement Image ---")
res_ad = matcher.match(IMG_AD, top_k=5, threshold=SIMILARITY_THRESHOLD)

print(f"Decision        : {res_ad['decision']}")
print(f"Best Similarity : {res_ad['best_similarity']:.4f} (Threshold: {res_ad['threshold']:.2f})")
print(f"Query Time      : {res_ad['query_time_ms']:.2f} ms")
print("Top-5 Candidates:")
ad_cand_ids = [c["product_id"] for c in res_ad["results"]]
for c in res_ad["results"]:
    is_gt = " <-- [GROUND TRUTH]" if c["product_id"] == gt_product_id else ""
    print(f"  Rank {c['rank']}: {c['product_id']} | Sim: {c['similarity']:.4f} | {c['category']} | {c['product_name']}{is_gt}")

gt_rank_a = ad_cand_ids.index(gt_product_id) + 1 if gt_product_id in ad_cand_ids else None
print(f"Ground-Truth Rank in Top-5: {gt_rank_a if gt_rank_a else 'NOT in Top-5'}")

# Also search top 50 to see where ground truth actually ranks for the full ad
all_scores, all_indices = matcher.index.search(
    matcher.encoder.encode_image(Image.open(IMG_AD)),
    top_k=50
)
gt_idx = matcher.product_ids.index(gt_product_id)
if gt_idx in all_indices[0]:
    actual_pos = list(all_indices[0]).index(gt_idx) + 1
    actual_score = all_scores[0][actual_pos - 1]
    print(f"Ground-Truth actual rank in Top-50: #{actual_pos} with similarity {actual_score:.4f}")
else:
    print(f"Ground-Truth is outside Top-50 for full ad image.")

# 3. Create Cropped Image (Crop B: isolate the pendant)
# Inspect dimensions of IMG_AD
ad_img = Image.open(IMG_AD)
w, h = ad_img.size
print(f"\nAd Image Dimensions: {w} x {h}")

# In the advertisement, the bull pendant is located roughly in the upper-middle area.
# Let's crop tight around the bull pendant:
# Bull horns go from ~25% to ~85% width, top ring to bottom snout goes from ~25% to ~60% height.
crop_box = (int(w * 0.25), int(h * 0.24), int(w * 0.88), int(h * 0.60))
cropped_img = ad_img.crop(crop_box)
cropped_path = USER_UPLOADED_DIR / "bull_pendant_cropped.jpg"
cropped_img.save(cropped_path, quality=95)
print(f"Saved cropped image to {cropped_path} (box: {crop_box})")

# 4. Evaluate Experiment B: Cropped Image
print("\n--- Experiment B: Cropped Jewellery Image ---")
res_crop = matcher.match(cropped_path, top_k=5, threshold=SIMILARITY_THRESHOLD)

print(f"Decision        : {res_crop['decision']}")
print(f"Best Similarity : {res_crop['best_similarity']:.4f} (Threshold: {res_crop['threshold']:.2f})")
print(f"Query Time      : {res_crop['query_time_ms']:.2f} ms")
print("Top-5 Candidates:")
crop_cand_ids = [c["product_id"] for c in res_crop["results"]]
for c in res_crop["results"]:
    is_gt = " <-- [GROUND TRUTH]" if c["product_id"] == gt_product_id else ""
    print(f"  Rank {c['rank']}: {c['product_id']} | Sim: {c['similarity']:.4f} | {c['category']} | {c['product_name']}{is_gt}")

gt_rank_b = crop_cand_ids.index(gt_product_id) + 1 if gt_product_id in crop_cand_ids else None
print(f"Ground-Truth Rank in Top-5: {gt_rank_b if gt_rank_b else 'NOT in Top-5'}")

# Check rank in top 50 if needed
all_scores_b, all_indices_b = matcher.index.search(
    matcher.encoder.encode_image(cropped_img),
    top_k=50
)
if gt_idx in all_indices_b[0]:
    actual_pos_b = list(all_indices_b[0]).index(gt_idx) + 1
    actual_score_b = all_scores_b[0][actual_pos_b - 1]
    print(f"Ground-Truth actual rank in Top-50: #{actual_pos_b} with similarity {actual_score_b:.4f}")

