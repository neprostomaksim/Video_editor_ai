# -*- coding: utf-8 -*-
"""Терминал: команда печатается по буквам, затем вывод строками.

Параметры:
  variant  "zsh" (по умолч.) | "claude" (шапка Claude Code) | "codex"
  title    заголовок окна
  lines    [{"cmd": "npx skills add …"}, {"out": "✓ установлено", "style": "ok|err|dim|lime"}, …]
           у любой строки можно задать "t" (сек) или "w" (индекс слова) — иначе авто-очередь
  heading  (необязательно) крупный заголовок над окном
"""
from core import esc, chars_html

KIND = "terminal"
CSS = """
.s-terminal .wrap{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 54px;gap:34px;}
.s-terminal .head{font-size:64px;}
.s-terminal .win{background:#0E0F11;border-radius:30px;box-shadow:0 30px 80px rgba(0,0,0,.28);overflow:hidden;border:1px solid #23252A;}
.s-terminal .bar{height:70px;display:flex;align-items:center;gap:14px;padding:0 28px;background:#17181B;border-bottom:1px solid #23252A;}
.s-terminal .dot{width:20px;height:20px;border-radius:50%;}
.s-terminal .ttl{margin-left:18px;font-family:'Mono',monospace;font-size:26px;color:#8A8F98;}
.s-terminal .body{padding:34px 36px 40px;font-family:'Mono',monospace;font-size:34px;line-height:1.5;color:#E8E8E3;min-height:360px;}
.s-terminal .ln{white-space:pre-wrap;word-break:break-word;}
.s-terminal .ps{color:#7EE787;font-weight:600;}
.s-terminal .ln.out{opacity:0;color:#C9CDD3;}
.s-terminal .ln.ok{color:#7EE787;} .s-terminal .ln.err{color:#FF7B72;} .s-terminal .ln.dim{color:#6E7681;}
.s-terminal .ln.lime{color:var(--accent);font-weight:800;}
.s-terminal .cc{border:2px solid #D97757;border-radius:16px;padding:18px 24px;margin-bottom:26px;color:#E8E8E3;font-size:30px;}
.s-terminal .cc b{color:#D97757;}
"""


def render(s, cx):
    v = s.get("variant", "zsh")
    title = s.get("title", {"claude": "claude — ~/project", "codex": "codex — ~/project"}.get(v, "zsh — ~/project"))
    rows = []
    if v == "claude":
        rows.append('<div class="cc"><b>✻</b> Welcome to <b>Claude Code</b></div>')
    for i, ln in enumerate(s.get("lines", [])):
        if "cmd" in ln:
            ps = "&gt;" if v in ("claude", "codex") else "$"
            rows.append(f'<div class="ln cmd" data-i="{i}"><span class="ps">{ps}</span> {chars_html(ln["cmd"])}</div>')
        else:
            st = {"acc": "lime"}.get(ln.get("style", ""), ln.get("style", ""))       # «acc» занят маркером
            rows.append(f'<div class="ln out {esc(st)}" data-i="{i}">{esc(ln.get("out",""))}</div>')
    head = f'<div class="head">{esc(s["heading"])}</div>' if s.get("heading") else ""
    return (f'<div class="wrap">{head}<div class="win"><div class="bar"><span class="dot" style="background:#FF5F57"></span>'
            f'<span class="dot" style="background:#FEBC2E"></span><span class="dot" style="background:#28C840"></span>'
            f'<span class="ttl">{esc(title)}</span></div><div class="body">{"".join(rows)}</div></div></div>')


def animate(s, cx, tl):
    t = cx.t0
    tl.from_(cx.sel(".win"), {"opacity": 0, "y": 40, "scale": .96, "duration": .45, "ease": "power3.out"}, t)
    if s.get("heading"):
        tl.from_(cx.sel(".head"), {"opacity": 0, "y": -20, "duration": .4, "ease": "power3.out"}, t)
    t += 0.45
    for i, ln in enumerate(s.get("lines", [])):
        t = cx.T(ln, t)
        if "cmd" in ln:
            d = min(1.6, max(.35, len(ln["cmd"]) * 0.045))
            tl.type_chars(cx.sel(f'.ln[data-i="{i}"] .ch'), t, d)
            cx.sfx("typing", t, dur=d)
            t += d + 0.25
        else:
            tl.to(cx.sel(f'.ln[data-i="{i}"]'), {"opacity": 1, "duration": .12}, t)
            t += 0.22
