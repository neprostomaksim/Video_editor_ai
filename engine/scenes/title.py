# -*- coding: utf-8 -*-
"""Мини-титул поверх полного аватара (layout overlay): кикер акцентного цвета + белый жирный заголовок.
Для хука/ключевого тезиса, когда графика не нужна, а подчеркнуть мысль хочется.

Параметры:
  kicker  «ФАКТ», «СЕКРЕТ», «GITHUB»
  lines   ["99%", "НЕ ЗНАЮТ"]
  pos     "top" (по умолч.) | "center"
"""
from core import esc

KIND = "title"
DEFAULT_LAYOUT = "overlay"
CSS = """
.s-title .tt{position:absolute;left:64px;right:64px;display:flex;flex-direction:column;align-items:flex-start;}
.s-title .tt.center{align-items:center;text-align:center;}
.s-title .mk{font-weight:700;font-size:30px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin-bottom:12px;text-shadow:0 2px 12px rgba(0,0,0,.7);}
.s-title .ml{font-family:"Head";font-weight:var(--head_weight);font-size:92px;line-height:1.0;color:#fff;text-shadow:0 4px 20px rgba(0,0,0,.75);text-transform:var(--title_case);}
"""


def render(s, cx):
    pos = s.get("pos", "top")
    top = 150 if pos == "top" else 700
    lines = "".join(f'<span class="ml">{esc(l)}</span>' for l in s.get("lines", []))
    kk = f'<div class="mk">{esc(s["kicker"])}</div>' if s.get("kicker") else ""
    return f'<div class="tt {pos}" style="top:{top}px">{kk}{lines}</div>'


def animate(s, cx, tl):
    tl.from_(cx.sel(".mk"), {"opacity": 0, "x": -30, "duration": .4, "ease": "power3.out"}, cx.t0 + .02)
    tl.from_(cx.sel(".ml"), {"opacity": 0, "y": 28, "duration": .45, "stagger": .09, "ease": "power3.out"}, cx.t0 + .1)
    tl.to(cx.sel(".tt"), {"opacity": 0, "duration": .25, "ease": "power2.in"}, cx.t1 - .25)
