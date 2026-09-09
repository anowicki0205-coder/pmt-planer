# -*- coding: utf-8 -*-
"""Pomocnik wersji — używany przez pliki .bat.

  python wersja_pomocnik.py            → wypisuje wersję z PMT_Delegacje.py
  python wersja_pomocnik.py plik.exe   → 0 gdy zbudowany program zawiera
                                         tę wersję, 1 gdy nie

DLACZEGO NIE SZUKAMY TYLKO W PLIKU .EXE:
w budowie folderowej (--onedir, zalecanej) sam PMT_Planer.exe to wyłącznie
program rozruchowy — kod i numer wersji leżą w podkatalogu _internal.
Szukanie numeru w samym .exe dawało fałszywe „STARA kompilacja". Dlatego
przeszukujemy też katalog obok programu, a numer sprawdzamy w dwóch
zapisach: zwykłym (ASCII) i szesnastobitowym (UTF-16), bo tak Windows
trzyma metadane wersji pliku.
"""
import os
import re
import sys

MAX_PLIK_MB = 200          # nie czytamy w całości gigantycznych plików


def wersja_zrodla(katalog="."):
    try:
        with open(os.path.join(katalog, "PMT_Delegacje.py"), encoding="utf-8") as f:
            m = re.search(r'WERSJA_PROGRAMU\s*=\s*"([^"]+)"', f.read())
        return m.group(1) if m else ""
    except Exception:
        return ""


def _plik_zawiera(sciezka, wzorce):
    try:
        if os.path.getsize(sciezka) > MAX_PLIK_MB * 1024 * 1024:
            return False
        with open(sciezka, "rb") as f:
            dane = f.read()
        return any(w in dane for w in wzorce)
    except Exception:
        return False


def build_ma_wersje(sciezka_exe, wersja):
    """Czy zbudowany program pochodzi z tej wersji źródła?"""
    if not wersja or not os.path.exists(sciezka_exe):
        return False
    wzorce = [wersja.encode("ascii", "ignore"),
              wersja.encode("utf-16-le")]
    if _plik_zawiera(sciezka_exe, wzorce):
        return True
    # budowa folderowa: numer siedzi w plikach obok, głównie w _internal
    katalog = os.path.dirname(os.path.abspath(sciezka_exe))
    znacznik = os.path.join(katalog, "pmt_wersja.txt")
    try:
        if os.path.exists(znacznik):
            with open(znacznik, encoding="utf-8", errors="ignore") as f:
                if f.read().strip().startswith(wersja):
                    return True
    except Exception:
        pass
    for korzen, _katalogi, pliki in os.walk(katalog):
        for nazwa in pliki:
            if nazwa.lower().endswith((".pyc", ".pyd", ".dll", ".zip", ".exe", ".manifest")) \
                    or nazwa.lower() in ("base_library.zip",):
                if _plik_zawiera(os.path.join(korzen, nazwa), wzorce):
                    return True
    return False


if __name__ == "__main__":
    w = wersja_zrodla()
    if len(sys.argv) > 1:
        sys.exit(0 if build_ma_wersje(sys.argv[1], w) else 1)
    print(w)
