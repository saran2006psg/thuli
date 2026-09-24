# Stumper Evaluation Dataset Guide

This directory contains the real-world **Stumper Dataset** used to rigorously evaluate the **PS2 — Stump the Model** retrieval system under challenging conditions.

---

## 1. Directory Structure

```
evaluation/
├── README.md               # This guide
├── stumper.csv             # Ground-truth annotations for phone photos
├── images/                 # Store your captured photos here (e.g. stump_0001.jpg)
├── results.csv             # Generated output per query from scripts/evaluate.py
├── metrics.json            # Generated aggregate metrics (Top-1, Top-5, per condition)
└── analysis.md             # Generated error analysis report
```

---

## 2. Image Guidelines & Capturing Protocol

Take **100+ phone photos** of real jewellery items that exist in our catalogue (`data/catalogue.csv`).
Deliberately capture photos under challenging real-world failure conditions.

### Target Distribution (~10–15 photos per condition):
1. `bad_lighting` — Low ambient light, harsh shadows, yellow tungsten tint, backlighting.
2. `unusual_angle` — Steep side view, 45° angle, tilted, top-down isometric view.
3. `occlusion` — Partially covered by fingers, cloth, jewelry pouch, price tag, box edge.
4. `cluttered_background` — Patterned tablecloth, wooden textures, mixed objects on desk.
5. `motion_blur` — Slight camera shake, moving hand, low shutter speed blur.
6. `reflection` — Specular highlights on gold/silver surfaces, gemstone glare, glass reflections.
7. `hand_wrist_visible` — Ring on finger, bracelet on wrist, necklace on neck, item held in fingers.
8. `distance_scale` — Distant shot (item occupies <20% of frame) or extreme macro close-up.
9. `multiple_items` — Two or more jewellery pieces visible in the same frame.

---

## 3. Metadata Annotation Format (`stumper.csv`)

File: `evaluation/stumper.csv`

| Column | Type | Example | Description |
|---|---|---|---|
| `image_id` | string | `stump_0001` | Unique ID matching filename `stump_0001.jpg` |
| `product_id` | string | `JW_000042` | Ground-truth catalogue product ID (`JW_NNNNNN`) |
| `failure_condition` | string | `bad_lighting` | One of the standard failure conditions listed above |
| `notes` | string | `Dim room with shadows` | Brief description of capture context |
| `image_path` | string | `evaluation/images/stump_0001.jpg` | Path relative to project root |

### Example CSV Rows:
```csv
image_id,product_id,failure_condition,notes,image_path
stump_0001,JW_000001,bad_lighting,Dim indoor lighting with yellow tint,evaluation/images/stump_0001.jpg
stump_0002,JW_000001,unusual_angle,Steep 60 degree top-down view,evaluation/images/stump_0002.jpg
stump_0003,JW_000012,occlusion,Partially covered by jewelry box lid,evaluation/images/stump_0003.jpg
stump_0004,JW_000088,hand_wrist_visible,Bracelet worn on wrist with skin visible,evaluation/images/stump_0004.jpg
```

---

## 4. How to Validate & Run Evaluation

### Step 1: Validate Dataset Integrity
Check that all image files exist, all product IDs exist in `catalogue.csv`, and failure labels are valid:
```bash
python scripts/validate_stumper_dataset.py
```

### Step 2: Run Full Stumper Evaluation
Run the exact production `JewelleryMatcher` across all photos:
```bash
python scripts/evaluate.py
```

### Outputs Generated:
- `evaluation/results.csv` — Full row-by-row prediction logs.
- `evaluation/metrics.json` — Aggregated Top-1, Top-5, per-condition breakdown, and latency percentiles.
- `evaluation/analysis.md` — Detailed error breakdown and failure mode insights.
