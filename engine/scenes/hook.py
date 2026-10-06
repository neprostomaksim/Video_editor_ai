# -*- coding: utf-8 -*-
"""ХУК — первая сцена ролика. Всё на экране С ПЕРВОГО КАДРА (никаких «появлений» — первый кадр = обложка
и решение «листать или нет»), дальше только лёгкая постоянная анимация: медленный наезд, блик по
акцентной плашке, покачивание логотипа, зачёркивание старой цены.

Стили (style):
  "result" — РЕЗУЛЬТАТ СРАЗУ: демо/результат на весь экран (media, 1080×1920 — clip.py --fit blur),
             заголовок сверху; аватар скрыт, только голос. Самый сильный вариант, когда есть «вау»-кадр.
  "split"  — ДЕМО + ЛИЦО: сверху демо (media, 1080×1010), на нём заголовок; снизу аватар.
  "face"   — ЛИЦО + ДОКАЗАТЕЛЬСТВО: полный аватар, над головой заголовок + доказательство
             (цена «было/стало», звёзды, логотипы «X + Y»). Когда вау-кадра нет.
  "comment"— ОТВЕТ НА КОММЕНТАРИЙ (сильный формат: ответ на реальное возражение аудитории, см. studio/profile.md): полный аватар, сверху
             карточка комментария в стиле Instagram (боль/возражение зрителя) + короткий заголовок-ответ.
Параметры:
  style    см. выше (по умолч. "face"); layout выставь: result → "full", split → "split", face → "overlay"
  media    путь к MP4 в проекте (для result/split) — ДВИЖЕНИЕ С КАДРА 0: запись демо или анимированный макет
           (tools/html_record.mjs). PNG допустим только как крайний случай — статичная картинка в хуке запрещена правилом
  media_start  секунда исходника (по умолч. 0)
  lines    заголовок 1–3 строки, *акцент* = плашка акцентного цвета с бликом. 2–6 слов, конкретная выгода/интрига
  kicker   мелкая строка над заголовком (необязательно)
  logo / logos   логотип(ы) над заголовком (для face; в result/split — мелко или не нужно)
  price    {"old": "$20/мес", "new": "$0"} — старая цена зачёркивается
  proof    плашка-доказательство: «★ 31 000 на GitHub»
  apps     ряд «откуда → куда»: {"from": "ChatGPT", "to": ["Gmail", "YouTube", "Notion"], "more": "+1000"}
           — известные бренды как доказательство (для связок, интеграций, MCP)
  comment  {"name": "Алина", "text": "Все эти ваши нейросети платные!!! ОБМАН", "likes": 102}
           — карточка комментария (для style "comment"; можно и в face). Текст — реальный комментарий
           или типичное возражение базы; имя — реальное (с согласия) или нейтральное
  size     кегль заголовка (по умолч. по длине строки)
  drop     (face/comment) на сколько px опустить аватар, чтобы заголовок не лежал на лице; по умолч. считается
           сам (build.py → avatar_drops, верх головы — avatar.face_top=540); освободившийся верх — размытый кадр
Правила: не логотип неизвестного продукта крупно (зритель не знает бренд — это сигнал рекламы),
а РЕЗУЛЬТАТ или ВЫГОДА. Текст читается за 1 секунду без звука. Верх ~200px и низ ~350px — зона
интерфейса Instagram, туда важное не ставить.
"""
from core import esc, words_html, q, SPLIT_H

