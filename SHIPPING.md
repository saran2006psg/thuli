# Thuli Shipping Guide

Thuli is shipped as a normal Python application. Docker is not required.

## What Goes to Git

Keep these in the Git repository:

```text
app/
scripts/
tests/
evaluation/
experiments/
phases/
README.md
requirements.txt
SETUP.md
```

The entire `evaluation/` directory stays in Git. It contains evaluation datasets, reports, metrics, and evaluation images.

## What Goes to Google Drive

Upload one archive named `thuli-data.zip` to Google Drive containing the catalogue data:

```text
thuli-data/
  catalogue.csv
  catalogue/
    jewelry_dataset/
      bracelet/
      earring/
      necklace/
      ring/
```

The download link is in [SETUP.md](SETUP.md).

Users download this archive and extract its contents into the repository as:

```text
thuli/
  data/
    catalogue.csv
    catalogue/
      jewelry_dataset/
        bracelet/
        earring/
        necklace/
        ring/
```

Do not upload `.venv/`, `.cache/`, `artifacts/`, `.env`, or source code to Drive.

## Data Path Rule

The `image_path` column in `data/catalogue.csv` must use repository-relative paths:

```text
data/catalogue/jewelry_dataset/ring/ring_00001.jpg
```

Never use an absolute path from the original computer:

```text
D:\PL\thuli\data\catalogue\ring\ring_00001.jpg
```

The current application configuration already resolves `data/catalogue.csv`, `data/catalogue`, and `artifacts/` from the repository root. No source-code path changes are required for a new user.

## User Setup

Users should follow [SETUP.md](SETUP.md):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/setup.py --rebuild
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The first setup downloads the CLIP model into `.cache/`, creates catalogue embeddings, and builds the FAISS index. Later runs reuse those files and only need Uvicorn.

## Release Checklist

- [ ] Push application code, scripts, tests, documentation, and `evaluation/` to Git.
- [ ] Upload the `data/` archive to Google Drive.
- [ ] Confirm the archive extracts to `data/catalogue.csv` and `data/catalogue/...`.
- [ ] Confirm all CSV image paths are relative and use `/` separators.
- [ ] Confirm no CSV path contains a developer computer path.
- [ ] Test `python scripts/setup.py --rebuild` on a clean machine.
- [ ] Test `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- [ ] Test `GET /api/health` and one image match.
- [ ] Do not commit `.env`, `.cache/`, catalogue images, or generated artifacts.
