"""
app/main.py
───────────
FastAPI application entry point for Jewellery Image Retrieval System.
Mounts API routes, static assets, and catalogue image directories.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import PROJECT_ROOT

app = FastAPI(
    title="Thuli — Jewellery Retrieval Engine",
    description="Vector search & vision matcher for 6,157 jewellery catalogue items (PS2 - Stump the Model).",
    version="1.0.0",
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

# Mount static folder for frontend HTML/CSS/JS
static_dir = PROJECT_ROOT / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


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
