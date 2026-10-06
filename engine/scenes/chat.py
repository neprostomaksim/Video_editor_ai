# -*- coding: utf-8 -*-
"""Имитация чата Claude / ChatGPT: промпт печатается в поле ввода → отправка → ответ.

Параметры:
  app      "claude" | "chatgpt"
  prompt   текст промпта (по-русски — то, что диктует аватар)
  answer   (необязательно) строка или список строк ответа
  t_send   время отправки (по умолч.: сразу после печати; без answer — не отправляем)
  model    подпись модели ("Sonnet 5" / "ChatGPT 5")
  kicker, heading  (необязательно) заголовок над окном, как «ПРОМПТ 01 / ПОЙМИ МОЮ ЖИЗНЬ»
"""
from core import esc, chars_html, js

KIND = "chat"
CSS = """
.s-chat .wrap{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 50px;gap:26px;}
.s-chat .hd .kick{margin-bottom:8px;}
.s-chat .hd .head{font-size:64px;}
.s-chat .app{border-radius:34px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.14);border:1px solid rgba(0,0,0,.07);display:flex;flex-direction:column;}
.s-chat .top{height:88px;display:flex;align-items:center;gap:16px;padding:0 30px;font-weight:700;font-size:32px;}
.s-chat .top .md{font-weight:600;font-size:28px;opacity:.6;margin-left:auto;}
.s-chat .conv{padding:10px 34px 0;display:flex;flex-direction:column;gap:24px;min-height:120px;}
.s-chat .ub{align-self:flex-end;max-width:86%;border-radius:26px;padding:22px 28px;font-weight:500;font-size:32px;line-height:1.35;opacity:0;}
.s-chat .ans{font-weight:500;font-size:32px;line-height:1.42;display:flex;gap:18px;opacity:0;}
.s-chat .ans .ic{flex:none;}
.s-chat .ans .al{display:block;}
.s-chat .ans .wv{opacity:0;}
.s-chat .think{font-weight:600;font-size:30px;opacity:0;}
.s-chat .inp{margin:26px 26px 28px;border-radius:30px;padding:26px 28px 20px;display:flex;flex-direction:column;gap:22px;}
.s-chat .txt{font-weight:500;font-size:34px;line-height:1.38;min-height:94px;position:relative;}
.s-chat .ph{position:absolute;left:0;top:0;opacity:.45;}
.s-chat .row{display:flex;align-items:center;gap:18px;font-size:30px;font-weight:600;}
.s-chat .send{margin-left:auto;width:62px;height:62px;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:800;}
/* Claude */
.s-chat .claude{background:#F5F4EE;color:#1F1E1D;}
.s-chat .claude .inp{background:#fff;border:1px solid #E3E0D6;box-shadow:0 4px 18px rgba(0,0,0,.05);}
.s-chat .claude .send{background:#D97757;color:#fff;border-radius:16px;}
.s-chat .claude .ub{background:#EAE7DD;align-self:flex-start;}
.s-chat .claude .row .md{color:#6B6860;}
.s-chat .claude .think{color:#D97757;}
/* ChatGPT */
.s-chat .chatgpt{background:#FFFFFF;color:#0D0D0D;}
.s-chat .chatgpt .inp{background:#F4F4F4;border-radius:36px;}
.s-chat .chatgpt .send{background:#0D0D0D;color:#fff;border-radius:50%;}
.s-chat .chatgpt .ub{background:#F4F4F4;}
.s-chat .chatgpt .think{color:#8E8E8E;}
"""


