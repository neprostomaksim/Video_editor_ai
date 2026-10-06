# -*- coding: utf-8 -*-
"""Большое число: «$0», «7 млрд», «600+», «×700» — со счётчиком.

Параметры:
  value     число для счётчика (31000, 2.8) — ИЛИ text: готовая строка без счёта («2.8T»)
  prefix, suffix   «$», «+», « млрд»
  decimals  знаков после запятой
  label     мелкая строка над числом («Claude Code за»)
  sub       строка под числом («полностью бесплатно») — поддерживает *акцент*
  logo      (необязательно) логотип над числом
  style     "plain" (по умолч.) | "pill" (плашка с акцентным цветом)
"""
from core import esc, words_html

KIND = "number"
CSS = """
.s-number .wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:0 50px;}
.s-number .lb{font-weight:700;font-size:40px;color:var(--muted);letter-spacing:.02em;}
.s-number .big{font-family:"Head";font-weight:var(--head_weight);font-size:250px;line-height:.95;letter-spacing:-.04em;color:var(--ink);white-space:nowrap;}
.s-number.bg-dark .big{color:#fff;}
.s-number .big.pill{font-size:190px;padding:20px 56px;letter-spacing:-.03em;}
.s-number .sb{font-weight:700;font-size:50px;line-height:1.2;max-width:960px;}
"""


def _fmt(v, d):
    s = f"{v:,.{d}f}".replace(",", " ").replace(".", ",")
    return s


def render(s, cx):
    lg = f'<div class="lg">{cx.logo(s["logo"], 150)}</div>' if s.get("logo") else ""
    if "value" in s:
        start = s.get("from", 0)
        txt = f'{esc(s.get("prefix",""))}<span class="n">{_fmt(start, s.get("decimals",0))}</span>{esc(s.get("suffix",""))}'
    else:
        txt = esc(s.get("text", ""))
    cls = "big pill" if s.get("style") == "pill" else "big"
    lb = f'<div class="lb">{esc(s["label"])}</div>' if s.get("label") else ""
    sb = f'<div class="sb">{words_html(s["sub"])}</div>' if s.get("sub") else ""
    return f'<div class="wrap">{lg}{lb}<div class="{cls}">{txt}</div>{sb}</div>'


def animate(s, cx, tl):
    t = cx.t0
    tl.from_(cx.sel(".lg"), {"opacity": 0, "scale": .6, "duration": .45, "ease": "back.out(1.8)"}, t)
    tl.from_(cx.sel(".lb"), {"opacity": 0, "y": -16, "duration": .35, "ease": "power3.out"}, t + .05)
    cx.sfx("pop", t + .1)
    tl.fromTo(cx.sel(".big"), {"opacity": 0, "scale": .7, "y": 30},
              {"opacity": 1, "scale": 1, "y": 0, "duration": .55, "ease": "back.out(1.6)"}, t + .1)
    if "value" in s and s.get("count", True):
        tl.count(cx.sel(".big .n"), s.get("from", 0), s["value"], t + .15,
                 dur=min(1.4, max(.5, cx.dur * .55)), decimals=s.get("decimals", 0))
    tl.from_(cx.sel(".sb .wv"), {"opacity": 0, "y": 18, "duration": .3, "stagger": .07, "ease": "power3.out"}, t + .5)
