# PS2 — Stump the Model: Jewellery Image Retrieval

An image retrieval system that identifies exact jewellery catalogue items from real-world photographs, built using embedding-based nearest-neighbour search.

---

## Problem

Given a photograph of a jewellery item, find the matching product from a catalogue of 5,000+ items and return the Top-5 candidates with similarity scores.

## Architecture

```
Query Image
    ↓ Preprocessing
    ↓ Vision Encoder (pretrained)
    ↓ Embedding Vector
    ↓ FAISS Similarity Search
    ↓ Top-5 Ranked Candidates
    ↓ Threshold Decision (Match / Unknown)
    ↓ JSON Response
```

## Project Structure

```
thuli/
├── app/              FastAPI application
├── data/             Catalogue images + manifest
├── scripts/          Offline processing scripts
├── evaluation/       Stumper dataset + results
├── experiments/      Experiment notes
├── tests/            Pytest test suite
├── logs/             AI coding session logs
├── artifacts/        Embeddings + FAISS index
├── DECISIONS.md      Architecture decisions log
└── requirements.txt
```

## Setup

```bash
# 1. Clone and install dependencies
pip install -r requirements.txt

# 2. Copy config
cp .env.example .env
```

## Phase 1: Build Catalogue

```bash
python scripts/download_dataset.py    # Download from HuggingFace
python scripts/clean_catalogue.py     # Clean + validate
pytest tests/test_catalogue.py -v     # Verify ≥5,000 items
```

> Phases 2–5 will be documented here as they are implemented.

## Results

> To be filled in after evaluation (Phase 6+).

| Metric | Baseline | Improved |
|---|---|---|
| Top-1 accuracy | — | — |
| Top-5 accuracy | — | — |
| Avg latency | — | — |

## Decisions

See [DECISIONS.md](DECISIONS.md) for the full record of technical decisions and rationale.

## AI Development Logs

Session logs are stored in [`logs/`](logs/). Each session records what was built, what AI suggestions were accepted or modified, and why.
