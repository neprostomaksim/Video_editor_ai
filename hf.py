# -*- coding: utf-8 -*-
"""HyperFrames — движок анимации и рендера (open-source, Apache-2.0, от HeyGen). Работает на macOS, Windows и Linux.

  python3 hf.py check videos/<slug>/public
  python3 hf.py snapshot videos/<slug>/public --at 0,3,6 --describe false
  python3 hf.py render videos/<slug>/public -o videos/<slug>/output.mp4 --fps 25
  (на Windows — python hf.py …; на Mac/Linux то же самое делает ./hf …)

Версия закреплена в tools/package.json (ставит setup.py). Видит ffmpeg/ffprobe/yt-dlp из ./bin.
На Windows для распознавания речи (transcribe) сам скачивает готовый whisper-cli.
"""
import os, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import hf_platform as P  # noqa: E402


def main(argv):
    P.setup_io()
    P.env()
    if argv[:1] == ["transcribe"] and not os.environ.get("HYPERFRAMES_WHISPER_PATH"):
        w = P.whisper_cli(need=True)          # Windows/Linux; на Mac HyperFrames собирает whisper сам
        if w:
            os.environ["HYPERFRAMES_WHISPER_PATH"] = w
    try:
        return subprocess.call(P.hyperframes() + argv)
    except FileNotFoundError:
        print("не найден Node.js — поставь LTS с https://nodejs.org и запусти setup.py", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
