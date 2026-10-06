# -*- coding: utf-8 -*-
"""Каталог сцен из docstring'ов модулей — всегда актуален.   python3 engine/catalog.py [kind]"""
import importlib, os, pkgutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scenes  # noqa: E402

want = sys.argv[1] if len(sys.argv) > 1 else None
for m in sorted(pkgutil.iter_modules(scenes.__path__), key=lambda m: m.name):
    mod = importlib.import_module("scenes." + m.name)
    if not hasattr(mod, "KIND") or (want and mod.KIND != want):
        continue
    print(f"━━ {mod.KIND} ━━")
    print((mod.__doc__ or "").strip(), "\n")
