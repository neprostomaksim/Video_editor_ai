# -*- coding: utf-8 -*-
"""Ядро движка: стиль клиента, константы кадра, построитель GSAP-таймлайна, общие HTML-кусочки.

Стиль берётся из studio/studio.json (заполняет /setup-studio) поверх engine/defaults.json.
В раскадровке (shotlist.json) любой блок можно переопределить для одного ролика: theme, captions, cta, avatar.

Сцена — модуль в engine/scenes/ с атрибутами:
    KIND   — имя типа ("github", "terminal", …)
    CSS    — стили (префикс .s-<kind>); цвета — только var(--accent), var(--ink) и др. токены, шрифты 'Head'/'Body'/'Mono';
             карточки — var(--card_shadow, <тень>), var(--card_border, <рамка>), var(--card_fill, …), var(--card_blur, none)
             (вид карточек студии, surface_vars). Появления — tl.from_/to/fromTo с ease back.out/power*.out:
             таймлайн сам переводит их в характер движения студии (FEELS)
    render(s, cx) -> str       HTML внутри хоста сцены
    animate(s, cx, tl)         анимация (глобальное время, секунды)
    top_level(s, cx) -> str    (необязательно) HTML вне хоста — для <video> b-roll
"""
import copy, html as _html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS = ROOT                                  # совместимость: ассеты лежат в ROOT/assets
STUDIO = os.path.join(ROOT, "studio")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hf_platform as P     # noqa: E402
P.setup_io()                # UTF-8 в консоли Windows
P.add_bin_to_path()         # ffmpeg из bin/ (кладёт setup.py)
import logos as LOGOS       # noqa: E402


def deep_merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if str(k).startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_style():
    base = json.load(open(os.path.join(ROOT, "engine", "defaults.json"), encoding="utf-8"))
    p = os.path.join(STUDIO, "studio.json")
    if os.path.exists(p):
        base = deep_merge(base, json.load(open(p, encoding="utf-8")))
        base["_configured"] = True
    return base


STYLE = load_style()
W, H = 1080, 1920
SPLIT_H = int(STYLE["layout"].get("split_h", 1010))   # высота зоны графики в split
# порядок split: "graphics_top" — графика сверху, спикер снизу (по умолч.); "speaker_top" — спикер сверху, графика снизу
SPEAKER_TOP = STYLE["layout"].get("split_order", "graphics_top") == "speaker_top"
SPLIT_TOP = H - SPLIT_H if SPEAKER_TOP else 0          # где начинается зона графики в split
SEAM = H - SPLIT_H if SPEAKER_TOP else SPLIT_H         # стык графики и спикера
LOCALE = {"ru": "ru-RU", "en": "en-US", "uk": "uk-UA", "de": "de-DE", "es": "es-ES"}.get(
    STYLE.get("language", "ru"), "ru-RU")


def esc(s):
    return _html.escape(str(s), quote=True)


def js(v):
    return json.dumps(v, ensure_ascii=False)


def q(t, fps=25):
    return round(round(t * fps) / fps, 4)


def color(v, colors):
    """«accent» / «ink» → hex из палитры; любое другое значение — как есть."""
    return colors.get(v, v) if isinstance(v, str) else v


# Характер движения студии (motion.feel): сцены пишут «вылеты» как обычно (back.out — с отскоком, power*.out —
# доезжает), а таймлайн переводит их в характер клиента: (во что превращается back, во что — out, множитель длительности).
FEELS = {
    "bouncy": (None, None, 1.0),                  # как написано в сценах: выпрыгивает и пружинит
    "smooth": ("power3.out", None, 1.0),          # плавно доезжает, без отскока
    "snappy": ("expo.out", "expo.out", .7),       # резко и коротко
    "calm":   ("sine.out", "sine.out", 1.4),      # медленно и спокойно
}
_OUT = re.compile(r"(power\d|expo|circ|sine|quad|cubic|quart)\.out")


