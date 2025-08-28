# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg (obsahuje aj ffprobe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# (A) Urob pip toolchain aktuálny – menej build problémov
RUN python -m pip install --upgrade pip setuptools wheel

# (B) Torch CPU wheels z oficiálneho indexu (spoľahlivejšie)
RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu \
    torch torchvision torchaudio

# (C) Zvyšné Python závislosti z PyPI
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# App
COPY app ./app
COPY railway.json ./railway.json

ENV WHISPER_MODEL=small
ENV PORT=8080
EXPOSE 8080

CMD ["bash", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
