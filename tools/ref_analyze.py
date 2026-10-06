# -*- coding: utf-8 -*-
"""Разбор ролика-референса: скелет монтажа + стиль.

  python3 tools/ref_analyze.py <reference.mp4> videos/<slug> [--thr 0.22]       # референс конкретного ролика
  python3 tools/ref_analyze.py <reference.mp4> studio/references/<name>          # референс стиля при настройке

Создаёт <папка>/ref/:
  shots/NN_<start>.jpg  ключевой кадр каждого шота (середина), 360px
  sheet.jpg             контакт-лист шотов по порядку (номер = порядок в таблице)
  transcript.txt        речь донора с таймкодами
  analysis.md           таблица: шот · время · длительность · что говорит донор → сюда режиссёр
                        дописывает «тип сцены / брать как b-roll / перерисовать / пропустить»
  shots.json            то же машинно: [{i, start, end, text}]
  style.json            темп (средний шот, склеек/мин, слов/с) + палитра (8 главных цветов) + крупные кадры
  frames/               6 кадров в полный размер — по ним агент описывает субтитры, плашки, шрифты, раскладку
"""
import argparse, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as CM  # noqa: E402


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref"); ap.add_argument("proj")
    ap.add_argument("--thr", type=float, default=0.22, help="порог детекции склейки (0.15–0.35)")
    ap.add_argument("--thr-top", type=float, default=0.08, help="порог для верхней зоны (split-графика)")
    ap.add_argument("--min", type=float, default=0.6, help="минимальная длина шота, с")
    ap.add_argument("--lang", default="auto", help="язык речи донора (по умолч. определяется сам)")
    a = ap.parse_args()
    out = os.path.join(a.proj, "ref")
    os.makedirs(os.path.join(out, "shots"), exist_ok=True)
    dur = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.ref]).stdout)

    # 1. склейки
    # два прохода: весь кадр + только верхняя зона (в split-рилсах лицо внизу не меняется,
    # и склейка графики сверху по всему кадру почти не видна)
    found = []
    for vf in (f"select='gt(scene,{a.thr})',showinfo",
               f"crop=iw:ih*0.46:0:0,select='gt(scene,{a.thr_top})',showinfo"):
        err = sh(["ffmpeg", "-i", a.ref, "-vf", vf, "-an", "-f", "null", "-"]).stderr
        found += [float(x) for x in re.findall(r"pts_time:([\d.]+)", err)]
    cuts = [0.0] + sorted(found)
    bounds = []
    for t in cuts + [dur]:
        if not bounds or t - bounds[-1] >= a.min:
            bounds.append(t)
    if bounds[-1] < dur - 0.3:
        bounds.append(dur)
    shots = [{"i": i + 1, "start": round(s, 2), "end": round(e, 2)} for i, (s, e) in enumerate(zip(bounds, bounds[1:]))]

    # 2. речь донора (язык определяется сам)
    segs = []
    try:
        words = CM.speech_words(a.ref, os.path.join(out, ".asr"), a.lang)
        cur = []
        for w in words:
            cur.append(w)
            if w["w"][-1:] in ".!?…" or len(cur) >= 14:
                segs.append((cur[0]["start"], cur[-1]["end"], " ".join(x["w"] for x in cur)))
                cur = []
        if cur:
            segs.append((cur[0]["start"], cur[-1]["end"], " ".join(x["w"] for x in cur)))
    except SystemExit:
        print("⚠ речь донора не распознана — разбор только по кадрам")
    open(os.path.join(out, "transcript.txt"), "w").write(
        "\n".join(f"{a_:6.2f}–{b_:6.2f}  {t}" for a_, b_, t in segs))
    for s in shots:
        s["text"] = " ".join(t for a_, b_, t in segs if a_ < s["end"] and b_ > s["start"])

    # 3. ключевые кадры + контакт-лист
    for s in shots:
        mid = (s["start"] + s["end"]) / 2
        s["frame"] = f"shots/{s['i']:02d}_{s['start']:.1f}.jpg"
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{mid:.2f}", "-i", a.ref, "-frames:v", "1",
            "-vf", "scale=360:-1", os.path.join(out, s["frame"])])
    cols = 6
    rows = (len(shots) + cols - 1) // cols
    sh(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", os.path.join(out, "shots", "*.jpg"),
        "-vf", f"scale=240:-1,tile={cols}x{rows}", "-frames:v", "1", os.path.join(out, "sheet.jpg")])

    json.dump(shots, open(os.path.join(out, "shots.json"), "w"), ensure_ascii=False, indent=1)
    st = style_stats(a.ref, out, shots, segs, dur)
    md = [f"# Разбор референса: {os.path.basename(a.ref)} ({dur:.1f} c, {len(shots)} шотов)", "",
          "Контакт-лист: `ref/sheet.jpg` (слева направо, сверху вниз = порядок шотов).", "",
          "| # | время | с | что говорит донор | → решение (сцена / b-roll кроп / перерисовать / пропустить) |",
          "|---|---|---|---|---|"]
    for s in shots:
        md.append(f"| {s['i']} | {s['start']:.1f}–{s['end']:.1f} | {s['end']-s['start']:.1f} | {s['text'][:90]} | |")
    md += ["", "## Стиль и темп", "",
           f"- средний шот **{st['avg_shot']} c**, склеек **{st['cuts_per_min']}/мин**, речь **{st['wps']} слов/с**",
           "- палитра (по частоте): " + " ".join(f"`{c}`" for c in st["palette"]),
           "- крупные кадры: `ref/frames/*.jpg` — посмотри их и заполни:", "",
           "| что | как у референса |", "|---|---|",
           "| субтитры: где (низ/центр/стык), сколько слов, капс? | |",
           "| субтитры: плашка / обводка / подсветка активного слова, цвета | |",
           "| шрифт заголовков (гротеск/антиква/рукописный, жирность) | |",
           "| плашки и акценты: цвет, скругление | |",
           "| раскладки: split (графика + лицо), полный экран графики, только лицо | |",
           "| переходы, наезды, эффекты | |",
           "| хук (первые 2 с): что на экране | |",
           "| финал/CTA | |"]
    open(os.path.join(out, "analysis.md"), "w").write("\n".join(md) + "\n")
    print(f"→ {out}/analysis.md, sheet.jpg ({len(shots)} шотов)")