KIND = "hook"
DEFAULT_LAYOUT = "overlay"
CSS = """
.s-hook{background:transparent!important;}
.s-hook .shade{position:absolute;left:0;right:0;top:0;}
.s-hook .cm{width:100%;max-width:930px;background:#fff;border-radius:34px;padding:26px 30px;display:flex;gap:22px;
  align-items:flex-start;text-align:left;box-shadow:0 18px 50px rgba(0,0,0,.45);transform:rotate(-1.5deg);}
.s-hook .cm .av{flex:none;width:84px;height:84px;border-radius:50%;background:linear-gradient(135deg,#F58529,#DD2A7B 55%,#8134AF);
  display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:40px;}
.s-hook .cm .bd{flex:1;min-width:0;}
.s-hook .cm .nm{font-weight:800;font-size:30px;color:#111;}
.s-hook .cm .nm small{font-weight:500;font-size:24px;color:#8e8e8e;margin-left:12px;}
.s-hook .cm .tx{margin-top:6px;font-weight:700;font-size:42px;line-height:1.18;color:#111;}
.s-hook .cm .ft{margin-top:12px;font-weight:600;font-size:24px;color:#8e8e8e;display:flex;gap:26px;}
.s-hook .cm .lk{margin-left:auto;font-size:34px;color:#ED4956;align-self:center;text-align:center;line-height:1;}
.s-hook .cm .lk small{display:block;font-size:20px;color:#8e8e8e;font-weight:600;margin-top:4px;}
.s-hook .hk{position:absolute;left:44px;right:44px;display:flex;flex-direction:column;align-items:center;gap:16px;text-align:center;transform-origin:50% 0;}
.s-hook .lgs{display:flex;gap:24px;align-items:center;}
.s-hook .lgs .plus{font-weight:800;font-size:72px;color:#fff;}
.s-hook .kk{font-weight:700;font-size:30px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);text-shadow:0 2px 12px rgba(0,0,0,.7);}
.s-hook .ln{font-family:"Head";font-weight:var(--head_weight);font-size:var(--hs,94px);line-height:1.02;letter-spacing:-.02em;text-transform:var(--title_case);color:#fff;text-shadow:0 6px 28px rgba(0,0,0,.65);}
.s-hook .ln .wv{display:inline-block;}
.s-hook .ln .acc{color:var(--accent_ink);text-shadow:none;padding:0 .14em;margin-top:8px;
  background-image:linear-gradient(100deg,var(--accent) 0%,var(--accent) 40%,color-mix(in srgb,var(--accent) 45%,#fff) 50%,var(--accent) 60%,var(--accent) 100%);
  background-size:300% 100%;background-position:100% 0;}
.s-hook .price{display:flex;align-items:center;gap:26px;margin-top:6px;}
.s-hook .old{position:relative;font-weight:800;font-size:64px;color:#d9d9d4;text-shadow:0 4px 18px rgba(0,0,0,.6);}
.s-hook .old i{position:absolute;left:-6px;right:-6px;top:50%;height:8px;margin-top:-4px;background:#FF4D4D;border-radius:4px;transform-origin:0 50%;}
.s-hook .arr{font-weight:800;font-size:60px;color:#fff;}
.s-hook .new{font-weight:800;font-size:96px;line-height:1;color:var(--accent_ink);background:var(--accent);border-radius:18px;padding:4px 26px;}
.s-hook .proof{margin-top:4px;}
.s-hook .apps{display:flex;align-items:center;gap:14px;margin-top:10px;}
.s-hook .apps .ar{font-weight:800;font-size:54px;color:var(--accent);text-shadow:0 2px 12px rgba(0,0,0,.6);margin:0 4px;}
.s-hook .apps .more{font-size:34px;padding:12px 22px;}
.hookmedia{position:absolute;left:0;top:0;overflow:hidden;z-index:2;}
.hookmedia video,.hookmedia img{width:100%;height:100%;object-fit:cover;display:block;transform-origin:50% 45%;}
"""


def default_layout(s):
    return {"result": "full", "split": "split"}.get(s.get("style", "face"), "overlay")   # face/comment → overlay


def _style(s):
    return s.get("style", "face")



