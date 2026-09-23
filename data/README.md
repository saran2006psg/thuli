# data/ — Data Directory

## Structure

```
data/
├── sources/                 ← DROP ZONE: put manually downloaded datasets here
│   ├── README.md            ← instructions for adding sources
│   ├── <source_name>/
│   │   ├── source_info.json ← optional metadata description
│   │   └── images/          ← raw images go here
│   └── ...
│
├── catalogue/               ← generated: standardised images (JW_000001.jpg …)
├── catalogue.csv            ← generated: clean manifest (output of clean_catalogue.py)
├── raw_catalogue.csv        ← generated: unfiltered manifest (output of ingest_sources.py)
└── rejected.csv             ← generated: removed entries with rejection reasons
```

## catalogue.csv Schema

| Column | Type | Description |
|---|---|---|
| `product_id` | str | Stable unique ID, format `JW_NNNNNN` |
| `product_name` | str | Human-readable product name |
| `category` | str | ring / necklace / earring / bracelet / pendant / bangle / chain / anklet / brooch / watch / jewellery |
| `image_path` | str | Relative path from project root: `data/catalogue/JW_NNNNNN.jpg` |
| `source_url` | str | Original source reference |
| `width` | int | Image width in pixels |
| `height` | int | Image height in pixels |

## How to Build the Catalogue

### Step 1 — Add datasets to data/sources/

For each dataset you downloaded:
```
data/sources/
    kaggle_jewellery/
        source_info.json     ← fill in source name + URL
        images/
            *.jpg / *.png / ...
```

See [`data/sources/README.md`](sources/README.md) for full instructions.

### Step 2 — Ingest

```bash
python scripts/ingest_sources.py --dry-run    # preview counts
python scripts/ingest_sources.py              # actually ingest
```

### Step 3 — Clean

```bash
python scripts/clean_catalogue.py
```

### Step 4 — Verify

```bash
pytest tests/test_catalogue.py -v
```

## Notes

- `data/catalogue/` images are NOT tracked by git (too large)
- `data/sources/**/images/` NOT tracked by git
- `catalogue.csv` and `rejected.csv` SHOULD be committed (small, text)
- `source_info.json` files SHOULD be committed (documents data provenance)
