# -*- coding: utf-8 -*-
"""Экран настроек сервиса (ChatGPT / Claude): «зайди в настройки → раздел → включи X» или форма
«добавь плагин / коннектор → вставь ссылку». Курсор сам ведёт по шагам, переключатель щёлкает на слове.

Параметры:
  app       "chatgpt" (по умолч.) | "claude"
  title     заголовок окна («Настройки»)
  nav       пункты меню слева: ["Общие", "Плагины", "Безопасность и вход", …]
  active    какой пункт выбрать (имя или индекс); t_nav / w_nav — когда курсор его нажимает
  pane      заголовок правой панели (по умолч. = active)
  rows      строки с переключателями: [{"label": "Режим разработчика", "sub": "…", "on": false, "w": 41}]
            у строки с w/t переключатель щёлкает во «вкл» в этот момент
  form      вместо rows — форма: {"title": "Новый плагин",
                                  "fields": [{"label": "Название", "value": "Composio", "w": 62}, …],
                                  "button": "Создать", "w_button": 68}
Интерфейс — в духе сервиса (его цвета), подписи по-русски, как в озвучке. Реальные URL/ключи не показываем:
секретную часть заменяй на «••••».
"""
from core import esc, chars_html

KIND = "settings"
NAV_H, NAV_TOP = 70, 118          # высота пункта меню и отступ списка от верха окна
CSS = """
.s-settings .wrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:0 40px;}
.s-settings .win{position:relative;width:1010px;height:800px;border-radius:32px;overflow:hidden;display:flex;
  box-shadow:0 30px 90px rgba(0,0,0,.18);border:1px solid rgba(0,0,0,.08);}
.s-settings .nav{width:445px;flex:none;position:relative;}
.s-settings .wt{position:absolute;left:34px;top:36px;font-weight:800;font-size:44px;}
.s-settings .nl{position:absolute;left:14px;right:14px;}
.s-settings .ni{position:relative;z-index:1;height:70px;display:flex;align-items:center;gap:14px;padding:0 18px;
  font-weight:600;font-size:29px;border-radius:16px;white-space:nowrap;overflow:hidden;}
.s-settings .ni i{width:28px;height:28px;border-radius:8px;flex:none;opacity:.5;border:3px solid currentColor;}
.s-settings .hl{position:absolute;left:0;right:0;top:0;height:70px;border-radius:16px;z-index:0;}
.s-settings .pane{flex:1;padding:40px 40px;position:relative;min-width:0;}
.s-settings .pt{font-weight:800;font-size:42px;margin-bottom:22px;padding-bottom:20px;line-height:1.1;}
.s-settings .row{display:flex;align-items:center;gap:24px;padding:22px 0;opacity:0;}
.s-settings .rl{flex:1;}
.s-settings .rl b{display:block;font-weight:700;font-size:33px;line-height:1.15;margin-bottom:6px;}
.s-settings .rl span{display:block;font-weight:500;font-size:25px;line-height:1.3;opacity:.6;}
.s-settings .tg{position:relative;width:92px;height:54px;border-radius:27px;flex:none;}
.s-settings .tg .kn{position:absolute;top:5px;left:5px;width:44px;height:44px;border-radius:50%;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,.25);}
.s-settings .tg .on{position:absolute;inset:0;border-radius:27px;opacity:0;}
.s-settings .fld{margin-bottom:26px;opacity:0;}
.s-settings .fld label{display:block;font-weight:700;font-size:28px;margin-bottom:10px;opacity:.75;}
.s-settings .inp{border-radius:16px;padding:18px 20px;font-weight:600;font-size:32px;min-height:76px;font-family:'Body';}
.s-settings .inp.mono{font-family:'Mono',monospace;font-size:28px;}
.s-settings .btn{display:inline-block;margin-top:8px;border-radius:999px;padding:18px 44px;font-weight:800;font-size:30px;opacity:0;}
.s-settings .win.nonav{width:900px;height:auto;min-height:420px;}
.s-settings .win.nonav .nav{display:none;}
.s-settings .cur{position:absolute;left:0;top:0;width:46px;height:46px;z-index:5;filter:drop-shadow(0 3px 5px rgba(0,0,0,.35));}
/* ChatGPT */
.s-settings .chatgpt{background:#fff;color:#0d0d0d;}
.s-settings .chatgpt .nav{background:#F9F9F9;border-right:1px solid #ECECEC;}
.s-settings .chatgpt .hl{background:#ECECEC;}
.s-settings .chatgpt .pt{border-bottom:1px solid #ECECEC;}
.s-settings .chatgpt .tg{background:#D9D9D9;} .s-settings .chatgpt .tg .on{background:#0d0d0d;}
.s-settings .chatgpt .inp{background:#F4F4F4;border:2px solid #E5E5E5;}
.s-settings .chatgpt .btn{background:#0d0d0d;color:#fff;}
/* Claude */
.s-settings .claude{background:#FAF9F5;color:#1F1E1D;}
.s-settings .claude .nav{background:#F0EEE6;border-right:1px solid #E3E0D6;}
.s-settings .claude .hl{background:#E3E0D6;}
.s-settings .claude .pt{border-bottom:1px solid #E3E0D6;}
.s-settings .claude .tg{background:#D6D3C8;} .s-settings .claude .tg .on{background:#D97757;}
.s-settings .claude .inp{background:#fff;border:2px solid #E3E0D6;}
.s-settings .claude .btn{background:#D97757;color:#fff;}
"""

CURSOR = ('<svg class="cur" viewBox="0 0 24 24"><path d="M4 2l15 11-6.5 1.2L16 21l-3 1.3-3.4-6.8L4 20z" '
          'fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>')


