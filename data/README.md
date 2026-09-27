# Data Directory (`data/`)

This directory houses the jewellery catalogue dataset, item metadata, and collected stumper images used for search indexing and evaluation.

---

## Directory Structure

```
data/
├── catalogue/
│   └── jewelry_dataset/
│       ├── bracelet/            # Bracelet catalogue images (.jpg)
│       ├── earring/             # Earring catalogue images (.jpg)
│       ├── necklace/            # Necklace catalogue images (.jpg)
│       └── ring/                # Ring catalogue images (.jpg)
├── catalogue.csv                # Primary catalogue metadata (6,157 items)
├── collected_stumpers.csv       # Stumper test photos captured via frontend
└── collected_stumpers.json      # Stumper metadata in JSON format
```

---

## Metadata Specification: `catalogue.csv`

The master catalogue index file `data/catalogue.csv` contains 6,157 entries with the following schema:

| Column | Type | Example | Description |
|---|---|---|---|
| `product_id` | String | `ring_00001` | Unique primary key for each jewellery piece |
| `product_name` | String | `Diamond Solitaire Ring` | Human-readable product title |
| `category` | String | `ring` | Top-level category (`ring`, `necklace`, `bracelet`, `earring`) |
| `image_path` | String | `data/catalogue/jewelry_dataset/ring/ring_00001.jpg` | Relative path from project root to image file |

---

## Category Distribution (6,157 Total Items)

- **Rings**: ~2,500 items
- **Necklaces**: ~1,800 items
- **Earrings**: ~1,200 items
- **Bracelets**: ~657 items

---

## Stumper Collection (`collected_stumpers.csv`)

Used during data collection sessions (e.g. from the **Collect Data** tab in the web interface). It logs:
- `product_id`: The catalogue item being tested.
- `failure_condition`: The physical challenge condition applied (e.g. `bad_lighting`, `occlusion`, `odd_angle`).
- `timestamp`: When the photo was captured.
- `image_path`: Path to the stored capture.

---

## Data Ingestion & Management

- To ingest new product batches into `catalogue.csv`:
  ```bash
  python -m scripts.ingest_new_data --source <path_to_images> --category <category>
  ```
- To regenerate `catalogue.csv` from the disk folder structure:
  ```bash
  python -m scripts.build_catalogue_csv
  ```
