# -*- coding: utf-8 -*-
"""Лого-стинг поверх полного аватара (layout overlay): когда звучит «открой ChatGPT / зайди в Claude».

Параметры:
  logo   имя логотипа
  name   подпись (по умолч. имя бренда)
  pos    "top" (по умолч.) | "center"
"""
from core import esc

KIND = "sting"
DEFAULT_LAYOUT = "overlay"
CSS = """
.s-sting .st{position:absolute;left:0;right:0;display:flex;flex-direction:column;align-items:center;gap:18px;}
.s-sting .nm{font-weight:800;font-size:64px;color:#fff;text-shadow:0 4px 20px rgba(0,0,0,.7);}
.s-sting .logo{box-shadow:0 20px 60px rgba(0,0,0,.45);}
"""


def render(s, cx):
    top = 190 if s.get("pos", "top") == "top" else 640
    return (f'<div class="st" style="top:{top}px">{cx.logo(s["logo"], 220)}'
            f'<div class="nm">{esc(s.get("name", s["logo"]))}</div></div>')


def animate(s, cx, tl):
    tl.fromTo(cx.sel(".logo"), {"opacity": 0, "scale": .3, "rotation": -12},
              {"opacity": 1, "scale": 1, "rotation": 0, "duration": .5, "ease": "back.out(2)"}, cx.t0)
    tl.from_(cx.sel(".nm"), {"opacity": 0, "y": 20, "duration": .35, "ease": "power3.out"}, cx.t0 + .2)
    tl.to(cx.sel(".st"), {"opacity": 0, "scale": .9, "duration": .25, "ease": "power2.in"}, cx.t1 - .25)
