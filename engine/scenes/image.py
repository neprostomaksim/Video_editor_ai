# -*- coding: utf-8 -*-
"""Картинка/скриншот (новость, твит, бенчмарк, страница сайта) с медленным наездом.

Параметры:
  src      путь в проекте (captures/…png, media/…jpg)
  fit      "cover" (по умолч.) | "contain" (с размытым фоном)
  frame    "none" | "browser" | "phone" | "card" (по умолч. card при contain)
  zoom     [от, до] — по умолч. [1.0, 1.12]
  focus    [x, y] 0..1 — центр наезда (по умолч. [0.5, 0.35])
  overlay  (необязательно) крупный текст поверх затемнения: «7 МЛРД»; *акцент*
  sub      (необязательно) подпись под overlay
  t_overlay  время overlay
  url      (для frame=browser) адрес в строке браузера
"""
from core import esc, words_html

KIND = "image"
CSS = """
.s-image .bgblur{position:absolute;inset:-40px;background-size:cover;background-position:center;filter:blur(40px) brightness(.85);transform:scale(1.1);}
.s-image .zoom{position:absolute;inset:0;}
.s-image .zoom > img{position:absolute;inset:0;width:100%;height:100%;}
.s-image .box{position:absolute;left:50px;right:50px;top:70px;bottom:70px;display:flex;align-items:center;justify-content:center;}
.s-image .frm{max-width:100%;max-height:100%;border-radius:28px;overflow:hidden;background:#fff;box-shadow:var(--card_shadow,0 30px 80px rgba(0,0,0,.30));display:flex;flex-direction:column;}
.s-image .frm img{display:block;max-width:980px;max-height:100%;object-fit:contain;}
.s-image .frm.phone{border-radius:56px;border:14px solid #111;}
.s-image .brbar{height:64px;flex:none;display:flex;align-items:center;gap:12px;padding:0 22px;background:#EDEDED;}
.s-image .brbar i{width:16px;height:16px;border-radius:50%;display:block;}
.s-image .brbar .u{margin-left:14px;flex:1;height:38px;border-radius:12px;background:#fff;font-family:'Mono',monospace;font-size:22px;color:#555;display:flex;align-items:center;padding:0 16px;}
.s-image .ov{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;text-align:center;padding:0 50px;opacity:0;background:rgba(10,10,12,.74);}
.s-image .ov .big{font-weight:800;font-size:var(--ovs,130px);line-height:1;color:#fff;letter-spacing:-.03em;text-transform:uppercase;}
.s-image .ov .sb{font-weight:700;font-size:46px;color:#fff;}
"""


def render(s, cx):
    url = cx.media(s["src"])
    fit = s.get("fit", "cover")
    frame = s.get("frame", "card" if fit == "contain" else "none")
    ov = ""
    if s.get("overlay"):
        sb = f'<div class="sb">{words_html(s["sub"])}</div>' if s.get("sub") else ""
        size = int(s.get("overlay_size", min(150, 1900 // max(8, len(s["overlay"])))))
        ov = f'<div class="ov" style="--ovs:{size}px"><div class="big">{words_html(s["overlay"])}</div>{sb}</div>'
    fx, fy = s.get("focus", [0.5, 0.35])
    if frame == "none":
        return (f'<div class="zoom" style="transform-origin:{fx*100:.0f}% {fy*100:.0f}%">'
                f'<img src="{url}" style="object-fit:{fit};object-position:{fx*100:.0f}% {fy*100:.0f}%" alt=""/></div>{ov}')
    bar = ""
    if frame == "browser":
        bar = (f'<div class="brbar"><i style="background:#FF5F57"></i><i style="background:#FEBC2E"></i>'
               f'<i style="background:#28C840"></i><span class="u">{esc(s.get("url",""))}</span></div>')
    return (f'<div class="bgblur" style="background-image:url({url})"></div>'
            f'<div class="zoom" style="transform-origin:{fx*100:.0f}% {fy*100:.0f}%"><div class="box">'
            f'<div class="frm {frame}">{bar}<img src="{url}" alt=""/></div></div></div>{ov}')


def animate(s, cx, tl):
    t0 = cx.t0
    z0, z1 = s.get("zoom", [1.0, 1.12])
    tl.fromTo(cx.sel(".zoom"), {"scale": z0}, {"scale": z1, "duration": cx.dur, "ease": "none"}, t0)
    tl.from_(cx.sel(".frm"), {"opacity": 0, "y": 50, "duration": .45, "ease": "power3.out"}, t0)
    if s.get("overlay"):
        to = float(s["t_overlay"]) if "t_overlay" in s else t0 + cx.dur * .35
        tl.to(cx.sel(".ov"), {"opacity": 1, "duration": .3}, to)
        tl.from_(cx.sel(".ov .big .wv"), {"opacity": 0, "y": 40, "duration": .35, "stagger": .07, "ease": "back.out(1.6)"}, to + .05)
        tl.from_(cx.sel(".ov .sb"), {"opacity": 0, "y": 20, "duration": .3}, to + .35)
