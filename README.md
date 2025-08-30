# Whisper Subtitles on Railway (v3)

Enhancements in v3:
- Select **default transcription language** (Auto or specific) on the homepage.
- Upload **.srt** directly for translation.
- Increased default upload limit to **2 GB** (MAX_UPLOAD_MB=2048).

Stack: FastAPI + Jinja2, openai-whisper + ffmpeg + torch (CPU wheels), MarianMT via Hugging Face (Helsinki-NLP/opus-mt-*).

## Environment Variables
- `WHISPER_MODEL` (default: `small`)
- `CHUNK_SECONDS` (default: `30`)
- `MAX_UPLOAD_MB` (default: `2048`)  # ~2 GB
- `DEFAULT_LANG` (default: `auto`)   # UI default for language selector

## Notes
- Railway storage is **ephemeral**; files live under `/tmp/jobs/<job_id>`.
- Large uploads can be slow; ensure plan bandwidth/timeouts are sufficient.
