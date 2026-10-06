# -*- coding: utf-8 -*-
"""Сборщик ролика: shotlist.json + words.json + studio/studio.json (стиль клиента) → public/index.html

  python3 engine/build.py videos/<slug>

Раскладка аватара выводится из сцен автоматически:
  layout "split"   — графика сверху (0..1010), аватар снизу
  layout "full"    — графика на весь экран, аватар скрыт
  layout "overlay" — графика поверх полного аватара (титулы, лого-стинги)
  нет сцены        — полный аватар
"""
import importlib, json, os, pkgutil, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C  # noqa: E402
from core import W, H, SPLIT_H, esc, js, q  # noqa: E402
import scenes as SC  # noqa: E402

SCENES = {}
for m in pkgutil.iter_modules(SC.__path__):
    mod = importlib.import_module("scenes." + m.name)
    if hasattr(mod, "KIND"):
        SCENES[mod.KIND] = mod


def find_carve():
    """carve.mjs из официальных скиллов HyperFrames (npx hyperframes skills) — ищем в обычных местах установки."""
    for base in (os.path.join(C.ROOT, ".claude", "skills"), os.path.expanduser("~/.claude/skills"),
                 os.path.join(C.ROOT, ".agents", "skills"), os.path.expanduser("~/.agents/skills"),
                 os.path.expanduser("~/.codex/skills"), os.path.expanduser("~/.cursor/skills")):
        p = os.path.join(base, "hyperframes-audio", "scripts", "carve.mjs")
        if os.path.exists(p):
            return p
    return None


