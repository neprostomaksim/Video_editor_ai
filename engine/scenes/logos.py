# -*- coding: utf-8 -*-
"""Перечисление брендов: крупно текущий логотип + подпись, внизу копится ряд уже названных.
(«туда входят ChatGPT, Gemini, GLM, Kimi, Mistral, Qwen…»)

Параметры:
  items   [{"logo": "ChatGPT", "label": "ChatGPT", "w": 57}, …]  — w/t = момент, когда бренд звучит
  more    (необязательно) финальная подпись вместо логотипа: «и ещё 600+»
  t_more  время «more»
"""
from core import esc

KIND = "logos"
CSS = """
.s-logos .cur{position:absolute;left:0;right:0;display:flex;flex-direction:column;align-items:center;gap:20px;}
.s-logos .one{position:absolute;left:0;right:0;display:flex;flex-direction:column;align-items:center;gap:20px;opacity:0;}
.s-logos .one .lbl{font-weight:800;font-size:54px;}
.s-logos .row{position:absolute;left:0;right:0;display:flex;justify-content:center;gap:16px;}
.s-logos .row .mi{opacity:0;}
.s-logos .more{position:absolute;left:0;right:0;text-align:center;font-weight:800;font-size:92px;opacity:0;}
"""


def render(s, cx):
    items = s.get("items", [])
    top = int(cx.AH * 0.16) if cx.AH < 1500 else 380
    ones = "".join(
        f'<div class="one" data-i="{i}" style="top:{top}px">{cx.logo(it.get("logo", it.get("label")), 250)}'
        f'<div class="lbl">{esc(it.get("label", it.get("logo","")))}</div></div>' for i, it in enumerate(items))
    mini = int(min(110, (1000 - 16 * max(0, len(items) - 1)) / max(1, len(items))))
    row = "".join(f'<span class="mi" data-i="{i}">{cx.logo(it.get("logo", it.get("label")), mini)}</span>'
                  for i, it in enumerate(items))
    more = f'<div class="more" style="top:{top+90}px">{esc(s["more"])}</div>' if s.get("more") else ""
    row_top = int(cx.AH * 0.74) if cx.AH < 1500 else 1040      # в full — выше субтитров нижней трети
    return f'{ones}{more}<div class="row" style="top:{row_top}px">{row}</div>'


def animate(s, cx, tl):
    items = s.get("items", [])
    n = max(1, len(items))
    step = (cx.dur - 0.3) / (n + (1 if s.get("more") else 0))
    times = [cx.T(it, cx.t0 + 0.1 + i * step) for i, it in enumerate(items)]
    for i, t in enumerate(times):
        one = cx.sel(f'.one[data-i="{i}"]')
        cx.sfx("pop", t, vol=.35)
        tl.fromTo(one, {"opacity": 0, "scale": .6, "y": 20}, {"opacity": 1, "scale": 1, "y": 0, "duration": .32, "ease": "back.out(2)"}, t)
        nxt = times[i + 1] if i + 1 < len(times) else None
        if nxt:
            tl.to(one, {"opacity": 0, "scale": .85, "duration": .15}, max(t + .3, nxt - .12))
        tl.fromTo(cx.sel(f'.mi[data-i="{i}"]'), {"opacity": 0, "y": 20, "scale": .5},
                  {"opacity": 1, "y": 0, "scale": 1, "duration": .3, "ease": "back.out(2)"}, t + .12)
    if s.get("more"):
        tm = float(s["t_more"]) if "t_more" in s else (times[-1] + step if times else cx.t0)
        if times:
            tl.to(cx.sel(f'.one[data-i="{len(items)-1}"]'), {"opacity": 0, "duration": .15}, tm - .12)
        tl.fromTo(cx.sel(".more"), {"opacity": 0, "scale": .7}, {"opacity": 1, "scale": 1, "duration": .4, "ease": "back.out(2)"}, tm)