class TL:
    """Собирает строки JS для одного paused-таймлайна GSAP.
    motion — блок стиля {"feel": "smooth", "speed": 1.0}: характер появлений (FEELS) и общая скорость.
    Меняется только «как» (ease, длительность вылета ≤ 1 с, stagger), но не «когда»: время на таймлайне то же."""

    def __init__(self, fps=25, motion=None):
        self.lines, self.fps = [], fps
        m = motion or {}
        self.feel = FEELS.get(m.get("feel", "bouncy"), FEELS["bouncy"])
        self.speed = max(.25, float(m.get("speed", 1.0) or 1.0))

    def _t(self, t):
        return q(max(0.0, t), self.fps)

    def _mv(self, v):
        """Перевести одно появление в характер студии."""
        back, out, k = self.feel
        if not isinstance(v, dict) or (back is None and out is None and k == 1.0 and self.speed == 1.0):
            return v
        e = v.get("ease", "power1.out")
        if not isinstance(e, str):
            return v
        if e.startswith("back.out"):
            kind = "back"
        elif _OUT.fullmatch(e):
            kind = "out"
        else:
            return v                                # none / inOut / in — камера, циклы, уходы: не трогаем
        v = dict(v)
        new = back if kind == "back" else out
        if new:
            v["ease"] = new
        f = k / self.speed
        d = v.get("duration")
        if isinstance(d, (int, float)) and d <= 1.0:
            v["duration"] = round(d * f, 3)
        if isinstance(v.get("stagger"), (int, float)):
            v["stagger"] = round(v["stagger"] * f, 3)
        return v

    def raw(self, code):
        self.lines.append(code)

    def set(self, sel, v, t):
        self.raw(f"tl.set({js(sel)},{js(v)},{self._t(t)});")

    def to(self, sel, v, t):
        self.raw(f"tl.to({js(sel)},{js(self._mv(v))},{self._t(t)});")

    def from_(self, sel, v, t):
        self.raw(f"tl.from({js(sel)},{js(self._mv(v))},{self._t(t)});")

    def fromTo(self, sel, a, b, t):
        self.raw(f"tl.fromTo({js(sel)},{js(a)},{js(self._mv(b))},{self._t(t)});")

    def count(self, sel, a, b, t, dur=1.2, decimals=0, prefix="", suffix="", ease="power2.out"):
        """Счётчик числа: 0 → 31 000 (разбивка разрядов по языку студии)."""
        self.raw(
            "(function(){var o={v:%s};tl.to(o,{v:%s,duration:%s,ease:%s,onUpdate:function(){"
            "var e=document.querySelector(%s);if(!e)return;var n=o.v.toLocaleString(%s,"
            "{minimumFractionDigits:%d,maximumFractionDigits:%d});e.textContent=%s+n+%s;}},%s);})();"
            % (a, b, dur, js(ease), js(sel), js(LOCALE), decimals, decimals, js(prefix), js(suffix), self._t(t)))

    def type_chars(self, sel_chars, t, dur):
        """Печать по буквам: у каждого .ch opacity 0→1 со stagger (без курсора)."""
        self.raw(
            "(function(){var n=document.querySelectorAll(%s).length||1;"
            "tl.to(%s,{opacity:1,duration:0.01,stagger:%s/n,ease:'none'},%s);})();"
            % (js(sel_chars), js(sel_chars), round(dur, 3), self._t(t)))

    def js_text(self):
        return "\n".join(self.lines)


def chars_html(text, cls="ch"):
    """Текст → <span class=wd><span class=ch>…</span></span> с пробелами между словами (перенос по словам)."""
    out = []
    for word in str(text).split(" "):
        out.append('<span class="wd">' + "".join(
            f'<span class="{cls}">{esc(c)}</span>' for c in word) + "</span>")
    return " ".join(out)


