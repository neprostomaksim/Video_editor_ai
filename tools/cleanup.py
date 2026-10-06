# -*- coding: utf-8 -*-
"""Чистка ЖИВОЙ записи говорящей головы перед монтажом: паузы, «э-э», дубли и оговорки.

  python3 tools/cleanup.py raw.mp4 videos/<slug>             # 1. анализ → source/plan.md (читать) + plan.json (править)
  python3 tools/cleanup.py raw.mp4 videos/<slug> --apply     # 2. применить план → source/clean.mp4 + cuts.json
  дальше: python3 tools/transcribe.py videos/<slug>/source/clean.mp4 videos/<slug>

Что находит:
  pause    паузы между словами длиннее --pause (оставляет --keep с каждой стороны) + тишина в начале/конце
  filler   «э», «эм», «ммм»… — вырезаются; «ну», «типа», «короче», «как бы» — только помечаются (apply: false)
  repeat   запинка-повтор: «я хочу я хочу сказать» → первый повтор вырезается
  retake   дубль: следующая фраза начинается так же, как предыдущая (спикер начал заново) → вырезается ранняя
  marker   слово-маркер дубля («стоп», «заново», «ещё раз», «дубль», «переснимаю») → вырезается фраза с маркером
           и неудачная фраза перед ним
Каждый вырез в plan.json можно выключить ("apply": false) или поправить границы; новые — дописать руками
({"start": 12.3, "end": 14.1, "reason": "manual", "apply": true}).

cuts.json — моменты склеек в новом таймлайне. Движок (build.py) на каждой склейке меняет крупность кадра
(jump-cut), чтобы «прыжок» головы выглядел как монтажный приём, а не как брак.
"""
import argparse, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as CM  # noqa: E402

FILL_AUTO = {"э", "ээ", "эээ", "эм", "эмм", "мм", "ммм", "хм", "хмм", "ам", "аа", "ааа", "uh", "um", "umm", "erm", "hmm", "eh"}
FILL_SOFT = {"ну", "типа", "короче", "вот", "значит", "like", "so", "basically"}
FILL_SOFT2 = {("как", "бы"), ("в", "общем"), ("так", "сказать"), ("you", "know")}
MARKERS = {"стоп", "заново", "дубль", "переснимаю", "пересниму", "stop", "retake"}
MARKERS2 = {("ещё", "раз"), ("еще", "раз"), ("давай", "заново"), ("one", "more")}


def nw(w):
    return re.sub(r"[^a-zа-я0-9-]", "", w.lower().replace("ё", "е")).strip("-")


