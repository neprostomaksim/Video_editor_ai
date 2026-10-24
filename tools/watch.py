# -*- coding: utf-8 -*-
"""Посмотреть видео: ссылка или файл → ключевые кадры + расшифровка речи с таймкодами.
Агент потом открывает кадры как картинки и «видит» ролик: монтаж, субтитры, графику, темп.

  python3 tools/watch.py <ссылка|файл>                         # весь ролик
  python3 tools/watch.py <ссылка|файл> --start 0 --end 5       # кусок плотнее (например, хук)
  python3 tools/watch.py <файл> --at 1.5,7,12.4                # + кадры в конкретные моменты
  python3 tools/watch.py <файл> --width 1024                   # крупнее — чтобы читать мелкий текст
  python3 tools/watch.py <файл> --no-speech                    # без расшифровки

Ссылки: YouTube, Shorts, Instagram Reels, TikTok, VK и др. (yt-dlp; закрытые/приватные ролики не скачать).
Результат: videos/_watch/<имя>/ — video.mp4, frames/NN_t.jpg, sheet.jpg (контакт-лист), transcript.txt, report.md.
Кадров по длине: ≤30 с — 16, ≤1 мин — 24, ≤3 мин — 40, дальше 60 (не чаще 2 в секунду); сначала склейки, потом равномерно.
"""
import argparse, hashlib, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as CM  # noqa: E402


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def fmt(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def download(url, out):
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, "video.mp4")
    if os.path.exists(dst):
        return dst
    r = sh(["yt-dlp", "-q", "--no-playlist", "-f", "bv*[height<=1920][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
            "--merge-output-format", "mp4", "-o", dst, url])
    if r.returncode or not os.path.exists(dst):
        sys.stderr.write(r.stderr[-800:] + "\n")
        raise SystemExit("не скачалось: ролик закрытый, удалён или сайт не поддерживается — попроси прислать файл")
    return dst


def budget(d):
    return 16 if d <= 30 else 24 if d <= 60 else 40 if d <= 180 else 60


def pick_times(video, t0, t1, n, thr=0.22):
    """Склейки (смена сцены) + равномерная сетка → n моментов, не ближе 0.5 с друг к другу."""
    err = sh(["ffmpeg", "-ss", str(t0), "-to", str(t1), "-i", video, "-vf",
              f"scale=320:-2,select='gt(scene,{thr})',showinfo", "-an", "-f", "null", "-"]).stderr
    cuts = [t0 + float(x) + 0.2 for x in re.findall(r"pts_time:([\d.]+)", err)]
    span = t1 - t0
    grid = [t0 + span * (k + .5) / n for k in range(n)]
    if len(cuts) > n:                                   # склеек больше бюджета — берём равномерно из них
        cuts = [cuts[int(i * len(cuts) / n)] for i in range(n)]
    out = []
    for t in sorted([t0 + 0.05] + cuts + grid):         # кадр 0 всегда: это обложка в ленте
        if t < t1 and all(abs(t - x) >= 0.5 for x in out):
            out.append(t)
    while len(out) > n:                                 # лишнее — убираем самые близкие к соседям сеточные
        gaps = [(out[i + 1] - out[i - 1], i) for i in range(1, len(out) - 1)]
        out.pop(min(gaps)[1])
    return out, len(cuts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--at", default="", help="доп. кадры: 1.5,7,12.4 (сек)")
    ap.add_argument("--frames", type=int, help="сколько кадров (по умолч. по длине)")
    ap.add_argument("--width", type=int, default=540)
    ap.add_argument("--lang", default="auto")
    ap.add_argument("--no-speech", action="store_true")
    a = ap.parse_args()

    is_url = re.match(r"https?://", a.src)
    name = (re.sub(r"[^a-zA-Z0-9]+", "-", os.path.splitext(os.path.basename(a.src.split("?")[0]))[0]).strip("-")[:40]
            or "video") + "-" + hashlib.md5(a.src.encode()).hexdigest()[:6]
    out = a.out or os.path.join(CM.ROOT, "videos", "_watch", name)
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    video = download(a.src, out) if is_url else os.path.abspath(a.src)
    if not os.path.exists(video):
        raise SystemExit(f"нет файла: {video}")
    dur = CM.duration(video)
    w, h = CM.video_size(video)
    t0, t1 = max(0, a.start), min(dur, a.end or dur)
    focused = a.start > 0 or a.end is not None
    n = a.frames or (min(int((t1 - t0) * 2), 30) if focused else budget(dur))
    n = max(1, min(n, int((t1 - t0) * 2) or 1))
    times, ncuts = pick_times(video, t0, t1, n)
    times = sorted(set(times + [float(x) for x in a.at.split(",") if x.strip()]))
    for f in os.listdir(os.path.join(out, "frames")):
        os.remove(os.path.join(out, "frames", f))
    frames = []
    for i, t in enumerate(times):
        fp = os.path.join(out, "frames", f"{i + 1:02d}_{t:06.2f}s.jpg")
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
            "-vf", f"scale={a.width}:-2", "-q:v", "3", fp])
        if os.path.exists(fp):
            frames.append((t, fp))
    cols = 6 if h > w else 4
    CM.tile([fp for _, fp in frames], os.path.join(out, "sheet.jpg"),
            f"scale=240:-2,tile={cols}x{(len(frames) + cols - 1) // cols}:padding=4", ["-frames:v", "1"])
    lines = []
    if not a.no_speech:
        try:
            words = CM.speech_words(video, os.path.join(out, ".asr"), a.lang)
            cur = []
            for wd in words:
                if wd["end"] < t0 or wd["start"] > t1:
                    continue
                cur.append(wd)
                if wd["w"][-1:] in ".!?…" or len(cur) >= 14:
                    lines.append(f"[{fmt(cur[0]['start'])}] " + " ".join(x["w"] for x in cur))
                    cur = []
            if cur:
                lines.append(f"[{fmt(cur[0]['start'])}] " + " ".join(x["w"] for x in cur))
        except SystemExit:
            lines = ["(речь не распознана)"]
    open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    rep = [f"# Просмотр: {a.src}", "",
           f"- длительность **{dur:.1f} c**, кадр {w}×{h}{' (вертикальный)' if h > w else ''}",
           f"- склеек (смен сцены) в отрезке {fmt(t0)}–{fmt(t1)}: **{ncuts}** → в среднем шот {((t1 - t0) / max(1, ncuts + 1)):.1f} c",
           f"- видео: `{video}`", f"- контакт-лист: `{os.path.join(out, 'sheet.jpg')}`", "",
           "## Кадры (открой каждый)", ""] + [f"- t={fmt(t)} `{fp}`" for t, fp in frames] + \
          ["", "## Речь", ""] + (lines or ["(без расшифровки)"])
    open(os.path.join(out, "report.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
