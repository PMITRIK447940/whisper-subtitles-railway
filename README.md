# Whisper Subtitles on Railway (v2)

Web app for generating `.srt` subtitles from a user-uploaded video using **openai-whisper**, **ffmpeg**, and **torch**.
Includes translation using **MarianMT** (Helsinki-NLP/opus-mt-*). Designed for Docker deploy on **Railway**.

## Features
- Upload video/audio → chunks (~30s) → Whisper transcription
- Live progress bar (polls `/api/progress/{job_id}`)
- Download original **.srt**
- Translate to chosen language, then download translated **.srt**
- Clean UI (FastAPI + Jinja templates)

## Quick start (local, Docker required)
```bash
docker build -t whisper-subtitles .
docker run -p 8080:8080 -e WHISPER_MODEL=small whisper-subtitles
# open http://localhost:8080
```

## Deploy to Railway
1. Create a new Railway project and choose **Deploy from Dockerfile** (or GitHub).
2. Upload this repo / push it to GitHub.
3. (Optional) Set env vars:
   - `WHISPER_MODEL` (default: `small`) — try `base`, `small`, `medium`, `large-v3`
   - `CHUNK_SECONDS` (default: `30`)
   - `MAX_UPLOAD_MB` (default: `500`)
4. Deploy → Open URL.

### Notes
- Storage is **ephemeral** on typical Railway services. Outputs live in `/tmp/jobs/<job_id>`.
- Image uses **Torch CPU wheels** for reliability on Railway.
- Larger Whisper models require more RAM/CPU (or GPU plan).

## Endpoints
- `GET /` — upload
- `POST /upload` — start job, redirect to status
- `GET /status/{job_id}` — progress UI
- `GET /api/progress/{job_id}` — JSON progress
- `GET /download/{job_id}` — original .srt
- `POST /translate/{job_id}` — create translated .srt
- `GET /download/{job_id}/{lang}` — translated .srt
- `GET /health` — healthcheck
