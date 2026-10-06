# -*- coding: utf-8 -*-
"""Фоновая музыка под темп ролика.

  python3 tools/music.py videos/<slug>                  # авто: темп по речи и монтажу → трек из studio/music/ или каталога HeyGen
  python3 tools/music.py videos/<slug> --style epic     # стиль: funk | epic | electronic (по умолч. — sound.music_style студии)
  python3 music.py videos/<slug> --mood "lo-fi chill"   # своё настроение
  python3 music.py videos/<slug> --file ~/track.mp3     # свой трек (с лицензией)
  python3 music.py videos/<slug> --bpm 112              # задать темп вручную
  python3 music.py some.mp3 --measure                   # только измерить BPM файла

Что делает:
 1. Целевой темп: скорость речи (слов/с) + частота смены сцен из shotlist → 92–128 BPM.
 2. Кандидаты: свои треки клиента из studio/music/ (mp3/wav/m4a — с лицензией!), а если их нет —
    каталог HeyGen (скилл media-use, нужен `heygen auth login --oauth`). Меряет BPM каждого и берёт
    ближайший к цели (половинный/двойной темп тоже считается), не повторяя трек прошлого ролика.
 3. Режет по длине ролика, пропускает тишину в начале, выравнивает громкость до −27 LUFS
    (≈12 дБ под голосом −15), пишет media/music.mp3 и блок "music" в shotlist.json
    (движок включает fade и carve — музыка уступает голосу только в частотах речи).
"""
import argparse, array, json, math, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as CM  # noqa: E402

RESOLVE = next((p for p in (os.path.join(CM.ROOT, ".agents/skills/media-use/scripts/resolve.mjs"),
                            os.path.join(CM.ROOT, ".claude/skills/media-use/scripts/resolve.mjs"),
                            os.path.expanduser("~/.claude/skills/media-use/scripts/resolve.mjs"),
                            os.path.expanduser("~/.agents/skills/media-use/scripts/resolve.mjs"))
                if os.path.exists(p)), None)
OWN = os.path.join(CM.ROOT, "studio", "music")
TARGET_LUFS = -20          # файл; после carve+мягкого дака в миксе ≈ −24 (8–9 дБ под голосом −15)


# ---------- BPM без numpy: огибающая энергии → спектральный поток → автокорреляция ----------
def measure_bpm(path, start=0, dur=45):
    sr = 11025
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path,
                          "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h", raw)
    hop = sr // 100                                   # 100 кадров/с
    env = []
    for i in range(0, len(a) - hop, hop):
        s = 0
        for v in a[i:i + hop]:
            s += v * v
        env.append(math.sqrt(s / hop))
    if len(env) < 400:
        return None
    flux = [max(0.0, env[i] - env[i - 1]) for i in range(1, len(env))]
    m = sum(flux) / len(flux)
    flux = [f - m for f in flux]
    best, best_lag = -1e18, None
    for bpm10 in range(700, 1701, 5):                 # 70.0 … 170.0 BPM, шаг 0.5
        lag = 6000.0 / (bpm10 / 10.0)                 # кадров на удар
        L = int(round(lag))
        acc = 0.0
        for k in (1, 2, 4):                           # усиливаем периодичность на кратных долях
            lk = int(round(lag * k))
            n = len(flux) - lk
            if n <= 0:
                continue
            acc += sum(flux[i] * flux[i + lk] for i in range(0, n, 2)) / n
        if acc > best:
            best, best_lag = acc, L
    return round(6000.0 / best_lag, 1) if best_lag else None


def tempo_distance(bpm, target):
    return min(abs(bpm - target), abs(bpm * 2 - target), abs(bpm / 2 - target))


# ---------- темп ролика ----------
def target_bpm(proj):
    words = json.load(open(os.path.join(proj, "words.json")))
    dur = words[-1]["end"] - words[0]["start"]
    wps = len(words) / max(1, dur)
    cuts = 0
    sp = os.path.join(proj, "shotlist.json")
    if os.path.exists(sp):
        cuts = len(json.load(open(sp)).get("scenes", [])) + len(json.load(open(sp)).get("punches", []))
    cpm = cuts / max(1, dur) * 60
    bpm = 88 + (wps - 2.0) * 18 + cpm * 0.45
    return int(max(92, min(128, round(bpm)))), round(wps, 2), round(cpm, 1)


