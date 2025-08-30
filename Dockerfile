# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN python -m pip install --upgrade pip setuptools wheel
RUN python -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
COPY requirements.txt .
RUN python -m pip install -r requirements.txt
COPY app ./app
COPY railway.json ./railway.json
ENV WHISPER_MODEL=small MAX_UPLOAD_MB=2048 DEFAULT_LANG=auto PORT=8080
EXPOSE 8080
CMD ["bash","-lc","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
