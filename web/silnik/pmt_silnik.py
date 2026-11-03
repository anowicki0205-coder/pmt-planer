"""PMT — silnik delegacji WYCIĄGNIĘTY dosłownie z PMT_Delegacje.py przez narzedzia/wyciagnij_silnik.py.

NIE EDYTUJ RĘCZNIE: każda zmiana silnika dzieje się w programie na komputerze i trafia tu ponownym wyciągnięciem."""

# źródło: PMT_Delegacje.py sha256:9bb0062cd7bc2207

import sys

import os

import re

import json

import math

import random

import calendar

import datetime

import traceback

import itertools

import webbrowser

import subprocess

import zipfile

import urllib.request

import urllib.parse

import tempfile

import shutil

import hashlib

import unicodedata

from pathlib import Path

from dataclasses import dataclass, field

from typing import List, Dict, Optional, Tuple, Set

FPDF_BLAD = ""

try:
    from fpdf import FPDF
except Exception as _e_fpdf:
    FPDF_BLAD = "%s: %s" % (type(_e_fpdf).__name__, _e_fpdf)

    class FPDF:                       # atrapa — patrz _opis_bledu_pdf()
        def __init__(self, *a, **k):
            raise RuntimeError(_opis_bledu_pdf())

def _opis_bledu_pdf() -> str:
    """Czytelne wyjaśnienie, gdy biblioteka PDF nie weszła (FPDF_BLAD)."""
    tekst = ("Biblioteka do tworzenia PDF nie mogła się załadować:\n%s\n\n" % FPDF_BLAD)
    if "kontroli aplikacji" in FPDF_BLAD.lower() or "app control" in FPDF_BLAD.lower():
        tekst += ("Windows (Smart App Control albo zasady firmowe) zablokował jeden z plików "
                  "programu. Zaktualizuj program do wersji 3.21.4 lub nowszej — nie zawiera "
                  "tego pliku. Jeśli to nie pomoże, poproś administratora o dopuszczenie "
                  "folderu programu.")
    else:
        tekst += "Pobierz program ponownie z aktualnego wydania i rozpakuj CAŁY folder."
    return tekst

STAWKA_ZA_KM        = 0.60 

SREDNIA_PREDKOSC    = 65.0 

LIMIT_CZASU_MINUTY  = 8 * 60   # sufit dnia; ustaw_tryb_pracy() zmienia go w trybie wieczornym

MAX_KWOTA_DOKUMENTU  = 986.34

MAX_ETAPOW_DOKUMENTU = 30

MAX_KWOTA_DNIA       = 587.19

MIN_KWOTA           = 50.0 

MIN_ODLEGLOSC_OD_BAZY = 12.0   # km w linii prostej

PROCENT_WLASNE    = 0.50 

MIN_SIECI             = 1       

WAGI_SIECI = {1: 1.0, 2: 1.4, 3: 1.9, 4: 2.5, 5: 3.0}

def waga_sieci(sieci) -> float:
    """Mnożnik atrakcyjności miejscowości wg liczby sieci (1 → 1,0; 5 → 3,0)."""
    try:
        n = int(sieci)
    except (TypeError, ValueError):
        return 1.0
    return WAGI_SIECI.get(max(1, min(n, max(WAGI_SIECI))), 1.0)

TRYB_PRACY          = "tydzien"

NIEDZIELE_HANDLOWE  = False

GODZINA_STARTU_WIECZOR = "16:30"

def ustaw_tryb_pracy(tryb: str = "tydzien", dlugosc_dnia_h: float = None,
                     niedziele_handlowe: bool = None):
    """Przestawia silnik na wybrany tryb. Wywoływane PRZED generowaniem tras.

    dlugosc_dnia_h dotyczy trybu tygodniowego (domyślnie 3 h — tyle ustaliliśmy
    jako realny czas trasy). W trybie wieczornym długość wynika z okna
    16:30-22:00 i nie jest konfigurowalna.
    """
    global TRYB_PRACY, NIEDZIELE_HANDLOWE, LIMIT_CZASU_MINUTY, PRZERWA_JEDZENIE_MIN
    TRYB_PRACY = "wieczory" if str(tryb).startswith("wiecz") else "tydzien"
    if TRYB_PRACY == "wieczory":
        # Okno 16:30-22:00 to sufit dnia; wewnątrz niego silnik dalej miksuje
        # dni typu gniazdo / po drodze / daleki — tak jak w cyklu tygodniowym.
        LIMIT_CZASU_MINUTY = 5 * 60 + 30
        PRZERWA_JEDZENIE_MIN = 0              # krótkie okno, bez przerwy obiadowej
        NIEDZIELE_HANDLOWE = True             # jeśli w miesiącu są — silnik je wykorzysta
    else:
        LIMIT_CZASU_MINUTY = 8 * 60           # sufit dnia; realna długość wynika z typu dnia
        PRZERWA_JEDZENIE_MIN = 30
        NIEDZIELE_HANDLOWE = False
    return TRYB_PRACY, LIMIT_CZASU_MINUTY

TEST_MNOZNIK_TRASY = 1.28

MNOZNIK_MIN = 1.15

MNOZNIK_MAX = 1.30

MNOZNIK_DOL = 1.00

AWARIA_ROZRZUT = (0.90, 1.15)

AWARIA_POMIN_CO = 3

AWARIA_PROB = 6 

PRZERWA_JEDZENIE_MIN   = 30      # posiłek/odpoczynek wliczony w 8h

POSTOJ_MIN_MIN         = 12      # min. czas w miejscowości

POSTOJ_MAX_MIN         = 23      # max. czas w miejscowości

MAX_MIEJSCOWOSCI_DZIEN = 7       # górny limit punktów dziennie

POSTOJ_SREDNI_MIN      = (POSTOJ_MIN_MIN + POSTOJ_MAX_MIN) / 2.0   # 17,5 min

POSTOJE_TYPOWE         = 5       # tyle postojów ma przeciętny dzień (zakres 4–7)

def pojemnosc_dnia_km(postoje: int = None) -> float:
    """Ile kilometrów mieści się w jednej dobie przy takiej liczbie postojów."""
    if postoje is None: postoje = POSTOJE_TYPOWE
    minuty = (LIMIT_CZASU_MINUTY - PRZERWA_JEDZENIE_MIN
              - max(0, int(postoje)) * POSTOJ_SREDNI_MIN)
    return max(0.0, (minuty / 60.0) * SREDNIA_PREDKOSC)

def pojemnosc_dnia_zl(postoje: int = None, stawka: float = None,
                      limit_dnia: float = None) -> float:
    """Sufit kwoty jednego dnia: mniejsza z dwóch — fizyczna i regulaminowa."""
    if stawka is None: stawka = STAWKA_ZA_KM
    if limit_dnia is None: limit_dnia = MAX_KWOTA_DNIA
    return round(min(pojemnosc_dnia_km(postoje) * float(stawka), float(limit_dnia)), 2)

KM_TYPOWEGO_DNIA = 250.0

def kwota_typowego_dnia(stawka: float = None, limit_dnia: float = None) -> float:
    """Ile zarabia PRZECIĘTNY dzień — do szacowania LICZBY DNI.

    Do pytania „ile najwyżej da się rozpisać" służy pojemnosc_dnia_zl, która
    liczy sufit doby. Tu chodzi o coś innego: ile dni zajmie dana kwota."""
    if stawka is None: stawka = STAWKA_ZA_KM
    if limit_dnia is None: limit_dnia = MAX_KWOTA_DNIA
    return round(min(KM_TYPOWEGO_DNIA * float(stawka), float(limit_dnia)), 2)

def maks_kwota_miesiaca(ile_dni: int, stawka: float = None, postoje: int = None,
                        limit_dnia: float = None) -> float:
    """Górna granica kwoty miesiąca: dni robocze × realny sufit dnia.

    Sufit liczymy dla NAJGORSZEGO realnego dnia — pełnych MAX_MIEJSCOWOSCI_DZIEN
    postojów — a nie dla typowych pięciu. Pomiar na 2101 dniach pokazał, że 38 %
    dni ma sześć albo siedem postojów, a każdy postój zabiera z doby czas, który
    nie idzie na kilometry. Deklarowanie wyższego sufitu kończyło się tym, że
    program przyjmował kwotę, której potem nie potrafił rozpisać."""
    if postoje is None:
        postoje = MAX_MIEJSCOWOSCI_DZIEN
    return round(max(0, int(ile_dni)) * pojemnosc_dnia_zl(postoje, stawka, limit_dnia), 2)

def ile_dokumentow(kwota_zl: float) -> int:
    """Ile poleceń wyjazdu wychodzi z kwoty — sufit z kwoty przez sufit dokumentu."""
    return max(1, math.ceil((float(kwota_zl) - 0.005) / MAX_KWOTA_DOKUMENTU))

def rozdziel_rowno(kwota_zl: float, ile: int) -> List[float]:
    """Kwota na `ile` części równych CO DO GROSZA — suma części równa się kwocie."""
    ile = max(1, int(ile))
    grosze = int(round(float(kwota_zl) * 100))
    baza, reszta = divmod(grosze, ile)
    return [(baza + (1 if i < reszta else 0)) / 100.0 for i in range(ile)]

MAX_SKOK_MIEDZY_PUNKTAMI_KM = 35.0

def max_skok_bazowy(promien):
    """Bazowy maksymalny skok między punktami — nieco rośnie w większym promieniu."""
    return MAX_SKOK_MIEDZY_PUNKTAMI_KM if promien <= 70 else min(MAX_SKOK_MIEDZY_PUNKTAMI_KM * (promien/70.0), 55.0)

GEO_CACHE = os.path.join(os.path.expanduser("~"), ".pmt_geo_cache.json")

GEO_BRAKI = os.path.join(os.path.expanduser("~"), ".pmt_geo_braki.json")

NOTATKI_DNI_STORE = os.path.join(os.path.expanduser("~"), ".pmt_notatki_dni.json")

import time

import threading   # (pozostale importy sa juz na gorze programu)

URL_BACKENDU = "https://script.google.com/macros/s/AKfycbyKUur4Fhs90_I8w5qqB39V5nqSQgQYixkItuxvT3gu4HokQlaMz3yXbiL06S2jZgoYAw/exec"

PLIK_KOLEJKI = os.path.join(os.path.expanduser("~"), ".pmt_kolejka.json")

PLIK_STATUSU = os.path.join(os.path.expanduser("~"), ".pmt_status.json")

_blokada = threading.Lock()

def _wczytaj(plik, domyslne):
    try:
        with open(plik, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(domyslne)

def _zapisz(plik, dane):
    try:
        tmp = plik + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dane, f, ensure_ascii=False)
        os.replace(tmp, plik)          # zapis atomowy — brak "urwanych" plików
    except Exception:
        pass

def online_kod_uzytkownika():
    """Zwraca zapisany 5-cyfrowy kod albo None (trzeba zapytać w dialogu)."""
    kod = str(_wczytaj(PLIK_STATUSU, {}).get("kod", "")).strip()
    return kod if kod.isdigit() and len(kod) == 5 else None

def online_zdarzenie(uruchomienia=0, dokumenty=0, minuty=0):
    """Dopisuje zdarzenia do lokalnej kolejki. Błyskawiczne, bez internetu."""
    with _blokada:
        q = _wczytaj(PLIK_KOLEJKI, {"uruchomienia": 0, "dokumenty": 0, "minuty": 0})
        q["uruchomienia"] = int(q.get("uruchomienia", 0)) + uruchomienia
        q["dokumenty"]    = int(q.get("dokumenty", 0))    + dokumenty
        q["minuty"]       = int(q.get("minuty", 0))       + round(minuty)
        _zapisz(PLIK_KOLEJKI, q)

def online_synchronizuj() -> bool:
    """Jedna próba wysłania pulsu. True = sukces (kolejka wyzerowana,
    status odświeżony). Ciche niepowodzenie = zostajemy przy danych
    z pamięci podręcznej. NIE wywoływać z wątku interfejsu — patrz
    online_synchronizuj_w_tle()."""
    kod = online_kod_uzytkownika()
    if not kod or "TU_WKLEJ" in URL_BACKENDU:
        return False
    with _blokada:
        q = _wczytaj(PLIK_KOLEJKI, {"uruchomienia": 0, "dokumenty": 0, "minuty": 0})
    try:
        cialo = json.dumps(_podpisz_zadanie({
            "akcja": "puls", "kod": kod,
            "wersja": globals().get("WERSJA_PROGRAMU", "?"),
            "system": {"nt": "Windows"}.get(os.name,
                      "macOS" if __import__("sys").platform == "darwin" else "Linux"),
            "uruchomienia": q.get("uruchomienia", 0),
            "dokumenty":    q.get("dokumenty", 0),
            "minuty":       q.get("minuty", 0),
        })).encode("utf-8")
        req = urllib.request.Request(
            URL_BACKENDU, data=cialo,
            headers={"Content-Type": "application/json", "User-Agent": "PMT-Planer"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            odp = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return False

    if odp.get("status") not in ("ok", "wygasla"):
        return False           # np. zly_kod — kolejki nie zerujemy

    with _blokada:
        _zapisz(PLIK_KOLEJKI, {"uruchomienia": 0, "dokumenty": 0, "minuty": 0})
        st = _wczytaj(PLIK_STATUSU, {})
        st.update({
            "kod": kod,
            "status": odp.get("status"),
            "imie": odp.get("imie", ""),
            "rejon": odp.get("rejon", ""),
            "wazne_do": odp.get("wazne_do", ""),
            "nieobecnosci": odp.get("nieobecnosci", []),
            "ostatnia_synchronizacja": datetime.date.today().isoformat(),
        })
        _zapisz(PLIK_STATUSU, st)
    _zapamietaj_waznosc_konta(kod, odp.get("wazne_do", ""), odp.get("imie", ""), z_serwera=True)
    return True

def _katalogi_towarzyszace():
    """Wszystkie miejsca, w których może leżeć plik dołożony do programu.

    Program bywa uruchamiany na cztery sposoby i każdy daje inną ścieżkę:
      · ze źródeł           → katalog skryptu,
      · jako EXE folderowy  → katalog .exe ORAZ podkatalog _internal
                              (tam PyInstaller kładzie pliki z --add-data),
      · jako EXE jednoplikowy → katalog tymczasowy sys._MEIPASS,
      · ze skrótu z innym „Rozpocznij w" → bieżący katalog roboczy.
    Sprawdzamy wszystkie, bez powtórzeń."""
    kandydaci = []
    try:
        if getattr(sys, "frozen", False):
            kat_exe = os.path.dirname(os.path.abspath(sys.executable))
            kandydaci += [kat_exe, os.path.join(kat_exe, "_internal")]
    except Exception:
        pass
    for zrodlo in (lambda: os.path.dirname(os.path.abspath(sys.argv[0])),
                   lambda: getattr(sys, "_MEIPASS", ""),
                   lambda: os.getcwd()):
        try:
            k = zrodlo()
            if k:
                kandydaci.append(k)
        except Exception:
            continue
    wynik, widziane = [], set()
    for k in kandydaci:
        klucz = os.path.normcase(os.path.abspath(k))
        if klucz in widziane:
            continue
        widziane.add(klucz)
        wynik.append(k)
    return wynik

def _pierwsza_linia_pliku(sciezka) -> str:
    """Pierwsza niepusta linia pliku tekstowego. Radzi sobie z BOM-em,
    CRLF-em, plikiem zapisanym w Notatniku jako ANSI (cp1250) oraz jako
    „Unicode" (UTF-16 — Notatnik potrafi tak zapisać bez pytania)."""
    try:
        with open(sciezka, "rb") as f:
            poczatek = f.read(4)
        if poczatek[:2] in (b"\xff\xfe", b"\xfe\xff"):
            with open(sciezka, encoding="utf-16") as f:
                for linia in f:
                    linia = linia.strip()
                    if linia:
                        return linia
            return ""
    except Exception:
        pass
    for kodowanie in ("utf-8-sig", "cp1250", "latin-2"):
        try:
            with open(sciezka, encoding=kodowanie) as f:
                for linia in f:
                    linia = linia.strip()
                    if linia:
                        return linia
            return ""
        except UnicodeDecodeError:
            continue
        except Exception:
            return ""
    return ""

def _menedzer() -> str:
    """Nazwisko przełożonego drukowane na delegacji — trzymane POZA kodem.

    JEDYNE źródło: plik menedzer.txt obok programu, wkładany do paczki
    przy budowaniu z sekretu PMT_MENEDZER (u autora: plik obok zbuduj.py).
    Użytkownik nie ma pola do wpisania — nazwisko ma być zawsze to samo,
    a dane osobowe nie krążą w repozytorium ani w kodzie."""
    for kat in _katalogi_towarzyszace() + [os.path.expanduser("~")]:
        try:
            sc = os.path.join(kat, "menedzer.txt")
            if os.path.exists(sc):
                w = _pierwsza_linia_pliku(sc)
                if w:
                    return w
        except Exception:
            continue
    return ""

_SEKRET_PAMIEC = None          # odczyt raz na proces (None = jeszcze nie czytano)

_SEKRET_SZUKANE = []           # gdzie szukano pliku — do wpisu w dzienniku

def _sekret_aplikacji_dziennik():
    """Wpis „brak sekretu aplikacji" (z listą przeszukanych miejsc)
    do dziennika diagnostycznego — tylko gdy sekretu nie ma.

    Pierwszy odczyt w procesie robi ten wpis sam. Ale klik „Zaloguj"
    zaczyna dziennik OD NOWA (nowy=True), a sekret jest pamiętany do
    końca procesu — bez tej funkcji druga próba logowania kasowała
    wpis i nikt już go nie odtwarzał. Dlatego klik woła ją zaraz po
    rozpoczęciu dziennika: stan sekretu jest w nim po KAŻDEJ próbie.
    Jedno wywołanie = jeden wpis; z sekretem — nic."""
    if _SEKRET_PAMIEC is None:
        _sekret_aplikacji()        # pierwszy odczyt sam dopisuje wpis
        return
    if _SEKRET_PAMIEC:
        return
    try:
        _dziennik_animacji("brak sekretu aplikacji — zapytania do backendu bez podpisu"
                           " (puls, sesja, reset hasła będą odrzucane); szukano: "
                           + " | ".join(_SEKRET_SZUKANE) + " | zmienna PMT_SEKRET")
    except Exception:
        pass

def _sekret_aplikacji() -> str:
    """Sekret do podpisu zapytań — pierwsza linia sekret.txt z katalogów
    towarzyszących (jak menedzer.txt) i domowego, potem zmienna środowiskowa
    PMT_SEKRET. Brak = pusty napis: zapytania idą BEZ podpisu (backend
    odrzuca akcje podpisane) i dziennik diagnostyczny dostaje JEDEN wpis
    z listą przeszukanych miejsc (i znów po każdym kliku „Zaloguj" —
    _sekret_aplikacji_dziennik). Wynik jest pamiętany do końca procesu."""
    global _SEKRET_PAMIEC, _SEKRET_SZUKANE
    if _SEKRET_PAMIEC is not None:
        return _SEKRET_PAMIEC
    # Pierwszy odczyt idzie pod blokadą: dwa wątki naraz (logowanie i puls
    # w tle) dopisałyby dwa wpisy „brak sekretu" do dziennika.
    with _blokada:
        if _SEKRET_PAMIEC is not None:
            return _SEKRET_PAMIEC
        return _sekret_aplikacji_odczyt()

def _sekret_aplikacji_odczyt() -> str:
    """Samo szukanie sekretu — wołane raz, spod blokady."""
    global _SEKRET_PAMIEC, _SEKRET_SZUKANE
    szukane = []
    for kat in _katalogi_towarzyszace() + [os.path.expanduser("~")]:
        sc = os.path.join(kat, "sekret.txt")
        szukane.append(sc)
        try:
            if os.path.exists(sc):
                w = _pierwsza_linia_pliku(sc)
                if w:
                    _SEKRET_PAMIEC = w
                    return w
        except Exception:
            continue
    _SEKRET_SZUKANE = szukane
    w = str(os.environ.get("PMT_SEKRET", "") or "").strip()
    if w:
        _SEKRET_PAMIEC = w
        return w
    _SEKRET_PAMIEC = ""
    _sekret_aplikacji_dziennik()
    return ""

def _podpisz_zadanie(dane: dict) -> dict:
    """Dokłada znacznik czasu, wersję i podpis HMAC-SHA256 do zapytania.

    Klucz to _sekret_aplikacji(). Bez sekretu pola „podpis" NIE dokłada:
    backend (weryfikujPodpis) porównuje String(d.podpis || '') z HMAC-em,
    więc brak pola to ta sama „odmowa" co zły podpis — po włączeniu
    PODPIS_OBOWIAZKOWY dotyczy to KAŻDEJ akcji backendu (logowanie, puls,
    sesja, zmien_haslo, reset_hasla). W okresie przejściowym zapytanie
    przechodzi, ale backend zapisuje w Log wpis „podpis_zly"."""
    try:
        import hmac
        import hashlib
        czas = str(int(time.time()))
        baza = "%s|%s|%s" % (dane.get("kod", ""), dane.get("akcja", ""), czas)
        dane["klucz_czas"] = czas
        dane["wersja"] = WERSJA_PROGRAMU
        sekret = _sekret_aplikacji()
        if sekret:
            dane["podpis"] = hmac.new(sekret.encode("utf-8"),
                                      baza.encode("utf-8"),
                                      hashlib.sha256).hexdigest()
        else:
            dane.pop("podpis", None)
    except Exception:
        pass
    return dane

def online_synchronizuj_w_tle():
    """Odpala synchronizację w osobnym wątku — start programu nic nie czeka."""
    threading.Thread(target=online_synchronizuj, daemon=True).start()

PLIK_LOGOWAN = os.path.join(os.path.expanduser("~"), ".pmt_logowania.json")

def _zapamietaj_waznosc_konta(kod: str, wazne_do: str, imie: str = "", z_serwera: bool = False):
    """Ważność dostępu (kolumna „Ważne do") zapamiętana PER KONTO w historii
    urządzenia. Dzięki temu po logowaniu bez sieci program zna termin konta,
    zamiast wracać do 30-dniowej zasady demo i zamykać się „bez powodu"."""
    try:
        kod = str(kod or "").strip()
        if not kod:
            return
        dane = _wczytaj(PLIK_LOGOWAN, {})
        wpis = dane.get(kod)
        if not isinstance(wpis, dict):
            wpis = {}
        if wazne_do:
            wpis["wazne_do"] = str(wazne_do)
        elif z_serwera:
            wpis.pop("wazne_do", None)     # serwer: pusta rubryka = wygasłe
        if imie and not wpis.get("imie"):
            wpis["imie"] = str(imie)
        dane[kod] = wpis
        _zapisz(PLIK_LOGOWAN, dane)
    except Exception:
        pass

WERSJA_PROGRAMU = "3.24.0"   # JEDYNE źródło numeru: zbuduj.py, wersja_pomocnik.py i CI czytają go stąd;

def modul_pomocniczy(nazwa: str):
    """Leniwy, osłonięty import modułu towarzyszącego (pmt_dokumenty,
    pmt_podpis, pmt_wysylka). Brak modułu nie może wywrócić programu —
    wtedy zwracamy None, a wołający zostaje przy starym zachowaniu."""
    try:
        return __import__(nazwa)
    except Exception:
        return None

WIZYTY_STORE = os.path.join(os.path.expanduser("~"), ".pmt_wizyty.json")

_dziennik = None      # {klucz: {"czas": "...", "notatka": "..."}}

def _wczytaj_dziennik():
    """Wczytuje dziennik z dysku (raz)."""
    global _dziennik
    if _dziennik is not None:
        return _dziennik
    _dziennik = {}
    try:
        _sc = _plik_wizyt()
        if os.path.exists(_sc):
            with open(_sc, "r", encoding="utf-8") as f:
                dane = json.load(f)
            if isinstance(dane, dict):
                _dziennik = dane
            elif isinstance(dane, list):
                # zgodność wstecz: stary format (lista kluczy, bez czasu)
                _dziennik = {k: {"czas": "", "notatka": ""} for k in dane}
    except Exception:
        _dziennik = {}
    return _dziennik

def klucz_wizyty(data, adres) -> str:
    """Jednoznaczny klucz wizyty: dzień + adres punktu."""
    try:
        d = data.isoformat()
    except Exception:
        d = str(data)
    return f"{d}|{str(adres).strip().lower()}"

def czy_odwiedzona(data, adres) -> bool:
    return klucz_wizyty(data, adres) in _wczytaj_dziennik()

AKTYWNY_UZYTKOWNIK = ""

def _plik_konta(wzor: str, wspolny: str) -> str:
    """Ścieżka magazynu dla zalogowanego konta; przed zalogowaniem — wspólna."""
    if not AKTYWNY_UZYTKOWNIK:
        return wspolny
    return os.path.join(os.path.expanduser("~"), wzor % AKTYWNY_UZYTKOWNIK)

def _plik_wizyt() -> str:
    return _plik_konta(".pmt_wizyty_%s.json", WIZYTY_STORE)

def _plik_notatek() -> str:
    return _plik_konta(".pmt_notatki_dni_%s.json", NOTATKI_DNI_STORE)

USTAWIENIA_STORE = os.path.join(os.path.expanduser("~"), ".pmt_ustawienia.json")

_ustawienia = None

def _wczytaj_ustawienia():
    global _ustawienia
    if _ustawienia is not None:
        return _ustawienia
    _ustawienia = {}
    # PANCERZ: ucięty/uszkodzony plik (np. pad w trakcie zapisu) nie może
    # wyzerować ustawień — wtedy ratujemy się kopią .bak i odtwarzamy plik.
    for sciezka, z_baku in ((USTAWIENIA_STORE, False),
                            (USTAWIENIA_STORE + ".bak", True)):
        try:
            if os.path.exists(sciezka):
                with open(sciezka, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, dict):
                    _ustawienia = d
                    if z_baku:
                        try:
                            with open(USTAWIENIA_STORE, "w", encoding="utf-8") as f:
                                json.dump(d, f, ensure_ascii=False, indent=1)
                        except Exception:
                            pass
                    break
        except Exception:
            continue
    return _ustawienia

def ustawienie(klucz, domyslne=""):
    return _wczytaj_ustawienia().get(klucz, domyslne)

NAGLOWKI_KOLUMN = {
    "miasto": ["miasto", "miejscowość", "miejscowosc", "miejsc", "city", "town",
               "m.", "msc", "lokalizacja", "location", "poczta"],
    "ulica": ["ulica", "ul", "ul.", "adres", "address", "street", "str", "droga"],
    "numer": ["numer", "nr", "nr.", "nr bud", "nr budynku", "no", "building",
              "dom", "nr domu", "l.dz."],
    "kod": ["kod", "kod pocztowy", "kod poczt", "zip", "postal", "post code",
            "kod-pocztowy", "pna"],
    "siec": ["sieć", "siec", "sklep", "network", "chain", "brand", "marka",
             "klient", "punkt", "nazwa sklepu", "shop", "store"],
}

def _dopasuj_kolumny(naglowki: list) -> dict:
    """Zwraca mapę {rola: indeks_kolumny} na podstawie nagłówków pliku.
    Dopasowanie odporne na wielkość liter, spacje i drobne różnice nazw."""
    mapa = {}
    norm = [(_i, str(h or "").strip().lower()) for _i, h in enumerate(naglowki)]
    for rola, warianty in NAGLOWKI_KOLUMN.items():
        for idx, h in norm:
            if not h:
                continue
            # dokładne dopasowanie albo nagłówek zaczyna się od wariantu
            if h in warianty or any(h == w or h.startswith(w + " ") or h.startswith(w + ".") for w in warianty):
                mapa[rola] = idx
                break
        else:
            # druga runda: wariant zawiera się w nagłówku (np. "adres klienta").
            # Tylko dłuższe warianty (≥4 znaki), by uniknąć fałszywych trafień
            # typu "dom" w "Radom" albo "ul" w "Tytuł".
            for idx, h in norm:
                if h and any(len(w) >= 4 and w in h for w in warianty):
                    mapa[rola] = idx
                    break
    return mapa

def _wiersz_na_adres(wiersz, mapa: dict) -> tuple:
    """Z wiersza danych + mapy kolumn buduje (etykieta_do_planera, opis_sieci).
    Etykieta to możliwie pełny adres: 'ul. Nazwa Nr, KOD Miasto' lub sama
    miejscowość, jeśli tylko ona jest dostępna."""
    def pole(rola):
        i = mapa.get(rola)
        if i is None or i >= len(wiersz):
            return ""
        return str(wiersz[i] if wiersz[i] is not None else "").strip()

    miasto = pole("miasto"); ulica = pole("ulica")
    numer = pole("numer"); kod = pole("kod"); siec = pole("siec")

    # zbuduj adres z dostępnych części
    czesc_ulica = ""
    if ulica:
        # nie dubluj "ul." jeśli już jest
        u = ulica if ulica.lower().startswith(("ul", "al", "pl", "os")) else f"ul. {ulica}"
        czesc_ulica = f"{u} {numer}".strip() if numer else u
    lewa = czesc_ulica
    prawa = f"{kod} {miasto}".strip() if kod else miasto
    if lewa and prawa:
        adres = f"{lewa}, {prawa}"
    else:
        adres = lewa or prawa
    return adres.strip(), siec

_geo_cache = {}

_notatki_dni = None

def _wczytaj_notatki_dni():
    """Wczytuje notatki dnia z dysku (raz, potem cache w pamięci)."""
    global _notatki_dni
    if _notatki_dni is not None:
        return _notatki_dni
    _notatki_dni = {}
    try:
        _sc = _plik_notatek()
        if os.path.exists(_sc):
            with open(_sc, "r", encoding="utf-8") as f:
                dane = json.load(f)
            if isinstance(dane, dict):
                _notatki_dni = dane
    except Exception:
        pass
    return _notatki_dni

def notatka_dnia(iso_data: str) -> dict:
    """Zwraca {'notatka': str, 'wolne': bool} dla danego dnia (klucz: ISO)."""
    return _wczytaj_notatki_dni().get(iso_data, {"notatka": "", "wolne": False})

def czy_dzien_wolny(data: datetime.date) -> bool:
    """Używane przez planer wizyt — dzień wolny jest realnie omijany przy
    układaniu tras, nie tylko oznaczony wizualnie w kalendarzu."""
    return bool(notatka_dnia(data.isoformat()).get("wolne"))

def _klucz_geo(adres) -> str:
    """Jeden adres = jeden klucz. Różnice w wielkości liter i w odstępach
    (także twarda spacja z Worda) nie mogą rodzić drugiego wpisu i drugiego
    zapytania do serwera."""
    return " ".join(str(adres or "").replace("\u00a0", " ").lower().split())

def _oczysc_geo_cache(surowe) -> dict:
    """Zostawia wyłącznie wpisy „adres → [lat, lng]" z sensownymi liczbami."""
    czysty = {}
    if not isinstance(surowe, dict):
        return czysty
    for klucz, wartosc in surowe.items():
        # napis też da się indeksować ("51.4,21.1"[0] == "5"), więc wpis musi
        # być PARĄ LICZB, a nie czymkolwiek o dwóch elementach
        if not isinstance(wartosc, (list, tuple)) or len(wartosc) < 2:
            continue
        try:
            lat, lng = float(wartosc[0]), float(wartosc[1])
        except (TypeError, ValueError):
            continue
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            continue
        czysty[_klucz_geo(klucz)] = [lat, lng]
    return czysty

def _wczytaj_geo_cache(sciezka=None):
    """Uszkodzony plik (pad w trakcie zapisu, obcy plik) nie może wywrócić
    programu — sięgamy wtedy po kopię .bak, a gdy i ona jest zła, zaczynamy
    od pustej pamięci."""
    global _geo_cache
    sciezka = sciezka or GEO_CACHE
    _geo_cache = {}
    for plik, z_baku in ((sciezka, False), (sciezka + ".bak", True)):
        try:
            if not os.path.exists(plik):
                continue
            with open(plik, "r", encoding="utf-8") as f:
                dane = json.load(f)
        except Exception:
            continue
        czysty = _oczysc_geo_cache(dane)
        if czysty:
            _geo_cache = czysty
            if z_baku:
                try:
                    zapisz_geo_cache(sciezka)   # odtwórz główny plik z kopii
                except Exception:
                    pass                        # przy starcie modułu jeszcze go nie ma
            break
        if isinstance(dane, dict):
            break
    return _geo_cache

_geo_braki = None          # adresy nieznane serwerowi (trwale)

_geo_pytane = set()        # adresy odpytane w TEJ sesji bez wyniku

def _wczytaj_geo_braki(sciezka=None):
    global _geo_braki
    if _geo_braki is not None:
        return _geo_braki
    _geo_braki = {}
    try:
        sciezka = sciezka or GEO_BRAKI
        if os.path.exists(sciezka):
            with open(sciezka, "r", encoding="utf-8") as f:
                dane = json.load(f)
            if isinstance(dane, dict):
                _geo_braki = {str(k): str(v) for k, v in dane.items()}
    except Exception:
        _geo_braki = {}
    return _geo_braki

def _zapamietaj_geo_brak(klucz):
    braki = _wczytaj_geo_braki()
    braki[klucz] = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        tmp = GEO_BRAKI + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(braki, f, ensure_ascii=False, indent=1)
        os.replace(tmp, GEO_BRAKI)
    except Exception:
        pass

def _geo_brak_znany(klucz) -> bool:
    return klucz in _wczytaj_geo_braki() or klucz in _geo_pytane

_wczytaj_geo_cache()

MIESIACE_PL = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"] 

WSZYSTKIE_WOJEWODZTWA = ["dolnośląskie", "kujawsko-pomorskie", "lubelskie", "lubuskie", "łódzkie", "małopolskie", "mazowieckie", "opolskie", "podkarpackie", "podlaskie", "pomorskie", "śląskie", "świętokrzyskie", "warmińsko-mazurskie", "wielkopolskie", "zachodniopomorskie"] 

SASIEDZI_WOJ = {
    'dolnośląskie': ['dolnośląskie', 'lubuskie', 'wielkopolskie', 'opolskie'],
    'kujawsko-pomorskie': ['kujawsko-pomorskie', 'pomorskie', 'warmińsko-mazurskie', 'mazowieckie', 'łódzkie', 'wielkopolskie'],
    'lubelskie': ['lubelskie', 'podlaskie', 'mazowieckie', 'świętokrzyskie', 'podkarpackie'],
    'lubuskie': ['lubuskie', 'zachodniopomorskie', 'wielkopolskie', 'dolnośląskie'],
    'łódzkie': ['łódzkie', 'wielkopolskie', 'kujawsko-pomorskie', 'mazowieckie', 'świętokrzyskie', 'śląskie', 'opolskie'],
    'małopolskie': ['małopolskie', 'śląskie', 'świętokrzyskie', 'podkarpackie'],
    'mazowieckie': ['mazowieckie', 'warmińsko-mazurskie', 'podlaskie', 'lubelskie', 'świętokrzyskie', 'łódzkie', 'kujawsko-pomorskie'],
    'opolskie': ['opolskie', 'dolnośląskie', 'wielkopolskie', 'łódzkie', 'śląskie'],
    'podkarpackie': ['podkarpackie', 'lubelskie', 'świętokrzyskie', 'małopolskie'],
    'podlaskie': ['podlaskie', 'warmińsko-mazurskie', 'mazowieckie', 'lubelskie'],
    'pomorskie': ['pomorskie', 'zachodniopomorskie', 'wielkopolskie', 'kujawsko-pomorskie', 'warmińsko-mazurskie'],
    'śląskie': ['śląskie', 'opolskie', 'łódzkie', 'świętokrzyskie', 'małopolskie'],
    'świętokrzyskie': ['świętokrzyskie', 'łódzkie', 'mazowieckie', 'lubelskie', 'podkarpackie', 'małopolskie', 'śląskie'],
    'warmińsko-mazurskie': ['warmińsko-mazurskie', 'pomorskie', 'kujawsko-pomorskie', 'mazowieckie', 'podlaskie'],
    'wielkopolskie': ['wielkopolskie', 'zachodniopomorskie', 'pomorskie', 'kujawsko-pomorskie', 'łódzkie', 'opolskie', 'dolnośląskie', 'lubuskie'],
    'zachodniopomorskie': ['zachodniopomorskie', 'pomorskie', 'wielkopolskie', 'lubuskie']
}

AGLOMERACJE_LISTA = [(52.23, 21.01), (52.40, 16.92), (50.06, 19.94), (51.75, 19.45), (51.10, 17.03), (54.35, 18.64), (51.24, 22.56), (53.01, 18.59), (53.12, 18.01), (53.42, 14.55), (50.87, 20.62), (50.04, 21.99), (53.13, 23.16), (53.77, 20.48), (50.26, 19.02), (50.67, 17.92), (51.93, 15.50), (52.73, 15.24), (50.80, 19.11), (51.40, 21.14), (50.01, 20.98), (54.19, 16.18)]

STOLICE = {'mazowieckie': (52.23, 21.01), 'wielkopolskie': (52.40, 16.92), 'małopolskie': (50.06, 19.94), 'łódzkie': (51.75, 19.45), 'dolnośląskie': (51.10, 17.03), 'pomorskie': (54.35, 18.64), 'lubelskie': (51.24, 22.56), 'kujawsko-pomorskie': (53.01, 18.59), 'zachodniopomorskie': (53.42, 14.55), 'świętokrzyskie': (50.87, 20.62), 'podkarpackie': (50.04, 21.99), 'podlaskie': (53.13, 23.16), 'warmińsko-mazurskie': (53.77, 20.48), 'śląskie': (50.26, 19.02), 'opolskie': (50.67, 17.92), 'lubuskie': (51.93, 15.50)}

SEKTORY_KOLEJNOSC = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"] 

MIASTA_RAW = { 
  "mazowieckie": [{"n":"Goszczyn","lat":51.74,"lng":20.85,"typ":"gmina","sieci":3},{"n":"Błędów","lat":51.78,"lng":20.70,"typ":"gmina","sieci":4},{"n":"Mogielnica","lat":51.69,"lng":20.72,"typ":"gmina","sieci":3},{"n":"Promna","lat":51.68,"lng":20.95,"typ":"gmina","sieci":2},{"n":"Wyśmierzyce","lat":51.61,"lng":20.81,"typ":"gmina","sieci":2},{"n":"Stromiec","lat":51.64,"lng":21.08,"typ":"gmina","sieci":2},{"n":"Jedlińsk","lat":51.52,"lng":21.11,"typ":"gmina","sieci":3},{"n":"Zakrzew","lat":51.46,"lng":21.02,"typ":"gmina","sieci":2},{"n":"Przytyk","lat":51.46850,"lng":20.90424,"typ":"gmina","sieci":3},{"n":"Potworów","lat":51.52,"lng":20.72,"typ":"gmina","sieci":2},{"n":"Rusinów","lat":51.45,"lng":20.52,"typ":"gmina","sieci":2},{"n":"Odrzywół","lat":51.51914,"lng":20.55594,"typ":"gmina","sieci":2},{"n":"Maciejowice","lat":51.71,"lng":21.56,"typ":"gmina","sieci":3},{"n":"Sobolew","lat":51.74,"lng":21.67,"typ":"gmina","sieci":2},{"n":"Wilga","lat":51.85,"lng":21.38,"typ":"gmina","sieci":2},{"n":"Trojanów","lat":51.68,"lng":21.81,"typ":"gmina","sieci":2},{"n":"Wodynie","lat":52.04051,"lng":21.95615,"typ":"gmina","sieci":2},{"n":"Repki","lat":52.39,"lng":22.42,"typ":"gmina","sieci":3},{"n":"Sabnie","lat":52.51,"lng":22.30,"typ":"gmina","sieci":2},{"n":"Sterdyń","lat":52.58,"lng":22.29,"typ":"gmina","sieci":2},{"n":"Korczew","lat":52.35,"lng":22.61,"typ":"gmina","sieci":2},{"n":"Przesmyki","lat":52.26,"lng":22.58,"typ":"gmina","sieci":2},{"n":"Paprotnia","lat":52.26,"lng":22.46,"typ":"gmina","sieci":2},{"n":"Wiśniew","lat":52.09,"lng":22.28,"typ":"gmina","sieci":3},{"n":"Kotuń","lat":52.17,"lng":22.05,"typ":"gmina","sieci":2},{"n":"Mokobody","lat":52.26,"lng":22.11,"typ":"gmina","sieci":2},{"n":"Skórzec","lat":52.11,"lng":22.12,"typ":"gmina","sieci":2},{"n":"Korytnica","lat":52.41,"lng":21.82,"typ":"gmina","sieci":3},{"n":"Jadów","lat":52.47,"lng":21.62,"typ":"gmina","sieci":3},{"n":"Strachówka","lat":52.42768,"lng":21.63544,"typ":"gmina","sieci":2},{"n":"Poświętne","lat":52.33,"lng":21.43,"typ":"gmina","sieci":2},{"n":"Osieck","lat":51.97,"lng":21.44,"typ":"gmina","sieci":2},{"n":"Celestynów","lat":52.06,"lng":21.39,"typ":"gmina","sieci":3},{"n":"Kołbiel","lat":52.06,"lng":21.48,"typ":"gmina","sieci":3},{"n":"Sobienie-Jeziory","lat":51.93,"lng":21.31,"typ":"gmina","sieci":2},{"n":"Latowicz","lat":52.03,"lng":21.80,"typ":"gmina","sieci":2},{"n":"Parysów","lat":51.98,"lng":21.68,"typ":"gmina","sieci":2},{"n":"Borowie","lat":51.94,"lng":21.75,"typ":"gmina","sieci":2},{"n":"Górzno","lat":51.84701,"lng":21.70906,"typ":"gmina","sieci":2},{"n":"Miastków","lat":51.86,"lng":21.81,"typ":"gmina","sieci":2},{"n":"Siennica","lat":52.09,"lng":21.61,"typ":"gmina","sieci":3},{"n":"Cegłów","lat":52.14,"lng":21.71,"typ":"gmina","sieci":3},{"n":"Dębe Wielkie","lat":52.20,"lng":21.46,"typ":"gmina","sieci":3},{"n":"Halinów","lat":52.23,"lng":21.35,"typ":"gmina","sieci":3},{"n":"Zwoleń","lat":51.35,"lng":21.58,"typ":"powiat","sieci":4},{"n":"Kazanów","lat":51.27,"lng":21.46,"typ":"gmina","sieci":2},{"n":"Głowaczów","lat":51.61,"lng":21.30,"typ":"gmina","sieci":2},{"n":"Magnuszew","lat":51.75,"lng":21.38,"typ":"gmina","sieci":3},{"n":"Mniszew","lat":51.84637,"lng":21.28112,"typ":"gmina","sieci":2},{"n":"Tarczyn","lat":51.98,"lng":20.83,"typ":"gmina","sieci":3},{"n":"Chynów","lat":51.90,"lng":21.08,"typ":"gmina","sieci":2},{"n":"Pniewy","lat":51.90,"lng":20.73,"typ":"gmina","sieci":1},{"n":"Mszczonów","lat":51.97,"lng":20.52,"typ":"gmina","sieci":4},{"n":"Radziejowice","lat":52.00420,"lng":20.55576,"typ":"gmina","sieci":2},{"n":"Żabia Wola","lat":52.05,"lng":20.66,"typ":"gmina","sieci":2},{"n":"Nadarzyn","lat":52.09,"lng":20.80,"typ":"gmina","sieci":3},{"n":"Lesznowola","lat":52.08,"lng":20.93,"typ":"gmina","sieci":3},{"n":"Błonie","lat":52.19,"lng":20.61,"typ":"gmina","sieci":4},{"n":"Teresin","lat":52.19,"lng":20.41,"typ":"gmina","sieci":3},{"n":"Kampinos","lat":52.26,"lng":20.46,"typ":"gmina","sieci":2},{"n":"Leszno","lat":52.26,"lng":20.59,"typ":"gmina","sieci":2},{"n":"Izabelin","lat":52.29746,"lng":20.81063,"typ":"gmina","sieci":2},{"n":"Czosnów","lat":52.39,"lng":20.72,"typ":"gmina","sieci":3},{"n":"Leoncin","lat":52.40,"lng":20.52,"typ":"gmina","sieci":2},{"n":"Pomiechówek","lat":52.48,"lng":20.73,"typ":"gmina","sieci":3},{"n":"Zakroczym","lat":52.43,"lng":20.61,"typ":"gmina","sieci":2},{"n":"Nasielsk","lat":52.59,"lng":20.79,"typ":"gmina","sieci":4},{"n":"Winnica","lat":52.64,"lng":20.95,"typ":"gmina","sieci":2},{"n":"Serock","lat":52.51,"lng":21.06,"typ":"gmina","sieci":4},{"n":"Nieporęt","lat":52.42,"lng":21.03,"typ":"gmina","sieci":3},{"n":"Wieliszew","lat":52.45,"lng":20.95,"typ":"gmina","sieci":3},{"n":"Radzymin","lat":52.41,"lng":21.18,"typ":"gmina","sieci":4},{"n":"Klembów","lat":52.40,"lng":21.33,"typ":"gmina","sieci":2},{"n":"Stanisławów","lat":52.28,"lng":21.56,"typ":"gmina","sieci":2},{"n":"Grójec","lat":51.86,"lng":20.87,"typ":"powiat","sieci":5},{"n":"Warka","lat":51.78,"lng":21.20,"typ":"powiat","sieci":5},{"n":"Mińsk Maz.","lat":52.18,"lng":21.56,"typ":"powiat","sieci":5},{"n":"Góra Kalwaria","lat":51.98,"lng":21.22,"typ":"powiat","sieci":5},{"n":"Glinojeck","lat":52.82,"lng":20.29,"typ":"gmina","sieci":3},{"n":"Strzegowo","lat":52.90,"lng":20.28,"typ":"gmina","sieci":2},{"n":"Raciąż","lat":52.78,"lng":20.12,"typ":"gmina","sieci":3},{"n":"Baboszewo","lat":52.68139,"lng":20.25833,"typ":"gmina","sieci":2},{"n":"Ojrzeń","lat":52.78,"lng":20.53,"typ":"gmina","sieci":1},{"n":"Sochocin","lat":52.68733,"lng":20.47224,"typ":"gmina","sieci":2},{"n":"Nowe Miasto","lat":52.65648,"lng":20.62991,"typ":"gmina","sieci":2},{"n":"Joniec","lat":52.60178,"lng":20.58029,"typ":"gmina","sieci":1},{"n":"Załuski","lat":52.54,"lng":20.53,"typ":"gmina","sieci":1},{"n":"Drobin","lat":52.74,"lng":19.98,"typ":"gmina","sieci":2},{"n":"Gąbin","lat":52.39,"lng":19.73,"typ":"gmina","sieci":2},{"n":"Czerwińsk nad Wisłą","lat":52.39384,"lng":20.31277,"typ":"gmina","sieci":2},{"n":"Wyszogród","lat":52.39,"lng":20.20,"typ":"gmina","sieci":2},{"n":"Sierpc","lat":52.85,"lng":19.66,"typ":"gmina","sieci":4},{"n":"Gozdowo","lat":52.72256,"lng":19.68961,"typ":"gmina","sieci":1},{"n":"Rościszewo","lat":52.90,"lng":19.77,"typ":"gmina","sieci":1},{"n":"Mochowo","lat":52.76529,"lng":19.55823,"typ":"gmina","sieci":1},{"n":"Szczutowo","lat":52.93850,"lng":19.57556,"typ":"gmina","sieci":1},{"n":"Żuromin","lat":53.06,"lng":19.90,"typ":"gmina","sieci":3},{"n":"Bieżuń","lat":52.96,"lng":19.89,"typ":"gmina","sieci":2},{"n":"Kuczbork","lat":53.07,"lng":19.99,"typ":"gmina","sieci":1},{"n":"Lipowiec K.","lat":53.11,"lng":20.06,"typ":"gmina","sieci":1},{"n":"Lubowidz","lat":53.12082,"lng":19.84153,"typ":"gmina","sieci":1},{"n":"Brudzeń Duży","lat":52.66821,"lng":19.50476,"typ":"gmina","sieci":1},{"n":"Bielsk","lat":52.67136,"lng":19.80433,"typ":"gmina","sieci":2},{"n":"Zawidz","lat":52.80,"lng":19.90,"typ":"gmina","sieci":2},{"n":"Sanniki","lat":52.33,"lng":19.86,"typ":"gmina","sieci":2},{"n":"Gostynin","lat":52.42,"lng":19.46,"typ":"gmina","sieci":4},{"n":"Szczawin Kościelny","lat":52.37094,"lng":19.61346,"typ":"gmina","sieci":1},{"n":"Młodzieszyn","lat":52.29865,"lng":20.18605,"typ":"gmina","sieci":1},{"n":"Stara Biała","lat":52.61067,"lng":19.64797,"typ":"gmina","sieci":1},{"n":"Radzanowo","lat":52.57485,"lng":19.89648,"typ":"gmina","sieci":1},{"n":"Bulkowo","lat":52.54104,"lng":20.12807,"typ":"gmina","sieci":1},{"n":"Dąbrówka","lat":52.48389,"lng":21.29757,"typ":"gmina","sieci":1},{"n":"Małkinia G.","lat":52.69,"lng":21.89,"typ":"gmina","sieci":3},{"n":"Lochów","lat":52.63,"lng":21.71,"typ":"gmina","sieci":3},{"n":"Brok","lat":52.69,"lng":21.84,"typ":"gmina","sieci":2},{"n":"Jabłonna","lat":52.37,"lng":20.92,"typ":"gmina","sieci":3},{"n":"Tłuszcz","lat":52.43,"lng":21.44,"typ":"gmina","sieci":3},{"n":"Wołomin","lat":52.34,"lng":21.24,"typ":"gmina","sieci":4},{"n":"Kobyłka","lat":52.34,"lng":21.2,"typ":"gmina","sieci":3},{"n":"Zielonka","lat":52.3,"lng":21.15,"typ":"gmina","sieci":3},{"n":"Ząbki","lat":52.28933,"lng":21.11801,"typ":"gmina","sieci":4},{"n":"Sulejówek","lat":52.25,"lng":21.27,"typ":"gmina","sieci":3},{"n":"Wiązowna","lat":52.17172,"lng":21.30661,"typ":"gmina","sieci":2},{"n":"Karczew","lat":52.08,"lng":21.25,"typ":"gmina","sieci":3},{"n":"Otwock","lat":52.11,"lng":21.26,"typ":"gmina","sieci":4},{"n":"Piaseczno","lat":52.08,"lng":21.02,"typ":"gmina","sieci":5},{"n":"Prażmów","lat":51.94027,"lng":20.95479,"typ":"gmina","sieci":2},{"n":"Grabów nad Pilicą","lat":51.72556,"lng":21.22583,"typ":"gmina","sieci":1},{"n":"Iłża","lat":51.16,"lng":21.24,"typ":"gmina","sieci":3},{"n":"Skaryszew","lat":51.31,"lng":21.25,"typ":"gmina","sieci":2},{"n":"Pionki","lat":51.48,"lng":21.45,"typ":"gmina","sieci":4},{"n":"Jastrzębia","lat":51.42,"lng":21.3,"typ":"gmina","sieci":1},{"n":"Wierzbica","lat":51.2,"lng":21.08,"typ":"gmina","sieci":2},{"n":"Wolanów","lat":51.37926,"lng":20.97644,"typ":"gmina","sieci":1},{"n":"Gózd","lat":51.4,"lng":21.33,"typ":"gmina","sieci":1},{"n":"Kowala","lat":51.32495,"lng":21.07071,"typ":"gmina","sieci":1},{"n":"Marki","lat":52.32,"lng":21.1,"typ":"gmina","sieci":3},{"n":"Ostrów Maz.","lat":52.8,"lng":21.89,"typ":"gmina","sieci":3},{"n":"Wyszków","lat":52.59,"lng":21.46,"typ":"gmina","sieci":3},{"n":"Maków Maz.","lat":52.86,"lng":21.1,"typ":"gmina","sieci":2},{"n":"Różan","lat":52.88,"lng":21.39,"typ":"gmina","sieci":1},{"n":"Pułtusk","lat":52.7,"lng":21.08,"typ":"gmina","sieci":3},{"n":"Płońsk","lat":52.62,"lng":20.38,"typ":"gmina","sieci":3},{"n":"Mława","lat":53.11,"lng":20.38,"typ":"gmina","sieci":3},{"n":"Przasnysz","lat":53.02,"lng":20.88,"typ":"gmina","sieci":3},{"n":"Chorzele","lat":53.27,"lng":20.9,"typ":"gmina","sieci":1},{"n":"Krasnosielc","lat":53.02,"lng":21.15,"typ":"gmina","sieci":1},{"n":"Białobrzegi","lat":51.64,"lng":20.95,"typ":"gmina","sieci":2},{"n":"Kozienice","lat":51.58,"lng":21.55,"typ":"gmina","sieci":3},{"n":"Lipsko","lat":51.16,"lng":21.65,"typ":"gmina","sieci":1},{"n":"Przysucha","lat":51.36,"lng":20.63,"typ":"gmina","sieci":2},{"n":"Szydłowiec","lat":51.23,"lng":20.85,"typ":"gmina","sieci":2},{"n":"Andrzejewo","lat":52.83059,"lng":22.20047,"typ":"gmina","sieci":2}],
  "wielkopolskie": [{"n":"Luboń","lat":52.33,"lng":16.88,"typ":"gmina","sieci":4},{"n":"Komorniki","lat":52.33,"lng":16.80,"typ":"gmina","sieci":3},{"n":"Tarnowo Podg.","lat":52.46,"lng":16.66,"typ":"gmina","sieci":4},{"n":"Dopiewo","lat":52.35,"lng":16.67,"typ":"gmina","sieci":3},{"n":"Rokietnica","lat":52.50,"lng":16.75,"typ":"gmina","sieci":2},{"n":"Suchy Las","lat":52.48,"lng":16.86,"typ":"gmina","sieci":3},{"n":"Czerwonak","lat":52.46,"lng":16.98,"typ":"gmina","sieci":2},{"n":"Swarzędz","lat":52.41,"lng":17.07,"typ":"gmina","sieci":5},{"n":"Kostrzyn","lat":52.39,"lng":17.22,"typ":"gmina","sieci":3},{"n":"Kórnik","lat":52.24,"lng":17.09,"typ":"gmina","sieci":3},{"n":"Mosina","lat":52.24,"lng":16.84,"typ":"gmina","sieci":3},{"n":"Puszczykowo","lat":52.27,"lng":16.93,"typ":"gmina","sieci":2},{"n":"Stęszew","lat":52.28,"lng":16.70,"typ":"gmina","sieci":2},{"n":"Pobiedziska","lat":52.47,"lng":17.28,"typ":"gmina","sieci":2},{"n":"Mur. Goślina","lat":52.57,"lng":17.00,"typ":"gmina","sieci":2},{"n":"Opalenica","lat":52.30,"lng":16.41,"typ":"gmina","sieci":3},{"n":"Buk","lat":52.35,"lng":16.52,"typ":"gmina","sieci":2},{"n":"Kleszczewo","lat":52.33,"lng":17.17,"typ":"gmina","sieci":2},{"n":"Nekla","lat":52.36,"lng":17.41,"typ":"gmina","sieci":2},{"n":"Środa Wlkp.","lat":52.23,"lng":17.28,"typ":"gmina","sieci":4},{"n":"Zaniemyśl","lat":52.15,"lng":17.16,"typ":"gmina","sieci":2},{"n":"Pniewy","lat":52.51,"lng":16.26,"typ":"gmina","sieci":3},{"n":"Szamotuły","lat":52.61,"lng":16.58,"typ":"gmina","sieci":4},{"n":"Oborniki","lat":52.65,"lng":16.81,"typ":"gmina","sieci":4},{"n":"Rogoźno","lat":52.75,"lng":16.99,"typ":"gmina","sieci":3},{"n":"Skoki","lat":52.67,"lng":17.16,"typ":"gmina","sieci":2},{"n":"Kłecko","lat":52.63,"lng":17.43,"typ":"gmina","sieci":2},{"n":"Czerniejewo","lat":52.42657,"lng":17.49005,"typ":"gmina","sieci":2},{"n":"Trzemeszno","lat":52.56,"lng":17.82,"typ":"gmina","sieci":3},{"n":"Witkowo","lat":52.44046,"lng":17.77233,"typ":"gmina","sieci":3},{"n":"Miłosław","lat":52.20299,"lng":17.48949,"typ":"gmina","sieci":2},{"n":"Nowe Miasto nad Wartą","lat":52.09,"lng":17.41,"typ":"gmina","sieci":2},{"n":"Jarocin","lat":51.97238,"lng":17.50163,"typ":"gmina","sieci":4},{"n":"Pleszew","lat":51.90,"lng":17.78,"typ":"gmina","sieci":4},{"n":"Koźmin Wlkp.","lat":51.83,"lng":17.46,"typ":"gmina","sieci":3},{"n":"Krotoszyn","lat":51.69,"lng":17.44,"typ":"gmina","sieci":4},{"n":"Bojanowo","lat":51.70742,"lng":16.74890,"typ":"gmina","sieci":2},{"n":"Śmigiel","lat":52.01,"lng":16.52,"typ":"gmina","sieci":2},{"n":"Kościan","lat":52.08,"lng":16.65,"typ":"gmina","sieci":4},{"n":"Wolsztyn","lat":52.11,"lng":16.11,"typ":"gmina","sieci":4},{"n":"Rakoniewice","lat":52.14,"lng":16.27,"typ":"gmina","sieci":2},{"n":"Granowo","lat":52.22241,"lng":16.52881,"typ":"gmina","sieci":2},{"n":"Grodzisk Wlkp.","lat":52.22,"lng":16.36,"typ":"gmina","sieci":3},{"n":"Wronki","lat":52.71,"lng":16.38,"typ":"gmina","sieci":3},{"n":"Krzyż Wlkp.","lat":52.88,"lng":16.01,"typ":"gmina","sieci":2},{"n":"Trzcianka","lat":53.04,"lng":16.45,"typ":"gmina","sieci":3},{"n":"Ujście","lat":53.05,"lng":16.73,"typ":"gmina","sieci":2},{"n":"Wyrzysk","lat":53.15343,"lng":17.26712,"typ":"gmina","sieci":2},{"n":"Kaczory","lat":53.10204,"lng":16.88408,"typ":"gmina","sieci":1},{"n":"Wysoka","lat":53.14,"lng":17.08,"typ":"gmina","sieci":2},{"n":"Łobżenica","lat":53.27,"lng":17.26,"typ":"gmina","sieci":2},{"n":"Wągrowiec","lat":52.80,"lng":17.20,"typ":"gmina","sieci":4},{"n":"Margonin","lat":52.97,"lng":17.09,"typ":"gmina","sieci":2},{"n":"Mieścisko","lat":52.74375,"lng":17.32843,"typ":"gmina","sieci":1},{"n":"Zagorów","lat":52.01,"lng":15.72,"typ":"gmina","sieci":2},{"n":"Pyzdry","lat":52.16,"lng":17.67,"typ":"gmina","sieci":2},{"n":"Rychwał","lat":52.06976,"lng":18.16627,"typ":"gmina","sieci":2},{"n":"Czempiń","lat":52.16,"lng":16.76,"typ":"gmina","sieci":1},{"n":"Krzywiń","lat":51.96,"lng":16.83,"typ":"gmina","sieci":1},{"n":"Gostyń","lat":51.88,"lng":17.01,"typ":"gmina","sieci":3},{"n":"Poniec","lat":51.76340,"lng":16.80867,"typ":"gmina","sieci":1},{"n":"Krobia","lat":51.77418,"lng":16.98463,"typ":"gmina","sieci":1},{"n":"Borek Wlkp.","lat":51.91,"lng":17.22,"typ":"gmina","sieci":1},{"n":"Pogorzela","lat":51.82245,"lng":17.23035,"typ":"gmina","sieci":1},{"n":"Rozdrażew","lat":51.77876,"lng":17.50500,"typ":"gmina","sieci":1},{"n":"Wapno","lat":52.91090,"lng":17.47176,"typ":"gmina","sieci":1},{"n":"Dąbie","lat":52.08836,"lng":18.82230,"typ":"gmina","sieci":2},{"n":"Gołańcz","lat":52.94319,"lng":17.29968,"typ":"gmina","sieci":2},{"n":"Damasławek","lat":52.84011,"lng":17.49936,"typ":"gmina","sieci":2}],
  "łódzkie": [{"n":"Rzgów","lat":51.66,"lng":19.49,"typ":"gmina","sieci":3},{"n":"Tuszyn","lat":51.60,"lng":19.53,"typ":"gmina","sieci":2},{"n":"Stryków","lat":51.90,"lng":19.61,"typ":"gmina","sieci":3},{"n":"Głowno","lat":51.96,"lng":19.71,"typ":"gmina","sieci":3},{"n":"Ozorków","lat":51.96,"lng":19.29,"typ":"gmina","sieci":4},{"n":"Poddębice","lat":51.89,"lng":18.96,"typ":"gmina","sieci":3},{"n":"Dobroń","lat":51.63844,"lng":19.24530,"typ":"gmina","sieci":2},{"n":"Szadek","lat":51.69,"lng":18.98,"typ":"gmina","sieci":2},{"n":"Wodzierady","lat":51.72,"lng":19.13,"typ":"gmina","sieci":1},{"n":"Zelów","lat":51.46,"lng":19.22,"typ":"gmina","sieci":3},{"n":"Lutomiersk","lat":51.75,"lng":19.21,"typ":"gmina","sieci":2},{"n":"Dalików","lat":51.88,"lng":19.11,"typ":"gmina","sieci":1},{"n":"Parzęczew","lat":51.95,"lng":19.20,"typ":"gmina","sieci":2},{"n":"Dmosin","lat":51.91,"lng":19.75,"typ":"gmina","sieci":2},{"n":"Piątek","lat":52.06,"lng":19.48,"typ":"gmina","sieci":2},{"n":"Zduńska Wola","lat":51.60,"lng":18.94,"typ":"gmina","sieci":4},{"n":"Łask","lat":51.59,"lng":19.13,"typ":"gmina","sieci":4},{"n":"Aleksandrów Ł.","lat":51.81,"lng":19.30,"typ":"gmina","sieci":4},{"n":"Ksawerów","lat":51.67,"lng":19.46,"typ":"gmina","sieci":2},{"n":"Koluszki","lat":51.74,"lng":19.81,"typ":"gmina","sieci":3},{"n":"Brzeziny","lat":51.80,"lng":19.74,"typ":"gmina","sieci":3},{"n":"Widawa","lat":51.43829,"lng":18.94213,"typ":"gmina","sieci":2},{"n":"Złoczew","lat":51.41,"lng":18.60,"typ":"gmina","sieci":2},{"n":"Warta","lat":51.70694,"lng":18.62444,"typ":"gmina","sieci":2},{"n":"Błaszki","lat":51.65167,"lng":18.43774,"typ":"gmina","sieci":2},{"n":"Wieruszów","lat":51.29,"lng":18.15,"typ":"gmina","sieci":3},{"n":"Działoszyn","lat":51.11,"lng":18.86,"typ":"gmina","sieci":2},{"n":"Pajęczno","lat":51.14,"lng":18.99,"typ":"gmina","sieci":2},{"n":"Dębiak","lat":51.35,"lng":19.15,"typ":"gmina","sieci":1},{"n":"Rusiec","lat":51.32,"lng":18.98,"typ":"gmina","sieci":1},{"n":"Kleszczów","lat":51.22,"lng":19.30,"typ":"gmina","sieci":2},{"n":"Sulmierzyce","lat":51.18,"lng":19.19,"typ":"gmina","sieci":1},{"n":"Rząśnia","lat":51.22182,"lng":19.04251,"typ":"gmina","sieci":1},{"n":"Kiełczygłów","lat":51.23,"lng":18.97,"typ":"gmina","sieci":1},{"n":"Szczerców","lat":51.33225,"lng":19.11553,"typ":"gmina","sieci":1},{"n":"Rozprza","lat":51.30260,"lng":19.64606,"typ":"gmina","sieci":1},{"n":"Zgierz","lat":51.86,"lng":19.41,"typ":"gmina","sieci":3},{"n":"Konstantynów","lat":51.75,"lng":19.33,"typ":"gmina","sieci":2},{"n":"Pabianice","lat":51.66,"lng":19.35,"typ":"gmina","sieci":3},{"n":"Rogów","lat":51.80180,"lng":19.88360,"typ":"gmina","sieci":1},{"n":"Łęczyca","lat":52.06,"lng":19.2,"typ":"gmina","sieci":2},{"n":"Góra św.Małg.","lat":52.03,"lng":19.55,"typ":"gmina","sieci":1},{"n":"Sędziejowice","lat":51.52,"lng":19.0,"typ":"gmina","sieci":1},{"n":"Wieluń","lat":51.22,"lng":18.57,"typ":"gmina","sieci":3},{"n":"Buczek","lat":51.50095,"lng":19.16410,"typ":"gmina","sieci":1}],
  "śląskie": [{"n":"Pszczyna","lat":49.98,"lng":18.94,"typ":"gmina","sieci":4},{"n":"Łaziska Górne","lat":50.15,"lng":18.84,"typ":"gmina","sieci":3},{"n":"Orzesze","lat":50.10868,"lng":18.79256,"typ":"gmina","sieci":2},{"n":"Czerwionka","lat":50.15,"lng":18.67,"typ":"gmina","sieci":3},{"n":"Knułów","lat":50.22,"lng":18.67,"typ":"gmina","sieci":3},{"n":"Pyskowice","lat":50.39,"lng":18.62,"typ":"gmina","sieci":2},{"n":"Toszek","lat":50.45,"lng":18.52,"typ":"gmina","sieci":2},{"n":"Radzionków","lat":50.39,"lng":18.90,"typ":"gmina","sieci":3},{"n":"Siewierz","lat":50.46940,"lng":19.23635,"typ":"gmina","sieci":2},{"n":"Poręba","lat":50.49,"lng":19.33,"typ":"gmina","sieci":2},{"n":"Lędziny","lat":50.13,"lng":19.11,"typ":"gmina","sieci":2},{"n":"Imielin","lat":50.14,"lng":19.17,"typ":"gmina","sieci":2},{"n":"Czechowice-Dziedzice","lat":49.91118,"lng":19.00712,"typ":"gmina","sieci":3},{"n":"Bojszowy","lat":50.05977,"lng":19.09111,"typ":"gmina","sieci":2},{"n":"Chełm Śląski","lat":50.11,"lng":19.18,"typ":"gmina","sieci":2},{"n":"Suszec","lat":50.03792,"lng":18.78838,"typ":"gmina","sieci":2},{"n":"Kobiór","lat":50.05,"lng":18.94,"typ":"gmina","sieci":2},{"n":"Pawłowice","lat":49.96,"lng":18.71,"typ":"gmina","sieci":3},{"n":"Goczałkowice","lat":49.94,"lng":18.97,"typ":"gmina","sieci":2},{"n":"Wyry","lat":50.13,"lng":18.89,"typ":"gmina","sieci":2},{"n":"Ornontowice","lat":50.18,"lng":18.75,"typ":"gmina","sieci":2},{"n":"Wielowieś","lat":50.50,"lng":18.62,"typ":"gmina","sieci":1},{"n":"Rudziniec","lat":50.35,"lng":18.41,"typ":"gmina","sieci":2},{"n":"Tworóg","lat":50.53,"lng":18.71,"typ":"gmina","sieci":2},{"n":"Krupski Młyn","lat":50.57,"lng":18.62,"typ":"gmina","sieci":1},{"n":"Zbrosławice","lat":50.41,"lng":18.76,"typ":"gmina","sieci":2},{"n":"Miasteczko Śl.","lat":50.49,"lng":18.92,"typ":"gmina","sieci":2},{"n":"Ożarowice","lat":50.47,"lng":19.04,"typ":"gmina","sieci":2},{"n":"Świerklaniec","lat":50.43,"lng":18.95,"typ":"gmina","sieci":2},{"n":"Bieruń","lat":50.08,"lng":19.09,"typ":"powiat","sieci":3},{"n":"Kłobuck","lat":50.90,"lng":18.93,"typ":"gmina","sieci":4},{"n":"Krzepice","lat":50.97083,"lng":18.72833,"typ":"gmina","sieci":2},{"n":"Wręczyca Wlk.","lat":50.85,"lng":18.93,"typ":"gmina","sieci":2},{"n":"Przystajń","lat":50.88334,"lng":18.69038,"typ":"gmina","sieci":1},{"n":"Opatów","lat":50.95,"lng":18.81,"typ":"gmina","sieci":1},{"n":"Lipie","lat":51.02,"lng":18.80,"typ":"gmina","sieci":1},{"n":"Popów","lat":51.05,"lng":18.95,"typ":"gmina","sieci":1},{"n":"Miedźno","lat":50.96,"lng":18.96,"typ":"gmina","sieci":2},{"n":"Mykanów","lat":50.92126,"lng":19.19821,"typ":"gmina","sieci":2},{"n":"Rędziny","lat":50.86,"lng":19.22,"typ":"gmina","sieci":2},{"n":"Kłomnice","lat":50.92180,"lng":19.35681,"typ":"gmina","sieci":2},{"n":"Kruszyna","lat":50.96744,"lng":19.27543,"typ":"gmina","sieci":1},{"n":"Lubliniec","lat":50.66,"lng":18.68,"typ":"gmina","sieci":4},{"n":"Koszęcin","lat":50.63,"lng":18.84,"typ":"gmina","sieci":2},{"n":"Boronów","lat":50.67,"lng":18.90,"typ":"gmina","sieci":1},{"n":"Woźniki","lat":50.58581,"lng":19.05920,"typ":"gmina","sieci":2},{"n":"Wilamowice","lat":49.91,"lng":19.15,"typ":"gmina","sieci":2},{"n":"Kozy","lat":49.86,"lng":19.14,"typ":"gmina","sieci":2},{"n":"Wilkowice","lat":49.75,"lng":19.05,"typ":"gmina","sieci":2},{"n":"Buczkowice","lat":49.72,"lng":19.06,"typ":"gmina","sieci":1},{"n":"Szczyrk","lat":49.72,"lng":19.02,"typ":"gmina","sieci":2},{"n":"Jaworze","lat":49.79149,"lng":18.94816,"typ":"gmina","sieci":1},{"n":"Jasienica","lat":49.81,"lng":18.9,"typ":"gmina","sieci":2},{"n":"Jaworzynka","lat":49.53,"lng":18.85,"typ":"gmina","sieci":1},{"n":"Istebna","lat":49.55,"lng":18.9,"typ":"gmina","sieci":2},{"n":"Wisła","lat":49.66,"lng":18.86,"typ":"gmina","sieci":3},{"n":"Ustroń","lat":49.72,"lng":18.81,"typ":"gmina","sieci":3},{"n":"Skoczów","lat":49.8,"lng":18.79,"typ":"gmina","sieci":3},{"n":"Strumień","lat":49.91714,"lng":18.76337,"typ":"gmina","sieci":2},{"n":"Zebrzydowice","lat":49.87,"lng":18.6,"typ":"gmina","sieci":2},{"n":"Hażlach","lat":49.80259,"lng":18.66235,"typ":"gmina","sieci":1},{"n":"Dębowiec","lat":49.85,"lng":18.75,"typ":"gmina","sieci":1},{"n":"Chybie","lat":49.9,"lng":18.81,"typ":"gmina","sieci":1},{"n":"Brenna","lat":49.72,"lng":18.9,"typ":"gmina","sieci":1},{"n":"Miedźna","lat":49.98,"lng":19.03,"typ":"gmina","sieci":1},{"n":"Chełm Śl.","lat":50.1,"lng":19.2,"typ":"gmina","sieci":1},{"n":"Mysłowice","lat":50.21208,"lng":19.14765,"typ":"gmina","sieci":3},{"n":"Jaworzno","lat":50.2,"lng":19.27,"typ":"gmina","sieci":3},{"n":"Sosnowiec","lat":50.28526,"lng":19.17804,"typ":"gmina","sieci":4},{"n":"Będzin","lat":50.33,"lng":19.13,"typ":"gmina","sieci":3},{"n":"Czeladź","lat":50.32,"lng":19.08,"typ":"gmina","sieci":2},{"n":"Wojkowice","lat":50.36,"lng":19.02,"typ":"gmina","sieci":1},{"n":"Łazy","lat":50.43,"lng":19.4,"typ":"gmina","sieci":1},{"n":"Ogrodzieniec","lat":50.45,"lng":19.52,"typ":"gmina","sieci":1},{"n":"Zawiercie","lat":50.49,"lng":19.43,"typ":"gmina","sieci":3},{"n":"Kroczyce","lat":50.56143,"lng":19.57010,"typ":"gmina","sieci":1},{"n":"Włodowice","lat":50.55216,"lng":19.45035,"typ":"gmina","sieci":1},{"n":"Myszków","lat":50.58,"lng":19.32,"typ":"gmina","sieci":3},{"n":"Koziegłowy","lat":50.61,"lng":19.14,"typ":"gmina","sieci":1},{"n":"Kalety","lat":50.56430,"lng":18.88416,"typ":"gmina","sieci":1}],
  "małopolskie": [{"n":"Skawina","lat":49.97,"lng":19.82,"typ":"gmina","sieci":4},{"n":"Niepołomice","lat":50.03,"lng":20.21,"typ":"gmina","sieci":3},{"n":"Krzeszowice","lat":50.13,"lng":19.63,"typ":"gmina","sieci":3},{"n":"Zabierzów","lat":50.11,"lng":19.79,"typ":"gmina","sieci":2},{"n":"Liszki","lat":50.03,"lng":19.78,"typ":"gmina","sieci":2},{"n":"Zielonki","lat":50.11,"lng":19.93,"typ":"gmina","sieci":3},{"n":"Michałowice","lat":50.15884,"lng":19.97919,"typ":"gmina","sieci":2},{"n":"Słomniki","lat":50.24,"lng":20.08,"typ":"gmina","sieci":2},{"n":"Kocmyrzów","lat":50.12846,"lng":20.12987,"typ":"gmina","sieci":2},{"n":"Dobczyce","lat":49.88071,"lng":20.09276,"typ":"gmina","sieci":2},{"n":"Kłaj","lat":49.99337,"lng":20.29914,"typ":"gmina","sieci":2},{"n":"Biskupice","lat":49.96,"lng":20.12,"typ":"gmina","sieci":2},{"n":"Drwinia","lat":50.11,"lng":20.43,"typ":"gmina","sieci":1},{"n":"Rzezawa","lat":49.98,"lng":20.50,"typ":"gmina","sieci":2},{"n":"Koszyce","lat":50.16,"lng":20.57,"typ":"gmina","sieci":2},{"n":"Koniusza","lat":50.18776,"lng":20.21802,"typ":"gmina","sieci":1},{"n":"Igołomia","lat":50.09192,"lng":20.24742,"typ":"gmina","sieci":2},{"n":"Czernichów","lat":49.98,"lng":19.68,"typ":"gmina","sieci":2},{"n":"Świątniki Górne","lat":49.93,"lng":19.95,"typ":"gmina","sieci":2},{"n":"Gdów","lat":49.90,"lng":20.19,"typ":"gmina","sieci":3},{"n":"Sułkowice","lat":49.83,"lng":19.79,"typ":"gmina","sieci":3},{"n":"Pcim","lat":49.75,"lng":19.97,"typ":"gmina","sieci":2},{"n":"Wieliczka","lat":49.98,"lng":20.06,"typ":"gmina","sieci":5},{"n":"Proszowice","lat":50.19,"lng":20.28,"typ":"gmina","sieci":3},{"n":"Tuchów","lat":49.89,"lng":21.05,"typ":"gmina","sieci":2},{"n":"Ryglice","lat":49.87,"lng":21.13,"typ":"gmina","sieci":2},{"n":"Gromnik","lat":49.83,"lng":20.96,"typ":"gmina","sieci":2},{"n":"Żabno","lat":50.13,"lng":20.88,"typ":"gmina","sieci":2},{"n":"Wojnicz","lat":49.96,"lng":20.84,"typ":"gmina","sieci":2},{"n":"Radłów","lat":50.08,"lng":20.85,"typ":"gmina","sieci":2},{"n":"Wietrzychowice","lat":50.19104,"lng":20.76308,"typ":"gmina","sieci":1},{"n":"Bolesław","lat":50.23,"lng":20.87,"typ":"gmina","sieci":1},{"n":"Olesno","lat":50.21,"lng":20.95,"typ":"gmina","sieci":2},{"n":"Szczucin","lat":50.31,"lng":21.07,"typ":"gmina","sieci":2},{"n":"Radgoszcz","lat":50.20548,"lng":21.11102,"typ":"gmina","sieci":1},{"n":"Dąbrowa Tarn.","lat":50.17,"lng":20.98,"typ":"gmina","sieci":4},{"n":"Skrzyszów","lat":49.99604,"lng":21.05464,"typ":"gmina","sieci":1},{"n":"Pleśna","lat":49.93,"lng":20.94,"typ":"gmina","sieci":2},{"n":"Tarnów Opol.","lat":49.95,"lng":21.00,"typ":"gmina","sieci":2},{"n":"Ciężkowice","lat":49.78,"lng":20.97,"typ":"gmina","sieci":2},{"n":"Świątniki","lat":49.92,"lng":19.95,"typ":"gmina","sieci":2},{"n":"Mogilany","lat":49.94,"lng":19.9,"typ":"gmina","sieci":2},{"n":"Myślenice","lat":49.83,"lng":19.94,"typ":"gmina","sieci":4},{"n":"Kalwaria Z.","lat":49.85,"lng":19.68,"typ":"gmina","sieci":3},{"n":"Wadowice","lat":49.88,"lng":19.49,"typ":"gmina","sieci":4},{"n":"Andrychów","lat":49.86,"lng":19.34,"typ":"gmina","sieci":4},{"n":"Kęty","lat":49.88,"lng":19.22,"typ":"gmina","sieci":4},{"n":"Zator","lat":49.99,"lng":19.43,"typ":"gmina","sieci":2},{"n":"Brzeźnica","lat":49.98,"lng":19.63,"typ":"gmina","sieci":2},{"n":"Alwernia","lat":50.06,"lng":19.54,"typ":"gmina","sieci":2},{"n":"Wielka Wieś","lat":50.15,"lng":19.83,"typ":"gmina","sieci":2},{"n":"Iwanowice","lat":50.22567,"lng":19.96377,"typ":"gmina","sieci":1},{"n":"Trzebinia","lat":50.16,"lng":19.47,"typ":"gmina","sieci":3},{"n":"Chrzanów","lat":50.14,"lng":19.4,"typ":"gmina","sieci":3},{"n":"Libiąż","lat":50.1,"lng":19.32,"typ":"gmina","sieci":2},{"n":"Olkusz","lat":50.28,"lng":19.56,"typ":"gmina","sieci":3},{"n":"Bukowno","lat":50.27,"lng":19.46,"typ":"gmina","sieci":2},{"n":"Wolbrom","lat":50.38,"lng":19.76,"typ":"gmina","sieci":2},{"n":"Miechów","lat":50.36,"lng":20.03,"typ":"gmina","sieci":2},{"n":"Książ Wielki","lat":50.45,"lng":20.13,"typ":"gmina","sieci":1},{"n":"Charsznica","lat":50.42,"lng":19.93,"typ":"gmina","sieci":1},{"n":"Gołcza","lat":50.33572,"lng":19.92647,"typ":"gmina","sieci":1},{"n":"Skała","lat":50.22,"lng":19.86,"typ":"gmina","sieci":1},{"n":"Sułoszowa","lat":50.27085,"lng":19.72150,"typ":"gmina","sieci":1},{"n":"Jerzmanowice","lat":50.2,"lng":19.75,"typ":"gmina","sieci":1},{"n":"Chełmek","lat":50.1,"lng":19.25,"typ":"gmina","sieci":1},{"n":"Oświęcim","lat":50.04,"lng":19.22,"typ":"gmina","sieci":3},{"n":"Brzeszcze","lat":49.98,"lng":19.15,"typ":"gmina","sieci":2},{"n":"Polanka W.","lat":49.99,"lng":19.35,"typ":"gmina","sieci":1},{"n":"Spytkowice","lat":49.99,"lng":19.53,"typ":"gmina","sieci":1},{"n":"Tomice","lat":49.90045,"lng":19.48514,"typ":"gmina","sieci":1},{"n":"Wieprz","lat":49.89913,"lng":19.36515,"typ":"gmina","sieci":1},{"n":"Stryszów","lat":49.82,"lng":19.6,"typ":"gmina","sieci":1},{"n":"Lanckorona","lat":49.85,"lng":19.72,"typ":"gmina","sieci":1},{"n":"Budzów","lat":49.78,"lng":19.7,"typ":"gmina","sieci":1},{"n":"Zembrzyce","lat":49.77377,"lng":19.60034,"typ":"gmina","sieci":1}],
  "dolnośląskie": [{"n":"Kąty Wrocławskie","lat":51.03,"lng":16.77,"typ":"gmina","sieci":3},{"n":"Kobierzyce","lat":50.96,"lng":16.93,"typ":"gmina","sieci":3},{"n":"Żórawina","lat":50.98,"lng":17.04,"typ":"gmina","sieci":2},{"n":"Siechnice","lat":51.03,"lng":17.15,"typ":"gmina","sieci":3},{"n":"Długołęka","lat":51.17,"lng":17.18,"typ":"gmina","sieci":3},{"n":"Czernica","lat":51.06,"lng":17.25,"typ":"gmina","sieci":2},{"n":"Miękinia","lat":51.19051,"lng":16.73623,"typ":"gmina","sieci":2},{"n":"Sobótka","lat":50.90,"lng":16.74,"typ":"gmina","sieci":3},{"n":"Oborniki Śląskie","lat":51.30,"lng":16.91,"typ":"gmina","sieci":3},{"n":"Jelcz-Laskowice","lat":51.03,"lng":17.33,"typ":"gmina","sieci":3},{"n":"Brzeg Dolny","lat":51.26,"lng":16.72,"typ":"gmina","sieci":2},{"n":"Wołów","lat":51.34,"lng":16.64,"typ":"gmina","sieci":3},{"n":"Żmigród","lat":51.47,"lng":16.90,"typ":"gmina","sieci":3},{"n":"Prusice","lat":51.37,"lng":16.96,"typ":"gmina","sieci":2},{"n":"Milicz","lat":51.53,"lng":17.28,"typ":"gmina","sieci":3},{"n":"Twardogóra","lat":51.36,"lng":17.47,"typ":"gmina","sieci":2},{"n":"Bierutów","lat":51.12523,"lng":17.54408,"typ":"gmina","sieci":2},{"n":"Strzelin","lat":50.78,"lng":17.06,"typ":"gmina","sieci":4},{"n":"Wiązów","lat":50.81,"lng":17.20,"typ":"gmina","sieci":2},{"n":"Borów","lat":50.79,"lng":17.02,"typ":"gmina","sieci":1},{"n":"Kondratowice","lat":50.77,"lng":16.93,"typ":"gmina","sieci":1},{"n":"Jordanów Śląski","lat":50.86,"lng":16.87,"typ":"gmina","sieci":2},{"n":"Marcinowice","lat":50.95,"lng":16.53,"typ":"gmina","sieci":2},{"n":"Żarów","lat":50.94,"lng":16.50,"typ":"gmina","sieci":3},{"n":"Jaworzyna Śl.","lat":50.91,"lng":16.44,"typ":"gmina","sieci":2},{"n":"Strzegom","lat":50.96,"lng":16.35,"typ":"gmina","sieci":4},{"n":"Udanin","lat":51.03689,"lng":16.45383,"typ":"gmina","sieci":2},{"n":"Kostomłoty","lat":51.04617,"lng":16.61097,"typ":"gmina","sieci":2},{"n":"Ziębice","lat":50.60,"lng":17.04,"typ":"gmina","sieci":3},{"n":"Ząbkowice Śl.","lat":50.59,"lng":16.81,"typ":"gmina","sieci":4},{"n":"Ciepłowody","lat":50.67,"lng":16.90,"typ":"gmina","sieci":1},{"n":"Kamieniec Ząb.","lat":50.52,"lng":16.88,"typ":"gmina","sieci":2},{"n":"Przeworno","lat":50.68,"lng":17.15,"typ":"gmina","sieci":1},{"n":"Łagiewniki","lat":50.79,"lng":16.84,"typ":"gmina","sieci":2},{"n":"Niemcza","lat":50.72,"lng":16.83,"typ":"gmina","sieci":2},{"n":"Piława Górna","lat":50.68,"lng":16.74,"typ":"gmina","sieci":2},{"n":"Dzierżoniów","lat":50.73,"lng":16.65,"typ":"gmina","sieci":4},{"n":"Pieszyce","lat":50.71212,"lng":16.58084,"typ":"gmina","sieci":2},{"n":"Bielawa","lat":50.68,"lng":16.61,"typ":"gmina","sieci":3},{"n":"Stoszowice","lat":50.60,"lng":16.74,"typ":"gmina","sieci":1},{"n":"Złoty Stok","lat":50.44,"lng":16.87,"typ":"gmina","sieci":2},{"n":"Kąty Wr.","lat":51.03,"lng":16.77,"typ":"gmina","sieci":3},{"n":"Wisznia Mała","lat":51.25124,"lng":17.04698,"typ":"gmina","sieci":2},{"n":"Oborniki Śl.","lat":51.3,"lng":16.92,"typ":"gmina","sieci":3},{"n":"Trzebnica","lat":51.31,"lng":17.06,"typ":"gmina","sieci":4},{"n":"Środa Śl.","lat":51.16,"lng":16.6,"typ":"gmina","sieci":3},{"n":"Mietków","lat":50.97463,"lng":16.65056,"typ":"gmina","sieci":1},{"n":"Oleśnica","lat":51.21,"lng":17.38,"typ":"gmina","sieci":3},{"n":"Dobroszyce","lat":51.26530,"lng":17.34092,"typ":"gmina","sieci":1},{"n":"Syców","lat":51.3,"lng":17.72,"typ":"gmina","sieci":2},{"n":"Międzybórz","lat":51.39827,"lng":17.66556,"typ":"gmina","sieci":1},{"n":"Oława","lat":50.94,"lng":17.3,"typ":"gmina","sieci":3},{"n":"Jelcz","lat":51.02,"lng":17.32,"typ":"gmina","sieci":2},{"n":"Domaniów","lat":50.89409,"lng":17.13087,"typ":"gmina","sieci":1},{"n":"Bardo","lat":50.5,"lng":16.75,"typ":"gmina","sieci":1},{"n":"Kamieniec Z.","lat":50.52,"lng":16.88,"typ":"gmina","sieci":1}],
  "pomorskie": [{"n":"Żukowo","lat":54.34,"lng":18.36,"typ":"gmina","sieci":3},{"n":"Skarszewy","lat":54.06,"lng":18.45,"typ":"gmina","sieci":2},{"n":"Rumia","lat":54.57,"lng":18.39,"typ":"gmina","sieci":4},{"n":"Reda","lat":54.60,"lng":18.35,"typ":"gmina","sieci":3},{"n":"Luzino","lat":54.56,"lng":18.10,"typ":"gmina","sieci":2},{"n":"Szemud","lat":54.49,"lng":18.22,"typ":"gmina","sieci":2},{"n":"Kosakowo","lat":54.59,"lng":18.48,"typ":"gmina","sieci":2},{"n":"Przodkowo","lat":54.38,"lng":18.26,"typ":"gmina","sieci":2},{"n":"Kolbudy","lat":54.27,"lng":18.46,"typ":"gmina","sieci":2},{"n":"Trąbki Wielkie","lat":54.17,"lng":18.54,"typ":"gmina","sieci":2},{"n":"Pszczółki","lat":54.17,"lng":18.70,"typ":"gmina","sieci":2},{"n":"Przywidz","lat":54.19,"lng":18.32,"typ":"gmina","sieci":2},{"n":"Somonino","lat":54.28,"lng":18.19,"typ":"gmina","sieci":2},{"n":"Stężyca","lat":54.21,"lng":17.96,"typ":"gmina","sieci":2},{"n":"Chmielno","lat":54.32,"lng":18.10,"typ":"gmina","sieci":2},{"n":"Sierakowice","lat":54.34,"lng":17.89,"typ":"gmina","sieci":3},{"n":"Sulęczyno","lat":54.23,"lng":17.77,"typ":"gmina","sieci":2},{"n":"Linia","lat":54.45142,"lng":17.93481,"typ":"gmina","sieci":2},{"n":"Krokowa","lat":54.78,"lng":18.16,"typ":"gmina","sieci":2},{"n":"Władysławowo","lat":54.79,"lng":18.40,"typ":"gmina","sieci":4},{"n":"Gniewino","lat":54.71,"lng":18.01,"typ":"gmina","sieci":2},{"n":"Łęczyce","lat":54.60,"lng":17.86,"typ":"gmina","sieci":2},{"n":"Kartuzy","lat":54.33,"lng":18.19,"typ":"gmina","sieci":4},{"n":"Pruszcz Gdań.","lat":54.26,"lng":18.63,"typ":"gmina","sieci":4},{"n":"Puck","lat":54.71,"lng":18.40,"typ":"gmina","sieci":3},{"n":"Kępice","lat":54.24,"lng":16.88,"typ":"gmina","sieci":2},{"n":"Trzebielino","lat":54.20073,"lng":17.08790,"typ":"gmina","sieci":1},{"n":"Kołczygłowy","lat":54.24,"lng":17.23,"typ":"gmina","sieci":1},{"n":"Dębnica Kasz.","lat":54.26,"lng":17.16,"typ":"gmina","sieci":2},{"n":"Czarna Dąbr.","lat":54.35,"lng":17.56,"typ":"gmina","sieci":2},{"n":"Borzytuchom","lat":54.19,"lng":17.37,"typ":"gmina","sieci":1},{"n":"Tuchomie","lat":54.12,"lng":17.33,"typ":"gmina","sieci":1},{"n":"Lipnica","lat":54.00,"lng":17.40,"typ":"gmina","sieci":2},{"n":"Parchowo","lat":54.20,"lng":17.66,"typ":"gmina","sieci":2},{"n":"Studzienice","lat":54.09,"lng":17.57,"typ":"gmina","sieci":1},{"n":"Bytów","lat":54.17,"lng":17.49,"typ":"gmina","sieci":4},{"n":"Miastko","lat":54.00,"lng":16.98,"typ":"gmina","sieci":4},{"n":"Koczała","lat":53.90220,"lng":17.06621,"typ":"gmina","sieci":1},{"n":"Przechlewo","lat":53.80054,"lng":17.25323,"typ":"gmina","sieci":2},{"n":"Pruszcz Gd.","lat":54.26,"lng":18.63,"typ":"gmina","sieci":4},{"n":"Trąbki Wlk.","lat":54.19,"lng":18.62,"typ":"gmina","sieci":1},{"n":"Cedry Wlk.","lat":54.24,"lng":18.79,"typ":"gmina","sieci":1},{"n":"Suchy Dąb","lat":54.20664,"lng":18.76769,"typ":"gmina","sieci":1},{"n":"Tczew okolice","lat":54.09,"lng":18.78,"typ":"gmina","sieci":2},{"n":"Subkowy","lat":54.00239,"lng":18.76893,"typ":"gmina","sieci":1},{"n":"Gniew","lat":53.84,"lng":18.82,"typ":"gmina","sieci":2},{"n":"Starogard okolice","lat":53.96,"lng":18.53,"typ":"gmina","sieci":2},{"n":"Zblewo","lat":53.93,"lng":18.32,"typ":"gmina","sieci":1},{"n":"Kaliska","lat":53.90532,"lng":18.21804,"typ":"gmina","sieci":1},{"n":"Lubichowo","lat":53.86,"lng":18.42,"typ":"gmina","sieci":1},{"n":"Osieczna","lat":53.77127,"lng":18.20232,"typ":"gmina","sieci":1},{"n":"Czarna Woda","lat":53.84451,"lng":18.09995,"typ":"gmina","sieci":1},{"n":"Osiek","lat":53.79,"lng":18.35,"typ":"gmina","sieci":1},{"n":"Wejherowo","lat":54.6,"lng":18.24,"typ":"gmina","sieci":3},{"n":"Jastarnia","lat":54.7,"lng":18.68,"typ":"gmina","sieci":1},{"n":"Hel","lat":54.61,"lng":18.8,"typ":"gmina","sieci":1},{"n":"Choczewo","lat":54.74046,"lng":17.89163,"typ":"gmina","sieci":1},{"n":"Czarne","lat":53.68,"lng":16.93,"typ":"gmina","sieci":1},{"n":"Człuchów","lat":53.66,"lng":17.36,"typ":"gmina","sieci":3},{"n":"Debrzno","lat":53.54,"lng":17.24,"typ":"gmina","sieci":1}],
  "lubelskie": [{"n":"Niemce","lat":51.35,"lng":22.63,"typ":"gmina","sieci":2},{"n":"Poniatowa","lat":51.17,"lng":22.06,"typ":"gmina","sieci":2},{"n":"Bychawa","lat":51.01,"lng":22.53,"typ":"gmina","sieci":2},{"n":"Bełżyce","lat":51.17,"lng":22.28,"typ":"gmina","sieci":2},{"n":"Niedrzwica D.","lat":51.11,"lng":22.38,"typ":"gmina","sieci":2},{"n":"Piaski","lat":51.13,"lng":22.84,"typ":"gmina","sieci":2},{"n":"Nałęczów","lat":51.28,"lng":22.21,"typ":"gmina","sieci":2},{"n":"Garbów","lat":51.35,"lng":22.33,"typ":"gmina","sieci":2},{"n":"Jastków","lat":51.30,"lng":22.44,"typ":"gmina","sieci":2},{"n":"Wąwolnica","lat":51.29,"lng":22.14,"typ":"gmina","sieci":2},{"n":"Kurów","lat":51.39,"lng":22.18,"typ":"gmina","sieci":2},{"n":"Końskowola","lat":51.41,"lng":22.05,"typ":"gmina","sieci":2},{"n":"Kock","lat":51.64,"lng":22.44,"typ":"gmina","sieci":2},{"n":"Kamionka","lat":51.47,"lng":22.46,"typ":"gmina","sieci":2},{"n":"Firlej","lat":51.55,"lng":22.50,"typ":"gmina","sieci":2},{"n":"Spiczyn","lat":51.34174,"lng":22.75342,"typ":"gmina","sieci":2},{"n":"Milejów","lat":51.22,"lng":22.92,"typ":"gmina","sieci":2},{"n":"Rybczewice","lat":51.06,"lng":22.86,"typ":"gmina","sieci":1},{"n":"Świdnik","lat":51.21,"lng":22.69,"typ":"gmina","sieci":4},{"n":"Łęczna","lat":51.30,"lng":22.88,"typ":"gmina","sieci":3},{"n":"Lubartów","lat":51.46,"lng":22.60,"typ":"gmina","sieci":4},{"n":"Urzędów","lat":50.99,"lng":22.14,"typ":"gmina","sieci":2},{"n":"Zakrzówek","lat":50.95123,"lng":22.38029,"typ":"gmina","sieci":1},{"n":"Batorz","lat":50.84928,"lng":22.49307,"typ":"gmina","sieci":1},{"n":"Chodel","lat":51.11,"lng":22.13,"typ":"gmina","sieci":2},{"n":"Opole Lub.","lat":51.14,"lng":21.97,"typ":"gmina","sieci":3},{"n":"Karczmiska","lat":51.22,"lng":22.01,"typ":"gmina","sieci":2},{"n":"Wojciechów","lat":51.23,"lng":22.03,"typ":"gmina","sieci":1},{"n":"Puławy","lat":51.41,"lng":21.96,"typ":"gmina","sieci":5},{"n":"Gołąb","lat":51.35,"lng":22.33,"typ":"gmina","sieci":1},{"n":"Markuszów","lat":51.37,"lng":22.26,"typ":"gmina","sieci":1},{"n":"Baranów","lat":51.55,"lng":22.13,"typ":"gmina","sieci":2},{"n":"Michów","lat":51.52,"lng":22.31,"typ":"gmina","sieci":2},{"n":"Jeziorzany","lat":51.59,"lng":22.27,"typ":"gmina","sieci":1},{"n":"Abramów","lat":51.46,"lng":22.31,"typ":"gmina","sieci":1},{"n":"Ryki","lat":51.62,"lng":21.93,"typ":"gmina","sieci":3},{"n":"Dęblin","lat":51.56,"lng":21.84,"typ":"gmina","sieci":3},{"n":"Stężyca","lat":51.58033,"lng":21.77666,"typ":"gmina","sieci":2},{"n":"Mełgiew","lat":51.23085,"lng":22.78056,"typ":"gmina","sieci":2},{"n":"Wólka","lat":51.24,"lng":22.66,"typ":"gmina","sieci":2},{"n":"Konopnica","lat":51.22,"lng":22.44,"typ":"gmina","sieci":2},{"n":"Głusk","lat":51.18858,"lng":22.63002,"typ":"gmina","sieci":2},{"n":"Strzyżewice","lat":51.05207,"lng":22.44602,"typ":"gmina","sieci":1},{"n":"Krzczonów","lat":51.00704,"lng":22.71056,"typ":"gmina","sieci":1},{"n":"Borzechów","lat":51.1,"lng":22.3,"typ":"gmina","sieci":1},{"n":"Lubartów okolice","lat":51.46,"lng":22.61,"typ":"gmina","sieci":2},{"n":"Kraśnik","lat":50.92,"lng":22.22,"typ":"gmina","sieci":3},{"n":"Annopol","lat":50.88,"lng":21.85,"typ":"gmina","sieci":1},{"n":"Modliborzyce","lat":50.75,"lng":22.33,"typ":"gmina","sieci":1},{"n":"Janów Lub.","lat":50.71,"lng":22.41,"typ":"gmina","sieci":2},{"n":"Frampol","lat":50.67,"lng":22.67,"typ":"gmina","sieci":1},{"n":"Goraj","lat":50.72,"lng":22.66,"typ":"gmina","sieci":1},{"n":"Turobin","lat":50.83,"lng":22.74,"typ":"gmina","sieci":1},{"n":"Szczebrzeszyn","lat":50.7,"lng":22.98,"typ":"gmina","sieci":2},{"n":"Zwierzyniec","lat":50.61,"lng":22.97,"typ":"gmina","sieci":1},{"n":"Józefów","lat":50.48,"lng":23.05,"typ":"gmina","sieci":1},{"n":"Krasnobród","lat":50.55,"lng":23.21,"typ":"gmina","sieci":1},{"n":"Tomaszów Lub.","lat":50.45,"lng":23.42,"typ":"gmina","sieci":3},{"n":"Tarnawatka","lat":50.53,"lng":23.4,"typ":"gmina","sieci":1},{"n":"Łaszczów","lat":50.53,"lng":23.72,"typ":"gmina","sieci":1},{"n":"Tyszowce","lat":50.62,"lng":23.7,"typ":"gmina","sieci":1},{"n":"Komarów","lat":50.65,"lng":23.45,"typ":"gmina","sieci":1},{"n":"Zamość okolice","lat":50.72,"lng":23.25,"typ":"gmina","sieci":3},{"n":"Sitno","lat":50.68,"lng":23.38,"typ":"gmina","sieci":1},{"n":"Skierbieszów","lat":50.85153,"lng":23.36520,"typ":"gmina","sieci":1},{"n":"Izbica","lat":50.88,"lng":23.16,"typ":"gmina","sieci":1},{"n":"Krasnystaw","lat":50.98,"lng":23.17,"typ":"gmina","sieci":3},{"n":"Fajsławice","lat":51.09515,"lng":22.96307,"typ":"gmina","sieci":1},{"n":"Łopiennik Górny","lat":51.03810,"lng":23.01748,"typ":"gmina","sieci":1},{"n":"Siennica Róż.","lat":51.07,"lng":23.25,"typ":"gmina","sieci":1},{"n":"Stoczek Łukowski","lat":51.96165,"lng":21.96874,"typ":"gmina","sieci":2}],
  "kujawsko-pomorskie": [{"n":"Solec Kujawski","lat":53.08,"lng":18.22,"typ":"gmina","sieci":3},{"n":"Koronowo","lat":53.31,"lng":17.93,"typ":"gmina","sieci":3},{"n":"Chełmża","lat":53.18,"lng":18.60,"typ":"gmina","sieci":3},{"n":"Szubin","lat":53.00,"lng":17.74,"typ":"gmina","sieci":3},{"n":"Barcin","lat":52.85,"lng":17.95,"typ":"gmina","sieci":2},{"n":"Łabiszyn","lat":52.95,"lng":17.91,"typ":"gmina","sieci":2},{"n":"Złotniki Kuj.","lat":52.89,"lng":18.14,"typ":"gmina","sieci":2},{"n":"Pakość","lat":52.80,"lng":18.08,"typ":"gmina","sieci":2},{"n":"Ciechocinek","lat":52.88,"lng":18.79,"typ":"gmina","sieci":3},{"n":"Gniewkowo","lat":52.89,"lng":18.41,"typ":"gmina","sieci":2},{"n":"Janikowo","lat":52.75,"lng":18.11,"typ":"gmina","sieci":2},{"n":"Kruszwica","lat":52.68,"lng":18.32,"typ":"gmina","sieci":3},{"n":"Strzelno","lat":52.63,"lng":18.17,"typ":"gmina","sieci":2},{"n":"Radziejów","lat":52.62,"lng":18.52,"typ":"gmina","sieci":3},{"n":"Piotrków Kuj.","lat":52.55,"lng":18.49,"typ":"gmina","sieci":2},{"n":"Zakrzewo","lat":52.76,"lng":18.63,"typ":"gmina","sieci":1},{"n":"Koneck","lat":52.78,"lng":18.71,"typ":"gmina","sieci":1},{"n":"Aleksandrów Kuj.","lat":52.87,"lng":18.70,"typ":"gmina","sieci":3},{"n":"Raciążek","lat":52.85759,"lng":18.80815,"typ":"gmina","sieci":2},{"n":"Lubanie","lat":52.74748,"lng":18.92003,"typ":"gmina","sieci":2},{"n":"Waganiec","lat":52.80,"lng":18.85,"typ":"gmina","sieci":1},{"n":"Skępe","lat":52.86,"lng":19.34,"typ":"gmina","sieci":2},{"n":"Tłuchowo","lat":52.74,"lng":19.46,"typ":"gmina","sieci":2},{"n":"Dobrzyń n. Wisłą","lat":52.63,"lng":19.32,"typ":"gmina","sieci":2},{"n":"Nakło n. Notecią","lat":53.14,"lng":17.60,"typ":"gmina","sieci":3},{"n":"Sadki","lat":53.15,"lng":17.44,"typ":"gmina","sieci":2},{"n":"Mrocza","lat":53.24,"lng":17.60,"typ":"gmina","sieci":2},{"n":"Kcynia","lat":52.99165,"lng":17.48835,"typ":"gmina","sieci":2},{"n":"Sicienko","lat":53.20,"lng":17.81,"typ":"gmina","sieci":1},{"n":"Witosław","lat":53.24008,"lng":17.48645,"typ":"gmina","sieci":1},{"n":"Śmielin","lat":53.15025,"lng":17.48696,"typ":"gmina","sieci":1},{"n":"Dziewierzewo","lat":52.94627,"lng":17.52253,"typ":"gmina","sieci":1},{"n":"Żnin","lat":52.84927,"lng":17.72077,"typ":"gmina","sieci":3},{"n":"Janowiec Wlkp.","lat":52.75,"lng":17.49,"typ":"gmina","sieci":2},{"n":"Rogowo","lat":52.72,"lng":17.64,"typ":"gmina","sieci":2},{"n":"Gąsawa","lat":52.76,"lng":17.74,"typ":"gmina","sieci":2},{"n":"Solec Kuj.","lat":53.08,"lng":18.22,"typ":"gmina","sieci":3},{"n":"Białe Błota","lat":53.08,"lng":17.93,"typ":"gmina","sieci":2},{"n":"Nowa Wieś Wlk.","lat":53.14,"lng":17.86,"typ":"gmina","sieci":2},{"n":"Osielsko","lat":53.18,"lng":18.05,"typ":"gmina","sieci":2},{"n":"Dobrcz","lat":53.26540,"lng":18.14645,"typ":"gmina","sieci":1},{"n":"Dąbrowa Chełm.","lat":53.13,"lng":18.42,"typ":"gmina","sieci":1},{"n":"Unisław","lat":53.20991,"lng":18.38240,"typ":"gmina","sieci":1},{"n":"Kowalewo Pom.","lat":53.17,"lng":18.86,"typ":"gmina","sieci":2},{"n":"Łysomice","lat":53.09,"lng":18.63,"typ":"gmina","sieci":1},{"n":"Lubicz","lat":53.03221,"lng":18.74987,"typ":"gmina","sieci":2},{"n":"Obrowo","lat":52.96,"lng":18.87,"typ":"gmina","sieci":1},{"n":"Czernikowo","lat":52.94,"lng":18.92,"typ":"gmina","sieci":1},{"n":"Wielka Nieszawka","lat":53.0,"lng":18.5,"typ":"gmina","sieci":1},{"n":"Zławieś Wlk.","lat":53.08,"lng":18.42,"typ":"gmina","sieci":1},{"n":"Nakło","lat":53.14,"lng":17.6,"typ":"gmina","sieci":3},{"n":"Więcbork","lat":53.35,"lng":17.51,"typ":"gmina","sieci":1},{"n":"Sępólno Kr.","lat":53.45,"lng":17.53,"typ":"gmina","sieci":2},{"n":"Tuchola","lat":53.59,"lng":17.86,"typ":"gmina","sieci":2},{"n":"Śliwice","lat":53.7,"lng":18.19,"typ":"gmina","sieci":1},{"n":"Cekcyn","lat":53.57295,"lng":18.01018,"typ":"gmina","sieci":1},{"n":"Kęsowo","lat":53.55791,"lng":17.71466,"typ":"gmina","sieci":1},{"n":"Gostycyn","lat":53.48988,"lng":17.80968,"typ":"gmina","sieci":1},{"n":"Świecie","lat":53.41,"lng":18.44,"typ":"gmina","sieci":3},{"n":"Nowe","lat":53.65,"lng":18.73,"typ":"gmina","sieci":1},{"n":"Warlubie","lat":53.58763,"lng":18.62997,"typ":"gmina","sieci":1},{"n":"Jeżewo","lat":53.51,"lng":18.55,"typ":"gmina","sieci":1},{"n":"Bukowiec","lat":53.44,"lng":18.34,"typ":"gmina","sieci":1},{"n":"Pruszcz","lat":53.36,"lng":18.32,"typ":"gmina","sieci":1},{"n":"Świekatowo","lat":53.41912,"lng":18.09102,"typ":"gmina","sieci":1},{"n":"Lniano","lat":53.52798,"lng":18.21455,"typ":"gmina","sieci":1},{"n":"Drzycim","lat":53.51353,"lng":18.31649,"typ":"gmina","sieci":1},{"n":"Grudziądz","lat":53.48,"lng":18.75,"typ":"gmina","sieci":4},{"n":"Łasin","lat":53.52,"lng":19.09,"typ":"gmina","sieci":1},{"n":"Radzyń Chełm.","lat":53.38,"lng":18.93,"typ":"gmina","sieci":1},{"n":"Gruta","lat":53.46,"lng":18.98,"typ":"gmina","sieci":1},{"n":"Rogóźno","lat":53.53561,"lng":18.92870,"typ":"gmina","sieci":1},{"n":"Świecie nad Osą","lat":53.44401,"lng":19.10279,"typ":"gmina","sieci":1}],
  "zachodniopomorskie": [{"n":"Chojna","lat":52.96,"lng":14.42,"typ":"gmina","sieci":2},{"n":"Nowogard","lat":53.66,"lng":15.11,"typ":"gmina","sieci":3},{"n":"Maszewo","lat":53.49,"lng":15.05,"typ":"gmina","sieci":2},{"n":"Stepnica","lat":53.65,"lng":14.62,"typ":"gmina","sieci":2},{"n":"Wolin","lat":53.84,"lng":14.61,"typ":"gmina","sieci":3},{"n":"Międzyzdroje","lat":53.92,"lng":14.44,"typ":"gmina","sieci":3},{"n":"Kołbaskowo","lat":53.33,"lng":14.43,"typ":"gmina","sieci":2},{"n":"Nowe Warpno","lat":53.72,"lng":14.28,"typ":"gmina","sieci":1},{"n":"Banie","lat":53.10,"lng":14.66,"typ":"gmina","sieci":2},{"n":"Widuchowa","lat":53.12,"lng":14.38,"typ":"gmina","sieci":2},{"n":"Cedynia","lat":52.88,"lng":14.20,"typ":"gmina","sieci":2},{"n":"Mieszkowice","lat":52.78,"lng":14.49,"typ":"gmina","sieci":2},{"n":"Moryń","lat":52.85,"lng":14.39,"typ":"gmina","sieci":2},{"n":"Trzcińsko-Zdrój","lat":52.96,"lng":14.61,"typ":"gmina","sieci":2},{"n":"Kozielice","lat":53.07,"lng":14.80,"typ":"gmina","sieci":1},{"n":"Warnice","lat":53.25,"lng":14.99,"typ":"gmina","sieci":1},{"n":"Bielice","lat":53.16,"lng":14.65,"typ":"gmina","sieci":2},{"n":"Przelewice","lat":53.10,"lng":15.08,"typ":"gmina","sieci":2},{"n":"Stare Czarnowo","lat":53.27,"lng":14.77,"typ":"gmina","sieci":2},{"n":"Kobylanka","lat":53.34,"lng":14.88,"typ":"gmina","sieci":2},{"n":"Stara Dąbrowa","lat":53.42133,"lng":15.14300,"typ":"gmina","sieci":1},{"n":"Dziwnów","lat":54.02478,"lng":14.75330,"typ":"gmina","sieci":3},{"n":"Kamień Pomorski","lat":53.97,"lng":14.76,"typ":"gmina","sieci":3},{"n":"Świerzno","lat":53.96515,"lng":14.96612,"typ":"gmina","sieci":1},{"n":"Gryfice","lat":53.91,"lng":15.19,"typ":"gmina","sieci":4},{"n":"Karnice","lat":54.02,"lng":15.02,"typ":"gmina","sieci":1},{"n":"Rewal","lat":54.08,"lng":15.01,"typ":"gmina","sieci":3},{"n":"Trzebiatów","lat":54.06,"lng":15.26,"typ":"gmina","sieci":3},{"n":"Brojce","lat":53.95747,"lng":15.35110,"typ":"gmina","sieci":1},{"n":"Płoty","lat":53.80316,"lng":15.26728,"typ":"gmina","sieci":2},{"n":"Resko","lat":53.77302,"lng":15.40611,"typ":"gmina","sieci":2},{"n":"Radowo Małe","lat":53.66567,"lng":15.44744,"typ":"gmina","sieci":1},{"n":"Węgorzyno","lat":53.54,"lng":15.55,"typ":"gmina","sieci":2},{"n":"Dobra","lat":53.58,"lng":15.30,"typ":"gmina","sieci":2},{"n":"Marianowo","lat":53.38252,"lng":15.26720,"typ":"gmina","sieci":1},{"n":"Suchań","lat":53.27,"lng":15.32,"typ":"gmina","sieci":1},{"n":"Dobrzany","lat":53.35,"lng":15.42,"typ":"gmina","sieci":2},{"n":"Chociwel","lat":53.46688,"lng":15.33348,"typ":"gmina","sieci":2},{"n":"Dobra Szcz.","lat":53.46,"lng":14.44,"typ":"gmina","sieci":2},{"n":"Police","lat":53.55,"lng":14.57,"typ":"gmina","sieci":4},{"n":"Goleniów","lat":53.56,"lng":14.83,"typ":"gmina","sieci":4},{"n":"Gryfino","lat":53.25,"lng":14.49,"typ":"gmina","sieci":3},{"n":"Stargard okolice","lat":53.34,"lng":15.05,"typ":"gmina","sieci":2},{"n":"Pyrzyce","lat":53.15,"lng":14.89,"typ":"gmina","sieci":3},{"n":"Lipiany","lat":53.01,"lng":14.97,"typ":"gmina","sieci":1},{"n":"Barlinek","lat":52.99,"lng":15.22,"typ":"gmina","sieci":3},{"n":"Myślibórz","lat":52.92,"lng":14.87,"typ":"gmina","sieci":3},{"n":"Dębno","lat":52.74,"lng":14.7,"typ":"gmina","sieci":3},{"n":"Boleszkowice","lat":52.72,"lng":14.57,"typ":"gmina","sieci":1},{"n":"Świnoujście","lat":53.91,"lng":14.25,"typ":"gmina","sieci":3},{"n":"Kamień Pom.","lat":53.97,"lng":14.77,"typ":"gmina","sieci":2},{"n":"Golczewo","lat":53.82,"lng":14.98,"typ":"gmina","sieci":1},{"n":"Świdwin","lat":53.77,"lng":15.78,"typ":"gmina","sieci":2},{"n":"Połczyn-Zdrój","lat":53.76,"lng":16.1,"typ":"gmina","sieci":2},{"n":"Białogard","lat":54.01,"lng":15.99,"typ":"gmina","sieci":3},{"n":"Karlino","lat":54.04,"lng":15.87,"typ":"gmina","sieci":1},{"n":"Tychowo","lat":53.9,"lng":16.25,"typ":"gmina","sieci":1},{"n":"Szczecinek","lat":53.71,"lng":16.7,"typ":"gmina","sieci":3},{"n":"Borne Sulinowo","lat":53.58,"lng":16.53,"typ":"gmina","sieci":1},{"n":"Barwice","lat":53.75,"lng":16.35,"typ":"gmina","sieci":1},{"n":"Grzmiąca","lat":53.83,"lng":16.42,"typ":"gmina","sieci":1},{"n":"Czaplinek","lat":53.55,"lng":16.23,"typ":"gmina","sieci":2},{"n":"Drawsko Pom.","lat":53.53,"lng":15.81,"typ":"gmina","sieci":2},{"n":"Złocieniec","lat":53.53,"lng":16.01,"typ":"gmina","sieci":2},{"n":"Kalisz Pom.","lat":53.3,"lng":15.9,"typ":"gmina","sieci":1},{"n":"Wałcz","lat":53.27,"lng":16.47,"typ":"gmina","sieci":3},{"n":"Mirosławiec","lat":53.35,"lng":16.09,"typ":"gmina","sieci":1}],
  "świętokrzyskie": [{"n":"Chęciny","lat":50.79,"lng":20.46,"typ":"gmina","sieci":2},{"n":"Morawica","lat":50.75,"lng":20.61,"typ":"gmina","sieci":2},{"n":"Suchedniów","lat":51.04,"lng":20.83,"typ":"gmina","sieci":2},{"n":"Piekoszów","lat":50.88,"lng":20.46,"typ":"gmina","sieci":2},{"n":"Daleszyce","lat":50.80,"lng":20.80,"typ":"gmina","sieci":2},{"n":"Górno","lat":50.84882,"lng":20.82202,"typ":"gmina","sieci":1},{"n":"Masłów","lat":50.90374,"lng":20.72767,"typ":"gmina","sieci":1},{"n":"Zagnańsk","lat":50.98,"lng":20.66,"typ":"gmina","sieci":2},{"n":"Bodzentyn","lat":50.94,"lng":20.95,"typ":"gmina","sieci":2},{"n":"Miedziana Góra","lat":50.94,"lng":20.58,"typ":"gmina","sieci":2},{"n":"Strawczyn","lat":50.93,"lng":20.42,"typ":"gmina","sieci":2},{"n":"Łopuszno","lat":50.94862,"lng":20.25060,"typ":"gmina","sieci":2},{"n":"Sobków","lat":50.69,"lng":20.46,"typ":"gmina","sieci":2},{"n":"Małogoszcz","lat":50.81,"lng":20.26,"typ":"gmina","sieci":2},{"n":"Mniów","lat":51.02,"lng":20.48,"typ":"gmina","sieci":2},{"n":"Smyków","lat":51.05,"lng":20.40,"typ":"gmina","sieci":1},{"n":"Stąporków","lat":51.14,"lng":20.55,"typ":"gmina","sieci":3},{"n":"Bliżyn","lat":51.10,"lng":20.76,"typ":"gmina","sieci":2},{"n":"Wąchock","lat":51.07,"lng":21.01,"typ":"gmina","sieci":2},{"n":"Bieliny","lat":50.84,"lng":20.94,"typ":"gmina","sieci":2},{"n":"Łagów","lat":50.77,"lng":21.08,"typ":"gmina","sieci":2},{"n":"Raków","lat":50.67,"lng":21.04,"typ":"gmina","sieci":2},{"n":"Nowa Słupia","lat":50.86,"lng":21.08,"typ":"gmina","sieci":2},{"n":"Krasocin","lat":50.88972,"lng":20.11742,"typ":"gmina","sieci":2},{"n":"Ruda Maleniecka","lat":51.14688,"lng":20.22112,"typ":"gmina","sieci":1},{"n":"Fałków","lat":51.13473,"lng":20.10063,"typ":"gmina","sieci":1},{"n":"Gowarczów","lat":51.27839,"lng":20.43802,"typ":"gmina","sieci":2},{"n":"Słupia Konecka","lat":51.00,"lng":20.00,"typ":"gmina","sieci":1},{"n":"Secemin","lat":50.76815,"lng":19.83725,"typ":"gmina","sieci":2},{"n":"Radków","lat":50.71,"lng":19.98,"typ":"gmina","sieci":1},{"n":"Moskorzew","lat":50.64639,"lng":19.93065,"typ":"gmina","sieci":1},{"n":"Słupia","lat":50.61,"lng":20.01,"typ":"gmina","sieci":2},{"n":"Kluczewsko","lat":50.92712,"lng":19.91917,"typ":"gmina","sieci":2},{"n":"Włoszczowa","lat":50.85,"lng":19.96,"typ":"gmina","sieci":3},{"n":"Złotniki","lat":50.74989,"lng":20.25037,"typ":"gmina","sieci":1},{"n":"Nowy Korczyn","lat":50.31,"lng":20.80,"typ":"gmina","sieci":2},{"n":"Wiślica","lat":50.34,"lng":20.67,"typ":"gmina","sieci":2},{"n":"Opatowiec","lat":50.24,"lng":20.72,"typ":"gmina","sieci":1},{"n":"Solec-Zdrój","lat":50.36659,"lng":20.88693,"typ":"gmina","sieci":2},{"n":"Sitkówka","lat":50.81114,"lng":20.55493,"typ":"gmina","sieci":2},{"n":"Pierzchnica","lat":50.69738,"lng":20.75381,"typ":"gmina","sieci":1},{"n":"Busko-Zdrój","lat":50.47,"lng":20.72,"typ":"gmina","sieci":4},{"n":"Stopnica","lat":50.45,"lng":20.94,"typ":"gmina","sieci":1},{"n":"Jędrzejów","lat":50.64,"lng":20.3,"typ":"gmina","sieci":3},{"n":"Sędziszów","lat":50.57,"lng":20.06,"typ":"gmina","sieci":2},{"n":"Końskie","lat":51.19,"lng":20.41,"typ":"gmina","sieci":3},{"n":"Radoszyce","lat":51.07,"lng":20.25,"typ":"gmina","sieci":1},{"n":"Skarżysko","lat":51.11,"lng":20.87,"typ":"gmina","sieci":3},{"n":"Ostrowiec Św.","lat":50.93,"lng":21.39,"typ":"gmina","sieci":4},{"n":"Kunów","lat":50.95473,"lng":21.27937,"typ":"gmina","sieci":1},{"n":"Ćmielów","lat":50.9,"lng":21.51,"typ":"gmina","sieci":1},{"n":"Bodzechów","lat":50.90888,"lng":21.43933,"typ":"gmina","sieci":1},{"n":"Waśniów","lat":50.89924,"lng":21.22317,"typ":"gmina","sieci":1},{"n":"Ożarów","lat":50.88,"lng":21.66,"typ":"gmina","sieci":1},{"n":"Sandomierz","lat":50.68,"lng":21.75,"typ":"gmina","sieci":3},{"n":"Zawichost","lat":50.8,"lng":21.85,"typ":"gmina","sieci":1},{"n":"Klimontów","lat":50.68,"lng":21.42,"typ":"gmina","sieci":1},{"n":"Koprzywnica","lat":50.61,"lng":21.58,"typ":"gmina","sieci":1},{"n":"Łoniów","lat":50.56,"lng":21.55,"typ":"gmina","sieci":1}],
  "podkarpackie": [{"n":"Boguchwała","lat":49.98,"lng":21.93,"typ":"gmina","sieci":3},{"n":"Głogów Młp.","lat":50.15,"lng":21.96,"typ":"gmina","sieci":3},{"n":"Tyczyn","lat":49.96,"lng":22.02,"typ":"gmina","sieci":2},{"n":"Trzebownisko","lat":50.08,"lng":22.05,"typ":"gmina","sieci":2},{"n":"Sędziszów Młp.","lat":50.07,"lng":21.70,"typ":"gmina","sieci":3},{"n":"Dynów","lat":49.82,"lng":22.23,"typ":"gmina","sieci":2},{"n":"Czudec","lat":49.94,"lng":21.83,"typ":"gmina","sieci":2},{"n":"Świlcza","lat":50.06,"lng":21.91,"typ":"gmina","sieci":2},{"n":"Krasne","lat":50.04,"lng":22.06,"typ":"gmina","sieci":2},{"n":"Chmielnik","lat":49.98351,"lng":22.11606,"typ":"gmina","sieci":2},{"n":"Błażowa","lat":49.88,"lng":22.09,"typ":"gmina","sieci":2},{"n":"Niebylec","lat":49.85,"lng":21.89,"typ":"gmina","sieci":2},{"n":"Wiśniowa","lat":49.87,"lng":21.65,"typ":"gmina","sieci":2},{"n":"Wielopole Skrzyńskie","lat":49.94613,"lng":21.61513,"typ":"gmina","sieci":2},{"n":"Iwierzyce","lat":50.03,"lng":21.78,"typ":"gmina","sieci":2},{"n":"Sokołów Młp.","lat":50.23,"lng":22.11,"typ":"gmina","sieci":2},{"n":"Raniżów","lat":50.26,"lng":21.98,"typ":"gmina","sieci":1},{"n":"Dzikowiec","lat":50.27,"lng":21.84,"typ":"gmina","sieci":1},{"n":"Kolbuszowa","lat":50.24,"lng":21.76,"typ":"gmina","sieci":4},{"n":"Niwiska","lat":50.22415,"lng":21.63911,"typ":"gmina","sieci":1},{"n":"Majdan Król.","lat":50.36,"lng":21.76,"typ":"gmina","sieci":2},{"n":"Cmolas","lat":50.29504,"lng":21.74464,"typ":"gmina","sieci":1},{"n":"Tuszów Nar.","lat":50.37,"lng":21.46,"typ":"gmina","sieci":2},{"n":"Mielec","lat":50.28,"lng":21.42,"typ":"gmina","sieci":5},{"n":"Przecław","lat":50.19,"lng":21.48,"typ":"gmina","sieci":2},{"n":"Radomyśl Wlk.","lat":50.19,"lng":21.27,"typ":"gmina","sieci":3},{"n":"Wadowice G.","lat":50.20,"lng":21.24,"typ":"gmina","sieci":1},{"n":"Żyraków","lat":50.08554,"lng":21.39596,"typ":"gmina","sieci":2},{"n":"Czarna","lat":50.06,"lng":21.24,"typ":"gmina","sieci":2},{"n":"Pilzno","lat":49.97,"lng":21.29,"typ":"gmina","sieci":2},{"n":"Jodłowa","lat":49.88,"lng":21.29,"typ":"gmina","sieci":2},{"n":"Brzostek","lat":49.87912,"lng":21.41165,"typ":"gmina","sieci":2},{"n":"Frysztak","lat":49.83,"lng":21.61,"typ":"gmina","sieci":2},{"n":"Kołaczyce","lat":49.81,"lng":21.43,"typ":"gmina","sieci":2},{"n":"Brzyska","lat":49.82176,"lng":21.38856,"typ":"gmina","sieci":1},{"n":"Jasło","lat":49.74,"lng":21.47,"typ":"gmina","sieci":4},{"n":"Hyżne","lat":49.92093,"lng":22.17192,"typ":"gmina","sieci":1},{"n":"Kańczuga","lat":49.99,"lng":22.41,"typ":"gmina","sieci":2},{"n":"Pruchnik","lat":49.9,"lng":22.51,"typ":"gmina","sieci":1},{"n":"Roźwienica","lat":49.95257,"lng":22.59427,"typ":"gmina","sieci":1},{"n":"Jawornik Polski","lat":49.88909,"lng":22.28578,"typ":"gmina","sieci":1},{"n":"Kamień","lat":50.32914,"lng":22.13831,"typ":"gmina","sieci":1},{"n":"Łańcut","lat":50.07,"lng":22.23,"typ":"gmina","sieci":3},{"n":"Leżajsk","lat":50.26,"lng":22.42,"typ":"gmina","sieci":3},{"n":"Nowa Sarzyna","lat":50.32,"lng":22.32,"typ":"gmina","sieci":1},{"n":"Nisko","lat":50.52,"lng":22.14,"typ":"gmina","sieci":3},{"n":"Stalowa Wola","lat":50.58,"lng":22.05,"typ":"gmina","sieci":4},{"n":"Rudnik nad Sanem","lat":50.44160,"lng":22.24656,"typ":"gmina","sieci":1},{"n":"Ulanów","lat":50.49,"lng":22.27,"typ":"gmina","sieci":1},{"n":"Krzeszów","lat":50.42,"lng":22.34,"typ":"gmina","sieci":1},{"n":"Tarnobrzeg","lat":50.57,"lng":21.68,"typ":"gmina","sieci":3},{"n":"Baranów Sand.","lat":50.5,"lng":21.53,"typ":"gmina","sieci":1},{"n":"Nowa Dęba","lat":50.41637,"lng":21.75027,"typ":"gmina","sieci":2},{"n":"Majdan Kr.","lat":50.36,"lng":21.9,"typ":"gmina","sieci":1},{"n":"Ropczyce","lat":50.05,"lng":21.61,"typ":"gmina","sieci":3},{"n":"Dębica","lat":50.05,"lng":21.41,"typ":"gmina","sieci":3},{"n":"Strzyżów","lat":49.87,"lng":21.79,"typ":"gmina","sieci":2},{"n":"Zaklików","lat":50.75589,"lng":22.10196,"typ":"gmina","sieci":1}],
  "podlaskie": [{"n":"Choroszcz","lat":53.14,"lng":22.98,"typ":"gmina","sieci":2},{"n":"Wasilków","lat":53.20,"lng":23.20,"typ":"gmina","sieci":3},{"n":"Supraśl","lat":53.21,"lng":23.33,"typ":"gmina","sieci":2},{"n":"Czarna Białost.","lat":53.30,"lng":23.28,"typ":"gmina","sieci":2},{"n":"Zabłudów","lat":53.01,"lng":23.34,"typ":"gmina","sieci":2},{"n":"Łapy","lat":52.99,"lng":22.88,"typ":"gmina","sieci":3},{"n":"Michałowo","lat":53.03,"lng":23.60,"typ":"gmina","sieci":2},{"n":"Juchnowiec Kośc.","lat":53.01,"lng":23.13,"typ":"gmina","sieci":2},{"n":"Dobrzyniewo Duże","lat":53.19930,"lng":23.01080,"typ":"gmina","sieci":2},{"n":"Turośń Kościelna","lat":53.01509,"lng":23.05491,"typ":"gmina","sieci":2},{"n":"Suraż","lat":52.95,"lng":22.95,"typ":"gmina","sieci":1},{"n":"Narew","lat":52.91,"lng":23.52,"typ":"gmina","sieci":2},{"n":"Narewka","lat":52.83,"lng":23.76,"typ":"gmina","sieci":2},{"n":"Czyże","lat":52.78,"lng":23.42,"typ":"gmina","sieci":1},{"n":"Krynki","lat":53.26,"lng":23.77,"typ":"gmina","sieci":2},{"n":"Janów","lat":53.47,"lng":23.22,"typ":"gmina","sieci":2},{"n":"Dąbrowa Białost.","lat":53.65,"lng":23.35,"typ":"gmina","sieci":2},{"n":"Suchowola","lat":53.58,"lng":23.10,"typ":"gmina","sieci":2},{"n":"Korycin","lat":53.44,"lng":23.15,"typ":"gmina","sieci":2},{"n":"Jaświły","lat":53.48013,"lng":22.94809,"typ":"gmina","sieci":1},{"n":"Knyszyn","lat":53.31,"lng":22.92,"typ":"gmina","sieci":2},{"n":"Trzcianne","lat":53.34376,"lng":22.68158,"typ":"gmina","sieci":1},{"n":"Mońki","lat":53.40,"lng":22.79,"typ":"gmina","sieci":3},{"n":"Goniądz","lat":53.48,"lng":22.73,"typ":"gmina","sieci":2},{"n":"Krypno","lat":53.27,"lng":22.87,"typ":"gmina","sieci":1},{"n":"Sokółka","lat":53.40,"lng":23.49,"typ":"gmina","sieci":4},{"n":"Szudziałowo","lat":53.29,"lng":23.65,"typ":"gmina","sieci":1},{"n":"Kuznica","lat":53.50,"lng":23.64,"typ":"gmina","sieci":1},{"n":"Sidra","lat":53.54,"lng":23.46,"typ":"gmina","sieci":1},{"n":"Lipsk","lat":53.73,"lng":23.39,"typ":"gmina","sieci":2},{"n":"Sztabin","lat":53.68090,"lng":23.09802,"typ":"gmina","sieci":1},{"n":"Augustów","lat":53.84,"lng":22.97,"typ":"gmina","sieci":4},{"n":"Bargłów Kośc.","lat":53.76,"lng":22.82,"typ":"gmina","sieci":1},{"n":"Grajewo","lat":53.64,"lng":22.45,"typ":"gmina","sieci":4},{"n":"Szczuczyn","lat":53.56,"lng":22.28,"typ":"gmina","sieci":2},{"n":"Wąsosz","lat":53.52,"lng":22.31,"typ":"gmina","sieci":1},{"n":"Radziłów","lat":53.40975,"lng":22.40982,"typ":"gmina","sieci":1},{"n":"Zawady","lat":53.15,"lng":22.66,"typ":"gmina","sieci":1},{"n":"Kobylin-Borzymy","lat":53.10,"lng":22.66,"typ":"gmina","sieci":1},{"n":"Czarna Białostocka","lat":53.3,"lng":23.29,"typ":"gmina","sieci":2},{"n":"Turośń","lat":52.98,"lng":23.05,"typ":"gmina","sieci":1},{"n":"Juchnowiec","lat":53.06,"lng":23.24,"typ":"gmina","sieci":2},{"n":"Sokoły","lat":52.98,"lng":22.68,"typ":"gmina","sieci":1},{"n":"Wysokie Maz.","lat":52.92,"lng":22.51,"typ":"gmina","sieci":3},{"n":"Czyżew","lat":52.8,"lng":22.3,"typ":"gmina","sieci":2},{"n":"Szepietowo","lat":52.86,"lng":22.55,"typ":"gmina","sieci":2},{"n":"Ciechanowiec","lat":52.68,"lng":22.5,"typ":"gmina","sieci":2},{"n":"Brańsk","lat":52.74,"lng":22.84,"typ":"gmina","sieci":2},{"n":"Rajgród","lat":53.73,"lng":22.7,"typ":"gmina","sieci":1},{"n":"Dąbrowa Biał.","lat":53.65,"lng":23.35,"typ":"gmina","sieci":1},{"n":"Kuźnica","lat":53.51,"lng":23.65,"typ":"gmina","sieci":1},{"n":"Gródek","lat":53.1,"lng":23.66,"typ":"gmina","sieci":1},{"n":"Bielsk Podl.","lat":52.77,"lng":23.19,"typ":"gmina","sieci":3},{"n":"Boćki","lat":52.66,"lng":23.04,"typ":"gmina","sieci":1},{"n":"Orla","lat":52.71,"lng":23.33,"typ":"gmina","sieci":1},{"n":"Kleszczele","lat":52.58,"lng":23.32,"typ":"gmina","sieci":1},{"n":"Hajnówka","lat":52.74,"lng":23.58,"typ":"gmina","sieci":3},{"n":"Siemiatycze","lat":52.43,"lng":22.86,"typ":"gmina","sieci":3},{"n":"Drohiczyn","lat":52.4,"lng":22.66,"typ":"gmina","sieci":1},{"n":"Mielnik","lat":52.33,"lng":23.05,"typ":"gmina","sieci":1},{"n":"Nurzec","lat":52.44,"lng":23.06,"typ":"gmina","sieci":1},{"n":"Milejczyce","lat":52.53,"lng":23.13,"typ":"gmina","sieci":1},{"n":"Dziadkowice","lat":52.55,"lng":22.9,"typ":"gmina","sieci":1},{"n":"Grodzisk","lat":52.62,"lng":22.75,"typ":"gmina","sieci":1}],
  "warmińsko-mazurskie": [{"n":"Barczewo","lat":53.82,"lng":20.69,"typ":"gmina","sieci":2},{"n":"Dobre Miasto","lat":53.98,"lng":20.39,"typ":"gmina","sieci":3},{"n":"Olsztynek","lat":53.58,"lng":20.28,"typ":"gmina","sieci":3},{"n":"Biskupiec","lat":53.86,"lng":20.95,"typ":"gmina","sieci":3},{"n":"Jeziorany","lat":53.97,"lng":20.74,"typ":"gmina","sieci":2},{"n":"Pasym","lat":53.65015,"lng":20.79148,"typ":"gmina","sieci":2},{"n":"Stawiguda","lat":53.66,"lng":20.39,"typ":"gmina","sieci":2},{"n":"Jonkowo","lat":53.83,"lng":20.31,"typ":"gmina","sieci":2},{"n":"Purda","lat":53.71,"lng":20.70,"typ":"gmina","sieci":2},{"n":"Morąg","lat":53.91,"lng":19.92,"typ":"gmina","sieci":3},{"n":"Gietrzwałd","lat":53.73,"lng":20.23,"typ":"gmina","sieci":2},{"n":"Dywity","lat":53.83,"lng":20.47,"typ":"gmina","sieci":2},{"n":"Świątki","lat":53.92,"lng":20.24,"typ":"gmina","sieci":2},{"n":"Lubomino","lat":54.06,"lng":20.24,"typ":"gmina","sieci":1},{"n":"Miłakowo","lat":54.00,"lng":20.07,"typ":"gmina","sieci":2},{"n":"Małdyty","lat":53.92,"lng":19.74,"typ":"gmina","sieci":2},{"n":"Miłomłyn","lat":53.76,"lng":19.84,"typ":"gmina","sieci":2},{"n":"Łukta","lat":53.80,"lng":20.08,"typ":"gmina","sieci":2},{"n":"Grunwald","lat":53.48,"lng":20.12,"typ":"gmina","sieci":1},{"n":"Kozłowo","lat":53.30,"lng":20.30,"typ":"gmina","sieci":1},{"n":"Janowiec Kośc.","lat":53.28,"lng":20.52,"typ":"gmina","sieci":1},{"n":"Jedwabno","lat":53.52871,"lng":20.72616,"typ":"gmina","sieci":2},{"n":"Dźwierzuty","lat":53.70,"lng":20.95,"typ":"gmina","sieci":2},{"n":"Działdowo","lat":53.23,"lng":20.18,"typ":"gmina","sieci":4},{"n":"Iłowo-Osada","lat":53.16,"lng":20.29,"typ":"gmina","sieci":2},{"n":"Nidzica","lat":53.36,"lng":20.42,"typ":"gmina","sieci":3},{"n":"Rybno","lat":53.38,"lng":19.98,"typ":"gmina","sieci":2},{"n":"Lidzbark","lat":53.26,"lng":19.82,"typ":"gmina","sieci":3},{"n":"Płośnica","lat":53.27256,"lng":20.01003,"typ":"gmina","sieci":1},{"n":"Kurzętnik","lat":53.39,"lng":19.58,"typ":"gmina","sieci":2},{"n":"Biskupiec Pom.","lat":53.48,"lng":19.33,"typ":"gmina","sieci":2},{"n":"Iława","lat":53.59,"lng":19.56,"typ":"gmina","sieci":4},{"n":"Kisielice","lat":53.60,"lng":19.26,"typ":"gmina","sieci":2},{"n":"Susz","lat":53.72,"lng":19.34,"typ":"gmina","sieci":2},{"n":"Zalewo","lat":53.84,"lng":19.60,"typ":"gmina","sieci":2},{"n":"Lubawa","lat":53.50271,"lng":19.74978,"typ":"gmina","sieci":3},{"n":"Nowe Miasto L.","lat":53.42,"lng":19.59,"typ":"gmina","sieci":3},{"n":"Grodziczno","lat":53.41440,"lng":19.76603,"typ":"gmina","sieci":1},{"n":"Kolno","lat":53.99699,"lng":20.99457,"typ":"gmina","sieci":1},{"n":"Reszel","lat":54.05,"lng":21.15,"typ":"gmina","sieci":2},{"n":"Bisztynek","lat":54.09,"lng":20.9,"typ":"gmina","sieci":2},{"n":"Lidzbark W.","lat":54.13,"lng":20.58,"typ":"gmina","sieci":3},{"n":"Orneta","lat":54.12,"lng":20.13,"typ":"gmina","sieci":2},{"n":"Ostróda","lat":53.7,"lng":19.97,"typ":"gmina","sieci":3},{"n":"Dąbrówno","lat":53.42,"lng":20.03,"typ":"gmina","sieci":1},{"n":"Janowo","lat":53.3,"lng":20.51,"typ":"gmina","sieci":1},{"n":"Pasłęk","lat":54.06,"lng":19.66,"typ":"gmina","sieci":2},{"n":"Młynary","lat":54.18,"lng":19.75,"typ":"gmina","sieci":1},{"n":"Godkowo","lat":54.07974,"lng":19.90426,"typ":"gmina","sieci":1},{"n":"Elbląg","lat":54.16,"lng":19.4,"typ":"gmina","sieci":4},{"n":"Tolkmicko","lat":54.32,"lng":19.53,"typ":"gmina","sieci":1},{"n":"Frombork","lat":54.36,"lng":19.68,"typ":"gmina","sieci":1},{"n":"Braniewo","lat":54.38,"lng":19.82,"typ":"gmina","sieci":3},{"n":"Pieniężno","lat":54.24,"lng":20.13,"typ":"gmina","sieci":1},{"n":"Górowo Iław.","lat":54.28,"lng":20.49,"typ":"gmina","sieci":1},{"n":"Bartoszyce","lat":54.25,"lng":20.81,"typ":"gmina","sieci":3},{"n":"Sępopol","lat":54.26808,"lng":21.01493,"typ":"gmina","sieci":1},{"n":"Korsze","lat":54.17,"lng":21.15,"typ":"gmina","sieci":1},{"n":"Kętrzyn","lat":54.08,"lng":21.38,"typ":"gmina","sieci":3},{"n":"Mrągowo","lat":53.87,"lng":21.3,"typ":"gmina","sieci":3}],
  "opolskie": [{"n":"Ozimek","lat":50.67,"lng":18.21,"typ":"gmina","sieci":3},{"n":"Gogolin","lat":50.48,"lng":18.02,"typ":"gmina","sieci":2},{"n":"Zdzieszowice","lat":50.42,"lng":18.12,"typ":"gmina","sieci":2},{"n":"Grodków","lat":50.69850,"lng":17.38519,"typ":"gmina","sieci":3},{"n":"Prószków","lat":50.57,"lng":17.87,"typ":"gmina","sieci":2},{"n":"Niemodlin","lat":50.64,"lng":17.62,"typ":"gmina","sieci":2},{"n":"Dobrzeń Wielki","lat":50.75,"lng":17.84,"typ":"gmina","sieci":2},{"n":"Komprachcice","lat":50.63,"lng":17.81,"typ":"gmina","sieci":2},{"n":"Tarnów Opolski","lat":50.57,"lng":18.08,"typ":"gmina","sieci":2},{"n":"Chrząstowice","lat":50.66,"lng":18.08,"typ":"gmina","sieci":2},{"n":"Turawa","lat":50.73,"lng":18.08,"typ":"gmina","sieci":2},{"n":"Murów","lat":50.86,"lng":17.93,"typ":"gmina","sieci":2},{"n":"Łubniany","lat":50.77881,"lng":17.99866,"typ":"gmina","sieci":2},{"n":"Popielów","lat":50.82,"lng":17.74,"typ":"gmina","sieci":2},{"n":"Pokój","lat":50.90,"lng":17.83,"typ":"gmina","sieci":2},{"n":"Lewin Brzeski","lat":50.75,"lng":17.61,"typ":"gmina","sieci":2},{"n":"Tułowice","lat":50.59,"lng":17.65,"typ":"gmina","sieci":2},{"n":"Zawadzkie","lat":50.61,"lng":18.47,"typ":"gmina","sieci":3},{"n":"Ujazd","lat":50.39,"lng":18.35,"typ":"gmina","sieci":2},{"n":"Krapkowice","lat":50.47,"lng":17.96,"typ":"gmina","sieci":3},{"n":"Głuchołazy","lat":50.31,"lng":17.38,"typ":"gmina","sieci":3},{"n":"Biała","lat":50.38,"lng":17.66,"typ":"gmina","sieci":2},{"n":"Strzeleczki","lat":50.46,"lng":17.86,"typ":"gmina","sieci":1},{"n":"Walce","lat":50.37185,"lng":18.00832,"typ":"gmina","sieci":1},{"n":"Głogówek","lat":50.35,"lng":17.86,"typ":"gmina","sieci":2},{"n":"Otmuchów","lat":50.46621,"lng":17.17540,"typ":"gmina","sieci":2},{"n":"Paczków","lat":50.46,"lng":17.00,"typ":"gmina","sieci":2},{"n":"Kamiennik","lat":50.57039,"lng":17.14932,"typ":"gmina","sieci":1},{"n":"Lubsza","lat":50.91617,"lng":17.52187,"typ":"gmina","sieci":1},{"n":"Skarbimierz","lat":50.84806,"lng":17.43556,"typ":"gmina","sieci":1},{"n":"Namysłów","lat":51.07,"lng":17.71,"typ":"gmina","sieci":4},{"n":"Wilków","lat":51.01,"lng":17.65,"typ":"gmina","sieci":1},{"n":"Domaszowice","lat":51.04247,"lng":17.88858,"typ":"gmina","sieci":1},{"n":"Kluczbork","lat":50.97,"lng":18.21,"typ":"gmina","sieci":4},{"n":"Wołczyn","lat":51.01,"lng":18.05,"typ":"gmina","sieci":2},{"n":"Byczyna","lat":51.11,"lng":18.21,"typ":"gmina","sieci":2},{"n":"Gorzów Śl.","lat":51.02816,"lng":18.42233,"typ":"gmina","sieci":2},{"n":"Praszka","lat":51.05377,"lng":18.45313,"typ":"gmina","sieci":2},{"n":"Olesno","lat":50.87,"lng":18.42,"typ":"gmina","sieci":3},{"n":"Dobrzeń Wlk.","lat":50.75,"lng":17.86,"typ":"gmina","sieci":2},{"n":"Kolonowskie","lat":50.65323,"lng":18.38424,"typ":"gmina","sieci":1},{"n":"Dobrodzień","lat":50.72,"lng":18.44,"typ":"gmina","sieci":2},{"n":"Lubrza","lat":50.33554,"lng":17.62604,"typ":"gmina","sieci":1},{"n":"Prudnik","lat":50.32,"lng":17.58,"typ":"gmina","sieci":4},{"n":"Nysa okolice","lat":50.47,"lng":17.33,"typ":"gmina","sieci":3},{"n":"Lasowice Wielkie","lat":50.87087,"lng":18.22079,"typ":"gmina","sieci":1},{"n":"Rudniki","lat":51.03894,"lng":18.59817,"typ":"gmina","sieci":1},{"n":"Świerczów","lat":50.96028,"lng":17.76100,"typ":"gmina","sieci":1},{"n":"Namysłów ok.","lat":51.05,"lng":17.75,"typ":"gmina","sieci":1},{"n":"Brzeg","lat":50.86,"lng":17.47,"typ":"gmina","sieci":3},{"n":"Lewin Brz.","lat":50.75,"lng":17.61,"typ":"gmina","sieci":1},{"n":"Skoroszyce","lat":50.59748,"lng":17.38247,"typ":"gmina","sieci":1},{"n":"Pakosławice","lat":50.54547,"lng":17.36185,"typ":"gmina","sieci":1},{"n":"Nysa","lat":50.47,"lng":17.33,"typ":"gmina","sieci":3},{"n":"Korfantów","lat":50.48623,"lng":17.59771,"typ":"gmina","sieci":1},{"n":"Łambinowice","lat":50.53846,"lng":17.55988,"typ":"gmina","sieci":1}],
  "lubuskie": [{"n":"Sulechów","lat":52.08,"lng":15.62,"typ":"gmina","sieci":4},{"n":"Czerwieńsk","lat":52.01,"lng":15.42,"typ":"gmina","sieci":2},{"n":"Nowogród Bobrz.","lat":51.79,"lng":15.23,"typ":"gmina","sieci":2},{"n":"Kargowa","lat":52.07197,"lng":15.86517,"typ":"gmina","sieci":2},{"n":"Babimost","lat":52.16,"lng":15.82,"typ":"gmina","sieci":2},{"n":"Zbąszynek","lat":52.24,"lng":15.81,"typ":"gmina","sieci":2},{"n":"Rzepin","lat":52.34,"lng":14.83,"typ":"gmina","sieci":3},{"n":"Skwierzyna","lat":52.59,"lng":15.50,"typ":"gmina","sieci":3},{"n":"Ośno Lubuskie","lat":52.45,"lng":14.87,"typ":"gmina","sieci":2},{"n":"Cybinka","lat":52.19,"lng":14.79,"typ":"gmina","sieci":2},{"n":"Torzym","lat":52.31,"lng":15.08,"typ":"gmina","sieci":2},{"n":"Lubniewice","lat":52.51,"lng":15.24,"typ":"gmina","sieci":2},{"n":"Krzeszyce","lat":52.58308,"lng":15.00722,"typ":"gmina","sieci":2},{"n":"Bytnica","lat":52.14,"lng":15.16,"typ":"gmina","sieci":1},{"n":"Trzebiechów","lat":52.02,"lng":15.73,"typ":"gmina","sieci":2},{"n":"Bojadła","lat":51.95,"lng":15.81,"typ":"gmina","sieci":1},{"n":"Świdnica","lat":51.88,"lng":15.39,"typ":"gmina","sieci":2},{"n":"Zabór","lat":51.95,"lng":15.71,"typ":"gmina","sieci":1},{"n":"Sława","lat":51.87,"lng":16.08,"typ":"gmina","sieci":3},{"n":"Wschowa","lat":51.80,"lng":16.31,"typ":"gmina","sieci":4},{"n":"Szlichtyngowa","lat":51.71,"lng":16.24,"typ":"gmina","sieci":2},{"n":"Kolsko","lat":51.96147,"lng":15.96482,"typ":"gmina","sieci":1},{"n":"Trzciel","lat":52.37,"lng":15.88,"typ":"gmina","sieci":2},{"n":"Bledzew","lat":52.51,"lng":15.41,"typ":"gmina","sieci":1},{"n":"Deszczno","lat":52.67,"lng":15.32,"typ":"gmina","sieci":2},{"n":"Santok","lat":52.73,"lng":15.40,"typ":"gmina","sieci":2},{"n":"Bogdaniec","lat":52.68888,"lng":15.07066,"typ":"gmina","sieci":2},{"n":"Lubiszyn","lat":52.77981,"lng":14.94786,"typ":"gmina","sieci":1},{"n":"Witnica","lat":52.67,"lng":14.90,"typ":"gmina","sieci":2},{"n":"Kostrzyn n. Odrą","lat":52.58,"lng":14.66,"typ":"gmina","sieci":4},{"n":"Górzyca","lat":52.49439,"lng":14.65485,"typ":"gmina","sieci":2},{"n":"Słońsk","lat":52.56353,"lng":14.80564,"typ":"gmina","sieci":2},{"n":"Nowa Sól","lat":51.80,"lng":15.71,"typ":"gmina","sieci":5},{"n":"Otyń","lat":51.84,"lng":15.71,"typ":"gmina","sieci":2},{"n":"Kozuchów","lat":51.76,"lng":15.53,"typ":"gmina","sieci":3},{"n":"Brodce","lat":51.64,"lng":15.33,"typ":"gmina","sieci":2},{"n":"Lubsko","lat":51.79,"lng":14.97,"typ":"gmina","sieci":3},{"n":"Tuplice","lat":51.67438,"lng":14.83215,"typ":"gmina","sieci":1},{"n":"Żary","lat":51.64,"lng":15.13,"typ":"gmina","sieci":5},{"n":"Jasień","lat":51.75,"lng":15.01,"typ":"gmina","sieci":2},{"n":"Międzyrzecz","lat":52.44,"lng":15.58,"typ":"gmina","sieci":3},{"n":"Przytoczna","lat":52.57739,"lng":15.67963,"typ":"gmina","sieci":1},{"n":"Kłodawa","lat":52.78935,"lng":15.21317,"typ":"gmina","sieci":1},{"n":"Sulęcin","lat":52.44,"lng":15.12,"typ":"gmina","sieci":2},{"n":"Zielona Góra ok.","lat":51.94,"lng":15.51,"typ":"gmina","sieci":3},{"n":"Nowogród Bob.","lat":51.79,"lng":15.24,"typ":"gmina","sieci":1},{"n":"Żagań","lat":51.62,"lng":15.32,"typ":"gmina","sieci":3},{"n":"Iłowa","lat":51.5,"lng":15.21,"typ":"gmina","sieci":1},{"n":"Gozdnica","lat":51.44,"lng":15.1,"typ":"gmina","sieci":1},{"n":"Wymiarki","lat":51.51000,"lng":15.08201,"typ":"gmina","sieci":1},{"n":"Szprotawa","lat":51.56,"lng":15.54,"typ":"gmina","sieci":2},{"n":"Małomice","lat":51.57,"lng":15.44,"typ":"gmina","sieci":1},{"n":"Niegosławice","lat":51.58858,"lng":15.71749,"typ":"gmina","sieci":1},{"n":"Kożuchów","lat":51.75,"lng":15.59,"typ":"gmina","sieci":2},{"n":"Bytom Odrz.","lat":51.73,"lng":15.83,"typ":"gmina","sieci":1},{"n":"Nowe Miasteczko","lat":51.68,"lng":15.72,"typ":"gmina","sieci":1},{"n":"Krosno Odrz.","lat":52.05,"lng":15.09,"typ":"gmina","sieci":2},{"n":"Gubin","lat":51.95,"lng":14.72,"typ":"gmina","sieci":2},{"n":"Brody","lat":51.79,"lng":14.77,"typ":"gmina","sieci":1},{"n":"Łęknica","lat":51.55,"lng":14.74,"typ":"gmina","sieci":1},{"n":"Trzebiel","lat":51.63,"lng":14.82,"typ":"gmina","sieci":1},{"n":"Przewóz","lat":51.48,"lng":14.94,"typ":"gmina","sieci":1}]
}

@dataclass
class Miasto:
    n: str
    lat: float
    lng: float
    typ: str
    sieci: int
    woj: str = ""
    sektor: str = ""

@dataclass
class RawEtap:
    skad: str
    dokad: str
    data_str: str
    d_line: float
    czas_w_sklepie: float
    dokad_woj: str
    skad_lat: float
    skad_lng: float
    dokad_lat: float
    dokad_lng: float
    kwota: float = 0.0
    czas_jazdy_minuty: float = 0.0
    # odległość w linii prostej — zapamiętana, zanim d_line stanie się
    # odległością DROGOWĄ; to ona jest fizyczną granicą dolną odcinka
    linia_prosta: float = 0.0
    # skąd wzięły się kilometry TEGO odcinka: ZRODLO_DROGI / ZRODLO_PAMIEC /
    # ZRODLO_SZACUNEK („" = jeszcze nie liczono). Licznik stan_zrodla_odleglosci
    # mówi o całym rozliczeniu; to pole o jednym odcinku — druga strona
    # kartki delegacji pokazuje je przy każdym odcinku dnia.
    zrodlo: str = ""

@dataclass
class Etap:
    skad: str
    dokad: str
    data: str
    godz_wyj: str
    godz_przyj: str
    kwota: float
    dokad_woj: str = ""

@dataclass
class DzienTrasy:
    data: datetime.date
    etapy_surowe: List[RawEtap] = field(default_factory=list)
    etapy: List[Etap] = field(default_factory=list)
    # numer polecenia wyjazdu, do którego trafia ten dzień (0 = jeszcze nieznany)
    dokument: int = 0

    @property
    def suma(self) -> float:
        return sum(e.kwota for e in self.etapy)

@dataclass
class DanePracownika:
    imie: str
    pesel: str
    adres: str
    stanowisko: str
    kod_pocztowy: str
    baza_miasto: str
    baza_lat: float = 52.23
    baza_lng: float = 21.01
    wojewodztwo: str = "mazowieckie"

_baza_miast: Dict[str, List[Miasto]] = {}

def oblicz_dystans(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

ZRODLO_DROGI = "drogi"          # policzone teraz po drogach (Google albo OSRM)

ZRODLO_PAMIEC = "pamiec"        # z pamięci podręcznej (kiedyś policzone po drogach)

ZRODLO_SZACUNEK = "szacunek"    # linia prosta × krętość — brak sieci albo błąd

ZRODLO_BRAK = "brak"            # ani jednego policzonego odcinka — nic nie zapewniamy

ETYKIETY_ZRODLA = {
    ZRODLO_DROGI: "realne drogi",
    ZRODLO_PAMIEC: "drogi z pamięci",
    ZRODLO_SZACUNEK: "szacunek",
    ZRODLO_BRAK: "",            # pusta etykieta = dokument i interfejs milczą
}

ROAD_CACHE_FILE = os.path.join(os.path.expanduser("~"), ".pmt_road_cache.json")

_road_cache = {}

_osrm_dostepny = None    # None=niesprawdzone, True/False po pierwszej próbie

_google_dostepny = None  # jak wyżej, dla Google (gdy klucz w ogóle jest)

_zrodlo_licznik = {ZRODLO_DROGI: 0, ZRODLO_PAMIEC: 0, ZRODLO_SZACUNEK: 0}

_ostatnie_zrodlo = ZRODLO_BRAK      # źródło OSTATNIO policzonego odcinka

def _klucz_drogi(lat1, lon1, lat2, lon2) -> str:
    """Klucz pamięci podręcznej WSPÓLNY DLA OBU KIERUNKÓW. Droga A→B i B→A to
    ta sama droga, a dotąd każdy kierunek zajmował osobny wpis i osobne
    zapytanie do sieci — dzień jadący pętlę w drugą stronę liczył wszystko
    jeszcze raz."""
    a = "%.4f,%.4f" % (lat1, lon1)
    b = "%.4f,%.4f" % (lat2, lon2)
    return ("%s;%s" % (a, b)) if a <= b else ("%s;%s" % (b, a))

def _oczysc_road_cache(surowe) -> dict:
    """Z wczytanego pliku zostaje tylko to, czego da się użyć: klucz w postaci
    „lat,lng;lat,lng" i dodatnia liczba kilometrów. Stare klucze kierunkowe
    sprowadzamy do klucza wspólnego dla obu kierunków."""
    czysty = {}
    if not isinstance(surowe, dict):
        return czysty
    for klucz, wartosc in surowe.items():
        try:
            km = float(wartosc)
        except (TypeError, ValueError):
            continue
        if not (0 < km < 1e6):          # odsiewa też NaN i nieskończoność
            continue
        try:
            a, b = str(klucz).split(";")
            la1, lg1 = [float(x) for x in a.split(",")]
            la2, lg2 = [float(x) for x in b.split(",")]
        except Exception:
            continue
        k = _klucz_drogi(la1, lg1, la2, lg2)
        if k not in czysty or km < czysty[k]:
            czysty[k] = round(km, 2)
    return czysty

def _zapisz_road_cache(sciezka=None):
    """Zapis atomowy: plik tymczasowy → podmiana, poprzedni ląduje w .bak.
    Pad w trakcie zapisu nie zostawia uciętego pliku bez kopii."""
    sciezka = sciezka or ROAD_CACHE_FILE
    try:
        tmp = sciezka + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_road_cache, f)
        try:
            if os.path.exists(sciezka):
                os.replace(sciezka, sciezka + ".bak")
        except Exception:
            pass
        os.replace(tmp, sciezka)
    except Exception:
        pass

def _wczytaj_road_cache(sciezka=None):
    """Pamięć podręczna przeżywa zamknięcie programu. Uszkodzony plik (pad
    w trakcie zapisu, ręczna edycja, obcy plik) nie może wywrócić programu:
    sięgamy wtedy po kopię .bak, a gdy i ona jest zła — zaczynamy od pustej."""
    global _road_cache
    sciezka = sciezka or ROAD_CACHE_FILE
    _road_cache = {}
    for plik, z_baku in ((sciezka, False), (sciezka + ".bak", True)):
        try:
            if not os.path.exists(plik):
                continue
            with open(plik, "r", encoding="utf-8") as f:
                dane = json.load(f)
        except Exception:
            continue
        czysty = _oczysc_road_cache(dane)
        if czysty:
            _road_cache = czysty
            if z_baku:
                _zapisz_road_cache(sciezka)
            break
        if isinstance(dane, dict):
            break               # plik poprawny, tylko pusty
    return _road_cache

_wczytaj_road_cache()

def zeruj_zrodlo_odleglosci():
    """Nowe rozliczenie = nowy licznik źródeł."""
    for k in list(_zrodlo_licznik):
        _zrodlo_licznik[k] = 0

def _odnotuj_zrodlo(rodzaj):
    global _ostatnie_zrodlo
    _zrodlo_licznik[rodzaj] = _zrodlo_licznik.get(rodzaj, 0) + 1
    _ostatnie_zrodlo = rodzaj

def zrodlo_ostatniego_odcinka() -> str:
    """Skąd wzięła się liczba z OSTATNIEGO wywołania dystans_drogowy —
    do zapisania w RawEtap.zrodlo zaraz po policzeniu odcinka."""
    return _ostatnie_zrodlo

def uzupelnij_zrodla_etapow(etapy) -> int:
    """Odcinki bez zapisanego źródła (dobudowane po przycinaniu, pętla
    odwrócona) dostają je z pamięci dróg: odcinek, którego droga leży w
    pamięci podręcznej, liczył się z niej (ZRODLO_PAMIEC); reszta to linia
    prosta × krętość (ZRODLO_SZACUNEK). Zwraca liczbę uzupełnionych."""
    ile = 0
    for e in etapy:
        if getattr(e, "zrodlo", ""):
            continue
        try:
            w_pamieci = bool(_road_cache.get(
                _klucz_drogi(e.skad_lat, e.skad_lng, e.dokad_lat, e.dokad_lng)))
        except Exception:
            w_pamieci = False
        e.zrodlo = ZRODLO_PAMIEC if w_pamieci else ZRODLO_SZACUNEK
        ile += 1
    return ile

def stan_zrodla_odleglosci() -> dict:
    """Stan źródła odległości dla CAŁEGO rozliczenia. Wystarczy jeden odcinek
    policzony szacunkiem, żeby stanem całości był szacunek — bo to on
    rozstrzyga o wiarygodności sumy kilometrów.

    Zero policzonych odcinków to osobny stan ZRODLO_BRAK z pustą etykietą:
    dotąd wychodziło stąd „realne drogi" i realne=True — zapewnienie bez ani
    jednego pomiaru, drukowane potem na dokumencie."""
    ile = dict(_zrodlo_licznik)
    if ile.get(ZRODLO_SZACUNEK):
        stan = ZRODLO_SZACUNEK
    elif ile.get(ZRODLO_DROGI):
        stan = ZRODLO_DROGI
    elif ile.get(ZRODLO_PAMIEC):
        stan = ZRODLO_PAMIEC
    else:
        stan = ZRODLO_BRAK
    return {
        ZRODLO_DROGI: ile.get(ZRODLO_DROGI, 0),
        ZRODLO_PAMIEC: ile.get(ZRODLO_PAMIEC, 0),
        ZRODLO_SZACUNEK: ile.get(ZRODLO_SZACUNEK, 0),
        "stan": stan,
        "etykieta": ETYKIETY_ZRODLA[stan],
        "odcinki": sum(ile.values()),
        "realne": stan in (ZRODLO_DROGI, ZRODLO_PAMIEC),
    }

def etykieta_zrodla_odleglosci() -> str:
    """Krótka etykieta do interfejsu: „realne drogi" / „drogi z pamięci" /
    „szacunek"."""
    return stan_zrodla_odleglosci()["etykieta"]

GOOGLE_KLUCZ_ENV = "PMT_GOOGLE_KLUCZ"

GOOGLE_KLUCZ_ENV_ALT = "GOOGLE_MAPS_API_KEY"

GOOGLE_KLUCZ_USTAWIENIE = "google_klucz"

def google_klucz() -> str:
    """Klucz ze zmiennej środowiskowej (pierwszeństwo) albo z ustawień.
    Pusty napis = brak klucza = źródło bezpłatne."""
    for zmienna in (GOOGLE_KLUCZ_ENV, GOOGLE_KLUCZ_ENV_ALT):
        k = (os.environ.get(zmienna) or "").strip()
        if k:
            return k
    try:
        return str(ustawienie(GOOGLE_KLUCZ_USTAWIENIE, "") or "").strip()
    except Exception:
        return ""

def _google_km(lat1, lon1, lat2, lon2, klucz):
    """Odległość drogowa z Google Distance Matrix. Zwraca km albo None."""
    url = ("https://maps.googleapis.com/maps/api/distancematrix/json"
           "?origins=%.6f,%.6f&destinations=%.6f,%.6f"
           "&mode=driving&units=metric&key=%s"
           % (lat1, lon1, lat2, lon2, urllib.parse.quote(klucz, safe="")))
    req = urllib.request.Request(url, headers={"User-Agent": "PMT-Delegacje/1.0"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        dane = json.loads(resp.read().decode("utf-8"))
    if dane.get("status") != "OK":
        return None
    wiersze = dane.get("rows") or []
    elementy = (wiersze[0].get("elements") or []) if wiersze else []
    el = elementy[0] if elementy else {}
    if el.get("status") != "OK":
        return None
    metry = (el.get("distance") or {}).get("value")
    return (float(metry) / 1000.0) if metry else None

def _osrm_km(lat1, lon1, lat2, lon2):
    """Odległość drogowa z publicznego OSRM. Zwraca km albo None."""
    url = (f"https://router.project-osrm.org/route/v1/driving/"
           f"{lon1},{lat1};{lon2},{lat2}?overview=false")
    req = urllib.request.Request(url, headers={"User-Agent": "PMT-Delegacje/1.0"})
    with urllib.request.urlopen(req, timeout=4) as resp:
        dane = json.loads(resp.read().decode("utf-8"))
    if dane.get("code") == "Ok" and dane.get("routes"):
        return dane["routes"][0]["distance"] / 1000.0
    return None

def dystans_drogowy(lat1, lon1, lat2, lon2, tylko_cache=False) -> float:
    """Realna odległość DROGOWA w km (nie w linii prostej).
    Kolejność źródeł: pamięć podręczna → Google (tylko gdy jest klucz) →
    OSRM → szacunek. Każde wywołanie odnotowuje, skąd wzięła się liczba;
    stan całego rozliczenia czyta stan_zrodla_odleglosci()."""
    global _osrm_dostepny, _google_dostepny
    klucz = _klucz_drogi(lat1, lon1, lat2, lon2)
    zapamietane = _road_cache.get(klucz)
    if zapamietane:
        _odnotuj_zrodlo(ZRODLO_PAMIEC)
        return zapamietane
    if not tylko_cache:
        g_klucz = google_klucz() if _google_dostepny is not False else ""
        if g_klucz:
            try:
                km = _google_km(lat1, lon1, lat2, lon2, g_klucz)
                if km and km > 0:
                    _google_dostepny = True
                    _road_cache[klucz] = round(km, 2)
                    _odnotuj_zrodlo(ZRODLO_DROGI)
                    return _road_cache[klucz]
            except Exception:
                # brak odpowiedzi Google (sieć, limit, zły klucz) → OSRM.
                # Zapamiętujemy to, żeby nie czekać na timeout przy każdym
                # kolejnym odcinku miesiąca.
                _google_dostepny = False
        if _osrm_dostepny is not False:
            try:
                km = _osrm_km(lat1, lon1, lat2, lon2)
                if km and km > 0:
                    _osrm_dostepny = True
                    _road_cache[klucz] = round(km, 2)
                    _odnotuj_zrodlo(ZRODLO_DROGI)
                    return _road_cache[klucz]
            except Exception:
                _osrm_dostepny = False
    _odnotuj_zrodlo(ZRODLO_SZACUNEK)
    return oblicz_dystans(lat1, lon1, lat2, lon2) * TEST_MNOZNIK_TRASY

def dystans_odcinek_punkt(lat1, lon1, lat2, lon2, p_lat, p_lon):
    kx = 111.0 * math.cos(math.radians((lat1+lat2)/2.0))
    ky = 111.0
    x1, y1 = lon1 * kx, lat1 * ky
    x2, y2 = lon2 * kx, lat2 * ky
    px, py = p_lon * kx, p_lat * ky

    l2 = (x2 - x1)**2 + (y2 - y1)**2
    if l2 == 0: return math.sqrt((px - x1)**2 + (py - y1)**2)
    t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2))
    return math.sqrt((px - (x1 + t * (x2 - x1)))**2 + (py - (y1 + t * (y2 - y1)))**2)

def wyznacz_sektor(lat_cel, lng_cel, lat_baza, lng_baza) -> str:
    kat = math.degrees(math.atan2(lng_cel - lng_baza, lat_cel - lat_baza)) % 360
    if kat < 22.5 or kat >= 337.5: return "N"
    elif kat < 67.5: return "NE"
    elif kat < 112.5: return "E"
    elif kat < 157.5: return "SE"
    elif kat < 202.5: return "S"
    elif kat < 247.5: return "SW"
    elif kat < 292.5: return "W"
    else: return "NW"

def odsuwa_sie_od_stolicy(baza_lat, baza_lng, m_lat, m_lng, woj):
    if woj not in STOLICE: return True
    w_lat, w_lng = STOLICE[woj]
    d_baza = oblicz_dystans(baza_lat, baza_lng, w_lat, w_lng)
    if d_baza < 20.0: return True
    d_cel = oblicz_dystans(m_lat, m_lng, w_lat, w_lng)
    if d_cel <= d_baza: return False  
    return True

def pobierz_zablokowane_sektory(baza_lat, baza_lng, woj) -> List[str]:
    if woj not in STOLICE: return []
    w_lat, w_lng = STOLICE[woj]
    d = oblicz_dystans(baza_lat, baza_lng, w_lat, w_lng)
    if d < 12.0: return []
    sek = wyznacz_sektor(w_lat, w_lng, baza_lat, baza_lng)
    idx = SEKTORY_KOLEJNOSC.index(sek)
    if d <= 90.0: 
        return [SEKTORY_KOLEJNOSC[(idx - 2) % 8], SEKTORY_KOLEJNOSC[(idx - 1) % 8], sek, SEKTORY_KOLEJNOSC[(idx + 1) % 8], SEKTORY_KOLEJNOSC[(idx + 2) % 8]]
    else: 
        return [SEKTORY_KOLEJNOSC[(idx - 1) % 8], sek, SEKTORY_KOLEJNOSC[(idx + 1) % 8]]

_baza_miast_coords = None   # (lat, lng) bazy dla której policzono sektory w cache

def zaladuj_baze(baza_lat, baza_lng) -> Dict[str, List[Miasto]]:
    """Ładuje miasta i wylicza ich sektory (Płn/Płd/...) WZGLĘDEM PODANEJ BAZY.
    Cache jest ważny tylko dla tej samej bazy — gdy kolejny pracownik ma inny
    adres domowy, sektory są przeliczane od nowa (inaczej Marek z Krakowa
    dostałby kierunki liczone względem Warszawy Jana)."""
    global _baza_miast, _baza_miast_coords
    biezaca = (round(baza_lat, 4), round(baza_lng, 4))
    if _baza_miast and _baza_miast_coords == biezaca:
        return _baza_miast

    # Baza się zmieniła (lub pierwszy raz) — przeliczamy sektory od zera
    _baza_miast = {}
    _baza_miast_coords = biezaca
    for woj, lista in MIASTA_RAW.items():
        _baza_miast[woj] = []
        for d in lista:
            sektor = wyznacz_sektor(d['lat'], d['lng'], baza_lat, baza_lng)
            _baza_miast[woj].append(Miasto(n=d['n'], lat=d['lat'], lng=d['lng'], typ=d.get('typ', 'gmina'), sieci=d.get('sieci', 2), woj=woj, sektor=sektor))
    
    for woj in WSZYSTKIE_WOJEWODZTWA:
        if woj not in _baza_miast: _baza_miast[woj] = []
        obecne = {m.n for m in _baza_miast[woj]}
        if len(_baza_miast[woj]) < 15:
            for s in SASIEDZI_WOJ.get(woj, []):
                if s == woj: continue
                for m in _baza_miast.get(s, []):
                    if m.n not in obecne:
                        sekt = wyznacz_sektor(m.lat, m.lng, baza_lat, baza_lng)
                        _baza_miast[woj].append(Miasto(n=m.n, lat=m.lat, lng=m.lng, typ=m.typ, sieci=m.sieci, woj=s, sektor=sekt))
                        obecne.add(m.n)
    return _baza_miast

def _wielkanoc(rok: int) -> datetime.date:
    """Data Wielkanocy (algorytm gaussowski) — potrzebna też do ustalenia
    niedzieli handlowej poprzedzającej święta."""
    a = rok % 19; b = rok // 100; c = rok % 100; d = b // 4; e = b % 4; f = (b + 8) // 25
    g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7; m = (a + 11 * h + 22 * l) // 451
    miesiac = (h + l - 7 * m + 114) // 31; dzien = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(rok, miesiac, dzien)

ROK_WIGILII_WOLNEJ = 2025

def swieta_w_roku(rok: int) -> Set[datetime.date]:
    """Dni ustawowo wolne od pracy w roku (ustawa z 18 stycznia 1951 r.
    o dniach wolnych od pracy, z późniejszymi zmianami):
        1.01, 6.01, Wielkanoc i Poniedziałek Wielkanocny, 1.05, 3.05,
        Zielone Świątki (49 dni po Wielkanocy), Boże Ciało (60 dni po),
        15.08, 1.11, 11.11, 24.12 (od 2025 r.), 25.12, 26.12.
    Wielkanoc i Zielone Świątki wypadają w niedzielę — są w zbiorze, żeby
    kalendarz i taśma znały pełną listę, a nie tylko dni, które akurat
    zdejmują dzień roboczy."""
    wielkanoc = _wielkanoc(rok)
    stale = [
        datetime.date(rok, 1, 1), datetime.date(rok, 1, 6),
        datetime.date(rok, 5, 1), datetime.date(rok, 5, 3),
        datetime.date(rok, 8, 15), datetime.date(rok, 11, 1),
        datetime.date(rok, 11, 11), datetime.date(rok, 12, 25), datetime.date(rok, 12, 26),
        wielkanoc, wielkanoc + datetime.timedelta(days=1),
        wielkanoc + datetime.timedelta(days=49), wielkanoc + datetime.timedelta(days=60)
    ]
    if rok >= ROK_WIGILII_WOLNEJ:
        stale.append(datetime.date(rok, 12, 24))
    return set(stale)

def dni_zablokowane_miesiaca(rok: int, miesiac: int) -> Set[int]:
    """Numery dni miesiąca, w które w bieżącym trybie NIE MA pracy: święta
    i dni poza tygodniem roboczym (weekendy w trybie tygodniowym; w trybie
    wieczornym soboty są robocze, a niedziele tylko handlowe). Dopełnienie
    pobierz_dni_robocze — kalendarz „Dni bez pracy" blokuje je z góry."""
    robocze = {d.day for d in pobierz_dni_robocze(rok, miesiac)}
    _, n = calendar.monthrange(rok, miesiac)
    return {d for d in range(1, n + 1) if d not in robocze}

def pobierz_dni_robocze(rok: int, miesiac: int) -> List[datetime.date]:
    """Dni, w które można rozpisać pracę.

    Tryb tygodniowy: poniedziałek-piątek, bez świąt (jak dotychczas).
    Tryb wieczorny: dodatkowo SOBOTY. Niedziele wchodzą wyłącznie wtedy, gdy
    włączono niedziele handlowe — i tylko te, które nimi są.
    """
    swieta = swieta_w_roku(rok)
    _, n = calendar.monthrange(rok, miesiac)
    dni = []
    for d in range(1, n + 1):
        data = datetime.date(rok, miesiac, d)
        if data in swieta:
            continue
        dow = data.weekday()                     # 0=pon ... 5=sob, 6=nie
        if dow < 5:
            dni.append(data)
        elif dow == 5 and TRYB_PRACY == "wieczory":
            dni.append(data)                     # sobota jak zwykły dzień
        elif dow == 6 and TRYB_PRACY == "wieczory" and NIEDZIELE_HANDLOWE \
                and czy_niedziela_handlowa(data):
            dni.append(data)
    return dni

def czy_niedziela_handlowa(data: datetime.date) -> bool:
    """Niedziele handlowe: ostatnia niedziela stycznia, kwietnia, czerwca
    i sierpnia, dwie niedziele przed Bożym Narodzeniem oraz niedziela przed
    Wielkanocą. Zasada z ustawy o ograniczeniu handlu w niedziele —
    gdyby przepisy się zmieniły, wystarczy poprawić tę jedną funkcję."""
    if data.weekday() != 6:
        return False
    _, dni_mies = calendar.monthrange(data.year, data.month)
    ostatnia_niedziela = max(d for d in range(1, dni_mies + 1)
                             if datetime.date(data.year, data.month, d).weekday() == 6)
    if data.month in (1, 4, 6, 8) and data.day == ostatnia_niedziela:
        return True
    if data.month == 12:                          # dwie niedziele przed 24.12
        przed = [d for d in range(1, 25)
                 if datetime.date(data.year, 12, d).weekday() == 6]
        if data.day in przed[-2:]:
            return True
    try:
        wielkanoc = _wielkanoc(data.year)          # niedziela przed Wielkanocą
        if data == wielkanoc - datetime.timedelta(days=7):
            return True
    except Exception:
        pass
    return False

PLAN_CZAS_WIZYTY_MIN = 20           # średni czas jednej wizyty w punkcie

PLAN_SREDNIA_PREDKOSC_KMH = 50      # średnia prędkość w trasie (miasto+trasa)

class PunktWizyty:
    """Pojedynczy punkt do odwiedzenia (sklep/klient)."""
    __slots__ = ("nazwa", "adres", "siec", "lat", "lng", "miasto")
    def __init__(self, nazwa, adres, siec="", lat=None, lng=None, miasto=""):
        self.nazwa = nazwa          # etykieta wyświetlana
        self.adres = adres          # pełny adres (do geokodowania)
        self.siec = siec            # sieć/marka (opcjonalnie)
        self.lat = lat; self.lng = lng
        self.miasto = miasto

    def __repr__(self):
        return f"PunktWizyty({self.nazwa!r})"

class DzienPlanu:
    """Jeden dzień roboczy planu z listą wizyt w kolejności przejazdu."""
    __slots__ = ("data", "wizyty", "km", "minuty")
    def __init__(self, data):
        self.data = data            # datetime.date
        self.wizyty = []            # lista PunktWizyty w kolejności
        self.km = 0.0               # łączny dystans dnia
        self.minuty = 0.0           # łączny czas dnia (dojazdy + wizyty)

def _czas_przejazdu_min(km: float, predkosc: float = None) -> float:
    """Ile minut zajmie przejazd danego dystansu (średnia prędkość)."""
    v = predkosc or PLAN_SREDNIA_PREDKOSC_KMH
    if not v or v <= 0:
        v = PLAN_SREDNIA_PREDKOSC_KMH
    return (km / v) * 60.0

def ustawienia_planowania() -> dict:
    """Parametry planowania wg ustawień użytkownika (z sensownymi domyślnymi).
    Wcześniej były to sztywne stałe — a od nich zależy CAŁY plan: ile wizyt
    zmieści się w dniu, ile godzin zajmie, ile km."""
    def _num(klucz, dom, mini, maks):
        try:
            v = float(ustawienie(klucz, dom))
        except (TypeError, ValueError):
            v = float(dom)
        return max(mini, min(maks, v))
    return {
        "limit_minut": _num("plan_godziny", 8.0, 1.0, 16.0) * 60.0,
        "czas_wizyty": _num("plan_minuty_wizyta", PLAN_CZAS_WIZYTY_MIN, 1.0, 240.0),
        "predkosc": _num("plan_predkosc", PLAN_SREDNIA_PREDKOSC_KMH, 10.0, 130.0),
        "powrot": bool(ustawienie("plan_powrot_do_bazy", False)),
    }

def _dyst_prosty(a: PunktWizyty, b: PunktWizyty) -> float:
    """Szybki dystans liniowy (haversine) × współczynnik krętości dróg.
    Używany w planowaniu — NIE odpytuje sieci, więc działa błyskawicznie
    nawet dla tysięcy punktów."""
    if a.lat is None or b.lat is None:
        return 0.0
    return oblicz_dystans(a.lat, a.lng, b.lat, b.lng) * TEST_MNOZNIK_TRASY

MIASTA_ROZSZERZENIE = {
  "mazowieckie": [{"n":"Ciechanów","lat":52.88,"lng":20.62,"typ":"gmina","sieci":3},{"n":"Sochaczew","lat":52.23,"lng":20.24,"typ":"gmina","sieci":3},{"n":"Żyrardów","lat":52.05,"lng":20.45,"typ":"gmina","sieci":3},{"n":"Grodzisk Mazowiecki","lat":52.11,"lng":20.63,"typ":"gmina","sieci":4},{"n":"Pruszków","lat":52.17,"lng":20.81,"typ":"gmina","sieci":4},{"n":"Mińsk Mazowiecki","lat":52.18,"lng":21.57,"typ":"gmina","sieci":3},{"n":"Legionowo","lat":52.40,"lng":20.93,"typ":"gmina","sieci":4},{"n":"Nowy Dwór Mazowiecki","lat":52.43,"lng":20.72,"typ":"gmina","sieci":3},{"n":"Ostrów Mazowiecka","lat":52.80,"lng":21.90,"typ":"gmina","sieci":3},{"n":"Ostrołęka","lat":53.09,"lng":21.57,"typ":"gmina","sieci":3},{"n":"Maków Mazowiecki","lat":52.86,"lng":21.10,"typ":"gmina","sieci":2},{"n":"Płock","lat":52.55,"lng":19.71,"typ":"gmina","sieci":4},{"n":"Radom","lat":51.40,"lng":21.15,"typ":"gmina","sieci":4},{"n":"Konstancin-Jeziorna","lat":52.09,"lng":21.11,"typ":"gmina","sieci":3},{"n":"Garwolin","lat":51.90,"lng":21.61,"typ":"gmina","sieci":2},{"n":"Łaskarzew","lat":51.79,"lng":21.60,"typ":"gmina","sieci":2},{"n":"Pilawa","lat":51.87,"lng":21.55,"typ":"gmina","sieci":2},{"n":"Siedlce","lat":52.17,"lng":22.29,"typ":"gmina","sieci":4},{"n":"Sokołów Podlaski","lat":52.41,"lng":22.25,"typ":"gmina","sieci":3},{"n":"Węgrów","lat":52.40,"lng":22.02,"typ":"gmina","sieci":2},{"n":"Łochów","lat":52.53,"lng":21.68,"typ":"gmina","sieci":2},{"n":"Kosów Lacki","lat":52.60,"lng":22.15,"typ":"gmina","sieci":2},{"n":"Mordy","lat":52.21,"lng":22.52,"typ":"gmina","sieci":2},{"n":"Łosice","lat":52.21,"lng":22.72,"typ":"gmina","sieci":2},{"n":"Żelechów","lat":51.81,"lng":21.90,"typ":"gmina","sieci":2},{"n":"Raszyn","lat":52.15833,"lng":20.92417,"typ":"gmina","sieci":3},{"n":"Brwinów","lat":52.14,"lng":20.72,"typ":"gmina","sieci":3},{"n":"Milanówek","lat":52.12,"lng":20.67,"typ":"gmina","sieci":3},{"n":"Podkowa Leśna","lat":52.12300,"lng":20.72502,"typ":"gmina","sieci":2},{"n":"Ożarów Mazowiecki","lat":52.21,"lng":20.81,"typ":"gmina","sieci":3},{"n":"Łomianki","lat":52.34,"lng":20.88,"typ":"gmina","sieci":3},{"n":"Józefów (otwocki)","lat":52.14,"lng":21.23,"typ":"gmina","sieci":3},{"n":"Wierzbica (radomska)","lat":51.22,"lng":21.09,"typ":"gmina","sieci":2},{"n":"Jedlnia-Letnisko","lat":51.43119,"lng":21.33139,"typ":"gmina","sieci":2},{"n":"Zakrzew (radomski)","lat":51.42,"lng":21.00,"typ":"gmina","sieci":2},{"n":"Kozłów","lat":51.58,"lng":21.28,"typ":"gmina","sieci":2},{"n":"Sienno","lat":51.08497,"lng":21.47345,"typ":"gmina","sieci":2},{"n":"Solec nad Wisłą","lat":51.14,"lng":21.77,"typ":"gmina","sieci":2},{"n":"Chotcza","lat":51.28,"lng":21.75,"typ":"gmina","sieci":2},{"n":"Sarnaki","lat":52.32,"lng":22.90,"typ":"gmina","sieci":2},{"n":"Platerów","lat":52.30417,"lng":22.81709,"typ":"gmina","sieci":2},{"n":"Huszlew","lat":52.13743,"lng":22.83987,"typ":"gmina","sieci":2},{"n":"Bielany","lat":52.33430,"lng":22.25777,"typ":"gmina","sieci":2},{"n":"Olszanka","lat":52.19,"lng":22.70,"typ":"gmina","sieci":2},{"n":"Suchożebry","lat":52.25906,"lng":22.25311,"typ":"gmina","sieci":2},{"n":"Zbuczyn","lat":52.08934,"lng":22.43846,"typ":"gmina","sieci":2},{"n":"Domanice","lat":52.03744,"lng":22.17605,"typ":"gmina","sieci":2}],
  "łódzkie": [{"n":"Piotrków Trybunalski","lat":51.40,"lng":19.70,"typ":"gmina","sieci":4},{"n":"Radomsko","lat":51.07,"lng":19.44,"typ":"gmina","sieci":3},{"n":"Bełchatów","lat":51.37,"lng":19.36,"typ":"gmina","sieci":3},{"n":"Tomaszów Mazowiecki","lat":51.53,"lng":20.01,"typ":"gmina","sieci":3},{"n":"Opoczno","lat":51.38,"lng":20.28,"typ":"gmina","sieci":2},{"n":"Rawa Mazowiecka","lat":51.77,"lng":20.25,"typ":"gmina","sieci":2},{"n":"Skierniewice","lat":51.96,"lng":20.15,"typ":"gmina","sieci":3},{"n":"Łowicz","lat":52.11,"lng":19.95,"typ":"gmina","sieci":3},{"n":"Kutno","lat":52.23,"lng":19.36,"typ":"gmina","sieci":3},{"n":"Aleksandrów Łódzki","lat":51.82,"lng":19.30,"typ":"gmina","sieci":3},{"n":"Konstantynów Łódzki","lat":51.75,"lng":19.32,"typ":"gmina","sieci":3},{"n":"Sieradz","lat":51.60,"lng":18.73,"typ":"gmina","sieci":3},{"n":"Sulejów","lat":51.36,"lng":19.88,"typ":"gmina","sieci":2},{"n":"Wolbórz","lat":51.51,"lng":19.83,"typ":"gmina","sieci":2},{"n":"Moszczenica","lat":51.44,"lng":19.71,"typ":"gmina","sieci":2},{"n":"Gorzkowice","lat":51.21509,"lng":19.59654,"typ":"gmina","sieci":2},{"n":"Kamieńsk","lat":51.20444,"lng":19.49694,"typ":"gmina","sieci":2},{"n":"Przedbórz","lat":51.09,"lng":19.87,"typ":"gmina","sieci":2},{"n":"Żarnów","lat":51.25,"lng":20.17,"typ":"gmina","sieci":2},{"n":"Drzewica","lat":51.45,"lng":20.45,"typ":"gmina","sieci":2},{"n":"Białaczów","lat":51.30,"lng":20.27,"typ":"gmina","sieci":2},{"n":"Sławno","lat":51.39089,"lng":20.14109,"typ":"gmina","sieci":2},{"n":"Inowłódz","lat":51.53,"lng":20.24,"typ":"gmina","sieci":2},{"n":"Lubochnia","lat":51.61082,"lng":20.03932,"typ":"gmina","sieci":2},{"n":"Czerniewice","lat":51.65518,"lng":20.15650,"typ":"gmina","sieci":2},{"n":"Żelechlinek","lat":51.71093,"lng":20.03363,"typ":"gmina","sieci":2},{"n":"Mszczonów-Puszcza","lat":51.86,"lng":20.20,"typ":"gmina","sieci":2},{"n":"Nowy Kawęczyn","lat":51.88677,"lng":20.24298,"typ":"gmina","sieci":2},{"n":"Bolimów","lat":52.07644,"lng":20.16362,"typ":"gmina","sieci":2},{"n":"Kiernozia","lat":52.26853,"lng":19.87130,"typ":"gmina","sieci":2},{"n":"Bielawy","lat":52.05,"lng":19.75,"typ":"gmina","sieci":2},{"n":"Domaniewice","lat":52.00619,"lng":19.80294,"typ":"gmina","sieci":2},{"n":"Zduny","lat":52.10,"lng":19.92,"typ":"gmina","sieci":2},{"n":"Chąśno","lat":52.18566,"lng":19.93272,"typ":"gmina","sieci":2},{"n":"Krośniewice","lat":52.25,"lng":19.17,"typ":"gmina","sieci":2},{"n":"Żychlin","lat":52.24,"lng":19.62,"typ":"gmina","sieci":2},{"n":"Bedlno","lat":52.20,"lng":19.55,"typ":"gmina","sieci":2},{"n":"Krzyżanów","lat":52.20,"lng":19.35,"typ":"gmina","sieci":2},{"n":"Strzelce","lat":52.31539,"lng":19.40777,"typ":"gmina","sieci":2},{"n":"Oporów","lat":52.26173,"lng":19.55654,"typ":"gmina","sieci":2},{"n":"Świnice Warckie","lat":52.04107,"lng":18.92028,"typ":"gmina","sieci":2},{"n":"Uniejów","lat":51.97,"lng":18.79,"typ":"gmina","sieci":2},{"n":"Wartkowice","lat":51.97551,"lng":19.00184,"typ":"gmina","sieci":2},{"n":"Zadzim","lat":51.77590,"lng":18.84993,"typ":"gmina","sieci":2}],
  "kujawsko-pomorskie": [{"n":"Bydgoszcz","lat":53.12,"lng":18.01,"typ":"gmina","sieci":4},{"n":"Toruń","lat":53.01,"lng":18.60,"typ":"gmina","sieci":4},{"n":"Włocławek","lat":52.65,"lng":19.07,"typ":"gmina","sieci":4},{"n":"Inowrocław","lat":52.79,"lng":18.26,"typ":"gmina","sieci":3},{"n":"Brodnica","lat":53.25,"lng":19.40,"typ":"gmina","sieci":3},{"n":"Chełmno","lat":53.35,"lng":18.42,"typ":"gmina","sieci":2},{"n":"Nakło nad Notecią","lat":53.14,"lng":17.60,"typ":"gmina","sieci":2},{"n":"Sępólno Krajeńskie","lat":53.45,"lng":17.53,"typ":"gmina","sieci":2},{"n":"Janowiec Wielkopolski","lat":52.75,"lng":17.49,"typ":"gmina","sieci":2},{"n":"Piotrków Kujawski","lat":52.55032,"lng":18.49576,"typ":"gmina","sieci":2},{"n":"Aleksandrów Kujawski","lat":52.87,"lng":18.70,"typ":"gmina","sieci":2},{"n":"Nieszawa","lat":52.83409,"lng":18.90236,"typ":"gmina","sieci":2},{"n":"Kowalewo Pomorskie","lat":53.15469,"lng":18.89776,"typ":"gmina","sieci":2},{"n":"Golub-Dobrzyń","lat":53.11,"lng":19.05,"typ":"gmina","sieci":2},{"n":"Wąbrzeźno","lat":53.28,"lng":18.94,"typ":"gmina","sieci":2},{"n":"Rypin","lat":53.07,"lng":19.41,"typ":"gmina","sieci":2},{"n":"Lipno","lat":52.85,"lng":19.18,"typ":"gmina","sieci":2},{"n":"Dobrzyń nad Wisłą","lat":52.64,"lng":19.34,"typ":"gmina","sieci":2},{"n":"Kikoł","lat":52.79,"lng":19.20,"typ":"gmina","sieci":2},{"n":"Chrostkowo","lat":52.94346,"lng":19.25344,"typ":"gmina","sieci":2},{"n":"Brześć Kujawski","lat":52.61,"lng":18.90,"typ":"gmina","sieci":2},{"n":"Kowal","lat":52.53,"lng":19.15,"typ":"gmina","sieci":2},{"n":"Lubraniec","lat":52.53,"lng":18.85,"typ":"gmina","sieci":2},{"n":"Izbica Kujawska","lat":52.42,"lng":18.76,"typ":"gmina","sieci":2},{"n":"Chodecz","lat":52.40,"lng":19.03,"typ":"gmina","sieci":2},{"n":"Lubień Kujawski","lat":52.39,"lng":19.16,"typ":"gmina","sieci":2},{"n":"Baruchowo","lat":52.49126,"lng":19.23788,"typ":"gmina","sieci":2},{"n":"Fabianki","lat":52.72,"lng":19.10,"typ":"gmina","sieci":2},{"n":"Bobrowniki","lat":52.77849,"lng":18.95475,"typ":"gmina","sieci":2},{"n":"Jabłonowo Pomorskie","lat":53.39,"lng":19.15,"typ":"gmina","sieci":2},{"n":"Bartniczka","lat":53.24905,"lng":19.60763,"typ":"gmina","sieci":2},{"n":"Zbiczno","lat":53.33335,"lng":19.37526,"typ":"gmina","sieci":2},{"n":"Bobrowo","lat":53.28669,"lng":19.27034,"typ":"gmina","sieci":2},{"n":"Dragacz","lat":53.50244,"lng":18.73129,"typ":"gmina","sieci":2},{"n":"Radzyń Chełmiński","lat":53.38,"lng":18.93,"typ":"gmina","sieci":2},{"n":"Lisewo","lat":53.28,"lng":18.52,"typ":"gmina","sieci":2},{"n":"Papowo Biskupie","lat":53.24874,"lng":18.56487,"typ":"gmina","sieci":2},{"n":"Dąbrowa Chełmińska","lat":53.17528,"lng":18.30476,"typ":"gmina","sieci":2},{"n":"Zławieś Wielka","lat":53.10,"lng":18.35,"typ":"gmina","sieci":2}],
  "lubelskie": [{"n":"Lublin","lat":51.25,"lng":22.57,"typ":"gmina","sieci":4},{"n":"Zamość","lat":50.72,"lng":23.25,"typ":"gmina","sieci":3},{"n":"Chełm","lat":51.14,"lng":23.47,"typ":"gmina","sieci":3},{"n":"Biała Podlaska","lat":52.03,"lng":23.12,"typ":"gmina","sieci":3},{"n":"Łuków","lat":51.93,"lng":22.38,"typ":"gmina","sieci":2},{"n":"Radzyń Podlaski","lat":51.78,"lng":22.62,"typ":"gmina","sieci":2},{"n":"Parczew","lat":51.64,"lng":22.90,"typ":"gmina","sieci":2},{"n":"Włodawa","lat":51.55,"lng":23.55,"typ":"gmina","sieci":2},{"n":"Hrubieszów","lat":50.81,"lng":23.89,"typ":"gmina","sieci":2},{"n":"Tomaszów Lubelski","lat":50.45,"lng":23.42,"typ":"gmina","sieci":2},{"n":"Biłgoraj","lat":50.54,"lng":22.72,"typ":"gmina","sieci":2},{"n":"Janów Lubelski","lat":50.71,"lng":22.41,"typ":"gmina","sieci":2},{"n":"Opole Lubelskie","lat":51.15,"lng":21.97,"typ":"gmina","sieci":2},{"n":"Trawniki","lat":51.13,"lng":22.98,"typ":"gmina","sieci":2},{"n":"Ostrów Lubelski","lat":51.49,"lng":22.85,"typ":"gmina","sieci":2},{"n":"Kazimierz Dolny","lat":51.32,"lng":21.95,"typ":"gmina","sieci":2},{"n":"Żyrzyn","lat":51.49,"lng":22.09,"typ":"gmina","sieci":2},{"n":"Zakrzew (lubelski)","lat":51.04,"lng":22.35,"typ":"gmina","sieci":2},{"n":"Nowodwór","lat":51.72,"lng":22.03,"typ":"gmina","sieci":2},{"n":"Ułęż","lat":51.59208,"lng":22.11238,"typ":"gmina","sieci":2},{"n":"Kłoczew","lat":51.72218,"lng":21.95624,"typ":"gmina","sieci":2},{"n":"Adamów","lat":51.75,"lng":22.25,"typ":"gmina","sieci":2},{"n":"Serokomla","lat":51.70030,"lng":22.33289,"typ":"gmina","sieci":2},{"n":"Wojcieszków","lat":51.76824,"lng":22.31578,"typ":"gmina","sieci":2},{"n":"Stanin","lat":51.87029,"lng":22.20266,"typ":"gmina","sieci":2},{"n":"Trzebieszów","lat":51.98687,"lng":22.58269,"typ":"gmina","sieci":2},{"n":"Ulan-Majorat","lat":51.81145,"lng":22.48082,"typ":"gmina","sieci":2},{"n":"Kąkolewnica","lat":51.89924,"lng":22.70103,"typ":"gmina","sieci":2},{"n":"Międzyrzec Podlaski","lat":51.98,"lng":22.79,"typ":"gmina","sieci":2},{"n":"Wisznice","lat":51.79,"lng":23.20,"typ":"gmina","sieci":2},{"n":"Rossosz","lat":51.86,"lng":23.08,"typ":"gmina","sieci":2},{"n":"Łomazy","lat":51.90,"lng":23.19,"typ":"gmina","sieci":2},{"n":"Piszczac","lat":51.98100,"lng":23.37601,"typ":"gmina","sieci":2},{"n":"Kodeń","lat":51.91,"lng":23.61,"typ":"gmina","sieci":2},{"n":"Janów Podlaski","lat":52.19,"lng":23.21,"typ":"gmina","sieci":2},{"n":"Leśna Podlaska","lat":52.13,"lng":23.02,"typ":"gmina","sieci":2},{"n":"Rokitno","lat":52.10,"lng":23.24,"typ":"gmina","sieci":2},{"n":"Zalesie","lat":52.10,"lng":23.42,"typ":"gmina","sieci":2},{"n":"Sławatycze","lat":51.76290,"lng":23.55446,"typ":"gmina","sieci":2},{"n":"Hanna","lat":51.72,"lng":23.53,"typ":"gmina","sieci":2},{"n":"Dubienka","lat":51.05,"lng":23.87,"typ":"gmina","sieci":2},{"n":"Dorohusk","lat":51.15,"lng":23.79,"typ":"gmina","sieci":2},{"n":"Rejowiec","lat":51.09460,"lng":23.28352,"typ":"gmina","sieci":2},{"n":"Siedliszcze","lat":51.16,"lng":23.20,"typ":"gmina","sieci":2},{"n":"Sawin","lat":51.28,"lng":23.42,"typ":"gmina","sieci":2},{"n":"Ruda-Huta","lat":51.23601,"lng":23.59486,"typ":"gmina","sieci":2},{"n":"Wierzbica (chełmska)","lat":51.05,"lng":23.32,"typ":"gmina","sieci":2},{"n":"Żółkiewka","lat":50.86,"lng":22.86,"typ":"gmina","sieci":2},{"n":"Gorzków","lat":50.94113,"lng":22.98776,"typ":"gmina","sieci":2},{"n":"Grabowiec","lat":50.83,"lng":23.55,"typ":"gmina","sieci":2},{"n":"Miączyn","lat":50.75,"lng":23.50,"typ":"gmina","sieci":2},{"n":"Józefów (biłgorajski)","lat":50.48,"lng":23.05,"typ":"gmina","sieci":2},{"n":"Susiec","lat":50.42,"lng":23.20,"typ":"gmina","sieci":2},{"n":"Komarów-Osada","lat":50.62831,"lng":23.47584,"typ":"gmina","sieci":2},{"n":"Tarnogród","lat":50.36,"lng":22.74,"typ":"gmina","sieci":2},{"n":"Józefów Roztoczański","lat":50.48,"lng":23.05,"typ":"gmina","sieci":2},{"n":"Terespol","lat":52.07,"lng":23.61,"typ":"gmina","sieci":2}],
  "podlaskie": [{"n":"Białystok","lat":53.13,"lng":23.16,"typ":"gmina","sieci":4},{"n":"Suwałki","lat":54.10,"lng":22.93,"typ":"gmina","sieci":3},{"n":"Łomża","lat":53.18,"lng":22.06,"typ":"gmina","sieci":3},{"n":"Bielsk Podlaski","lat":52.77,"lng":23.19,"typ":"gmina","sieci":2},{"n":"Zambrów","lat":52.98,"lng":22.24,"typ":"gmina","sieci":2},{"n":"Wysokie Mazowieckie","lat":52.92,"lng":22.51,"typ":"gmina","sieci":2},{"n":"Sejny","lat":54.11,"lng":23.35,"typ":"gmina","sieci":2},{"n":"Dąbrowa Białostocka","lat":53.65,"lng":23.35,"typ":"gmina","sieci":2},{"n":"Jasionówka","lat":53.39519,"lng":23.03789,"typ":"gmina","sieci":2},{"n":"Stawiski","lat":53.38,"lng":22.14,"typ":"gmina","sieci":2},{"n":"Jedwabne","lat":53.29,"lng":22.30,"typ":"gmina","sieci":2},{"n":"Nowogród","lat":53.22,"lng":21.88,"typ":"gmina","sieci":2},{"n":"Piątnica","lat":53.19,"lng":22.11,"typ":"gmina","sieci":2},{"n":"Wizna","lat":53.19,"lng":22.38,"typ":"gmina","sieci":2},{"n":"Śniadowo","lat":53.03817,"lng":21.99077,"typ":"gmina","sieci":2},{"n":"Miastkowo","lat":53.15178,"lng":21.82354,"typ":"gmina","sieci":2},{"n":"Czerwone","lat":53.42374,"lng":21.88950,"typ":"gmina","sieci":2},{"n":"Turośl","lat":53.38780,"lng":21.72755,"typ":"gmina","sieci":2},{"n":"Zbójna","lat":53.24247,"lng":21.79243,"typ":"gmina","sieci":2},{"n":"Łomża-Wschód","lat":53.16,"lng":22.15,"typ":"gmina","sieci":2},{"n":"Rutki-Kossaki","lat":53.08923,"lng":22.44065,"typ":"gmina","sieci":2},{"n":"Kołaki Kościelne","lat":53.02234,"lng":22.37798,"typ":"gmina","sieci":2},{"n":"Szumowo","lat":52.90,"lng":22.09,"typ":"gmina","sieci":2},{"n":"Klukowo","lat":52.75,"lng":22.42,"typ":"gmina","sieci":2},{"n":"Nowe Piekuty","lat":52.85657,"lng":22.70946,"typ":"gmina","sieci":2},{"n":"Kulesze Kościelne","lat":53.01573,"lng":22.50562,"typ":"gmina","sieci":2},{"n":"Rudka","lat":52.63,"lng":22.75,"typ":"gmina","sieci":2},{"n":"Czeremcha","lat":52.51,"lng":23.34,"typ":"gmina","sieci":2},{"n":"Białowieża","lat":52.70,"lng":23.86,"typ":"gmina","sieci":2},{"n":"Dubicze Cerkiewne","lat":52.65214,"lng":23.43798,"typ":"gmina","sieci":2},{"n":"Nurzec-Stacja","lat":52.51,"lng":23.05,"typ":"gmina","sieci":2},{"n":"Perlejewo","lat":52.56915,"lng":22.56283,"typ":"gmina","sieci":2},{"n":"Filipów","lat":54.18,"lng":22.61,"typ":"gmina","sieci":2},{"n":"Bakałarzewo","lat":54.09358,"lng":22.65164,"typ":"gmina","sieci":2},{"n":"Raczki","lat":53.98,"lng":22.78,"typ":"gmina","sieci":2},{"n":"Nowinka","lat":53.92,"lng":23.02,"typ":"gmina","sieci":2},{"n":"Płaska","lat":53.90517,"lng":23.26708,"typ":"gmina","sieci":2},{"n":"Giby","lat":54.04130,"lng":23.35375,"typ":"gmina","sieci":2},{"n":"Krasnopol","lat":54.11585,"lng":23.20670,"typ":"gmina","sieci":2},{"n":"Puńsk","lat":54.24,"lng":23.19,"typ":"gmina","sieci":2},{"n":"Szypliszki","lat":54.25386,"lng":23.07225,"typ":"gmina","sieci":2},{"n":"Jeleniewo","lat":54.20578,"lng":22.91255,"typ":"gmina","sieci":2},{"n":"Suwałki-Wschód","lat":54.09,"lng":23.00,"typ":"gmina","sieci":2},{"n":"Wiżajny","lat":54.38,"lng":22.86,"typ":"gmina","sieci":2}],
  "warmińsko-mazurskie": [{"n":"Olsztyn","lat":53.78,"lng":20.49,"typ":"gmina","sieci":4},{"n":"Ełk","lat":53.83,"lng":22.36,"typ":"gmina","sieci":3},{"n":"Giżycko","lat":54.04,"lng":21.77,"typ":"gmina","sieci":2},{"n":"Szczytno","lat":53.56,"lng":21.00,"typ":"gmina","sieci":2},{"n":"Pisz","lat":53.63,"lng":21.81,"typ":"gmina","sieci":2},{"n":"Lidzbark Warmiński","lat":54.13,"lng":20.58,"typ":"gmina","sieci":2},{"n":"Olecko","lat":54.03,"lng":22.50,"typ":"gmina","sieci":2},{"n":"Gołdap","lat":54.31,"lng":22.31,"typ":"gmina","sieci":2},{"n":"Węgorzewo","lat":54.21,"lng":21.74,"typ":"gmina","sieci":2},{"n":"Nowe Miasto Lubawskie","lat":53.42,"lng":19.60,"typ":"gmina","sieci":2},{"n":"Dobrze Miasto-Wieś","lat":53.99,"lng":20.42,"typ":"gmina","sieci":2},{"n":"Wilczęta","lat":54.16866,"lng":19.88265,"typ":"gmina","sieci":2},{"n":"Górowo Iławeckie","lat":54.28,"lng":20.49,"typ":"gmina","sieci":2},{"n":"Srokowo","lat":54.22,"lng":21.52,"typ":"gmina","sieci":2},{"n":"Barciany","lat":54.21991,"lng":21.35346,"typ":"gmina","sieci":2},{"n":"Kruklanki","lat":54.09050,"lng":21.92429,"typ":"gmina","sieci":2},{"n":"Pozezdrze","lat":54.14,"lng":21.86,"typ":"gmina","sieci":2},{"n":"Budry","lat":54.25292,"lng":21.88089,"typ":"gmina","sieci":2},{"n":"Banie Mazurskie","lat":54.25,"lng":22.05,"typ":"gmina","sieci":2},{"n":"Kowale Oleckie","lat":54.16686,"lng":22.41457,"typ":"gmina","sieci":2},{"n":"Świętajno","lat":54.05,"lng":22.35,"typ":"gmina","sieci":2},{"n":"Wieliczki","lat":53.98547,"lng":22.56717,"typ":"gmina","sieci":2},{"n":"Prostki","lat":53.70,"lng":22.44,"typ":"gmina","sieci":2},{"n":"Kalinowo","lat":53.87498,"lng":22.67300,"typ":"gmina","sieci":2},{"n":"Stare Juchy","lat":53.92207,"lng":22.17378,"typ":"gmina","sieci":2},{"n":"Ryn","lat":53.94,"lng":21.55,"typ":"gmina","sieci":2},{"n":"Miłki","lat":53.94204,"lng":21.87385,"typ":"gmina","sieci":2},{"n":"Wydminy","lat":53.98184,"lng":22.03221,"typ":"gmina","sieci":2},{"n":"Orzysz","lat":53.81,"lng":21.94,"typ":"gmina","sieci":2},{"n":"Biała Piska","lat":53.61,"lng":22.05,"typ":"gmina","sieci":2},{"n":"Ruciane-Nida","lat":53.64176,"lng":21.53714,"typ":"gmina","sieci":2},{"n":"Świętajno-Szczytno","lat":53.65,"lng":21.14,"typ":"gmina","sieci":2},{"n":"Rozogi","lat":53.44,"lng":21.35,"typ":"gmina","sieci":2},{"n":"Wielbark","lat":53.40,"lng":20.94,"typ":"gmina","sieci":2},{"n":"Janowiec Kościelny","lat":53.28988,"lng":20.52262,"typ":"gmina","sieci":2},{"n":"Biskupiec Pomorski","lat":53.45,"lng":19.44,"typ":"gmina","sieci":2}],
}

_SKROTY_NAZW = {
    "maz.": "mazowiecki", "maz": "mazowiecki", "mazowiecka": "mazowiecki",
    "mazowieckie": "mazowiecki", "wlkp.": "wielkopolski", "wlkp": "wielkopolski",
    "wielkopolska": "wielkopolski", "śl.": "śląski", "sl.": "śląski",
    "śląska": "śląski", "gd.": "gdański", "kuj.": "kujawski",
    "pom.": "pomorski", "pomorska": "pomorski", "lub.": "lubelski",
    "podl.": "podlaski", "podlaska": "podlaski", "warm.": "warmiński",
    "krak.": "krakowski", "ł.": "łódzki", "l.": "łódzki", "łódzka": "łódzki",
    "wlk.": "wielki", "wielka": "wielki", "wlk": "wielki",
    "dln.": "dolny", "dolna": "dolny", "górna": "górny", "gorna": "górny",
    "g.": "górny", "st.": "stary", "stara": "stary", "n.": "nowy", "nowa": "nowy",
}

def _normalizuj_nazwe(nazwa: str) -> str:
    """Ujednolica nazwę do porównań: małe litery, rozwinięte skróty.
    'Maków Maz.' i 'Maków Mazowiecki' dają ten sam wynik."""
    czesci = str(nazwa).strip().lower().replace("-", " ").split()
    return " ".join(_SKROTY_NAZW.get(c, c) for c in czesci)

def _blisko_km(lat1, lng1, lat2, lng2) -> float:
    """Odległość w linii prostej — do wykrywania tego samego punktu."""
    import math as _m
    dlat = _m.radians(lat2 - lat1); dlng = _m.radians(lng2 - lng1)
    a = (_m.sin(dlat / 2) ** 2 + _m.cos(_m.radians(lat1)) *
         _m.cos(_m.radians(lat2)) * _m.sin(dlng / 2) ** 2)
    return 6371.0 * 2 * _m.asin(_m.sqrt(a))

def _rdzen_nazwy(nazwa: str) -> str:
    """Nazwa bez dopisku w nawiasie: 'Wierzbica (radomska)' → 'wierzbica'.
    Służy wyłącznie do wyłapywania tej samej miejscowości zapisanej dwa razy."""
    rdzen = str(nazwa or "").split("(")[0]
    return _normalizuj_nazwe(rdzen).strip()

def _scal_baze_miast():
    """Dokłada rozszerzenie do bazy głównej, pomijając duplikaty. Dodatkowo
    czyści duplikaty już obecne w danych źródłowych — dzięki temu w jednej
    trasie nie pojawi się dwa razy to samo miasto pod dwiema nazwami."""
    for _woj in list(MIASTA_RAW.keys()) + [w for w in MIASTA_ROZSZERZENIE if w not in MIASTA_RAW]:
        istniejace = MIASTA_RAW.get(_woj, [])
        wynik, klucze = [], []
        for _m in list(istniejace) + list(MIASTA_ROZSZERZENIE.get(_woj, [])):
            klucz = _normalizuj_nazwe(_m.get("n", ""))
            rdzen = _rdzen_nazwy(_m.get("n", ""))
            lat, lng = float(_m.get("lat", 0)), float(_m.get("lng", 0))
            duplikat = -1
            for _i, (k2, r2, la2, ln2) in enumerate(klucze):
                odl = _blisko_km(lat, lng, la2, ln2)
                # ta sama nazwa, ten sam punkt — albo ta sama nazwa w dwóch
                # zapisach ("Wierzbica" i "Wierzbica (radomska)") w promieniu
                # jednego powiatu. Bez tego jedna trasa potrafiła odwiedzić tę
                # samą miejscowość dwa razy pod dwiema nazwami.
                if klucz == k2 or odl < 2.0 or (rdzen and rdzen == r2 and odl < 12.0):
                    duplikat = _i
                    break
            if duplikat >= 0:
                # zostaje wpis z lepszą wiedzą o rynku (więcej sieci)
                if int(_m.get("sieci", 0)) > int(wynik[duplikat].get("sieci", 0)):
                    wynik[duplikat] = _m
                continue
            klucze.append((klucz, rdzen, lat, lng))
            wynik.append(_m)
        MIASTA_RAW[_woj] = wynik

    # Ten sam punkt wpisany pod dwoma województwami (Grodków siedział i w
    # opolskim, i w dolnośląskim). Scalanie wyżej idzie po województwach, więc
    # takiej pary nie widzi — ta pętla sprząta po całej bazie.
    _punkty = {}
    for _woj in list(MIASTA_RAW.keys()):
        _zostaje = []
        for _m in MIASTA_RAW[_woj]:
            _kl = (_rdzen_nazwy(_m.get("n", "")),
                   round(float(_m.get("lat", 0)), 2), round(float(_m.get("lng", 0)), 2))
            _byl = _punkty.get(_kl)
            if _byl is None:
                _punkty[_kl] = (_woj, _m)
                _zostaje.append(_m)
                continue
            _woj_b, _m_b = _byl
            if int(_m.get("sieci", 0)) > int(_m_b.get("sieci", 0)):
                MIASTA_RAW[_woj_b] = [x for x in MIASTA_RAW[_woj_b] if x is not _m_b]
                _punkty[_kl] = (_woj, _m)
                _zostaje.append(_m)
        MIASTA_RAW[_woj] = _zostaje

def _rozwin_skroty_w_bazie():
    """Na dokumencie i w trasach mają być pełne nazwy: 'Maków Mazowiecki',
    nie 'Maków Maz.'. Zamiana obejmuje wyłącznie widoczną nazwę."""
    _pelne = {"maz.": "Mazowiecki", "wlkp.": "Wielkopolski", "śl.": "Śląski",
              "gd.": "Gdański", "kuj.": "Kujawski", "pom.": "Pomorski",
              "lub.": "Lubelski", "podl.": "Podlaski", "warm.": "Warmiński",
              "krak.": "Krakowski", "ł.": "Łódzki", "wlk.": "Wielki",
              "g.": "Górny", "dln.": "Dolny", "st.": "Stary"}
    # "n." w środku nazwy to przyimek "nad" (Kostrzyn nad Odrą), a nie "Nowy" —
    # rozwinięte na "Nowy" psuło nazwę i wypychało ją poza dawny limit długości
    _przyimki = {"n.": "nad"}
    # nieregularne formy, których nie da się wyprowadzić z końcówki poprzedniego
    # słowa (Ostrów Mazowiecka jest rodzaju żeńskiego mimo spółgłoski na końcu)
    _wyjatki = {"Ostrów Mazowiecki": "Ostrów Mazowiecka"}
    _nijakie = {"Mazowiecki": "Mazowieckie", "Wielkopolski": "Wielkopolskie",
                "Śląski": "Śląskie", "Pomorski": "Pomorskie",
                "Wielki": "Wielkie", "Kujawski": "Kujawskie",
                "Lubelski": "Lubelskie", "Podlaski": "Podlaskie"}
    _konczy_e = lambda n: n.strip().endswith("e")
    # formy żeńskie tam, gdzie nazwa miasta jest rodzaju żeńskiego
    _zenskie = {"Mazowiecki": "Mazowiecka", "Wielkopolski": "Wielkopolska",
                "Śląski": "Śląska", "Pomorski": "Pomorska", "Wielki": "Wielka"}
    _konczy_a = lambda n: n.strip().endswith("a")
    for _woj, _lista in MIASTA_RAW.items():
        for _m in _lista:
            czesci = str(_m.get("n", "")).split()
            if not czesci:
                continue
            zmiana = False
            for i, c in enumerate(czesci):
                if i > 0 and c.lower() in _przyimki:
                    czesci[i] = _przyimki[c.lower()]
                    zmiana = True
                    continue
                pelna = _pelne.get(c.lower())
                if not pelna:
                    continue
                if i > 0 and _konczy_a(czesci[i - 1]):
                    pelna = _zenskie.get(pelna, pelna)
                elif i > 0 and _konczy_e(czesci[i - 1]):
                    pelna = _nijakie.get(pelna, pelna)
                czesci[i] = pelna
                zmiana = True
            if zmiana:
                nowa = " ".join(czesci)
                _m["n"] = _wyjatki.get(nowa, nowa)

_scal_baze_miast()

_rozwin_skroty_w_bazie()

MIASTA_DUZE = {
    "warszawa": (52.23, 21.01), "kraków": (50.06, 19.94), "łódź": (51.76, 19.46),
    "wrocław": (51.11, 17.03), "poznań": (52.41, 16.93), "gdańsk": (54.35, 18.65),
    "szczecin": (53.43, 14.55), "bydgoszcz": (53.12, 18.01), "lublin": (51.25, 22.57),
    "białystok": (53.13, 23.16), "katowice": (50.26, 19.02), "gdynia": (54.52, 18.53),
    "częstochowa": (50.81, 19.12), "radom": (51.40, 21.15), "toruń": (53.01, 18.60),
    "kielce": (50.87, 20.63), "rzeszów": (50.04, 22.00), "gliwice": (50.29, 18.67),
    "zabrze": (50.32, 18.79), "olsztyn": (53.78, 20.49), "bielsko-biała": (49.82, 19.04),
    "bytom": (50.35, 18.92), "zielona góra": (51.94, 15.51), "rybnik": (50.10, 18.55),
    "ruda śląska": (50.26, 18.86), "tychy": (50.14, 18.99), "dąbrowa górnicza": (50.32, 19.20),
    "gorzów wielkopolski": (52.73, 15.24), "płock": (52.55, 19.71), "wałbrzych": (50.77, 16.28),
    "włocławek": (52.65, 19.07), "tarnów": (50.01, 20.99), "chorzów": (50.30, 18.95),
    "koszalin": (54.19, 16.18), "legnica": (51.21, 16.16), "słupsk": (54.46, 17.03),
    "jaworzno": (50.20, 19.27), "jastrzębie-zdrój": (49.95, 18.60), "nowy sącz": (49.62, 20.70),
    "jelenia góra": (50.90, 15.73), "siedlce": (52.17, 22.29), "mysłowice": (50.21, 19.13),
    "piła": (53.15, 16.74), "konin": (52.22, 18.25), "piotrków trybunalski": (51.41, 19.70),
    "inowrocław": (52.79, 18.26), "lubin": (51.40, 16.20), "ostrów wielkopolski": (51.65, 17.81),
    "suwałki": (54.10, 22.93), "stargard": (53.34, 15.05), "gniezno": (52.53, 17.60),
    "ostrowiec świętokrzyski": (50.93, 21.39), "siemianowice śląskie": (50.33, 19.03),
    "głogów": (51.66, 16.08), "pabianice": (51.66, 19.36), "leszno": (51.84, 16.58),
    "żory": (50.05, 18.70), "zamość": (50.72, 23.25), "pruszków": (52.17, 20.81),
    "łomża": (53.18, 22.08), "ełk": (53.83, 22.36), "tarnobrzeg": (50.57, 21.68),
    "chełm": (51.14, 23.47), "mielec": (50.29, 21.42), "kędzierzyn-koźle": (50.35, 18.23),
    "piaseczno": (52.08, 21.02), "tomaszów mazowiecki": (51.53, 20.01), "świdnica": (50.84, 16.49),
    "bełchatów": (51.37, 19.36), "zgierz": (51.86, 19.41), "otwock": (52.11, 21.26),
    "legionowo": (52.40, 20.93), "wejherowo": (54.60, 18.24), "skierniewice": (51.96, 20.16),
    "starachowice": (51.05, 21.07), "racibórz": (50.09, 18.22), "świnoujście": (53.91, 14.25),
    "kutno": (52.23, 19.36), "sieradz": (51.60, 18.73), "nowa sól": (51.80, 15.72),
    "krosno": (49.69, 21.77), "szczecinek": (53.71, 16.70), "skarżysko-kamienna": (51.11, 20.88),
    "malbork": (54.04, 19.03), "sanok": (49.56, 22.21), "świętochłowice": (50.29, 18.92),
    "puławy": (51.42, 21.97), "przemyśl": (49.78, 22.77), "stalowa wola": (50.58, 22.05),
    "biała podlaska": (52.03, 23.12), "ciechanów": (52.88, 20.62), "żyrardów": (52.05, 20.44),
    "nowy targ": (49.48, 20.03), "oświęcim": (50.04, 19.22), "zawiercie": (50.49, 19.42),
    "wodzisław śląski": (50.00, 18.47), "mikołów": (50.17, 18.90), "knurów": (50.22, 18.66),
    "czechowice-dziedzice": (49.91, 19.00), "cieszyn": (49.75, 18.63), "będzin": (50.33, 19.13),
    "sopot": (54.44, 18.56), "tczew": (54.09, 18.79), "starogard gdański": (53.97, 18.53),
    "kwidzyn": (53.73, 18.93), "chojnice": (53.70, 17.56), "lębork": (54.55, 17.75),
    "rumia": (54.57, 18.39), "reda": (54.60, 18.35), "iława": (53.60, 19.57),
    "ostróda": (53.70, 19.97), "giżycko": (54.04, 21.76), "kętrzyn": (54.07, 21.38),
    "mrągowo": (53.87, 21.30), "szczytno": (53.56, 20.99), "działdowo": (53.24, 20.18),
    "augustów": (53.84, 22.98), "grudziądz": (53.48, 18.75), "elbląg": (54.16, 19.40),
    "opole": (50.67, 17.92), "kalisz": (51.76, 18.09), "sosnowiec": (50.28, 19.13),
    "nowy dwór mazowiecki": (52.43, 20.72), "wołomin": (52.34, 21.24), "mińsk mazowiecki": (52.18, 21.57),
    "grodzisk mazowiecki": (52.11, 20.63), "żyrardow": (52.05, 20.44), "sochaczew": (52.23, 20.24),
    "wyszków": (52.59, 21.46), "garwolin": (51.90, 21.62), "kozienice": (51.58, 21.55),
    "grójec": (51.86, 20.87), "pułtusk": (52.70, 21.09), "sokołów podlaski": (52.41, 22.25),
    "ostrołęka": (53.08, 21.57), "mława": (53.11, 20.38), "przasnysz": (53.02, 20.88),
    "zwoleń": (51.36, 21.59), "pionki": (51.48, 21.45), "szydłowiec": (51.23, 20.85),
    "końskie": (51.19, 20.41), "jędrzejów": (50.64, 20.30), "busko-zdrój": (50.47, 20.72),
    "sandomierz": (50.68, 21.75), "staszów": (50.56, 21.17), "opatów": (50.80, 21.42),
}

_INDEKS_MIAST = None

def _norm_miasto(nazwa: str) -> str:
    """Normalizuje nazwę miasta do porównań (małe litery, bez skrótów/spacji)."""
    s = str(nazwa or "").strip().lower()
    # usuń typowe skróty wojewódzkie/powiatowe na końcu
    for skrot in [" wlkp.", " maz.", " k.", " śl.", " lub.", " podl.", " pom."]:
        if s.endswith(skrot):
            s = s[:-len(skrot)]
    return s.strip()

def _zbuduj_indeks_miast():
    global _INDEKS_MIAST
    if _INDEKS_MIAST is not None:
        return _INDEKS_MIAST
    _INDEKS_MIAST = {}
    # 1) gminy z MIASTA_RAW
    for woj, miasta in MIASTA_RAW.items():
        for m in miasta:
            klucz = _norm_miasto(m["n"])
            if klucz and klucz not in _INDEKS_MIAST:
                _INDEKS_MIAST[klucz] = (m["lat"], m["lng"])
    # 2) duże miasta (mają pierwszeństwo — dokładniejsze centra)
    for nazwa, coords in MIASTA_DUZE.items():
        _INDEKS_MIAST[_norm_miasto(nazwa)] = coords
    return _INDEKS_MIAST

def coords_z_miasta(miasto: str):
    """Zwraca (lat, lng) z bazy offline dla nazwy miasta albo None.
    Natychmiastowe — bez internetu."""
    if not miasto:
        return None
    idx = _zbuduj_indeks_miast()
    return idx.get(_norm_miasto(miasto))

def planuj_wizyty(punkty: List[PunktWizyty], rok: int, miesiac: int,
                  baza: PunktWizyty = None, offline=False, postep_cb=None,
                  max_miesiecy=12, od_daty: datetime.date = None) -> dict:
    """Główny planer WIELOMIESIĘCZNY. Rozkłada punkty na dni robocze —
    jeśli nie mieszczą się w jednym miesiącu, przechodzą na kolejne (aż do
    max_miesiecy). Każdy punkt odwiedzany RAZ (w swoim miesiącu).
      - grupuje geograficznie (najbliższy sąsiad),
      - limit 8h dziennie (dojazdy liniowe + wizyty),
      - pon-pt, bez świąt.
    baza: punkt startowy każdego dnia (np. adres domowy). None = środek
    geograficzny punktów.
    od_daty: pomija dni robocze WCZEŚNIEJSZE niż podana data — używane przy
    przenoszeniu zaległych wizyt (nie planujemy w przeszłości).
    Zwraca dict: 'miesiace' (lista planów miesięcznych) + zbiorcze metryki.
    Dla zgodności zwraca też 'dni' = wszystkie dni ze wszystkich miesięcy."""
    z_pozycja = [p for p in punkty if p.lat is not None and p.lng is not None]
    bez_pozycji = [p for p in punkty if p.lat is None or p.lng is None]

    if not z_pozycja:
        return {"dni": [], "miesiace": [], "bez_pozycji": bez_pozycji,
                "nierozplanowane": [], "suma_km": 0.0, "suma_wizyt": 0,
                "rok": rok, "miesiac": miesiac, "liczba_miesiecy": 0}

    # baza — punkt startowy dnia. Jeśli nie podano, bierzemy środek geograficzny
    # (sztuczny). Realny adres domowy daje znacznie lepsze trasy.
    if baza is None or baza.lat is None:
        sx = sum(p.lat for p in z_pozycja) / len(z_pozycja)
        sy = sum(p.lng for p in z_pozycja) / len(z_pozycja)
        baza = PunktWizyty("Środek trasy", "", lat=sx, lng=sy)

    # parametry planowania z ustawień użytkownika (godziny/dzień, czas wizyty…)
    UP = ustawienia_planowania()
    LIMIT = UP["limit_minut"]; CZAS_W = UP["czas_wizyty"]
    PREDK = UP["predkosc"];    POWROT = UP["powrot"]

    pozostale = list(z_pozycja)
    miesiace_plan = []
    wszystkie_dni = []
    cur_rok, cur_mies = rok, miesiac
    licznik_mies = 0

    while pozostale and licznik_mies < max_miesiecy:
        dni_robocze = pobierz_dni_robocze(cur_rok, cur_mies)
        dni_robocze = [d for d in dni_robocze if not czy_dzien_wolny(d)]
        if od_daty:
            dni_robocze = [d for d in dni_robocze if d >= od_daty]
        dni_plan = []
        aktualna_pozycja = baza
        for data in dni_robocze:
            if not pozostale:
                break
            dzien = DzienPlanu(data)
            czas = 0.0; km_dnia = 0.0
            pozycja = aktualna_pozycja
            if postep_cb:
                zrobione = len(z_pozycja) - len(pozostale)
                postep_cb(f"Planowanie {cur_mies:02d}.{cur_rok} — {data.strftime('%d.%m')}...",
                          zrobione / max(len(z_pozycja), 1))
            while pozostale:
                najbl = None; najbl_km = None
                for p in pozostale:
                    d = _dyst_prosty(pozycja, p)
                    if najbl_km is None or d < najbl_km:
                        najbl_km = d; najbl = p
                czas_do = _czas_przejazdu_min(najbl_km, PREDK)
                # jeśli wliczamy powrót do bazy — rezerwujemy na niego czas
                rezerwa = _czas_przejazdu_min(_dyst_prosty(najbl, baza), PREDK) if POWROT else 0.0
                if czas + czas_do + CZAS_W + rezerwa > LIMIT and dzien.wizyty:
                    break
                dzien.wizyty.append(najbl)
                czas += czas_do + CZAS_W
                km_dnia += najbl_km
                pozycja = najbl
                pozostale.remove(najbl)
            if POWROT and dzien.wizyty:
                km_pow = _dyst_prosty(pozycja, baza)
                km_dnia += km_pow
                czas += _czas_przejazdu_min(km_pow, PREDK)
            dzien.km = round(km_dnia, 1)
            dzien.minuty = round(czas, 0)
            if dzien.wizyty:
                dni_plan.append(dzien)
                aktualna_pozycja = dzien.wizyty[-1]

        if dni_plan:
            miesiace_plan.append({
                "rok": cur_rok, "miesiac": cur_mies,
                "dni": dni_plan,
                "suma_km": round(sum(d.km for d in dni_plan), 1),
                "suma_wizyt": sum(len(d.wizyty) for d in dni_plan),
            })
            wszystkie_dni.extend(dni_plan)

        # następny miesiąc
        cur_mies += 1
        if cur_mies > 12:
            cur_mies = 1; cur_rok += 1
        licznik_mies += 1

    suma_km = round(sum(d.km for d in wszystkie_dni), 1)
    suma_wizyt = sum(len(d.wizyty) for d in wszystkie_dni)
    return {
        "dni": wszystkie_dni,           # wszystkie dni (zgodność wstecz)
        "miesiace": miesiace_plan,      # plany per miesiąc
        "liczba_miesiecy": len(miesiace_plan),
        "bez_pozycji": bez_pozycji,
        "nierozplanowane": pozostale,   # gdyby przekroczono max_miesiecy
        "suma_km": suma_km,
        "suma_wizyt": suma_wizyt,
        "rok": rok, "miesiac": miesiac,
    }

MIASTA_WIELKIE = {
    "warszawa", "kraków", "łódź", "wrocław", "poznań", "gdańsk", "szczecin",
    "bydgoszcz", "lublin", "białystok", "katowice", "gdynia", "częstochowa",
    "radom", "sosnowiec", "toruń", "kielce", "rzeszów", "gliwice", "zabrze",
    "olsztyn", "bielsko-biała", "bytom", "zielona góra", "rybnik", "ruda śląska",
    "opole", "tychy", "gorzów wielkopolski", "elbląg", "dąbrowa górnicza",
    "płock", "wałbrzych", "włocławek", "tarnów", "chorzów", "koszalin",
    "kalisz", "legnica", "grudziądz", "słupsk", "jaworzno", "jastrzębie-zdrój",
    "nowy sącz", "jelenia góra", "konin", "piotrków trybunalski", "siedlce",
    "mysłowice", "piła", "ostrów wielkopolski", "lubin", "suwałki",
    "inowrocław", "gniezno", "stargard", "ostrowiec świętokrzyski",
    "siemianowice śląskie", "głogów", "pabianice", "leszno", "żory",
}

def czy_duze_miasto(miasto: str) -> bool:
    """Czy miejscowość to DUŻE miasto (>~100 tys.) — wg listy MIASTA_WIELKIE.
    Używane w regułach cyklu: np. Biedronki w miastach częściej niż poza nimi."""
    if not miasto:
        return False
    return _norm_miasto(miasto) in MIASTA_WIELKIE

def cykl_dla_punktu(punkt, cykl_domyslny=4, cykle_sieci=None,
                    cykle_sieci_duze=None, cykle_punktow=None) -> int:
    """Ustala co ile TYGODNI odwiedzać dany punkt. Hierarchia (od najsilniejszej):
      1. cykl ustawiony dla KONKRETNEGO punktu (adres) — nadpisuje wszystko,
      2. cykl sieci Z PODZIAŁEM na duże miasta / poza nimi,
      3. cykl sieci (wspólny),
      4. cykl domyślny.
    """
    cykle_sieci = cykle_sieci or {}
    cykle_sieci_duze = cykle_sieci_duze or {}
    cykle_punktow = cykle_punktow or {}

    def _int(v):
        try:
            v = int(v)
            return v if v >= 1 else None
        except (TypeError, ValueError):
            return None

    adres = (getattr(punkt, "adres", "") or getattr(punkt, "nazwa", "") or "").strip().lower()
    siec = (getattr(punkt, "siec", "") or "").strip()
    miasto = getattr(punkt, "miasto", "") or ""

    # 1) punkt indywidualny
    v = _int(cykle_punktow.get(adres))
    if v:
        return v
    # 2) sieć + klasa miasta
    if czy_duze_miasto(miasto):
        v = _int(cykle_sieci_duze.get(siec))
        if v:
            return v
    # 3) sieć (wspólny)
    v = _int(cykle_sieci.get(siec))
    if v:
        return v
    # 4) domyślny
    return max(1, _int(cykl_domyslny) or 4)

def planuj_cyklicznie(punkty: List[PunktWizyty], rok: int, miesiac: int,
                      cykl_domyslny: int = 4, cykle_sieci: dict = None,
                      cykle_sieci_duze: dict = None, cykle_punktow: dict = None,
                      miesiecy: int = 3, baza: PunktWizyty = None,
                      offline=False, od_daty: datetime.date = None,
                      postep_cb=None) -> dict:
    """PLANER CYKLICZNY (rotacja).

    Każdy punkt odwiedzany jest POWTARZALNIE — co X tygodni, a nie raz.
    Tak wygląda realna praca przedstawiciela: Biedronki co 2 tygodnie,
    Żabki co 4 itd.

    Jak działa:
      • każdy punkt ma termin następnej wizyty (na starcie: pierwszy dzień),
      • każdego dnia roboczego bierzemy punkty, którym termin już minął,
        i układamy z nich trasę metodą najbliższego sąsiada (limit 8h),
      • po odwiedzeniu punkt dostaje nowy termin: dziś + jego cykl.

    Dzięki temu plan sam się balansuje: punkty niedawno odwiedzone czekają,
    a te zaległe mają pierwszeństwo w kolejnych dniach.

    cykl_domyslny  — co ile tygodni odwiedzać punkt (gdy sieć nie ma własnego)
    cykle_sieci    — słownik {nazwa_sieci: tygodnie}, np. {"Biedronka": 2}
    miesiecy       — na ile miesięcy w przód generujemy cykl
    """
    cykle_sieci = cykle_sieci or {}
    cykle_sieci_duze = cykle_sieci_duze or {}
    cykle_punktow = cykle_punktow or {}
    z_pozycja = [p for p in punkty if p.lat is not None and p.lng is not None]
    bez_pozycji = [p for p in punkty if p.lat is None or p.lng is None]

    if not z_pozycja:
        return {"dni": [], "miesiace": [], "liczba_miesiecy": 0,
                "bez_pozycji": bez_pozycji, "nierozplanowane": [],
                "suma_km": 0.0, "suma_wizyt": 0, "rok": rok, "miesiac": miesiac,
                "cykliczny": True}

    if baza is None or baza.lat is None:
        sx = sum(p.lat for p in z_pozycja) / len(z_pozycja)
        sy = sum(p.lng for p in z_pozycja) / len(z_pozycja)
        baza = PunktWizyty("Środek trasy", "", lat=sx, lng=sy)

    def cykl_punktu(p) -> int:
        """Ile tygodni między wizytami — wg hierarchii reguł."""
        return cykl_dla_punktu(p, cykl_domyslny, cykle_sieci,
                               cykle_sieci_duze, cykle_punktow)

    # parametry planowania z ustawień użytkownika
    UP = ustawienia_planowania()
    LIMIT = UP["limit_minut"]; CZAS_W = UP["czas_wizyty"]
    PREDK = UP["predkosc"];    POWROT = UP["powrot"]

    # zbierz dni robocze w horyzoncie
    dni_robocze = []
    cur_r, cur_m = rok, miesiac
    for _ in range(max(1, miesiecy)):
        dni_robocze.extend(pobierz_dni_robocze(cur_r, cur_m))
        cur_m += 1
        if cur_m > 12:
            cur_m = 1; cur_r += 1
    if od_daty:
        dni_robocze = [d for d in dni_robocze if d >= od_daty]
    dni_robocze.sort()
    if not dni_robocze:
        return {"dni": [], "miesiace": [], "liczba_miesiecy": 0,
                "bez_pozycji": bez_pozycji, "nierozplanowane": [],
                "suma_km": 0.0, "suma_wizyt": 0, "rok": rok, "miesiac": miesiac,
                "cykliczny": True}

    start = dni_robocze[0]
    # termin następnej wizyty dla każdego punktu (na starcie: wszystkie zaległe)
    termin = {id(p): start for p in z_pozycja}

    dni_plan = []
    for nr_dnia, data in enumerate(dni_robocze):
        if postep_cb and nr_dnia % 5 == 0:
            postep_cb(f"Układanie cyklu ({nr_dnia+1}/{len(dni_robocze)})...",
                      (nr_dnia + 1) / len(dni_robocze))
        # punkty, którym termin już minął
        nalezne = [p for p in z_pozycja if termin[id(p)] <= data]
        if not nalezne:
            continue
        dzien = DzienPlanu(data)
        czas = 0.0; km_dnia = 0.0
        pozycja = baza
        dostepne = list(nalezne)
        while dostepne:
            najbl = None; najbl_km = None
            for p in dostepne:
                d = _dyst_prosty(pozycja, p)
                if najbl_km is None or d < najbl_km:
                    najbl_km = d; najbl = p
            czas_do = _czas_przejazdu_min(najbl_km, PREDK)
            rezerwa = _czas_przejazdu_min(_dyst_prosty(najbl, baza), PREDK) if POWROT else 0.0
            if czas + czas_do + CZAS_W + rezerwa > LIMIT and dzien.wizyty:
                break                      # dzień pełny
            dzien.wizyty.append(najbl)
            czas += czas_do + CZAS_W
            km_dnia += najbl_km
            pozycja = najbl
            dostepne.remove(najbl)
            # następna wizyta w tym punkcie za X tygodni
            termin[id(najbl)] = data + datetime.timedelta(weeks=cykl_punktu(najbl))
        if POWROT and dzien.wizyty:
            km_pow = _dyst_prosty(pozycja, baza)
            km_dnia += km_pow
            czas += _czas_przejazdu_min(km_pow, PREDK)
        dzien.km = round(km_dnia, 1)
        dzien.minuty = round(czas, 0)
        if dzien.wizyty:
            dni_plan.append(dzien)

    # grupowanie miesięczne
    miesiace_plan = []
    for d in dni_plan:
        klucz = (d.data.year, d.data.month)
        if not miesiace_plan or (miesiace_plan[-1]["rok"], miesiace_plan[-1]["miesiac"]) != klucz:
            miesiace_plan.append({"rok": d.data.year, "miesiac": d.data.month,
                                  "dni": [], "suma_km": 0.0, "suma_wizyt": 0})
        miesiace_plan[-1]["dni"].append(d)
    for m in miesiace_plan:
        m["suma_km"] = round(sum(x.km for x in m["dni"]), 1)
        m["suma_wizyt"] = sum(len(x.wizyty) for x in m["dni"])

    # punkty, które ani razu nie trafiły do planu (np. skrajnie oddalone)
    odwiedzone_ids = set()
    for d in dni_plan:
        for w in d.wizyty:
            odwiedzone_ids.add(id(w))
    nigdy = [p for p in z_pozycja if id(p) not in odwiedzone_ids]

    return {
        "dni": dni_plan,
        "miesiace": miesiace_plan,
        "liczba_miesiecy": len(miesiace_plan),
        "bez_pozycji": bez_pozycji,
        "nierozplanowane": nigdy,
        "suma_km": round(sum(d.km for d in dni_plan), 1),
        "suma_wizyt": sum(len(d.wizyty) for d in dni_plan),
        "rok": rok, "miesiac": miesiac,
        "cykliczny": True,
        "cykl_domyslny": cykl_domyslny,
        "cykle_sieci": dict(cykle_sieci),
        "cykle_sieci_duze": dict(cykle_sieci_duze),
        "cykle_punktow": dict(cykle_punktow),
    }

def zalegle_wizyty(plan: dict) -> list:
    """Zwraca listę (data, punkt) wizyt z MINIONYCH dni, których nie odhaczono.
    To one 'wypadły' z planu — trzeba je przenieść na kolejne dni."""
    if not plan:
        return []
    dzis = datetime.date.today()
    out = []
    for d in plan.get("dni", []):
        if d.data < dzis:
            for w in d.wizyty:
                if not czy_odwiedzona(d.data, w.adres or w.nazwa):
                    out.append((d.data, w))
    return out

def przeplanuj_zalegle(plan: dict, baza: PunktWizyty = None, offline=False) -> dict:
    """Przenosi niezrealizowane wizyty na kolejne dni robocze.

    Zasady:
      • HISTORIA JEST NIETYKALNA — dni minione zachowują tylko te wizyty, które
        faktycznie odhaczono (z ich pieczątkami i notatkami). Nic nie znika
        i nic nie jest dopisywane wstecz.
      • Wszystkie wizyty nieodhaczone (zaległe z przeszłości + przyszłe)
        układane są od nowa, poczynając od DZIŚ.
    """
    if not plan:
        return plan
    dzis = datetime.date.today()

    # 1) historia: minione dni, tylko odhaczone wizyty
    historia = []
    for d in plan.get("dni", []):
        if d.data < dzis:
            zrobione = [w for w in d.wizyty if czy_odwiedzona(d.data, w.adres or w.nazwa)]
            if zrobione:
                nd = DzienPlanu(d.data)
                nd.wizyty = zrobione
                nd.km = d.km; nd.minuty = d.minuty
                historia.append(nd)

    # 2) do przeplanowania: wszystko, co nieodhaczone (przeszłe i przyszłe)
    do_zaplanowania = []
    for d in plan.get("dni", []):
        for w in d.wizyty:
            if not czy_odwiedzona(d.data, w.adres or w.nazwa):
                do_zaplanowania.append(w)
    # dorzuć te, które wcześniej się nie zmieściły
    do_zaplanowania.extend(plan.get("nierozplanowane", []))

    if not do_zaplanowania:
        return plan     # nie ma czego przenosić

    if plan.get("cykliczny"):
        # PLAN CYKLICZNY — punkty się powtarzają, więc nie przeplanowujemy
        # pojedynczych wystąpień, tylko generujemy cykl od nowa (od dziś)
        # na unikalnych punktach. Historia zostaje nietknięta.
        unikalne = {}
        for w in do_zaplanowania:
            klucz = (w.adres or w.nazwa).strip().lower()
            if klucz not in unikalne:
                unikalne[klucz] = w
        nowy = planuj_cyklicznie(
            list(unikalne.values()), dzis.year, dzis.month,
            cykl_domyslny=int(plan.get("cykl_domyslny", 4) or 4),
            cykle_sieci=plan.get("cykle_sieci", {}) or {},
            cykle_sieci_duze=plan.get("cykle_sieci_duze", {}) or {},
            cykle_punktow=plan.get("cykle_punktow", {}) or {},
            miesiecy=max(1, plan.get("liczba_miesiecy", 3) or 3),
            baza=baza, offline=offline, od_daty=dzis)
    else:
        nowy = planuj_wizyty(do_zaplanowania, dzis.year, dzis.month,
                             baza=baza, offline=offline, od_daty=dzis)

    # 3) scal: historia + nowe dni
    wszystkie = historia + nowy.get("dni", [])
    wszystkie.sort(key=lambda d: d.data)

    # przebuduj grupowanie miesięczne
    miesiace = []
    for d in wszystkie:
        klucz = (d.data.year, d.data.month)
        if not miesiace or (miesiace[-1]["rok"], miesiace[-1]["miesiac"]) != klucz:
            miesiace.append({"rok": d.data.year, "miesiac": d.data.month,
                             "dni": [], "suma_km": 0.0, "suma_wizyt": 0})
        miesiace[-1]["dni"].append(d)
    for m in miesiace:
        m["suma_km"] = round(sum(x.km for x in m["dni"]), 1)
        m["suma_wizyt"] = sum(len(x.wizyty) for x in m["dni"])

    return {
        "dni": wszystkie, "miesiace": miesiace, "liczba_miesiecy": len(miesiace),
        "bez_pozycji": plan.get("bez_pozycji", []),
        "nierozplanowane": nowy.get("nierozplanowane", []),
        "suma_km": round(sum(d.km for d in wszystkie), 1),
        "suma_wizyt": sum(len(d.wizyty) for d in wszystkie),
        "rok": plan.get("rok"), "miesiac": plan.get("miesiac"),
        "cykliczny": bool(plan.get("cykliczny")),
        "cykl_domyslny": plan.get("cykl_domyslny", 4),
        "cykle_sieci": plan.get("cykle_sieci", {}) or {},
        "adres_bazy": plan.get("adres_bazy", ""),
    }

def generuj_mape_planu_html(plan: dict, folder: str, is_dark: bool = True) -> str:
    """Tworzy plik HTML z podglądem planu wizyt — każdy dzień jako karta z
    trasą i przyciskiem 'Otwórz w Google Maps'. Zwraca ścieżkę pliku."""
    bg = "#0B1320" if is_dark else "#F1F5F9"
    txt = "#F8FAFC" if is_dark else "#0F172A"
    karta = "rgba(16,25,43,0.85)" if is_dark else "#FFFFFF"
    ramka = "rgba(0,240,255,0.3)" if is_dark else "rgba(13,148,136,0.3)"
    tytul_c = "#00F0FF" if is_dark else "#0D9488"
    mut = "#94A3B8" if is_dark else "#475569"
    btn_bg = "linear-gradient(to right,#00F0FF,#00E4A1)" if is_dark else "#0D9488"
    btn_txt = "#04121A" if is_dark else "#FFFFFF"

    mies_pl = ["","styczeń","luty","marzec","kwiecień","maj","czerwiec","lipiec",
               "sierpień","wrzesień","październik","listopad","grudzień"]
    naglo_mies = f"{mies_pl[plan['miesiac']].capitalize()} {plan['rok']}"

    html = f"""<!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8">
<title>Plan Wizyt — {naglo_mies}</title><style>
body {{ font-family:'Segoe UI',sans-serif; background:{bg}; color:{txt}; padding:24px; }}
.container {{ max-width:820px; margin:0 auto; }}
h1 {{ color:{tytul_c}; text-align:center; margin-bottom:4px; }}
.sub {{ text-align:center; color:{mut}; margin-bottom:24px; }}
.day {{ background:{karta}; border:1px solid {ramka}; border-radius:10px; padding:16px 20px; margin-bottom:14px; }}
.day-t {{ font-size:15px; font-weight:bold; margin-bottom:6px; }}
.meta {{ font-size:12px; color:{mut}; margin-bottom:10px; }}
.route {{ font-size:13px; color:{mut}; line-height:1.6; margin-bottom:12px; }}
.btn {{ display:inline-block; background:{btn_bg}; color:{btn_txt}; padding:8px 16px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:13px; }}
</style></head><body><div class="container">
<h1>Plan Wizyt</h1><div class="sub">{naglo_mies} &nbsp;•&nbsp; {plan['suma_wizyt']} wizyt &nbsp;•&nbsp; {plan['suma_km']:.0f} km</div>
"""
    dni_pl = ["Poniedziałek","Wtorek","Środa","Czwartek","Piątek","Sobota","Niedziela"]
    for d in plan["dni"]:
        if not d.wizyty:
            continue
        etykiety = []; url_punkty = []
        for w in d.wizyty:
            ety = w.nazwa or w.miasto
            etykiety.append(ety)
            cel = w.adres if w.adres else f"{w.miasto}, Polska"
            url_punkty.append(urllib.parse.quote(cel, safe=""))   # „5/58" to JEDEN punkt
        h = int(d.minuty // 60); m = int(d.minuty % 60)
        dzien_tyg = dni_pl[d.data.weekday()]
        html += f"""<div class="day"><div class="day-t">{dzien_tyg}, {d.data.strftime('%d.%m.%Y')}</div>
<div class="meta">{len(d.wizyty)} wizyt • {d.km:.0f} km • ok. {h}h {m}min</div>
<div class="route">{' ➔ '.join(etykiety)}</div>
<a class="btn" target="_blank" href="https://www.google.com/maps/dir/{'/'.join(url_punkty)}">🗺 Otwórz w Google Maps</a></div>
"""
    html += "</div></body></html>"
    sciezka = os.path.join(folder, "Plan_Wizyt_Mapa.html")
    with open(sciezka, "w", encoding="utf-8") as f:
        f.write(html)
    return sciezka

def waliduj_pesel(pesel: str) -> bool:
    if not re.match(r"^\d{11}$", pesel): return False
    return (10 - sum(int(pesel[i]) * w for i, w in enumerate([1, 3, 7, 9, 1, 3, 7, 9, 1, 3])) % 10) % 10 == int(pesel[10])

def _czy_znana_miejscowosc(nazwa: str) -> bool:
    """Czy nazwa występuje w naszej bazie miejscowości? Jeśli tak, adres bez
    przedrostka jest adresem wiejskim i nie trzeba o nic pytać."""
    try:
        cel = str(nazwa).strip().lower()
        if not cel:
            return False
        for _lista in MIASTA_RAW.values():
            for _m in _lista:
                if str(_m.get("n", "")).strip().lower() == cel:
                    return True
        for _n in MIASTA_DUZE:
            if str(_n).strip().lower() == cel:
                return True
    except Exception:
        pass
    return False

def _klasyfikuj_adres(nazwa: str) -> str:
    """Zwraca typ członu po 'ul.':
      'ulica'          — pewna ulica (nie pytamy użytkownika),
      'wies'           — pewna miejscowość (nie pytamy),
      'niejednoznaczne'— nie da się rozstrzygnąć z nazwy → zapytamy użytkownika.
    Nie da się w 100% odróżnić 'Zielona Ścieżka' (ulica) od 'Sarnowa Góra'
    (wieś) — obie to dwa słowa z wielkich liter. Dlatego takie przypadki
    oznaczamy jako niejednoznaczne i pytamy użytkownika."""
    n = nazwa.strip()
    if not n:
        return 'ulica'
    # Nazwa jest w bazie miejscowości → adres wiejski, bez pytania użytkownika.
    if _czy_znana_miejscowosc(n):
        return 'wies'
    slowa = n.split()
    low = [s.lower().strip(".") for s in slowa]

    # 1) PEWNA ULICA — typowe słowa uliczne albo patron z inicjałami/cyframi
    ulica_slowa = {"aleja", "aleje", "rondo", "plac", "osiedle", "os", "skwer", "bulwar"}
    if any(s in ulica_slowa for s in low):
        return 'ulica'
    if any(s in {"i", "im", "gen", "ks", "sw", "św", "dr", "mjr", "kpt", "płk", "por"} for s in low):
        return 'ulica'
    if any(any(ch.isdigit() for ch in s) for s in slowa):   # "3 Maja", "1000-lecia"
        return 'ulica'

    # Częste patronki/patroni ulic (imiona, tytuły) — jeśli pierwszy człon to
    # popularne imię, to niemal na pewno ULICA (Jana Pawła, Marii Curie itd.).
    imiona_ulic = {"jana", "marii", "adama", "stefana", "józefa", "jozefa",
                   "tadeusza", "władysława", "wladyslawa", "kazimierza",
                   "mikołaja", "mikolaja", "henryka", "stanisława", "stanislawa",
                   "bolesława", "boleslawa", "fryderyka", "ignacego", "romualda",
                   "księdza", "ksiedza", "świętego", "swietego", "generała", "generala",
                   "marszałka", "marszalka", "papieża", "papieza", "króla", "krola"}
    if low[0] in imiona_ulic:
        return 'ulica'

    # 2) Jednoczłonowa nazwa (Marszałkowska, Kowalskiego, Krzyżówki) — traktujemy
    #    jako ULICA (najczęstszy przypadek miejski). Jeśli to jednak wieś
    #    jednoczłonowa, użytkownik użyje przełącznika (rzadki przypadek).
    if len(slowa) == 1:
        return 'ulica'

    # 3) Dwu-/trzyczłonowa, każde słowo z wielkiej litery — NIEJEDNOZNACZNE
    #    (Sarnowa Góra = wieś, Zielona Ścieżka = ulica). Pytamy użytkownika.
    if 2 <= len(slowa) <= 3 and all(s[0].isupper() for s in slowa if s):
        return 'niejednoznaczne'

    # 4) Wszystko inne (np. z małą literą w środku: "Jana Pawła") — ULICA
    return 'ulica'

def waliduj_adres(adres: str, wymus_typ: str = None) -> dict:
    """wymus_typ: None (auto), 'ulica' lub 'wies' — decyzja użytkownika dla
    adresów niejednoznacznych. Gdy typ jest niejednoznaczny i nie podano
    wymus_typ, zwracamy flagę 'niejednoznaczne'=True, żeby formularz zapytał."""
    # PRZEDROSTEK JEST OPCJONALNY. Adresy wiejskie zapisuje się bez "ul." —
    # np. "Dębowa Wola 12, 26-660 Jedlińsk". Wcześniej taki adres był odrzucany,
    # a użytkownik był zmuszany dopisywać "ul." przed nazwą wsi.
    m = re.match(
        r"^(?:(ul\.|al\.|pl\.|ulica|aleja|plac|os\.|osiedle)\s+)?"   # opcjonalny przedrostek
        r"(.+?)\s+"                                                   # nazwa (ulicy albo wsi)
        r"(\d+[a-zA-Z]?(?:\s*[/\\]\s*\d+[a-zA-Z]?)?)"                 # numer, także 12/3 lub 12A
        r"[,\s]+\s*(\d{2}-\d{3})\s+(.+)$",                           # kod pocztowy + poczta
        adres.strip(), re.IGNORECASE)
    if not m:
        raise ValueError(
            "Błędny format adresu!\n\nPodaj adres wg jednego ze wzorów:\n"
            "  Kowalczyka 12, 03-193 Warszawa\n"
            "  ul. Kowalczyka 12, 03-193 Warszawa\n"
            "  Dębowa Wola 12, 26-660 Jedlińsk        (adres wiejski)\n\n"
            "Wymagany jest numer domu, kod pocztowy i miejscowość.")
    prefiks_raw = (m.group(1) or "").lower()
    # ujednolicamy zapis przedrostka; brak przedrostka = pusty napis
    prefiks = {"ulica": "ul.", "aleja": "al.", "plac": "pl.",
               "osiedle": "os.", "os.": "os.", "ul.": "ul.",
               "al.": "al.", "pl.": "pl."}.get(prefiks_raw, prefiks_raw)
    nazwa = ' '.join(w.capitalize() for w in m.group(2).split())   # "Sarnowa Góra" lub "Kowalskiego"
    numer = m.group(3).strip()
    kod = m.group(4).strip()
    poczta = ' '.join(w.capitalize() for w in m.group(5).split())  # "Sońsk" / "Warszawa"
    # Jawny przedrostek to rozstrzygnięcie użytkownika — nie pytamy o typ.
    if prefiks and not wymus_typ:
        wymus_typ = 'ulica'

    typ = _klasyfikuj_adres(nazwa)
    niejednoznaczne = False
    if wymus_typ in ('ulica', 'wies'):
        typ = wymus_typ                    # użytkownik rozstrzygnął
    elif typ == 'niejednoznaczne':
        niejednoznaczne = True
        typ = 'ulica'                      # tymczasowo, formularz i tak zapyta

    to_wies = (typ == 'wies')

    if to_wies:
        # Miejscowością (bazą, startem/metą, celem geocodingu) jest nazwa wsi,
        # a NIE poczta. Poczta to tylko urząd, do którego wieś przynależy.
        baza_miasto = nazwa
        adres_pdf = f"{nazwa} {numer}, {kod} {poczta}"
        adres_geo = f"{nazwa}, {kod} {poczta}"
    else:
        # Klasyczny adres miejski z ulicą — start/meta to MIEJSCOWOŚĆ (poczta).
        baza_miasto = poczta
        _pre = (prefiks + " ") if prefiks else ""
        adres_pdf = f"{_pre}{nazwa} {numer}, {kod} {poczta}"
        # DO MAPY IDZIE NUMER BUDYNKU, BEZ NUMERU LOKALU. „Zamiejska 5/58"
        # na mapie nie istnieje — serwer albo nie znajdował nic, albo czytał
        # „58" jako osobny punkt i trasa dostawała nadmiarowy przystanek.
        _numer_domu = re.split(r"[/\\]", numer)[0].strip() or numer
        adres_geo = f"{_pre}{nazwa} {_numer_domu}, {kod} {poczta}"

    return {
        'adres_caly': adres_pdf,        # to trafia do PDF (start/meta, nagłówek)
        'adres_geo': adres_geo,         # to idzie do geocodingu (wyznaczenie bazy)
        'kod_pocztowy': kod,
        'baza_miasto': baza_miasto,     # start/meta trasy i to, co liczy silnik
        'to_wies': to_wies,
        'niejednoznaczne': niejednoznaczne,   # True → formularz pyta użytkownika
        'nazwa_do_pytania': nazwa,      # co pokazać w pytaniu
    }

def waliduj_miesiac(s: str) -> Tuple[int, int]:
    if not re.match(r"^\d{2}\.\d{4}$", s.strip()): raise ValueError("Format daty: MM.YYYY (np. 06.2026)")
    return map(int, s.strip().split('.'))

def waliduj_kwote(s: str) -> float:
    try: k = float(s.replace(' ', '').replace(',', '.'))
    except ValueError: raise ValueError("Kwota nieprawidłowa.")
    if k < MIN_KWOTA: raise ValueError(f"Min kwota to {MIN_KWOTA:.0f} PLN.")
    return k

def _bez_numeru_lokalu(adres: str) -> str:
    """„Zamiejska 5/58" → „Zamiejska 5". Numer lokalu jest poza mapą: serwer
    albo nie znajduje takiego adresu, albo czyta „58" jako osobny punkt —
    stąd brał się nadmiarowy przystanek. Dla mapy liczy się numer BUDYNKU."""
    return re.sub(r"(\d+\s*[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]?)\s*[/\\]\s*\d+\s*[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]?",
                  r"\1", str(adres or "")).strip()

def _warianty_geo(adres_caly: str, miasto: str):
    """Kolejne zapytania do serwera — od najdokładniejszego do miejscowości.
    Bez powtórek, żeby ten sam napis nie poszedł do serwera dwa razy."""
    warianty = []
    for w in (adres_caly, _bez_numeru_lokalu(adres_caly), miasto):
        w = " ".join(str(w or "").split())
        if w and w not in warianty:
            warianty.append(w)
    return warianty

def pobierz_coords(adres_caly: str, miasto: str, woj: str, zapisz_cache=True) -> Tuple[float, float]:
    """Współrzędne adresu. Wynik zapamiętujemy trwale — także odpowiedź
    „nie znam takiego adresu" — więc o ten sam adres nie pytamy dwa razy."""
    global _geo_cache
    klucz = _klucz_geo(adres_caly)
    if klucz in _geo_cache: return tuple(_geo_cache[klucz])
    stary = str(adres_caly or "").lower().strip()      # klucz sprzed ujednolicenia
    if stary in _geo_cache:
        _geo_cache[klucz] = _geo_cache[stary]
        return tuple(_geo_cache[klucz])
    if _geo_brak_znany(klucz):
        return _wspolrzedne_zastepcze(miasto, woj)
    odpowiedz_serwera = False
    for zapytanie in _warianty_geo(adres_caly, miasto):
        try:
            q = urllib.parse.quote(f"{zapytanie}, Polska", safe="")
            req = urllib.request.Request(f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1", headers={'User-Agent': 'PMT/112'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read())
            odpowiedz_serwera = True
            if data:
                coords = (float(data[0]['lat']), float(data[0]['lon']))
                _geo_cache[klucz] = list(coords)
                # Zapis cache TYLKO gdy zapisz_cache=True. Przy masowym
                # geokodowaniu (setki punktów) zapisujemy raz na końcu —
                # inaczej zapis całego pliku przy każdym punkcie zawiesza program.
                if zapisz_cache:
                    zapisz_geo_cache()
                return coords
        except Exception: continue
    # Serwer odpowiedział i nie zna tego adresu → zapamiętujemy to na stałe.
    # Awaria sieci (żadnej odpowiedzi) zostaje tylko na czas tej sesji.
    _geo_pytane.add(klucz)
    if odpowiedz_serwera:
        _zapamietaj_geo_brak(klucz)
    return _wspolrzedne_zastepcze(miasto, woj)

def _wspolrzedne_zastepcze(miasto: str, woj: str) -> Tuple[float, float]:
    """Gdy geokodowanie zawiodło: najpierw miasto z bazy offline programu,
    dopiero potem stolica województwa. Wcześniej brak internetu (albo
    adres, którego serwer nie zna) cofał bazę prosto do stolicy — pracownik
    z Radomia dostawał dokumenty z trasami liczonymi z Warszawy, choć Radom
    leży w bazie miast programu. Ta sama kolejność, co w podglądzie
    (nowy_wyglad.wspolrzedne_bazy)."""
    try:
        z_bazy = coords_z_miasta(miasto)
    except Exception:
        z_bazy = None
    if z_bazy:
        return float(z_bazy[0]), float(z_bazy[1])
    return STOLICE.get(woj, (52.23, 21.01))

def zapisz_geo_cache(sciezka=None):
    """Zapisuje pamięć geolokalizacji na dysk (po masowym geokodowaniu).
    Zapis atomowy: plik tymczasowy → podmiana, poprzedni ląduje w .bak."""
    global _geo_cache
    sciezka = sciezka or GEO_CACHE
    try:
        tmp = sciezka + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_geo_cache, f, ensure_ascii=False, indent=2)
        try:
            if os.path.exists(sciezka):
                os.replace(sciezka, sciezka + ".bak")
        except Exception:
            pass
        os.replace(tmp, sciezka)
    except Exception:
        pass

WYJATKI_WOJEWODZTW = {
    "19-3": "warmińsko-mazurskie", "19-4": "warmińsko-mazurskie",   # Ełk, Olecko
    "19-5": "warmińsko-mazurskie",                                  # Gołdap
    "26-3": "łódzkie",                                              # Opoczno, Drzewica
    "26-4": "mazowieckie", "26-5": "mazowieckie",                   # Przysucha, Szydłowiec
    "26-6": "mazowieckie", "26-7": "mazowieckie",                   # Radom, Zwoleń
    "26-8": "mazowieckie", "26-9": "mazowieckie",                   # Białobrzegi, Kozienice
    "27-1": "mazowieckie", "27-3": "mazowieckie",                   # Iłża, Lipsko
    "34-3": "śląskie",                                              # Żywiec
    "76-2": "pomorskie",                                            # Słupsk, Ustka
    "77-1": "pomorskie", "77-2": "pomorskie", "77-3": "pomorskie",  # Bytów, Miastko, Człuchów
    "77-4": "wielkopolskie",                                        # Złotów
    "82-3": "warmińsko-mazurskie",                                  # Elbląg, Pasłęk
    "89-4": "pomorskie", "89-6": "pomorskie",                       # Chojnice, Czersk
}

def rozpoznaj_wojewodztwo(kod: str) -> str:
    kod = str(kod or "").strip()
    wyjatek = WYJATKI_WOJEWODZTW.get(kod[:4])
    if wyjatek: return wyjatek
    try: p = int(kod[:2])
    except: return "mazowieckie"
    if p <= 9: return "mazowieckie"
    if p <= 14: return "warmińsko-mazurskie"
    if p <= 19: return "podlaskie"
    if p <= 24: return "lubelskie"
    if p <= 29: return "świętokrzyskie"
    if p <= 34: return "małopolskie"
    if p <= 39: return "podkarpackie"
    if p <= 44: return "śląskie"
    if p <= 49: return "opolskie"
    if p <= 59: return "dolnośląskie"
    if p <= 64: return "wielkopolskie"
    if p <= 69: return "lubuskie"
    if p <= 78: return "zachodniopomorskie"
    if p <= 84: return "pomorskie"
    if p <= 89: return "kujawsko-pomorskie"
    return "łódzkie"

def szacuj_delegacje(kwota: float, stawka: float, dni_robocze: int) -> dict:
    """Szybki szacunek BEZ uruchamiania pełnego algorytmu — zasila panel
    podglądu na żywo. Ten sam model co silnik: najpierw dokumenty (kwota przez
    sufit dokumentu), potem dni wewnątrz dokumentu (kwota dokumentu przez
    pojemność doby), nie realny dobór miast."""
    if stawka <= 0 or dni_robocze <= 0:
        return {"km": 0, "dni_wyjazdowe": 0, "km_dzien": 0, "dokumenty": 0}
    km_real = kwota / stawka
    dokumenty = ile_dokumentow(kwota)
    sufit_dnia = max(pojemnosc_dnia_zl(POSTOJE_TYPOWE, stawka), MIN_KWOTA)
    dni_w_dokumencie = max(1, math.ceil((kwota / dokumenty - 0.005) / sufit_dnia))
    dni_wyjazdowe = max(1, min(dni_robocze, dokumenty * dni_w_dokumencie))
    km_dzien = km_real / dni_wyjazdowe if dni_wyjazdowe else 0
    return {
        "km": round(km_real),
        "dni_wyjazdowe": dni_wyjazdowe,
        "km_dzien": round(km_dzien),
        "dokumenty": dokumenty,
    }

def optymalizuj_tsp(trasa: List[Miasto], baza_lat, baza_lng) -> List[Miasto]:
    if len(trasa) <= 1: return trasa
    najlepsza = trasa
    min_dyst = float('inf')
    for perm in itertools.permutations(trasa):
        d = oblicz_dystans(baza_lat, baza_lng, perm[0].lat, perm[0].lng)
        for i in range(len(perm) - 1): d += oblicz_dystans(perm[i].lat, perm[i].lng, perm[i+1].lat, perm[i+1].lng)
        d += oblicz_dystans(perm[-1].lat, perm[-1].lng, baza_lat, baza_lng)
        if d < min_dyst: min_dyst = d; najlepsza = list(perm)
    return najlepsza

def usun_duplikaty_nazw(lista: List[Miasto]) -> List[Miasto]:
    u = {}
    for m in lista:
        if m.n not in u: u[m.n] = m
    return list(u.values())

def przecina_aglomeracje(lat1, lng1, lat2, lng2, baza_lat=None, baza_lng=None):
    """Sprawdza czy odcinek trasy przechodzi przez aglomerację.
    Aglomeracje w promieniu 30 km od bazy użytkownika są POMIJANE —
    mieszkaniec stolicy województwa musi móc z niej wyjechać i do niej wrócić."""
    for w_lat, w_lng in AGLOMERACJE_LISTA:
        if baza_lat is not None and oblicz_dystans(baza_lat, baza_lng, w_lat, w_lng) < 30.0:
            continue  # macierzysta aglomeracja — nie blokuje tras z/do domu
        if dystans_odcinek_punkt(lat1, lng1, lat2, lng2, w_lat, w_lng) < 25.0: return True
    return False

def miasto_w_obcej_aglomeracji(baza_lat, baza_lng, m_lat, m_lng):
    for w_lat, w_lng in AGLOMERACJE_LISTA:
        if oblicz_dystans(m_lat, m_lng, w_lat, w_lng) < 40.0:
            if oblicz_dystans(baza_lat, baza_lng, w_lat, w_lng) >= 45.0: return True
    return False

class ListaTras(list):
    """Lista dni tras z dodatkowymi metadanymi o pokryciu kwoty. Dziedziczy po
    list, więc działa wszędzie jak zwykła lista — po prostu niesie też info,
    czy realnymi trasami udało się pokryć żądaną kwotę."""
    kwota_docelowa = 0.0
    kwota_osiagnieta = 0.0
    kwota_niepelna = False
    brak_dni = False

def generuj_trasy(kwota_calkowita, baza_nazwa, baza_lat, baza_lng, woj, dni_robocze, pesel, stawka=None, postep_cb=None, dzien_cb=None) -> List[DzienTrasy]:
    if stawka is None: stawka = STAWKA_ZA_KM
    # jedno rozliczenie = jeden stan źródła odległości
    zeruj_zrodlo_odleglosci()
    seed_val = int(pesel[-6:]) if pesel.isdigit() and len(pesel) >= 6 else 42
    rng = random.Random(seed_val)
    baza = zaladuj_baze(baza_lat, baza_lng)
    
    ostatnie_uzycie = {} 
    finalne_dni = []
    
    cel_calkowity_dystans = kwota_calkowita / stawka
    aktualny_dystans_linii = 0.0

    sasiednie = [w for w in SASIEDZI_WOJ.get(woj, []) if w != woj]
    zablokowane_sektory = pobierz_zablokowane_sektory(baza_lat, baza_lng, woj)
    dozwolone_sektory = [s for s in SEKTORY_KOLEJNOSC if s not in zablokowane_sektory]
    if not dozwolone_sektory: dozwolone_sektory = SEKTORY_KOLEJNOSC[:]

    # ADAPTACYJNY PROMIEŃ PĘTLI — bazowo 70 km, ale w rzadko zaludnionych
    # rejonach (peryferia, przygranicze) miast bywa za mało, więc rozszerzamy
    # promień, żeby dało się w ogóle ułożyć trasę z min. 3 postojami.
    _wszystkie_okoliczne = []
    for _w in [woj] + sasiednie:
        for _m in baza.get(_w, []):
            _wszystkie_okoliczne.append(oblicz_dystans(baza_lat, baza_lng, _m.lat, _m.lng))
    _blisko_70 = sum(1 for d in _wszystkie_okoliczne if d <= 70.0)
    if _blisko_70 >= 25:
        promien_petli = 70.0
    elif _blisko_70 >= 15:
        promien_petli = 95.0
    elif _blisko_70 >= 8:
        promien_petli = 120.0
    else:
        promien_petli = 150.0

    # BAZA PRZYGRANICZNA: gdy blokada sektorów (kierunki "za granicę") zostawia
    # za mało miast w zasięgu, odblokowujemy wszystkie sektory. Inaczej pracownik
    # z rogu kraju (Suwałki, Ustrzyki, Kołobrzeg) nie dostałby żadnej trasy.
    _miast_w_dozwolonych = 0
    for _w in [woj] + sasiednie:
        for _m in baza.get(_w, []):
            if _m.sektor in dozwolone_sektory and oblicz_dystans(baza_lat, baza_lng, _m.lat, _m.lng) <= promien_petli:
                _miast_w_dozwolonych += 1
    if _miast_w_dozwolonych < 12:
        dozwolone_sektory = SEKTORY_KOLEJNOSC[:]   # odblokuj wszystkie kierunki

    # ADAPTACYJNY COOLDOWN — ile dni miasto "odpoczywa" zanim może się powtórzyć.
    # Domyślnie 35 dni (żadnych powtórek w miesiącu). Ale gdy dostępnych miast
    # jest za mało, by wypełnić wszystkie dni robocze bez powtórek, skracamy go —
    # inaczej silnik wygenerowałby za mało dni i naciągał kilometry, by trafić
    # w kwotę. Realnie merchandiser i tak odwiedza te same sklepy cyklicznie.
    _pula_szac = 0
    for _w in [woj] + sasiednie:
        for _m in baza.get(_w, []):
            if oblicz_dystans(baza_lat, baza_lng, _m.lat, _m.lng) <= promien_petli:
                _pula_szac += 1
    _dni_do_pokrycia = max(1, len(dni_robocze))
    # ile miast potrzeba: ~6 na dzień. Jeśli pula wystarcza na wszystkie dni → 35.
    if _pula_szac >= _dni_do_pokrycia * 6:
        cooldown_dni = 35
    elif _pula_szac >= _dni_do_pokrycia * 3:
        cooldown_dni = 14
    else:
        cooldown_dni = 8

    # === NAJPIERW DOKUMENTY, POTEM DNI ===
    # Sufit MAX_KWOTA_DOKUMENTU (986,34 zł) dotyczy JEDNEGO polecenia wyjazdu,
    # a jedno polecenie obejmuje kilka dni. Kolejność rachunku:
    #   1) ile dokumentów  → sufit z kwoty podzielonej przez sufit dokumentu,
    #   2) ile dni w dokumencie → kwota dokumentu podzielona przez pojemność
    #      doby (posiłek + jazda + postoje — pojemnosc_dnia_zl, ten sam rachunek
    #      co weryfikacja czasowa dnia niżej),
    #   3) dokument nie może przekroczyć liczby wierszy strony A4 — jeśli dni
    #      się na niej nie mieszczą, dokumentów musi być więcej.
    # Dzień planujemy na PEŁNĄ pojemność doby — tylko wtedy dni dzielą kwotę
    # dokumentu tak, żeby dokument dobijał do sufitu, a nie zostawał w połowie.
    # Gdy realne trasy wyjdą krótsze, pętla budowania dni niżej dokłada dni.
    _sufit_dnia_zl = max(pojemnosc_dnia_zl(POSTOJE_TYPOWE, stawka), MIN_KWOTA)
    _dni_z_wierszy = max(1, MAX_ETAPOW_DOKUMENTU // (POSTOJE_TYPOWE + 1))
    _dok_potrzeba = ile_dokumentow(kwota_calkowita)
    _dni_w_dokumencie = max(1, math.ceil((kwota_calkowita / _dok_potrzeba - 0.005) / _sufit_dnia_zl))
    if _dni_w_dokumencie > _dni_z_wierszy:
        _dni_w_dokumencie = _dni_z_wierszy
        _dok_potrzeba = max(_dok_potrzeba,
                            math.ceil((kwota_calkowita - 0.005)
                                      / (_dni_w_dokumencie * _sufit_dnia_zl)))
    _dni_z_planu = max(1, _dok_potrzeba * _dni_w_dokumencie)
    # Dolny próg trzech dni jak dotąd: przy małych kwotach silnik rozpisuje
    # kilka dni i zostawia najkrótszy (przycinanie niżej), bo pojedynczy długi
    # dzień nie zmieściłby się w kwocie bez ściskania odcinków poniżej drogi.
    _dni_potrzeba = max(3, _dni_z_planu)
    # Jeśli potrzeba więcej dni niż jest w miesiącu — bierzemy WSZYSTKIE dostępne
    # i sygnalizujemy, że kwota może się nie zmieścić (komunikat po generacji).
    _brak_dni_na_kwote = _dni_potrzeba > len(dni_robocze)
    _dni_potrzeba = min(len(dni_robocze), _dni_potrzeba)
    # ZAPAS DO WYBORU: gdy plan przewiduje więcej niż jeden dzień, rozpisujemy
    # dwa dni ponad plan. Przycinanie niżej zdejmuje NAJDŁUŻSZE dni, więc
    # w dokumentach zostają te krótsze — równiejsze i z zapasem godzin, dzięki
    # czemu kwota dobija co do grosza także tam, gdzie miejscowości są rzadko
    # rozsiane. Przy kwocie na jeden dzień zapasu nie ma: liczą się wtedy
    # same trzy dni progu, z których zostaje najkrótszy.
    _dni_budowane = min(len(dni_robocze), _dni_potrzeba + (2 if _dni_z_planu > 1 else 0))
    # Wybierz dni rozłożone równomiernie przez cały miesiąc (nie po kolei z początku).
    if _dni_potrzeba >= len(dni_robocze):
        dni_wybrane = list(range(len(dni_robocze)))
    else:
        krok = len(dni_robocze) / _dni_potrzeba
        dni_wybrane = sorted(set(int(i * krok) for i in range(_dni_potrzeba)))
        _i = 0
        while len(dni_wybrane) < _dni_potrzeba and _i < len(dni_robocze):
            if _i not in dni_wybrane: dni_wybrane.append(_i)
            _i += 1
        dni_wybrane = sorted(dni_wybrane)
    dni_wybrane_set = set(dni_wybrane)

    # Budujemy dni, celując w _dni_potrzeba UDANYCH dni. Zaczynamy od równomiernie
    # rozłożonego zestawu (dni_wybrane_set) dla ładnego pokrycia miesiąca, ale
    # jeśli któryś dzień się nie zbuduje, sięgamy po KOLEJNE wolne daty — dzięki
    # temu zawsze powstaje tyle dni, ile trzeba na budżet (o ile starczy dat).
    # Najpierw preferowane daty (równomierny rozkład), potem cała reszta jako zapas.
    kolejnosc_dni = [d for d in dni_wybrane] + [i for i in range(len(dni_robocze)) if i not in dni_wybrane_set]

    # POJEMNOŚĆ ZAMIAST SZTYWNEJ LICZBY DNI: gdy realne trasy wyjdą krótsze
    # od szacunku, dokładamy kolejne dni, aż pokryją zamówioną kwotę.
    _pojemnosc_km = 0.0
    _dni_nieudane = 0
    _dni_awaryjne = 0
    _cel_km_z_zapasem = cel_calkowity_dystans * 1.04

    def _pojemnosc_dnia(etapy):
        km = sum(e.d_line for e in etapy)
        postoje = sum((e.czas_w_sklepie or 0) for e in etapy) + PRZERWA_JEDZENIE_MIN
        wolne = LIMIT_CZASU_MINUTY - postoje
        if wolne <= 0 or km <= 0:
            return 0.0
        mozliwe = (wolne / 60.0) * SREDNIA_PREDKOSC
        # Po wyznaczeniu tras drogowych odcinki urosną z linii prostej do drogi
        # (TEST_MNOZNIK_TRASY), a dzień musi się zmieścić w dobie jeszcze przy
        # dolnym progu MNOZNIK_MIN. Dzień, który tego nie przejdzie, i tak
        # wypadnie przy przycinaniu — więc nie wnosi pojemności i silnik dokłada
        # w jego miejsce kolejny dzień.
        if mozliwe < km * TEST_MNOZNIK_TRASY * MNOZNIK_MIN:
            return 0.0
        # Ile dzień NAPRAWDĘ udźwignie: odcinki urosną z linii prostej do drogi
        # (TEST_MNOZNIK_TRASY) i najwyżej o sufit rozciągnięcia (MNOZNIK_MAX).
        # Dawne "km × 4" zakładało rozciąganie czterokrotne — przez to silnik
        # przestawał dokładać dni, choć kwoty nie dało się już wyjeździć.
        return min(mozliwe, km * TEST_MNOZNIK_TRASY * MNOZNIK_MAX)

    for _poz, numer_dnia in enumerate(kolejnosc_dni):
        if (len(finalne_dni) >= _dni_budowane
                and _pojemnosc_km >= _cel_km_z_zapasem):
            break            # dość dni ORAZ pojemności na całą kwotę
        data = dni_robocze[numer_dnia]
        # Mianownik liczony na bieżąco: gdy realne trasy wyjdą krótsze od
        # szacunku, silnik dokłada dni ponad _dni_potrzeba — pasek pokazywał
        # wtedy „Dzień 15/12".
        _ile_dni_pokaz = max(_dni_budowane, len(finalne_dni) + 1)
        if postep_cb: postep_cb(f"Klastrowanie GPS (Dzień {len(finalne_dni)+1}/{_ile_dni_pokaz})...", 0.30 + (_poz / max(len(kolejnosc_dni),1)) * 0.40)

        # W rzadkich rejonach (przygranicze) stare filtry "ucieczki od stolicy"
        # i "obcej aglomeracji" są zbyt restrykcyjne i zostawiają 0 miast.
        # Wykrywamy taki przypadek i wtedy je pomijamy.
        _rzadki_rejon = (promien_petli > 70)

        def dostepne_miasta(pula, wymus_ucieczke=True, spr_cooldown=True):
            dostepne = []
            for m in pula:
                if m.n.lower() == baza_nazwa.lower() or m.sieci < MIN_SIECI: continue
                if oblicz_dystans(baza_lat, baza_lng, m.lat, m.lng) < MIN_ODLEGLOSC_OD_BAZY:
                    continue          # nic „pod domem"
                if wymus_ucieczke and not _rzadki_rejon and not odsuwa_sie_od_stolicy(baza_lat, baza_lng, m.lat, m.lng, woj): continue
                if not _rzadki_rejon and miasto_w_obcej_aglomeracji(baza_lat, baza_lng, m.lat, m.lng): continue
                if spr_cooldown and m.n in ostatnie_uzycie and (data - ostatnie_uzycie[m.n]).days < cooldown_dni: continue

                d = oblicz_dystans(baza_lat, baza_lng, m.lat, m.lng) * TEST_MNOZNIK_TRASY
                # limit: dojazd do miasta i z powrotem musi się mieścić w dniu
                # (z zapasem na postoje). W rzadkim rejonie dajemy większy zapas.
                zapas = 60 if _rzadki_rejon else 90
                if (d * 2 / SREDNIA_PREDKOSC) * 60 + zapas <= LIMIT_CZASU_MINUTY:
                    if _rzadki_rejon or not przecina_aglomeracje(baza_lat, baza_lng, m.lat, m.lng, baza_lat, baza_lng):
                        dostepne.append(m)
            return dostepne

        czy_wlasne = (rng.random() <= PROCENT_WLASNE)
        def pobierz_kandydatow(ucieczka, spr_cd):
            kw = usun_duplikaty_nazw(dostepne_miasta(baza.get(woj, []), ucieczka, spr_cd))
            ko = usun_duplikaty_nazw([m for w in sasiednie for m in dostepne_miasta(baza.get(w, []), ucieczka, spr_cd)])
            if czy_wlasne and kw: return kw
            elif not czy_wlasne and ko: return ko
            elif kw: return kw
            elif ko: return ko
            return []

        kandydaci = pobierz_kandydatow(True, True)
        if not kandydaci: kandydaci = pobierz_kandydatow(False, True)
        # Gdy cooldown wyczerpał pulę miast (przy wielu dniach to naturalne),
        # NIE pomijamy dnia — próbujemy bez cooldownu. Realny merchandiser i tak
        # odwiedza te same sklepy cyklicznie. Priorytetem jest rozpisanie
        # WSZYSTKICH potrzebnych dni, żeby pokryć budżet realnymi trasami.
        if not kandydaci: kandydaci = pobierz_kandydatow(True, False)
        if not kandydaci: kandydaci = pobierz_kandydatow(False, False)
        if not kandydaci:
            # Brak kandydatów to NAJCZĘSTSZA przyczyna utraty dnia, a do 3.21.0
            # wychodziła z pętli, zanim licznik zdążył cokolwiek policzyć.
            # Przez to reguły nigdy się nie rozluźniały tam, gdzie było to
            # najbardziej potrzebne — w rejonach, w których filtry wycinają
            # prawie wszystko.
            _dni_nieudane += 1
            continue

        # DETERMINIZM: sortujemy kandydatów po nazwie, ZANIM losujemy z nich
        # trasę. Bez tego kolejność zależałaby od losowego haszowania tekstu
        # w Pythonie (inne przy każdym starcie programu), więc ten sam pracownik
        # dostawałby różne trasy przy każdym uruchomieniu — a bywało, że w
        # niektórych kolejnościach budowało się dużo mniej dni.
        kandydaci = sorted(kandydaci, key=lambda m: (m.n, round(m.lat, 5), round(m.lng, 5)))

        # --- TYP DNIA (różnorodność, jak w realnej pracy merchandisera) ---
        # Trzy typy losowane w miesiącu dają naturalną zmienność zamiast
        # jednakowych dni. Deterministyczne wg PESEL+dzień, więc ten sam
        # pracownik zawsze dostaje ten sam plan.
        _typy = ["gniazdo", "po_drodze", "po_drodze", "po_drodze", "daleki", "po_drodze"]
        typ_dnia = _typy[(seed_val + numer_dnia * 3) % len(_typy)]
        if promien_petli > 70:
            typ_dnia = "po_drodze"    # w rzadkich rejonach trzymamy się bezpiecznego schematu

        if typ_dnia == "gniazdo":
            # ciasna pętla blisko bazy, DUŻO punktów, krótkie skoki
            start_min, start_max = 15.0, 45.0
            skok_dnia = 24.0
            cele_min, cele_max = 5, 7
        elif typ_dnia == "daleki":
            # dojazd w dalszy rejon (dużo km z dojazdu), potem solidna pętla
            start_min, start_max = min(45.0, promien_petli*0.6), promien_petli
            skok_dnia = min(max_skok_bazowy(promien_petli), 40.0)
            cele_min, cele_max = 5, 7
        else:  # po_drodze
            start_min, start_max = 25.0, promien_petli * 0.75
            skok_dnia = max_skok_bazowy(promien_petli)
            cele_min, cele_max = 5, 7

        sektor_dnia = dozwolone_sektory[(seed_val + numer_dnia * 7) % len(dozwolone_sektory)]
        idx_sek = SEKTORY_KOLEJNOSC.index(sektor_dnia)
        aktywne_sektory = [SEKTORY_KOLEJNOSC[(idx_sek - 1) % 8], sektor_dnia, SEKTORY_KOLEJNOSC[(idx_sek + 1) % 8]]

        # Punkt startowy dnia: miasto w wybranym sektorze, w pierścieniu zależnym
        # od TYPU dnia (gniazdo blisko, daleki wyjazd dalej).
        srodek_startu = (start_min + start_max) / 2.0
        wagi = []
        for m in kandydaci:
            d = oblicz_dystans(baza_lat, baza_lng, m.lat, m.lng)
            if d > promien_petli or d < start_min - 8:
                waga = 0.001
            else:
                waga = 1000.0 / (abs(d - srodek_startu) + 8.0)
            waga *= 50.0 if m.typ == 'gmina' else 1.0
            waga *= waga_sieci(m.sieci)          # więcej sieci = chętniej na start dnia
            if m.sektor == sektor_dnia: waga *= 1000.0
            elif m.sektor in aktywne_sektory: waga *= 12.0
            else: waga *= 0.05
            wagi.append(waga)

        udana_trasa = False
        ostateczne_etapy_dnia = []

        for proba in range(40):
            # każda nieudana próba i każdy przepadły dzień rozluźniają reguły
            _luz = (1.0 + min(proba, 25) * 0.06) * (1.0 + min(_dni_nieudane, 12) * 0.06)
            _bez_ograniczen_typu = (proba >= 15) or (_dni_nieudane >= 2)
            punkt_startowy = rng.choices(kandydaci, weights=wagi, k=1)[0]
            ile_celow = rng.randint(cele_min, cele_max)

            # --- BUDOWA ŁAŃCUCHA "PO DRODZE" ---
            # Zaczynamy od punktu startowego, a każdy kolejny przystanek to
            # NAJBLIŻSZY nieodwiedzony sąsiad poprzedniego. Maksymalny skok
            # zależy od TYPU dnia (gniazdo = ciasno, po drodze = luźniej).
            wybrane = [punkt_startowy]
            uzyte_nazwy = {punkt_startowy.n}
            max_skok = (skok_dnia if promien_petli <= 70 else min(skok_dnia * (promien_petli/70.0), 60.0)) * _luz
            while len(wybrane) < ile_celow:
                ostatni = wybrane[-1]
                najlepszy = None
                najlepszy_d = max_skok        # skok WAŻONY (dojazd / waga sieci)
                for m in kandydaci:
                    if m.n in uzyte_nazwy: continue
                    if (not _bez_ograniczen_typu) and m.typ != 'gmina' and len(wybrane) > 1: continue
                    d_skok = oblicz_dystans(ostatni.lat, ostatni.lng, m.lat, m.lng)
                    if d_skok < 4.0: continue                    # to praktycznie ten sam punkt
                    if d_skok >= max_skok: continue              # realny skok ponad limit dnia
                    # Sieci WAŻĄ wybór sąsiada: miejscowość z 4–5 sieciami wygrywa
                    # z bliższą jedynką, o ile realny skok mieści się w limicie.
                    d_wazony = d_skok / waga_sieci(m.sieci)
                    if d_wazony >= najlepszy_d: continue         # dalej niż obecny najlepszy
                    if oblicz_dystans(baza_lat, baza_lng, m.lat, m.lng) > promien_petli: continue
                    if (not _bez_ograniczen_typu) and przecina_aglomeracje(ostatni.lat, ostatni.lng, m.lat, m.lng, baza_lat, baza_lng): continue
                    najlepszy = m; najlepszy_d = d_wazony
                if najlepszy is None: break
                wybrane.append(najlepszy); uzyte_nazwy.add(najlepszy.n)

            # Optymalna kolejność zwiedzania (pętla z bazy i z powrotem)
            wybrane_tsp = optymalizuj_tsp(wybrane, baza_lat, baza_lng)

            # --- WERYFIKACJA CZASOWA (8h = posiłek + jazda + postoje + POWRÓT) ---
            # Przerwa na posiłek jest wliczona w budżet z góry. Sprawdzamy, czy
            # CAŁY dzień z powrotem do bazy mieści się w limicie — jeśli nie,
            # obcinamy ostatnie punkty, aż się zmieści. Powrót do domu NIGDY nie
            # może wypchnąć dnia ponad 8h.
            czas_akt_test = PRZERWA_JEDZENIE_MIN
            etapy_test = []
            obecny_lat, obecny_lng, obecna_nazwa = baza_lat, baza_lng, baza_nazwa

            for cel in wybrane_tsp:
                d_line = oblicz_dystans(obecny_lat, obecny_lng, cel.lat, cel.lng)
                t_drive = (d_line * TEST_MNOZNIK_TRASY / SREDNIA_PREDKOSC) * 60
                t_shop = rng.randint(POSTOJ_MIN_MIN, POSTOJ_MAX_MIN)
                # powrót Z TEGO punktu prosto do bazy
                d_ret_line = oblicz_dystans(cel.lat, cel.lng, baza_lat, baza_lng)
                t_ret = (d_ret_line * TEST_MNOZNIK_TRASY / SREDNIA_PREDKOSC) * 60

                # pełny czas gdyby to był ostatni punkt: dojazd + postój + powrót do bazy
                if czas_akt_test + t_drive + t_shop + t_ret > LIMIT_CZASU_MINUTY:
                    break

                etapy_test.append(RawEtap(
                    skad=obecna_nazwa, dokad=cel.n, data_str=data.strftime("%d.%m.%Y") + "r",
                    d_line=d_line, czas_w_sklepie=t_shop, dokad_woj=cel.woj,
                    skad_lat=obecny_lat, skad_lng=obecny_lng, dokad_lat=cel.lat, dokad_lng=cel.lng
                ))
                czas_akt_test += t_drive + t_shop
                obecny_lat, obecny_lng, obecna_nazwa = cel.lat, cel.lng, cel.n

            # Dzień ważny tylko z min. 3 postojami "po drodze".
            _min_postojow = 2 if _dni_nieudane >= 4 else 3
            if len(etapy_test) < _min_postojow:
                continue

            # powrót do domu — dodajemy i liczymy PEŁNY czas dnia
            d_p_line = oblicz_dystans(obecny_lat, obecny_lng, baza_lat, baza_lng)
            t_powrot = (d_p_line * TEST_MNOZNIK_TRASY / SREDNIA_PREDKOSC) * 60
            czas_pelny = czas_akt_test + t_powrot

            # TWARDY BEZPIECZNIK: jeśli mimo wszystko przekracza 8h, obcinamy
            # ostatnie punkty aż cały dzień (z powrotem) zmieści się w limicie.
            while czas_pelny > LIMIT_CZASU_MINUTY and len(etapy_test) > (2 if _dni_nieudane >= 4 else 3):
                usuniety = etapy_test.pop()
                # przelicz czas: cofamy do punktu przed usuniętym
                if etapy_test:
                    ost = etapy_test[-1]
                    obecny_lat, obecny_lng, obecna_nazwa = ost.dokad_lat, ost.dokad_lng, ost.dokad
                else:
                    obecny_lat, obecny_lng, obecna_nazwa = baza_lat, baza_lng, baza_nazwa
                # odejmij czas usuniętego etapu (dojazd do niego + jego postój)
                czas_akt_test -= (usuniety.d_line * TEST_MNOZNIK_TRASY / SREDNIA_PREDKOSC) * 60 + (usuniety.czas_w_sklepie or 0)
                d_p_line = oblicz_dystans(obecny_lat, obecny_lng, baza_lat, baza_lng)
                t_powrot = (d_p_line * TEST_MNOZNIK_TRASY / SREDNIA_PREDKOSC) * 60
                czas_pelny = czas_akt_test + t_powrot

            # po obcięciu dzień nadal musi mieć min. 3 postoje — inaczej pomijamy
            _min_postojow = 2 if _dni_nieudane >= 4 else 3
            if len(etapy_test) < _min_postojow:
                continue
            # ostateczna kontrola — jeśli wciąż ponad limit, ten dzień odrzucamy
            if czas_pelny > LIMIT_CZASU_MINUTY:
                continue

            etapy_test.append(RawEtap(
                skad=obecna_nazwa, dokad=baza_nazwa, data_str=data.strftime("%d.%m.%Y") + "r",
                d_line=d_p_line, czas_w_sklepie=0, dokad_woj="",
                skad_lat=obecny_lat, skad_lng=obecny_lng, dokad_lat=baza_lat, dokad_lng=baza_lng
            ))

            udana_trasa = True
            ostateczne_etapy_dnia = etapy_test
            break

        if not udana_trasa:
            # Czterdzieści prób nie ułożyło dnia (bywa w rejonach, gdzie
            # filtry kierunkowe wycinają prawie wszystko). Zamiast tracić
            # dzień — a z nim część kwoty — budujemy trasę pewną: kolejne
            # najbliższe miejscowości od bazy, bez filtrów uznaniowych,
            # w granicach ośmiu godzin i nie bliżej niż MIN_ODLEGLOSC_OD_BAZY.
            try:
                # RÓŻNORODNOŚĆ DNI AWARYJNYCH: sama kolejność „od najbliższej"
                # dawała co dzień tę samą trasę (kopie w dokumencie). Każda
                # próba losuje rozrzut odległości i pomija kilka pierwszych
                # miejscowości; trasę identyczną z już zbudowaną odrzucamy
                # i próbujemy jeszcze raz (do AWARIA_PROB razy). rng jest
                # powtarzalny — ten sam plan dla tych samych danych.
                _slady_aw = set(tuple(_e.dokad for _e in _dz.etapy_surowe) for _dz in finalne_dni)
                for _proba_aw in range(AWARIA_PROB):
                    _pula = sorted(kandydaci,
                                   key=lambda _mm: oblicz_dystans(baza_lat, baza_lng, _mm.lat, _mm.lng)
                                   * rng.uniform(AWARIA_ROZRZUT[0], AWARIA_ROZRZUT[1])
                                   / waga_sieci(_mm.sieci))
                    _pomin = (_dni_awaryjne + _proba_aw) % AWARIA_POMIN_CO
                    _etapy = []
                    _ob_lat, _ob_lng, _ob_naz = baza_lat, baza_lng, baza_nazwa
                    _czas = PRZERWA_JEDZENIE_MIN
                    _uzyte = set()
                    for _cel in _pula:
                        if len(_etapy) >= 7:
                            break
                        if _pomin > 0 and _cel.n.lower() != baza_nazwa.lower():
                            _pomin -= 1
                            continue
                        if _cel.n in _uzyte or _cel.n.lower() == baza_nazwa.lower():
                            continue
                        if oblicz_dystans(baza_lat, baza_lng, _cel.lat, _cel.lng) < MIN_ODLEGLOSC_OD_BAZY:
                            continue
                        _d = oblicz_dystans(_ob_lat, _ob_lng, _cel.lat, _cel.lng)
                        if _d < 4.0:
                            continue
                        _t_dr = (_d * TEST_MNOZNIK_TRASY / SREDNIA_PREDKOSC) * 60
                        _t_sh = rng.randint(POSTOJ_MIN_MIN, POSTOJ_MAX_MIN)
                        _d_ret = oblicz_dystans(_cel.lat, _cel.lng, baza_lat, baza_lng)
                        _t_ret = (_d_ret * TEST_MNOZNIK_TRASY / SREDNIA_PREDKOSC) * 60
                        if _czas + _t_dr + _t_sh + _t_ret > LIMIT_CZASU_MINUTY:
                            continue
                        _etapy.append(RawEtap(
                            skad=_ob_naz, dokad=_cel.n, data_str=data.strftime("%d.%m.%Y") + "r",
                            d_line=_d, czas_w_sklepie=_t_sh, dokad_woj=_cel.woj,
                            skad_lat=_ob_lat, skad_lng=_ob_lng,
                            dokad_lat=_cel.lat, dokad_lng=_cel.lng))
                        _uzyte.add(_cel.n)
                        _czas += _t_dr + _t_sh
                        _ob_lat, _ob_lng, _ob_naz = _cel.lat, _cel.lng, _cel.n
                    # PRÓG DWÓCH POSTOJÓW — ŚWIADOMIE niższy niż w ścieżce
                    # normalnej (tam trzy): ostatnia deska ratunku dla dnia,
                    # a z nim dla części kwoty. Wyjazd do dwóch miejscowości
                    # i powrót to nadal najzwyklejsza podróż służbowa.
                    if len(_etapy) < 2:
                        continue
                    _d_pow = oblicz_dystans(_ob_lat, _ob_lng, baza_lat, baza_lng)
                    _etapy.append(RawEtap(
                        skad=_ob_naz, dokad=baza_nazwa, data_str=data.strftime("%d.%m.%Y") + "r",
                        d_line=_d_pow, czas_w_sklepie=0, dokad_woj="",
                        skad_lat=_ob_lat, skad_lng=_ob_lng,
                        dokad_lat=baza_lat, dokad_lng=baza_lng))
                    _slad = tuple(_e.dokad for _e in _etapy)
                    if _slad in _slady_aw:
                        # te same miejscowości w ODWROTNEJ kolejności to inny
                        # dzień (inne odcinki, inne godziny) — i tyle samo km
                        _post = [(_e.dokad, _e.dokad_lat, _e.dokad_lng, _e.czas_w_sklepie, _e.dokad_woj)
                                 for _e in _etapy[:-1]][::-1]
                        _et2 = []
                        _pl, _pg, _pn = baza_lat, baza_lng, baza_nazwa
                        for (_n, _la, _lg, _sh, _wj) in _post:
                            _et2.append(RawEtap(
                                skad=_pn, dokad=_n, data_str=data.strftime("%d.%m.%Y") + "r",
                                d_line=oblicz_dystans(_pl, _pg, _la, _lg), czas_w_sklepie=_sh,
                                dokad_woj=_wj, skad_lat=_pl, skad_lng=_pg, dokad_lat=_la, dokad_lng=_lg))
                            _pl, _pg, _pn = _la, _lg, _n
                        _et2.append(RawEtap(
                            skad=_pn, dokad=baza_nazwa, data_str=data.strftime("%d.%m.%Y") + "r",
                            d_line=oblicz_dystans(_pl, _pg, baza_lat, baza_lng), czas_w_sklepie=0,
                            dokad_woj="", skad_lat=_pl, skad_lng=_pg, dokad_lat=baza_lat, dokad_lng=baza_lng))
                        _slad2 = tuple(_e.dokad for _e in _et2)
                        if _slad2 not in _slady_aw:
                            _etapy, _slad = _et2, _slad2
                    if _slad in _slady_aw and _proba_aw < AWARIA_PROB - 1:
                        continue                     # kopia — jeszcze raz
                    udana_trasa = True
                    ostateczne_etapy_dnia = _etapy
                    _dni_awaryjne += 1
                    break
            except Exception:
                pass
        if not udana_trasa:
            _dni_nieudane += 1
            continue

        for e in ostateczne_etapy_dnia[:-1]:
            ostatnie_uzycie[e.dokad] = data
            aktualny_dystans_linii += e.d_line
            
        aktualny_dystans_linii += ostateczne_etapy_dnia[-1].d_line
        _pojemnosc_km += _pojemnosc_dnia(ostateczne_etapy_dnia)
        finalne_dni.append(DzienTrasy(data=data, etapy_surowe=ostateczne_etapy_dnia))
        if dzien_cb:
            # Przelot w oknie zapala trasę tego dnia. Silnik go nie czeka
            # i nie obchodzi go, czy ktoś patrzy — błąd odbiorcy nie psuje dnia.
            try:
                dzien_cb(finalne_dni[-1])
            except Exception:
                pass

    # Dni mogły powstać w innej kolejności niż kalendarzowa (gdy sięgaliśmy po
    # zapasowe daty) — porządkujemy chronologicznie.
    finalne_dni.sort(key=lambda d: d.data)

    if postep_cb: postep_cb("Skalowanie wektorów do budżetu...", 0.75)

    wszystkie_surowe = [e for dzien in finalne_dni for e in dzien.etapy_surowe]
    if not wszystkie_surowe:
        # Nie udało się zbudować ANI JEDNEGO dnia (bywa przy adresie bazy
        # wpisanym z błędem albo w rejonie bez miejscowości w zasięgu).
        # Zwracamy pustą listę Z INFORMACJĄ — inaczej program wyświetlał
        # „PDF wygenerowany" i otwierał folder z jednym pustym podsumowaniem.
        pusta = ListaTras()
        pusta.kwota_docelowa = kwota_calkowita
        pusta.kwota_osiagnieta = 0.0
        pusta.kwota_niepelna = True
        pusta.brak_dni = True
        try:
            with open(os.path.join(os.path.expanduser("~"), ".pmt_silnik_diag.txt"),
                      "a", encoding="utf-8") as _f:
                _f.write("%s | kwota %.2f | BRAK DNI — nie zbudowano zadnej trasy "
                         "(baza %s, woj %s, dni robocze %d)\n"
                         % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            kwota_calkowita, baza_nazwa, woj, len(dni_robocze)))
        except Exception:
            pass
        return pusta

    # --- REALNE ODLEGŁOŚCI DROGOWE ---
    # Do tej pory d_line to odległość w linii prostej (szybka, do doboru miast).
    # Teraz każdemu finalnemu odcinkowi nadajemy realny dystans DROGOWY z OSRM
    # (z cache + fallbackiem offline). Dzięki temu skalowanie kwot i wyliczone
    # kilometry odpowiadają faktycznym trasom po drogach, a nie liniom prostym.
    if postep_cb: postep_cb("Wyznaczanie realnych tras drogowych...", 0.78)
    for e in wszystkie_surowe:
        # linia prosta zostaje zapamiętana — to ona jest fizyczną granicą
        # dolną odcinka, a d_line za chwilę przestanie nią być
        if not getattr(e, "linia_prosta", 0):
            e.linia_prosta = e.d_line
        try:
            km_droga = dystans_drogowy(e.skad_lat, e.skad_lng, e.dokad_lat, e.dokad_lng)
            e.zrodlo = zrodlo_ostatniego_odcinka()
            if km_droga and km_droga > 0:
                e.d_line = km_droga
        except Exception:
            # zostaje linia prosta — ale NIE PO CICHU: to szacunek i tak
            # ma być pokazany w interfejsie oraz na dokumencie
            _odnotuj_zrodlo(ZRODLO_SZACUNEK)
            e.zrodlo = ZRODLO_SZACUNEK
    _zapisz_road_cache()

    suma_linii = max(sum(e.d_line for e in wszystkie_surowe), 1.0)
    wymagany_dystans_calkowity = kwota_calkowita / stawka
    rzeczywisty_mnoznik = wymagany_dystans_calkowity / suma_linii

    # --- TWARDY LIMIT 8h ---
    # Skalowanie km do kwoty nie może sprawić, że jakikolwiek dzień przekroczy
    # 8h (jazda + postoje + 30 min przerwy). Wyliczamy maksymalny dopuszczalny
    # mnożnik dla każdego dnia i bierzemy najmniejszy — dzięki temu ŻADEN dzień
    # nie wyjdzie ponad 8h, nawet kosztem tego, że kwota nie zostanie w całości
    # "wyjeżdżona" (nadwyżkę i tak przycinamy do realiów).
    def _czas_dnia_przy_mnozniku(dzien, mn):
        # przerwa na jedzenie wliczona w dzień pracy
        czas = PRZERWA_JEDZENIE_MIN
        for e in dzien.etapy_surowe:
            czas += (e.d_line * mn / SREDNIA_PREDKOSC) * 60      # jazda po realnym dystansie
            czas += (e.czas_w_sklepie or 0)                       # postój w miejscowości
        return czas

    # MNOŻNIK LICZONY OSOBNO DLA KAŻDEGO DNIA.
    # Wspólny mnożnik miał wadę: najciaśniejszy dzień — ten z największą
    # liczbą postojów — przycinał skalowanie CAŁEGO miesiąca, przez co
    # suma zatrzymywała się poniżej zamówionej kwoty, choć pozostałe dni
    # miały jeszcze wolne godziny. Teraz każdy dzień rozciąga się do
    # WŁASNEGO sufitu ośmiu godzin, a brakujące kilometry dolewamy tam,
    # gdzie został zapas.
    def _mnoznik_max_dnia(dzien):
        """Do ilu można rozciągnąć dzień: tyle, ile zostaje godzin po postojach
        i posiłku (FIZYKA doby), i nie więcej niż regulaminowy sufit dnia.
        Dolną granicą zostaje realna droga (MNOZNIK_MIN)."""
        baza_km = sum(e.d_line for e in dzien.etapy_surowe)
        postoje = sum((e.czas_w_sklepie or 0) for e in dzien.etapy_surowe) + PRZERWA_JEDZENIE_MIN
        dostepne = LIMIT_CZASU_MINUTY - postoje
        if dostepne <= 0 or baza_km <= 0:
            return MNOZNIK_MIN, baza_km
        _z_godzin = (dostepne / 60) * SREDNIA_PREDKOSC / baza_km
        _z_limitu_dnia = (MAX_KWOTA_DNIA / stawka) / baza_km
        return max(MNOZNIK_DOL, min(_z_godzin, _z_limitu_dnia, MNOZNIK_MAX)), baza_km

    # ── DROGA NIGDY KRÓTSZA NIŻ LINIA PROSTA ─────────────────────────
    # Dotąd mnożnik mógł spaść do 0,3: przy małej kwocie (albo po prostu
    # przy zbyt wielu zbudowanych dniach) silnik „ściskał" wszystkie odcinki —
    # Warszawa→Bolimów wychodziła na 20 km i 18 minut u jednej osoby, a 45 km
    # u drugiej. Odcinek krótszy niż w linii prostej jest fizycznie
    # niemożliwy, więc zamiast skracać kilometry:
    #   0) każdy dzień musi mieścić się w 8 h przy REALNEJ drodze
    #      (MNOZNIK_MIN) — jeśli nie, zdejmujemy mu ostatnie postoje,
    #   1) gdy suma dni × MNOZNIK_MIN przekracza cel, USUWAMY DNI — najpierw
    #      te o najdłuższej trasie, żeby zostało możliwie WIELE krótszych dni
    #      rozrzuconych po miesiącu,
    #   2) gdy został jeden dzień i nadal jest za długi — zdejmujemy postoje
    #      (zostają co najmniej dwa).
    _dni_przyciete = 0
    _postoje_przyciete = 0

    def _linia_dnia(dz):
        return sum(e.d_line for e in dz.etapy_surowe)

    def _linia_wszystkich():
        return sum(_linia_dnia(dz) for dz in finalne_dni)

    def _km_odcinka(la1, lg1, la2, lg2):
        """Odcinek dobudowany po przycięciu liczy się TAK SAMO jak reszta:
        realna droga z pamięci podręcznej albo linia prosta × krętość. Sama
        linia prosta dawała mu zaniżone kilometry względem sąsiadów.
        Klucz pamięci obejmuje oba kierunki, więc dzień jadący pętlę w drugą
        stronę trafia na tę samą drogę bez dodatkowego zapytania."""
        try:
            km = dystans_drogowy(la1, lg1, la2, lg2, tylko_cache=True)
            if km and km > 0:
                return km
        except Exception:
            pass
        return oblicz_dystans(la1, lg1, la2, lg2)

    def _sufit_surowy(dz):
        """Mnożnik, przy którym dzień dobija DOKŁADNIE do limitu godzin
        (bez dolnej granicy — do decyzji o przycinaniu)."""
        baza_km = _linia_dnia(dz)
        postoje = sum((e.czas_w_sklepie or 0) for e in dz.etapy_surowe) + PRZERWA_JEDZENIE_MIN
        dostepne = LIMIT_CZASU_MINUTY - postoje
        if dostepne <= 0 or baza_km <= 0:
            return 0.0
        return (dostepne / 60) * SREDNIA_PREDKOSC / baza_km

    def _zdejmij_postoj(dz, ktory=None):
        """etapy: [baza→A, A→B, …, X→baza]. Zdejmuje postój numer `ktory`
        (0 = pierwszy; None = ostatni) i skleja odcinek z sąsiadami. Dni
        awaryjne rodzą się z tej samej listy najbliższych miejscowości, więc
        ucinanie zawsze OSTATNIEGO postoju zamieniałoby je w kopie — dlatego
        przy limicie godzin wybieramy postój losowo (rng jest powtarzalny).
        Zwraca False, gdy nie ma czego ciąć (zostają co najmniej 2 postoje)."""
        n = len(dz.etapy_surowe) - 1            # liczba postojów
        if n <= 2:
            return False
        if ktory is None or not (0 <= ktory < n):
            ktory = n - 1
        _do = dz.etapy_surowe[ktory]              # etap kończący się w usuwanym postoju
        _z = dz.etapy_surowe[ktory + 1]           # etap wychodzący z niego
        _sklejony = RawEtap(
            skad=_do.skad, dokad=_z.dokad, data_str=_z.data_str,
            d_line=_km_odcinka(_do.skad_lat, _do.skad_lng, _z.dokad_lat, _z.dokad_lng),
            czas_w_sklepie=_z.czas_w_sklepie, dokad_woj=_z.dokad_woj,
            skad_lat=_do.skad_lat, skad_lng=_do.skad_lng,
            dokad_lat=_z.dokad_lat, dokad_lng=_z.dokad_lng)
        dz.etapy_surowe = dz.etapy_surowe[:ktory] + [_sklejony] + dz.etapy_surowe[ktory + 2:]
        return True

    def _zdejmij_ostatni_postoj(dz):
        return _zdejmij_postoj(dz, None)

    def _sciagnij_dzien(dz, budzet_km):
        """Buduje dzień od nowa z NAJBLIŻSZYCH miejscowości.

        Potrzebne przy małych kwotach: gdy nawet dwupostojowa pętla wybrana
        przez silnik kosztuje więcej, niż wynosi kwota, jedyną alternatywą
        byłoby ściśnięcie drogi poniżej linii prostej — a droga krótsza od
        linii prostej to delegacja, której nikt nie przejechał. Zamiast tego
        szukamy najdłuższej pętli z dwoma postojami, która MIEŚCI SIĘ w
        budżecie. Zwraca False, gdy nic krótszego nie ma.

        Pętla liczona jest w LINII PROSTEJ, a na dokumencie odcinek nigdy nie
        schodzi poniżej linia × MNOZNIK_MIN — więc to MNOZNIK_MIN, nie
        MNOZNIK_DOL, mówi, czy pętla mieści się w budżecie. Z dolną granicą
        1,0 silnik wybierał pętlę o włos pod budżetem, podłoga podnosiła ją
        o 15 % i 80 zł z Radomia kończyło się meldunkiem „kwota za mała:
        91,28 zł", choć dziesięć kilometrów dalej stały tańsze pętle."""
        if not dz.etapy_surowe or budzet_km <= 0:
            return False
        wzor = dz.etapy_surowe[0]
        teraz = _linia_dnia(dz)
        # Bierzemy z CAŁEJ wczytanej bazy, a nie z kandydatów dnia: kandydaci są
        # przefiltrowani sektorem i minimalną odległością od bazy, więc przy
        # najmniejszych kwotach potrafi w nich nie być ani jednej miejscowości
        # dość blisko. Tu liczy się wyłącznie to, żeby pętla była prawdziwa.
        _pula = [m for _lista in _baza_miast.values() for m in _lista
                 if m.n.lower() != str(baza_nazwa).lower()
                 and oblicz_dystans(baza_lat, baza_lng, m.lat, m.lng) > 3.0]
        blisko = sorted(_pula or list(kandydaci),
                        key=lambda m: oblicz_dystans(baza_lat, baza_lng, m.lat, m.lng))[:14]
        najlepsza = None
        for i, a in enumerate(blisko):
            for b2 in blisko[i + 1:]:
                linia = (oblicz_dystans(baza_lat, baza_lng, a.lat, a.lng)
                         + oblicz_dystans(a.lat, a.lng, b2.lat, b2.lng)
                         + oblicz_dystans(b2.lat, b2.lng, baza_lat, baza_lng))
                if linia * MNOZNIK_MIN > budzet_km or linia >= teraz:
                    continue
                if najlepsza is None or linia > najlepsza[0]:
                    najlepsza = (linia, a, b2)
        if najlepsza is None:
            # Najmniejsza prawdziwa delegacja to wyjazd do JEDNEJ miejscowości
            # i powrót. Przy kwocie rzędu pięćdziesięciu złotych tak właśnie
            # wygląda dzień — dwa postoje już się w niej nie mieszczą.
            for a in blisko:
                linia = 2.0 * oblicz_dystans(baza_lat, baza_lng, a.lat, a.lng)
                if linia * MNOZNIK_MIN > budzet_km or linia >= teraz:
                    continue
                if najlepsza is None or linia > najlepsza[0]:
                    najlepsza = (linia, a, None)
        if najlepsza is None and blisko:
            # Nic nie mieści się w kwocie — zostaje NAJKRÓTSZY prawdziwy
            # wyjazd (najbliższa miejscowość i powrót), o ile jest krótszy
            # od obecnego dnia. Meldunek „kwota za mała" podaje wtedy
            # prawdziwe minimum, a nie koszt przypadkowej pętli (Ustrzyki
            # Dolne: 194 zł przez Jasło, choć Dynów i powrót to 103 zł).
            a = blisko[0]
            linia = 2.0 * oblicz_dystans(baza_lat, baza_lng, a.lat, a.lng)
            if linia < teraz:
                najlepsza = (linia, a, None)
        if najlepsza is None:
            return False
        _, a, b2 = najlepsza
        _postoj = wzor.czas_w_sklepie or POSTOJ_MIN_MIN
        _ds = wzor.data_str
        _woj_bazy = dz.etapy_surowe[-1].dokad_woj
        if b2 is None:
            dz.etapy_surowe = [
                RawEtap(skad=str(baza_nazwa), dokad=a.n, data_str=_ds,
                        d_line=oblicz_dystans(baza_lat, baza_lng, a.lat, a.lng),
                        czas_w_sklepie=_postoj, dokad_woj=a.woj,
                        skad_lat=baza_lat, skad_lng=baza_lng,
                        dokad_lat=a.lat, dokad_lng=a.lng),
                RawEtap(skad=a.n, dokad=str(baza_nazwa), data_str=_ds,
                        d_line=oblicz_dystans(a.lat, a.lng, baza_lat, baza_lng),
                        czas_w_sklepie=0, dokad_woj=_woj_bazy,
                        skad_lat=a.lat, skad_lng=a.lng,
                        dokad_lat=baza_lat, dokad_lng=baza_lng),
            ]
            return True
        dz.etapy_surowe = [
            RawEtap(skad=str(baza_nazwa), dokad=a.n, data_str=_ds,
                    d_line=oblicz_dystans(baza_lat, baza_lng, a.lat, a.lng),
                    czas_w_sklepie=_postoj, dokad_woj=a.woj,
                    skad_lat=baza_lat, skad_lng=baza_lng,
                    dokad_lat=a.lat, dokad_lng=a.lng),
            RawEtap(skad=a.n, dokad=b2.n, data_str=_ds,
                    d_line=oblicz_dystans(a.lat, a.lng, b2.lat, b2.lng),
                    czas_w_sklepie=_postoj, dokad_woj=b2.woj,
                    skad_lat=a.lat, skad_lng=a.lng,
                    dokad_lat=b2.lat, dokad_lng=b2.lng),
            RawEtap(skad=b2.n, dokad=str(baza_nazwa), data_str=_ds,
                    d_line=oblicz_dystans(b2.lat, b2.lng, baza_lat, baza_lng),
                    czas_w_sklepie=0, dokad_woj=dz.etapy_surowe[-1].dokad_woj,
                    skad_lat=b2.lat, skad_lng=b2.lng,
                    dokad_lat=baza_lat, dokad_lng=baza_lng),
        ]
        return True

    # KOPIE DNI: dwa dni z identyczną kolejnością miejscowości wyglądają
    # jak dokument przepisany przez kalkę. Drugi egzemplarz jedzie tę samą
    # pętlę W ODWROTNĄ STRONĘ (inne odcinki i godziny, te same kilometry);
    # gdy i to jest już zajęte — dzień zostaje, ale to rzadkość.
    _widziane_slady = set()
    for _dz in finalne_dni:
        _s = tuple(e.dokad for e in _dz.etapy_surowe)
        if _s in _widziane_slady and len(_dz.etapy_surowe) >= 3:
            _post = [(e.dokad, e.dokad_lat, e.dokad_lng, e.czas_w_sklepie, e.dokad_woj)
                     for e in _dz.etapy_surowe[:-1]][::-1]
            _pow = _dz.etapy_surowe[-1]
            _et2 = []
            _pl, _pg, _pn = _pow.dokad_lat, _pow.dokad_lng, _pow.dokad
            _ds = _dz.etapy_surowe[0].data_str
            for (_n, _la, _lg, _sh, _wj) in _post:
                _et2.append(RawEtap(skad=_pn, dokad=_n, data_str=_ds,
                                    d_line=_km_odcinka(_pl, _pg, _la, _lg), czas_w_sklepie=_sh,
                                    dokad_woj=_wj, skad_lat=_pl, skad_lng=_pg, dokad_lat=_la, dokad_lng=_lg))
                _pl, _pg, _pn = _la, _lg, _n
            _et2.append(RawEtap(skad=_pn, dokad=_pow.dokad, data_str=_ds,
                                d_line=_km_odcinka(_pl, _pg, _pow.dokad_lat, _pow.dokad_lng),
                                czas_w_sklepie=0, dokad_woj=_pow.dokad_woj, skad_lat=_pl, skad_lng=_pg,
                                dokad_lat=_pow.dokad_lat, dokad_lng=_pow.dokad_lng))
            _s2 = tuple(e.dokad for e in _et2)
            if _s2 not in _widziane_slady:
                _dz.etapy_surowe = _et2
                _s = _s2
        _widziane_slady.add(_s)

    # 0) osiem godzin przy realnej drodze — losowy postój (każdy, także
    #    pierwszy: inaczej dni awaryjne z tej samej listy zaczynały się zawsze
    #    tą samą miejscowością)
    for _dz in list(finalne_dni):
        while _sufit_surowy(_dz) < MNOZNIK_DOL:
            _n = len(_dz.etapy_surowe) - 1
            if _n <= 2 or not _zdejmij_postoj(_dz, rng.randint(0, _n - 1)):
                break
            _postoje_przyciete += 1
        if _sufit_surowy(_dz) < MNOZNIK_DOL and len(finalne_dni) > 1:
            finalne_dni.remove(_dz)              # dwa postoje i nadal za daleko
            _dni_przyciete += 1

    def _moc_dnia(dz):
        """Ile kilometrów dzień UDŹWIGNIE: tyle, ile zostaje godzin po postojach
        i posiłku. Dzień, który nie mieści się w dobie przy realnej drodze,
        nie udźwignie nic — i tak wypadnie."""
        _s = _sufit_surowy(dz)
        return _linia_dnia(dz) * min(_s, MNOZNIK_MAX) if _s >= MNOZNIK_DOL else 0.0

    # 1) za dużo kilometrów na tę kwotę: odpadają najdłuższe dni. Dzień
    #    zdejmujemy jednak tylko wtedy, gdy reszta dni NADAL udźwignie kwotę;
    #    inaczej najdłuższy dzień tracił postój (mniej kilometrów, dzień
    #    zostaje), bo po zdjęciu całego dnia kwoty nie dałoby się już
    #    wyjeździć — a to ona jest tu punktem odniesienia.
    while len(finalne_dni) > 1 and _linia_wszystkich() * MNOZNIK_DOL > wymagany_dystans_calkowity + 0.5:
        _najdluzszy = max(finalne_dni, key=lambda dz: (_linia_dnia(dz), -len(dz.etapy_surowe)))
        _moc_reszty = sum(_moc_dnia(_dz) for _dz in finalne_dni if _dz is not _najdluzszy)
        if _moc_reszty >= wymagany_dystans_calkowity:
            finalne_dni.remove(_najdluzszy)
            _dni_przyciete += 1
        elif len(_najdluzszy.etapy_surowe) - 1 > 2 and _zdejmij_ostatni_postoj(_najdluzszy):
            _postoje_przyciete += 1
        else:
            break

    # 2) jeden dzień i nadal za długi: mniej postojów
    if len(finalne_dni) == 1:
        _dz = finalne_dni[0]
        while _linia_dnia(_dz) * MNOZNIK_DOL > wymagany_dystans_calkowity + 0.5:
            if not _zdejmij_ostatni_postoj(_dz):
                break
            _postoje_przyciete += 1

    # 2b) najmniejsza liczba postojów, a pętla nadal droższa niż kwota:
    #     dzień budujemy od nowa z najbliższych miejscowości. Bez tego trzeba
    #     by ścisnąć drogę poniżej linii prostej (patrz _sciagnij_dzien).
    for _ in range(len(finalne_dni) + 2):
        # bez luzu: pół kilometra zapasu wystarczało, żeby końcowe skalowanie
        # zeszło z mnożnikiem poniżej MNOZNIK_MIN, czyli poniżej linii prostej
        if _linia_wszystkich() * MNOZNIK_DOL <= wymagany_dystans_calkowity:
            break
        _dz = max(finalne_dni, key=_linia_dnia)
        _reszta = _linia_wszystkich() - _linia_dnia(_dz)
        _budzet = wymagany_dystans_calkowity / MNOZNIK_DOL - _reszta
        if not _sciagnij_dzien(_dz, _budzet * MNOZNIK_DOL):
            break

    _dane_dni = []
    for dzien in finalne_dni:
        mn_max, baza_km = _mnoznik_max_dnia(dzien)
        _dane_dni.append({"dzien": dzien, "max": mn_max, "km": baza_km, "mn": MNOZNIK_DOL})

    # Wszystkie dni rozciągamy TYM SAMYM mnożnikiem — kilometry tego samego
    # odcinka nie mogą zależeć od tego, w którym dniu wypadł. Dzień, któremu
    # zabraknie godzin, zatrzymuje się na swoim suficie (x["max"]), a brakujące
    # kilometry dolewamy tam, gdzie zapas jeszcze został.
    _suma_km_bazowa = max(sum(x["km"] for x in _dane_dni), 1.0)
    _cel = wymagany_dystans_calkowity
    _mn_start = max(MNOZNIK_DOL, _cel / _suma_km_bazowa)
    for x in _dane_dni:
        x["mn"] = max(MNOZNIK_DOL, min(_mn_start, x["max"]))
    for _ in range(24):
        _osiagniete = sum(x["km"] * x["mn"] for x in _dane_dni)
        _brak = _cel - _osiagniete
        if _brak <= 0.5:
            break
        _zapas = [x for x in _dane_dni if x["max"] - x["mn"] > 1e-6 and x["km"] > 0]
        if not _zapas:
            break
        _poj = sum((x["max"] - x["mn"]) * x["km"] for x in _zapas)
        if _poj <= 0:
            break
        _udzial = min(1.0, _brak / _poj)
        for x in _zapas:
            x["mn"] += (x["max"] - x["mn"]) * _udzial

    for x in _dane_dni:
        for e in x["dzien"].etapy_surowe:
            e._mnoznik_dnia = x["mn"]

    wszystkie_surowe = [e for dzien in finalne_dni for e in dzien.etapy_surowe]
    suma_linii = max(sum(e.d_line for e in wszystkie_surowe), 1.0)
    _osiagniete = sum(e.d_line * getattr(e, "_mnoznik_dnia", 1.0) for e in wszystkie_surowe)
    rzeczywisty_mnoznik = _osiagniete / suma_linii      # tylko do statystyk

    # Koszt każdego etapu = jego REALNY dystans (km × mnożnik) × stawka.
    # Nic nie dopisujemy. Dzięki dobraniu mnożnika suma wychodzi z natury
    # bardzo blisko celu (różnica to zwykle kilka GROSZY z zaokrągleń).
    for e in wszystkie_surowe:
        _km = e.d_line * getattr(e, "_mnoznik_dnia", rzeczywisty_mnoznik)
        # sufit: odcinek nie może być wielokrotnością prawdziwej drogi
        _km = min(_km, e.d_line * MNOZNIK_MAX)
        # podłoga: droga nigdy krótsza niż linia prosta między punktami.
        # Odcinki dobudowane po przycinaniu nie przeszły przez pętlę wyżej,
        # więc linię prostą liczymy im tutaj — inaczej zostałyby bez podłogi.
        _prosta = float(getattr(e, "linia_prosta", 0.0) or 0.0)
        if _prosta <= 0:
            try:
                _prosta = oblicz_dystans(e.skad_lat, e.skad_lng, e.dokad_lat, e.dokad_lng)
                e.linia_prosta = _prosta
            except Exception:
                _prosta = 0.0
        if _prosta > 0:
            _km = max(_km, _prosta * MNOZNIK_MIN)
        e.dystans_rzeczywisty = _km
        e.kwota = max(round(e.dystans_rzeczywisty * stawka, 2), 0.0)
        e.czas_jazdy_minuty = (e.dystans_rzeczywisty / SREDNIA_PREDKOSC) * 60

    # Jedyna korekta: domknięcie DROBNYCH groszy z zaokrągleń, rozłożone po
    # 1 groszu na kolejne etapy. To NIE jest dopisywanie kwot do tras — to
    # tylko wyrównanie zaokrągleń (rzędu kilku groszy). Gdyby różnica była
    # duża (co nie powinno się zdarzyć), zostawiamy trasy realne — lepiej
    # kwota bliska niż sztucznie napompowany odcinek.
    reszta = round(kwota_calkowita - sum(e.kwota for e in wszystkie_surowe), 2)

    # BEZPIECZNIK PRZEKROCZENIA: jeśli suma WYSZŁA PONAD budżet (zdarza się dla
    # bardzo małych kwot w rzadkich rejonach, gdzie minimum dni i tak generuje
    # sporo km), delikatnie skalujemy WSZYSTKIE etapy w dół do budżetu. Delegacja
    # NIGDY nie może przekroczyć wpisanej kwoty.
    suma_biezaca = sum(e.kwota for e in wszystkie_surowe)
    _kwota_za_mala = False
    _kwota_min_realna = 0.0
    if suma_biezaca > kwota_calkowita + 0.01 and suma_biezaca > 0:
        # PODŁOGA JEST NIEPRZEKRACZALNA: ściśnięcie do budżetu nie może
        # zejść poniżej linii prostej między punktami. Dawniej schodziło
        # nawet do 0,15 × linii (Ustrzyki Dolne przy 50 zł: 126 km w linii
        # prostej, 19 km na dokumencie) — taki przejazd jest niemożliwy.
        def _podloga_km(e):
            _pr = float(getattr(e, "linia_prosta", 0.0) or 0.0)
            if _pr <= 0:
                try:
                    _pr = oblicz_dystans(e.skad_lat, e.skad_lng, e.dokad_lat, e.dokad_lng)
                    e.linia_prosta = _pr
                except Exception:
                    _pr = 0.0
            return _pr * MNOZNIK_MIN
        # Poniżej dolnej granicy mnożnika (MNOZNIK_MIN) odcinek przestaje
        # być realną drogą. Kwota pozostaje nieprzekraczalna, ale gdy nawet
        # najkrótszy możliwy dzień (2 postoje) się w niej nie mieści,
        # użytkownik dostaje wprost informację: kwota ZA MAŁA + minimum.
        try:
            # Sygnał tylko przy ISTOTNEJ różnicy: przekroczenie o grosze
            # (zaokrąglenia, zapas 0,5 km z przycinania) to nie „kwota za mała".
            # Minimum liczone TAK SAMO jak podłoga: z linii prostej, nie z drogi
            # (droga × MNOZNIK_MIN meldowała „za mało" przy 250 zł z Radomia,
            # choć dwa dni mieściły się w kwocie z zapasem).
            _minimum = round(sum(_podloga_km(e) * stawka for e in wszystkie_surowe), 2)
            if _minimum > kwota_calkowita + max(1.0, 0.01 * kwota_calkowita):
                _kwota_za_mala = True
                _kwota_min_realna = _minimum
        except Exception:
            pass
        # Ściskamy W KILKU PRZEBIEGACH: odcinek, który stanął na podłodze,
        # w następnym przebiegu już nie oddaje kilometrów — oddają je te,
        # które mają jeszcze luz. Jedno wspólne skalowanie zostawiało resztę
        # ponad kwotą (Radom, 250 zł: 251,44 zł), bo część odcinków odbijała
        # się od podłogi, a reszta nie nadrabiała.
        for _przebieg in range(8):
            suma_biezaca = sum(e.kwota for e in wszystkie_surowe)
            if suma_biezaca <= kwota_calkowita + 0.01:
                break
            _z_luzem = [e for e in wszystkie_surowe
                        if e.dystans_rzeczywisty > _podloga_km(e) + 1e-6]
            if not _z_luzem:
                break
            _id_luz = set(id(e) for e in _z_luzem)
            _na_podlodze_zl = sum(e.kwota for e in wszystkie_surowe if id(e) not in _id_luz)
            _ruchome_zl = sum(e.kwota for e in _z_luzem)
            if _ruchome_zl <= 0:
                break
            skala = max(0.0, (kwota_calkowita - _na_podlodze_zl) / _ruchome_zl)
            for e in _z_luzem:
                e.dystans_rzeczywisty = max(e.dystans_rzeczywisty * skala, _podloga_km(e))
                e.kwota = max(round(e.dystans_rzeczywisty * stawka, 2), 0.0)
                e.czas_jazdy_minuty = (e.dystans_rzeczywisty / SREDNIA_PREDKOSC) * 60
        _po_podlodze = round(sum(e.kwota for e in wszystkie_surowe), 2)
        # Delegacja NIE MOŻE przekroczyć zamówionej kwoty. Jeśli po dociśnięciu
        # podłogi suma i tak wychodzi wyżej, to znaczy, że kwota jest mniejsza
        # niż najtańszy prawdziwy wyjazd z tej bazy — i trzeba to powiedzieć
        # razem z liczbą, a nie przemilczeć.
        if _po_podlodze > kwota_calkowita + 0.05:
            # Kwota jest mniejsza niż najtańszy PRAWDZIWY wyjazd z tej bazy.
            # Nie udajemy, że się zmieściła — mówimy, ile naprawdę wynosi.
            _kwota_za_mala = True
            _kwota_min_realna = _po_podlodze
        reszta = round(kwota_calkowita - _po_podlodze, 2)

    # dziennik silnika — komplet liczb do diagnozy, gdyby kwota nie dobiła.
    # Plik jest przycinany do ostatnich 200 wpisów, żeby nie puchł bez końca.
    try:
        _osi = sum(e.kwota for e in wszystkie_surowe)
        _plik_diag = os.path.join(os.path.expanduser("~"), ".pmt_silnik_diag.txt")
        try:
            if os.path.exists(_plik_diag) and os.path.getsize(_plik_diag) > 120000:
                with open(_plik_diag, encoding="utf-8", errors="ignore") as _fd:
                    _ogon = _fd.readlines()[-200:]
                with open(_plik_diag, "w", encoding="utf-8") as _fd:
                    _fd.writelines(_ogon)
        except Exception:
            pass
        with open(_plik_diag, "a", encoding="utf-8") as _f:
            _mnozniki = [x["mn"] for x in _dane_dni] or [0.0]
            _f.write("%s | kwota %.2f | stawka %.2f | cel %.0f km | dni robocze %d | "
                     "potrzeba %d | zbudowane %d | awaryjne %d | nieudane %d | "
                     "przyciete dni %d postoje %d | linia %.0f km | mnoznik %.2f-%.2f | "
                     "limit dnia %d min | pojemnosc %.0f km | osiagnieto %.2f (%.1f%%)"
                     % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        kwota_calkowita, stawka, cel_calkowity_dystans, len(dni_robocze),
                        _dni_potrzeba, len(finalne_dni), _dni_awaryjne, _dni_nieudane,
                        _dni_przyciete, _postoje_przyciete, suma_linii,
                        min(_mnozniki), max(_mnozniki),
                        LIMIT_CZASU_MINUTY, _pojemnosc_km, _osi,
                        100.0 * _osi / max(kwota_calkowita, 1e-9))
                     + (" | KWOTA ZA MALA (min %.2f zl)\n" % _kwota_min_realna
                        if _kwota_za_mala else "\n"))
    except Exception:
        pass

    LIMIT_KOREKTY_GROSZY = max(len(wszystkie_surowe), 20)  # max ~1 gr/etap
    if 0.01 <= abs(reszta) <= LIMIT_KOREKTY_GROSZY * 0.01 and wszystkie_surowe:
        krok = 0.01 if reszta > 0 else -0.01
        idx = 0
        while abs(reszta) >= 0.01:
            e = wszystkie_surowe[idx % len(wszystkie_surowe)]
            e.kwota = round(e.kwota + krok, 2)
            reszta = round(reszta - krok, 2); idx += 1

    # odcinki dobudowane po przycinaniu i pętle odwrócone nie przeszły przez
    # pętlę dróg wyżej — źródło biorą z pamięci dróg, tak jak ich kilometry
    uzupelnij_zrodla_etapow(e for dzien in finalne_dni for e in dzien.etapy_surowe)

    for dzien in finalne_dni:
        # Godzina wyjazdu zależy od TRYBU PRACY:
        #  tygodniowy — rano, między 7:00 a 8:00 (jak dotąd),
        #  wieczorny  — po pracy, między 16:15 a 16:45, tak aby ostatnia
        #               placówka zamknęła się przed 22:00 (patrz limit dnia).
        if TRYB_PRACY == "wieczory":
            czas_akt = rng.randint(16 * 60 + 15, 16 * 60 + 45)
        else:
            czas_akt = rng.randint(7 * 60, 8 * 60)
        ile_etapow = len(dzien.etapy_surowe)
        polowa = ile_etapow // 2
        for idx, e in enumerate(dzien.etapy_surowe):
            godz_wyj = f"{int(czas_akt//60)%24:02d}:{int(czas_akt%60):02d}"
            czas_akt += e.czas_jazdy_minuty
            godz_przyj = f"{int(czas_akt//60)%24:02d}:{int(czas_akt%60):02d}"
            dzien.etapy.append(Etap(skad=e.skad, dokad=e.dokad, data=e.data_str, godz_wyj=godz_wyj, godz_przyj=godz_przyj, kwota=e.kwota, dokad_woj=e.dokad_woj))
            czas_akt += e.czas_w_sklepie
            # przerwa na jedzenie mniej więcej w połowie dnia (wliczona w 8h)
            if idx == polowa:
                czas_akt += PRZERWA_JEDZENIE_MIN

    # Informacja dla warstwy UI: czy realnymi trasami udało się pokryć kwotę.
    # Jeśli mimo wykorzystania wszystkich możliwych dni suma odbiega od celu
    # o więcej niż ~2%, sygnalizujemy to (użytkownik dostanie komunikat, że
    # kwota jest za wysoka na ten miesiąc/rejon). NIE pompujemy tras na siłę.
    suma_final = sum(d.suma for d in finalne_dni)
    finalne_dni = ListaTras(finalne_dni)
    finalne_dni.kwota_docelowa = kwota_calkowita
    finalne_dni.kwota_osiagnieta = round(suma_final, 2)
    # Każdy brak, nie tylko duży. Dawny próg (2 % albo 20 zł) przepuszczał po
    # cichu nawet 96 zł: program pokazywał zielone „PDF wygotowany", a z
    # rozliczenia znikały pieniądze. Grosz różnicy to i tak różnica.
    finalne_dni.kwota_niepelna = (kwota_calkowita - suma_final) > 0.01
    finalne_dni.kwota_za_mala = bool(_kwota_za_mala)
    finalne_dni.kwota_min_realna = float(_kwota_min_realna or 0.0)
    finalne_dni.brak_dni = _brak_dni_na_kwote
    return finalne_dni

def generuj_mape_html(finalne_dni: List[DzienTrasy], pracownik: DanePracownika, miesiac_slownie: str, rok: int, folder: str, is_dark: bool):
    bg_color = "#0B1320" if is_dark else "#F1F5F9"
    text_color = "#F8FAFC" if is_dark else "#0F172A"
    card_bg = "rgba(16, 25, 43, 0.8)" if is_dark else "#FFFFFF"
    border_c = "rgba(0, 240, 255, 0.3)" if is_dark else "rgba(13, 148, 136, 0.3)"
    title_c = "#00F0FF" if is_dark else "#0D9488"
    text_muted = "#94A3B8" if is_dark else "#475569"
    btn_bg = "linear-gradient(to right, #00F0FF, #0093E9)" if is_dark else "#10B981"
    btn_txt = "#000000" if is_dark else "#FFFFFF"
    _etykieta_zrodla = etykieta_zrodla_odleglosci()
    zrodlo_html = ("<p>Odległości: %s</p>" % _etykieta_zrodla) if _etykieta_zrodla else ""
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <title>Trasy Delegacji - {pracownik.imie}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: {bg_color}; color: {text_color}; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ color: {title_c}; margin-bottom: 5px; }}
            .day-card {{ background-color: {card_bg}; border: 1px solid {border_c}; border-radius: 8px; padding: 15px 20px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); }}
            .day-title {{ font-size: 16px; font-weight: bold; color: {text_color}; margin-bottom: 10px; }}
            .route {{ font-size: 14px; color: {text_muted}; margin-bottom: 15px; line-height: 1.5; }}
            .btn {{ display: inline-block; background: {btn_bg}; color: {btn_txt}; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 13px; transition: opacity 0.2s; }}
            .btn:hover {{ opacity: 0.8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Wykaz Tras Geograficznych - {pracownik.imie}</h1>
                <p>Miesiąc: {miesiac_slownie} {rok}</p>
                {zrodlo_html}
            </div>
    """
    # Baza (dom pracownika) to START i KONIEC każdej trasy. Przekazujemy pełny
    # adres pracownika — jest dokładny (ulica+kod), więc Google nie podstawi
    # sąsiedniego budynku, a jednocześnie czytelnie pokazuje punkt startu/powrotu.
    # Fallback na współrzędne, gdyby adres był pusty.
    # START i POWRÓT KAŻDEJ DELEGACJI to adres z FORMULARZA DELEGACJI
    # (pole „Adres zamieszkania"). Nigdy adres bazy planera ani ustawienie
    # wspólne — dokument musi zgadzać się z tym, co podano do rozliczenia.
    adres_bazy = (pracownik.adres or "").strip()
    if adres_bazy:
        baza_punkt = adres_bazy
    else:
        baza_punkt = f"{pracownik.baza_lat:.6f},{pracownik.baza_lng:.6f}"
    for dzien in finalne_dni:
        if not dzien.etapy: continue
        # START = baza (dom). Etykieta pokazuje miasto, ale URL używa pełnego adresu.
        punkty_wyswietlane = [f"🏠 {pracownik.baza_miasto}"]
        # safe="": ukośnik w numerze mieszkania („5/58") nie może rozbić adresu
        # na dwa przystanki w linku Google Maps
        punkty_url = [urllib.parse.quote(baza_punkt, safe="")]
        _ostatni_indeks = len(dzien.etapy) - 1
        for _i, e in enumerate(dzien.etapy):
            # PEŁNY ADRES DOMOWY WYŁĄCZNIE NA POCZĄTKU I NA KOŃCU TRASY.
            # Wcześniej wystarczyło, że przystanek leżał w TYM SAMYM MIEŚCIE
            # co baza (a pierwszy sklep zwykle leży), żeby w środek trasy
            # wskoczył pełny adres zamieszkania — z ulicą i numerem mieszkania.
            # Na mapie wyglądało to jak zbędny wjazd do domu w połowie dnia,
            # a przy okazji rozwoziło adres domowy po linkach.
            if e.dokad == pracownik.baza_miasto and _i == _ostatni_indeks:
                punkty_wyswietlane.append(f"🏠 {pracownik.baza_miasto}")
                punkty_url.append(urllib.parse.quote(baza_punkt, safe=""))
            else:
                punkty_wyswietlane.append(f"{e.dokad}")
                _cel = f"{e.dokad}, {e.dokad_woj}, Polska" if e.dokad_woj else f"{e.dokad}, Polska"
                punkty_url.append(urllib.parse.quote(_cel, safe=""))
        html_content += f"""
            <div class="day-card">
                <div class="day-title">Data: {dzien.data.strftime("%d.%m.%Y")}</div>
                <div class="route"><strong>Trasa:</strong> {" ➔ ".join(punkty_wyswietlane)}</div>
                <a href="https://www.google.com/maps/dir/{"/".join(punkty_url)}" target="_blank" class="btn">🗺️ Otwórz w Google Maps</a>
            </div>
        """
    html_content += "</div></body></html>"
    
    html_path = os.path.join(folder, "Trasy_Mapa.html")
    try:
        with open(html_path, "w", encoding="utf-8") as f: f.write(html_content)
    except OSError:
        raise ValueError("Plik Trasy_Mapa.html jest otwarty w przeglądarce! Zamknij go przed wygenerowaniem.")

def _znajdz_font(nazwa_win: str) -> Optional[str]:
    """Szuka czcionki TTF do PDF-ów — Windows, macOS i Linux.
    nazwa_win to windowsowa nazwa pliku (arial.ttf / arialbd.ttf);
    dla pozostałych systemów mapujemy ją na tamtejsze odpowiedniki
    (macOS: systemowy Arial; Linux: Liberation Sans lub DejaVu Sans,
    które mają pełny zestaw polskich znaków)."""
    bold = "bd" in nazwa_win.lower()
    kandydaci = [
        Path(r"C:\Windows\Fonts") / nazwa_win,
        Path("/System/Library/Fonts/Supplemental") / ("Arial Bold.ttf" if bold else "Arial.ttf"),
        Path("/Library/Fonts") / nazwa_win,
        Path(os.path.expanduser("~/Library/Fonts")) / nazwa_win,
        Path("/usr/share/fonts/truetype/msttcorefonts") / nazwa_win,
        Path("/usr/share/fonts/truetype/liberation") / ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu") / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF") / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
    ]
    for p in kandydaci:
        if p.exists(): return str(p)
    return None

SKROTY_NAZW = (
    ("Trybunalski", "Tryb."), ("Wielkopolski", "Wlkp."), ("Wielkopolska", "Wlkp."),
    ("Mazowiecki", "Maz."), ("Mazowiecka", "Maz."), ("Mazowieckie", "Maz."),
    ("Kujawski", "Kuj."), ("Pomorski", "Pom."), ("Pomorskie", "Pom."),
    ("Lubelski", "Lub."), ("Podlaski", "Podl."), ("Warmiński", "Warm."),
    ("Krakowski", "Krak."), ("Biłgorajski", "Biłg."), ("Kościelny", "Kośc."),
    ("Kaszubski", "Kasz."), ("Białostocki", "Białost."), ("Tarnowski", "Tarn."),
    ("Chełmiński", "Chełm."), ("Szczeciński", "Szcz."), ("Odrzański", "Odrz."),
    ("Sandomierski", "Sand."), ("Iławecki", "Iław."), ("Małopolski", "Młp."),
    ("Gdański", "Gd."), ("Śląski", "Śl."), ("Śląskie", "Śl."), ("Łódzki", "Łódz."),
    ("Dolny", "Dln."), ("Górny", "Gór."), ("Wielki", "Wlk."), ("Nowe Miasto", "N. Miasto"),
)

def nazwa_do_rubryki(pdf, nazwa: str, szerokosc_mm: float) -> str:
    """Nazwa miejscowości dopasowana DO SZEROKOŚCI rubryki na dokumencie.

    Dawniej nazwa była ucinana po 18 znakach i doklejany był wielokropek —
    a że szerokość zależy od liter, a nie od ich liczby, „Tomaszów
    Mazowieck..." i tak wychodził poza kratkę. Najpierw więc próbujemy
    normalnego polskiego skrótu („Tomaszów Maz."), potem zdejmujemy dopisek
    w nawiasie, a dopiero na końcu ucinamy — i to mierząc szerokość."""
    tekst = str(nazwa or "")
    zapas = max(1.0, szerokosc_mm * 0.05)
    limit = szerokosc_mm - zapas
    try:
        if pdf.get_string_width(tekst) <= limit:
            return tekst
    except Exception:
        return tekst[:18] + "..." if len(tekst) > 18 else tekst
    for _pelny, _skrot in SKROTY_NAZW:
        if _pelny in tekst:
            tekst = tekst.replace(_pelny, _skrot)
            if pdf.get_string_width(tekst) <= limit:
                return tekst
    if "(" in tekst:
        bez_nawiasu = tekst.split("(")[0].strip()
        if bez_nawiasu and pdf.get_string_width(bez_nawiasu) <= limit:
            return bez_nawiasu
    while tekst and pdf.get_string_width(tekst + "...") > limit:
        tekst = tekst[:-1]
    return (tekst + "...") if tekst else str(nazwa or "")[:1]

class PDFReport(FPDF):
    def __init__(self):
        super().__init__()
        fr, fb = _znajdz_font("arial.ttf"), _znajdz_font("arialbd.ttf")
        if fr and fb:
            try: self.add_font("Arial", "", fr); self.add_font("Arial", "B", fb)
            except: pass
    def header(self): pass

def _wypelnij_do_sufitu(dni: List[DzienTrasy]) -> List[List[DzienTrasy]]:
    """Kolejne dni pakowane do dokumentu aż po sufit kwoty i wierszy strony.
    Używane dla dni bez przydziału z silnika (np. delegacja z planu wizyt)
    oraz jako twarda kontrola grup, które przyszły z silnika."""
    docs, obecny, koszt, etapy = [], [], 0.0, 0
    for d in dni:
        e = len(d.etapy)
        if (koszt + d.suma > MAX_KWOTA_DOKUMENTU + 0.005
                or etapy + e > MAX_ETAPOW_DOKUMENTU) and obecny:
            docs.append(obecny); obecny, koszt, etapy = [d], d.suma, e
        else: obecny.append(d); koszt += d.suma; etapy += e
    if obecny: docs.append(obecny)
    return docs

def _podziel_na_dokumenty(dni: List[DzienTrasy]) -> List[List[DzienTrasy]]:
    """Dni → polecenia wyjazdu. Sufit 986,34 zł dotyczy DOKUMENTU, nie dnia —
    jeden dokument obejmuje kilka dni.

    Liczba dokumentów wynika z kwoty: bierzemy NAJMNIEJSZĄ, jaka mieści dni pod
    sufitem kwoty i na stronach A4 (pakowanie do sufitu jest tu podziałem
    optymalnym). Przy dniach rozpisanych przez silnik wychodzi z tego dokładnie
    sufit z kwoty przez sufit dokumentu. Kwotę rozkładamy potem na te dokumenty
    równo — dokument zamykamy, gdy kolejny dzień oddalałby go od jego części
    kwoty, ale tylko wtedy, gdy reszta dni nadal mieści się w pozostałych
    dokumentach. Dzięki temu dokumentów nie przybywa, a ostatni nie zostaje
    z resztką. Każdy dzień dostaje numer swojego dokumentu."""
    dni = list(dni)
    if not dni:
        return []
    ile = len(_wypelnij_do_sufitu(dni))          # najmniejsza możliwa liczba
    docs, poz = [], 0
    while poz < len(dni):
        zostalo_dok = ile - len(docs)
        if zostalo_dok <= 1:
            docs.extend(_wypelnij_do_sufitu(dni[poz:]))
            break
        reszta = dni[poz:]
        cel = sum(d.suma for d in reszta) / zostalo_dok
        koszt, etapy, ile_dni = 0.0, 0, 0
        for i, d in enumerate(reszta):
            e = len(d.etapy)
            if ile_dni and (koszt + d.suma > MAX_KWOTA_DOKUMENTU + 0.005
                            or etapy + e > MAX_ETAPOW_DOKUMENTU):
                break
            if (ile_dni and abs(koszt + d.suma - cel) > abs(koszt - cel)
                    and len(_wypelnij_do_sufitu(reszta[i:])) <= zostalo_dok - 1):
                break
            koszt += d.suma; etapy += e; ile_dni += 1
        docs.append(dni[poz:poz + ile_dni])
        poz += ile_dni
    for nr, doc in enumerate(docs, start=1):
        for d in doc:
            d.dokument = nr
    return docs

ZNAKI_ZABRONIONE_W_NAZWIE = '<>:"/\\|?*'

PODFOLDER_POPRZEDNICH = "Poprzednie"

def nazwa_do_pliku(imie: str) -> str:
    """Imię i nazwisko w postaci bezpiecznej dla nazwy pliku i folderu.

    Odstępy idą w „_" (jak dotąd), a znaki zabronione w nazwach Windows —
    < > : " / \\ | ? * — i znaki sterujące znikają; na Windows zapis takiej
    nazwy padał, a program mówił wtedy o pliku „otwartym w innym programie".
    Polskie litery ZOSTAJĄ: pmt_dokumenty i pmt_podpis porównują nazwy po
    zdjęciu ogonków, a Windows, macOS i Linux przyjmują je w nazwach."""
    tekst = "".join(z for z in str(imie or "")
                    if z not in ZNAKI_ZABRONIONE_W_NAZWIE and ord(z) >= 32)
    tekst = "_".join(tekst.split()).strip("_")
    return tekst or "pracownik"

def tekst_stawki(stawka: float) -> str:
    """Stawka za km tak, jak stoi na dokumencie: „1,15", „0,89", „0,60";
    stawka z większą liczbą miejsc dostaje ich tyle, ile trzeba (do czterech)."""
    calosc, ulamek = ("%.4f" % float(stawka)).split(".")
    ulamek = ulamek.rstrip("0")
    ulamek = (ulamek + "00")[:max(2, len(ulamek))]
    return "%s,%s" % (calosc, ulamek)

def kilometry_dokumentu(kwota: float, stawka: float) -> str:
    """Kilometry, które stoją za kwotą dokumentu — do rubryki „(1) Przejazdy".

    Liczone Z KWOTY (kwota / stawka), nie z odcinków trasy: kwoty etapów
    niosą poprawkę groszową, która domyka miesiąc co do grosza, więc suma
    odległości odcinków razy stawka różniłaby się od kwoty dokumentu o kilka
    groszy. Tekst dostaje tyle miejsc po przecinku (1–3), ile trzeba, żeby
    km × stawka po zaokrągleniu do grosza dały DOKŁADNIE kwotę z dokumentu —
    arytmetyka na kartce musi się zgadzać z kalkulatorem. Trzy miejsca
    wystarczają zawsze, gdy stawka nie przekracza 10 zł/km."""
    stawka_dok = float(tekst_stawki(stawka).replace(",", "."))
    kwota = round(float(kwota), 2)
    if stawka_dok <= 0:
        return ""
    km = kwota / stawka_dok
    tekst = "%.3f" % km
    for miejsc in (1, 2, 3):
        proba = "%.*f" % (miejsc, km)
        if round(float(proba) * stawka_dok, 2) == kwota:
            tekst = proba
            break
    return tekst.replace(".", ",")

def opis_przejazdow(kwota: float, stawka: float) -> str:
    """Treść rubryki „(1) Przejazdy": „Prywatny samochód: 312,4 km × 1,15 zł/km".
    Dotąd stała tu formułka o wzorze, a kilometrów ani stawki nie było —
    ten sam komplet przy każdej stawce dawał bajt w bajt ten sam plik."""
    km = kilometry_dokumentu(kwota, stawka)
    if not km:
        return "Prywatny samochód"
    return "Prywatny samochód: %s km × %s zł/km" % (km, tekst_stawki(stawka))

def _slad_podpisu(folder: str) -> bool:
    """Czy poprzedni przebieg w tym folderze ma już coś podpisanego: pliki
    w Do_podpisu/Podpisane albo wpis „podpisany" w manifeście paczki
    (nazwy podfolderów i statusów bierzemy z pmt_podpis, gdy jest)."""
    modul = modul_pomocniczy("pmt_podpis")
    paczka = getattr(modul, "NAZWA_PODFOLDERU", "Do_podpisu")
    podpisane = getattr(modul, "NAZWA_PODPISANE", "Podpisane")
    manifest = getattr(modul, "NAZWA_MANIFESTU", "manifest_podpisu.json")
    status = str(getattr(modul, "STATUS_PODPISANY", "podpisany")).casefold()
    for kat in (os.path.join(folder, paczka, podpisane), os.path.join(folder, podpisane)):
        try:
            if any(os.path.isfile(os.path.join(kat, n)) for n in os.listdir(kat)):
                return True
        except OSError:
            continue
    for sc in (os.path.join(folder, paczka, manifest), os.path.join(folder, manifest)):
        try:
            with open(sc, encoding="utf-8") as f:
                dane = json.load(f)
            for w in (dane.get("pliki") or []):
                if isinstance(w, dict) and str(w.get("status") or "").casefold() == status:
                    return True
        except Exception:
            continue
    return False

def uprzatnij_poprzedni_komplet(folder: str, imie_plik: str, ms: str, rok: int) -> dict:
    """Zdejmuje z folderu wyniku dokumenty POPRZEDNIEGO przebiegu tego samego
    pracownika i miesiąca, zanim powstaną nowe.

    Ponowne generowanie z mniejszą kwotą daje mniej poleceń wyjazdu, a pliki
    o wyższych numerach zostawały z poprzedniego przebiegu — i szły do kadr
    razem z nowymi. Ruszamy WYŁĄCZNIE pliki o nazwach, jakie sami składamy
    (delegacja_NN_imię_miesiąc_rokr.pdf i rozliczenie_wydatków_…), wyłącznie
    w samym folderze (podfoldery Do_podpisu i Podpisane zostają nietknięte)
    i wyłącznie tego pracownika i miesiąca; nazwy porównujemy w NFC i bez
    rozróżniania wielkości liter (macOS zapisuje ogonki w NFD).

    Bez śladu podpisu stare pliki po prostu znikają — to wynik programu, który
    zaraz powstanie od nowa. Gdy poprzedni przebieg ma już ślad podpisu
    (patrz _slad_podpisu), starych plików NIE kasujemy: idą do podfolderu
    „Poprzednie_<data_czas>", żeby podpisane egzemplarze miały obok siebie
    oryginały, do których należą.

    Plik, którego nie da się ruszyć (otwarty w czytniku), zatrzymuje
    generowanie PRZED zapisem czegokolwiek — jak dotąd zatrzymywał je zapis.
    Zwraca słownik: usuniete, przeniesione (nazwy) i dokad (podfolder)."""
    def _norm(nazwa):
        return unicodedata.normalize("NFC", str(nazwa)).casefold()
    sufiks = re.escape(_norm("_%s_%s_%sr.pdf" % (imie_plik, ms, rok)))
    wzor = re.compile(r"^(delegacja_\d+|%s)%s$" % (re.escape(_norm("rozliczenie_wydatków")), sufiks))
    wynik = {"usuniete": [], "przeniesione": [], "dokad": ""}
    try:
        nazwy = os.listdir(folder)
    except OSError:
        return wynik
    stare = sorted(os.path.join(folder, n) for n in nazwy
                   if wzor.match(_norm(n)) and os.path.isfile(os.path.join(folder, n)))
    if not stare:
        return wynik
    dokad = ""
    if _slad_podpisu(folder):
        dokad = os.path.join(folder, "%s_%s" % (
            PODFOLDER_POPRZEDNICH, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))
        os.makedirs(dokad, exist_ok=True)
    for sc in stare:
        nazwa = os.path.basename(sc)
        try:
            if dokad:
                shutil.move(sc, os.path.join(dokad, nazwa))
                wynik["przeniesione"].append(nazwa)
            else:
                os.remove(sc)
                wynik["usuniete"].append(nazwa)
        except OSError:
            raise ValueError(f"Plik PDF jest otwarty w innym programie!\nZamknij: {nazwa}")
    wynik["dokad"] = dokad
    return wynik

def generuj_pdfy(finalne_dni: List[DzienTrasy], pracownik: DanePracownika, miesiac: int, rok: int, folder: str, stawka: float = None, postep_callback=None, zrodlo: dict = None) -> List[dict]:
    if FPDF_BLAD:
        raise ValueError(_opis_bledu_pdf())
    if stawka is None: stawka = STAWKA_ZA_KM
    # Skąd wzięły się kilometry — to stoi na dokumencie, bo od tego zależy,
    # czy podane odległości są realne. Pusta etykieta (stan „brak": ani jeden
    # odcinek nie był liczony) = dokument o źródle milczy, zamiast zapewniać.
    if zrodlo is None: zrodlo = stan_zrodla_odleglosci()
    etykieta_zrodla = str(zrodlo.get("etykieta") or "")
    zrodlo_txt = ("Odległości: %s" % etykieta_zrodla) if etykieta_zrodla else ""
    os.makedirs(folder, exist_ok=True)
    ms = MIESIACE_PL[miesiac - 1]
    imie_plik = nazwa_do_pliku(pracownik.imie)
    # Najpierw porządek: dokumenty poprzedniego przebiegu tego pracownika
    # i miesiąca schodzą z folderu, żeby do kadr nie poszły sieroty.
    uprzatnij_poprzedni_komplet(folder, imie_plik, ms, rok)
    # Gwarancja chronologii: dni zawsze rosnąco wg daty, ZANIM podzielimy je na
    # dokumenty. Dzięki temu daty w obrębie każdego PDF-a idą po kolei.
    finalne_dni = sorted(finalne_dni, key=lambda d: d.data)
    docs = _podziel_na_dokumenty(finalne_dni)
    podsumowanie = []
    firma_nazwa = "PMT HR SP. Z O.O. SP. K." if pracownik.stanowisko == "KR" else "PMT SERVICES SP. Z O.O. SP. K."
    nip_dlugi   = "NIP 779-24-86-133" if pracownik.stanowisko == "KR" else "NIP 779-24-86-127"
    nip_krotki  = "NIP 779-248-61-33" if pracownik.stanowisko == "KR" else "NIP 779-248-61-27"

    total = len(docs)
    for i, doc_dni in enumerate(docs, 1):
        if postep_callback: postep_callback(f"Renderowanie pliku PDF ({i}/{total})...", 0.75 + (i/total)*0.20)
        suma_doc = sum(d.suma for d in doc_dni)
        pdf = PDFReport(); pdf.add_page(); pdf.set_margins(10, 8, 10)
        pdf.set_font("Arial",'B',10); pdf.cell(0,4,firma_nazwa,new_x="LMARGIN",new_y="NEXT")
        pdf.set_font("Arial",'',9); pdf.cell(0,4,"ul. Ptasia 10, 60-319 Poznań",new_x="LMARGIN",new_y="NEXT")
        pdf.cell(0,4,nip_dlugi,new_x="LMARGIN",new_y="NEXT"); pdf.ln(3)
        pdf.set_font("Arial",'B',13); pdf.cell(100,6,"Rozliczenie delegacji",border=0)
        pdf.set_font("Arial",'B',10); pdf.cell(90,6,"6",border=0,new_x="LMARGIN",new_y="NEXT",align='R')
        pdf.set_font("Arial",'',8); pdf.set_xy(pdf.get_x()+130, pdf.get_y()-2); pdf.cell(60,3,"Centrum",border=0,new_x="LMARGIN",new_y="NEXT",align='R'); pdf.ln(3)
        pdf.set_font("Arial",'B',9); pdf.cell(95,5,f"{pracownik.imie} {pracownik.pesel}",border=1,align='C')
        pdf.cell(95,5,pracownik.stanowisko,border=1,new_x="LMARGIN",new_y="NEXT",align='C')
        pdf.set_font("Arial",'',7); pdf.cell(95,3,"imię i nazwisko oraz PESEL",border=0,align='C'); pdf.cell(95,3,"stanowisko",border=0,new_x="LMARGIN",new_y="NEXT",align='C')
        pdf.set_font("Arial",'B',9); pdf.cell(95,5,nazwa_do_rubryki(pdf, pracownik.adres, 95.0),border=1,align='C'); pdf.cell(95,5,_menedzer(),border=1,new_x="LMARGIN",new_y="NEXT",align='C')
        pdf.set_font("Arial",'',7); pdf.cell(95,3,"adres zamieszkania",border=0,align='C'); pdf.cell(95,3,"przełożony",border=0,new_x="LMARGIN",new_y="NEXT",align='C')
        pdf.set_font("Arial",'B',8); pdf.cell(95,5,"projekt: Biedronka, Dino, Eurocash, Społem, Stokrotka, Żabka",border=1,new_x="LMARGIN",new_y="NEXT",align='C')
        pdf.set_font("Arial",'',7); pdf.cell(95,3,"cel wyjazdu - Projekt",border=0,new_x="LMARGIN",new_y="NEXT",align='C'); pdf.ln(3)
        pdf.set_font("Arial",'B',10); pdf.cell(120,5,"Rozliczenie kosztów podróży",border=0)
        pdf.set_font("Arial",'',7); pdf.cell(70,5,zrodlo_txt,border=0,new_x="LMARGIN",new_y="NEXT",align='R')
        pdf.set_font("Arial",'B',8); pdf.cell(65,4,"WYJAZD",border=1,align='C'); pdf.cell(65,4,"PRZYJAZD",border=1,align='C')
        y_s = pdf.get_y(); pdf.cell(35,8,"Środki lokomocji",border=1,align='C'); pdf.cell(25,8,"Koszty",border=1,new_x="LMARGIN",new_y="NEXT",align='C')
        pdf.set_y(y_s+4)
        for lbl in ["miejscowość","data","godz.","miejscowość","data","godz."]:
            pdf.cell(30 if lbl=="miejscowość" else (20 if lbl=="data" else 15),4,lbl,border=1,align='C')
        pdf.set_y(y_s+8); pdf.set_x(10); pdf.set_font("Arial",'',8)
        for dzien in doc_dni:
            for etap in dzien.etapy:
                if pdf.get_y() > 250: pdf.add_page(); pdf.set_margins(10,8,10)
                pdf.cell(30,4.5,nazwa_do_rubryki(pdf, etap.skad, 30.0),border=1)
                pdf.cell(20,4.5,etap.data,border=1,align='C'); pdf.cell(15,4.5,etap.godz_wyj,border=1,align='C')
                pdf.cell(30,4.5,nazwa_do_rubryki(pdf, etap.dokad, 30.0),border=1)
                pdf.cell(20,4.5,etap.data,border=1,align='C'); pdf.cell(15,4.5,etap.godz_przyj,border=1,align='C')
                pdf.cell(35,4.5,"samochód osobowy",border=1,align='C'); pdf.cell(25,4.5,f"{etap.kwota:.2f}",border=1,new_x="LMARGIN",new_y="NEXT",align='R')
                
        pdf.ln(3); pdf.set_font("Arial",'B',8)
        pdf.cell(25,4.5,"Rodzaj",border=1,align='C'); pdf.cell(140,4.5,"Opis kosztu",border=1,align='C'); pdf.cell(25,4.5,"Koszty",border=1,new_x="LMARGIN",new_y="NEXT",align='C')
        pdf.set_font("Arial",'',8)
        for r,o,k in [("(1) Przejazdy",opis_przejazdow(suma_doc, stawka),f"{suma_doc:.2f}"),("(2) Noclegi","Koszt hotelu lub ryczałt 67,50 zł","-"),("(3) Diety","22,50 zł lub 45,00 zł","-"),("(4) Inne","Autostrada, parking, reprezentacja","-")]:
            pdf.cell(25,4.5,r,border=1); pdf.cell(140,4.5,o,border=1); pdf.cell(25,4.5,k,border=1,new_x="LMARGIN",new_y="NEXT",align='R')
        pdf.set_font("Arial",'B',8); pdf.cell(165,4.5,"Suma wydatków",border=1,align='R'); pdf.cell(25,4.5,f"{suma_doc:.2f}",border=1,new_x="LMARGIN",new_y="NEXT",align='R')
        pdf.ln(3); ys = pdf.get_y(); pdf.rect(10,ys,190,24)
        pdf.line(18,ys,18,ys+24); pdf.line(78,ys,78,ys+18); pdf.line(138,ys,138,ys+18); pdf.line(18,ys+18,200,ys+18); pdf.line(180,ys+18,180,ys+24)
        pdf.set_font("Arial",'B',6); yl = ys+1.5
        for letter in "AKCEPTACJA": pdf.set_xy(10,yl); pdf.cell(8,2,letter,align='C'); yl+=2
        pdf.set_font("Arial",'',7)
        for x,sz,ly,txt in [(18,60,ys+13,"podpis Księgowej"), (78,60,ys+13,"podpis Dyrektora Zarządzającego"), (138,62,ys+13,"podpis pracownika")]:
            pdf.line(x+5,ly,x+sz-5,ly); pdf.set_xy(x,ly); pdf.cell(sz,3,txt,align='C')
        pdf.set_font("Arial",'B',8); pdf.set_xy(20,ys+19); pdf.cell(160,3,"Liczba załączników"); pdf.set_xy(180,ys+19); pdf.cell(20,3,"1",align='C')
        
        pdf_path = os.path.join(folder, f"delegacja_{i:02d}_{imie_plik}_{ms}_{rok}r.pdf")
        try: pdf.output(pdf_path)
        except OSError: raise ValueError(f"Plik PDF jest otwarty w innym programie!\nZamknij: delegacja_{i:02d}...pdf")
        podsumowanie.append({'lp':i,'dokument':f"delegacja {i:02d} {pracownik.imie}",'opis':"Koszty dojazdów",'kwota':suma_doc})

    pdf = PDFReport(); pdf.add_page(); pdf.set_margins(10,10,10)
    pdf.set_font("Arial",'B',10); pdf.cell(0,5,firma_nazwa,new_x="LMARGIN",new_y="NEXT")
    pdf.set_font("Arial",'',10); pdf.cell(0,5,"ul. Ptasia 10, 60-319 Poznań",new_x="LMARGIN",new_y="NEXT"); pdf.cell(0,5,nip_krotki,new_x="LMARGIN",new_y="NEXT"); pdf.ln(5)
    pdf.set_font("Arial",'B',12); pdf.cell(0,8,f"Rozliczenie wydatków za miesiąc: {ms} {rok}r.",new_x="LMARGIN",new_y="NEXT"); pdf.ln(2)
    wiersze_naglowka = [("Imię i Nazwisko:",pracownik.imie),("Projekt/Stanowisko:",pracownik.stanowisko),("MENEDŻER:",_menedzer()),("Liczba dokumentów:",str(len(podsumowanie)))]
    if etykieta_zrodla: wiersze_naglowka.append(("Odległości:", etykieta_zrodla))
    for lbl,val in wiersze_naglowka:
        pdf.set_font("Arial",'B',9); pdf.cell(50,6,lbl,border=0); pdf.set_font("Arial",'',9); pdf.cell(140,6,val,border=0,new_x="LMARGIN",new_y="NEXT")
    pdf.ln(5); pdf.set_font("Arial",'B',9)
    for sz,t in [(10,"Lp."),(80,"Dokument"),(70,"Opis"),(30,"Kwota brutto")]: pdf.cell(sz,8,t,border=1,align='C')
    pdf.ln(); suma_g = 0.0; pdf.set_font("Arial",'',9)
    for w in podsumowanie:
        pdf.cell(10,6,f"{w['lp']}.",border=1,align='C'); pdf.cell(80,6,w['dokument'],border=1); pdf.cell(70,6,w['opis'],border=1); pdf.cell(30,6,f"{w['kwota']:.2f}",border=1,new_x="LMARGIN",new_y="NEXT",align='R'); suma_g += w['kwota']
    for idx in range(len(podsumowanie)+1,14):
        pdf.cell(10,6,f"{idx}.",border=1,align='C'); pdf.cell(80,6,"",border=1); pdf.cell(70,6,"",border=1); pdf.cell(30,6,"",border=1,new_x="LMARGIN",new_y="NEXT")
    pdf.cell(160,6,"zaliczka:",border=0,align='R'); pdf.cell(30,6,"",border=1,new_x="LMARGIN",new_y="NEXT")
    pdf.set_font("Arial",'B',9); pdf.cell(160,6,"Suma wydatków global:",border=0,align='R'); pdf.cell(30,6,f"{suma_g:.2f}",border=1,new_x="LMARGIN",new_y="NEXT",align='R')
    
    pdf_path_summary = os.path.join(folder,f"rozliczenie_wydatków_{imie_plik}_{ms}_{rok}r.pdf")
    try: pdf.output(pdf_path_summary)
    except OSError: raise ValueError(f"Plik podsumowania jest otwarty w innym programie!\nZamknij: rozliczenie_wydatków...pdf")
    try:
        online_zdarzenie(dokumenty=len(podsumowanie))
        try:
            _st = _wczytaj(PLIK_STATUSU, {})
            _st["dokumenty_sesja"] = int(_st.get("dokumenty_sesja", 0)) + len(podsumowanie)
            _zapisz(PLIK_STATUSU, _st)
        except Exception:
            pass
        online_synchronizuj_w_tle()   # dane w arkuszu od razu, nie za 15 min
    except Exception:
        pass
    return podsumowanie

def dni_delegacji_z_planu(plan: dict, pracownik: DanePracownika, stawka: float,
                          postep_cb=None) -> dict:
    """MOST plan -> delegacja (3.20.50): z wczytanego z Excela i ulozonego
    PLANU WIZYT buduje realne dni delegacji: baza -> sklepy w kolejnosci
    planu -> baza, z faktycznymi kilometrami DROGOWYMI (OSRM + cache,
    offline fallback). ZERO skalowania do kwoty - kwota kazdego etapu to
    realny dystans x stawka. Zwraca {(rok, mies): [DzienTrasy]}."""
    zeruj_zrodlo_odleglosci()
    ust = ustawienia_planowania()
    predk = max(10.0, float(ust.get("predkosc") or PLAN_SREDNIA_PREDKOSC_KMH))
    czas_w = float(ust.get("czas_wizyty") or PLAN_CZAS_WIZYTY_MIN)
    dni_zrodlo = [d for d in (plan or {}).get("dni", []) if getattr(d, "wizyty", None)]
    grupy = {}
    ost4 = str(getattr(pracownik, "pesel", "") or "")[-4:]
    rng_g = random.Random(int(ost4) if ost4.isdigit() else 7)

    def _mce(p):
        m = (getattr(p, "miasto", "") or "").strip()
        if m:
            return m
        n = (getattr(p, "nazwa", "") or getattr(p, "adres", "") or "?").strip()
        return n.split(",")[0][:24]

    for nr, d in enumerate(dni_zrodlo):
        if postep_cb:
            postep_cb("Realne kilometry: dzien %d/%d..." % (nr + 1, len(dni_zrodlo)),
                      0.10 + 0.60 * (nr + 1) / max(1, len(dni_zrodlo)))
        wiz = [p for p in d.wizyty if p.lat is not None and p.lng is not None]
        if not wiz:
            continue
        data_str = d.data.strftime("%d.%m.%Y")
        et = []
        sk_naz, sk_lat, sk_lng = pracownik.baza_miasto, pracownik.baza_lat, pracownik.baza_lng
        cele = [( _mce(p), p.lat, p.lng ) for p in wiz]
        cele.append((pracownik.baza_miasto, pracownik.baza_lat, pracownik.baza_lng))
        for ci, (c_naz, c_lat, c_lng) in enumerate(cele):
            try:
                km = dystans_drogowy(sk_lat, sk_lng, c_lat, c_lng)
                zrodlo_odc = zrodlo_ostatniego_odcinka()
            except Exception:
                _odnotuj_zrodlo(ZRODLO_SZACUNEK)
                zrodlo_odc = ZRODLO_SZACUNEK
                km = oblicz_dystans(sk_lat, sk_lng, c_lat, c_lng) * TEST_MNOZNIK_TRASY
            ostatni = (ci == len(cele) - 1)
            et.append(RawEtap(skad=sk_naz, dokad=c_naz, data_str=data_str,
                              d_line=max(float(km or 0.0), 0.1), zrodlo=zrodlo_odc,
                              czas_w_sklepie=(0.0 if ostatni else czas_w),
                              dokad_woj=pracownik.wojewodztwo,
                              skad_lat=sk_lat, skad_lng=sk_lng,
                              dokad_lat=c_lat, dokad_lng=c_lng))
            sk_naz, sk_lat, sk_lng = c_naz, c_lat, c_lng
        for e in et:
            e.dystans_rzeczywisty = e.d_line
            e.kwota = max(round(e.d_line * float(stawka), 2), 0.0)
            e.czas_jazdy_minuty = (e.d_line / predk) * 60.0
        dz = DzienTrasy(data=d.data, etapy_surowe=et)
        czas_akt = rng_g.randint(7 * 60, 8 * 60)
        polowa = len(et) // 2
        for idx, e in enumerate(et):
            godz_wyj = "%02d:%02d" % (int(czas_akt // 60) % 24, int(czas_akt % 60))
            czas_akt += e.czas_jazdy_minuty
            godz_przyj = "%02d:%02d" % (int(czas_akt // 60) % 24, int(czas_akt % 60))
            dz.etapy.append(Etap(skad=e.skad, dokad=e.dokad, data=e.data_str,
                                 godz_wyj=godz_wyj, godz_przyj=godz_przyj,
                                 kwota=e.kwota, dokad_woj=e.dokad_woj))
            czas_akt += e.czas_w_sklepie
            if idx == polowa:
                czas_akt += PRZERWA_JEDZENIE_MIN
        grupy.setdefault((d.data.year, d.data.month), []).append(dz)
    try:
        _zapisz_road_cache()
    except Exception:
        pass
    return grupy

class PrzerwanoGenerowanie(BaseException):
    """Użytkownik przerwał generowanie — to nie jest błąd programu.

    Dziedziczy po BaseException, a nie po Exception, ŚWIADOMIE: leci przez
    wnętrze generuj_trasy, gdzie po drodze stoi niejeden „except Exception".
    Przerwanie ma dojść do końca, a nie zostać po cichu połknięte i zamienić
    się w połowiczny wynik."""

def slad_dnia(dzien) -> tuple:
    """Lekki ślad ułożonego dnia dla interfejsu: (data, ((miejscowość,
    szerokość, długość), ...)) — od bazy przez przystanki z powrotem do bazy.
    Krotka, więc okno dostaje kopię, której silnik już nie zmieni (odcinki
    skalują się i przycinają dopiero po ułożeniu wszystkich dni)."""
    etapy = list(getattr(dzien, "etapy_surowe", None) or [])
    if not etapy:
        return (getattr(dzien, "data", None), ())
    punkty = [(etapy[0].skad, float(etapy[0].skad_lat), float(etapy[0].skad_lng))]
    for e in etapy:
        punkty.append((e.dokad, float(e.dokad_lat), float(e.dokad_lng)))
    return (dzien.data, tuple(punkty))

def _dziennik_animacji(tekst, nowy=False):
    """Dziennik diagnostyczny programu: PMT_diagnostyka_animacji.txt
    (nazwa została po animacji startowej, której od 3.23.0 nie ma)
    w KATALOGU UŻYTKOWNIKA (a gdy tam się nie da — obok programu).

    Kolejność jest odwrócona względem 3.20.57 celowo. Program dopisywał
    do tego pliku ponad dwadzieścia razy przy KAŻDYM starcie, i to prosto
    do własnego katalogu instalacyjnego. Program, który przy starcie
    modyfikuje pliki w swoim folderze, to zachowanie, które ochrona
    Windows traktuje podejrzliwie — a w folderze wymagającym uprawnień
    (np. C:\Program Files) każdy taki zapis i tak się nie udaje."""
    try:
        linia = "%s | %s\n" % (datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], tekst)
        if getattr(sys, "frozen", False):
            kat_prog = os.path.dirname(os.path.abspath(sys.executable))
        else:
            kat_prog = os.path.dirname(os.path.abspath(__file__))
        for kat in (os.path.expanduser("~"), kat_prog):
            try:
                with open(os.path.join(kat, "PMT_diagnostyka_animacji.txt"),
                          "w" if nowy else "a", encoding="utf-8") as f:
                    f.write(linia)
                return
            except Exception:
                continue
    except Exception:
        pass
