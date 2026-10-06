# -*- coding: utf-8 -*-
"""Профиль студии (studio/studio.json): создать из пресета, править, проверить.

  python3 tools/studio.py presets                          # готовые стили
  python3 tools/studio.py init neon [--force]              # studio.json из пресета (+ скачать его шрифты)
  python3 tools/studio.py set colors.accent=#FF2E88 captions.style=highlight captions.uppercase=true
  python3 tools/studio.py fonts                            # докачать шрифты, указанные в studio.json
  python3 tools/studio.py show                             # итоговые настройки (база + студия)
  python3 tools/studio.py check                            # проверка: цвета, шрифты, контраст, позиции

В studio.json хранится только то, что отличается от engine/defaults.json.
"""
import json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as CM  # noqa: E402

PATH = os.path.join(CM.STUDIO, "studio.json")
PRESETS = os.path.join(CM.ROOT, "presets")


def load_own():
    return json.load(open(PATH, encoding="utf-8")) if os.path.exists(PATH) else {}


def save_own(d):
    os.makedirs(CM.STUDIO, exist_ok=True)
    json.dump(d, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def parse(v):
    try:
        return json.loads(v)
    except Exception:
        return v


def presets():
    for fn in sorted(os.listdir(PRESETS)):
        if fn.endswith(".json"):
            p = json.load(open(os.path.join(PRESETS, fn), encoding="utf-8"))["_preset"]
            print(f"{fn[:-5]:11} {p['title']:18} {p['description']}")


def init(name, force=False):
    src = os.path.join(PRESETS, name + ".json")
    if not os.path.exists(src):
        raise SystemExit(f"нет пресета {name}; список: python3 tools/studio.py presets")
    if os.path.exists(PATH) and not force:
        raise SystemExit("studio/studio.json уже есть — добавь --force, чтобы перезаписать (или правь через set)")
    d = json.load(open(src, encoding="utf-8"))
    d.pop("_preset", None)
    d = {"_comment": f"Стиль студии (из пресета «{name}»). Только отличия от engine/defaults.json. Правка: tools/studio.py set",
         **d}
    save_own(d)
    print(f"✓ studio/studio.json ← пресет {name}")
    fonts()


def set_(pairs):
    d = load_own()
    for p in pairs:
        k, v = p.split("=", 1)
        cur = d
        parts = k.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = parse(v)
        print(f"  {k} = {cur[parts[-1]]!r}")
    save_own(d)
    if any(p.startswith("fonts.") for p in pairs):
        fonts()


def fonts():
    from core import font_registry      # noqa: E402
    st = CM.style()
    reg = font_registry()
    for role in ("head", "body", "mono"):
        fam = st["fonts"].get(role)
        if fam and fam.lower() not in reg:
            print(f"шрифт {role}: {fam} — скачиваю")
            subprocess.run([sys.executable, os.path.join(CM.ROOT, "tools", "fonts.py"), "add", fam])
            reg = font_registry()


def lum(hexc):
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", hexc.strip())
    if not m:
        return None
    r, g, b = (int(m.group(1)[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return (hi + .05) / (lo + .05)


def check():
    from core import font_registry, color      # noqa: E402
    st = CM.style()
    c = st["colors"]
    ok = True
    if not os.path.exists(PATH):
        print("⚠ нет studio/studio.json — студия не настроена (/setup-studio)")
        ok = False
    for k, v in c.items():
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            print(f"⚠ colors.{k} = {v} — нужен формат #RRGGBB")
            ok = False
    for a, b, what in (("accent", "accent_ink", "текст на акцентной плашке"), ("ink", "bg", "текст графики на фоне"),
                       ("dark_ink", "dark", "текст на тёмных сценах")):
        r = contrast(c.get(a, ""), c.get(b, ""))
        if r is not None and r < 3:
            print(f"⚠ слабый контраст {a}/{b} ({r:.1f}:1) — {what} будет плохо читаться (нужно ≥ 3, лучше ≥ 4.5)")
            ok = False
    cap = st["captions"]
    if cap.get("style") == "box":
        r = contrast(color(cap.get("text", "#FFFFFF"), c), color(cap.get("box", "#000000"), c)
                     if str(cap.get("box", "")).startswith("#") else "#000000")
        if r is not None and r < 4.5:
            print(f"⚠ субтитры: текст и плашка мало контрастны ({r:.1f}:1)")
            ok = False
    if cap.get("style") not in ("box", "highlight", "outline", "word"):
        print("⚠ captions.style: box | highlight | outline | word")
        ok = False
    reg = font_registry()
    for role in ("head", "body", "mono"):
        if st["fonts"].get(role, "").lower() not in reg:
            print(f"⚠ шрифт {role} «{st['fonts'].get(role)}» не установлен → python3 tools/studio.py fonts")
            ok = False
    ob = os.path.join(CM.STUDIO, "onboarding.md")
    if os.path.exists(ob):
        txt = open(ob, encoding="utf-8").read()
        rows = [l for l in txt.splitlines() if l.startswith("| ") and l[2:3].isdigit()]
        todo = [l.split("|")[1].strip() for l in rows if "⬜" in l]
        wait = [l.split("|")[1].strip() for l in rows if "⏳" in l]
        if todo:
            print(f"⚠ анкета: не заданы вопросы {', '.join(todo)}")
            ok = False
        if wait:
            print(f"… анкета: ждём ответ/материал по вопросам {', '.join(wait)}")
    if not os.path.exists(os.path.join(CM.STUDIO, "profile.md")):
        print("⚠ нет studio/profile.md — агенту не на что опираться в хуках и сценах (/setup-studio)")
        ok = False
    print("✓ студия в порядке" if ok else "— есть замечания")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "presets":
        presets()
    elif cmd == "init":
        init(sys.argv[2], "--force" in sys.argv)
    elif cmd == "set":
        set_(sys.argv[2:])
    elif cmd == "fonts":
        fonts()
    elif cmd == "check":
        check()
    else:
        st = CM.style()
        st.pop("_comment", None)
        print(json.dumps(st, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
