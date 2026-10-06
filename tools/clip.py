# -*- coding: utf-8 -*-
"""Нарезка b-roll вставок (из референса, промо, своих записей экрана) под зону графики.

  python3 clip.py <src.mp4|gif|png> <out.mp4> --ss 29.9 --t 4.8 [--crop x,y,w,h] [--size 1080x1010] [--fit cover|contain]

--crop   область исходника (например графика донора в split: 0,0,720,570) — лицо/субтитры донора
         должны остаться СНАРУЖИ области
--size   1080x1010 для split, 1080x1920 для full
--fit    cover: заполнить с обрезкой краёв (по умолч.), contain: вписать и залить поля цветом --pad,
         blur: вписать по ширине поверх размытой и притемнённой копии себя — для full-screen 1080x1920
--fg-y   (для blur) вертикальный центр картинки 0..1 (по умолч. 0.5; 0.58 — если сверху заголовок)
--blur   x,y,w,h — замазать область ИСХОДНИКА размытием (вшитые субтитры донора поверх интерфейса);
         флаг можно повторять. Сначала пробуй обойти субтитры кадрированием (--crop), blur — когда они на контенте
Выход: h264 25fps, без звука, keyint 25 (точный сик в HyperFrames).
"""
import argparse, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--ss", type=float, required=True)
ap.add_argument("--t", type=float, required=True)
ap.add_argument("--crop")
ap.add_argument("--size", default="1080x1010")
ap.add_argument("--fit", default="cover")
ap.add_argument("--pad", default="0x0B0F1A")
ap.add_argument("--fg-y", type=float, default=0.5)
ap.add_argument("--blur", action="append", default=[])
ap.add_argument("--speed", type=float, default=1.0, help="0.65 = замедлить (растянуть короткий кусок)")
a = ap.parse_args()
W, H = map(int, a.size.split("x"))
IS_IMG = a.src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) or open(a.src, "rb").read(8).startswith(b"\x89PNG")
INP = (["-loop", "1", "-t", str(a.t), "-i", a.src] if IS_IMG else ["-ss", str(a.ss), "-t", str(round(a.t * a.speed, 3)), "-i", a.src])
vf = [f"setpts=PTS/{a.speed}"] if a.speed != 1.0 else []
for k, b in enumerate(a.blur):                      # замазываем до кадрирования, в координатах исходника
    bx, by, bw, bh = map(int, b.split(","))
    vf.append(f"split[m{k}][n{k}];[n{k}]crop={bw}:{bh}:{bx}:{by},gblur=sigma=45,eq=brightness=-0.10:saturation=0.9[z{k}];[m{k}][z{k}]overlay={bx}:{by}")
if a.crop:
    x, y, w, h = map(int, a.crop.split(","))
    vf.append(f"crop={w}:{h}:{x}:{y}")
if a.fit == "blur":
    pre = ",".join(vf) + "," if vf else ""
    fc = (f"[0:v]{pre}split[a][b];"
          f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:4,eq=brightness=-0.12:saturation=1.1[bg];"
          f"[b]scale={W - 60}:-2:flags=lanczos[fg];"
          f"[bg][fg]overlay=(W-w)/2:(H-h)*{a.fg_y},fps=25,setsar=1[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *INP, "-an",
                    "-filter_complex", fc, "-map", "[v]", "-t", str(a.t), "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                    "-g", "25", "-keyint_min", "25", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], check=True)
    print("→", a.out)
    raise SystemExit
if a.fit == "cover":
    vf.append(f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}")
else:
    vf.append(f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={a.pad}")
vf.append("fps=25,setsar=1")
subprocess.run(["ffmpeg", "-v", "error", "-y", *INP, "-an",
                "-vf", ",".join(vf), "-t", str(a.t), "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-g", "25",
                "-keyint_min", "25", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], check=True)
print("→", a.out)
