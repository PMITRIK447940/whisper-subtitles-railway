from pathlib import Path
from typing import List

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

AVAILABLE_LANGUAGES = [
    ("auto", "Auto (detekcia)"),
    ("en", "English"),
    ("sk", "Slovenčina"),
    ("cs", "Čeština"),
    ("de", "Deutsch"),
    ("pl", "Polski"),
    ("hu", "Magyar"),
    ("fr", "Français"),
    ("es", "Español"),
    ("it", "Italiano"),
    ("ro", "Română"),
    ("bg", "Български"),
    ("hr", "Hrvatski"),
    ("sl", "Slovenščina"),
    ("sr", "Srpski"),
    ("uk", "Українська"),
    ("ru", "Русский"),
    ("tr", "Türkçe"),
    ("ar", "العربية"),
    ("zh", "中文"),
    ("ja", "日本語"),
    ("ko", "한국어"),
]

def _load_translator(model_name: str):
    tok = AutoTokenizer.from_pretrained(model_name)
    mdl = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return pipeline("translation", model=mdl, tokenizer=tok)

def _split_srt_blocks(srt_text: str):
    blocks, current = [], []
    for line in srt_text.splitlines():
        if line.strip() == "":
            if current:
                blocks.append("\\n".join(current)); current = []
            continue
        current.append(line)
    if current: blocks.append("\\n".join(current))
    parsed = []
    for b in blocks:
        parts = b.split("\\n", 2)
        if len(parts) == 3:
            parsed.append((parts[0], parts[1], parts[2]))
    return parsed

def _rebuild_srt(blocks):
    out = []
    for idx, timing, text in blocks:
        out += [idx, timing, text, ""]
    return "\\n".join(out)

def _translate_texts(texts: List[str], model_name: str) -> List[str]:
    nlp = _load_translator(model_name)
    outputs = []
    BATCH = 16
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i+BATCH]
        results = nlp(batch, truncation=True, max_length=512)
        outputs.extend([r["translation_text"] for r in results])
    return outputs

def translate_srt(srt_path: str, out_path: str, source_lang: str, target_lang: str):
    srt = Path(srt_path).read_text(encoding="utf-8")
    blocks = _split_srt_blocks(srt)
    texts = [t for _,_,t in blocks]

    if (source_lang or "auto") == target_lang:
        Path(out_path).write_text(srt, encoding="utf-8"); return

    translated = None
    # Try direct
    if source_lang not in (None, "auto"):
        try:
            translated = _translate_texts(texts, f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}")
        except Exception:
            translated = None
    # Pivot via English
    if translated is None:
        mid = texts
        if source_lang not in (None, "auto", "en"):
            mid = _translate_texts(texts, f"Helsinki-NLP/opus-mt-{source_lang}-en")
        if target_lang != "en":
            translated = _translate_texts(mid, f"Helsinki-NLP/opus-mt-en-{target_lang}")
        else:
            translated = mid

    out_blocks = []
    for (idx, timing, _), new_text in zip(blocks, translated):
        out_blocks.append((idx, timing, new_text))
    Path(out_path).write_text(_rebuild_srt(out_blocks), encoding="utf-8")
