# -*- coding: utf-8 -*-
"""Установка и проверка окружения AI Montage Kit — macOS, Windows (без WSL) и Linux.

  python3 setup.py           поставить недостающее (без прав администратора — всё кладётся в папку проекта)
  python3 setup.py --check   только проверить
  python3 setup.py --yes     Windows: ещё и Node.js и Visual C++ Runtime через winget, если их нет
  python3 setup.py --heygen  подключить HeyGen (по желанию: музыка из каталога HeyGen; вход через браузер)

На Windows пиши `python` (или `py`) вместо `python3`, или просто запусти setup.cmd.
Нужно заранее: Python 3.9+ и Node.js 22+ (nodejs.org, LTS; на Windows поставит --yes).
"""
import os, platform, shutil, stat, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hf_platform as P  # noqa: E402

TOOLS = os.path.join(ROOT, "tools")
HF = [sys.executable, os.path.join(ROOT, "hf.py")]
HEYGEN_DIRS = [os.path.join(P.HOME, ".local", "bin")]


def say(name, status):
    print(f"  {name:<32} {status}", flush=True)


def ok(cmd, **kw):
    try:
        return P.run_text(cmd, timeout=kw.pop("timeout", 120), **kw).returncode == 0
    except Exception:
        return False


def node_major():
    n = P.which("node")
    if not n:
        return 0
    r = P.run_text([n, "-p", "process.versions.node.split('.')[0]"])
    try:
        return int(r.stdout.strip())
    except ValueError:
        return 0


def npm(*args):
    n = P.which("npm")
    if not n:
        raise SystemExit("нет npm (ставится вместе с Node.js) — https://nodejs.org")
    return subprocess.run([n, *args, "--no-fund", "--no-audit", "--loglevel=error"], cwd=TOOLS).returncode == 0


def heygen_bin():
    h = P.which("heygen")
    if h:
        return h
    for d in HEYGEN_DIRS:
        c = os.path.join(d, P.exe("heygen"))
        if os.path.exists(c):
            return c
    return None


def winget(pkg):
    w = P.which("winget")
    if not w:
        print(f"  winget не найден — поставь {pkg} вручную")
        return False
    print(f"• winget install {pkg}")
    return subprocess.run([w, "install", "-e", "--id", pkg, "--accept-package-agreements",
                           "--accept-source-agreements", "--silent"]).returncode == 0


def connect_heygen():
    h = heygen_bin()
    if not h:
        if P.IS_WIN:
            print("HeyGen CLI для Windows ставится по инструкции https://developers.heygen.com/cli — "
                  "после установки снова запусти: python setup.py --heygen")
            return 1
        print("Ставлю HeyGen CLI…")
        if subprocess.run("curl -fsSL https://static.heygen.ai/cli/install.sh | bash", shell=True).returncode:
            print("не вышло — https://developers.heygen.com/cli")
            return 1
        h = heygen_bin()
    print("Вход в HeyGen: откроется браузер — войди в свой аккаунт HeyGen (можно бесплатный) и подтверди доступ.")
    r = subprocess.run([h, "auth", "login", "--oauth"]).returncode
    if r == 0:
        print("✓ HeyGen подключён: музыка из каталога доступна")
    return r


def check():
    """→ список недостающего."""
    P.add_bin_to_path()
    miss = []
    print("AI Montage Kit — проверка окружения")
    nm = node_major()
    if nm >= 22 and P.which("npx"):
        say("Node.js", f"✓ v{nm}")
    else:
        say("Node.js 22+", "✗ нет или старая версия — скачай LTS с https://nodejs.org"
            + (" (или python setup.py --yes)" if P.IS_WIN else ""))
        miss.append("node")
    say("Python", f"✓ {platform.python_version()}" if sys.version_info >= (3, 9) else "✗ нужен 3.9+ — python.org")
    if sys.version_info < (3, 9):
        miss.append("python")
    if P.which("ffmpeg") and P.which("ffprobe"):
        say("ffmpeg (видео и звук)", "✓")
    else:
        say("ffmpeg (видео и звук)", "✗ нет")
        miss.append("ffmpeg")
    if P.which("yt-dlp"):
        say("yt-dlp (видео по ссылкам)", "✓")
    else:
        say("yt-dlp (видео по ссылкам)", "✗ нет")
        miss.append("ytdlp")
    cli = os.path.join(TOOLS, "node_modules", "hyperframes", "dist", "cli.js")
    if os.path.exists(cli) and os.path.isdir(os.path.join(TOOLS, "node_modules", "puppeteer-core")):
        say("HyperFrames (анимация и рендер)", f"✓ {P.HF_VERSION}")
        if ok(HF + ["browser", "path"], timeout=60):
            say("браузер для рендера", "✓")
        else:
            say("браузер для рендера", "✗ нет")
            miss.append("browser")
    else:
        say("HyperFrames (анимация и рендер)", "✗ нет")
        miss += ["npm", "browser"]
    w = P.whisper_cli()
    if P.IS_WIN or sys.platform.startswith("linux"):
        if not w:
            say("распознавание речи (whisper)", "— скачается при установке")
            miss.append("whisper")
        elif not P.whisper_works(w):
            say("распознавание речи (whisper)", "✗ не запускается — нужен Visual C++ Runtime: python setup.py --yes")
            miss.append("vcredist")
        else:
            say("распознавание речи (whisper)", "✓")
    if P.whisper_model("small"):
        say("модель распознавания речи", "✓")
    else:
        say("модель распознавания речи", "— скачается при установке (~470 МБ)")
        miss.append("asr")
    roots = [os.path.join(ROOT, ".agents", "skills"), os.path.join(ROOT, ".claude", "skills")] + \
            [os.path.join(P.HOME, d, "skills") for d in (".claude", ".agents", ".codex", ".cursor")]
    if any(os.path.exists(os.path.join(r, "hyperframes-audio", "scripts", "carve.mjs")) for r in roots):
        say("скиллы HyperFrames (музыка)", "✓")
    else:
        say("скиллы HyperFrames (музыка)", "— нет (желательно)")
        miss.append("skills")
    h = heygen_bin()
    if h and ok([h, "auth", "status"], timeout=30):
        say("HeyGen (музыка из каталога)", "✓ подключён")
    else:
        say("HeyGen (музыка из каталога)", "— не подключён (по желанию: setup.py --heygen)")
    st = os.path.join(ROOT, "studio")
    if os.path.exists(os.path.join(st, "studio.json")) and os.path.exists(os.path.join(st, "profile.md")):
        say("монтаж", "✓ настроен")
    else:
        say("монтаж", "— не настроен: открой агента и напиши «привет»")
    return miss


