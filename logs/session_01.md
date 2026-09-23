# Session 01 — Phase 1: Catalogue Setup

**Date:** 2026-09-23  
**Phase:** 1 — Catalogue Setup  
**Goal:** Create a clean jewellery catalogue with ≥5,000 images from a public source.

---

## What Was Done

### Planning
- Reviewed PS2 full specification (`context/context.md`)
- Reviewed phase breakdown (`context/decision.md`)
- Chose HuggingFace `ashraq/fashion-product-images-small` as primary data source (44k Myntra fashion products, includes jewellery subcategories)
- Decided to use perceptual hashing for deduplication instead of exact MD5

### AI Tool Used
- Antigravity IDE (Claude Sonnet 4.6 Thinking)

### Files Created This Session

| File | Purpose |
|---|---|
| `requirements.txt` | Phase 1 Python dependencies |
| `.env.example` | Config template for all phases |
| `scripts/download_dataset.py` | Downloads jewellery catalogue from HF/Kaggle |
| `scripts/clean_catalogue.py` | Validates, deduplicates, cleans catalogue |
| `tests/test_catalogue.py` | Verifies catalogue meets Phase 1 requirements |
| `DECISIONS.md` | Started architecture decisions log |
| `data/README.md` | Documents data directory layout |
| Stub files under `app/` | Empty placeholders for Phase 2–5 |

### Project Skeleton Created
```
thuli/
├── app/ (api/, retrieval/, preprocessing/)
├── data/ (catalogue/)
├── scripts/
├── evaluation/ (images/)
├── experiments/
├── tests/
├── logs/
└── artifacts/ (embeddings/, indexes/)
```

---

## AI Suggestions Accepted vs Modified

| Suggestion | Accepted/Modified | Reason |
|---|---|---|
| HuggingFace as primary source | Accepted | No credentials required; reproducible |
| Kaggle as fallback | Accepted | More flexibility; optional credentials |
| pHash deduplication | Accepted | Better than MD5 for visual near-duplicates |
| JW_NNNNNN ID scheme | Accepted | Clean, stable, human-readable |
| JPEG quality=95 | Accepted | Good quality/size balance for embeddings |

---

## Final Outcome — Phase 1 Complete

- **Primary Source**: `sidd707/jewelry-design-dataset` (HuggingFace)
- **Ingested Items**: 8,565 raw images
- **Clean Catalogue**: 5,804 validated items in `data/catalogue.csv`
- **Catalogue Images**: Stored in `data/catalogue/` (JW_000001 ... JW_008565)
- **Tests**: `pytest tests/test_catalogue.py -v` -> **11/11 tests PASSED** (100% pass)
- **Cleanup**: Temporary unstandardized `dataset/` folder removed to save disk space.

---

## Next Steps

1. Phase 2: Embedding Generation (CLIP / DINOv2)
2. Generate catalogue embeddings (`artifacts/embeddings/catalogue_embeddings.npy`)
3. Build vector index (FAISS / HNSW)

