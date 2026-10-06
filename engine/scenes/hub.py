# -*- coding: utf-8 -*-
"""Хаб интеграций: продукт в центре, вокруг — сервисы, линии дорисовываются к каждому.
(«работает с Claude Code, Codex, Cursor и другими агентами»)

Параметры:
  center   логотип в центре (имя или путь)
  label    (необязательно) подпись под центром
  items    ["Claude Code", "Codex", {"logo": "Cursor", "label": "Cursor", "w": 88}, …]
  labels   bool — подписи под спутниками (по умолч. true)
"""
import math
from core import esc

KIND = "hub"
CSS = """
.s-hub svg{position:absolute;left:0;top:0;}
.s-hub .ln{stroke:#C9C9C1;stroke-width:4;stroke-dasharray:8 10;fill:none;}
.s-hub.bg-dark .ln{stroke:#3a3a3f;}
.s-hub .node{position:absolute;display:flex;flex-direction:column;align-items:center;gap:10px;transform:translate(-50%,-50%);}
.s-hub .node .lbl{font-weight:700;font-size:28px;white-space:nowrap;}
.s-hub .ctr .lbl{font-weight:800;font-size:40px;}
"""


def _items(s):
    out = []
    for it in s.get("items", []):
        out.append(it if isinstance(it, dict) else {"logo": it, "label": it})
    return out


def render(s, cx):
    items = _items(s)
    n = max(1, len(items))
    cxp, cyp = 540, cx.AH * 0.50
    R = min(390, cx.AH * 0.36)
    s["_pos"] = []
    lines, nodes = [], []
    for i, it in enumerate(items):
        a = -math.pi / 2 + 2 * math.pi * i / n
        x, y = cxp + R * math.cos(a), cyp + R * math.sin(a) * 0.92
        s["_pos"].append((x, y))
        L = math.hypot(x - cxp, y - cyp)
        lines.append(f'<line class="ln" data-i="{i}" x1="{cxp:.0f}" y1="{cyp:.0f}" x2="{x:.0f}" y2="{y:.0f}" '
                     f'style="stroke-dashoffset:0"/>')
        lbl = f'<span class="lbl">{esc(it.get("label",""))}</span>' if s.get("labels", True) and it.get("label") else ""
        nodes.append(f'<div class="node sat" data-i="{i}" style="left:{x:.0f}px;top:{y:.0f}px">'
                     f'{cx.logo(it.get("logo"), 130)}{lbl}</div>')
    ctr_lbl = f'<span class="lbl">{esc(s["label"])}</span>' if s.get("label") else ""
    ctr = (f'<div class="node ctr" style="left:{cxp}px;top:{cyp:.0f}px">{cx.logo(s.get("center"), 200)}{ctr_lbl}</div>')
    return (f'<svg width="1080" height="{cx.AH}" viewBox="0 0 1080 {cx.AH}">{"".join(lines)}</svg>'
            f'{"".join(nodes)}{ctr}')


def animate(s, cx, tl):
    items = _items(s)
    t0 = cx.t0
    tl.fromTo(cx.sel(".ctr"), {"opacity": 0, "scale": .5}, {"opacity": 1, "scale": 1, "duration": .5, "ease": "back.out(1.8)"}, t0 + .05)
    step = min(.45, (cx.dur - .9) / max(1, len(items)))
    for i, it in enumerate(items):
        t = cx.T(it, t0 + .5 + i * step)
        tl.fromTo(cx.sel(f'.ln[data-i="{i}"]'), {"opacity": 0}, {"opacity": 1, "duration": .25}, t)
        tl.fromTo(cx.sel(f'.sat[data-i="{i}"]'), {"opacity": 0, "scale": .4},
                  {"opacity": 1, "scale": 1, "duration": .4, "ease": "back.out(2)"}, t + .1)
