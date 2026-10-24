# -*- coding: utf-8 -*-
"""B-roll видео: запись экрана продукта, промо-кусок, запись GitHub-страницы.

Параметры:
  src          путь в проекте (media/demo.mp4) — mp4 h264
  media_start  с какой секунды исходника начинать (по умолч. 0)
  fit          "cover" | "contain" (по умолч. contain в рамке)
  frame        "none" | "browser" | "card" (по умолч. card)
  url          адрес для frame=browser
  label        (необязательно) плашка-подпись сверху: «авто-зум на каждом клике»; *акцент*
  label_pos    "top" (по умолч.) | "bottom"
Вставки из референса/промо режь заранее: python3 tools/clip.py (кроп без лица и субтитров донора).
<video> с data-start нельзя класть внутрь хоста сцены (у него свой data-start),
поэтому видео живёт в отдельной обёртке top_level и показывается тем же таймлайном.
"""
from core import esc, W, q, words_html

KIND = "video"
CSS = """
.s-video .bgv{position:absolute;inset:0;background:radial-gradient(120% 80% at 50% 30%,#2a2a30 0%,#0b0b0c 70%);}
.broll .frm{position:absolute;border-radius:28px;overflow:hidden;background:#000;box-shadow:0 30px 80px rgba(0,0,0,.35);display:flex;flex-direction:column;}
.broll .brbar{height:60px;flex:none;display:flex;align-items:center;gap:12px;padding:0 22px;background:#EDEDED;}
.broll .brbar i{width:16px;height:16px;border-radius:50%;display:block;}
.broll .brbar .u{margin-left:14px;flex:1;height:36px;border-radius:12px;background:#fff;font-family:'Mono',monospace;font-size:22px;color:#555;display:flex;align-items:center;padding:0 16px;}
.broll .frm video{flex:1;min-height:0;width:100%;}
.broll .vlab{position:absolute;left:0;right:0;display:flex;justify-content:center;z-index:2;}
.broll .vlab .pill{font-size:44px;padding:16px 36px;box-shadow:0 14px 40px rgba(0,0,0,.4);}
.broll .vlab .pill .acc{color:var(--accent_ink);}
"""


def render(s, cx):
    return '<div class="bgv"></div>'


def top_level(s, cx):
    url = cx.media(s["src"])
    frame = s.get("frame", "card")
    fit = s.get("fit", "contain" if frame != "none" else "cover")
    AH = cx.AH
    if frame == "none":
        box, fr = (0, cx.TOP, W, AH), ""
    else:
        box = (0, cx.TOP, W, AH)
        fr = "frm"
    bar = ""
    if frame == "browser":
        bar = (f'<div class="brbar"><i style="background:#FF5F57"></i><i style="background:#FEBC2E"></i>'
               f'<i style="background:#28C840"></i><span class="u">{esc(s.get("url",""))}</span></div>')
    vid = (f'<video id="{cx.id}-v" src="{url}" muted playsinline data-start="{cx.t0}" data-duration="{q(cx.dur)}" '
           f'data-media-start="{s.get("media_start", 0)}" data-track-index="2" style="object-fit:{fit};"></video>')
    inner = (f'<div class="frm" style="left:50px;top:60px;width:980px;height:{AH-120}px">{bar}{vid}</div>'
             if fr else vid)
    lab = ""
    if s.get("label"):
        ly = f"top:56px" if s.get("label_pos", "top") == "top" else f"bottom:56px"
        lab = f'<div class="vlab" style="{ly}"><span class="pill">{words_html(s["label"])}</span></div>'
    return (f'<div class="broll" id="{cx.id}-broll" data-broll="{cx.id}" style="left:{box[0]}px;top:{box[1]}px;'
            f'width:{box[2]}px;height:{box[3]}px;visibility:hidden;">{inner}{lab}</div>')


def animate(s, cx, tl):
    b = f"#{cx.id}-broll"
    tl.set(b, {"visibility": "visible"}, cx.t0)
    tl.from_(b + " .frm", {"opacity": 0, "y": 50, "scale": .96, "duration": .45, "ease": "power3.out"}, cx.t0)
    if s.get("label"):
        tl.fromTo(b + " .vlab .pill", {"opacity": 0, "y": -24, "scale": .9},
                  {"opacity": 1, "y": 0, "scale": 1, "duration": .4, "ease": "back.out(1.8)"}, cx.t0 + .15)
    tl.set(b, {"visibility": "hidden"}, cx.t1)
