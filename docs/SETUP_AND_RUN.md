# Setup & Run Guide from Scratch

This guide walks you through setting up and running the **Thuli Jewellery Retrieval Engine** from scratch on Windows, macOS, or Linux using **Python only**.

---

## 1. System Requirements

- **Python:** 3.10, 3.11, or 3.12
- **RAM:** Minimum 8 GB recommended (for loading CLIP model and FAISS in-memory index)
- **Disk:** ~2 GB free disk space (dataset + virtual environment)
- **Node.js/npm:** **NOT required** for running the application. The production React web UI is already compiled into `app/static/` and served directly by Python.

---

## 2. Step 1: Clone & Setup Python Virtual Environment

```bash
# Clone the repository
git clone https://github.com/saran2006psg/thuli.git
cd thuli

# Create a virtual environment
python -m venv venv

# Activate the virtual environment:
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Upgrade pip and install Python dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Step 2: Automated Setup, Dataset Download & Verification

Run the all-in-one setup tool:
```bash
python -m scripts.setup
```

This automated script performs:
1. **CSV Path Portability:** Normalizes all paths across `catalogue.csv`, `stumper.csv`, `automated_stumper.csv`, and `multi_item_eval.csv` to cross-platform relative paths.
2. **Dataset Check & Download:** Checks if the 6,157 jewellery catalogue images exist in `data/catalogue/jewelry_dataset/`. If missing, it can automatically stream and extract the 182 MB archive from [Google Drive (File ID: `1P_CvDHlEmH3iyZ5XwaPl2w86jY7yxgct`)](https://drive.google.com/file/d/1P_CvDHlEmH3iyZ5XwaPl2w86jY7yxgct/view?usp=sharing).
3. **Vision Transformer Pre-warming:** Pre-caches the CLIP ViT-B/32 model into `.cache/`.
4. **FastSAM Segmentation Weights:** Verifies `FastSAM-s.pt` (22.7 MB) is available in the project root.
5. **FAISS Vector Index Verification:** Automatically generates embeddings and builds the `catalogue.faiss` index if missing or if `--rebuild` is passed.

---

## 4. Step 3: Run the Application (Python Only)

You can launch the complete retrieval engine and web UI with a single command:

```bash
python -m scripts.setup --run
```

Or using Uvicorn directly:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Open your browser and navigate to:
**`http://localhost:3000`**

You will see the complete interactive web application:
- **Visual Search Tab:** Single-item drag-and-drop search with similarity scoring.
- **Multi-Item Search:** Automatic FastSAM segmentation detecting and matching multiple jewellery pieces in one photo.
- **Evaluation Arena:** Live benchmark evaluation, Top-1/Top-5 accuracy cards, and filterable results table.
- **Automated Stumper Benchmark:** 900 synthetic tests under 9 physical conditions.

---

## 5. Step 4: Running Test Suites

Verify system correctness with `pytest`:

```bash
# Run core matcher tests (13 tests)
python -m pytest tests/test_matcher.py -v

# Run evaluation suite (11 tests)
python -m pytest tests/test_evaluation.py -v

# Run API and catalogue tests (19 tests)
python -m pytest tests/test_api.py tests/test_catalogue.py -v

# Run all test suites
python -m pytest tests/ -v
```

---

## 6. Manual Dataset Download (Fallback)

If your environment restricts automated Google Drive streaming:
1. Download the archive manually from [Google Drive](https://drive.google.com/file/d/1P_CvDHlEmH3iyZ5XwaPl2w86jY7yxgct/view?usp=sharing).
2. Extract the archive into the `data/` folder so the layout is:
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
3. Run `python -m scripts.setup` to verify.

---

## 7. Troubleshooting & FAQ

### Issue: "Missing script: ev"
**Solution:** If using the frontend dev server, run `npm run dev` instead of `npm run ev`. Or simply run `python -m scripts.setup --run` to skip Node.js entirely.

### Issue: "FAISS DLL load failed" on Windows
**Solution:** Ensure you installed CPU FAISS:
```bash
pip install faiss-cpu
```

### Issue: Stale image displayed in Evaluation Arena
**Solution:**
1. Hard refresh your browser with **`Ctrl + Shift + R`** (or **`Ctrl + F5`**).
2. Click **"Run Evaluation"** in the web UI to re-score the dataset.
