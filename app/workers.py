import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any

import whisper
from .srt_utils import segments_to_srt

JOBS: Dict[str, Dict[str, Any]] = {}
CHUNK_SECONDS = int(os.getenv("CHUNK_SECONDS", "30"))

def _set_progress(job_id: str, pct: float, message: str):
    job = JOBS.get(job_id)
    if not job:
        return
    job["progress"] = int(max(0, min(100, round(pct))))
    job["message"] = message

def _set_status(job_id: str, status: str):
    job = JOBS.get(job_id)
    if not job:
        return
    job["status"] = status

def _set_error(job_id: str, err: str):
    job = JOBS.get(job_id)
    if not job:
        return
    job["error"] = err
    job["status"] = "failed"
    job["progress"] = 100
    job["message"] = "Chyba: " + err

def _ffprobe_duration(path: str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
        text=True
    ).strip()
    return float(out)

def _split_audio(video_path: str, out_dir: Path, segment_seconds: int) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "chunk_%04d.wav")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-ac", "1", "-ar", "16000",
        "-f", "segment", "-segment_time", str(segment_seconds),
        "-c:a", "pcm_s16le",
        pattern
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return sorted(out_dir.glob("chunk_*.wav"))

def process_job(job_id: str, video_path: str):
    try:
        _set_status(job_id, "running")
        _set_progress(job_id, 5, "Analýza videa…")
        job_dir = Path(video_path).parent
        chunks_dir = job_dir / "chunks"
        _set_progress(job_id, 15, "Extrakcia audia a delenie na úseky…")
        chunk_files = _split_audio(video_path, chunks_dir, CHUNK_SECONDS)
        if not chunk_files:
            raise RuntimeError("Nepodarilo sa extrahovať audio.")

        _set_progress(job_id, 25, "Načítavam model Whisper…")
        model_name = os.getenv("WHISPER_MODEL", "small")
        model = whisper.load_model(model_name)

        all_segments = []
        _set_progress(job_id, 30, "Prepis prebieha…")
        n = len(chunk_files)
        for i, wav_path in enumerate(chunk_files, start=1):
            result = model.transcribe(str(wav_path), task="transcribe", verbose=False)
            if i == 1:
                JOBS[job_id]["source_lang"] = result.get("language", None)

            offset = (i - 1) * CHUNK_SECONDS
            for seg in result.get("segments", []):
                all_segments.append({
                    "id": seg.get("id", 0),
                    "start": seg["start"] + offset,
                    "end": seg["end"] + offset,
                    "text": seg["text"].strip()
                })

            base_pct = 30
            span = 65
            pct = base_pct + span * (i / n)
            _set_progress(job_id, pct, f"Prepis {i}/{n}…")

        srt_path = job_dir / "output.srt"
        _set_progress(job_id, 96, "Ukladám titulky…")
        srt_text = segments_to_srt(all_segments)
        srt_path.write_text(srt_text, encoding="utf-8")

        JOBS[job_id]["srt_path"] = str(srt_path)
        _set_progress(job_id, 100, "Hotovo ✅")
        _set_status(job_id, "done")
    except Exception as e:
        _set_error(job_id, str(e))
