# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# OS deps: ffmpeg (includes ffprobe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Torch CPU wheels explicitly for reliability on Railway
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY app ./app
COPY railway.json ./railway.json

# Default model can be overridden via env
ENV WHISPER_MODEL=small
ENV PORT=8080

EXPOSE 8080
CMD ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
