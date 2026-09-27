"""
app/main.py
───────────
FastAPI application entry point for Jewellery Image Retrieval System.
Mounts API routes, static assets, and catalogue image directories.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router, get_matcher
from app.config import PROJECT_ROOT


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm JewelleryMatcher and FAISS index at startup to avoid cold-start race conditions."""
    try:
        get_matcher()
    except Exception as e:
        print(f"[WARN] Failed to pre-warm matcher during startup: {e}")
    yield


app = FastAPI(
    title="Thuli — Jewellery Retrieval Engine",
    description="Vector search & vision matcher for 6,157 jewellery catalogue items (PS2 - Stump the Model).",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local testing and external frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(router, prefix="/api")

# Mount data folder to serve catalogue images directly (e.g. /data/catalogue/jewelry_dataset/...)
data_dir = PROJECT_ROOT / "data"
if data_dir.exists():
    app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")

# Mount evaluation images so the dashboard can display thumbnails
eval_images_dir = PROJECT_ROOT / "evaluation" / "images"
eval_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/evaluation/images", StaticFiles(directory=str(eval_images_dir)), name="eval_images")

# Mount automated stumper images
auto_images_dir = PROJECT_ROOT / "evaluation" / "automated_images"
auto_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/evaluation/automated_images", StaticFiles(directory=str(auto_images_dir)), name="auto_images")

# Mount static folder for frontend HTML/CSS/JS
static_dir = PROJECT_ROOT / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

assets_dir = static_dir / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")



@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon():
    """Serve favicon."""
    fav = static_dir / "favicon.svg"
    if fav.exists():
        return FileResponse(str(fav), media_type="image/svg+xml")
    return {
        "status": "not_found"
    }


@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serve the interactive web test interface."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "Thuli Jewellery Retrieval API is running. Access /docs for Swagger UI.",
        "status": "healthy",
    }