# Характер трека для поиска в каталоге. Свой стиль студии — sound.music_style / sound.music_mood в studio.json.
STYLES = {
    "funk": {"base": "upbeat funky groove, slap bass, playful brass stabs, fun and catchy",
             "pool": ["funky upbeat groove, {bpm} bpm, slap bass, instrumental, no vocals, fun",
                      "nu-disco funk, {bpm} bpm, groovy bassline, instrumental, energetic and positive",
                      "playful funk pop instrumental, {bpm} bpm, claps and guitar licks, no vocals",
                      "retro funk groove, {bpm} bpm, wah guitar, brass hits, instrumental",
                      "energetic funky house, {bpm} bpm, catchy, no vocals",
                      "cheerful funk beat for short video, {bpm} bpm, bouncy, instrumental",
                      "groovy electro funk, {bpm} bpm, punchy drums, no vocals"],
             "prefer": r"funk|groov|disco|bass|bouncy|playful|catchy|fun", "avoid": r"chill|lo-?fi|ambient|soft|sad|calm"},
    "epic": {"base": "epic cinematic hybrid trailer music, driving percussion, rising energy, heroic",
             "pool": ["epic cinematic percussion, {bpm} bpm, instrumental, driving, no vocals",
                      "hybrid trailer music, {bpm} bpm, powerful drums, rising, no vocals",
                      "epic motivational orchestral beat, {bpm} bpm, instrumental",
                      "cinematic action pulse, {bpm} bpm, big drums, no vocals",
                      "heroic electronic orchestral, {bpm} bpm, energetic, instrumental",
                      "dramatic tech trailer, {bpm} bpm, hits and risers, no vocals"],
             "prefer": r"epic|cinematic|trailer|drum|heroic|powerful|driving|orchestral", "avoid": r"chill|lo-?fi|soft|calm|ambient"},
    "electronic": {"base": "",
             "pool": ["{bpm} bpm, background music for tech explainer, no vocals",
                      "modern minimal electronic groove, {bpm} bpm, instrumental, subtle",
                      "light corporate tech beat, {bpm} bpm, no vocals, optimistic",
                      "soft future bass background, {bpm} bpm, instrumental, airy",
                      "light lo-fi house groove, {bpm} bpm, no vocals, clean",
                      "playful plucky electronic background, {bpm} bpm, instrumental",
                      "smooth chill electronic, {bpm} bpm, background, no vocals, positive",
                      "minimal tech pulse with light percussion, {bpm} bpm, instrumental"],
             "prefer": r"light|subtle|background|soft|chill|minimal", "avoid": r"driving|epic|aggressive|intense|hard"},
}


def mood_for(bpm):
    if bpm < 100:
        return "light chill lo-fi electronic, soft beat, warm"
    if bpm < 115:
        return "light upbeat electronic pop, modern tech, positive"
    return "energetic upbeat electronic, modern tech, driving but light"


def resolve_bgm(proj, intent):
    r = subprocess.run(["node", RESOLVE, "--type", "bgm", "--intent", intent, "--project", proj],
                       capture_output=True, text=True, timeout=240)
    m = re.search(r"resolved \S+ → (\S+)", r.stdout + r.stderr)
    if not m:
        sys.stderr.write((r.stdout + r.stderr)[-600:] + "\n")
        return None
    p = m.group(1)
    return p if os.path.isabs(p) else os.path.join(proj, p)


