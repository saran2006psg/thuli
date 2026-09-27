# THULI — Visual Jewellery Retrieval Engine

> **Submission for PS2: Stump the Model**  
> Visual similarity search, multi-item segmentation, and physical robustness evaluation across 6,157 fine jewellery items.

---

## 🎯 How We Assess: The Clean Gate

> *"First, a gate. Does it run from a clean checkout using only your README, and are the logs and write-up there? If not, we stop reading."*

This submission passes the gate in **60 seconds on any machine** (Windows, macOS, Linux) **using Python only**:

```bash
# 1. Clone & enter repository
git clone https://github.com/saran2006psg/thuli.git
cd thuli

# 2. Create virtual environment & install requirements
python -m venv venv
.\venv\Scripts\Activate.ps1    # (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt

# 3. One-Command Setup & Launch (Port 3000)
python -m scripts.setup --run
```

- 🌐 **Interactive Web UI:** Open **[http://localhost:3000](http://localhost:3000)** (Pre-compiled React 18 served directly by FastAPI — **zero Node.js or npm required**).
- 📝 **Engineering Write-Up:** [**`WRITEUP.md`**](WRITEUP.md) — Comprehensive assessment narrative covering design thinking, empirical rejections, named weaknesses, and human-overrule logs.
- 📜 **Session Logs:** [**`logs/`**](logs/) — Full chronological development logs (`session_01.md` through `session_09.md`) documenting how the engineer directed the AI tool.
- 📐 **Architecture Decisions:** [**`DECISIONS.md`**](DECISIONS.md) — Full log of 12 formal architecture decision records (Context → Decision → Reason → Alternatives Rejected).
- ⚡ **Standalone Setup Guide:** [**`SETUP.md`**](SETUP.md) — One-page quickstart with automatic Google Drive dataset streaming.
- 🧪 **Automated Test Suite:** `python -m pytest tests/ -v` (**43/43 tests passing**).

---

## 🧭 Navigating the "Yes Pile"

This submission is deliberately built to satisfy the **"Yes Pile"** evaluation criteria:

| Assessor Rubric Criteria | Where to Find It | Summary of Evidence |
|---|---|---|
| **1. The Clean Gate** | [Section above](#-how-we-assess-the-clean-gate) & [`SETUP.md`](SETUP.md) | 1-command Python run on port 3000, automatic 182 MB dataset download, zero Node dependency. |
| **2. Why It Is Built This Way** | [`WRITEUP.md` § 2](WRITEUP.md#2-why-it-is-built-this-way-architecture--tradeoffs) | Why fine jewellery breaks naive vision models, why CLIP ViT-B/32, why exact SIMD `IndexFlatIP`, why calibrated rejection gating. |
| **3. Something Not Asked For That Matters** | [`WRITEUP.md` § 3](WRITEUP.md#3-what-we-built-that-was-not-asked-for-and-turns-out-to-matter) | **900-test synthetic degradation benchmark** isolating 9 physical variables; **FastSAM multi-item segmentation** with 15% context margins; **zero-Node Python distribution**. |
| **4. The Obvious Approach Tried, Measured & Rejected** | [`WRITEUP.md` § 4](WRITEUP.md#4-the-obvious-approaches-tried-measured-and-rejected) | **Experiment 01:** Saliency/Otsu cropping severed delicate chains (dropped accuracy from 72.1% to 65.7%). HNSW rejected after measuring 0.52 ms latency on FlatIP. Unconstrained Top-1 rejected after 38.2% false acceptance rate. |
| **5. Weaknesses Found and Named Before You Found Them** | [`WRITEUP.md` § 5](WRITEUP.md#5-honest-account-of-what-does-not-work-named-weaknesses) | Fine prong symmetry collapse under linear motion blur (drops to 62.0%); open-palm skin tone dominating ViT attention; lookalike boundary ambiguity in $[0.74, 0.78]$. |
| **6. Candidate Overruled the Tool and Was Right To** | [`WRITEUP.md` § 6](WRITEUP.md#6-where-the-human-overruled-the-ai-tool) & [`logs/`](logs/) | Overruled cloud vector DBs (saved 50 ms latency); overruled HSV skin masking; overruled dual-terminal Node/Python setup; overruled hardcoded paths. |

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
