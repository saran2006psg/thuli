FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USE_TF=0 \
    USE_TORCH=1 \
    TF_ENABLE_ONEDNN_OPTS=0 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    MODEL_CACHE_DIR=/app/.cache

WORKDIR /app

# Install CPU-only PyTorch first; no CUDA or GPU runtime is included.
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        torch torchvision

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY evaluation ./evaluation
COPY experiments ./experiments
COPY phases ./phases
COPY tests ./tests
COPY README.md SHIPPING.md SETUP.md .env.example ./

RUN mkdir -p /app/data /app/artifacts /app/.cache

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
