# -*- coding: utf-8 -*-
"""Шрифты студии: любой шрифт Google Fonts (через Fontsource) или свой файл.

  python3 tools/fonts.py list                                   # что установлено (встроенные + свои)
  python3 tools/fonts.py add "Unbounded"                        # скачать (латиница + кириллица), веса 400–800
  python3 tools/fonts.py add "Rubik Mono One" --weights 400
  python3 tools/fonts.py file "Мой шрифт" ~/Downloads/MyFont-Bold.woff2 --weight 700   # свой файл (woff2/ttf/otf)

Файлы → studio/fonts/, реестр → studio/fonts/fonts.json. В studio.json шрифт подключается по имени:
"fonts": {"head": "Unbounded", "body": "Montserrat", "mono": "JetBrains Mono"}.
Для русского языка шрифт обязан иметь кириллицу — add это проверяет.
"""
import json, os, shutil, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "studio", "fonts")
REG = os.path.join(DIR, "fonts.json")
API = "https://api.fontsource.org/v1/fonts/{}"
CDN = "https://cdn.jsdelivr.net/fontsource/fonts/{id}@latest/{subset}-{w}-normal.woff2"


def load():
    return json.load(open(REG, encoding="utf-8")) if os.path.exists(REG) else {}


def save(reg):
    os.makedirs(DIR, exist_ok=True)
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ai-montage-kit"})
    return urllib.request.urlopen(req, timeout=30).read()


def add(family, weights):
    fid = family.strip().lower().replace(" ", "-")
    try:
        meta = json.loads(get(API.format(fid)))
    except Exception:
        raise SystemExit(f"шрифт «{family}» не найден в Google Fonts / Fontsource (проверь написание на fonts.google.com)")
    subsets = [x for x in ("latin", "cyrillic") if x in meta["subsets"]]
    if "cyrillic" not in subsets:
        print(f"⚠ у «{meta['family']}» нет кириллицы — для русских текстов он не подойдёт (буквы упадут на запасной шрифт)")
    have = meta["weights"]
    ws = [w for w in weights if w in have] or [min(have, key=lambda x: abs(x - 700))]
    files = []
    os.makedirs(DIR, exist_ok=True)
    for w in ws:
        for sub in subsets:
            fn = f"{fid}-{w}-{sub}.woff2"
            open(os.path.join(DIR, fn), "wb").write(get(CDN.format(id=fid, subset=sub, w=w)))
            files.append({"file": fn, "weight": w, "range": meta.get("unicodeRange", {}).get(sub, "")})
    reg = load()
    reg[meta["family"]] = files
    save(reg)
    print(f"✓ {meta['family']}: веса {', '.join(map(str, ws))}, наборы {', '.join(subsets)} → studio/fonts/")
    print(f"  подключи в studio/studio.json: \"fonts\": {{\"head\": \"{meta['family']}\"}}")


def add_file(family, path, weight):
    os.makedirs(DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    fn = base + ".woff2"
    dst = os.path.join(DIR, fn)
    if path.lower().endswith(".woff2"):
        shutil.copy2(os.path.expanduser(path), dst)
    else:
        try:   # ttf/otf → woff2 (если есть fonttools), иначе кладём как есть — Chrome читает и ttf
            subprocess.run([sys.executable, "-m", "fontTools.ttLib.woff2", "compress", "-o", dst,
                            os.path.expanduser(path)], check=True, capture_output=True)
        except Exception:
            fn = os.path.basename(path)
            dst = os.path.join(DIR, fn)
            shutil.copy2(os.path.expanduser(path), dst)
    reg = load()
    files = [f for f in reg.get(family, []) if f["file"] != fn]
    files.append({"file": fn, "weight": weight, "range": ""})
    reg[family] = files
    save(reg)
    print(f"✓ {family} ({weight}) → studio/fonts/{fn}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "add":
        ws = [400, 500, 600, 700, 800]
        if "--weights" in sys.argv:
            ws = [int(x) for x in sys.argv[sys.argv.index("--weights") + 1].split(",")]
        add(sys.argv[2], ws)
    elif cmd == "file":
        w = int(sys.argv[sys.argv.index("--weight") + 1]) if "--weight" in sys.argv else 700
        add_file(sys.argv[2], sys.argv[3], w)
    else:
        for d, title in ((os.path.join(ROOT, "assets", "fonts"), "встроенные"), (DIR, "свои")):
            p = os.path.join(d, "fonts.json")
            if os.path.exists(p):
                for fam, files in json.load(open(p, encoding="utf-8")).items():
                    ws = sorted({str(f["weight"]) for f in files})
                    print(f"{title:10} {fam:22} веса: {', '.join(ws)}")


if __name__ == "__main__":
    main()
