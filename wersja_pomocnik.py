# -*- coding: utf-8 -*-
"""Pomocnik wersji — używany przez pliki .bat.

  python wersja_pomocnik.py            → wypisuje wersję z PMT_Delegacje.py
  python wersja_pomocnik.py plik.exe   → 0 gdy plik zawiera tę wersję, 1 gdy nie
"""
import os, re, sys

def wersja_zrodla():
    try:
        with open("PMT_Delegacje.py", encoding="utf-8") as f:
            m = re.search(r'WERSJA_PROGRAMU\s*=\s*"([^"]+)"', f.read())
        return m.group(1) if m else ""
    except Exception:
        return ""

w = wersja_zrodla()
if len(sys.argv) > 1:
    plik = sys.argv[1]
    if not w or not os.path.exists(plik):
        sys.exit(1)
    try:
        with open(plik, "rb") as f:
            sys.exit(0 if w.encode("ascii") in f.read() else 1)
    except Exception:
        sys.exit(1)
print(w)
