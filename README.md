# THULI

> Visual jewellery search powered by CLIP, FAISS, and FastAPI.

Thuli matches a jewellery photograph against a catalogue of products, returns
the best candidates, and marks low-confidence searches as `UNKNOWN`. It also
provides catalogue ingestion, multi-item search, stumper-data collection, and
evaluation dashboards for testing model robustness.

![Thuli architecture](arch.png)

## Highlights

- **Visual search:** Upload a jewellery photograph and retrieve Top-K catalogue candidates.
- **Confidence-aware results:** Similarity thresholding returns `MATCH` or `UNKNOWN` rather than forcing a weak match.
- **Multi-item search:** Segment or grid-crop a photo, search each region, then deduplicate the matches.
- **Catalogue management:** Add a product image and metadata; Thuli generates its embedding and updates the search index.
- **Evaluation suite:** Run hand-shot, unseen-holdout, and automated-stumper benchmarks with per-condition metrics.

## Stack

| Layer | Technology |
| --- | --- |
| Web interface | React 19, Vite, CSS |
| API | FastAPI, Uvicorn |
| Image embedding | CLIP ViT-B/32 via Transformers and PyTorch |
| Vector search | FAISS `IndexFlatIP` with L2-normalized 512-dimensional vectors |
| Multi-item proposals | FastSAM-s |
| Data and reports | CSV, JSON, NumPy, FAISS artifacts |

## ⚡ Easy Setup (Run in 1 Minute)

> 🚀 **Looking for the fastest, simplest setup?**
> Click here for the dedicated guide: 👉 [**SETUP.md**](SETUP.md)
>
> Run the entire project and interactive web application on **`http://localhost:3000`** using **Python only** (no Node.js or npm needed):
>
> ```bash
> # 1. Clone & enter repository
> git clone https://github.com/saran2006psg/thuli.git
> cd thuli
>
> # 2. Create virtual environment & install requirements
> python -m venv venv
> .\venv\Scripts\Activate.ps1    # (Linux/macOS: source venv/bin/activate)
> pip install -r requirements.txt
>
> # 3. One-Command Setup & Launch (Port 3000)
> python -m scripts.setup --run
> ```
>
> 👉 Then open your browser to: **[http://localhost:3000](http://localhost:3000)**
>
> 📖 *For complete manual steps, Google Drive dataset links, and troubleshooting, see [**SETUP.md**](SETUP.md).*

---

## Quick start

### 1. Prerequisites

- Python 3.10 or later
- Node.js 18 or later (only needed for frontend development)
- Internet access for the first CLIP model download
- Catalogue images, if they are not already present in `data/catalogue/`

### 2. Install Python dependencies

Run these commands from the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents activation, run this once and activate the environment again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. Prepare the model and search index

If `artifacts/` already contains the FAISS index and product-ID mapping, this
command verifies them and downloads the CLIP model cache when required:

```powershell
python scripts/setup.py
```

For a new catalogue or a checkout without generated artifacts, first place the
catalogue images under `data/catalogue/jewelry_dataset/`, then rebuild:

```powershell
python scripts/setup.py --rebuild
```

The rebuild generates embeddings, the product-ID mapping, and the FAISS index.
It can take several minutes on CPU and only needs to be repeated after the
catalogue changes.

### 4. Run Thuli

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Open [http://localhost:3000](http://localhost:3000). API documentation is at
[http://localhost:3000/docs](http://localhost:3000/docs).

Verify service readiness:

```powershell
Invoke-RestMethod http://localhost:3000/api/health
```

## Frontend development

FastAPI serves the built interface from `app/static/`. To develop the React
interface with hot reload, start the API first, then run:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite development
server proxies API requests to port `3000`.

Build the frontend for FastAPI to serve:

```powershell
cd frontend
npm run build
```

## How search works

1. The API validates the uploaded image and converts it to RGB.
2. CLIP ViT-B/32 produces a 512-dimensional, L2-normalized image embedding.
3. FAISS performs exact inner-product search; with normalized vectors this is cosine similarity.
4. Thuli resolves product metadata for the Top-K candidates.
5. The highest score is compared with the configured threshold (default: `0.75`).
6. The API returns `MATCH` or `UNKNOWN` plus ranked candidates and timing data.

## Project layout

```text
app/                 FastAPI application, retrieval, collection, and evaluation code
frontend/            React/Vite source application
data/                Catalogue metadata and images
artifacts/           Generated embeddings, ID mapping, and FAISS index
evaluation/          Stumper datasets, benchmark results, and analysis
tests/               Unit and integration tests
scripts/             Setup, index-building, ingestion, and evaluation commands
docs/                Architecture, API, pipeline, and evaluation documentation
```

## Useful commands

```powershell
# Run all tests
python -m pytest -q

# Run the real-image evaluation suite
python scripts/evaluate.py

# Run final baseline vs. experiment validation
python scripts/run_final_validation.py

# Start on another port
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Documentation

- [Implementation architecture and user flows](docs/IMPLEMENTATION_ARCHITECTURE_AND_USER_FLOWS.md)
- [Architecture overview](docs/ARCHITECTURE.md)
- [Pipeline and ingestion](docs/PIPELINE.md)
- [API reference](docs/API_REFERENCE.md)
- [Evaluation guide](docs/EVALUATION_GUIDE.md)
- [Setup details](SETUP.md)

## Data and generated files

Do not commit `.env`, `.cache/`, generated `artifacts/`, or large catalogue
images unless your repository policy explicitly requires them. Catalogue image
paths in `data/catalogue.csv` must remain relative to the repository root.

## License

This repository does not currently declare a license.
