# -*- coding: utf-8 -*-
"""Список, который собирается по пунктам (4 правила, 7 скиллов, «офферы / хуки / призывы»).

Параметры:
  kicker, heading   заголовок
  items   [{"text": "Никаких догадок", "icon": "cross", "w": 40}, …]
          icon: "check" | "cross" | "num" | "dot" | имя логотипа («Claude», «ElevenLabs»)
  style   "cards" (по умолч., белые плашки) | "plain"
"""
from core import esc, words_html

KIND = "list"
CSS = """
.s-list .wrap{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 60px;gap:22px;}
.s-list .hd{margin-bottom:14px;}
.s-list .hd .kick{margin-bottom:10px;}
.s-list .it{display:flex;align-items:center;gap:26px;opacity:0;}
.s-list .cards .it{background:var(--card);border:1px solid var(--line);border-radius:26px;padding:24px 30px;box-shadow:0 8px 24px rgba(0,0,0,.05);}
.s-list.bg-dark .cards .it{background:#16161a;border-color:#26262b;}
.s-list .ic{flex:none;width:66px;height:66px;border-radius:18px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:38px;}
.s-list .ic.check{background:var(--accent);color:var(--accent_ink);}
.s-list .ic.cross{background:#FF4D4D;color:#fff;}
.s-list .ic.num{background:var(--ink);color:var(--accent);font-family:'Mono',monospace;}
.s-list.bg-dark .ic.num{background:var(--accent);color:var(--accent_ink);}
.s-list .ic.dot{background:transparent;} .s-list .ic.dot::after{content:'';width:22px;height:22px;border-radius:50%;background:var(--ink);}
.s-list .tx{font-weight:700;font-size:46px;line-height:1.15;}
"""


def render(s, cx):
    hd = ""
    if s.get("heading") or s.get("kicker"):
        hd = (f'<div class="hd"><div class="kick">{esc(s.get("kicker",""))}</div>'
              f'<div class="head">{words_html(s.get("heading",""))}</div></div>')
    rows = []
    for i, it in enumerate(s.get("items", [])):
        it = it if isinstance(it, dict) else {"text": it}
        ic = it.get("icon", "num")
        if ic == "check":
            icon = '<span class="ic check">✓</span>'
        elif ic == "cross":
            icon = '<span class="ic cross">✕</span>'
        elif ic == "num":
            icon = f'<span class="ic num">{i+1}</span>'
        elif ic == "dot":
            icon = '<span class="ic dot"></span>'
        else:
            icon = cx.logo(ic, 66)
        rows.append(f'<div class="it" data-i="{i}">{icon}<span class="tx">{words_html(it["text"])}</span></div>')
    return f'<div class="wrap {esc(s.get("style", "cards"))}">{hd}{"".join(rows)}</div>'


def animate(s, cx, tl):
    t0 = cx.t0
    tl.from_(cx.sel(".hd > *"), {"opacity": 0, "y": -18, "duration": .4, "stagger": .08, "ease": "power3.out"}, t0 + .05)
    items = s.get("items", [])
    step = min(.6, (cx.dur - .6) / max(1, len(items)))
    for i, it in enumerate(items):
        t = cx.T(it if isinstance(it, dict) else {}, t0 + .4 + i * step)
        cx.sfx("click-soft", t)
        tl.fromTo(cx.sel(f'.it[data-i="{i}"]'), {"opacity": 0, "x": -40},
                  {"opacity": 1, "x": 0, "duration": .38, "ease": "power3.out"}, t)
