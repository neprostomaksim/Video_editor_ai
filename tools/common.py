# -*- coding: utf-8 -*-
"""Общее для инструментов: корень проекта, настройки студии, модель whisper, глоссарий."""
import json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIO = os.path.join(ROOT, "studio")
sys.path.insert(0, os.path.join(ROOT, "engine"))


def style():
    from core import load_style          # noqa: E402  (engine/core.py)
    return load_style()


def whisper_model():
    """ggml-модель whisper.cpp: $WHISPER_MODEL → models/ в проекте → кэш HyperFrames."""
    for p in (os.environ.get("WHISPER_MODEL"),
              os.path.join(ROOT, "models", "ggml-small.bin"),
              os.path.expanduser("~/.cache/hyperframes/whisper/models/ggml-small.bin"),
              os.path.join(ROOT, "models", "ggml-base.bin")):
        if p and os.path.exists(p):
            return p
    raise SystemExit("Нет модели распознавания речи. Запусти ./setup.sh (скачает models/ggml-small.bin, ~470 МБ)")


def whisper_bin():
    for b in ("whisper-cli", "whisper-cpp", "main"):
        if shutil.which(b):
            return b
    raise SystemExit("Нет whisper-cli. macOS: brew install whisper-cpp  (или ./setup.sh)")


def whisper_json(wav, out_base, lang):
    """Слова с таймингами (по одному токену на сегмент) → [{w, start, end}]."""
    subprocess.run([whisper_bin(), "-m", whisper_model(), "-l", lang, "-ml", "1", "-sow", "-oj", "-np",
                    "-f", wav, "-of", out_base], check=True)
    data = json.load(open(out_base + ".json", encoding="utf-8"))
    words = []
    for seg in data.get("transcription", []):
        txt = seg["text"]
        if not txt.strip():
            continue
        a, b = seg["offsets"]["from"] / 1000, seg["offsets"]["to"] / 1000
        if txt.startswith(" ") or not words:
            words.append({"w": txt.strip(), "start": a, "end": b})
        else:
            words[-1]["w"] += txt.strip()
            words[-1]["end"] = b
    return words


def glossary():
    """Базовый глоссарий (бренды ИИ) + свой клиента studio/glossary.json (его правила первыми)."""
    g = {"word": [], "join": []}
    for p in (os.path.join(STUDIO, "glossary.json"), os.path.join(ROOT, "assets", "glossary.base.json")):
        if os.path.exists(p):
            d = json.load(open(p, encoding="utf-8"))
            g["word"] += d.get("word", [])
            g["join"] += d.get("join", [])
    return g


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode())


def video_size(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:stream_side_data=rotation", "-of", "json", path]).decode()
    st = json.loads(out)["streams"][0]
    w, h = st["width"], st["height"]
    rot = 0
    for sd in st.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    return (h, w) if abs(rot) == 90 else (w, h)
