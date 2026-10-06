# -*- coding: utf-8 -*-
"""Окно редактора с кодом/файлом (CLAUDE.md, промпт-файл, компонент, конфиг) — для обучающих роликов.
Строки появляются по очереди (или блоками на словах «первое/второе…»), нужная строка подсвечивается.

Параметры:
  file       имя вкладки: "CLAUDE.md", "app/page.tsx", "prompt.txt"
  lines      список строк кода (как есть, с отступами)
  reveal     "lines" (по умолч., построчно) | "all" (сразу всё) | "blocks"
  blocks     для reveal=blocks: [{"from": 0, "to": 2, "w": 41}, …] — диапазоны строк и момент появления
  highlight  [{"line": 3, "w": 45}] — подсветить строку акцентом в момент слова
  heading    (необязательно) заголовок над окном
  editor     "cursor" (по умолч.) | "vscode" — лишь подпись в шапке
  diff       bool — режим диффа: строки с «+» зелёные (добавлено), с «-» красные (удалено), как в git diff
Подсветка простая (комментарии, строки, ключевые слова, markdown-заголовки) — читаемость важнее точности.
"""
import re
from core import esc

KIND = "code"
CSS = """
.s-code .wrap{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 44px;gap:28px;}
.s-code .head{font-size:60px;}
.s-code .ed{background:#141519;border-radius:28px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.3);border:1px solid #26282e;}
.s-code .bar{height:66px;display:flex;align-items:center;gap:12px;padding:0 24px;background:#1b1c21;border-bottom:1px solid #26282e;}
.s-code .dot{width:18px;height:18px;border-radius:50%;}
.s-code .tab{margin-left:18px;height:46px;display:flex;align-items:center;gap:10px;padding:0 20px;border-radius:10px 10px 0 0;
  background:#141519;color:#E6E6E6;font-family:'Mono',monospace;font-size:24px;align-self:flex-end;}
.s-code .tab i{width:12px;height:12px;border-radius:3px;background:var(--accent);display:block;}
.s-code .app{margin-left:auto;font-family:'Mono',monospace;font-size:22px;color:#6b6f78;}
.s-code .body{padding:26px 0 32px;font-family:'Mono',monospace;font-size:31px;line-height:1.55;color:#D4D4D4;}
.s-code .ln{display:flex;opacity:0;position:relative;padding:0 30px 0 0;white-space:pre;}
.s-code .ln .n{width:74px;flex:none;text-align:right;padding-right:22px;color:#4b4f58;}
.s-code .ln .t{white-space:pre-wrap;word-break:break-word;}
.s-code .ln .hl{position:absolute;left:0;right:0;top:0;bottom:0;background:color-mix(in srgb,var(--accent) 16%,transparent);border-left:6px solid var(--accent);opacity:0;}
.s-code .c{color:#6A9955;} .s-code .s{color:#CE9178;} .s-code .k{color:#C586C0;} .s-code .h{color:#4FC1FF;font-weight:700;}
.s-code .b{color:var(--accent);}
.s-code .ln.add{background:rgba(46,160,67,.22);} .s-code .ln.add .t{color:#7EE787;} .s-code .ln.add .n{color:#3FB950;}
.s-code .ln.del{background:rgba(248,81,73,.20);} .s-code .ln.del .t{color:#FFA198;} .s-code .ln.del .n{color:#F85149;}
"""
KW = r"\b(import|from|export|default|const|let|var|function|return|if|else|for|while|class|def|async|await|new|true|false|null|None|True|False)\b"


def _hl(line):
    s = esc(line)
    if re.match(r"^\s*(#|//)", line):                      # комментарий или markdown-заголовок
        return f'<span class="{"h" if line.lstrip().startswith("#") and not line.lstrip().startswith("#!") else "c"}">{s}</span>'
    # строки прячем за метками, чтобы подсветка ключевых слов не лезла внутрь них и в теги
    keep = []
    def stash(m):
        keep.append(m.group(1))
        return f"\x00{len(keep) - 1}\x00"
    s = re.sub(r"(&quot;.*?&quot;|&#x27;.*?&#x27;|`[^`]*`)", stash, s)
    s = re.sub(KW, r'<span class="k">\1</span>', s)
    s = re.sub(r"^(\s*)([-*] )", r'\1<span class="b">\2</span>', s)   # пункты списка в .md
    s = re.sub(r"\x00(\d+)\x00", lambda m: f'<span class="s">{keep[int(m.group(1))]}</span>', s)
    return s


def render(s, cx):
    lines = s.get("lines", [])
    diff = s.get("diff")

    def cls(l):
        return (" add" if l.startswith("+") else " del" if l.startswith("-") else "") if diff else ""
    rows = "".join(f'<div class="ln{cls(l)}" data-i="{i}"><span class="hl"></span><span class="n">{i+1}</span>'
                   f'<span class="t">{(esc(l) if cls(l) else _hl(l)) or "&nbsp;"}</span></div>' for i, l in enumerate(lines))
    head = f'<div class="head">{esc(s["heading"])}</div>' if s.get("heading") else ""
    app = {"vscode": "VS Code"}.get(s.get("editor", "cursor"), "Cursor")
    return (f'<div class="wrap">{head}<div class="ed"><div class="bar"><span class="dot" style="background:#FF5F57"></span>'
            f'<span class="dot" style="background:#FEBC2E"></span><span class="dot" style="background:#28C840"></span>'
            f'<span class="tab"><i></i>{esc(s.get("file","file.md"))}</span><span class="app">{app}</span></div>'
            f'<div class="body">{rows}</div></div></div>')


def animate(s, cx, tl):
    t0 = cx.t0
    tl.from_(cx.sel(".ed"), {"opacity": 0, "y": 40, "scale": .97, "duration": .4, "ease": "power3.out"}, t0)
    if s.get("heading"):
        tl.from_(cx.sel(".head"), {"opacity": 0, "y": -18, "duration": .35, "ease": "power3.out"}, t0)
    n = len(s.get("lines", []))
    mode = s.get("reveal", "lines")
    if mode == "all":
        tl.to(cx.sel(".ln"), {"opacity": 1, "duration": .2}, t0 + .3)
    elif mode == "blocks":
        for b in s.get("blocks", []):
            tb = cx.T(b, t0 + .4)
            for i in range(int(b["from"]), int(b["to"]) + 1):
                tl.fromTo(cx.sel(f'.ln[data-i="{i}"]'), {"opacity": 0, "x": -16},
                          {"opacity": 1, "x": 0, "duration": .22, "ease": "power2.out"}, tb + .06 * (i - int(b["from"])))
            cx.sfx("key-press", tb)
    else:
        step = min(.22, max(.08, (cx.dur * .55) / max(1, n)))
        for i in range(n):
            tl.fromTo(cx.sel(f'.ln[data-i="{i}"]'), {"opacity": 0, "x": -16},
                      {"opacity": 1, "x": 0, "duration": .2, "ease": "power2.out"}, t0 + .4 + i * step)
        cx.sfx("typing", t0 + .4, dur=min(1.5, n * step))
    for h in s.get("highlight", []):
        th = cx.T(h, t0 + cx.dur * .6)
        tl.to(cx.sel(f'.ln[data-i="{int(h["line"]) - 1}"] .hl'), {"opacity": 1, "duration": .25}, th)
