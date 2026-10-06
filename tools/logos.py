# -*- coding: utf-8 -*-
"""Библиотека логотипов: встроенная (assets/logos — популярные ИИ-сервисы и приложения) + своя (studio/logos).

  python3 tools/logos.py sync            # зарегистрировать PNG/JPG, которые клиент положил в studio/logos/
  python3 tools/logos.py list            # показать реестр
  python3 tools/logos.py find "клод код" # по какому слагу найдётся
  python3 tools/logos.py fetch cursor    # скачать недостающий знак из @lobehub/icons (бренды ИИ и техно)
  python3 tools/logos.py add mybrand <файл|url> "Мой бренд" "мой бренд,майбренд" [--bare] [--trim N]
                                   # логотип продукта/клиента; --bare = готовая иконка-плитка без белой подложки;
                                   # --trim N = срезать N% полей; aliases = как название звучит в речи

Реестры: assets/logos/logos.json (встроенный, не трогаем) и studio/logos/logos.json (свои — сюда пишут sync/add/fetch).
Свой логотип с тем же слагом перекрывает встроенный.
"""
import json, os, re, shutil, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(ROOT, "assets", "logos")
LOGO_DIR = os.path.join(ROOT, "studio", "logos")
REG = os.path.join(LOGO_DIR, "logos.json")
LOBE = "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-png@latest/light/{}.png"


def norm(s):
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[\s_\-\.·]+", " ", s)
    return re.sub(r"[^a-zа-я0-9 ]", "", s).strip()


def _read(d):
    p = os.path.join(d, "logos.json")
    if not os.path.exists(p):
        return {}
    reg = json.load(open(p, encoding="utf-8"))
    for e in reg.values():
        e["_dir"] = d
    return reg


def load():
    reg = _read(BASE_DIR)
    reg.update(_read(LOGO_DIR))
    return reg


def own():
    reg = _read(LOGO_DIR)
    for e in reg.values():
        e.pop("_dir", None)
    return reg


def save(reg):
    os.makedirs(LOGO_DIR, exist_ok=True)
    clean = {k: {kk: vv for kk, vv in v.items() if kk != "_dir"} for k, v in reg.items()}
    json.dump(dict(sorted(clean.items())), open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def slug_from_file(fn):
    base = os.path.splitext(fn)[0].lower()
    base = re.sub(r"\s*\d+$", "", base)          # «kimi 1» → kimi
    base = base.replace("midjouney", "midjourney")
    tr = dict(zip("абвгдеёзийклмнопрстуфхцыэ", "abvgdeezijklmnoprstufhcye"))
    tr.update({"ж": "zh", "ч": "ch", "ш": "sh", "щ": "sch", "ю": "yu", "я": "ya", "ь": "", "ъ": ""})
    base = "".join(tr.get(c, c) for c in base)
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def resolve(name, reg=None):
    """Имя из сценария/раскадровки → slug или None."""
    reg = reg or load()
    n = norm(name)
    if n.replace(" ", "-") in reg:
        return n.replace(" ", "-")
    best = None
    for slug, e in reg.items():
        keys = [norm(slug), norm(e.get("name", ""))] + [norm(a) for a in e.get("aliases", [])]
        for k in keys:
            if not k:
                continue
            if n == k:
                return slug
            # «claude code» → claude, «kimi k3» → kimi (самое длинное совпадение с начала)
            if n.startswith(k + " ") and (best is None or len(k) > best[1]):
                best = (slug, len(k))
            # падежи: «клоду», «гитхабе», «кимика»
            elif (len(k) >= 4 and n.startswith(k) and len(n) - len(k) <= 2
                  and re.match(r"[а-я]", k) and (best is None or len(k) > best[1])):
                best = (slug, len(k))
    return best[0] if best else None


def path_of(name, reg=None):
    reg = reg or load()
    s = resolve(name, reg)
    return os.path.join(reg[s].get("_dir", BASE_DIR), reg[s]["file"]) if s else None


def sync():
    """Файлы, которые клиент положил в studio/logos/ (любое имя, png/jpg/webp) → реестр.
    Имя файла = слаг; название и синонимы потом можно поправить в studio/logos/logos.json."""
    os.makedirs(LOGO_DIR, exist_ok=True)
    reg = own()
    known = {e.get("file") for e in reg.values()} | {e.get("orig") for e in reg.values()}
    added = []
    for fn in sorted(os.listdir(LOGO_DIR)):
        if fn.startswith(".") or not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) or fn in known:
            continue
        slug = slug_from_file(fn) or "logo"
        dst = slug + ".png"
        src = os.path.join(LOGO_DIR, fn)
        if fn != dst:
            os.system(f'ffmpeg -v error -y -i "{src}" "{os.path.join(LOGO_DIR, dst)}"')
        e = reg.get(slug, {"name": os.path.splitext(fn)[0], "aliases": []})
        e.update(file=dst, orig=fn, source="client")
        reg[slug] = e
        added.append(slug)
    save(reg)
    print("synced:", ", ".join(added) if added else "нет новых")


def fetch(slug, name=None, aliases=()):
    os.makedirs(LOGO_DIR, exist_ok=True)
    reg = own()
    for variant in (slug + "-color", slug):
        try:
            data = urllib.request.urlopen(LOBE.format(variant), timeout=15).read()
        except Exception:
            continue
        open(os.path.join(LOGO_DIR, slug + ".png"), "wb").write(data)
        e = reg.get(slug, {"name": name or slug.title(), "aliases": list(aliases)})
        e.update(file=slug + ".png", source="lobehub", mark_only=True)
        reg[slug] = e
        save(reg)
        print("fetched", slug, "←", variant)
        return True
    print("не найдено в lobehub:", slug)
    return False


def add(slug, src, name, aliases="", bare=False, trim=0):
    os.makedirs(LOGO_DIR, exist_ok=True)
    dst = os.path.join(LOGO_DIR, slug + ".png")
    tmp = dst + ".src"
    if src.startswith("http"):
        open(tmp, "wb").write(urllib.request.urlopen(src, timeout=20).read())
    else:
        shutil.copy2(os.path.expanduser(src), tmp)
    vf = "format=rgba"
    if trim:
        vf = f"crop=iw*{1-2*trim/100}:ih*{1-2*trim/100},format=rgba"
    os.system(f'ffmpeg -v error -y -i "{tmp}" -vf "{vf}" "{dst}"')
    os.remove(tmp)
    reg = own()
    e = reg.get(slug, {})
    e.update(file=slug + ".png", name=name, source="product",
             aliases=[a.strip() for a in aliases.split(",") if a.strip()] or e.get("aliases", []))
    if bare:
        e["bare"] = True
    reg[slug] = e
    save(reg)
    print("added", slug, "→", dst)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "sync":
        sync()
    elif cmd == "find":
        q = " ".join(sys.argv[2:])
        print(q, "→", resolve(q))
    elif cmd == "add":
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        trim = 0
        if "--trim" in sys.argv:
            trim = float(sys.argv[sys.argv.index("--trim") + 1]); args.remove(str(sys.argv[sys.argv.index("--trim") + 1]))
        add(args[0], args[1], args[2], args[3] if len(args) > 3 else "", "--bare" in sys.argv, trim)
    elif cmd == "fetch":
        fetch(sys.argv[2], *(sys.argv[3:4]))
    else:
        for s, e in load().items():
            print(f"{s:14} {e.get('source',''):8} {e['name']:16} {', '.join(e.get('aliases', []))}")
