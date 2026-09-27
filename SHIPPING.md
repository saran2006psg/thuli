# Thuli Shipping and Setup Guide

This document is the handoff guide for running Thuli on another computer.

## What Goes Where

### Tracked in Git

The repository contains the application, tests, scripts, documentation, and evaluation material:

```text
app/
scripts/
tests/
evaluation/
experiments/
phases/
README.md
requirements.txt
```

The `evaluation/` directory is intentionally part of Git. It contains the evaluation CSV files, reports, metrics, and evaluation images used to reproduce the benchmark results.

### Downloaded separately

The catalogue dataset is large and should be distributed through Drive, object storage, or another file-sharing service instead of Git. Share one archive containing this structure:

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

After downloading, extract it into the repository as `data/`:

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

Do not put the downloaded dataset inside `.venv/`, `.cache/`, `artifacts/`, or `evaluation/`.

### Generated locally

The model cache and vector artifacts are machine-local:

```text
.cache/                         downloaded CLIP model
artifacts/embeddings/           generated catalogue vectors
artifacts/indexes/              generated FAISS index
```

These files do not need to be committed to Git. They can be regenerated from the downloaded catalogue dataset.

## First-Time Docker Setup

Requirements:

- Docker Desktop on Windows or Docker Engine on Linux
- Docker Compose v2 (`docker compose` command)
- Internet access for the first CLIP model download
- Enough disk space for the catalogue images, model cache, and generated artifacts

Docker is the recommended shipping and runtime method. It is CPU-only and works on standard AMD or Intel `amd64/x86_64` machines. No CUDA, NVIDIA driver, or GPU configuration is required.

From the repository root, after extracting the Drive dataset as `data/`:

### Windows PowerShell

```powershell
docker compose build
docker compose run --rm setup
docker compose up -d app
docker compose logs -f app
```

### Linux or macOS

```bash
docker compose build
docker compose run --rm setup
docker compose up -d app
docker compose logs -f app
```

Open `http://localhost:8000` after the server starts.

The first setup downloads `openai/clip-vit-base-patch32` and generates the catalogue artifacts. The model is stored in the persistent Docker volume `thuli-model-cache`; it is not downloaded on every query or normal restart.

To stop the service:

```powershell
docker compose down
```

The named model volume and the host `data/` and `artifacts/` folders are preserved.

## What Must Change From the Current Codebase

No application source path needs to be changed for Docker. The current [app/config.py](app/config.py) already resolves paths from the project root and supports environment overrides. Compose mounts the repository folders at the same paths inside the container:

| Local folder                      | Container folder | Purpose                                    |
| --------------------------------- | ---------------- | ------------------------------------------ |
| `./data`                          | `/app/data`      | Drive-downloaded catalogue data, read-only |
| `./artifacts`                     | `/app/artifacts` | Generated embeddings and FAISS index       |
| Docker volume `thuli-model-cache` | `/app/.cache`    | Downloaded CLIP model                      |

Do not change `CATALOGUE_CSV` to a Windows path or a Docker path. Keep it as `data/catalogue.csv`. Do not put a path such as `D:\\PL\\thuli\\...` in the CSV. The only required data-side change is to make every `image_path` portable and relative to the repository root.

Do not copy the Drive dataset into the Docker image. Do not commit the catalogue images, `.cache/`, or generated artifacts to Git. They are supplied through the mounts above.

The new Docker files are:

- `Dockerfile`: CPU-only Python image with CPU PyTorch, FAISS, FastAPI, and the application.
- `docker-compose.yml`: setup and app services with data, artifact, and model-cache persistence.
- `.dockerignore`: keeps the external dataset and generated files out of the image build context.

The evaluation code remains in Git and is copied into the image. The normal app service does not require evaluation data to answer matches.

## Preparing Data and Artifacts

There are two supported cases.

### Case 1: Prepared artifacts are supplied

If the release also includes `artifacts/embeddings/` and `artifacts/indexes/`, run:

```powershell
docker compose build
docker compose run --rm setup --skip-model
```

This checks the catalogue CSV, FAISS index, and product ID mapping, then downloads/checks the model.

### Case 2: Only the data archive is supplied

If the release does not include generated artifacts, place the downloaded `data/` folder at the repository root and run:

```powershell
docker compose run --rm setup
```

This performs the following pipeline:

1. Reads `data/catalogue.csv`.
2. Resolves each catalogue image.
3. Loads the CLIP model from the Docker cache or downloads it once.
4. Generates normalized catalogue embeddings.
5. Writes `artifacts/embeddings/catalogue_embeddings.npy`.
6. Writes `artifacts/embeddings/product_ids.json`.
7. Builds and validates the FAISS index.
8. Writes `artifacts/indexes/catalogue.faiss`.

