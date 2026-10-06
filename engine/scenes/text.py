# -*- coding: utf-8 -*-
"""Крупный кинетический текст: «БЕЗ ЛИМИТОВ», «ЛИМИТ CLAUDE», «УЖЕ ЗНАЕТ ТВОЙ КОНТЕКСТ».

Параметры:
  lines   ["почти", "*БЕЗ ЛИМИТОВ*"] — *акцент* = маркер акцентного цвета
  kicker  (необязательно) мелкая строка сверху
  icon    (необязательно) логотип над текстом
  size    кегль (по умолч. 110)
  upper   bool — капсом (по умолч. true)
"""
from core import esc, words_html

KIND = "text"
CSS = """
.s-text .wrap{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;text-align:center;padding:0 60px;}
.s-text .ln{font-family:"Head";font-weight:var(--head_weight);line-height:1.02;letter-spacing:-.02em;}
.s-text .ln .wv{display:inline-block;}
.s-text .up .ln{text-transform:var(--title_case);}
"""


def render(s, cx):
    size = int(s.get("size", 110))
    lines = "".join(f'<div class="ln" style="font-size:{size}px">{words_html(l)}</div>' for l in s.get("lines", []))
    ic = f'<div class="ic">{cx.logo(s["icon"], 170)}</div>' if s.get("icon") else ""
    kk = f'<div class="kick">{esc(s["kicker"])}</div>' if s.get("kicker") else ""
    return f'<div class="wrap {"up" if s.get("upper", True) else ""}">{ic}{kk}{lines}</div>'


def animate(s, cx, tl):
    t0 = cx.t0
    tl.from_(cx.sel(".ic"), {"opacity": 0, "scale": .5, "duration": .45, "ease": "back.out(1.8)"}, t0)
    tl.from_(cx.sel(".kick"), {"opacity": 0, "y": -14, "duration": .3}, t0 + .05)
    tl.from_(cx.sel(".ln .wv"), {"opacity": 0, "y": 50, "scale": .9, "duration": .38, "stagger": .08, "ease": "back.out(1.6)"}, t0 + .1)