def first_sound(path):
    out = subprocess.run(["ffmpeg", "-i", path, "-af", "silencedetect=noise=-40dB:d=0.3", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.search(r"silence_start: (-?[\d.]+)\n.*?silence_end: ([\d.]+)", out, re.S)
    if m and float(m.group(1)) <= 0.05:
        return round(float(m.group(2)), 2)
    return 0.0



XF = 1.5   # кроссфейд на стыке повторов, сек


def media_len(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode())


def render_track(src, st, need, out):
    """Вырезает трек с секунды st длиной need. Трек короче ролика (в каталоге HeyGen бывают по 14–30 с)
    зацикливается встык с кроссфейдом — иначе музыка обрывается посреди ролика."""
    seg = media_len(src) - st
    n = 1 if seg >= need else math.ceil((need - XF) / (seg - XF))
    inp, fc, last = [], [], "0:a"
    for i in range(n):
        inp += ["-ss", str(st), "-i", src]
    for i in range(1, n):
        fc.append(f"[{last}][{i}:a]acrossfade=d={XF}:c1=tri:c2=tri[x{i}]")
        last = f"x{i}"
    fc.append(f"[{last}]atrim=0:{need},asetpts=N/SR/TB,loudnorm=I={TARGET_LUFS}:TP=-3:LRA=11[o]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inp, "-filter_complex", ";".join(fc), "-map", "[o]",
                    "-ar", "48000", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k", out], check=True)
    if n > 1:
        print(f"  трек {seg:.0f} с короче ролика — зациклен ×{n} с кроссфейдом {XF} с")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("proj")
    ap.add_argument("--mood")
    snd = CM.style().get("sound", {})
    ap.add_argument("--style", choices=sorted(STYLES), default=snd.get("music_style", "electronic") if snd.get("music_style") in STYLES else "electronic",
                    help="характер трека: funk (весёлый грув), epic (кинематографичный драйв), electronic (лёгкий фон)")
    ap.add_argument("--file")
    ap.add_argument("--bpm", type=int)
    ap.add_argument("--tries", type=int, default=6)
    ap.add_argument("--measure", action="store_true")
    a = ap.parse_args()
    if a.measure:
        print(a.proj, "→", measure_bpm(a.proj), "BPM")
        return
    proj = os.path.abspath(a.proj)
    tb, wps, cpm = target_bpm(proj)
    tb = a.bpm or tb
    print(f"темп ролика: речь {wps} слов/с, монтаж {cpm} склеек/мин → цель ≈ {tb} BPM")
    cands = []
    sty = STYLES[a.style]
    own = sorted(os.path.join(OWN, f) for f in os.listdir(OWN)
                 if f.lower().endswith((".mp3", ".wav", ".m4a", ".aac", ".ogg"))) if os.path.isdir(OWN) else []
    if a.file:
        cands = [os.path.expanduser(a.file)]
    elif own:
        cands = own
        print(f"свои треки студии: {len(own)}")
    elif not RESOLVE:
        raise SystemExit("нет треков: положи музыку в studio/music/ или поставь скиллы HyperFrames (npx hyperframes skills) "
                         "и войди в HeyGen (heygen auth login --oauth) — ролик соберётся и без музыки")
    else:
        base = a.mood or snd.get("music_mood") or (sty["base"] if a.style != "electronic" else mood_for(tb))
        pool = [f"{base}, around {tb} BPM, instrumental, no vocals, background for short video"] + \
               [v.format(bpm=tb) for v in sty["pool"]]
        import hashlib
        h = int(hashlib.md5(os.path.basename(proj).encode()).hexdigest(), 16)
        variants = [pool[0]] + [pool[1 + (h + i * 3) % (len(pool) - 1)] for i in range(a.tries - 1)]
        for v in variants:
            p = resolve_bgm(proj, v)
            if p and p not in cands:
                cands.append(p)
        if not cands:
            raise SystemExit("каталог не ответил: нужен вход `heygen auth login --oauth` или --file трек.mp3")
    desc, tid = {}, {}
    man = os.path.join(proj, ".media", "manifest.jsonl")
    if os.path.exists(man):
        for l in open(man):
            try:
                e = json.loads(l)
                desc[os.path.basename(e["path"])] = e.get("description", "")
                tid[os.path.basename(e["path"])] = (e.get("provenance") or {}).get("track_id", "")
            except Exception:
                pass
    # треки, уже стоящие в других роликах, — со штрафом (разнообразие)
    used = set()
    vids = os.path.dirname(proj)
    for d in os.listdir(vids):
        sp2 = os.path.join(vids, d, "shotlist.json")
        if d != os.path.basename(proj) and os.path.exists(sp2):
            try:
                used.add(json.load(open(sp2)).get("music", {}).get("track_id", ""))
            except Exception:
                pass
    used.discard("")
    vid = os.path.join(proj, "public", "input-video.mp4")
    vdur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", vid]).decode())
    scored = []
    for p in cands:
        st = first_sound(p)
        bpm = measure_bpm(p, start=st)
        d = tempo_distance(bpm, tb) if bpm else 99
        dd = desc.get(os.path.basename(p), "")
        light = bool(re.search(sty["prefer"], dd, re.I))     # «в стиле» — бонус
        heavy = bool(re.search(sty["avoid"], dd, re.I))      # «мимо стиля» — штраф
        reused = tid.get(os.path.basename(p), "") in used
        short = media_len(p) - st < vdur + 1          # короткий трек придётся зацикливать — лёгкий штраф
        d_adj = d - (1.5 if light else 0) + (1.5 if heavy else 0) + (8 if reused else 0) + (3 if short else 0)
        scored.append((d_adj, bpm, st, p))
        print(f"  {os.path.basename(p)}: {bpm} BPM (Δ {d:.1f}){' [уже в другом ролике]' if reused else ''}"
              f"{f' [{media_len(p):.0f} с — короче ролика]' if short else ''} {dd[:60]}")
    scored.sort()
    d, bpm, st, src = scored[0]
    os.makedirs(os.path.join(proj, "media"), exist_ok=True)
    out = os.path.join(proj, "media", "music.mp3")
    render_track(src, st, vdur + 1, out)
    sp = os.path.join(proj, "shotlist.json")
    sh = json.load(open(sp))
    sh["music"] = {"src": "media/music.mp3", "volume": 1.0, "fade_in": 0.3, "fade_out": 1.2, "carve": 0.8,
                   "bpm": bpm, "style": a.style, "source": os.path.basename(src), "track_id": tid.get(os.path.basename(src), "")}
    json.dump(sh, open(sp, "w"), ensure_ascii=False, indent=1)
    print(f"→ media/music.mp3  ({bpm} BPM, {TARGET_LUFS} LUFS) — блок music записан в shotlist.json")


if __name__ == "__main__":
    main()