def words_html(text, cls="wv"):
    """Текст → слова-спаны; *слово* → акцент (маркер цвета accent)."""
    out = []
    for tok in re.findall(r"\*[^*]+\*|\S+", str(text)):
        if tok.startswith("*") and tok.endswith("*"):
            out.append(f'<span class="{cls} acc">{esc(tok[1:-1])}</span>')
        elif "*" in tok:                                  # акцент внутри слова: «авто-*зум*»
            inner = re.sub(r"\*([^*]+)\*", lambda m: f'<span class="acc">{m.group(1)}</span>', esc(tok))
            out.append(f'<span class="{cls}">{inner}</span>')
        else:
            out.append(f'<span class="{cls}">{esc(tok)}</span>')
    return " ".join(out)


class Ctx:
    """Контекст сборки одной сцены."""

    def __init__(self, build, s):
        self.b, self.s = build, s
        self.W = W
        self.AH = SPLIT_H if s.get("layout", "split") == "split" else H
        self.TOP = SPLIT_TOP if s.get("layout", "split") == "split" else 0   # верх зоны графики на странице
        self.t0, self.t1 = s["start"], s["end"]
        self.dur = self.t1 - self.t0
        self.id = s["id"]

    def sel(self, sub=""):
        return f'[data-scene="{self.id}"] {sub}'.strip()

    def T(self, item, default):
        """Время элемента: item.t (сек) или item.w (индекс слова) или default."""
        if isinstance(item, dict):
            if "t" in item:
                return float(item["t"])
            if "w" in item:
                return self.b.words[int(item["w"])]["start"]
        return default

    def logo(self, name, size=160, radius=None, cls=""):
        return self.b.logo_html(name, size, radius, cls)

    def media(self, path):
        return self.b.add_media(path)

    def sfx(self, name, t, vol=None, dur=None):
        """Звуковой акцент из assets/sfx (pop, click-soft, typing, whoosh-short, sparkle…)."""
        self.b.add_sfx(name, t, vol, dur)

    def warn(self, msg):
        self.b.warn(f"[{self.id}:{self.s['kind']}] {msg}")


# ---------------- шрифты ----------------
RANGES = {
    "LAT": "U+0000-00FF,U+0131,U+0152-0153,U+2000-20FF,U+2190-21FF,U+2212,U+2215,U+2116,U+2600-27BF",
    "CYR": "U+0400-04FF,U+0500-052F,U+2116",
}


def font_registry():
    """{family_lower: {name, dir, files: [{file, weight, range}]}} — встроенные + шрифты клиента."""
    reg = {}
    for d in (os.path.join(ROOT, "assets", "fonts"), os.path.join(STUDIO, "fonts")):
        p = os.path.join(d, "fonts.json")
        if os.path.exists(p):
            for fam, files in json.load(open(p, encoding="utf-8")).items():
                reg[fam.lower()] = {"name": fam, "dir": d, "files": files}
    return reg


def font_faces(fonts):
    """@font-face для трёх ролей: 'Head' (заголовки), 'Body' (всё остальное), 'Mono' (код, кодовое слово).
    Возвращает (css, [(src_path, file)], warnings)."""
    reg = font_registry()
    css, files, warns = [], [], []
    for role, key, fallback in (("Head", "head", "montserrat"), ("Body", "body", "montserrat"),
                                ("Mono", "mono", "jetbrains mono")):
        fam = str(fonts.get(key, fallback)).lower()
        if fam not in reg:
            warns.append(f"шрифт «{fonts.get(key)}» не установлен → {fallback} "
                          f"(добавь: python3 tools/fonts.py add \"{fonts.get(key)}\")")
            fam = fallback
        e = reg[fam]
        for f in e["files"]:
            rng = RANGES.get(f.get("range", ""), f.get("range", ""))
            w = f.get("weight", "100 900")
            css.append(f"@font-face{{font-family:'{role}';src:url('fonts/{f['file']}') format('woff2');"
                       f"font-weight:{w};font-display:block;" + (f"unicode-range:{rng};" if rng else "") + "}")
            files.append((os.path.join(e["dir"], f["file"]), f["file"]))
    return "\n".join(css), files, warns