def style_stats(ref, out, shots, segs, dur):
    """Темп + палитра + крупные кадры для описания стиля."""
    fr = os.path.join(out, "frames")
    os.makedirs(fr, exist_ok=True)
    for k in range(6):
        t = dur * (k + .5) / 6
        sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", ref, "-frames:v", "1",
            "-vf", "scale=720:-2", os.path.join(fr, f"{k+1}_{t:.1f}.jpg")])
    pal = os.path.join(out, "palette.png")
    sh(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", os.path.join(fr, "*.jpg"),
        "-vf", "scale=360:-2,tile=6x1,palettegen=max_colors=8:reserve_transparent=0:stats_mode=full", pal])
    colors = []
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", pal, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    for i in range(0, len(raw) - 2, 3):
        c = "#%02X%02X%02X" % (raw[i], raw[i + 1], raw[i + 2])
        if c not in colors:
            colors.append(c)
    colors = colors[:8]
    words = sum(len(t.split()) for _, _, t in segs)
    st = {"duration": round(dur, 1), "shots": len(shots),
          "avg_shot": round(dur / max(1, len(shots)), 2),
          "cuts_per_min": round(max(0, len(shots) - 1) / max(1e-6, dur) * 60, 1),
          "wps": round(words / max(1e-6, dur), 2), "palette": colors}
    json.dump(st, open(os.path.join(out, "style.json"), "w"), ensure_ascii=False, indent=1)
    return st


if __name__ == "__main__":
    main()
