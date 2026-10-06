# -*- coding: utf-8 -*-
"""Финал после рендера: выравнивает громкость готового ролика и делает лёгкую копию для телефона.

  python3 finalize.py videos/<slug>            # output.mp4 → output.mp4 (громкость) + output_web.mp4 (crf 26)

Зачем: рендер иногда отдаёт микс заметно тише голоса (ролик ai-learn-5: −21 LUFS при голосе −15.5),
а в ленте тихий ролик проигрывает соседним. Цель −16 LUFS, пики не выше −1.5 dBTP.
Если ролик уже в коридоре −17…−15 LUFS, громкость не трогаем (видео не перекодируется).
"""
import json, os, re, shutil, subprocess, sys

TARGET, TP, TOL = -16.0, -1.5, 1.0


def measure(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                          f"loudnorm=I={TARGET}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S).group(0))


def main():
    proj = sys.argv[1]
    out = os.path.join(proj, "output.mp4")
    m = measure(out)
    li = float(m["input_i"])
    print(f"громкость рендера: {li:.1f} LUFS, пик {float(m['input_tp']):.1f} dBTP")
    if abs(li - TARGET) > TOL:
        tmp = os.path.join(proj, "output.tmp.mp4")
        g = TARGET - li                                   # усиление + лимитер: пики не выше TP, без «накачки» loudnorm
        af = f"volume={g:.2f}dB,alimiter=limit={10 ** (TP / 20):.3f}:attack=2:release=50:level=false"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-c:v", "copy", "-af", af, "-ar", "48000",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", tmp], check=True)
        shutil.move(tmp, out)
        print(f"→ выровнено: {float(measure(out)['input_i']):.1f} LUFS")
    web = os.path.join(proj, "output_web.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-c:v", "libx264", "-crf", "26", "-preset", "medium",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", web], check=True)
    print(f"→ {web} ({os.path.getsize(web) / 1e6:.1f} МБ)")


if __name__ == "__main__":
    main()
