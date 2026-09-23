# data/README.md — Data Directory

## Structure

```
data/
├── catalogue/           ← downloaded images (JW_000001.jpg … JW_NNNNNN.jpg)
├── catalogue.csv        ← clean manifest (output of clean_catalogue.py)
├── raw_catalogue.csv    ← unfiltered manifest (output of download_dataset.py)
└── rejected.csv         ← entries removed during cleaning (with reasons)
```

## catalogue.csv Schema

| Column | Type | Description |
|---|---|---|
| `product_id` | str | Stable unique ID, format `JW_NNNNNN` |
| `product_name` | str | Human-readable product name |
| `category` | str | ring / necklace / earring / bracelet / pendant / bangle / chain / anklet / brooch / watch / jewellery |
| `image_path` | str | Relative path from project root: `data/catalogue/JW_NNNNNN.jpg` |
| `source_url` | str | Original source reference (HuggingFace or Kaggle) |
| `width` | int | Image width in pixels |
| `height` | int | Image height in pixels |

## Reproduction

```bash
python scripts/download_dataset.py   # download from HuggingFace (default)
python scripts/clean_catalogue.py    # validate + clean
pytest tests/test_catalogue.py -v    # verify
```

## Notes

- Images not tracked by git (add `data/catalogue/` to `.gitignore`)
- `catalogue.csv` and `rejected.csv` should be committed to git for reproducibility
- Source: HuggingFace `ashraq/fashion-product-images-small`, jewellery subcategories
