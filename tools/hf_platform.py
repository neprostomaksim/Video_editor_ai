# -*- coding: utf-8 -*-
"""Кроссплатформенный слой (macOS / Windows / Linux): всё, что зависит от ОС, — только здесь.

    import hf_platform as P
    P.setup_io()              # UTF-8 в консоли (Windows: иначе «→», «✓» и кириллица роняют скрипт)
    P.env()                   # окружение для HyperFrames: bin/ проекта в PATH, whisper-cli, без проверки обновлений
    P.hyperframes()           # команда HyperFrames CLI списком: закреплённая версия из tools/node_modules или npx
    P.whisper_cli(need=True)  # whisper-cli (Windows/Linux — скачает готовую сборку whisper.cpp)
    P.whisper_model("small")  # модель распознавания речи
    P.exe("ffmpeg")           # имя исполняемого файла с .exe на Windows
"""
import json, os, platform, shutil, subprocess, sys, tarfile, urllib.request, zipfile

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin")
HOME = os.path.expanduser("~")
WHISPER_DIR = os.path.join(HOME, ".cache", "hyperframes", "whisper")      # тот же кэш, что у HyperFrames CLI
MODELS_DIR = os.path.join(WHISPER_DIR, "models")
WHISPER_BIN_DIR = os.path.join(WHISPER_DIR, "bin")
HF_VERSION = "0.8.138"                     # как в tools/package.json
WHISPER_FALLBACK_TAG = "b5454"             # релиз whisper.cpp с готовыми сборками, если API GitHub недоступен
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{}.bin"
UA = {"User-Agent": "ai-montage-kit"}


def setup_io():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def exe(name):
    return name + ".exe" if IS_WIN else name


def which(name):
    return shutil.which(name)


def run_text(cmd, **kw):
    """subprocess.run с текстом в UTF-8 (в Windows кодировка консоли по умолчанию — cp1251/cp866)."""
    kw.setdefault("capture_output", True)
    return subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", **kw)


def add_bin_to_path():
    p = os.environ.get("PATH", "")
    if BIN not in p.split(os.pathsep):
        os.environ["PATH"] = BIN + os.pathsep + p


def env():
    """Окружение для HyperFrames и наших инструментов (меняет os.environ и возвращает его)."""
    add_bin_to_path()
    os.environ["HYPERFRAMES_NO_UPDATE_CHECK"] = "1"
    if not os.environ.get("HYPERFRAMES_WHISPER_PATH"):
        w = whisper_cli()
        if w:
            os.environ["HYPERFRAMES_WHISPER_PATH"] = w
    return os.environ


def hyperframes():
    """HyperFrames CLI: закреплённая версия в tools/node_modules (ставит setup) → npx hyperframes@<версия>."""
    cli = os.path.join(ROOT, "tools", "node_modules", "hyperframes", "dist", "cli.js")
    if os.path.exists(cli):
        return [which("node") or "node", cli]
    return [which("npx") or ("npx.cmd" if IS_WIN else "npx"), "--yes", f"hyperframes@{HF_VERSION}"]


def download(url, dst, label=None):
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    tmp = dst + ".download"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r, open(tmp, "wb") as f:
        total, done, last = int(r.headers.get("Content-Length") or 0), 0, -10
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total and label and done * 100 // total - last >= 10:
                last = done * 100 // total
                print(f"  {label}: {last}%", flush=True)
    os.replace(tmp, dst)
    return dst


# ---------- whisper (распознавание речи) ----------
def _whisper_asset():
    m = platform.machine().lower()
    if IS_WIN:
        return "whisper-bin-win-cpu-arm64.zip" if m in ("arm64", "aarch64") else "whisper-bin-x64.zip"
    if sys.platform.startswith("linux"):
        return "whisper-bin-ubuntu-arm64.tar.gz" if m in ("arm64", "aarch64") else "whisper-bin-ubuntu-x64.tar.gz"
    return None                            # macOS: HyperFrames собирает whisper сам (или brew install whisper-cpp)


def _find_in(d, name):
    for root, _, files in os.walk(d):
        if name in files:
            return os.path.join(root, name)
    return None


def whisper_cli(need=False):
    """HYPERFRAMES_WHISPER_PATH → PATH → Homebrew → наш кэш → сборка HyperFrames.
    need=True и не найден: Windows/Linux — скачать готовую сборку whisper.cpp (на Windows HyperFrames сам не соберёт)."""
    name = exe("whisper-cli")
    e = os.environ.get("HYPERFRAMES_WHISPER_PATH")
    if e and os.path.exists(e):
        return e
    p = which("whisper-cli")
    if p:
        return p
    if IS_MAC:
        for c in ("/opt/homebrew/bin/whisper-cli", "/usr/local/bin/whisper-cli"):
            if os.path.exists(c):
                return c
    for d in (WHISPER_BIN_DIR, os.path.join(WHISPER_DIR, "whisper.cpp", "build")):
        if os.path.isdir(d):
            p = _find_in(d, name)
            if p:
                return p
    asset = _whisper_asset()
    if not need or not asset:
        return None
    url = None
    try:
        req = urllib.request.Request("https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=10", headers=UA)
        for rel in json.load(urllib.request.urlopen(req, timeout=30)):
            url = next((a["browser_download_url"] for a in rel.get("assets", []) if a["name"] == asset), None)
            if url:
                break
    except Exception:
        pass
    url = url or f"https://github.com/ggml-org/whisper.cpp/releases/download/{WHISPER_FALLBACK_TAG}/{asset}"
    print(f"• распознавание речи: скачиваю готовую сборку whisper.cpp ({asset})…", flush=True)
    arc = download(url, os.path.join(WHISPER_DIR, asset), "whisper.cpp")
    os.makedirs(WHISPER_BIN_DIR, exist_ok=True)
    if arc.endswith(".zip"):
        with zipfile.ZipFile(arc) as z:
            z.extractall(WHISPER_BIN_DIR)
    else:
        with tarfile.open(arc) as t:
            t.extractall(WHISPER_BIN_DIR)
    os.remove(arc)
    p = _find_in(WHISPER_BIN_DIR, name)
    if not p:
        raise SystemExit(f"в архиве {asset} нет {name} — поставь whisper.cpp вручную и укажи путь в HYPERFRAMES_WHISPER_PATH")
    if not IS_WIN:
        os.chmod(p, 0o755)
    return p


def whisper_works(path):
    """Windows: готовой сборке нужен Visual C++ Redistributable — без него программа не запускается."""
    try:
        r = subprocess.run([path, "--help"], capture_output=True, timeout=30)
        return r.returncode in (0, 1) or b"usage" in (r.stdout + r.stderr).lower()
    except Exception:
        return False


def whisper_model(name="small", need=False):
    path = os.path.join(MODELS_DIR, f"ggml-{name}.bin")
    if os.path.exists(path) and os.path.getsize(path) > 10_000_000:
        return path
    if not need:
        return None
    print(f"• модель распознавания речи ggml-{name}.bin (~470 МБ, один раз)…", flush=True)
    return download(MODEL_URL.format(name), path, f"ggml-{name}")


def link_or_copy(src, dst):
    """Жёсткая ссылка (быстро), а если нельзя (другой диск, FAT, сеть) — копия."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
