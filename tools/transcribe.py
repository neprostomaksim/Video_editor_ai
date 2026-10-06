# -*- coding: utf-8 -*-
"""Видео спикера → проект: перекодированное вертикальное видео + тайминги слов.

  python3 tools/transcribe.py <video.mp4> videos/<slug> [--x 0.5] [--lang ru]

Подходит и для ИИ-аватара (HeyGen и др.), и для живой записи. Живую запись сначала чистим:
tools/cleanup.py (паузы, «э-э», дубли) → transcribe.py videos/<slug>/source/clean.mp4 videos/<slug>.

Горизонтальное/квадратное видео обрезается до 9:16 вокруг спикера: --x — центр кадрирования
(0 = левый край, 0.5 = центр, 1 = правый край). Проверь кадр: videos/<slug>/frame.jpg.

Создаёт:
  <project>/public/input-video.mp4   (1080×1920, h264, keyint 25 — точный сик; звук выровнен до −15 LUFS)
  <project>/words.json               [{w, start, end}] — слова с пунктуацией, после глоссария
  <project>/transcript.txt           читаемый текст с таймкодами (для режиссёра)
"""
import argparse, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as CM  # noqa: E402

PUNCT = ",.!?…:;»«\"'—"


def run(cmd):
    subprocess.run(cmd, check=True)


def split_punct(w):
    m = re.match(r"^([" + re.escape(PUNCT) + r"]*)(.*?)([" + re.escape(PUNCT) + r"]*)$", w)
    return m.group(1), m.group(2), m.group(3)


def apply_glossary(words):
    g = CM.glossary()
    rules = [(re.compile(p, re.I), to) for p, to in g["word"]]
    for w in words:
        pre, core, post = split_punct(w["w"])
        for rx, to in rules:
            if rx.match(core.lower().replace("ё", "е")):
                w["w"] = pre + to + post
                break
    out, i = [], 0
    joins = sorted(g["join"], key=lambda j: -len(j[0]))
    while i < len(words):
        hit = None
        for seq, to in joins:
            n = len(seq)
            chunk = words[i:i + n]
            if len(chunk) == n and all(split_punct(c["w"])[1].lower() == s for c, s in zip(chunk, seq)):
                hit = (n, to)
                break
        if hit:
            n, to = hit
            pre = split_punct(words[i]["w"])[0]
            post = split_punct(words[i + n - 1]["w"])[2]
            out.append({"w": pre + to + post, "start": words[i]["start"], "end": words[i + n - 1]["end"]})
            i += n
        else:
            out.append(words[i])
            i += 1
    return out


def unsquish(words):
    """whisper иногда сжимает кусок фразы в доли секунды — растягиваем кучку
    из 3+ «мгновенных» слов до начала следующего слова пропорционально длине."""
    i = 0
    while i < len(words):
        j = i
        while j < len(words) and words[j]["end"] - words[j]["start"] < 0.1:
            j += 1
        if j - i >= 3:
            a = words[i]["start"]
            if j < len(words):          # хвост кучки обычно «съел» следующее слово — делим и его
                b = words[j]["end"]
                j += 1
            else:
                b = words[j - 1]["end"] + 0.3 * (j - i)
            lens = [len(w["w"]) + 2 for w in words[i:j]]
            tot, t = sum(lens), a
            for w, L in zip(words[i:j], lens):
                d = (b - a) * L / tot
                w["start"], w["end"] = round(t, 3), round(t + d * 0.92, 3)
                t += d
            i = j
        else:
            i += 1
    return words


def transcript_text(words):
    """Строки по фразам: [idx] 12.34  текст — режиссёр ставит сцены по этим таймкодам."""
    lines, cur = [], []
    for i, w in enumerate(words):
        cur.append((i, w))
        if w["w"][-1:] in ".!?…" or (i + 1 < len(words) and words[i + 1]["start"] - w["end"] > 0.6):
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    out = []
    for ln in lines:
        i0, w0 = ln[0]
        body = " ".join(f"{w['w']} ·{w['start']:.2f}" for _, w in ln)
        out.append(f"[{i0:03d}] {w0['start']:6.2f}–{ln[-1][1]['end']:6.2f} | {body}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("proj")
    ap.add_argument("--x", type=float, help="центр кадрирования 0..1 для горизонтального видео (по умолч. source.crop_x студии)")
    ap.add_argument("--lang", help="язык речи (по умолч. из studio.json)")
    a = ap.parse_args()
    st = CM.style()
    lang = a.lang or st.get("language", "ru")
    if a.x is None:
        a.x = float(st.get("source", {}).get("crop_x", 0.5))
    ava, proj = a.video, a.proj
    pub = os.path.join(proj, "public")
    os.makedirs(pub, exist_ok=True)
    vid = os.path.join(pub, "input-video.mp4")
    w, h = CM.video_size(ava)
    if w / h > 0.6:                                 # не вертикальное → вырезаем 9:16 вокруг спикера
        cw = int(h * 9 / 16) // 2 * 2
        x = int(max(0, min(w - cw, a.x * w - cw / 2)))
        vf = f"crop={cw}:{h}:{x}:0,scale=1080:1920:flags=lanczos,setsar=1"
        print(f"видео {w}×{h} → кадрирую 9:16 (центр x={a.x})")
    else:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1"
    # ИИ-аватары часто отдают тихую озвучку (HeyGen ~−42 LUFS), телефоны — разную. Выравниваем до −15 LUFS.
    run(["ffmpeg", "-v", "error", "-y", "-i", ava, "-vf", vf, "-r", "25", "-c:v", "libx264", "-crf", "18", "-g", "25",
         "-keyint_min", "25", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", vid])
    run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", vid, "-frames:v", "1", "-vf", "scale=540:-1",
         os.path.join(proj, "frame.jpg")])
    words = unsquish(apply_glossary(CM.speech_words(vid, os.path.join(proj, ".asr"), lang)))
    json.dump(words, open(os.path.join(proj, "words.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    dur = CM.duration(vid)
    txt = f"# длительность {dur:.2f} c, слов {len(words)}\n" + transcript_text(words)
    open(os.path.join(proj, "transcript.txt"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