def render(s, cx):
    st = _style(s)
    names = s.get("logos") or ([s["logo"]] if s.get("logo") else [])
    parts = []
    lsize = 190 if len(names) <= 1 else 150
    if st != "face":
        lsize = 120
    for i, n in enumerate(names):
        if i:
            parts.append('<span class="plus">+</span>')
        parts.append(cx.logo(n, lsize))
    lgs = f'<div class="lgs">{"".join(parts)}</div>' if parts else ""
    kk = f'<div class="kk">{esc(s["kicker"])}</div>' if s.get("kicker") else ""
    longest = max([len(l.replace("*", "")) for l in s.get("lines", [])] or [1])
    hs = int(s.get("size", min(100, 1560 // max(10, longest))))
    lines = "".join(f'<div class="ln">{words_html(l)}</div>' for l in s.get("lines", []))
    price = ""
    if s.get("price"):
        p = s["price"]
        price = (f'<div class="price"><span class="old">{esc(p["old"])}<i></i></span>'
                 f'<span class="arr">→</span><span class="new">{esc(p["new"])}</span></div>')
    proof = f'<div class="pill proof">{esc(s["proof"])}</div>' if s.get("proof") else ""
    apps = ""
    if s.get("apps"):
        a = s["apps"]
        tiles = "".join(f'<span class="ap">{cx.logo(n, 96)}</span>' for n in a.get("to", []))
        more = f'<span class="pill more">{esc(a["more"])}</span>' if a.get("more") else ""
        src = f'<span class="ap src">{cx.logo(a["from"], 112)}</span><span class="ar">→</span>' if a.get("from") else ""
        apps = f'<div class="apps">{src}{tiles}{more}</div>'
    cm = ""
    if s.get("comment"):
        c = s["comment"]
        nm = c.get("name", "")
        likes = f'<div class="lk">♥<small>{esc(str(c["likes"]))}</small></div>' if c.get("likes") else ""
        cm = (f'<div class="cm"><div class="av">{esc(nm[:1].upper())}</div><div class="bd">'
              f'<div class="nm">{esc(nm)}<small>{esc(c.get("ago", "2 ч"))}</small></div>'
              f'<div class="tx">{esc(c["text"])}</div><div class="ft"><span>Ответить</span></div></div>{likes}</div>')
    if st in ("face", "comment"):
        top, shade_h, shade_a = 90, 900, .72
    elif st == "result":
        top, shade_h, shade_a = 210, 820, .80
    else:                                   # split: заголовок поверх демо сверху
        top, shade_h, shade_a = 130, 560, .80
    shade = (f'<div class="shade" style="height:{shade_h}px;background:linear-gradient(180deg,'
             f'rgba(0,0,0,{shade_a}) 0%,rgba(0,0,0,{shade_a*.7:.2f}) 55%,rgba(0,0,0,0) 100%)"></div>')
    return f'{shade}<div class="hk" style="top:{top}px;--hs:{hs}px">{cm}{lgs}{kk}{lines}{price}{proof}{apps}</div>'


def top_level(s, cx):
    if not s.get("media") or _style(s) in ("face", "comment"):
        return ""
    url = cx.media(s["media"])
    h = 1920 if _style(s) == "result" else SPLIT_H
    if url.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        el = f'<img src="{url}" alt=""/>'
    else:
        el = (f'<video id="{cx.id}-hv" src="{url}" muted playsinline data-start="{cx.t0}" data-duration="{q(cx.dur)}" '
              f'data-media-start="{s.get("media_start", 0)}" data-track-index="2"></video>')
    vis = "" if cx.t0 < 0.05 else "visibility:hidden;"      # хук в 0 — виден с первого кадра
    return f'<div class="hookmedia" id="{cx.id}-hm" style="width:1080px;height:{h}px;{vis}">{el}</div>'


def animate(s, cx, tl):
    t0, t1, d = cx.t0, cx.t1, cx.dur
    hm = f"#{cx.id}-hm"
    if s.get("media") and _style(s) not in ("face", "comment"):
        tl.set(hm, {"visibility": "visible"}, t0)
        tl.fromTo(hm + " video, " + hm + " img", {"scale": 1.0}, {"scale": 1.07, "duration": d, "ease": "none"}, t0)
        tl.set(hm, {"visibility": "hidden"}, t1)
    # постоянная лёгкая жизнь — без «появлений»
    tl.fromTo(cx.sel(".hk"), {"scale": 1.0}, {"scale": 1.035, "duration": d, "ease": "none"}, t0)
    n_sweep = max(1, int(d // 1.6))
    tl.fromTo(cx.sel(".ln .acc"), {"backgroundPosition": "100% 0"},
              {"backgroundPosition": "-50% 0", "duration": 1.1, "ease": "power1.inOut",
               "repeat": n_sweep - 1, "repeatDelay": .5}, t0 + .25)
    n_float = max(1, int(d // .9))
    tl.fromTo(cx.sel(".lgs .logo"), {"y": 0, "rotation": 0},
              {"y": -10, "rotation": 2, "duration": .9, "ease": "sine.inOut", "yoyo": True,
               "repeat": n_float - 1}, t0)
    if s.get("apps"):
        tl.fromTo(cx.sel(".apps .ap"), {"y": 0}, {"y": -9, "duration": .7, "ease": "sine.inOut", "yoyo": True,
                                                 "repeat": max(1, int(d // .7)) - 1, "stagger": .12}, t0)
        tl.fromTo(cx.sel(".apps .ar"), {"x": 0}, {"x": 8, "duration": .45, "ease": "sine.inOut", "yoyo": True,
                                                 "repeat": max(1, int(d // .45)) - 1}, t0)
    if s.get("price"):
        tl.fromTo(cx.sel(".old i"), {"scaleX": 0}, {"scaleX": 1, "duration": .35, "ease": "power2.out"}, t0 + .55)
        tl.fromTo(cx.sel(".new"), {"scale": 1}, {"scale": 1.08, "duration": .18, "yoyo": True, "repeat": 1,
                                                 "ease": "power2.out"}, t0 + .9)
    if s.get("comment"):                                    # карточка «дышит», сердечко пульсирует
        tl.fromTo(cx.sel(".cm"), {"scale": 1}, {"scale": 1.025, "duration": .8, "ease": "sine.inOut", "yoyo": True,
                                               "repeat": max(1, int(d // .8)) - 1}, t0)
        tl.fromTo(cx.sel(".cm .lk"), {"scale": 1}, {"scale": 1.25, "duration": .22, "yoyo": True, "repeat": 1,
                                                   "ease": "power2.out"}, t0 + .6)
    if s.get("proof"):
        tl.fromTo(cx.sel(".proof"), {"scale": 1}, {"scale": 1.06, "duration": .5, "yoyo": True, "repeat": 1,
                                                   "ease": "sine.inOut"}, t0 + 1.2)
    tl.to(cx.sel(".hk, .shade"), {"opacity": 0, "duration": .18, "ease": "power2.in"}, t1 - .18)
