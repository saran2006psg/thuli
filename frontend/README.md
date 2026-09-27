# Frontend Web Application (`frontend/`)

This directory contains the single-page web application (SPA) for the **Thuli Jewellery Retrieval Engine**, built with **React 18** and **Vite**.

---

## Directory Structure

```
frontend/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── AutomatedStumperTab.jsx  # Automated Stumper benchmark dashboard (900 tests)
│   │   ├── CollectDataTab.jsx       # Physical stumper data collection & upload UI
│   │   ├── CollectionsTab.jsx       # Catalogue browser and collection explorer
│   │   └── DatasetTab.jsx           # Dataset distribution & coverage analytics
│   ├── App.jsx                      # Main application, Visual Search & Evaluation Arena
│   ├── index.css                    # Design system, CSS tokens, glassmorphism, dark/light themes
│   └── main.jsx                     # React entrypoint
├── index.html                       # HTML template
├── package.json                     # NPM dependencies and scripts
└── vite.config.js                   # Vite configuration & backend proxy mappings
```

---

## Key Features & Tabs

### 1. Visual Search Tab (`App.jsx`)
- **Single-Item Retrieval:** Drag-and-drop or upload a jewellery photo; retrieves top-$K$ candidates with real-time cosine similarity scores and confidence verdicts (`MATCH` vs. `UNKNOWN`).
- **Multi-Item Search:** Uses FastSAM (`/api/match/multi`) to segment multiple jewellery pieces in a single image, displaying crops and matched catalogue items side-by-side.
- **Catalogue Sample Picker:** Quick one-click testing using curated catalogue samples.
- **Interactive Threshold & Top-K Sliders:** Dynamically adjust the confidence threshold (`0.50`–`0.95`) and candidate count.

### 2. Evaluation Arena Tab (`App.jsx`)
- **Real-Time Benchmark Dashboard:** Runs live evaluations on 115 test images from `evaluation/images/`.
- **KPI Metrics Cards:** Top-1 Accuracy, Top-5 Accuracy, False Acceptance Rate (FAR), False Rejection Rate (FRR), and P50/P95 latency.
- **Interactive Results Table:** Filter by All, Correct Matches, False Acceptances, or False Rejections; search by image ID or category; view thumbnail previews with cache-busting.
- **Export:** One-click download of `results.csv`.

### 3. Automated Stumper Benchmark Tab (`AutomatedStumperTab.jsx`)
- Visualizes the 900 automated test suite (100 items &times; 9 conditions).
- Delta comparisons between real handheld captures and synthetic physical stress-tests.
- Filter failures by condition (`motion_blur`, `occlusion`, `bad_lighting`, etc.) with inspection modals.

### 4. Collect Data Tab (`CollectDataTab.jsx`)
- Interface for capturing and uploading real handheld stumper test photos across 10 physical conditions per catalogue product.

### 5. Dataset Analytics Tab (`DatasetTab.jsx`)
- Visualizes catalogue distribution across rings, necklaces, bracelets, and earrings (6,157 items).

---

## Proxy Configuration (`vite.config.js`)

In development, Vite proxies API requests to the FastAPI backend running on port 8000:
- `/api` &rarr; `http://localhost:8000`
- `/data` &rarr; `http://localhost:8000`
- `/evaluation` &rarr; `http://localhost:8000`
- `/static` &rarr; `http://localhost:8000`

---

## Development Setup

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Run local development server
npm run dev
```

Application will run at: `http://localhost:5173`

---

## Production Build

```bash
npm run build
```
Build output is saved to `app/static/` and served directly by FastAPI at `http://localhost:8000/`.
