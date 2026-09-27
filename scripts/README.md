# Pipeline Scripts (`scripts/`)

This directory contains standalone Python utility scripts for the offline indexing pipeline, dataset generation, index benchmarking, evaluation, and data ingestion.

---

## Directory Structure

```
scripts/
├── setup.py                        # Automated project verification & environment check
├── build_catalogue_csv.py          # Scans catalogue image folders and generates catalogue.csv
├── generate_embeddings.py          # Batch encodes all 6,157 items with CLIP ViT-B/32
├── build_index.py                  # Builds and serializes FAISS IndexFlatIP
├── benchmark_index.py              # Performance & latency benchmarking for FAISS
├── generate_automated_stumper.py   # Generates 900 synthetic stumper images across 9 conditions
├── evaluate_automated_stumper.py   # Runs benchmark on 900 synthetic stumper images
├── evaluate.py                     # CLI evaluator for baseline test images
├── ingest_new_data.py              # Ingests new catalogue items and updates index
├── prepare_unseen_dataset.py       # Assembles open-set evaluation benchmark
├── run_final_validation.py         # End-to-end test verifying all project deliverables
├── run_matcher.py                  # CLI visual search tool for ad-hoc image queries
└── validate_stumper_dataset.py     # Data validation & integrity check for stumper.csv
```

---

## Script Descriptions & Usage

### 1. `setup.py`
Verifies Python version, dependencies, model weights (`FastSAM-s.pt`), FAISS binaries, and catalogue directories.
```bash
python -m scripts.setup
```

### 2. `build_catalogue_csv.py`
Scans `data/catalogue/jewelry_dataset/` and populates `data/catalogue.csv` with 6,157 validated records.
```bash
python -m scripts.build_catalogue_csv
```

### 3. `generate_embeddings.py`
Loads `sentence-transformers/clip-ViT-B-32`, encodes all catalogue images in batches, normalizes embeddings (L2), and saves:
- `artifacts/embeddings/catalogue_embeddings.npy`
- `artifacts/embeddings/product_ids.json`
```bash
python -m scripts.generate_embeddings
```

### 4. `build_index.py`
Initializes a FAISS `IndexFlatIP(512)` instance, adds the 6,157 vectors, and writes `artifacts/indexes/catalogue.faiss`.
```bash
python -m scripts.build_index
```

### 5. `benchmark_index.py`
Measures query throughput (QPS), P50 latency, and P95 latency across thousands of simulated searches.
```bash
python -m scripts.benchmark_index
```

### 6. `generate_automated_stumper.py`
Selects 100 representative catalogue items and generates 900 synthetic test images across 9 physical perturbations using PIL and OpenCV.
```bash
python -m scripts.generate_automated_stumper
```

### 7. `evaluate_automated_stumper.py`
Runs the matcher through all 900 automated stumper images and saves `automated_results.csv` and `automated_metrics.json`.
```bash
python -m scripts.evaluate_automated_stumper
```

### 8. `run_matcher.py`
Query the visual search engine directly from the command line:
```bash
python -m scripts.run_matcher --image path/to/jewellery.jpg --top-k 5
```

### 9. `run_final_validation.py`
Comprehensive test harness validating catalogue integrity, embedding shapes, FAISS search, threshold behavior, API routes, and evaluation metrics.
```bash
python -m scripts.run_final_validation
```
