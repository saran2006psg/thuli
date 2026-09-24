# Phase 6 — Real-World Stumper Dataset & Evaluation

## 1. Overview & Purpose

In **Phase 6**, we establish the real-world evaluation framework required by the problem statement ("PS2: Stump the Model"). The primary goal is to rigorously measure how our baseline retrieval system (**CLIP ViT-B/32** + **FAISS `IndexFlatIP`**) performs on realistic, challenging smartphone photos of jewellery items that genuinely exist in our 6,157-item catalogue.

```
+-------------------------------------------------------------+
|                     BASELINE SYSTEM                         |
|  (CLIP ViT-B/32 + FAISS IndexFlatIP + Production Matcher)   |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|             100+ REAL-WORLD STUMPER IMAGES                  |
|    (Phone photos of actual catalogue jewellery items)       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                   PRODUCTION MATCHER                        |
|       (Exact JewelleryMatcher used in API / UI)             |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     PREDICTIONS                             |
|          (Top-1, Top-5 candidates, similarities)            |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                      METRICS                                |
|   (Top-1 %, Top-5 %, Per-Condition Accuracy, Latencies)    |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                 DETAILED FAILURE ANALYSIS                   |
|     (Saved in results.csv, metrics.json, analysis.md)       |
+-------------------------------------------------------------+
```

---

## 2. Dataset Design & Guidelines

The evaluation dataset consists of personally captured smartphone photos of jewellery items that exist in `data/catalogue.csv` (6,157 items).

### Rules for Dataset Creation
1. **No Fake/Synthetic Images:** Real smartphone camera photos only.
2. **Ground Truth Alignment:** Every captured image must map to a valid `product_id` (e.g., `JW_001234`) present in `data/catalogue.csv`.
3. **Diverse Challenge Conditions:** Each photo should represent at least one deliberate real-world difficulty mode.

---

## 3. Failure Conditions Taxonomy

| Failure Condition | Description | Example Real-World Scenario |
|---|---|---|
| `bad_lighting` | Low light, heavy shadows, uneven ambient lighting, harsh yellow incandescent light | Photo taken inside a dimly lit room or under uneven lamp shadows |
| `unusual_angle` | Extreme steep perspective, side view, diagonal tilt, back-side view | Photo taken looking down obliquely at 70 degrees from normal |
| `occlusion` | Item partially covered by fingers, cloth, tag, jewelry pouch | Ring or necklace partially covered by fingers holding it |
| `cluttered_background` | Non-white, textured, patterned backgrounds (wood, cloth, marble, desks) | Item placed on bedspread, wooden dining table, carpet |
| `motion_blur` | Slight or moderate camera shake / subject motion | Quick handheld snapshot without autofocus lock |
| `reflection` | Specular glare on gemstone or polished metal surfaces | Direct flashlight or sunlight bouncing off gold/diamond surfaces |
| `hand_wrist_visible` | Item worn on body (finger, ear, neck, wrist) or held in hand | Ring worn on finger, bracelet worn on wrist |
| `distance_scale` | Extreme close-up macro or distant wide shot | Distant snapshot where jewellery takes up <15% of frame area |
| `multiple_items` | Multiple jewellery pieces present in the frame | Earring set placed next to rings on a tray |
| `clean_control` | Well-lit, centered photo on neutral background | Control query to verify baseline clean performance |

---

## 4. Dataset Directory & Annotation Schema

### Directory Structure
```
evaluation/
├── README.md               # Instructions for capturing and annotating
├── stumper.csv             # Ground truth annotation table
├── images/                 # Directory containing phone-captured photos (e.g. stump_0001.jpg)
├── results.csv             # Evaluation run output (per-query predictions and ranks)
├── metrics.json            # Aggregate evaluation metrics (Top-1, Top-5, Latencies, Breakdowns)
└── analysis.md             # Markdown error analysis report
```

### Annotation Schema (`evaluation/stumper.csv`)
```csv
image_id,product_id,failure_condition,notes,image_path
stump_0001,JW_000142,bad_lighting,dim indoor light,evaluation/images/stump_0001.jpg
stump_0002,JW_001850,occlusion,partially covered by finger,evaluation/images/stump_0002.jpg
stump_0003,JW_003204,hand_wrist_visible,worn on wrist,evaluation/images/stump_0003.jpg
```

---

## 5. Validation Tools

Before running evaluation, the dataset is verified using:
```bash
python scripts/validate_stumper_dataset.py
```

The validation script checks:
- [x] CSV schema & required columns (`image_id`, `product_id`, `failure_condition`, `image_path`)
- [x] No duplicate `image_id` entries
- [x] Every `product_id` exists in `data/catalogue.csv`
- [x] Every `failure_condition` belongs to the allowed taxonomy
- [x] Every image file exists on disk and is readable via PIL `img.verify()`

---

## 6. Evaluation Methodology

The evaluation script (`scripts/evaluate.py`) uses the **exact production `JewelleryMatcher`** from `app.retrieval.matcher` to ensure zero discrepancy between offline evaluation and live serving:

1. Loads each stumper photo.
2. Extracts 512-d normalized embedding via CLIP ViT-B/32.
3. Executes FAISS `IndexFlatIP` search for Top-5 nearest neighbors.
4. Determines MATCH / UNKNOWN decision based on threshold $\tau$.
5. Records:
   - `image_id`
   - `ground_truth_product_id`
   - `predicted_top1_product_id`
   - `is_top1_correct` (bool)
   - `is_top5_correct` (bool)
   - `correct_rank` (1..5 or None)
   - `top1_similarity` (float)
   - `decision` (MATCH / UNKNOWN)
   - `failure_condition`
   - `latency_ms`
   - `top5_product_ids` (semicolon-separated)

### Running Evaluation
```bash
python scripts/evaluate.py
```

---

## 7. Metrics Specification

1. **Top-1 Accuracy:**
   $$\text{Top-1 Accuracy} = \frac{\sum_{i=1}^{N} \mathbb{I}(\hat{y}_{i,1} = y_i)}{N} \times 100\%$$
2. **Top-5 Accuracy:**
   $$\text{Top-5 Accuracy} = \frac{\sum_{i=1}^{N} \mathbb{I}(y_i \in \text{Top-5}(\hat{y}_i))}{N} \times 100\%$$
3. **Per-Condition Accuracy:** Top-1 and Top-5 accuracy segmented by each failure condition.
4. **Decision Distribution:** Count of queries classified as `MATCH` vs `UNKNOWN`.
5. **Latency Statistics:** Mean, median, p95, p99, min, and max retrieval latencies (in milliseconds).

---

## 8. Baseline Status & Next Steps

- **Pipeline Status:** Infrastructure, validation tools, production evaluator, and unit tests (**65/65 passing**) are fully operational.
- **Photos Status:** Awaiting real-world smartphone photo capture and annotation by the user in `evaluation/images/` and `evaluation/stumper.csv`.
- **Note:** In adherence to strict scientific evaluation principles, baseline metrics will be computed once real photos are provided, without inventing synthetic accuracy values.
