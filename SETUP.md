# Thuli Setup

This is the shortest way to run Thuli on a new CPU-only machine.

## 1. Install Docker

Install Docker Desktop on Windows or Docker Engine with Docker Compose v2 on Linux. Start Docker and confirm that this command works:

```powershell
docker version
docker compose version
```

No Python installation is required on the host. Python and all project dependencies run inside Docker.

## 2. Download the Catalogue Data

Download the [`thuli-data.zip` catalogue archive from Google Drive](https://drive.google.com/file/d/1P_CvDHlEmH3iyZ5XwaPl2w86jY7yxgct/view?usp=sharing). Extract it into the repository root so the final layout is exactly:

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

Do not extract it as `data/thuli-data/`, `thuli-data/`, or another nested folder.

The `evaluation/` folder is already supplied by Git. Do not replace it with the Drive data.

## 3. Check the CSV Paths

Open `data/catalogue.csv`. The `image_path` column must contain paths relative to the repository root:

```csv
image_path
data/catalogue/jewelry_dataset/ring/ring_00001.jpg
```

Remove or replace paths from the original computer, such as:

```text
D:\PL\thuli\data\catalogue\ring\ring_00001.jpg
C:\Users\someone\Downloads\jewelry\ring_00001.jpg
```

The CSV must use forward slashes and must match the extracted filenames exactly. The existing project CSV already uses the expected `data/catalogue/...` format, so normally no code or CSV change is needed after extracting the official archive.

Do not change these application settings for a normal setup:

```dotenv
CATALOGUE_CSV=data/catalogue.csv
CATALOGUE_IMG_DIR=data/catalogue
EMBEDDINGS_PATH=artifacts/embeddings/catalogue_embeddings.npy
PRODUCT_IDS_PATH=artifacts/embeddings/product_ids.json
FAISS_INDEX_PATH=artifacts/indexes/catalogue.faiss
```

Docker mounts them inside the container as `/app/data` and `/app/artifacts`. The application resolves the relative settings from `/app` automatically.

## 4. Build the CPU Image

Run these commands from the repository root:

```powershell
docker compose build
```

The image contains CPU-only PyTorch, Transformers, FAISS, FastAPI, and the Thuli application. It does not contain the large catalogue dataset.

## 5. Prepare the Model and Index

Run:

```powershell
docker compose run --rm setup --rebuild
```

This one-time preparation step:

1. Downloads the CLIP model into the persistent `thuli-model-cache` Docker volume.
2. Reads `data/catalogue.csv`.
3. Checks the catalogue images.
4. Generates catalogue embeddings.
5. Builds the FAISS index.
6. Saves generated files under the host `artifacts/` folder.

The first run may take several minutes because thousands of images are embedded on the CPU. Do not repeat this step unless the catalogue changes or the artifacts are deleted.

## 6. Start Thuli

```powershell
docker compose up -d app
```

Open:

```text
http://localhost:8000
```

Check that the service is ready:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

The response should contain `"status": "healthy"`, an index size, and dimension `512`.

View logs:

```powershell
docker compose logs -f app
```

Stop the application:

```powershell
docker compose down
```

Stopping the containers does not delete the downloaded model, catalogue data, or generated artifacts.

## What Users Need to Download

Users need only:

1. The Git repository.
2. The `thuli-data.zip` archive from Drive.
3. Docker Desktop or Docker Engine.
4. Internet access for the first model download.

Users do not need to install Python, PyTorch, FAISS, Node.js, or frontend dependencies on the host.

## What Is Stored Where

| Item                            | Location                               | Shared or generated         |
| ------------------------------- | -------------------------------------- | --------------------------- |
| Application and evaluation code | Git repository                         | Shared in Git               |
| Evaluation datasets and reports | `evaluation/` in Git                   | Shared in Git               |
| Catalogue CSV and images        | `data/` from Drive                     | Shared separately           |
| Embeddings and FAISS index      | `artifacts/`                           | Generated locally           |
| CLIP model and tokenizer        | Docker volume `thuli-model-cache`      | Downloaded once per machine |
| User uploads and runtime files  | Repository-mounted application folders | Local runtime data          |

The catalogue images are not copied into the Docker image. The application reads them from the mounted `data/` folder.

## When the Catalogue Changes

Replace or update the external `data/` folder, then run:

```powershell
docker compose run --rm setup --rebuild
docker compose restart app
```

The setup service regenerates the embeddings and FAISS index so they stay aligned with the CSV.

## If a User Has a Different Image Folder

The user has two choices:

1. Copy their images into the official `data/catalogue/` folder structure and keep the official CSV.
2. Create a new `data/catalogue.csv` whose `image_path` values point to files under `data/` using relative paths.

Example:

```text
User's files:
  data/catalogue/my_collection/ring/ring_a.jpg

CSV image_path:
  data/catalogue/my_collection/ring/ring_a.jpg
```

Do not edit Python code or use the user's absolute Windows path. After changing the CSV or images, run the preparation command again.

## Troubleshooting

### Docker daemon is not running

Start Docker Desktop, wait until it reports that Docker is running, then retry the Docker command.

### `data/catalogue.csv` not found

The Drive archive was extracted at the wrong level. Move the archive contents so `data/catalogue.csv` exists directly under the repository root.

### Images are missing

Compare the CSV `image_path` values with the actual files. Use forward slashes and preserve filenames exactly.

### The model downloads again

The model cache volume was removed or Docker is using a different Compose project name. Normally, keep the volume named `thuli-model-cache`.

### Port 8000 is busy

Edit `docker-compose.yml` from:

```yaml
ports:
  - "8000:8000"
```

to:

```yaml
ports:
  - "8001:8000"
```

Then run `docker compose up -d app` and open `http://localhost:8001`.
