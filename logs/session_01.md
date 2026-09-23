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

## Issues / Notes

- The HF dataset `ashraq/fashion-product-images-small` contains 44k products. Jewellery will be a subset. Need to verify ≥5,000 after filtering.
- If jewellery count is below 5,000, plan is to:
  1. Broaden keyword filter (include "watches" etc.)
  2. Try an additional Kaggle jewellery dataset
  3. Combine multiple sources

---

## Next Steps

1. Install Phase 1 requirements: `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`
3. Run `python scripts/download_dataset.py`
4. Run `python scripts/clean_catalogue.py`
5. Run `pytest tests/test_catalogue.py -v`
6. If ≥5,000 clean items → Phase 2 ready
