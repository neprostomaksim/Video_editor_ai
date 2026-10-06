# -*- coding: utf-8 -*-
"""Примерка стиля: собирает 15-секундный демо-ролик в стиле студии и снимает контакт-лист кадров.

  python3 tools/style_preview.py                    # на видео-пробнике студии (studio/sample.mp4), иначе на заглушке
  python3 tools/style_preview.py --video talk.mp4   # на любом видео спикера
  python3 tools/style_preview.py --render           # + отрендерить сам демо-ролик (videos/_style-preview/output.mp4)

Результат: studio/preview.jpg — хук, split-сцена со списком, полноэкранное число, удар на лицо с титулом,
субтитры во всех раскладках, CTA. Показываем клиенту → правим studio/studio.json → запускаем снова.
"""
import argparse, json, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as CM  # noqa: E402

PROJ = os.path.join(CM.ROOT, "videos", "_style-preview")
DEMO = ("Вот как будут выглядеть твои ролики. Сначала хук, потом три главных пункта: первый, второй, третий. "
        "Дальше крупная цифра на весь экран — девяносто процентов. А это удар на лицо, чтобы держать внимание. "
        "И в конце призыв: напиши слово СТИЛЬ в комментарии.")
AT = [1.2, 6.2, 8.9, 10.0, 11.6, 14.2]


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def synth_words(dur=15.0):
    toks = DEMO.split()
    t, step = 0.25, (dur - 0.6) / len(toks)
    out = []
    for w in toks:
        out.append({"w": w, "start": round(t, 3), "end": round(t + step * .85, 3)})
        t += step
    return out


def shotlist(st):
    acc = st["colors"]["accent"]
    return {
        "fps": 25,
        "cta": {"start": 13.4, "word": "СТИЛЬ"},
        "punches": [{"t": 9.4, "scale": 1.14, "dur": 1.2}],
        "scenes": [
            {"kind": "hook", "style": "face", "start": 0, "end": 3.0, "kicker": "ПРИМЕРКА СТИЛЯ",
             "lines": ["твой ролик", "*в твоём стиле*"], "proof": f"акцент {acc}"},
            {"kind": "list", "start": 3.0, "end": 7.0, "kicker": "split-сцена", "heading": "Три главных пункта",
             "items": [{"text": "Первый", "icon": "num", "t": 3.6}, {"text": "Второй", "icon": "num", "t": 4.6},
                       {"text": "Третий — *акцент*", "icon": "check", "t": 5.6}]},
            {"kind": "number", "layout": "full", "start": 7.0, "end": 9.3, "value": 90, "suffix": "%",
             "label": "полноэкранная графика", "sub": "цифра со *счётчиком*"},
            {"kind": "title", "start": 11.0, "end": 13.0, "kicker": "УДАР", "lines": ["держим", "внимание"]},
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    st = CM.style()
    if os.path.isdir(PROJ):
        shutil.rmtree(PROJ)
    os.makedirs(os.path.join(PROJ, "public"))
    src = a.video or (os.path.join(CM.STUDIO, "sample.mp4") if os.path.exists(os.path.join(CM.STUDIO, "sample.mp4")) else None)
    if src:
        x = st.get("source", {}).get("crop_x", 0.5)
        run([sys.executable, os.path.join(CM.ROOT, "tools", "transcribe.py"), src, PROJ, "--x", str(x)],
            stdout=subprocess.DEVNULL)
        words = json.load(open(os.path.join(PROJ, "words.json"), encoding="utf-8"))
        if CM.duration(os.path.join(PROJ, "public", "input-video.mp4")) < 14.5 or len(words) < 10:
            print("пробник короче 15 с или без речи — беру заглушку")
            src = None
    if not src:
        c0, c1 = "0x2B2F3A", "0x6B7280"
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"gradients=s=1080x1920:c0={c0}:c1={c1}:d=15:r=25:speed=0.01",
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "15", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-g", "25", "-c:a", "aac", "-shortest", os.path.join(PROJ, "public", "input-video.mp4")])
        json.dump(synth_words(), open(os.path.join(PROJ, "words.json"), "w", encoding="utf-8"), ensure_ascii=False)
    sh = shotlist(st)
    if not st.get("sound", {}).get("sfx", True):
        sh["sfx"] = {"enabled": False}
    json.dump(sh, open(os.path.join(PROJ, "shotlist.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    run([sys.executable, os.path.join(CM.ROOT, "engine", "build.py"), PROJ, "--duration", "15"])
    pub = os.path.join(PROJ, "public")
    run([os.path.join(CM.ROOT, "hf"), "snapshot", pub, "--at", ",".join(map(str, AT)), "--no-end",
         "--describe", "false"], cwd=PROJ, stdout=subprocess.DEVNULL)
    sheet = os.path.join(pub, "snapshots", "contact-sheet.jpg")
    frames = sorted(f for f in os.listdir(os.path.join(pub, "snapshots")) if f.startswith("frame-"))
    out = os.path.join(CM.STUDIO, "preview.jpg")
    if len(frames) >= 6:                      # своя сетка 3×2 крупнее стандартного контакт-листа
        ins = sum((["-i", os.path.join(pub, "snapshots", f)] for f in frames[:6]), [])
        fc = "".join(f"[{i}:v]scale=432:768[s{i}];" for i in range(6)) + \
             "".join(f"[s{i}]" for i in range(6)) + "xstack=inputs=6:layout=0_0|w0_0|w0+w1_0|0_h0|w0_h0|w0+w1_h0[o]"
        run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[o]", "-q:v", "3", out])
    elif os.path.exists(sheet):
        shutil.copy2(sheet, out)
    print(f"→ {out}  (кадры: хук · список · число · удар · титул · CTA)")
    if a.render:
        run([os.path.join(CM.ROOT, "hf"), "render", pub, "-o", os.path.join(PROJ, "output.mp4"), "--fps", "25"], cwd=PROJ)
        print("→", os.path.join(PROJ, "output.mp4"))


if __name__ == "__main__":
    main()
