# -*- coding: utf-8 -*-
"""PMT Planer — bezpłatny podpis elektroniczny: paczka do podpisu
i rozpoznanie podpisanego pliku po powrocie użytkownika.

Moduł celowo nie zależy od PyQt6 ani od PMT_Delegacje.py — wyłącznie
biblioteka standardowa. Dzięki temu da się go sprawdzić osobno:

    python pmt_podpis.py          (uruchamia test własny na plikach tymczasowych)

Zakres: tylko ścieżki bezpłatne — profil zaufany i e-dowód. Program niczego
nie podpisuje sam i nie czyta metadanych podpisu. Przygotowuje paczkę,
podaje adres usługi, a po powrocie użytkownika rozpoznaje plik, który wrócił,
po SUMIE PRZESŁANEK (punktacja niżej), nie po zgadywaniu.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime

# --- ADRESY USŁUG ------------------------------------------------------------
# Wszystkie adresy w JEDNYM miejscu, nigdy sklejane w locie.
#
# KAŻDY Z NICH WYMAGA POTWIERDZENIA NA ŻYWEJ USŁUDZE przed wydaniem —
# gov.pl przestawia adresy usług bez zapowiedzi, a program, który otworzy
# użytkownikowi błąd 404, zostawia go bez miejsca na wgranie dokumentu.
URL_PODPIS_PROFIL_ZAUFANY = ("https://www.gov.pl/web/gov/"
                             "podpisz-dokument-elektronicznie-wykorzystaj-podpis-zaufany")
# UWAGA: to STRONA INFORMACYJNA o e-dowodzie, BEZ formularza wgrywania pliku.
# Docelowo ma tu być adres usługi podpisu obsługującej podpis osobisty
# (najpewniej ta sama usługa gov.pl co dla podpisu zaufanego) — DO POTWIERDZENIA.
# Do czasu potwierdzenia pozycja „e-dowód" nie wchodzi do wydania: patrz
# USLUGI_GOTOWE niżej.
URL_PODPIS_EDOWOD = "https://www.gov.pl/web/e-dowod"
URL_WALIDATOR_PODPISU = "https://www.gov.pl/web/gov/sprawdz-podpis-elektroniczny"

ADRESY_USLUG = {
    "profil_zaufany": URL_PODPIS_PROFIL_ZAUFANY,
    "e_dowod": URL_PODPIS_EDOWOD,
    "walidator": URL_WALIDATOR_PODPISU,
}
# Usługi potwierdzone na żywo i dopuszczone do wydania.
USLUGI_GOTOWE = ("profil_zaufany",)
# Nazwy zapasowe przyjmowane przez adres_uslugi(); w interfejsie e-dowód
# nazywamy „e-dowód (podpis osobisty)", nigdy „mObywatel".
_ALIASY_USLUG = {
    "pz": "profil_zaufany", "profil": "profil_zaufany",
    "profil zaufany": "profil_zaufany", "podpis zaufany": "profil_zaufany",
    "edowod": "e_dowod", "e dowod": "e_dowod", "dowod": "e_dowod",
    "podpis osobisty": "e_dowod",
    "sprawdz": "walidator", "weryfikacja": "walidator",
}

# --- STAŁE PACZKI ------------------------------------------------------------
NAZWA_PODFOLDERU = "Do_podpisu"
NAZWA_PODPISANE = "Podpisane"
NAZWA_MANIFESTU = "manifest_podpisu.json"
WERSJA_MANIFESTU = 1          # wersja SCHEMATU, nie wersja programu

STATUS_DO_PODPISU = "do_podpisu"
STATUS_PODPISANY = "podpisany"
STATUS_NIEAKTUALNY = "nieaktualny"

# --- STAŁE ROZPOZNAWANIA -----------------------------------------------------
# Rozszerzenia i sufiksy oddawane przez portale — DO POTWIERDZENIA na żywym
# pliku z każdej usługi. Zmieniamy je TYLKO tutaj.
ROZSZERZENIA_PODPISU = (".pdf", ".xades", ".xml", ".sig", ".zip")
SUFIKSY_PODPISU = ("-podpisany", "_podpisany", "-signed", "_signed", "-sig", "-xades")
# Pliki w trakcie pobierania i śmieci pakietu biurowego — nigdy ich nie liczymy.
ROZSZERZENIA_POMIJANE = (".crdownload", ".part", ".tmp", ".download")

PKT_NAZWA = 3
PKT_SUFIKS = 2
PKT_SWIEZOSC = 2
PKT_ROZSZERZENIE = 1
PROG_AUTOMAT = 5              # >= tyle punktów I punkt za nazwę → przyjmujemy
PROG_PYTANIA = 3              # >= tyle punktów → pytamy; niżej — cisza
MARGINES_CZASU_S = 60         # zapas na zegar: mtime > od_czasu - 60 s
LIMIT_WPISOW_SKANU = 300      # najnowsze wpisy z katalogu (Pobrane bywa ogromne)
LIMIT_ZUZYTYCH = 300          # ile zużytych plików pamięta manifest

DECYZJA_PRZYJMIJ = "przyjmij"
DECYZJA_ZAPYTAJ = "zapytaj"
DECYZJA_ODRZUC = "odrzuc"     # weto po identycznej sumie kontrolnej
DECYZJA_REMIS = "remis"       # kilka wpisów z tą samą punktacją — brak dopasowania

KOMUNIKAT_WETO = "To wciąż niepodpisany plik"

MIESIACE_PL = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
               "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]

# --- ogonki ------------------------------------------------------------------
# Prosta tablica podmian, bez unicodedata: nazwy plików z portali bywają
# w NFC albo NFD i dekodowane procentowo — obie strony porównania muszą
# przechodzić DOKŁADNIE tę samą normalizację.
_OGONKI = {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
           "ó": "o", "ś": "s", "ź": "z", "ż": "z"}
_TABLICA_OGONKOW = {}
for _mala, _bez in _OGONKI.items():
    _TABLICA_OGONKOW[ord(_mala)] = _bez
    _TABLICA_OGONKOW[ord(_mala.upper())] = _bez.upper()


def bez_ogonkow(tekst):
    """ąćęłńóśźż → acelnoszz (także wielkie litery). Nic więcej nie rusza."""
    return str(tekst or "").translate(_TABLICA_OGONKOW)


def _normalizuj(tekst):
    """Nazwa do porównań: bez ogonków, małe litery, tylko znaki alfanumeryczne."""
    return "".join(z for z in bez_ogonkow(tekst).lower() if z.isalnum())


_MIESIACE_NORM = [_normalizuj(m) for m in MIESIACE_PL]


def _teraz():
    return datetime.now().replace(microsecond=0).isoformat()


def _klucz_sciezki(sciezka):
    try:
        return os.path.normcase(os.path.abspath(str(sciezka)))
    except Exception:
        return str(sciezka)


# --- sumy kontrolne ----------------------------------------------------------
def suma_sha256(sciezka, blok=1024 * 1024):
    """SHA-256 pliku, czytany kawałkami — delegacje bywają duże."""
    skrot = hashlib.sha256()
    with open(sciezka, "rb") as f:
        for kawalek in iter(lambda: f.read(blok), b""):
            skrot.update(kawalek)
    return skrot.hexdigest()


# --- manifest ----------------------------------------------------------------
def sciezka_manifestu(folder_paczki):
    """Przyjmuje folder paczki albo gotową ścieżkę manifestu."""
    sc = os.path.abspath(str(folder_paczki))
    if os.path.isdir(sc):
        return os.path.join(sc, NAZWA_MANIFESTU)
    return sc


def wczytaj_manifest(sciezka):
    try:
        with open(sciezka_manifestu(sciezka), "r", encoding="utf-8") as f:
            dane = json.load(f)
        return dane if isinstance(dane, dict) else {}
    except Exception:
        return {}


def zapisz_manifest(sciezka, dane):
    """Zapis atomowy (tmp → os.replace). Manifest to robocza ewidencja
    programu, a nie dowód podpisania czegokolwiek — ale urwany plik JSON
    oznacza utratę informacji, co już poszło do podpisu."""
    cel = sciezka_manifestu(sciezka)
    tmp = cel + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dane, f, ensure_ascii=False, indent=2)
    os.replace(tmp, cel)
    return cel


def _manifest_jako_slownik(manifest):
    if isinstance(manifest, dict):
        return manifest
    return wczytaj_manifest(manifest)


# --- adresy ------------------------------------------------------------------
def adres_uslugi(rodzaj):
    """Adres strony podpisu dla danego rodzaju usługi.

    Przyjmuje „profil_zaufany", „e_dowod", „walidator" oraz kilka nazw
    zapasowych („e-dowód", „podpis zaufany", …). Nieznany rodzaj to błąd
    programisty, nie cichy None — inaczej program otworzyłby pustą stronę.
    """
    klucz = _normalizuj(rodzaj).replace(" ", "")
    prosty = str(rodzaj or "").strip().lower().replace("-", " ").replace("_", " ")
    prosty = bez_ogonkow(prosty)
    for kandydat in (str(rodzaj or "").strip().lower(), prosty, klucz):
        if kandydat in ADRESY_USLUG:
            return ADRESY_USLUG[kandydat]
        if kandydat in _ALIASY_USLUG:
            return ADRESY_USLUG[_ALIASY_USLUG[kandydat]]
    # ostatnia szansa: „edowod", „profilzaufany" bez separatorów
    for nazwa, adres in ADRESY_USLUG.items():
        if _normalizuj(nazwa) == klucz:
            return adres
    raise ValueError("Nieznany rodzaj usługi podpisu: %r" % (rodzaj,))


# --- katalog Pobrane ---------------------------------------------------------
def _pobrane_z_rejestru():
    if os.name != "nt":
        return ""
    try:
        import winreg
        klucz = (r"Software\Microsoft\Windows\CurrentVersion\Explorer"
                 r"\User Shell Folders")
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, klucz) as k:
            sc, _ = winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")
        return os.path.expandvars(sc)
    except Exception:
        return ""


def _pobrane_z_xdg():
    plik = os.path.join(os.path.expanduser("~"), ".config", "user-dirs.dirs")
    try:
        with open(plik, "r", encoding="utf-8") as f:
            for linia in f:
                linia = linia.strip()
                if not linia.startswith("XDG_DOWNLOAD_DIR"):
                    continue
                wartosc = linia.split("=", 1)[1].strip().strip('"')
                wartosc = wartosc.replace("$HOME", os.path.expanduser("~"))
                return os.path.expandvars(wartosc)
    except Exception:
        pass
    return ""


def sciezka_pobranych():
    """Katalog Pobrane użytkownika. Zwraca PARĘ (ścieżka, czy_prawdziwe_pobrane).

    Zejście do katalogu domowego jest celowo oznaczone drugim polem: katalog
    domowy nadaje się na katalog startowy okna wyboru pliku, ale NIE wolno go
    obserwować — nie ma w nim pobrań, jest za to wszystko inne.
    Kolejność: rejestr Windows / XDG → Downloads i Pobrane w katalogu domowym
    → te same nazwy w katalogach OneDrive → katalog domowy (czy_prawdziwe=False).
    """
    dom = os.path.expanduser("~")
    for kandydat in (_pobrane_z_rejestru(), _pobrane_z_xdg()):
        if kandydat and os.path.isdir(kandydat):
            return (kandydat, True)
    for nazwa in ("Downloads", "Pobrane"):
        sc = os.path.join(dom, nazwa)
        if os.path.isdir(sc):
            return (sc, True)
    # OneDrive — w firmach katalogi użytkownika bywają przeniesione
    try:
        for wpis in os.listdir(dom):
            if not wpis.lower().startswith("onedrive"):
                continue
            for nazwa in ("Downloads", "Pobrane"):
                sc = os.path.join(dom, wpis, nazwa)
                if os.path.isdir(sc):
                    return (sc, True)
    except Exception:
        pass
    return (dom, False)


# --- rozpoznanie nazwy folderu ----------------------------------------------
def rozpoznaj_folder(nazwa_folderu):
    """Z „Rozliczenie_Jan_Kowalski_Lipiec_2026r" robi ("Jan Kowalski", 7, 2026).

    Obsługuje też „Rozliczenie_z_planu_…". Czego nie rozpozna — zwraca puste,
    bo manifest ma mieć te pola zawsze, choćby puste.
    """
    baza = os.path.basename(str(nazwa_folderu or "").rstrip("\\/"))
    czesci = [c for c in baza.split("_") if c]
    imie, miesiac, rok = "", None, None
    idx = None
    for i in range(len(czesci) - 1, -1, -1):
        n = _normalizuj(czesci[i])
        if n in _MIESIACE_NORM:
            idx = i
            miesiac = _MIESIACE_NORM.index(n) + 1
            break
    if idx is None:
        return (imie, miesiac, rok)
    for token in czesci[idx + 1:]:
        cyfry = "".join(z for z in token if z.isdigit())
        if len(cyfry) == 4:
            rok = int(cyfry)
            break
    wstep = ("rozliczenie", "z", "planu")
    poczatek = 0
    while poczatek < idx and _normalizuj(czesci[poczatek]) in wstep:
        poczatek += 1
    imie = " ".join(czesci[poczatek:idx])
    return (imie, miesiac, rok)


# --- paczka ------------------------------------------------------------------
def _pliki_pdf(folder):
    znalezione = []
    try:
        with os.scandir(folder) as it:
            for wpis in it:
                try:
                    if not wpis.is_file():
                        continue
                except OSError:
                    continue
                if wpis.name.startswith("~$"):
                    continue
                if os.path.splitext(wpis.name)[1].lower() != ".pdf":
                    continue
                znalezione.append(wpis.name)
    except OSError:
        return []
    znalezione.sort()
    return znalezione


def _uzupelnij_wpis(wpis):
    for pole, domyslne in (("plik", ""), ("plik_zrodlowy", ""), ("skrot", ""),
                           ("rozmiar", 0), ("utworzono", ""),
                           ("status", STATUS_DO_PODPISU), ("podpisany_plik", None),
                           ("skrot_podpisanego", None), ("podpisano", None),
                           ("dostawca_deklarowany", None)):
        wpis.setdefault(pole, domyslne)
    return wpis


def przygotuj_paczke(folder_dokumentow, folder_docelowy=None):
    """Buduje podfolder „Do_podpisu" z kopiami PDF-ów i manifestem.

    folder_dokumentow — folder wyniku z gotowymi PDF-ami.
    folder_docelowy   — katalog, W KTÓRYM powstaje podfolder „Do_podpisu"
                        (domyślnie ten sam folder co dokumenty).

    Zwraca (ścieżka_folderu_paczki, lista_wpisów).

    Kopiujemy shutil.copy2 (daty zachowane), nigdy nie przenosimy oryginałów.
    Nazwy kopii idą BEZ ogonków — portale różnie traktują diakrytyki w nazwach;
    nazwa oryginalna zostaje w polu „plik_zrodlowy". Do paczki idą wyłącznie
    pliki .pdf — podgląd tras (.html) podpisowi nie podlega.

    Powtórne wejście: wpis o tej samej sumie kontrolnej NIE jest kopiowany
    ponownie (statusy zostają), wpis o innej sumie odświeżamy i odkładamy stary
    do „historia_podpisow", a wpis bez pliku źródłowego dostaje status
    „nieaktualny" — jego kopii nie kasujemy, bo może być już podpisana.
    """
    zrodlo = os.path.abspath(str(folder_dokumentow or ""))
    if not os.path.isdir(zrodlo):
        raise ValueError("Nie ma folderu z dokumentami: %s" % zrodlo)
    baza = os.path.abspath(str(folder_docelowy)) if folder_docelowy else zrodlo
    paczka = os.path.join(baza, NAZWA_PODFOLDERU)
    os.makedirs(paczka, exist_ok=True)

    stary = wczytaj_manifest(paczka)
    stare_wpisy = {}
    for w in stary.get("pliki", []):
        if isinstance(w, dict) and w.get("plik"):
            stare_wpisy[w["plik"]] = _uzupelnij_wpis(dict(w))
    historia = [h for h in stary.get("historia_podpisow", []) if isinstance(h, dict)]

    teraz = _teraz()
    wpisy = []
    uzyte_nazwy = set()
    for nazwa in _pliki_pdf(zrodlo):
        zrodlowy = os.path.join(zrodlo, nazwa)
        docelowa = bez_ogonkow(nazwa)
        if docelowa in uzyte_nazwy:            # kolizja po zdjęciu ogonków
            rdzen, roz = os.path.splitext(docelowa)
            licznik = 2
            while "%s_%d%s" % (rdzen, licznik, roz) in uzyte_nazwy:
                licznik += 1
            docelowa = "%s_%d%s" % (rdzen, licznik, roz)
        uzyte_nazwy.add(docelowa)
        skrot = suma_sha256(zrodlowy)
        rozmiar = os.path.getsize(zrodlowy)
        cel = os.path.join(paczka, docelowa)
        poprzedni = stare_wpisy.pop(docelowa, None)
        if poprzedni and poprzedni.get("skrot") == skrot and os.path.exists(cel):
            wpis = poprzedni                    # bez ponownego kopiowania
        else:
            if poprzedni:
                historia.append({"plik": poprzedni.get("plik"),
                                 "skrot": poprzedni.get("skrot"),
                                 "status": poprzedni.get("status"),
                                 "podpisany_plik": poprzedni.get("podpisany_plik"),
                                 "podpisano": poprzedni.get("podpisano"),
                                 "zastapiono": teraz})
            shutil.copy2(zrodlowy, cel)
            wpis = _uzupelnij_wpis({"plik": docelowa, "utworzono": teraz,
                                    "status": STATUS_DO_PODPISU})
        wpis["plik_zrodlowy"] = nazwa
        wpis["skrot"] = skrot
        wpis["rozmiar"] = rozmiar
        wpisy.append(wpis)

    # wpisy bez pliku źródłowego (poprzednia generacja) — zostają, ale oznaczone
    for pozostaly in stare_wpisy.values():
        pozostaly["status"] = STATUS_NIEAKTUALNY
        wpisy.append(pozostaly)

    imie, miesiac, rok = rozpoznaj_folder(zrodlo)
    manifest = {
        "program": "PMT Planer",
        "wersja_manifestu": WERSJA_MANIFESTU,
        "utworzono": stary.get("utworzono") or teraz,
        "zaktualizowano": teraz,
        "folder_zrodlowy": zrodlo,
        "folder_paczki": paczka,
        "imie": imie or stary.get("imie", ""),
        "miesiac": miesiac if miesiac is not None else stary.get("miesiac"),
        "rok": rok if rok is not None else stary.get("rok"),
        "dostawca_deklarowany": stary.get("dostawca_deklarowany"),
        "pliki": wpisy,
        "historia_podpisow": historia[-LIMIT_ZUZYTYCH:],
        "zuzyte_pliki": [z for z in stary.get("zuzyte_pliki", [])
                         if isinstance(z, dict)][-LIMIT_ZUZYTYCH:],
    }
    zapisz_manifest(paczka, manifest)
    return (paczka, wpisy)


# --- rozpoznanie pliku podpisanego ------------------------------------------
def _znane_sciezki(dane):
    """Kopie z paczki, oryginały i już skopiowane podpisy — pomijamy je
    w ciszy, bez punktowania i bez komunikatu. Leżą w obserwowanych
    katalogach stale i z założenia."""
    zbior = set()
    zrodlo = dane.get("folder_zrodlowy") or ""
    paczka = dane.get("folder_paczki") or ""
    podpisane = os.path.join(paczka, NAZWA_PODPISANE) if paczka else ""
    for w in dane.get("pliki", []):
        if not isinstance(w, dict):
            continue
        pary = ((paczka, w.get("plik")), (zrodlo, w.get("plik_zrodlowy")),
                (zrodlo, w.get("plik")), (podpisane, w.get("podpisany_plik")))
        for katalog, nazwa in pary:
            if katalog and nazwa:
                zbior.add(_klucz_sciezki(os.path.join(katalog, nazwa)))
    return zbior


def _klucz_zuzytego(sciezka, mtime, rozmiar):
    return (_klucz_sciezki(sciezka), int(mtime), int(rozmiar))


def _zuzyte_klucze(dane):
    zbior = set()
    for z in dane.get("zuzyte_pliki", []):
        if not isinstance(z, dict):
            continue
        try:
            zbior.add(_klucz_zuzytego(z.get("sciezka", ""), z.get("mtime", 0),
                                      z.get("rozmiar", 0)))
        except (TypeError, ValueError):
            continue
    return zbior


def _skanuj_katalog(katalog, limit=LIMIT_WPISOW_SKANU):
    """Skan NIEREKURENCYJNY. Wejście w podkatalogi zapętliłoby wykrywanie:
    „Podpisane" leży w „Do_podpisu", a skopiowany tam plik zbiera komplet
    punktów i zostaje wykryty po raz drugi, trzeci i dziesiąty."""
    znalezione = []
    try:
        with os.scandir(katalog) as it:
            for wpis in it:
                try:
                    if not wpis.is_file():
                        continue
                    if wpis.name.startswith("~$"):
                        continue
                    if os.path.splitext(wpis.name)[1].lower() in ROZSZERZENIA_POMIJANE:
                        continue
                    st = wpis.stat()
                except OSError:
                    continue
                znalezione.append((wpis.path, st.st_mtime, st.st_size))
    except (OSError, ValueError):
        return []
    znalezione.sort(key=lambda t: (-t[1], t[0]))
    return znalezione[:limit]


def _skladniki_punktacji(nazwa_pliku, mtime, od_czasu, rdzen_wpisu):
    """Punkty jednego pliku wobec JEDNEGO wpisu manifestu."""
    rdzen_kandydata, rozszerzenie = os.path.splitext(nazwa_pliku)
    rozszerzenie = rozszerzenie.lower()
    nazwa = _normalizuj(rdzen_kandydata)
    trafiona_nazwa = bool(rdzen_wpisu) and rdzen_wpisu in nazwa
    plaska = bez_ogonkow(rdzen_kandydata).lower()
    sufiks = any(s in plaska for s in SUFIKSY_PODPISU)
    swiezy = (od_czasu is not None
              and float(mtime) > float(od_czasu) - MARGINES_CZASU_S)
    return {
        "nazwa": PKT_NAZWA if trafiona_nazwa else 0,
        "sufiks": PKT_SUFIKS if sufiks else 0,
        "swiezosc": PKT_SWIEZOSC if swiezy else 0,
        "rozszerzenie": PKT_ROZSZERZENIE if rozszerzenie in ROZSZERZENIA_PODPISU else 0,
    }


def znajdz_podpisane(manifest, katalogi, od_czasu):
    """Przegląda katalogi i dopasowuje pliki podpisane do wpisów manifestu.

    manifest  — słownik manifestu albo ścieżka do niego (także folder paczki).
    katalogi  — katalogi do przejrzenia, każdy NIEREKURENCYJNIE.
    od_czasu  — moment otwarcia strony usługi (czas epoki); None wyłącza punkt
                za świeżość.

    Zwraca listę słowników — po jednym na plik, o którym jest co powiedzieć:
        sciezka, plik (nazwa wpisu z manifestu albo None), punkty, decyzja,
        skladniki, skrot, rozmiar, mtime, powod, kandydaci
    decyzja:
        „przyjmij" — >= 5 punktów I punkt za nazwę (pliki .zip nigdy);
        „zapytaj"  — 3-4 punkty albo komplet punktów bez trafionej nazwy;
        „odrzuc"   — WETO: suma kontrolna identyczna z oryginałem, więc plik
                     nie jest podpisany (podpisany PDF ma z definicji inną sumę);
        „remis"    — kilka wpisów z tą samą punktacją: brak dopasowania,
                     nazwa wpisu to None, nazwy kandydatów w „kandydaci".
    Pliki poniżej 3 punktów, kopie z paczki, oryginały i pliki już zużyte
    pomijamy w ciszy — nie ma po nich wpisu w wyniku.
    """
    dane = _manifest_jako_slownik(manifest)
    wpisy = [w for w in dane.get("pliki", []) if isinstance(w, dict)]
    dostepne = [w for w in wpisy if w.get("status", STATUS_DO_PODPISU) == STATUS_DO_PODPISU]
    skroty = {}
    for w in wpisy:
        if w.get("skrot"):
            skroty.setdefault(w["skrot"], w.get("plik"))
    rozmiary = {int(w.get("rozmiar") or 0) for w in wpisy}
    znane = _znane_sciezki(dane)
    zuzyte = _zuzyte_klucze(dane)
    rdzenie = {w.get("plik"): _normalizuj(os.path.splitext(w.get("plik") or "")[0])
               for w in wpisy}

    pliki = []
    widziane = set()
    for katalog in (katalogi or []):
        if not katalog:
            continue
        for sciezka, mtime, rozmiar in _skanuj_katalog(katalog):
            klucz = _klucz_sciezki(sciezka)
            if klucz in widziane or klucz in znane:
                continue
            if _klucz_zuzytego(sciezka, mtime, rozmiar) in zuzyte:
                continue
            widziane.add(klucz)
            pliki.append((sciezka, mtime, rozmiar))
    pliki.sort(key=lambda t: (-t[1], t[0]))

    wyniki = []
    zajete = set()
    for sciezka, mtime, rozmiar in pliki:
        nazwa = os.path.basename(sciezka)
        rozszerzenie = os.path.splitext(nazwa)[1].lower()

        # WETO przed liczeniem punktów: identyczna suma kontrolna znaczy,
        # że użytkownik pobrał z powrotem tę samą, NIEPODPISANĄ kopię.
        # Sumę liczymy tylko wtedy, gdy rozmiar w ogóle pozwala na trafienie.
        skrot = None
        if int(rozmiar) in rozmiary:
            try:
                skrot = suma_sha256(sciezka)
            except OSError:
                continue
            if skrot in skroty:
                wyniki.append({"sciezka": sciezka, "plik": None, "punkty": 0,
                               "decyzja": DECYZJA_ODRZUC, "skladniki": {},
                               "skrot": skrot, "rozmiar": int(rozmiar),
                               "mtime": float(mtime), "powod": KOMUNIKAT_WETO,
                               "kandydaci": [skroty[skrot]] if skroty[skrot] else []})
                continue

        najlepsze, punkty_max = [], 0
        skladniki_max = {}
        for wpis in dostepne:
            if wpis.get("plik") in zajete:
                continue
            skladniki = _skladniki_punktacji(nazwa, mtime, od_czasu,
                                             rdzenie.get(wpis.get("plik"), ""))
            suma = sum(skladniki.values())
            if suma > punkty_max:
                punkty_max, najlepsze, skladniki_max = suma, [wpis], skladniki
            elif suma == punkty_max and suma > 0:
                najlepsze.append(wpis)
        if punkty_max < PROG_PYTANIA or not najlepsze:
            continue

        if skrot is None:
            try:
                skrot = suma_sha256(sciezka)
            except OSError:
                continue

        wynik = {"sciezka": sciezka, "plik": None, "punkty": punkty_max,
                 "decyzja": DECYZJA_ZAPYTAJ, "skladniki": dict(skladniki_max),
                 "skrot": skrot, "rozmiar": int(rozmiar), "mtime": float(mtime),
                 "powod": "", "kandydaci": [w.get("plik") for w in najlepsze]}
        if len(najlepsze) > 1:
            # Kilka wpisów z tą samą punktacją — nie zgadujemy „pierwszy z listy".
            wynik["decyzja"] = DECYZJA_REMIS
            wynik["powod"] = "remis punktowy: %d pkt dla %d dokumentów" % (
                punkty_max, len(najlepsze))
            wyniki.append(wynik)
            continue
        wpis = najlepsze[0]
        wynik["plik"] = wpis.get("plik")
        automat = (punkty_max >= PROG_AUTOMAT and skladniki_max.get("nazwa")
                   and rozszerzenie != ".zip")
        if automat:
            wynik["decyzja"] = DECYZJA_PRZYJMIJ
            zajete.add(wpis.get("plik"))
        elif rozszerzenie == ".zip":
            wynik["powod"] = "archiwum — nie rozpakowujemy"
        elif not skladniki_max.get("nazwa"):
            wynik["powod"] = "nazwa nie wskazuje dokumentu"
        else:
            wynik["powod"] = "za mało przesłanek"
        wyniki.append(wynik)
    return wyniki


def oznacz_podpisany(manifest_sciezka, plik, dopasowanie):
    """Zapisuje stan w manifeście i zwraca zaktualizowany manifest.

    plik        — nazwa wpisu z manifestu (pole „plik"). None albo puste znaczy
                  „tylko odnotuj plik jako zużyty" — tak zapamiętujemy odpowiedź
                  „nie, szukaj dalej", żeby to samo pytanie nie wróciło za 5 s.
    dopasowanie — słownik z znajdz_podpisane (albo ręcznie złożony: wymaga
                  klucza „sciezka"); pola „skrot", „rozmiar", „mtime",
                  „podpisany_plik" i „dostawca_deklarowany" są opcjonalne.

    Nie kopiuje plików — kopiowanie do „Podpisane/" należy do warstwy okna,
    razem z obsługą kolizji nazw. Zapis jest atomowy.
    """
    cel = sciezka_manifestu(manifest_sciezka)
    dane = wczytaj_manifest(cel)
    if not dane:
        raise ValueError("Nie wczytałem manifestu: %s" % cel)
    d = dict(dopasowanie or {})
    if d.get("decyzja") == DECYZJA_ODRZUC and plik:
        raise ValueError("Plik odrzucony wetem nie może oznaczyć wpisu %r" % plik)
    teraz = _teraz()
    znaleziony = str(d.get("sciezka") or "")

    if plik:
        trafiony = None
        for w in dane.get("pliki", []):
            if isinstance(w, dict) and w.get("plik") == plik:
                trafiony = _uzupelnij_wpis(w)
                break
        if trafiony is None:
            raise ValueError("W manifeście nie ma wpisu %r" % plik)
        trafiony["status"] = STATUS_PODPISANY
        trafiony["podpisany_plik"] = (d.get("podpisany_plik")
                                      or (os.path.basename(znaleziony) or None))
        trafiony["skrot_podpisanego"] = d.get("skrot")
        trafiony["podpisano"] = d.get("podpisano") or teraz
        trafiony["dostawca_deklarowany"] = d.get("dostawca_deklarowany")

    if znaleziony:
        zuzyte = [z for z in dane.get("zuzyte_pliki", []) if isinstance(z, dict)]
        mtime = d.get("mtime")
        rozmiar = d.get("rozmiar")
        if mtime is None or rozmiar is None:
            try:
                st = os.stat(znaleziony)
                mtime = st.st_mtime if mtime is None else mtime
                rozmiar = st.st_size if rozmiar is None else rozmiar
            except OSError:
                mtime = mtime or 0
                rozmiar = rozmiar or 0
        nowy = {"sciezka": znaleziony, "mtime": int(mtime), "rozmiar": int(rozmiar),
                "skrot": d.get("skrot"), "odnotowano": teraz,
                "wpis": plik or None}
        klucz = _klucz_zuzytego(nowy["sciezka"], nowy["mtime"], nowy["rozmiar"])
        if all(_klucz_zuzytego(z.get("sciezka", ""), z.get("mtime", 0),
                               z.get("rozmiar", 0)) != klucz for z in zuzyte):
            zuzyte.append(nowy)
        dane["zuzyte_pliki"] = zuzyte[-LIMIT_ZUZYTYCH:]

    dane["zaktualizowano"] = teraz
    zapisz_manifest(cel, dane)
    return dane


# --- test własny -------------------------------------------------------------
_BLEDY = []


def _sprawdz(warunek, opis):
    if warunek:
        print("  ok   %s" % opis)
    else:
        _BLEDY.append(opis)
        print("  BŁĄD %s" % opis)


def _zapisz_pdf(sciezka, tresc, mtime=None):
    with open(sciezka, "wb") as f:
        f.write(b"%PDF-1.4\n" + tresc + b"\n%%EOF\n")
    if mtime is not None:
        os.utime(sciezka, (mtime, mtime))
    return sciezka


def main():
    print("pmt_podpis — test własny")
    teraz = time.time()
    otwarcie = teraz - 120        # moment otwarcia strony usługi
    swiezo = teraz - 10

    with tempfile.TemporaryDirectory(prefix="pmt_podpis_") as baza:
        folder = os.path.join(baza, "Rozliczenie_Jan_Kowalski_Lipiec_2026r")
        os.makedirs(folder)
        d1 = _zapisz_pdf(os.path.join(folder, "delegacja_01_Jan_Kowalski_Lipiec_2026r.pdf"),
                         b"delegacja pierwsza")
        _zapisz_pdf(os.path.join(folder, "delegacja_02_Jan_Kowalski_Lipiec_2026r.pdf"),
                    b"delegacja druga")
        _zapisz_pdf(os.path.join(folder, "rozliczenie_wydatków_Jan_Kowalski_Lipiec_2026r.pdf"),
                    b"zbiorcze rozliczenie")
        with open(os.path.join(folder, "Trasy_Mapa.html"), "w", encoding="utf-8") as f:
            f.write("<html></html>")

        # 1. paczka i manifest
        paczka, wpisy = przygotuj_paczke(folder)
        manifest_plik = os.path.join(paczka, NAZWA_MANIFESTU)
        dane = wczytaj_manifest(manifest_plik)
        _sprawdz(os.path.basename(paczka) == NAZWA_PODFOLDERU, "paczka to podfolder Do_podpisu")
        _sprawdz(len(wpisy) == 3, "w paczce 3 pliki PDF, bez Trasy_Mapa.html")
        _sprawdz(os.path.exists(os.path.join(
            paczka, "rozliczenie_wydatkow_Jan_Kowalski_Lipiec_2026r.pdf")),
            "kopia zbiorczego bez ogonków w nazwie")
        _sprawdz(all(k in dane for k in ("imie", "miesiac", "rok", "folder_zrodlowy")),
                 "manifest ma imie, miesiac, rok, folder_zrodlowy")
        _sprawdz((dane.get("imie"), dane.get("miesiac"), dane.get("rok"))
                 == ("Jan Kowalski", 7, 2026), "rozpoznane imię, miesiąc i rok")
        _sprawdz(all(k in wpisy[0] for k in ("plik", "skrot", "rozmiar", "utworzono")),
                 "wpis ma plik, skrot, rozmiar, utworzono")
        _sprawdz(wpisy[0]["skrot"] == suma_sha256(d1), "suma kontrolna zgodna z plikiem")

        # 2. adresy usług
        _sprawdz(adres_uslugi("profil_zaufany").startswith("https://"),
                 "adres profilu zaufanego")
        _sprawdz(adres_uslugi("e-dowód") == URL_PODPIS_EDOWOD, "adres e-dowodu po aliasie")
        try:
            adres_uslugi("bank")
            _sprawdz(False, "nieznana usługa kończy się błędem")
        except ValueError:
            _sprawdz(True, "nieznana usługa kończy się błędem")

        # 3. katalog Pobrane
        pobrane, prawdziwe = sciezka_pobranych()
        _sprawdz(isinstance(pobrane, str) and pobrane and os.path.isdir(pobrane),
                 "sciezka_pobranych zwraca istniejący katalog")
        _sprawdz(isinstance(prawdziwe, bool), "sciezka_pobranych mówi, czy to Pobrane")

        # 4. kopie z paczki i oryginały pomijane w ciszy
        ciche = znajdz_podpisane(dane, [paczka, folder], otwarcie)
        _sprawdz(ciche == [], "kopie z paczki i oryginały pomijane bez komunikatu")

        # 5. WETO: identyczna suma kontrolna
        pobrane_weto = os.path.join(baza, "Pobrane_weto")
        os.makedirs(pobrane_weto)
        weto_plik = os.path.join(pobrane_weto,
                                 "delegacja_01_Jan_Kowalski_Lipiec_2026r-podpisany.pdf")
        shutil.copyfile(d1, weto_plik)
        os.utime(weto_plik, (swiezo, swiezo))
        wynik = znajdz_podpisane(dane, [pobrane_weto], otwarcie)
        _sprawdz(len(wynik) == 1 and wynik[0]["decyzja"] == DECYZJA_ODRZUC,
                 "identyczna suma kontrolna = weto, mimo kompletu przesłanek")
        _sprawdz(all(w["decyzja"] not in (DECYZJA_PRZYJMIJ, DECYZJA_ZAPYTAJ)
                     for w in wynik), "plik z wetem nie trafia ani do przyjęcia, ani do pytania")
        try:
            oznacz_podpisany(manifest_plik, wpisy[0]["plik"], wynik[0])
            _sprawdz(False, "wetem nie da się oznaczyć wpisu jako podpisanego")
        except ValueError:
            _sprawdz(True, "wetem nie da się oznaczyć wpisu jako podpisanego")

        # 6. REMIS: nazwa neutralna pasuje tak samo do każdego wpisu
        pobrane_remis = os.path.join(baza, "Pobrane_remis")
        os.makedirs(pobrane_remis)
        _zapisz_pdf(os.path.join(pobrane_remis, "dokument_podpisany.pdf"),
                    b"cos zupelnie innego", swiezo)
        wynik = znajdz_podpisane(dane, [pobrane_remis], otwarcie)
        _sprawdz(len(wynik) == 1 and wynik[0]["punkty"] == 5,
                 "neutralna nazwa zbiera 5 punktów (próg automatu)")
        _sprawdz(wynik[0]["decyzja"] == DECYZJA_REMIS and wynik[0]["plik"] is None,
                 "remis punktowy = brak dopasowania, bez zgadywania")
        _sprawdz(len(wynik[0]["kandydaci"]) == 3, "remis wymienia wszystkich kandydatów")

        # 6b. ten sam plik przy JEDNYM wpisie: nadal pytanie, nie automat
        folder_maly = os.path.join(baza, "Rozliczenie_Anna_Nowak_Maj_2026r")
        os.makedirs(folder_maly)
        _zapisz_pdf(os.path.join(folder_maly, "delegacja_01_Anna_Nowak_Maj_2026r.pdf"),
                    b"pojedyncza delegacja")
        paczka_mala, _ = przygotuj_paczke(folder_maly)
        wynik = znajdz_podpisane(paczka_mala, [pobrane_remis], otwarcie)
        _sprawdz(len(wynik) == 1 and wynik[0]["decyzja"] == DECYZJA_ZAPYTAJ,
                 "5 punktów bez trafionej nazwy = pytanie, nigdy automat")

        # 7. poprawne dopasowanie i zapis stanu
        pobrane_ok = os.path.join(baza, "Pobrane")
        os.makedirs(pobrane_ok)
        podpisany = _zapisz_pdf(
            os.path.join(pobrane_ok, "delegacja_02_Jan_Kowalski_Lipiec_2026r-podpisany.pdf"),
            b"delegacja druga z podpisem", swiezo)
        wynik = znajdz_podpisane(manifest_plik, [pobrane_ok], otwarcie)
        _sprawdz(len(wynik) == 1 and wynik[0]["decyzja"] == DECYZJA_PRZYJMIJ,
                 "podpisany plik o trafionej nazwie przyjęty automatycznie")
        _sprawdz(wynik[0]["plik"] == "delegacja_02_Jan_Kowalski_Lipiec_2026r.pdf",
                 "przypisany do właściwego wpisu manifestu")
        po = oznacz_podpisany(manifest_plik, wynik[0]["plik"], wynik[0])
        stan = [w for w in po["pliki"] if w["plik"] == wynik[0]["plik"]][0]
        _sprawdz(stan["status"] == STATUS_PODPISANY and stan["podpisano"],
                 "manifest zapamiętał status podpisany i czas")
        _sprawdz(stan["skrot_podpisanego"] == suma_sha256(podpisany),
                 "manifest zapamiętał sumę kontrolną podpisanego pliku")
        _sprawdz(len(po.get("zuzyte_pliki", [])) == 1, "plik trafił do zużytych")

        # 8. ten sam plik nie może zostać dopasowany drugi raz
        powtorka = znajdz_podpisane(manifest_plik, [pobrane_ok], otwarcie)
        _sprawdz(powtorka == [], "raz dopasowany plik nie wraca przy kolejnym skanie")

        # 8b. odrzucenie użytkownika też zapamiętujemy
        obcy = _zapisz_pdf(os.path.join(pobrane_ok, "dokument_podpisany.pdf"),
                           b"obcy plik z podpisem", swiezo)
        przed = znajdz_podpisane(manifest_plik, [pobrane_ok], otwarcie)
        _sprawdz(len(przed) == 1 and przed[0]["decyzja"] == DECYZJA_REMIS,
                 "obcy plik pyta albo remisuje, nie wchodzi po cichu")
        oznacz_podpisany(manifest_plik, None, przed[0])
        _sprawdz(znajdz_podpisane(manifest_plik, [pobrane_ok], otwarcie) == [],
                 "odrzucony plik nie wraca z pytaniem")
        _sprawdz(os.path.exists(obcy), "oryginału w Pobranych nie kasujemy")

        # 9. powtórne wejście: bez ponownego kopiowania, ze śladem po zmianie
        kopia_przed = os.path.getmtime(os.path.join(paczka, os.path.basename(d1)))
        paczka2, wpisy2 = przygotuj_paczke(folder)
        dane2 = wczytaj_manifest(paczka2)
        stan2 = [w for w in dane2["pliki"]
                 if w["plik"] == "delegacja_02_Jan_Kowalski_Lipiec_2026r.pdf"][0]
        _sprawdz(paczka2 == paczka and len(wpisy2) == 3, "powtórne wejście nie mnoży wpisów")
        _sprawdz(stan2["status"] == STATUS_PODPISANY, "status podpisany przetrwał")
        _sprawdz(os.path.getmtime(os.path.join(paczka, os.path.basename(d1)))
                 == kopia_przed, "niezmieniony plik nie jest kopiowany ponownie")

        _zapisz_pdf(d1, b"delegacja pierwsza PO ZMIANIE KWOTY")
        os.remove(os.path.join(folder, "delegacja_02_Jan_Kowalski_Lipiec_2026r.pdf"))
        paczka3, wpisy3 = przygotuj_paczke(folder)
        dane3 = wczytaj_manifest(paczka3)
        nowy1 = [w for w in dane3["pliki"] if w["plik"] == os.path.basename(d1)][0]
        stary2 = [w for w in dane3["pliki"]
                  if w["plik"] == "delegacja_02_Jan_Kowalski_Lipiec_2026r.pdf"][0]
        _sprawdz(nowy1["skrot"] == suma_sha256(d1)
                 and nowy1["status"] == STATUS_DO_PODPISU,
                 "wygenerowany od nowa plik wraca do podpisu")
        _sprawdz(len(dane3.get("historia_podpisow", [])) == 1,
                 "po zmianie pliku zostaje ślad w historii")
        _sprawdz(stary2["status"] == STATUS_NIEAKTUALNY,
                 "wpis bez pliku źródłowego oznaczony jako nieaktualny")
        _sprawdz(os.path.exists(os.path.join(
            paczka, "delegacja_02_Jan_Kowalski_Lipiec_2026r.pdf")),
            "kopii nieaktualnego wpisu nie kasujemy")

    print("")
    if _BLEDY:
        print("NIE PRZESZŁO: %d" % len(_BLEDY))
        for b in _BLEDY:
            print("   - %s" % b)
        return 1
    print("wszystko przeszło")
    return 0


if __name__ == "__main__":
    sys.exit(main())
