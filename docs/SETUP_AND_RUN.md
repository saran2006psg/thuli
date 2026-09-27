# Setup & Run Guide from Scratch

This guide walks you through setting up and running the **Thuli Jewellery Retrieval Engine** from scratch on Windows, macOS, or Linux.

---

## 1. System Requirements

- **Python:** 3.10, 3.11, or 3.12
- **Node.js:** v18.0.0 or later (with npm)
- **RAM:** Minimum 8 GB recommended (for loading CLIP model and in-memory index)
- **Disk:** ~2 GB free disk space (dataset + virtual environment)

---

## 2. Step 1: Clone & Setup Python Virtual Environment

```bash
# Clone the repository
git clone https://github.com/saran2006psg/thuli.git
cd thuli

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

---

## 3. Step 2: Verify Setup & Weights

Run the automated verification script:

```bash
python -m scripts.setup
```

This confirms:

- PyTorch and Torchvision are installed.
- `sentence-transformers` / CLIP model can be downloaded/loaded.
- `FastSAM-s.pt` model weights exist in project root.
- FAISS library is operational.

---

## 4. Step 3: Build Catalogue & Vector Indices (Offline Step)

If you are running the project on a new machine without pre-built artifacts:

```bash
# 1. Build the catalogue metadata CSV (6,157 items)
python -m scripts.build_catalogue_csv

# 2. Generate CLIP ViT-B/32 embeddings
python -m scripts.generate_embeddings

# 3. Build and serialize the FAISS IndexFlatIP index
python -m scripts.build_index
```

Generated artifacts will appear in `artifacts/embeddings/` and `artifacts/indexes/`.

---

## 5. Step 4: Run the Backend Server

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API is live at: `http://localhost:8000`
- Swagger API Docs: `http://localhost:8000/docs`

---

## 6. Step 5: Setup & Run Frontend

Open a new terminal window:

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

- Open your browser to: `http://localhost:5173`

---

## 7. Step 6: Running Tests

To verify that all modules are working correctly:

```bash
# Run the entire test suite
pytest tests/ -v

# Run visual matcher unit tests specifically
pytest tests/test_matcher.py -v

# Run FastSAM multi-matcher tests
pytest tests/test_multi_matcher.py -v
```

---

## 8. Troubleshooting & FAQ

### Issue: "Missing script: ev"

**Solution:** Run `npm run dev` in the `frontend` folder instead of `npm run ev`.

### Issue: "FAISS DLL load failed" on Windows

**Solution:** Ensure you installed `faiss-cpu` (not `faiss-gpu` unless you have CUDA setup):

```bash
pip install faiss-cpu
```

### Issue: Stale image displayed after replacing a file in `evaluation/images/`

**Solution:**

1. Hard refresh your browser with **`Ctrl + Shift + R`** (or **`Ctrl + F5`**).
2. Click **"Run Evaluation"** in the Evaluation Arena tab so the model scores the new image.
