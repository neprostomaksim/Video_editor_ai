# -*- coding: utf-8 -*-
"""Общее для инструментов: корень проекта, настройки студии, распознавание речи, глоссарий."""
import json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUDIO = os.path.join(ROOT, "studio")
sys.path.insert(0, os.path.join(ROOT, "engine"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hf_platform as P  # noqa: E402

P.setup_io()            # UTF-8 в консоли Windows
P.add_bin_to_path()     # ffmpeg / ffprobe / yt-dlp, которые setup положил в проект (если их нет в системе)


def style():
    from core import load_style          # noqa: E402  (engine/core.py)
    return load_style()


def hf(args, **kw):
    """HyperFrames CLI (hf.py — одинаково на macOS, Windows, Linux): hf(["snapshot", pub, …], cwd=…)."""
    return subprocess.run([sys.executable, os.path.join(ROOT, "hf.py")] + list(args), **kw)


def speech_words(media, workdir, lang):
    """Речь → слова с таймингами [{w, start, end}] через HyperFrames (`hf.py transcribe`).
    Whisper и модель HyperFrames скачивает сам при первом запуске (ничего ставить не нужно).
    Модель: small (многоязычная; по умолчанию), точнее и медленнее — HF_WHISPER_MODEL=large-v3."""
    os.makedirs(workdir, exist_ok=True)
    model = os.environ.get("HF_WHISPER_MODEL", "small")
    r = hf(["transcribe", os.path.abspath(media), "-d", os.path.abspath(workdir), "-m", model, "-l", lang, "--json"],
           capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = os.path.join(workdir, "transcript.json")
    if r.returncode or not os.path.exists(out):
        sys.stderr.write((r.stdout + r.stderr)[-1500:] + "\n")
        raise SystemExit("распознавание речи не удалось (hf.py transcribe) — проверь интернет при первом запуске и `python3 setup.py --check`")
    words = [{"w": w["text"].strip(), "start": float(w["start"]), "end": float(w["end"])}
             for w in json.load(open(out, encoding="utf-8")) if w.get("text", "").strip()]
    return words


def tile(images, out, vf, extra=()):
    """Склеить картинки в одну (контакт-лист, палитра) фильтром ffmpeg vf. Вместо `-pattern_type glob`,
    которого нет в ffmpeg на Windows: временная нумерованная последовательность 0001.jpg, 0002.jpg…"""
    import tempfile
    images = sorted(images)
    if not images:
        return None
    with tempfile.TemporaryDirectory() as td:
        for i, src in enumerate(images):
            P.link_or_copy(src, os.path.join(td, f"{i + 1:04d}.jpg"))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-start_number", "1", "-i", os.path.join(td, "%04d.jpg"),
                        "-vf", vf, *extra, out], capture_output=True)
    return out if os.path.exists(out) else None


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