def sentences(words):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 9
        if w["w"][-1:] in ".!?…" or gap > 0.7:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def analyze(raw, proj, a):
    src = os.path.join(proj, "source")
    os.makedirs(src, exist_ok=True)
    lang = a.lang or CM.style().get("language", "ru")
    words = CM.speech_words(raw, os.path.join(src, ".asr"), lang)
    dur = CM.duration(raw)
    json.dump(words, open(os.path.join(src, "raw_words.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    cuts = []

    def cut(s, e, reason, text="", apply=True):
        if e - s >= 0.08:
            cuts.append({"start": round(max(0, s), 2), "end": round(min(dur, e), 2), "reason": reason,
                         "text": text, "apply": apply})

    if not words:
        raise SystemExit("речь не распознана — проверь звук в записи")
    k = a.keep
    # тишина в начале и в конце
    cut(0, words[0]["start"] - k, "pause", "начало")
    cut(words[-1]["end"] + 0.35, dur, "pause", "конец")
    # паузы между словами
    for x, y in zip(words, words[1:]):
        if y["start"] - x["end"] > a.pause:
            cut(x["end"] + k, y["start"] - k, "pause", f"{y['start'] - x['end']:.1f} c")
    # слова-паразиты
    n = [nw(w["w"]) for w in words]
    for i, w in enumerate(words):
        if n[i] in FILL_AUTO:
            cut(w["start"] - 0.03, w["end"] + 0.03, "filler", w["w"])
        elif n[i] in FILL_SOFT or (i + 1 < len(n) and (n[i], n[i + 1]) in FILL_SOFT2):
            cut(w["start"], (words[i + 1] if (i + 1 < len(n) and (n[i], n[i + 1]) in FILL_SOFT2) else w)["end"],
                "filler?", w["w"], apply=False)
    # запинки-повторы 1–3 слов подряд: «я хочу я хочу»
    i = 0
    while i < len(n):
        hit = 0
        for L in (3, 2, 1):
            if i + 2 * L <= len(n) and n[i:i + L] == n[i + L:i + 2 * L] and all(n[i:i + L]) \
                    and (L > 1 or len(n[i]) > 2):
                hit = L
                break
        if hit:
            cut(words[i]["start"] - 0.02, words[i + hit]["start"] - 0.02, "repeat",
                " ".join(w["w"] for w in words[i:i + hit]))
            i += hit
        else:
            i += 1
    # дубли и маркеры
    sents = sentences(words)
    for si, S in enumerate(sents):
        toks = [n[j] for j in S]
        pairs = set(zip(toks, toks[1:]))
        marker = any(t in MARKERS for t in toks) or bool(pairs & MARKERS2)
        text = " ".join(words[j]["w"] for j in S)
        if marker and len(S) <= 6:
            nxt = words[sents[si + 1][0]]["start"] if si + 1 < len(sents) else dur
            prev = sents[si - 1] if si else None
            s0 = words[prev[0]]["start"] if prev else words[S[0]]["start"]
            cut(s0 - 0.05, nxt - a.keep, "marker",
                (" ".join(words[j]["w"] for j in prev) + " | " if prev else "") + text)
            continue
    # дубль: фраза начинается так же (3 слова), как одна из фраз за последние 25 с → спикер начал заново;
    # вырезаем всё от ранней попытки до новой (берём самую раннюю совпавшую — повтор мог начаться с неё)
    floor = 0                     # фразы до floor уже вырезаны как неудачный дубль — с ними не сравниваем
    for sj in range(1, len(sents)):
        T = [n[j] for j in sents[sj]]
        if len(T) < 2:
            continue
        t_new = words[sents[sj][0]]["start"]
        for si in range(floor, sj):
            S = sents[si]
            toks = [n[j] for j in S]
            m = 3 if len(toks) >= 3 and len(T) >= 3 else 2
            if t_new - words[S[0]]["start"] < 25 and len(toks) >= m and toks[:m] == T[:m] and all(toks[:m]):
                text = " ".join(words[j]["w"] for k in range(si, sj) for j in sents[k])
                cut(words[S[0]]["start"] - 0.05, t_new - a.keep, "retake", text)
                floor = sj
                break
    cuts.sort(key=lambda c: c["start"])
    for i, c in enumerate(cuts):
        c["id"] = i + 1
    plan = {"source": os.path.abspath(raw), "duration": round(dur, 2), "keep": a.keep, "cuts": cuts}
    json.dump(plan, open(os.path.join(src, "plan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    on = [c for c in cuts if c["apply"]]
    removed = sum(e - s for s, e in merge([(c["start"], c["end"]) for c in on]))
    md = [f"# План чистки: {os.path.basename(raw)}", "",
          f"Длительность {dur:.1f} c → после чистки ≈ {dur - removed:.1f} c (вырезов: {len(on)}, "
          f"помечено на проверку: {len(cuts) - len(on)}).", "",
          "Выключить вырез: `\"apply\": false` в plan.json. Включить помеченный — `true`. Потом `--apply`.", "",
          "| # | время | причина | что вырезаем | применить |", "|---|---|---|---|---|"]
    for c in cuts:
        if c["reason"] == "pause" and c["end"] - c["start"] < 1.5 and c["text"] not in ("начало", "конец"):
            continue                                   # мелкие паузы не засоряют таблицу
        md.append(f"| {c['id']} | {c['start']:.2f}–{c['end']:.2f} | {c['reason']} | {c['text'][:80]} | "
                  f"{'да' if c['apply'] else 'нет'} |")
    np_ = sum(1 for c in cuts if c["reason"] == "pause" and c["end"] - c["start"] < 1.5)
    md += ["", f"(+ {np_} коротких пауз < 1.5 c — вырезаются автоматически)", "",
           "## Распознанный текст сырой записи", "", " ".join(w["w"] for w in words)]
    open(os.path.join(src, "plan.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md[:3]))
    print(f"→ {os.path.join(src, 'plan.md')}")


def merge(iv):
    out = []
    for s, e in sorted(iv):
        if out and s <= out[-1][1] + 0.25:          # обрывки < 0.25 с между вырезами тоже убираем
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def apply(raw, proj):
    src = os.path.join(proj, "source")
    plan = json.load(open(os.path.join(src, "plan.json"), encoding="utf-8"))
    dur = plan["duration"]
    drops = merge([(c["start"], c["end"]) for c in plan["cuts"] if c.get("apply")])
    keep, cur = [], 0.0
    for s, e in drops:
        if s - cur > 0.06:
            keep.append((cur, s))
        cur = max(cur, e)
    if dur - cur > 0.06:
        keep.append((cur, dur))
    fc, cat = [], ""
    for i, (s, e) in enumerate(keep):
        d = e - s
        f = min(0.01, d / 4)
        fc.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{i}]")
        fc.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={f:.3f},"
                  f"afade=t=out:st={d - f:.3f}:d={f:.3f}[a{i}]")
        cat += f"[v{i}][a{i}]"
    fc.append(f"{cat}concat=n={len(keep)}:v=1:a=1[v][a]")
    script = os.path.join(src, ".filter.txt")
    open(script, "w").write(";\n".join(fc))
    out = os.path.join(src, "clean.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-filter_complex_script", script, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", out], check=True)
    os.remove(script)
    joints, t = [], 0.0
    for s, e in keep[:-1]:
        t += e - s
        joints.append(round(t, 3))
    json.dump(joints, open(os.path.join(proj, "cuts.json"), "w"))
    new = sum(e - s for s, e in keep)
    print(f"→ {out}: {dur:.1f} c → {new:.1f} c, склеек {len(joints)} (cuts.json — для jump-cut наездов)")
    print(f"дальше: python3 tools/transcribe.py {out} {proj}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw"); ap.add_argument("proj")
    ap.add_argument("--apply", action="store_true", help="применить source/plan.json")
    ap.add_argument("--pause", type=float, default=0.45, help="паузы длиннее (с) сжимаются")
    ap.add_argument("--keep", type=float, default=0.12, help="сколько тишины оставить с каждой стороны паузы")
    ap.add_argument("--lang")
    a = ap.parse_args()
    if a.apply:
        apply(a.raw, a.proj)
    else:
        analyze(a.raw, a.proj, a)


if __name__ == "__main__":
    main()
