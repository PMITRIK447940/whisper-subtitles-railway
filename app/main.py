import os
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .workers import process_job, JOBS
from .translation import translate_srt, AVAILABLE_LANGUAGES

app = FastAPI(title="Whisper Subtitles v3")

BASE_DIR = Path(os.getenv("DATA_DIR", "/tmp")) / "jobs"
BASE_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

def _lang_choices():
    return AVAILABLE_LANGUAGES

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "2048"))
    chunk_seconds = int(os.getenv("CHUNK_SECONDS", "30"))
    default_lang = os.getenv("DEFAULT_LANG", "auto")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "max_upload_mb": max_upload_mb,
            "chunk_seconds": chunk_seconds,
            "language_choices": _lang_choices(),
            "default_lang": default_lang,
        },
    )

@app.post("/upload")
async def upload(request: Request, background_tasks: BackgroundTasks,
                 file: UploadFile = File(...),
                 forced_lang: str = Form("auto")):
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "2048"))
    job_id = str(uuid.uuid4())
    job_dir = BASE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    dest_path = job_dir / file.filename

    # stream save with size guard
    size = 0
    with dest_path.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_mb * 1024 * 1024:
                f.close()
                dest_path.unlink(missing_ok=True)
                shutil.rmtree(job_dir, ignore_errors=True)
                return JSONResponse({"error": f"Súbor je väčší ako {max_mb} MB."}, status_code=413)
            f.write(chunk)

    JOBS[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Pripravujem spracovanie…",
        "srt_path": None,
        "source_lang": None,
        "video_path": str(dest_path),
        "forced_lang": forced_lang,
        "error": None,
    }

    background_tasks.add_task(process_job, job_id, str(dest_path), forced_lang=forced_lang)
    return RedirectResponse(url=f"/status/{job_id}", status_code=303)

@app.get("/status/{job_id}", response_class=HTMLResponse)
async def status_view(request: Request, job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return HTMLResponse("Job not found", status_code=404)
    return templates.TemplateResponse(
        "status.html",
        {
            "request": request,
            "job_id": job_id,
            "job": job,
            "languages": [(c,n) for c,n in AVAILABLE_LANGUAGES if c != "auto"],
        },
    )

@app.get("/api/progress/{job_id}")
async def api_progress(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
        "ready": job["srt_path"] is not None and job["error"] is None,
        "error": job["error"],
    }

@app.get("/download/{job_id}")
async def download_original(job_id: str):
    job = JOBS.get(job_id)
    if not job or not job["srt_path"]:
        return JSONResponse({"error": "not ready"}, status_code=404)
    return FileResponse(job["srt_path"], filename=f"{job_id}.srt", media_type="application/x-subrip")

@app.post("/translate/{job_id}", response_class=HTMLResponse)
async def translate_view(request: Request, job_id: str, target_lang: str = Form(...)):
    job = JOBS.get(job_id)
    if not job or not job["srt_path"]:
        return HTMLResponse("Súbor ešte nie je pripravený.", status_code=400)
    src_lang = job["source_lang"] or job.get("forced_lang") or "auto"
    out_path = Path(job["srt_path"]).with_suffix(f".{target_lang}.srt")
    try:
        translate_srt(job["srt_path"], str(out_path), source_lang=src_lang, target_lang=target_lang)
    except Exception as e:
        return HTMLResponse(f"Preklad zlyhal: {e}", status_code=500)

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "job_id": job_id,
            "original_ready": True,
            "translated_ready": True,
            "translated_path": f"/download/{job_id}/{target_lang}",
            "target_lang": target_lang,
        },
    )

@app.get("/download/{job_id}/{lang}")
async def download_translated(job_id: str, lang: str):
    job = JOBS.get(job_id)
    if not job or not job["srt_path"]:
        return JSONResponse({"error": "not ready"}, status_code=404)
    translated = Path(job["srt_path"]).with_suffix(f".{lang}.srt")
    if not translated.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(str(translated), filename=f"{job_id}.{lang}.srt", media_type="application/x-subrip")

@app.post("/translate-srt", response_class=HTMLResponse)
async def translate_uploaded_srt(request: Request,
                                 srtfile: UploadFile = File(...),
                                 target_lang: str = Form(...)):
    job_id = str(uuid.uuid4())
    job_dir = BASE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    srt_path = job_dir / srtfile.filename

    # Save SRT (stream)
    with srt_path.open("wb") as f:
        while True:
            chunk = await srtfile.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)

    out_path = srt_path.with_suffix(f".{target_lang}.srt")
    try:
        translate_srt(str(srt_path), str(out_path), source_lang="auto", target_lang=target_lang)
    except Exception as e:
        return HTMLResponse(f"Preklad zlyhal: {e}", status_code=500)

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "job_id": job_id,
            "original_ready": False,
            "translated_ready": True,
            "translated_path": f"/download/{job_id}/{target_lang}",
            "target_lang": target_lang,
        },
    )
