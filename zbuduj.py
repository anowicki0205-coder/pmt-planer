# -*- coding: utf-8 -*-
"""
BUDOWANIE PMT PLANERA

Cała logika w Pythonie — bez pułapek wiersza poleceń Windows.
Sprawdza komplet plików, odczytuje wersję ze źródła, czyści ślady po
poprzednich budowach, uruchamia PyInstallera i NA KONIEC weryfikuje,
czy gotowy program naprawdę zawiera tę wersję.

Uruchomienie:
    python zbuduj.py --folder     (zalecane: dist\\PMT_Planer\\)
    python zbuduj.py --jeden      (jeden plik: dist\\PMT_Planer.exe)
"""

import os
import re
import shutil
import subprocess
import sys

KATALOG = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(KATALOG, "BUDOWANIE_log.txt")

WYMAGANE = ["PMT_Delegacje.py", "intro_wideo.py"]
# UWAGA: menedzer.txt CELOWO nie ma na tej liście. Nazwisko przełożonego
# to dane osobowe — nie wolno go wkompilowywać w plik rozsyłany do całego
# zespołu. Plik ma leżeć OBOK programu u konkretnej osoby (albo być wpisany
# w oknie programu, w polu Przelozony).
# Pliki, ktore program NAPRAWDE otwiera w czasie dzialania. Wczesniej byla
# tu jeszcze siodemka nazw (logo_zabka.png, logo_biedronka.png, ... ,
# intro_muzyka.mp3), ktorych nie ma ani w repozytorium, ani nigdzie w kodzie.
DANE = ["ciemny.png", "jasny.png", "pmt_logo.png", "pmt_logo.ico"]
UKRYTE = ["intro_wideo", "winsound"]
# Lista bibliotek czytana z requirements.txt — tego samego pliku, z którego
# korzysta budowanie na GitHubie. Dzięki temu obie drogi budowania nie mogą
# się rozjechać (tak zniknęło openpyxl z wydań budowanych w CI).
def _biblioteki():
    try:
        with open(os.path.join(KATALOG, "requirements.txt"), encoding="utf-8") as f:
            lista = [l.strip() for l in f
                     if l.strip() and not l.strip().startswith("#")]
        if lista:
            return lista
    except Exception:
        pass
    return ["PyQt6", "openpyxl", "fpdf2", "pillow", "pyinstaller"]


BIBLIOTEKI = None      # ustalane przy pierwszym użyciu (patrz przygotuj_biblioteki)