class Build:
    def __init__(self, proj, shot="shotlist.json", pub="public", duration=None):
        self.proj = os.path.abspath(proj)
        self.warnings = []
        self.pub = os.path.join(self.proj, pub)
        self.shot = json.load(open(os.path.join(self.proj, shot), encoding="utf-8"))
        if duration:
            self.shot["duration"] = duration
        if pub != "public":                       # вариант: аватар — жёсткой ссылкой, без копии
            os.makedirs(self.pub, exist_ok=True)
            src, dst = os.path.join(self.proj, "public", "input-video.mp4"), os.path.join(self.pub, "input-video.mp4")
            if not os.path.exists(dst):
                os.link(src, dst)
        self.words = json.load(open(os.path.join(self.proj, "words.json"), encoding="utf-8"))
        self.fps = int(self.shot.get("fps", 25))
        sh = self.shot
        self.st = C.deep_merge(C.STYLE, {"colors": sh.get("theme", {}), "captions": sh.get("captions", {}),
                                         "cta": sh.get("cta_style", {}), "source": sh.get("avatar", {})})
        self.theme = self.st["colors"]
        self.av = self.st["source"]
        if not C.STYLE.get("_configured"):
            self.warn("студия не настроена (нет studio/studio.json) — собрано в базовом стиле; запусти /setup-studio")
        self.reg = C.LOGOS.load()
        self.logos_used, self.media_used = set(), {}
        self.sfx_events = []
        snd = self.st.get("sound", {})
        sc = self.shot.get("sfx", {"enabled": snd.get("sfx", True), "volume": snd.get("sfx_volume", 1.0)})
        self.sfx_on = sc.get("enabled", True) if isinstance(sc, dict) else bool(sc)
        self.sfx_vol = float(sc.get("volume", 1.0)) if isinstance(sc, dict) else 1.0
        self.sfx_manifest = json.load(open(os.path.join(C.SYS, "assets", "sfx", "manifest.json")))
        vid = os.path.join(self.pub, "input-video.mp4")
        self.dur = float(self.shot.get("duration") or subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vid]).decode())
        self.dur = round(int(self.dur * self.fps) / self.fps, 4)

    # ---------- ресурсы ----------
    def warn(self, m):
        self.warnings.append(m)

    def logo_html(self, name, size=160, radius=None, cls=""):
        st = f"width:{size}px;height:{size}px;" + (f"border-radius:{radius};" if radius else "")
        if name and os.path.isfile(os.path.join(self.proj, str(name))):      # свой файл в проекте
            url = self.add_media(name)
            return f'<span class="logo {cls}" style="{st}"><img src="{url}" alt=""/></span>'
        slug = C.LOGOS.resolve(str(name or ""), self.reg)
        if not slug:
            self.warn(f"логотип не найден: «{name}» → буквенная плитка (python3 tools/logos.py fetch <slug> или положи PNG в studio/logos/ и `logos.py sync`)")
            letter = esc((str(name or "?").strip() or "?")[0].upper())
            return f'<span class="logo letter {cls}" style="{st}font-size:{int(size*.5)}px">{letter}</span>'
        e = self.reg[slug]
        self.logos_used.add((e.get("_dir", os.path.join(C.ROOT, "assets", "logos")), e["file"]))
        mark = " mark" if e.get("mark_only") else (" bare" if e.get("bare") else "")
        return f'<span class="logo{mark} {cls}" style="{st}"><img src="logos/{e["file"]}" alt=""/></span>'

    def add_media(self, path):
        """Файл из проекта (captures/, media/, …) → копия в public/media/, вернуть URL."""
        src = path if os.path.isabs(path) else os.path.join(self.proj, path)
        if not os.path.isfile(src):
            self.warn(f"нет файла: {path}")
            return "media/missing.png"
        name = os.path.basename(src)
        self.media_used[name] = src
        return "media/" + name

    # громкость подобрана по LUFS файлов: акцент ≈ на 5–6 дБ тише голоса (голос выровнен до −15 LUFS)
    SFX_BASE = {"whoosh-short": .55, "whoosh": .5, "pop": 1.0, "click-soft": 1.0, "click": .8,
                "typing": 1.0, "key-press": 1.0, "sparkle": .3, "riser": .35, "impact-bass-1": .4, "chime": .4}

    def add_sfx(self, name, t, vol=None, dur=None):
        if not self.sfx_on or t < 0 or t >= self.dur - 0.05:
            return
        if any(n == name and abs(tt - t) < 0.25 for n, tt, _, _ in self.sfx_events):
            return
        full = float(self.sfx_manifest[name]["duration"])
        d = min(dur or full, full, self.dur - t)
        v = (vol if vol is not None else self.SFX_BASE.get(name, .4)) * self.sfx_vol
        self.sfx_events.append((name, t, round(v, 3), d))

    # ---------- время ----------
    def resolve_times(self, s):
        wd = self.words
        if "from_w" in s and "start" not in s:
            s["start"] = max(0.0, wd[int(s["from_w"])]["start"] - 0.06)
        if "to_w" in s and "end" not in s:
            i = int(s["to_w"])
            s["end"] = wd[i]["end"] + 0.12
            if i + 1 < len(wd):
                s["end"] = min(s["end"], wd[i + 1]["start"] - 0.02)
        if "start" not in s or "end" not in s:
            raise SystemExit(f"сцене {s.get('id')} нужны start/end или from_w/to_w")
        s["start"], s["end"] = q(float(s["start"]), self.fps), q(min(float(s["end"]), self.dur), self.fps)

    # ---------- сборка ----------
    def run(self):
        sh = self.shot
        scenes = sh.get("scenes", [])
        for i, s in enumerate(scenes):
            s.setdefault("id", f"sc{i+1:02d}")
            if s["kind"] not in SCENES:
                raise SystemExit(f"неизвестный тип сцены: {s['kind']} (есть: {', '.join(sorted(SCENES))})")
            mod = SCENES[s["kind"]]
            if hasattr(mod, "default_layout"):
                s.setdefault("layout", mod.default_layout(s))
            s.setdefault("layout", getattr(mod, "DEFAULT_LAYOUT", "split"))
            self.resolve_times(s)
            if s["kind"] == "hook" and s["start"] < 1.0:
                s["start"] = 0.0                      # хук = первый кадр (обложка в ленте), с 0.00
            if s["end"] - s["start"] < 0.6 and s["start"] < self.dur - 0.1:
                self.warn(f"[{s['id']}] сцена короче 0.6 c")
        scenes[:] = [s for s in scenes if s["start"] < self.dur - 0.1]       # превью: обрезка по duration
        scenes.sort(key=lambda s: s["start"])
        base = [s for s in scenes if s["layout"] != "overlay"]
        for a, b in zip(base, base[1:]):
            if b["start"] < a["end"] - 0.01:
                if a["end"] - b["start"] > 0.35:
                    self.warn(f"[{a['id']}] и [{b['id']}] перекрываются на {a['end']-b['start']:.2f} c — {a['id']} обрезан")
                a["end"] = b["start"]

        cta = sh.get("cta")
        if cta and not self.st["cta"].get("enabled", True):
            cta = None
        if cta:
            cta = dict({k: v for k, v in self.st["cta"].items() if k in ("line1", "line3")}, **cta)
            if "from_w" in cta and "start" not in cta:
                cta["start"] = self.words[int(cta["from_w"])]["start"] - 0.05
            cta["start"] = q(float(cta["start"]), self.fps)
            cta["end"] = self.dur
            if cta["start"] >= self.dur - 0.1:
                cta = None

        tl = C.TL(self.fps)
        body, top_level, css_kinds = [], [], {}

        # --- сцены
        for s in scenes:
            mod = SCENES[s["kind"]]
            cx = C.Ctx(self, s)
            css_kinds[s["kind"]] = mod.CSS
            if s["layout"] == "overlay":
                box = f"left:0;top:0;width:{W}px;height:{H}px;"
            else:
                box = f"left:0;top:0;width:{W}px;height:{cx.AH}px;"
            bgcls = "" if s["layout"] == "overlay" else (" bg-dark" if s.get("bg") == "dark" else " bg-light")
            inner = mod.render(s, cx)
            body.append(
                f'<div class="scene clip s-{s["kind"]} layout-{s["layout"]}{bgcls}" data-scene="{s["id"]}" '
                f'data-start="{s["start"]}" data-duration="{round(s["end"]-s["start"], 4)}" data-track-index="3" '
                f'style="{box}">{inner}</div>')
            if hasattr(mod, "top_level"):
                top_level.append(mod.top_level(s, cx))
            mod.animate(s, cx, tl)          # видимость клипа ведёт сам HyperFrames по data-start/duration

        # --- раскладка аватара (из сцен)
        self.overlay_scenes = [x for x in scenes if x["layout"] == "overlay"]
        self.avatar_layout(tl, base, cta)

        # --- субтитры
        cap_on = self.st["captions"].get("enabled", True)
        if cap_on:
            body += self.captions(tl, cta)

        # --- CTA
        if cta:
            body.append(
                f'<div class="cta clip" id="cta" data-start="{cta["start"]}" data-duration="{q(cta["end"]-cta["start"])}" '
                f'data-track-index="6"><div class="cbox"><div class="l1">{esc(cta.get("line1","напиши"))}</div>'
                f'<div class="l2">{esc(cta["word"])}</div><div class="l3">{esc(cta.get("line3","в комментарии"))}</div></div></div>')
            tl.fromTo("#cta .cbox", {"opacity": 0, "scale": .8, "y": 30},
                      {"opacity": 1, "scale": 1, "y": 0, "duration": .5, "ease": "back.out(1.7)"}, cta["start"])
            tl.from_("#cta .l2", {"opacity": 0, "scale": .7, "duration": .4, "ease": "back.out(2)"}, cta["start"] + .2)
            self.add_sfx("pop", cta["start"] + .15)

        # --- ручные звуковые акценты из раскадровки: [{"name": "chime", "w": 69}]
        for e in sh.get("sfx_events", []):
            t = e["t"] if "t" in e else self.words[int(e["w"])]["start"]
            self.add_sfx(e["name"], t, e.get("volume"))

        # --- акценты-наезды на аватар
        for p in sh.get("punches", []):
            t = p["t"] if "t" in p else self.words[int(p["w"])]["start"]
            sc, d = p.get("scale", 1.14), p.get("dur", 1.6)
            tl.to("#bg-video", {"scale": sc, "duration": .35, "ease": "power3.out"}, t)
            tl.to("#bg-video", {"scale": 1, "duration": .4, "ease": "power2.inOut"}, t + d)

        self.carve = None
        self.write(body, top_level, css_kinds, tl)

    def avatar_layout(self, tl, base, cta):
        """Ключевые точки: в каждой сцене split/full; в промежутках — full."""
        pts, cur = [], 0.0
        for s in base:
            if s["start"] > cur + 0.01:
                pts.append((cur, "avatar"))
            pts.append((s["start"], s["layout"]))
            cur = s["end"]
        if cur < self.dur:
            pts.append((cur, "avatar"))
        if not pts:
            pts = [(0.0, "avatar")]
        merged = []
        for t, m in pts:
            if merged and merged[-1][1] == m:
                continue
            merged.append((t, m))
        FULL = {"left": 0, "top": 0, "width": W, "height": H, "opacity": 1, "borderRadius": 0}
        SPLIT = {"left": 0, "top": SPLIT_H, "width": W, "height": H - SPLIT_H, "opacity": 1,
                 "borderRadius": f'{self.st["layout"].get("split_radius", 44)}px {self.st["layout"].get("split_radius", 44)}px 0 0'}
        tl.set("#bg-video", {"scale": 1}, 0)
        av = self.av
        pos_full = av.get("full_pos", "50% 24%")
        pos_split = av.get("split_pos", "50% 40%")      # голова выше в нижней половине
        punch_t = [p["t"] if "t" in p else self.words[int(p["w"])]["start"] for p in self.shot.get("punches", [])]
        for t, m in merged[1:]:
            self.add_sfx("whoosh-short", max(0, t - 0.08))          # звук смены раскладки
        prev = None
        for t, m in merged:
            if m == "avatar":
                tl.set("#video-wrap", FULL, t)
                tl.set("#bg-video", {"objectPosition": pos_full}, t)
                if prev in ("split", "full") and t > 0.1 and not any(abs(t - pt) < 1.0 for pt in punch_t):
                    tl.fromTo("#bg-video", {"scale": 1.08}, {"scale": 1, "duration": .5, "ease": "power2.out",
                                                             "immediateRender": False}, t)
            elif m == "split":
                tl.set("#video-wrap", SPLIT, t)
                tl.set("#bg-video", {"objectPosition": pos_split}, t)
            else:                                                  # full-графика — аватар прячем
                tl.set("#video-wrap", {"opacity": 0}, t)
            prev = m
        self.layout_points = merged
        self.jumpcuts(tl, merged, punch_t)
        self.avatar_drops(tl, merged, pos_full)

    def hook_block_bottom(self, s):
        """Грубая оценка нижней границы блока заголовка хука (px от верха кадра) — по тем же размерам, что в hook.py."""
        import math
        y, gap = 90, 16
        if s.get("comment"):
            n = max(1, math.ceil(len(s["comment"].get("text", "")) / 24))   # ~24 знака в строке при 42 px
            y += 60 + 36 + n * 50 + 40 + gap
        if s.get("logos") or s.get("logo"):
            y += 190 + gap
        if s.get("kicker"):
            y += 40 + gap
        lines = s.get("lines", [])
        longest = max([len(l.replace("*", "")) for l in lines] or [1])
        hs = int(s.get("size", min(100, 1560 // max(10, longest))))
        y += len(lines) * (hs * 1.02 + 8) + (gap if lines else 0)
        y += (110 + gap if s.get("price") else 0) + (80 + gap if s.get("proof") else 0) + (130 + gap if s.get("apps") else 0)
        return y

    def avatar_drops(self, tl, merged, pos_full):
        """Хук поверх лица (style face/comment): если заголовок заходит на голову — опускаем аватар ниже,
        освободившийся верх заполняем размытой копией кадра. Голова в полном кадре начинается примерно с
        avatar.face_top (по умолч. 600 px); смещение — "drop" у сцены хука (px), иначе считаем сами."""
        av = self.av
        face_top = int(av.get("face_top", 540))         # верх волос в полном кадре (калибруется в /setup-studio по пробному видео)
        self.drops = []
        for s in getattr(self, "overlay_scenes", []):
            if s.get("kind") != "hook" or s.get("style", "face") not in ("face", "comment"):
                continue
            drop = s.get("drop")
            if drop is None:
                drop = max(0, int(self.hook_block_bottom(s) + 110 - face_top))   # +110 — воздух между текстом и головой
            drop = min(int(drop), 520)
            if drop < 30:
                continue
            t0, t1 = s["start"], s["end"]
            self.drops.append((t0, t1, drop))
            ts = t0 + .01                                   # после базовой раскладки в t0 (иначе две set в один момент спорят)
            tl.set("#blur-wrap", {"opacity": 1}, ts)
            tl.set("#video-wrap", {"y": drop, "borderRadius": f'{self.st["layout"].get("split_radius", 44)}px {self.st["layout"].get("split_radius", 44)}px 0 0'}, ts)   # transform, не top
            tl.set("#blur-wrap", {"opacity": 0}, t1)
            tl.set("#video-wrap", {"y": 0}, t1)
            mode = next((m for tm, m in reversed(merged) if tm <= t1 + 1e-6), "avatar")
            if mode == "avatar" and not any(abs(tm - t1) < 1e-3 for tm, _ in merged):
                tl.set("#video-wrap", {"borderRadius": 0}, t1)

    def jumpcuts(self, tl, merged, punch_t):
        """Jump-cut наезды на аватар: на начале каждой фразы крупность резко меняется 1.0 ↔ 1.1 (как склейка
        говорящей головы). Без них аватар ~70% ролика стоит неподвижно — главный «скучный» кадр.
        Не трогаем: полноэкранную графику, ±0.4 с от смены раскладки, окна ударов (punches).
        Отключить: "avatar": {"jumpcuts": false}; крупность — "jump_scale"."""
        av = self.av
        if not av.get("jumpcuts", True) or not self.words:
            return
        zoom = float(av.get("jump_scale", 1.1))
        punches = []
        for p in self.shot.get("punches", []):
            t = p["t"] if "t" in p else self.words[int(p["w"])]["start"]
            punches.append((t - .3, t + p.get("dur", 1.6) + .5))
        changes = [t for t, _ in merged]
        cuts, last = [], -9.0
        for i, w in enumerate(self.words):
            if i == 0:
                continue
            prev_w = self.words[i - 1]["w"]
            t = w["start"]
            sent = prev_w.endswith((".", "?", "!", "…"))
            pause = prev_w.endswith((",", ":", "—", ";")) and t - last > 2.4
            if (sent or pause) and t - last > 1.2:
                cuts.append(t)
                last = t
        # склейки из чистки живой записи (tools/cleanup.py → cuts.json): на каждой меняем крупность,
        # иначе видно «прыжок» головы. Они важнее фразовых наездов.
        cp = os.path.join(self.proj, "cuts.json")
        if os.path.exists(cp):
            hard = [float(t) for t in json.load(open(cp))]
            cuts = sorted(set([round(t, 2) for t in hard] + [t for t in cuts if all(abs(t - h) > .8 for h in hard)]))
        state, prev_t = 1.0, 0.0
        resets = changes + [b for _, b in punches]          # после удара/смены раскладки масштаб снова 1.0
        for t in cuts:
            if any(prev_t < r <= t for r in resets):
                state = 1.0
            prev_t = t
            mode = next((m for tm, m in reversed(merged) if tm <= t + 1e-6), "avatar")
            if any(a <= t <= b for a, b in punches) or any(abs(t - c) < .4 for c in changes):
                continue
            if mode == "full" or t < .3 or t > self.dur - .3:
                continue
            state = zoom if state == 1.0 else 1.0
            tl.set("#bg-video", {"scale": state}, t)

    def captions(self, tl, cta):
        cfg = self.st["captions"]
        style = cfg.get("style", "box")
        mx = 1 if style == "word" else int(cfg.get("max_words", 3))
        max_chars = int(cfg.get("max_chars", 20))
        # split → на стыке графики и спикера; полный кадр/графика → нижняя треть
        ys = cfg.get("top_split", cfg.get("y_split", "seam"))
        top_split = SPLIT_H - int(int(str(cfg.get("size", 58)).rstrip("px")) * .8) if ys == "seam" else int(ys)
        top_full = int(cfg.get("top_full", cfg.get("y_full", 1360)))
        colors = self.theme
        active = C.color(cfg.get("active", "accent"), colors)
        active_ink = C.color(cfg.get("active_ink", "accent_ink"), colors)
        text = C.color(cfg.get("text", "#FFFFFF"), colors)

        def mode_at(t):
            m = "avatar"
            for pt, mm in self.layout_points:
                if pt <= t + 1e-3:
                    m = mm
            return m
        stop = cta["start"] - 0.05 if cta else self.dur
        ws = [w for w in self.words if w["start"] < stop]
        groups, i = [], 0
        while i < len(ws):
            g = [ws[i]]
            while len(g) < mx and i + len(g) < len(ws):
                nxt, last = ws[i + len(g)], g[-1]
                if nxt["start"] - last["end"] > 0.5 or last["w"][-1:] in ".!?…:":
                    break
                if (mode_at(nxt["start"]) == "split") != (mode_at(g[0]["start"]) == "split"):
                    break                                   # не тащим группу через смену раскладки
                if sum(len(x["w"]) + 1 for x in g) + len(nxt["w"]) > max_chars:
                    break
                g.append(nxt)
            groups.append(g)
            i += len(g)
        out = []
        for gi, g in enumerate(groups):
            gs = g[0]["start"]
            ge = min(g[-1]["end"] + 0.15, groups[gi + 1][0]["start"] if gi + 1 < len(groups) else stop)
            ge = max(ge, gs + 0.2)
            gs, ge = q(gs), q(ge)
            if gi + 1 < len(groups):
                ge = min(ge, q(groups[gi + 1][0]["start"]))
            spans = "".join(f'<span class="k" id="c{gi}-{wi}">{esc(w["w"])}</span>' for wi, w in enumerate(g))
            top = top_split if mode_at(gs) == "split" else top_full
            out.append(f'<div class="cap clip st-{style}" id="cap{gi}" data-start="{gs}" data-duration="{round(ge-gs, 4)}" '
                       f'data-track-index="5" style="top:{top}px;"><div class="box">{spans}</div></div>')
            tl.fromTo(f"#cap{gi} .box", {"opacity": 0, "y": 10, "scale": .96},
                      {"opacity": 1, "y": 0, "scale": 1, "duration": .16, "ease": "back.out(1.6)"}, gs)
            for wi, w in enumerate(g):
                on = ({"backgroundColor": active, "color": active_ink, "webkitTextStrokeWidth": 0}
                      if style == "highlight" else {"color": active})
                off = ({"backgroundColor": "rgba(0,0,0,0)", "color": text, "webkitTextStrokeWidth": "0.12em"}
                       if style == "highlight" else {"color": text})
                if style == "word":
                    tl.fromTo(f"#c{gi}-{wi}", {"scale": .7}, {"scale": 1, "duration": .14, "ease": "back.out(2.2)"}, w["start"])
                tl.set(f"#c{gi}-{wi}", on, w["start"])
                if wi < len(g) - 1:
                    tl.set(f"#c{gi}-{wi}", off, g[wi + 1]["start"])
        return out

    def soften_music_duck(self, k):
        """carve пишет спектральный вырез (полосы голоса) + общий gain-«дак» до −12…−19 дБ под речью.
        Для лёгкой подложки в Reels общий дак слишком глубокий — музыку не слышно. Полосы оставляем,
        а лейн общего gain масштабируем (k=0.4 → не глубже ~−5 дБ)."""
        import html as H, re as R
        path = os.path.join(self.pub, "index.html")
        doc = open(path, encoding="utf-8").read()
        m = R.search(r'<audio id="music"[^>]*>', doc)
        if not m:
            return
        tag = m.group(0)
        ch = R.search(r'data-fx-chain="([^"]*)"', tag)
        au = R.search(r'data-automation="([^"]*)"', tag)
        if not ch or not au:
            return
        chain = json.loads(H.unescape(ch.group(1)))
        gain_ids = {n["id"] for n in chain.get("nodes", []) if n.get("type") == "gain"}
        auto = json.loads(H.unescape(au.group(1)))
        lanes = auto if isinstance(auto, list) else auto.get("lanes", [])
        for lane in lanes:
            tgt = lane.get("target", "")
            if any(tgt == f"fx.{g}.gain" for g in gain_ids):
                for pt in lane.get("points", lane.get("keys", [])):
                    for key in ("v", "value"):
                        if key in pt and isinstance(pt[key], (int, float)):
                            pt[key] = round(pt[key] * k, 2)
        new_au = 'data-automation="' + H.escape(json.dumps(auto, ensure_ascii=False, separators=(",", ":")), quote=True) + '"'
        doc = doc.replace(tag, tag.replace(au.group(0), new_au))
        open(path, "w", encoding="utf-8").write(doc)

    def write(self, body, top_level, css_kinds, tl):
        th = self.theme
        self.sfx_files = set()
        root = ":root{" + ";".join(f"--{k}:{v}" for k, v in C.theme_vars(dict(self.st, colors=th)).items()) + ";}"
        faces, self.font_files, fw = C.font_faces(self.st["fonts"])
        for m in fw:
            self.warn(m)
        css = faces + "\n" + root + C.BASE_CSS + "\n".join(css_kinds.values())
        o = [f'<!doctype html><html lang="{self.st.get("language", "ru")}"><head><meta charset="utf-8"/>',
             f"<style>{css}</style></head><body>",
             f'<div id="stage" data-composition-id="talking-head-recut" data-start="0" data-duration="{self.dur}" '
             f'data-fps="{self.fps}" data-width="{W}" data-height="{H}">',
             (f'<div id="blur-wrap" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;overflow:hidden;z-index:0;opacity:0;">'
              f'<video id="blur-video" src="input-video.mp4" muted playsinline data-start="0" data-duration="{self.dur}" '
              f'data-track-index="0" style="width:100%;height:100%;object-fit:cover;object-position:50% 24%;'
              f'filter:blur(38px) brightness(.5) saturate(1.2);transform:scale(1.2);"></video></div>'
              if getattr(self, "drops", None) else ""),
             f'<div id="video-wrap" style="left:0;top:0;width:{W}px;height:{H}px;"><video id="bg-video" '
             f'src="input-video.mp4" muted playsinline data-start="0" data-duration="{self.dur}" data-track-index="1"></video></div>',
             f'<audio id="source-audio" src="input-video.mp4" data-start="0" data-duration="{self.dur}" data-track-index="10" '
             f'data-volume="1" data-audio-group="voiceover"></audio>']
        for k, (name, t, v, d) in enumerate(sorted(self.sfx_events, key=lambda e: e[1])):
            fn = self.sfx_manifest[name]["file"]
            o.append(f'<audio id="sfx{k}" src="sfx/{fn}" data-start="{q(t)}" data-duration="{round(d, 3)}" '
                     f'data-track-index="{12 + k % 4}" data-volume="{v}" data-audio-group="sfx"></audio>')
            self.sfx_files.add(fn)
        mu = self.shot.get("music")
        if mu:
            url = self.add_media(mu["src"])
            self.carve = find_carve()
            mv = float(mu.get("volume", 0.16)) if self.carve else float(mu.get("volume_nocarve", 0.35))
            self.music_carve = float(mu.get("carve", 0.8))
            o.append(f'<audio id="music" src="{url}" data-start="0" data-duration="{self.dur}" '
                     f'data-media-start="{mu.get("start", 0)}" data-track-index="11" data-volume="{mv}" '
                     f'data-audio-group="music"></audio>')
            fi, fo = float(mu.get("fade_in", .4)), float(mu.get("fade_out", 1.5))
            tl.fromTo("#music", {"volume": 0}, {"volume": mv, "duration": fi, "ease": "none"}, 0)
            tl.to("#music", {"volume": 0, "duration": fo, "ease": "none"}, self.dur - fo)
        o += [x for x in top_level if x]
        o += body
        o.append('<script src="vendor/gsap.min.js"></script>')
        o.append("<script>(function(){var tl=window.gsap.timeline({paused:true});\n" + tl.js_text() +
                 "\nwindow.__timelines=window.__timelines||{};window.__timelines['talking-head-recut']=tl;})();</script>")
        o.append("</div></body></html>")
        os.makedirs(self.pub, exist_ok=True)
        open(os.path.join(self.pub, "index.html"), "w", encoding="utf-8").write("\n".join(o))
        # ассеты
        A = os.path.join(C.SYS, "assets")
        os.makedirs(os.path.join(self.pub, "fonts"), exist_ok=True)
        for src, fn in self.font_files:
            dst = os.path.join(self.pub, "fonts", fn)
            if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                shutil.copy2(src, dst)
        C.copy_tree(os.path.join(A, "vendor"), os.path.join(self.pub, "vendor"))
        if self.sfx_files:
            os.makedirs(os.path.join(self.pub, "sfx"), exist_ok=True)
            for fn in self.sfx_files:
                shutil.copy2(os.path.join(A, "sfx", fn), os.path.join(self.pub, "sfx", fn))
        os.makedirs(os.path.join(self.pub, "logos"), exist_ok=True)
        for d, f in self.logos_used:
            shutil.copy2(os.path.join(d, f), os.path.join(self.pub, "logos", f))
        if self.media_used:
            os.makedirs(os.path.join(self.pub, "media"), exist_ok=True)
            for name, src in self.media_used.items():
                shutil.copy2(src, os.path.join(self.pub, "media", name))
        hj = os.path.join(self.pub, "hyperframes.json")
        if not os.path.exists(hj):
            json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                       "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
                       "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
                       "media": {"autoProxy": True}, "authoringSkill": "talking-head-recut"},
                      open(hj, "w"), indent=2)
        # музыка: carve — музыка уступает голосу в его частотах (анализ пишет fx-chain + огибающие)
        if self.shot.get("music") and not self.carve:
            self.warn("carve (скилл hyperframes-audio) не найден — музыка просто приглушена; поставь: npx hyperframes skills")
        if self.shot.get("music") and self.carve:
            r = subprocess.run(["node", self.carve,
                                "--comp", os.path.join(self.pub, "index.html"), "--bed", "music",
                                "--voice", "source-audio", "--strength", str(getattr(self, "music_carve", 0.8)),
                                "--core", os.path.join(C.SYS, "tools")], capture_output=True, text=True)
            bands = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith(("bands", "wrote"))]
            if r.returncode or not bands:
                self.warn("carve не отработал: " + (r.stdout + r.stderr)[-300:])
            else:
                self.soften_music_duck(float(self.shot["music"].get("duck", 0.2)))
                print("музыка: carve под голос —", bands[0][:90])
        n = len(self.shot.get("scenes", []))
        print(f"OK: {n} сцен, {self.dur:.2f} c → {os.path.relpath(os.path.join(self.pub,'index.html'))}")
        print("раскладка аватара:", " → ".join(f"{t:.1f}s {m}" for t, m in self.layout_points))
        for w in self.warnings:
            print("⚠", w)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="сборка ролика")
    ap.add_argument("proj")
    ap.add_argument("--shot", default="shotlist.json", help="другая раскадровка (варианты хука)")
    ap.add_argument("--pub", default="public", help="папка сборки варианта (public_hookA)")
    ap.add_argument("--duration", type=float, help="собрать только первые N секунд (превью хука)")
    a = ap.parse_args()
    Build(a.proj, a.shot, a.pub, a.duration).run()
