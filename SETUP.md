# ⚡ Setup Guide — Thuli Jewellery Retrieval Engine

Welcome to the setup guide for Thuli. You can get up and running on **any device** (Windows, macOS, Linux) in **less than 2 minutes using Python only**.

---

## 📋 Prerequisites

- **Python 3.10, 3.11, or 3.12** installed ([python.org](https://www.python.org/downloads/))
- **Git** installed ([git-scm.com](https://git-scm.com/))
- **Node.js / npm is NOT required!** The production React web UI is already pre-compiled into `app/static/` and served directly by Python.

---

## 🚀 3-Step Quick Start

### Step 1: Clone the Repository & Enter Folder
Open your terminal (PowerShell on Windows, or Bash/Zsh on Linux/Mac):
```bash
git clone https://github.com/saran2006psg/thuli.git
cd thuli
```

### Step 2: Create Virtual Environment & Install Requirements

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
*(If PowerShell blocks script execution, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again)*

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Run the All-in-One Setup & Server

```bash
python -m scripts.setup --run
```

**That's it! 🎉** 
This single command automatically:
1. Normalizes all CSV paths to cross-platform relative paths.
2. Checks for the 6,157 item catalogue dataset. If missing, it streams and extracts the archive directly from Google Drive.
3. Pre-caches the CLIP vision transformer model.
4. Verifies FastSAM segmentation weights (`FastSAM-s.pt`).
5. Generates embeddings and builds the FAISS vector index if needed.
6. Starts the server immediately on **port 3000**.

---

## 🌐 Open in Your Browser

Once your terminal shows:
```text
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
```

Open your browser and navigate to:
👉 **[http://localhost:3000](http://localhost:3000)**

You will see the complete interactive web interface:
- **Visual Search Tab:** Test jewellery images with similarity percentages and confidence gates.
- **Multi-Item Search:** Automatically detect and segment multiple pieces in a single image using FastSAM.
- **Evaluation Arena:** Run live accuracy benchmarks against real-world mobile captures.
- **Automated Stumper Benchmark:** Explore 900 synthetic stress tests under 9 physical conditions.

---

## 📦 Google Drive Dataset (Manual Download Fallback)

If your network blocks automated Google Drive downloads:
1. Download the catalogue archive manually from:
   👉 **[Google Drive Dataset Link (182 MB)](https://drive.google.com/file/d/1P_CvDHlEmH3iyZ5XwaPl2w86jY7yxgct/view?usp=sharing)**
2. Extract the archive into the `data/` folder so your folder layout is:
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
3. Run `python -m scripts.setup --run` again.

---

## 🛠️ Alternative Start Command

If you want to start the Uvicorn server directly:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000
```

---

## 🧪 Testing System Health

You can check API health anytime from another terminal:
```bash
# On Windows PowerShell:
Invoke-RestMethod http://localhost:3000/api/health

# On Linux / macOS:
curl http://localhost:3000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "index_size": 6196,
  "dimension": 512,
  "model": "openai/clip-vit-base-patch32",
  "default_threshold": 0.75,
  "default_top_k": 5
}
```

---

## ❓ Frequently Asked Questions

**Q: Do I need to install Node.js or run npm?**  
A: No! The web UI is pre-compiled into `app/static/`. Python serves the UI directly on port 3000.

**Q: How do I stop the server?**  
A: Press `Ctrl + C` in the terminal running the server.

**Q: How do I change the port?**  
A: Pass `--port <number>`:
```bash
python -m scripts.setup --run --port 8080
```
