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

JEDNO ŹRÓDŁO PRAWDY BUDOWANIA: to samo polecenie (--folder) uruchamia
robot na GitHubie (.github/workflows/build.yml) na Windows, macOS
i Linuksie. Listy modułów (WYMAGANE, UKRYTE, PROTOTYP), plików (DANE),
ikona, --onedir, --noupx i metadane .exe są TYLKO tutaj. Do 3.22.0 CI
miało własną, krótszą listę --hidden-import i paczka z GitHuba nie
zawierała nowego wyglądu ani okna logowania.
"""

import os
import re
import shutil
import subprocess
import sys

KATALOG = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(KATALOG, "BUDOWANIE_log.txt")

# Widżety nowego wyglądu — to on jest ekranem programu.
# Leżą w podfolderze prototyp\ — PyInstaller znajduje je dzięki --paths
# (patrz buduj()), a do paczki wchodzą jako zwykłe moduły.
PROTOTYP = ["proto_styl", "proto_dane", "proto_mapa", "proto_tasma",
            "proto_kompas", "proto_taca", "proto_okno", "proto_spektakl"]
WYMAGANE = ["PMT_Delegacje.py", "karta_testera.py",
            "wyglad_3d.py", "pmt_dokumenty.py", "pmt_podpis.py",
            "pmt_wysylka.py", "nowy_wyglad.py",
            "okno_logowania.py", "logo_retro.py"] + [
            os.path.join("prototyp", n + ".py") for n in PROTOTYP]
# Pliki, ktore program NAPRAWDE otwiera w czasie dzialania. Wczesniej byla
# tu jeszcze siodemka nazw (logo_zabka.png, logo_biedronka.png, ...),
# ktorych nie ma ani w repozytorium, ani nigdzie w kodzie.
#
# menedzer.txt: nazwisko przełożonego to wartość WSPÓLNA dla całego zespołu
# (drukowana na każdej delegacji), więc pakujemy ją do paczki — inaczej każda
# z 65 osób musiałaby ręcznie dokładać plik obok programu. W 3.21.0-3.21.1
# plik był wyrzucony z paczki i rubryka wychodziła pusta. Do repozytorium
# plik NIE trafia (.gitignore) — i tylko to było realnym problemem.
# pmt.jpg / PMT.jpg (zapasowe nazwy logo, patrz znajdz_logo) i czcionki
# DejaVu do PDF-ów dokładało dotąd samo CI — lista jest teraz jedna.
#
# sekret.txt: wspólny sekret aplikacji (klucz HMAC, którym program podpisuje
# zapytania puls/sesja/reset_hasla do backendu). Do 3.23.0 był literałem
# w PMT_Delegacje.py — czyli w repozytorium i w jego historii. Teraz, jak
# menedzer.txt, leży poza kodem: obok zbuduj.py (u autora) albo z sekretu
# PMT_SEKRET (na GitHubie) i trafia do paczki; do repozytorium NIE (.gitignore).
DANE = ["ciemny.png", "jasny.png", "pmt_logo.png", "pmt_logo.ico",
        "pmt_logo_retro.png", "pmt_logo_retro.ico", "pmt.jpg", "PMT.jpg",
        "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "menedzer.txt", "sekret.txt"]
# winsound i PyQt6.QtMultimedia wypadly z listy razem z intrem (3.23.0):
# tylko ono gralo dzwiek.
UKRYTE = ["karta_testera", "wyglad_3d", "pmt_dokumenty",
          "pmt_podpis", "pmt_wysylka",
          "nowy_wyglad", "okno_logowania", "logo_retro"] + PROTOTYP
# Lista bibliotek czytana z requirements.txt — tego samego pliku, z którego
# korzysta budowanie na GitHubie. Dzięki temu obie drogi budowania nie mogą
# się rozjechać (tak zniknęło openpyxl z wydań budowanych w CI).
def _biblioteki():
    try:
        import shlex
        lista = []
        with open(os.path.join(KATALOG, "requirements.txt"), encoding="utf-8") as f:
            for l in f:
                l = l.strip()
                if not l or l.startswith("#"):
                    continue
                # opcje pip („--no-binary fonttools") idą do argv jako
                # OSOBNE tokeny — jako jeden „--no-binary fonttools" pip
                # ich nie rozpozna i całe doinstalowanie padnie
                lista.extend(shlex.split(l) if l.startswith("-") else [l])
        if lista:
            return lista
    except Exception:
        pass
    return ["PyQt6", "openpyxl", "fpdf2", "pillow", "pyinstaller"]


BIBLIOTEKI = None      # ustalane przy pierwszym użyciu (patrz przygotuj_biblioteki)


def _fonttools_czysty(py):
    """fontTools bez skompilowanych .pyd — patrz requirements.txt. Biblioteki
    „na miejscu" mogły zostać zainstalowane dawniej, z modułami natywnymi;
    wtedy przeinstalowujemy sam fontTools w wersji czysto pythonowej."""
    kod = ("import fontTools,glob,os;d=os.path.dirname(fontTools.__file__);"
           "print(len(glob.glob(d+'/**/*.pyd',recursive=True)+glob.glob(d+'/**/*.so',recursive=True)))")
    try:
        w = subprocess.run([py, "-c", kod], capture_output=True, text=True)
        if w.returncode == 0 and w.stdout.strip() == "0":
            return True
    except Exception:
        return True
    pisz("  fontTools ma moduły natywne (.pyd) — przeinstalowuję czysto pythonowo…")
    for dodatkowe in ([], ["--user"], ["--break-system-packages"]):
        w = subprocess.run([py, "-m", "pip", "install", "--no-binary", "fonttools",
                            "--force-reinstall", "--no-deps"] + dodatkowe + ["fonttools"],
                           capture_output=True, text=True)
        if w.returncode == 0:
            break
    w = subprocess.run([py, "-c", kod], capture_output=True, text=True)
    if w.returncode == 0 and w.stdout.strip() == "0":
        pisz("  fontTools: czysto pythonowy")
        return True
    pisz("  [UWAGA] fontTools nadal ma .pyd — Windows może je blokować (patrz START_TUTAJ 6b)")
    return False


def pisz(txt):
    try:
        print(txt, flush=True)
    except UnicodeEncodeError:         # potok bez UTF-8 (np. robot na Windows)
        print(txt.encode("ascii", "replace").decode("ascii"), flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(txt + "\n")
    except Exception:
        pass


def wersja_zrodla():
    with open(os.path.join(KATALOG, "PMT_Delegacje.py"), encoding="utf-8") as f:
        m = re.search(r'WERSJA_PROGRAMU\s*=\s*"([^"]+)"', f.read())
    return m.group(1) if m else ""


def uzgodnij_wersje_exe(wer, sciezka=None):
    """Metadane pliku .exe (wersja_exe.txt) mają nieść TEN SAM numer, co
    WERSJA_PROGRAMU w PMT_Delegacje.py — jedyne źródło numeru. Gdy plik
    został w tyle, poprawiamy go tu, zanim PyInstaller go wczyta; inaczej
    Windows pokazywałby we właściwościach .exe stary numer.
    Zwraca True, gdy plik trzeba było poprawić."""
    sciezka = sciezka or os.path.join(KATALOG, "wersja_exe.txt")
    if not os.path.exists(sciezka):
        return False
    czesci = [int(x) for x in re.findall(r"\d+", wer)[:3]]
    while len(czesci) < 3:
        czesci.append(0)
    krotka = "(%d, %d, %d, 0)" % tuple(czesci)
    with open(sciezka, encoding="utf-8", newline="") as f:
        tresc = f.read()
    nowa = re.sub(r"filevers=\([^)]*\)", "filevers=" + krotka, tresc)
    nowa = re.sub(r"prodvers=\([^)]*\)", "prodvers=" + krotka, nowa)
    nowa = re.sub(r"('(?:File|Product)Version',\s*')[^']*(')",
                  lambda m: m.group(1) + wer + m.group(2), nowa)
    if nowa == tresc:
        return False
    with open(sciezka, "w", encoding="utf-8", newline="") as f:
        f.write(nowa)
    pisz("  wersja_exe.txt uzgodniono ze źródłem: %s" % wer)
    return True


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
        _fonttools_czysty(py)
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
        _fonttools_czysty(py)
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


def ikona_programu():
    """Ikona wg systemu — tak, jak budowało CI: Windows .ico (logo retro,
    stare tylko zapasowo), macOS .icns. Na Linuksie PyInstaller ikonę
    pomija, więc jej nie podajemy."""
    if os.name == "nt":
        kandydaci = ["pmt_logo_retro.ico", "pmt_logo.ico"]
    elif sys.platform == "darwin":
        kandydaci = ["pmt_logo_retro.icns", "pmt_logo.icns",
                     "pmt_logo_retro.ico", "pmt_logo.ico"]
    else:
        kandydaci = []
    for n in kandydaci:
        if os.path.exists(os.path.join(KATALOG, n)):
            return os.path.join(KATALOG, n)
    return ""


def polecenie_pyinstallera(py, folderowo=True):
    """Pełne polecenie PyInstallera i lista dołączonych plików.
    Osobna funkcja, bo testy sprawdzają je bez budowania."""
    rozdz = ";" if os.name == "nt" else ":"
    args = [py, "-m", "PyInstaller", "--noconfirm", "--noupx", "--windowed",
            "--name", "PMT_Planer",
            "--onedir" if folderowo else "--onefile"]
    ikona = ikona_programu()
    if ikona:
        args += ["--icon", ikona]
    # metadane .exe (producent, opis, numer) — tylko Windows je ma;
    # na innych systemach PyInstaller by je pominął z ostrzeżeniem
    meta = os.path.join(KATALOG, "wersja_exe.txt")
    if os.name == "nt" and os.path.exists(meta):
        args += ["--version-file", meta]
    for m in UKRYTE:
        args += ["--hidden-import", m]
    # Moduły nowego wyglądu siedzą w podfolderze — bez tego PyInstaller
    # nie znalazłby proto_okno i program padłby dopiero u użytkownika.
    katalog_prototypu = os.path.join(KATALOG, "prototyp")
    if os.path.isdir(katalog_prototypu):
        args += ["--paths", katalog_prototypu]
    dolaczone = []
    zasoby = os.path.join(KATALOG, "zasoby")
    if os.path.isdir(zasoby):
        args += ["--add-data", "zasoby" + rozdz + "zasoby"]
        dolaczone.append("zasoby\\")
    widziane = set()
    for n in DANE:                      # każdy plik osobno i pewnie
        if os.path.exists(os.path.join(KATALOG, n)) \
                and os.path.normcase(n) not in widziane:
            widziane.add(os.path.normcase(n))   # pmt.jpg/PMT.jpg na Windows = jeden plik
            args += ["--add-data", n + rozdz + "."]
            dolaczone.append(n)
    args.append("PMT_Delegacje.py")
    return args, dolaczone


def moduly_wlasne():
    """Moduły z UKRYTE, które są NASZYMI plikami (bez systemowych
    i bibliotecznych) — te muszą się znaleźć w archiwum PYZ paczki."""
    return [m for m in UKRYTE if m != "winsound" and not m.startswith("PyQt6")]


def sprawdz_zawartosc_paczki(katalog_budowy=None):
    """Po budowie: czy każdy własny moduł (nowy wygląd, okno logowania,
    dokumenty, podpis, wysyłka, widżety z prototyp\\) naprawdę trafił do
    archiwum PYZ. PyInstaller wypisuje jego spis do build\\PMT_Planer\\
    PYZ-00.toc. Zwraca listę brakujących (pusta = w porządku)."""
    katalog_budowy = katalog_budowy or os.path.join(KATALOG, "build", "PMT_Planer")
    toc = os.path.join(katalog_budowy, "PYZ-00.toc")
    try:
        with open(toc, encoding="utf-8", errors="ignore") as f:
            tresc = f.read()
    except Exception:
        return ["(nie odczytałem %s)" % toc]
    return [m for m in moduly_wlasne() if "('%s'," % m not in tresc]


def buduj(py, folderowo=True):
    args, dolaczone = polecenie_pyinstallera(py, folderowo)
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


def dolacz_do_paczki(sc, wer):
    """Dokłada do dist\\PMT_Planer to samo, co robot na GitHubie:
    URUCHOM_PMT.bat (pierwsze uruchomienie), podpowiedź dla osób, które
    klikną program W ŚRODKU ZIP-a, i znacznik wersji pmt_wersja.txt
    (bez niego program nie pozna, że sąsiedni folder jest nowszy)."""
    kat = os.path.dirname(sc)
    for nazwa in ("URUCHOM_PMT.bat", "0_NAJPIERW_ROZPAKUJ_CALY_FOLDER.txt"):
        zr = os.path.join(KATALOG, nazwa)
        if not os.path.exists(zr):
            pisz("  [UWAGA] brak %s obok zbuduj.py — paczka bez tego pliku" % nazwa)
            continue
        try:
            shutil.copy2(zr, os.path.join(kat, nazwa))
            pisz("  dołączam: %s" % nazwa)
        except Exception as e:
            pisz("  [UWAGA] nie udało się dołączyć %s: %s" % (nazwa, e))
    try:
        with open(os.path.join(kat, "pmt_wersja.txt"), "w", encoding="utf-8") as f:
            f.write(wer)
    except Exception as e:
        pisz("  [UWAGA] nie zapisałem znacznika wersji: %s" % e)


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
    uzgodnij_wersje_exe(wer)
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
        try:
            with open(os.path.join(KATALOG, "menedzer.txt"), "rb") as f:
                _ile = len(f.read(200))
            pisz("Przełożony: menedzer.txt (%d bajtów) trafi do paczki" % _ile)
        except Exception:
            pass
    else:
        pisz("[UWAGA] Brak menedzer.txt w tym folderze - rubryka PRZELOZONY na")
        pisz("        delegacjach bedzie pusta (w programie nie ma pola do")
        pisz("        wpisania). Utworz plik menedzer.txt (jedna linia)")
        pisz("        obok zbuduj.py i zbuduj ponownie.")
    # Sekret aplikacji: tylko obecnosc i niepusta pierwsza linia — samej
    # wartosci ani jej dlugosci do raportu nie wypisujemy.
    _sekret = os.path.join(KATALOG, "sekret.txt")
    _sekret_jest = False
    if os.path.exists(_sekret):
        try:
            with open(_sekret, "rb") as f:
                _sekret_jest = bool(f.read(4096).lstrip(b"\xef\xbb\xbf\xff\xfe").strip())
        except Exception:
            pass
    if _sekret_jest:
        pisz("Sekret aplikacji: sekret.txt trafi do paczki")
    else:
        pisz("[UWAGA] Brak sekret.txt w tym folderze (albo plik pusty) - program nie")
        pisz("        podpisze zapytan do backendu, wiec puls, sesja i reset hasla")
        pisz("        beda ODRZUCANE (odmowa). Utworz plik sekret.txt (jedna linia,")
        pisz("        ten sam sekret co w SEKRETY_PMT w Apps Script) obok zbuduj.py")
        pisz("        i zbuduj ponownie. Patrz BACKEND_APPS_SCRIPT.txt.")
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
    # Paczka bez nowego wyglądu uruchomi się i po cichu pokaże stare okno —
    # dlatego brak KTÓREGOKOLWIEK własnego modułu przerywa budowanie.
    brak = sprawdz_zawartosc_paczki()
    if brak:
        pisz("[BŁĄD] W paczce brakuje modułów: " + ", ".join(brak))
        pisz("       (spis archiwum: build\\PMT_Planer\\PYZ-00.toc)")
        return 1
    pisz("W paczce są wszystkie własne moduły (%d): %s"
         % (len(moduly_wlasne()), ", ".join(moduly_wlasne())))
    if folderowo:
        dolacz_do_paczki(sc, wer)
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
        # Eksplorator z gotową paczką — ale nie na robocie GitHuba
        if os.name == "nt" and not os.environ.get("GITHUB_ACTIONS"):
            os.startfile(os.path.join(KATALOG, "dist"))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