def render(s, cx):
    app = s.get("app", "claude")
    is_c = app == "claude"
    brand = "Claude" if is_c else "ChatGPT"
    model = s.get("model", "Sonnet 5" if is_c else "ChatGPT 5 ▾")
    ph = "Чем могу помочь сегодня?" if is_c else "Спросите что-нибудь"
    hd = ""
    if s.get("heading") or s.get("kicker"):
        hd = (f'<div class="hd"><div class="kick">{esc(s.get("kicker",""))}</div>'
              f'<div class="head">{esc(s.get("heading",""))}</div></div>')
    ans = s.get("answer")
    ans_html = ""
    if ans:
        lines = ans if isinstance(ans, list) else [ans]
        body = "".join('<span class="al">' + " ".join(f'<span class="wv">{esc(w)}</span>' for w in ln.split()) + "</span>"
                       for ln in lines)
        ic = cx.logo("claude", 50) if is_c else cx.logo("chatgpt", 50)
        ans_html = (f'<div class="think">{"✻ Думаю…" if is_c else "● Думаю…"}</div>'
                    f'<div class="ans"><span class="ic">{ic}</span><span>{body}</span></div>')
    top_right = "" if is_c else f'<span class="md">{esc(model)}</span>'
    top_left = cx.logo("claude" if is_c else "chatgpt", 54) + f"<span>{brand}</span>"
    row = (f'<span>＋</span><span class="md">{esc(model) if is_c else ""}</span><span class="send">↑</span>')
    return (f'<div class="wrap">{hd}<div class="app {app}"><div class="top">{top_left}{top_right}</div>'
            f'<div class="conv"><div class="ub">{esc(s["prompt"])}</div>{ans_html}</div>'
            f'<div class="inp"><div class="txt"><span class="ph">{ph}</span><span class="typ">{chars_html(s["prompt"])}</span></div>'
            f'<div class="row">{row}</div></div></div></div>')


def animate(s, cx, tl):
    t0, t1 = cx.t0, cx.t1
    tl.from_(cx.sel(".app"), {"opacity": 0, "y": 40, "scale": .97, "duration": .45, "ease": "power3.out"}, t0)
    if s.get("heading") or s.get("kicker"):
        tl.from_(cx.sel(".hd > *"), {"opacity": 0, "y": -16, "duration": .4, "stagger": .08, "ease": "power3.out"}, t0)
    has_ans = bool(s.get("answer"))
    t_type = t0 + 0.45
    t_send = float(s["t_send"]) if "t_send" in s else None
    budget = ((t_send - 0.25) if t_send else (t1 - 0.3 if not has_ans else t0 + (t1 - t0) * 0.5)) - t_type
    d = max(0.5, min(len(s["prompt"]) * 0.05, budget))
    tl.to(cx.sel(".ph"), {"opacity": 0, "duration": .1}, t_type)
    tl.type_chars(cx.sel(".typ .ch"), t_type, d)
    cx.sfx("typing", t_type, dur=d)
    if not has_ans:
        return
    ts = t_send or (t_type + d + 0.3)
    tl.to(cx.sel(".send"), {"scale": .85, "duration": .08, "yoyo": True, "repeat": 1}, ts)
    tl.to(cx.sel(".typ"), {"opacity": 0, "duration": .15}, ts + .1)
    tl.to(cx.sel(".ph"), {"opacity": 1, "duration": .15}, ts + .2)
    tl.fromTo(cx.sel(".ub"), {"opacity": 0, "y": 30}, {"opacity": 1, "y": 0, "duration": .35, "ease": "power3.out"}, ts + .12)
    tl.to(cx.sel(".think"), {"opacity": 1, "duration": .2}, ts + .45)
    tl.to(cx.sel(".think"), {"opacity": 0, "duration": .15}, ts + 1.0)
    ta = ts + 1.1
    tl.to(cx.sel(".ans"), {"opacity": 1, "duration": .15}, ta - .1)
    da = max(.4, t1 - ta - .3)
    tl.raw("(function(){var e=document.querySelectorAll(%s);var n=e.length||1;"
           "tl.to(e,{opacity:1,duration:.12,stagger:Math.min(.09,%s/n),ease:'none'},%s);})();"
           % (js(cx.sel(".ans .wv")), round(da, 3), round(ta, 3)))
