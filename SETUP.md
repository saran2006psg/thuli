# Thuli Setup

This is the simple CPU-only setup for a new machine. No Docker is required.

## Requirements

- Python 3.10 or newer
- Internet access for the first CLIP model download
- Enough disk space for the catalogue images, model cache, and generated artifacts

## 1. Get the Code and Catalogue

Clone or download this repository, then download the catalogue archive from [Google Drive](https://drive.google.com/file/d/1P_CvDHlEmH3iyZ5XwaPl2w86jY7yxgct/view?usp=sharing).

Extract the Drive archive into the repository root. The final layout must be:

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

Do not extract it as `data/thuli-data/` or `thuli-data/`.

The `evaluation/` directory comes from Git. Do not replace it with the Drive data.

## 2. Check Catalogue Paths

Open `data/catalogue.csv`. Each `image_path` must be relative to the repository root and use forward slashes:

```text
data/catalogue/jewelry_dataset/ring/ring_00001.jpg
```

Do not use paths from another computer, such as:

```text
D:\PL\thuli\data\catalogue\ring\ring_00001.jpg
C:\Users\someone\Downloads\jewelry\ring_00001.jpg
```

The official catalogue CSV already uses the correct format. Normally, no code or CSV edit is needed after extracting the official archive.

## 3. Create the Python Environment

Open PowerShell in the repository root:

```powershell
cd D:\PL\thuli
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run this once in PowerShell as your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 4. Prepare the Model and Catalogue Index

For a Drive-only catalogue, run:

```powershell
python scripts/setup.py --rebuild
```

This downloads `openai/clip-vit-base-patch32` once, stores it in `.cache/`, generates catalogue embeddings, and builds the FAISS index under `artifacts/`.

The first run may take several minutes because it processes thousands of images on the CPU. Do not repeat it unless the catalogue or `data/catalogue.csv` changes.

## 5. Start the Application

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`.

Check the service from another PowerShell window:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

The response should report `status` as `healthy` and `dimension` as `512`.

Stop the application with `Ctrl+C` in the terminal running Uvicorn.

## Later Runs

Activate the environment and start the application:

```powershell
cd D:\PL\thuli
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The model and FAISS index are reused. Do not run `--rebuild` again unless the catalogue changes.

## What Is Stored Where

| Item                            | Location       | Source                 |
| ------------------------------- | -------------- | ---------------------- |
| Application and evaluation code | Git repository | Git                    |
| Evaluation datasets and reports | `evaluation/`  | Git                    |
| Catalogue CSV and images        | `data/`        | Google Drive           |
| Downloaded model                | `.cache/`      | Created on first setup |
| Embeddings and FAISS index      | `artifacts/`   | Created by setup       |

Do not commit `.env`, `.cache/`, catalogue images, or generated artifacts.

## When the Catalogue Changes

Replace or update `data/`, confirm that `data/catalogue.csv` points to the correct relative image paths, then run:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/setup.py --rebuild
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Common Problems

### `data/catalogue.csv` not found

The Drive archive is in the wrong location. Move it so this file exists:

```text
D:\PL\thuli\data\catalogue.csv
```

### Images are not found

Compare the CSV `image_path` values with the actual files. Use relative paths, forward slashes, and exact filenames.

### Model download fails

Check internet access and rerun `python scripts/setup.py --rebuild`. The model download is cached after a successful run.

### Port 8000 is busy

Use another port:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Then open `http://localhost:8001`.