def install(miss, yes):
    os.makedirs(P.BIN, exist_ok=True)
    if P.IS_WIN and yes:
        if "node" in miss:
            winget("OpenJS.NodeJS.LTS")
            print("Node.js поставлен — закрой это окно, открой новое и снова запусти setup.cmd")
            return
        if "vcredist" in miss:
            winget("Microsoft.VCRedist.2015+.x64")
    if "node" in miss or "python" in miss:
        print("\nСначала поставь Node.js и Python (ссылки выше), потом снова setup")
        sys.exit(1)
    print("\nСтавлю недостающее в папку проекта…")
    print("• HyperFrames и зависимости")
    npm("install")
    if "ffmpeg" in miss:
        print("• ffmpeg")
        npm("install", "--no-save", "ffmpeg-static", "ffprobe-static")
        node = P.which("node")
        f = P.run_text([node, "-e", "process.stdout.write(require('ffmpeg-static'))"], cwd=TOOLS).stdout.strip()
        p = P.run_text([node, "-e", "process.stdout.write(require('ffprobe-static').path)"], cwd=TOOLS).stdout.strip()
        for src, name in ((f, "ffmpeg"), (p, "ffprobe")):
            if not src or not os.path.exists(src):
                print(f"  {name} не скачался — поставь вручную: https://ffmpeg.org/download.html")
                continue
            dst = os.path.join(P.BIN, P.exe(name))
            if os.path.lexists(dst):
                os.remove(dst)
            shutil.copy2(src, dst)            # копия, а не ссылка: на Windows ссылки требуют прав администратора
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IEXEC)
    if "ytdlp" in miss:
        print("• yt-dlp")
        m = platform.machine().lower()
        asset = ("yt-dlp.exe" if P.IS_WIN else "yt-dlp_macos" if P.IS_MAC
                 else "yt-dlp_linux_aarch64" if m in ("aarch64", "arm64") else "yt-dlp_linux")
        dst = os.path.join(P.BIN, P.exe("yt-dlp"))
        try:
            P.download(f"https://github.com/yt-dlp/yt-dlp/releases/latest/download/{asset}", dst)
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IEXEC)
        except Exception:
            print("  не скачался — видео по ссылкам не будут работать, файлами можно")
    if "browser" in miss or "npm" in miss:
        print("• браузер для рендера")
        if not ok(HF + ["browser", "ensure"], timeout=1200):
            print("  не скачался — повтори setup")
    if "whisper" in miss:
        try:
            w = P.whisper_cli(need=True)
            if P.IS_WIN and not P.whisper_works(w):
                print("  whisper не запускается: нужен Visual C++ Runtime — python setup.py --yes "
                      "(или https://aka.ms/vs/17/release/vc_redist.x64.exe)")
        except Exception as e:
            print(f"  не вышло: {e}")
    if "asr" in miss:
        try:
            P.whisper_model("small", need=True)
        except Exception as e:
            print(f"  модель не скачалась ({e}) — скачается при первом распознавании")
        if P.IS_MAC and not P.whisper_cli():
            # на Mac HyperFrames собирает whisper.cpp сам при первом распознавании — делаем это сейчас на пробнике
            print("• распознавание речи: первая сборка whisper.cpp (пару минут)")
            wav = os.path.join(P.BIN, ".probe.wav")
            if ok(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=2", "-ar", "16000", "-ac", "1", wav]):
                ok(HF + ["transcribe", wav, "-d", os.path.join(P.BIN, ".probe"), "-m", "small", "-l", "ru", "--json"],
                   timeout=1800)
            shutil.rmtree(os.path.join(P.BIN, ".probe"), ignore_errors=True)
            if os.path.exists(wav):
                os.remove(wav)
    if "skills" in miss:
        print("• скиллы HyperFrames")
        if not ok(HF + ["skills"], timeout=600):
            print("  не вышло — можно позже: python3 hf.py skills")


def main():
    P.setup_io()
    args = sys.argv[1:]
    if "--heygen" in args:
        sys.exit(connect_heygen())
    hard = {"node", "python", "ffmpeg", "npm", "browser", "ytdlp", "whisper", "vcredist"}
    miss = check()
    if not miss or ("--check" in args and not hard & set(miss)):
        print("\nГотово. Открой папку в Claude Code или Codex и напиши «привет».")
        return
    if "--check" in args:
        print("\nНе хватает: " + ", ".join(miss) + " → запусти setup (python3 setup.py; Windows: setup.cmd)")
        sys.exit(1)
    install(miss, "--yes" in args)
    print()
    miss = check()
    left = hard & set(miss)
    print("\nГотово. Открой папку в Claude Code или Codex и напиши «привет»." if not left
          else "\nЕщё не хватает: " + ", ".join(sorted(left)))
    sys.exit(1 if left else 0)


if __name__ == "__main__":
    main()
