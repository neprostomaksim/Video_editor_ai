# -*- coding: utf-8 -*-
"""Сравнение двух сторон: Kimi vs Claude, «было / стало», «результат ≠ ожидал».

Параметры:
  left, right  {"logo": "Kimi", "title": "Kimi K3", "value": "$0.6", "sub": "за 1M токенов"}
  sep          "vs" (по умолч.) | "≠" | "→" | ">" | "<"
  winner       "left" | "right" — подсветка акцентом
  heading      (необязательно) заголовок сверху
  t_right      время появления правой стороны
"""
from core import esc, words_html

KIND = "compare"
CSS = """
.s-compare .wrap{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 44px;gap:40px;}
.s-compare .head{text-align:center;font-size:62px;}
.s-compare .row{display:flex;align-items:stretch;gap:22px;}
.s-compare .side{flex:1;background:var(--card_fill,var(--card));border:var(--card_border,2px solid var(--line));backdrop-filter:var(--card_blur,none);border-radius:30px;padding:36px 26px;display:flex;flex-direction:column;align-items:center;gap:18px;text-align:center;box-shadow:var(--card_shadow,0 12px 30px rgba(0,0,0,.06));}
.s-compare.bg-dark .side{background:#16161a;border-color:#26262b;}
.s-compare .side.win{border-color:var(--ink);box-shadow:0 0 0 6px var(--accent),var(--card_shadow,0 16px 40px rgba(0,0,0,.12));}
.s-compare .ti{font-weight:800;font-size:46px;line-height:1.05;}
.s-compare .va{font-weight:800;font-size:76px;line-height:1;letter-spacing:-.02em;}
.s-compare .sb{font-weight:600;font-size:28px;color:var(--muted);line-height:1.25;}
.s-compare .sep{align-self:center;font-weight:800;font-size:64px;color:var(--ink);flex:none;}
.s-compare.bg-dark .sep{color:#fff;}
"""


def _side(d, cx, cls):
    lg = cx.logo(d["logo"], 150) if d.get("logo") else ""
    parts = [lg]
    if d.get("title"):
        parts.append(f'<div class="ti">{esc(d["title"])}</div>')
    if d.get("value"):
        parts.append(f'<div class="va">{esc(d["value"])}</div>')
    if d.get("sub"):
        parts.append(f'<div class="sb">{words_html(d["sub"])}</div>')
    return f'<div class="side {cls}">{"".join(parts)}</div>'


def render(s, cx):
    w = s.get("winner")
    L = _side(s.get("left", {}), cx, "l" + (" win" if w == "left" else ""))
    R = _side(s.get("right", {}), cx, "r" + (" win" if w == "right" else ""))
    hd = f'<div class="head">{words_html(s["heading"])}</div>' if s.get("heading") else ""
    return f'<div class="wrap">{hd}<div class="row">{L}<div class="sep">{esc(s.get("sep","vs"))}</div>{R}</div></div>'


def animate(s, cx, tl):
    t0 = cx.t0
    tl.from_(cx.sel(".head"), {"opacity": 0, "y": -18, "duration": .4, "ease": "power3.out"}, t0)
    tl.from_(cx.sel(".side.l"), {"opacity": 0, "x": -60, "duration": .45, "ease": "power3.out"}, t0 + .1)
    tr = float(s["t_right"]) if "t_right" in s else t0 + min(1.0, cx.dur * .35)
    tl.from_(cx.sel(".sep"), {"opacity": 0, "scale": .3, "duration": .35, "ease": "back.out(2.4)"}, tr - .15)
    tl.from_(cx.sel(".side.r"), {"opacity": 0, "x": 60, "duration": .45, "ease": "power3.out"}, tr)
    if s.get("winner"):
        tl.from_(cx.sel(".side.win"), {"scale": .94, "duration": .4, "ease": "back.out(2)"}, tr + .5)