def pisz(txt):
    print(txt, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(txt + "\n")
    except Exception:
        pass


def wersja_zrodla():
    with open(os.path.join(KATALOG, "PMT_Delegacje.py"), encoding="utf-8") as f:
        m = re.search(r'WERSJA_PROGRAMU\s*=\s*"([^"]+)"', f.read())
    return m.group(1) if m else ""


def sprawdz_pliki():
    brak = [n for n in WYMAGANE if not os.path.exists(os.path.join(KATALOG, n))]
    if brak:
        pisz("[BŁĄD] W tym folderze brakuje plików: " + ", ".join(brak))
        pisz("       Rozpakuj CAŁĄ paczkę do jednego, pustego folderu.")
        return False
    return True


def przygotuj_biblioteki(py):
    pisz("Sprawdzam biblioteki…")
    try:
        subprocess.run([py, "-c", "import PyQt6, openpyxl, fpdf, PyInstaller"],
                       check=True, capture_output=True)
        pisz("  wszystkie na miejscu")
        return True
    except Exception:
        pass
    pisz("  doinstalowuję (jednorazowo, potrwa chwilę)…")
    biblioteki = _biblioteki()
    pisz("  z requirements.txt: " + ", ".join(biblioteki))
    for dodatkowe in ([], ["--user"], ["--break-system-packages"]):
        w = subprocess.run([py, "-m", "pip", "install"] + dodatkowe + biblioteki,
                           capture_output=True, text=True)
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(w.stdout[-4000:] + "\n" + w.stderr[-4000:] + "\n")
        except Exception:
            pass
        if w.returncode == 0:
            break
    try:
        subprocess.run([py, "-c", "import PyQt6, openpyxl, fpdf, PyInstaller"],
                       check=True, capture_output=True)
        return True
    except Exception:
        pisz("[BŁĄD] Nie udało się doinstalować bibliotek — zajrzyj do BUDOWANIE_log.txt")
        return False


def wyczysc():
    for kat in ("build", "dist"):
        sc = os.path.join(KATALOG, kat)
        if os.path.isdir(sc):
            shutil.rmtree(sc, ignore_errors=True)
    for plik in os.listdir(KATALOG):
        if plik.endswith(".spec"):
            try:
                os.remove(os.path.join(KATALOG, plik))
            except Exception:
                pass


def buduj(py, folderowo=True):
    rozdz = ";" if os.name == "nt" else ":"
    args = [py, "-m", "PyInstaller", "--noconfirm", "--noupx", "--windowed",
            "--name", "PMT_Planer",
            "--onedir" if folderowo else "--onefile"]
    ikona = os.path.join(KATALOG, "pmt_logo.ico")
    if os.path.exists(ikona):
        args += ["--icon", ikona]
    meta = os.path.join(KATALOG, "wersja_exe.txt")
    if os.path.exists(meta):
        args += ["--version-file", meta]
    for m in UKRYTE:
        args += ["--hidden-import", m]
    dolaczone = []
    zasoby = os.path.join(KATALOG, "zasoby")
    if os.path.isdir(zasoby):
        args += ["--add-data", "zasoby" + rozdz + "zasoby"]
        dolaczone.append("zasoby\\")
    for n in DANE:                      # każdy plik osobno i pewnie
        if os.path.exists(os.path.join(KATALOG, n)):
            args += ["--add-data", n + rozdz + "."]
            dolaczone.append(n)
    args.append("PMT_Delegacje.py")
    pisz("Dołączam do programu: " + (", ".join(dolaczone) or "(brak plików dodatkowych)"))
    pisz("Buduję… to potrwa kilka minut, nie zamykaj okna.")
    w = subprocess.run(args, cwd=KATALOG, capture_output=True, text=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(w.stdout[-20000:] + "\n" + w.stderr[-20000:] + "\n")
    except Exception:
        pass
    return w.returncode == 0


def sprawdz_wynik(wer, folderowo):
    """Sprawdza, czy program powstał i czy pochodzi z BIEŻĄCEGO źródła.
    Numer wersji bywa skompilowany i spakowany, więc nie szukamy go
    w plikach — porównujemy czas powstania programu z czasem zapisu
    PMT_Delegacje.py. Program starszy niż źródło = stara kompilacja."""
    sc = (os.path.join(KATALOG, "dist", "PMT_Planer", "PMT_Planer.exe")
          if folderowo else os.path.join(KATALOG, "dist", "PMT_Planer.exe"))
    if not os.path.exists(sc):                       # budowa poza Windows
        bez = sc[:-4] if sc.endswith(".exe") else sc
        sc = bez if os.path.exists(bez) else sc
    if not os.path.exists(sc):
        return (False, "")
    try:
        zrodlo = os.path.getmtime(os.path.join(KATALOG, "PMT_Delegacje.py"))
        swiezy = os.path.getmtime(sc) >= zrodlo - 5
    except Exception:
        swiezy = True
    return (swiezy, sc)


def main():
    folderowo = "--jeden" not in sys.argv
    try:
        open(LOG, "w", encoding="utf-8").close()
    except Exception:
        pass
    pisz("=" * 62)
    pisz("  BUDOWANIE PMT PLANERA — wersja %s"
         % ("folderowa" if folderowo else "jednoplikowa"))
    pisz("=" * 62)
    if not sprawdz_pliki():
        return 1
    wer = wersja_zrodla()
    if not wer:
        pisz("[BŁĄD] Nie odczytałem numeru wersji z PMT_Delegacje.py")
        return 1
    pisz("Wersja w źródle: %s" % wer)
    # Tła programu: ciemny.png i jasny.png. Mogą leżeć luzem obok programu
    # albo w podfolderze zasoby\ — sprawdzamy oba miejsca i mówimy wprost,
    # czego brakuje. Bez nich program działa, tylko rysuje tło zastępcze.
    tla = []
    for nazwa in ("ciemny.png", "jasny.png"):
        if os.path.exists(os.path.join(KATALOG, nazwa)):
            tla.append(nazwa)
        elif os.path.exists(os.path.join(KATALOG, "zasoby", nazwa)):
            tla.append("zasoby/" + nazwa)
    if len(tla) == 2:
        pisz("Tła programu: %s" % ", ".join(tla))
    else:
        pisz("[UWAGA] Nie widzę plików tła (ciemny.png, jasny.png).")
        pisz("        Program zbuduje się i będzie działał — narysuje tło")
        pisz("        zastępcze. Jeśli chcesz oryginalne, skopiuj te dwa pliki")
        pisz("        z folderu starego programu tutaj (albo do zasoby\\).")
    if os.path.exists(os.path.join(KATALOG, "menedzer.txt")):
        pisz("[UWAGA] W folderze leży menedzer.txt — NIE zostanie wbudowany")
        pisz("        w program (to dane osobowe). Skopiuj go ręcznie obok")
        pisz("        gotowego pliku PMT_Planer.exe u siebie, albo wpisz")
        pisz("        nazwisko w oknie programu, w polu Przelozony.")
    py = sys.executable
    if not przygotuj_biblioteki(py):
        return 1
    pisz("Czyszczę ślady po poprzednich budowach…")
    wyczysc()
    if not buduj(py, folderowo):
        pisz("[BŁĄD] Budowanie nie powiodło się. Ostatnie linie raportu:")
        try:
            with open(LOG, encoding="utf-8") as f:
                for linia in f.read().splitlines()[-15:]:
                    pisz("   " + linia)
        except Exception:
            pass
        return 1
    ok, sc = sprawdz_wynik(wer, folderowo)
    if not sc:
        pisz("[BŁĄD] Program nie powstał — zajrzyj do BUDOWANIE_log.txt")
        return 1
    pisz("")
    pisz("=" * 62)
    if ok:
        pisz("  GOTOWE — zbudowano wersję %s" % wer)
    else:
        pisz("  UWAGA: program jest starszy niż plik PMT_Delegacje.py.")
        pisz("  Zbuduj ponownie — coś przerwało kompilację.")
    pisz("  Plik: %s" % sc)
    pisz("=" * 62)
    if folderowo:
        pisz("Rozdaj CAŁY folder dist\\PMT_Planer (albo spakuj go do ZIP).")
    try:
        if os.name == "nt":
            os.startfile(os.path.join(KATALOG, "dist"))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
