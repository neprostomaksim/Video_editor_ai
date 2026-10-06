# -*- coding: utf-8 -*-
"""Общее для инструментов: корень проекта, настройки студии, распознавание речи, глоссарий."""
import json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIO = os.path.join(ROOT, "studio")
sys.path.insert(0, os.path.join(ROOT, "engine"))
# ffmpeg / ffprobe / yt-dlp, которые ./setup.sh положил в проект (если их нет в системе)
os.environ["PATH"] = os.path.join(ROOT, "bin") + os.pathsep + os.environ.get("PATH", "")


def style():
    from core import load_style          # noqa: E402  (engine/core.py)
    return load_style()


def speech_words(media, workdir, lang):
    """Речь → слова с таймингами [{w, start, end}] через `npx hyperframes transcribe`.
    Whisper и модель HyperFrames скачивает сам при первом запуске (ничего ставить не нужно).
    Модель: small (многоязычная; по умолчанию), точнее и медленнее — HF_WHISPER_MODEL=large-v3."""
    os.makedirs(workdir, exist_ok=True)
    model = os.environ.get("HF_WHISPER_MODEL", "small")
    r = subprocess.run(npx() + ["hyperframes", "transcribe", os.path.abspath(media), "-d", os.path.abspath(workdir),
                        "-m", model, "-l", lang, "--json"], capture_output=True, text=True)
    out = os.path.join(workdir, "transcript.json")
    if r.returncode or not os.path.exists(out):
        sys.stderr.write((r.stdout + r.stderr)[-1500:] + "\n")
        raise SystemExit("распознавание речи не удалось (npx hyperframes transcribe) — проверь интернет при первом запуске")
    words = [{"w": w["text"].strip(), "start": float(w["start"]), "end": float(w["end"])}
             for w in json.load(open(out, encoding="utf-8")) if w.get("text", "").strip()]
    return words


def npx():
    return ["npx", "--yes"]


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
    """(ширина, высота) с учётом поворота телефонного видео; совместимо со старыми ffprobe."""
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
                                   "-of", "json", path]).decode()
    st = json.loads(out)["streams"][0]
    w, h = st["width"], st["height"]
    rot = int(float((st.get("tags") or {}).get("rotate", 0) or 0))
    for sd in st.get("side_data_list", []) or []:
        rot = int(float(sd.get("rotation", rot) or rot))
    return (h, w) if abs(rot) % 180 == 90 else (w, h)
