from app.evaluation.runner import run_evaluation, _load_gt_lookup, IMAGES_DIR
from app.retrieval.matcher import JewelleryMatcher
from app.config import CATALOGUE_CSV, ENCODER_MODEL, FAISS_INDEX_PATH, PRODUCT_IDS_PATH, SIMILARITY_THRESHOLD, TOP_K

print("Loading matcher...")
matcher = JewelleryMatcher(
    index_path=FAISS_INDEX_PATH,
    product_ids_path=PRODUCT_IDS_PATH,
    catalogue_csv_path=CATALOGUE_CSV,
    encoder_model=ENCODER_MODEL,
    threshold=SIMILARITY_THRESHOLD,
    top_k=TOP_K,
)
print("Matcher loaded. Running test on 5 images...")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
files = sorted([p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTS], key=lambda p: p.stem)
files_test = [f for f in files[:5] if f.stat().st_size >= 1024]
print(f"Testing: {[f.name for f in files_test]}")

for img in files_test:
    try:
        res = matcher.match(image_input=img, top_k=5)
        sim = res["results"][0]["similarity"] if res["results"] else 0
        print(f"  {img.name}: decision={res['decision']}, top1_sim={sim:.4f}")
    except Exception as e:
        print(f"  {img.name}: ERROR - {e}")

print("\nRunning FULL evaluation...")
try:
    report = run_evaluation(matcher)
    m = report["metrics"]
    print(f"Done! total={m['total_images']}, scored={m['scored_images']}, top1={m['top1_accuracy']*100:.1f}%")
except Exception as e:
    import traceback
    print(f"FAILED: {e}")
    traceback.print_exc()
