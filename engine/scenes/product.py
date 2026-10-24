# -*- coding: utf-8 -*-
"""Карточка продукта/скилла/MCP: крупный логотип + название + подпись + плашки.

Параметры:
  logo     имя из библиотеки («Claude», «Kimi») или путь к файлу в проекте (media/x.png)
  name     название («Spec Kit», «Kimi K3»)
  tagline  подпись под названием
  chips    ["open-source", "MIT", "Python"] — появляются по очереди
  badge    (необязательно) плашка с текстом акцентного цвета: «×700 быстрее», «★ 60 796»
  t_badge  время появления плашки
"""
from core import esc

KIND = "product"
CSS = """
.s-product .wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:30px;text-align:center;padding:0 60px;}
.s-product .nm{font-weight:800;font-size:108px;line-height:1;letter-spacing:-.02em;}
.s-product .tg{font-weight:500;font-size:38px;line-height:1.3;color:var(--muted);max-width:900px;}
.s-product .chips{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;}
.s-product .chip{border:var(--card_border,2px solid var(--line));background:var(--card_fill,var(--card));backdrop-filter:var(--card_blur,none);border-radius:999px;padding:12px 26px;font-weight:700;font-size:28px;letter-spacing:.04em;text-transform:uppercase;color:#3b3b36;}
.s-product.bg-dark .tg{color:#A6A6A0;} .s-product.bg-dark .chip{background:#17171a;border-color:#2a2a2e;color:#ddd;}
"""


def render(s, cx):
    chips = "".join(f'<span class="chip">{esc(c)}</span>' for c in s.get("chips", []))
    badge = f'<div class="pill badge">{esc(s["badge"])}</div>' if s.get("badge") else ""
    tg = f'<div class="tg">{esc(s["tagline"])}</div>' if s.get("tagline") else ""
    return (f'<div class="wrap"><div class="lg">{cx.logo(s.get("logo", s.get("name")), int(s.get("logo_size", 230)))}</div>'
            f'<div class="nm">{esc(s.get("name",""))}</div>{tg}'
            f'{"<div class=chips>"+chips+"</div>" if chips else ""}{badge}</div>')


def animate(s, cx, tl):
    t = cx.t0
    cx.sfx("pop", t + .05)
    tl.fromTo(cx.sel(".lg"), {"opacity": 0, "scale": .5, "rotation": -8},
              {"opacity": 1, "scale": 1, "rotation": 0, "duration": .55, "ease": "back.out(1.8)"}, t + .05)
    tl.from_(cx.sel(".nm"), {"opacity": 0, "y": 30, "duration": .45, "ease": "power3.out"}, t + .3)
    tl.from_(cx.sel(".tg"), {"opacity": 0, "y": 20, "duration": .4, "ease": "power3.out"}, t + .5)
    tl.from_(cx.sel(".chip"), {"opacity": 0, "y": 16, "scale": .9, "duration": .3, "stagger": .12, "ease": "back.out(2)"}, t + .7)
    if s.get("badge"):
        tb = float(s["t_badge"]) if "t_badge" in s else t + max(1.0, cx.dur * .5)
        tl.fromTo(cx.sel(".badge"), {"opacity": 0, "scale": .6}, {"opacity": 1, "scale": 1, "duration": .45, "ease": "back.out(2)"}, tb)