def theme_vars(st):
    """Плоский набор CSS-переменных из стиля: цвета + субтитры + CTA + форма."""
    c = dict(st["colors"])
    cap, cta, fo, sh = st["captions"], st["cta"], st["fonts"], st.get("shape", {})
    v = dict(c)
    v.update({
        "head_weight": fo.get("head_weight", 800),
        "title_case": fo.get("title_case", "uppercase"),
        "radius": f'{sh.get("radius", 18)}px',
        "plate": color(sh.get("plate", "dark"), c),
        "cap_size": f'{cap.get("size", 58)}px',
        "cap_weight": cap.get("weight", 800),
        "cap_case": "uppercase" if cap.get("uppercase") else "none",
        "cap_text": color(cap.get("text", "#FFFFFF"), c),
        "cap_active": color(cap.get("active", "accent"), c),
        "cap_active_ink": color(cap.get("active_ink", "accent_ink"), c),
        "cap_box": color(cap.get("box", "rgba(8,8,9,.92)"), c),
        "cap_radius": f'{cap.get("radius", 18)}px',
        "cap_stroke": color(cap.get("stroke", "#000000"), c),
        "cta_box": color(cta.get("box", "rgba(8,8,9,.94)"), c),
        "cta_text": color(cta.get("text", "#FFFFFF"), c),
        "cta_word": color(cta.get("word_color", "accent"), c),
        "cta_word_font": {"mono": "'Mono',monospace", "head": "'Head',sans-serif"}.get(
            cta.get("word_font", "mono"), "'Mono',monospace"),
        "split_radius": f'{st["layout"].get("split_radius", 44)}px',
    })
    v.update(surface_vars(st.get("surface", {}), c))
    return v


def surface_vars(sf, colors):
    """Вид карточек студии (surface.kind). Сцены пишут var(--card_shadow, <своя тень>) и т.п.: у «shadow» переменные
    не заданы — каждая сцена со своей тенью, как нарисована; остальные виды подменяют тень, рамку, заливку и размытие.
    Интерфейсы сервисов (чат, терминал, код, настройки) переменные не используют — остаются в родном виде."""
    kind = sf.get("kind", "shadow")
    none = "0 0 0 transparent"                    # не «none»: тень бывает в списке вместе с кольцом акцента
    border = f'{int(sf.get("border_width", 2))}px solid {color(sf.get("border_color", "ink"), colors)}'
    out = {
        "shadow": {},
        "flat": {"card_shadow": none},
        "outline": {"card_shadow": none, "card_border": border},
        "glass": {"card_shadow": "0 20px 50px rgba(0,0,0,.14)", "card_border": "1.5px solid rgba(255,255,255,.65)",
                  "card_fill": "rgba(255,255,255,.55)", "card_blur": "blur(18px) saturate(1.4)"},
    }.get(kind, {})
    if sf.get("shadow"):
        out["card_shadow"] = sf["shadow"]
    return out