Embedding thousands of images is a preparation task and may take several minutes or longer on a CPU. It is only required when the catalogue changes. Normal application startup loads the existing model and index; it does not regenerate them.

## Portable CSV Paths

The catalogue CSV must not contain a path from the original owner’s computer, such as:

```text
D:\PL\thuli\data\catalogue\jewelry_dataset\ring\ring_001.jpg
```

Use repository-relative paths instead, for example:

```text
data/catalogue/jewelry_dataset/ring/ring_001.jpg
```

Relative paths are resolved from the repository root, so the same CSV works on Windows, Linux, macOS, and inside a container. The folder names and filenames in the downloaded archive must match the paths in `data/catalogue.csv`.

If the data provider has a different local directory layout, the provider must either:

- rebuild `catalogue.csv` with paths relative to the repository root, or
- place the images in the layout expected by the existing CSV.

Do not edit application source code for a user-specific absolute path.

## Changing the Catalogue

When adding or replacing catalogue images:

1. Put the new images under `data/catalogue/`.
2. Update `data/catalogue.csv` with portable relative paths.
3. Remove the old generated artifacts if they no longer describe the catalogue.
4. Run `docker compose run --rm setup`.
5. Restart the application with `docker compose up -d app` and check `/api/health`.

The product ID order in `product_ids.json` must remain aligned with the rows in the FAISS index. Always rebuild through the provided script instead of manually editing generated files.

## Evaluation Workflow

Evaluation data is shipped through Git and is separate from the catalogue data.

The normal application does not need the evaluation datasets. To run evaluation, keep the repository’s `evaluation/` directory in place and ensure the catalogue data and generated artifacts are prepared first. Evaluation scripts can then be run from the repository root, for example:

```powershell
python scripts/evaluate.py
python scripts/run_final_validation.py
```

Evaluation outputs such as metrics and result CSVs may change after a run. Review those changes before committing them.

## Model Cache Location

With Docker, the model cache is stored in the named volume:

```text
thuli-model-cache
```

To inspect or remove it:

```powershell
docker volume inspect thuli_thuli-model-cache
docker volume rm thuli_thuli-model-cache
```

The cache contains downloaded model and tokenizer files. It does not contain catalogue images, evaluation results, or search results. Removing it is safe, but the next setup will download the model again.

## CPU-Only Operation

Thuli uses `faiss-cpu` and the Dockerfile installs CPU-only PyTorch. No GPU, CUDA toolkit, NVIDIA driver, or GPU Docker configuration is required.

AMD and Intel CPUs are supported on standard `amd64/x86_64` systems. Performance depends on the CPU and catalogue size; the expensive step is initial embedding generation, not normal FAISS search.

## Quick Health Check

After starting the server:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

A healthy response should report:

- `status`: `healthy`
- `index_size`: the number of catalogue vectors
- `dimension`: `512`
- the configured CLIP model name

If the response is `degraded`, check that `data/catalogue.csv`, the model cache, `artifacts/indexes/catalogue.faiss`, and `artifacts/embeddings/product_ids.json` exist.

## Common Problems

### Missing catalogue CSV

Download the data archive and extract it as the root-level `data/` directory. Do not extract it as `data/thuli-data/`.

### Missing FAISS index or product IDs

Run:

```powershell
docker compose run --rm setup
```

The catalogue images must be present before rebuilding.

### Model download fails

Check internet access and rerun `docker compose run --rm setup`. To retry from an empty model cache, remove the named volume first.

### Images listed in the CSV are not found

Check that the CSV uses repository-relative paths and that filenames match the downloaded archive exactly. Windows and Linux path separators should be written with `/` in the CSV.

### Port 8000 is already in use

Start on another port by changing the host side of the Compose port mapping from `8000:8000` to `8001:8000`, then run:

```powershell
docker compose up -d app
```

Then open `http://localhost:8001`.

## Release Checklist

Before sharing a release:

- [ ] Push application code, scripts, tests, documentation, and `evaluation/` to Git.
- [ ] Upload the large `data/` archive separately.
- [ ] Confirm `data/catalogue.csv` contains no absolute local paths.
- [ ] Confirm the archive extracts to `data/catalogue.csv` and `data/catalogue/...`.
- [ ] Test `docker compose run --rm setup` on a clean machine if generated artifacts are not shipped.
- [ ] Test `docker compose up -d app`.
- [ ] Test `GET /api/health` and one image match.
- [ ] Do not commit `.env`, `.cache/`, catalogue images, or generated artifacts unless the release policy explicitly requires them.
