# -*- coding: utf-8 -*-
"""Свободная сцена — уникальная метафора под сценарий (капча «проверка пройдена», полоса лимита,
стикер-записка, переключатель моделей…). Пишется прямо в раскладке.

Параметры:
  html   разметка (можно использовать .logo через {{logo:Claude:120}})
  css    стили — ОБЯЗАТЕЛЬНО с префиксом [data-scene="<id>"] или .s-html-<id>
  js     анимация; доступны: tl (GSAP-таймлайн), S(sel) — селектор внутри сцены,
         t0/t1 — начало/конец сцены (глобальные секунды). Никакого Math.random/Date.
Правила: только цвета/шрифты темы (var(--accent), var(--ink), 'Head', 'Body', 'Mono'), одна идея, ≤ 3–4 элемента.
Карточки — в виде студии: background:var(--card_fill,var(--card)); border:var(--card_border,1px solid var(--line));
box-shadow:var(--card_shadow,<своя тень>); backdrop-filter:var(--card_blur,none). Появления — через tl с ease
back.out/power*.out, как в сценах (характер движения студии к ним в js не применяется — держи его сам: studio motion.feel).
Удачную свободную сцену — выносить в отдельный модуль библиотеки.
"""
import re
from core import js

KIND = "html"
CSS = ""


def render(s, cx):
    h = s.get("html", "")
    h = re.sub(r"\{\{logo:([^:}]+)(?::(\d+))?\}\}",
               lambda m: cx.logo(m.group(1), int(m.group(2) or 140)), h)
    css = s.get("css", "")
    return (f"<style>{css}</style>" if css else "") + f'<div class="fill s-html-{cx.id}">{h}</div>'


def animate(s, cx, tl):
    code = s.get("js", "")
    if not code:
        tl.from_(cx.sel(".fill > *"), {"opacity": 0, "y": 30, "duration": .45, "stagger": .1, "ease": "power3.out"}, cx.t0)
        return
    tl.raw("(function(){var t0=%s,t1=%s;function S(x){return %s+' '+x;}\n%s\n})();"
           % (cx.t0, cx.t1, js(cx.sel()), code))