BASE_CSS = """
*{box-sizing:border-box;}
html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#000;font-family:'Body',system-ui,sans-serif;}
#stage{position:relative;width:100%;height:100%;overflow:hidden;background:#000;}
#video-wrap{position:absolute;overflow:hidden;z-index:1;}
#video-wrap video{width:100%;height:100%;object-fit:cover;object-position:50% 24%;transform-origin:50% 30%;}
.scene{position:absolute;left:0;top:0;overflow:hidden;pointer-events:none;z-index:3;}
.scene.layout-overlay{z-index:4;background:transparent!important;}
.scene .fill{position:absolute;inset:0;}
.bg-light{background:var(--bg);color:var(--ink);}
.bg-dark{background:var(--dark);color:var(--dark_ink);}
.broll{position:absolute;overflow:hidden;z-index:4;}
.broll video{width:100%;height:100%;}
/* логотип-плитка */
.logo{position:relative;display:inline-block;flex:none;border-radius:22.5%;overflow:hidden;background:#fff;
  box-shadow:var(--card_shadow,0 10px 30px rgba(0,0,0,.10),0 2px 6px rgba(0,0,0,.06));}
.logo img{display:block;width:100%;height:100%;object-fit:cover;}
.logo.mark img{object-fit:contain;padding:17%;}
.logo.bare{background:transparent;box-shadow:none;border-radius:0;overflow:visible;filter:drop-shadow(0 14px 30px rgba(0,0,0,.28));}
.logo.bare img{object-fit:contain;}
.logo.letter{display:inline-flex;align-items:center;justify-content:center;background:#111;color:#fff;font-weight:800;}
/* общие элементы графики */
.kick{font-weight:700;font-size:28px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);}
.head{font-family:'Head',sans-serif;font-weight:var(--head_weight);font-size:72px;line-height:1.02;letter-spacing:-.015em;color:var(--ink);}
.bg-dark .head,.bg-dark .kick{color:var(--dark_ink);} .bg-dark .kick{opacity:.6;}
.acc{background:var(--accent);color:var(--accent_ink);border-radius:calc(var(--radius) * .55);padding:0 .14em;box-decoration-break:clone;-webkit-box-decoration-break:clone;}
.pill{display:inline-flex;align-items:center;gap:14px;background:var(--plate);color:var(--accent);border-radius:999px;
  padding:16px 34px;font-weight:800;font-size:44px;}
.wd{white-space:nowrap;}
.ch{opacity:0;}
/* субтитры: стили box | highlight | outline | word */
.cap{position:absolute;left:0;width:1080px;display:flex;justify-content:center;z-index:5;pointer-events:none;}
.cap .box{display:inline-flex;gap:.2em;padding:16px 28px;border-radius:var(--cap_radius);max-width:980px;flex-wrap:wrap;justify-content:center;}
.cap .k{font-weight:var(--cap_weight);font-size:var(--cap_size);line-height:1.1;color:var(--cap_text);text-transform:var(--cap_case);
  border-radius:calc(var(--cap_radius) * .6);padding:0 .1em;}
.cap.st-box .box{background:var(--cap_box);}
.cap.st-highlight .box,.cap.st-outline .box,.cap.st-word .box{background:transparent;}
.cap.st-highlight .k,.cap.st-outline .k,.cap.st-word .k{paint-order:stroke fill;-webkit-text-stroke:.12em var(--cap_stroke);
  text-shadow:0 4px 18px rgba(0,0,0,.55);}
.cap.st-word .k{font-size:calc(var(--cap_size) * 1.45);}
/* CTA */
.cta{position:absolute;left:0;top:1120px;width:1080px;height:560px;display:flex;align-items:center;justify-content:center;z-index:6;}
.cta .cbox{background:var(--cta_box);padding:40px 64px;border-radius:calc(var(--radius) * 1.6);text-align:center;}
.cta .l1{font-weight:600;font-size:54px;color:var(--cta_text);margin-bottom:8px;}
.cta .l2{font-weight:800;font-size:124px;line-height:1;color:var(--cta_word);font-family:var(--cta_word_font);}
.cta .l3{font-weight:600;font-size:38px;color:var(--cta_text);opacity:.8;margin-top:14px;}
"""


def copy_tree(src, dst):
    os.makedirs(dst, exist_ok=True)
    for fn in os.listdir(src):
        if fn.startswith("."):
            continue
        s, d = os.path.join(src, fn), os.path.join(dst, fn)
        if os.path.isfile(s) and (not os.path.exists(d) or os.path.getmtime(s) > os.path.getmtime(d)):
            shutil.copy2(s, d)