def _active_idx(s):
    nav = s.get("nav", [])
    a = s.get("active", 0)
    return nav.index(a) if isinstance(a, str) and a in nav else (a if isinstance(a, int) else 0)


def render(s, cx):
    app = s.get("app", "chatgpt")
    nav = s.get("nav", [])
    ai = _active_idx(s)
    nav_html = "".join(f'<div class="ni" data-i="{i}"><i></i>{esc(n)}</div>' for i, n in enumerate(nav))
    pane_t = s.get("pane") or (nav[ai] if nav else "")
    body = ""
    if s.get("form"):
        f = s["form"]
        pane_t = f.get("title", pane_t)
        for i, fl in enumerate(f.get("fields", [])):
            mono = " mono" if fl.get("mono", fl.get("value", "").startswith("http")) else ""
            body += (f'<div class="fld" data-i="{i}"><label>{esc(fl["label"])}</label>'
                     f'<div class="inp{mono}">{chars_html(fl.get("value", ""))}</div></div>')
        if f.get("button"):
            body += f'<div class="btn">{esc(f["button"])}</div>'
    else:
        for i, r in enumerate(s.get("rows", [])):
            sub = f'<span>{esc(r["sub"])}</span>' if r.get("sub") else ""
            on = ' style="opacity:1"' if r.get("on") else ""
            kn = ' style="left:43px"' if r.get("on") else ""
            body += (f'<div class="row" data-i="{i}"><div class="rl"><b>{esc(r["label"])}</b>{sub}</div>'
                     f'<div class="tg"><div class="on"{on}></div><div class="kn"{kn}></div></div></div>')
    nn = "" if nav else " nonav"
    return (f'<div class="wrap"><div class="win {app}{nn}"><div class="nav"><div class="wt">{esc(s.get("title","Настройки"))}</div>'
            f'<div class="nl" style="top:{NAV_TOP}px"><div class="hl"></div>{nav_html}</div></div>'
            f'<div class="pane"><div class="pt">{esc(pane_t)}</div>{body}</div>{CURSOR}</div></div>')


def animate(s, cx, tl):
    t0, t1 = cx.t0, cx.t1
    ai = _active_idx(s)
    W0 = 1010                                   # ширина окна; nav 420
    tl.from_(cx.sel(".win"), {"opacity": 0, "y": 40, "scale": .97, "duration": .4, "ease": "power3.out"}, t0)
    t_nav = cx.T({"t": s["t_nav"]} if "t_nav" in s else ({"w": s["w_nav"]} if "w_nav" in s else {}), t0 + .6)
    nav_y = NAV_TOP + ai * NAV_H
    # курсор: старт справа внизу → пункт меню → (переключатель | поля/кнопка)
    tl.set(cx.sel(".cur"), {"x": 820, "y": 640}, t0)
    if s.get("nav"):
        tl.to(cx.sel(".cur"), {"x": 250, "y": nav_y + 24, "duration": .55, "ease": "power2.inOut"}, max(t0 + .1, t_nav - .55))
        tl.to(cx.sel(".hl"), {"y": ai * NAV_H, "duration": .25, "ease": "power2.out"}, t_nav)
        tl.fromTo(cx.sel(".cur"), {"scale": 1}, {"scale": .82, "duration": .08, "yoyo": True, "repeat": 1}, t_nav)
        cx.sfx("click-soft", t_nav)
    t_show = t_nav + .15
    if s.get("form"):
        f = s["form"]
        tl.to(cx.sel(".btn"), {"opacity": 1, "duration": .2}, t_show)
        t = t_show
        for i, fl in enumerate(f.get("fields", [])):
            t = cx.T(fl, t + (.1 if i else 0))
            tl.to(cx.sel(f'.fld[data-i="{i}"]'), {"opacity": 1, "duration": .2}, t_show + .05 * i)
            d = min(1.2, max(.3, len(fl.get("value", "")) * .045))
            fy = 150 + i * 150
            tl.to(cx.sel(".cur"), {"x": 520, "y": fy, "duration": .35, "ease": "power2.inOut"}, max(t_show, t - .35))
            tl.type_chars(cx.sel(f'.fld[data-i="{i}"] .ch'), t, d)
            cx.sfx("typing", t, dur=d)
            t += d
        if f.get("button"):
            tb = cx.T({"w": f["w_button"]} if "w_button" in f else ({"t": f["t_button"]} if "t_button" in f else {}), t + .35)
            by = 150 + len(f.get("fields", [])) * 150 + 20
            tl.to(cx.sel(".cur"), {"x": 470, "y": by, "duration": .35, "ease": "power2.inOut"}, tb - .35)
            tl.fromTo(cx.sel(".btn"), {"scale": 1}, {"scale": .92, "duration": .09, "yoyo": True, "repeat": 1}, tb)
            cx.sfx("click", tb)
    else:
        rows = s.get("rows", [])
        for i, r in enumerate(rows):
            tl.to(cx.sel(f'.row[data-i="{i}"]'), {"opacity": 1, "duration": .25}, t_show + .08 * i)
        for i, r in enumerate(rows):
            if "w" in r or "t" in r:
                ton = cx.T(r, t_show + .8)
                ry = 150 + 26 + i * 120
                tl.to(cx.sel(".cur"), {"x": W0 - 120, "y": ry, "duration": .45, "ease": "power2.inOut"}, max(t_show, ton - .45))
                tl.to(cx.sel(f'.row[data-i="{i}"] .kn'), {"x": 38, "duration": .22, "ease": "power2.out"}, ton)
                tl.to(cx.sel(f'.row[data-i="{i}"] .on'), {"opacity": 1, "duration": .22}, ton)
                cx.sfx("click", ton)
