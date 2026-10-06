# -*- coding: utf-8 -*-
"""GitHub-репозиторий: реальный скрин страницы → наезд камеры на owner/repo → бейдж звёзд со счётчиком.

Параметры:
  repo        "owner/name" (обязательно)
  stars       число (по умолчанию из captures/github/<owner>__<name>.json)
  show_stars  bool (по умолчанию stars >= 2000)
  t_stars     время появления бейджа (по умолчанию 45% сцены)
  stars_label подпись под числом («звёзд на GitHub»)
  desc        описание для карточки-фолбэка (если нет скрина)
Скрин снимает:  node tools/github_capture.mjs owner/name videos/<slug>
"""
import json, os
from core import esc

KIND = "github"
CSS = """
.s-github{background:#0d1117!important;}
.s-github .cam{position:absolute;left:0;top:0;width:1080px;transform-origin:0 0;}
.s-github .cam img{display:block;width:1080px;}
.s-github .hl{position:absolute;border:5px solid var(--accent);border-radius:14px;box-shadow:0 0 0 9999px rgba(0,0,0,.0);opacity:0;}
.s-github .dim{position:absolute;inset:0;background:linear-gradient(180deg,rgba(13,17,23,0) 30%,rgba(13,17,23,.88) 78%);opacity:0;}
.s-github .badge{position:absolute;left:0;right:0;display:flex;flex-direction:column;align-items:center;gap:14px;opacity:0;}
.s-github .badge .pill{font-size:88px;padding:20px 48px;gap:18px;box-shadow:0 20px 50px rgba(0,0,0,.45);}
.s-github .badge .pill .st{font-size:78px;}
.s-github .badge .lbl{font-weight:700;font-size:36px;color:#E6EDF3;letter-spacing:.02em;text-shadow:0 2px 10px rgba(0,0,0,.6);}
/* фолбэк-карточка без скрина */
.s-github .fb{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px;color:#E6EDF3;text-align:center;padding:0 70px;}
.s-github .fb .own{font-weight:600;font-size:44px;color:#8B949E;}
.s-github .fb .nm{font-weight:800;font-size:86px;line-height:1;letter-spacing:-.01em;}
.s-github .fb .ds{font-weight:500;font-size:34px;color:#A9B3BD;line-height:1.3;max-width:900px;}
"""


def _meta(s, cx):
    owner, name = s["repo"].split("/", 1)
    base = os.path.join(cx.b.proj, "captures", "github", f"{owner}__{name}")
    meta = json.load(open(base + ".json")) if os.path.exists(base + ".json") else {}
    shot = base + ".png" if os.path.exists(base + ".png") else None
    return owner, name, meta, shot


def render(s, cx):
    owner, name, meta, shot = _meta(s, cx)
    stars = s.get("stars", meta.get("stars"))
    s["_stars"] = stars
    s["_show"] = s.get("show_stars", bool(stars and stars >= 2000))
    lbl = s.get("stars_label", "звёзд на GitHub")
    badge_top = int(cx.AH * 0.62)
    badge = (f'<div class="badge" style="top:{badge_top}px"><div class="pill"><span class="st">★</span>'
             f'<span class="num">0</span></div><div class="lbl">{esc(lbl)}</div></div>') if s["_show"] else ""
    if shot:
        s["_meta"] = meta
        url = cx.media(shot)
        bb = meta.get("title_bbox")
        k = 1080 / meta.get("vw", 1280)
        hl = ""
        if bb:
            pad = 14
            hl = (f'<div class="hl" style="left:{bb[0]*k-pad:.0f}px;top:{bb[1]*k-pad:.0f}px;'
                  f'width:{bb[2]*k+2*pad:.0f}px;height:{bb[3]*k+2*pad:.0f}px"></div>')
        return f'<div class="cam"><img src="{url}" alt=""/>{hl}</div><div class="dim"></div>{badge}'
    cx.warn(f"нет скрина {s['repo']} — карточка-фолбэк (сними: node tools/github_capture.mjs {s['repo']} <проект>)")
    desc = s.get("desc", meta.get("desc", ""))
    return (f'<div class="fb"><div class="lg">{cx.logo("github", 150)}</div><div class="own">{esc(owner)} /</div>'
            f'<div class="nm">{esc(name)}</div><div class="ds">{esc(desc)}</div></div>{badge}')


def animate(s, cx, tl):
    t0, dur = cx.t0, cx.dur
    t_st = cx.T({"t": s["t_stars"]} if "t_stars" in s else {}, t0 + dur * 0.45)
    meta = s.get("_meta")
    if meta and meta.get("title_bbox"):
        bx, by, bw, bh = meta["title_bbox"]
        k = 1080 / meta.get("vw", 1280)
        cxp, cyp = (bx + bw / 2) * k, (by + bh / 2) * k
        Z = max(1.5, min(3.0, 0.72 * 1080 / (bw * k)))
        ty = cx.AH * (0.30 if s["_show"] else 0.45)
        X, Y = 540 - cxp * Z, ty - cyp * Z
        img_h = meta.get("vh", 1600) * k
        X = min(0, max(1080 - 1080 * Z, X))            # камера не выходит за края скрина
        Y = min(0, max(cx.AH - img_h * Z, Y))
        tl.fromTo(cx.sel(".cam"), {"x": 0, "y": 0, "scale": 1.0},
                  {"x": X, "y": Y, "scale": Z, "duration": 1.25, "ease": "power3.inOut"}, t0 + 0.25)
        tl.to(cx.sel(".hl"), {"opacity": 1, "duration": .3}, t0 + 1.35)
    elif meta:
        tl.fromTo(cx.sel(".cam"), {"scale": 1}, {"scale": 1.12, "duration": dur, "ease": "none"}, t0)
    else:
        tl.from_(cx.sel(".fb > *"), {"opacity": 0, "y": 24, "duration": .45, "stagger": .1, "ease": "power3.out"}, t0 + .1)
    if s["_show"]:
        if meta:
            tl.to(cx.sel(".dim"), {"opacity": 1, "duration": .4}, t_st - 0.1)
        tl.fromTo(cx.sel(".badge"), {"opacity": 0, "y": 40, "scale": .8},
                  {"opacity": 1, "y": 0, "scale": 1, "duration": .5, "ease": "back.out(1.7)"}, t_st)
        cx.sfx("pop", t_st)
        tl.count(cx.sel(".badge .num"), 0, int(s["_stars"]), t_st + 0.05, dur=min(1.4, max(.6, cx.t1 - t_st - .4)))
