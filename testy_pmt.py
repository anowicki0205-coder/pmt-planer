# -*- coding: utf-8 -*-
"""
TESTY PMT PLANERA — uruchom przed każdym wydaniem.

    python testy_pmt.py            (pełny zestaw, ~2 minuty)
    python testy_pmt.py --szybko   (bez generowania tras i PDF-ów, ~5 sekund)

Testy NIE wymagają internetu ani konta. Nie ruszają Twoich danych —
pracują na tymczasowym katalogu domowym.

Wynik: lista PRZESZŁO / NIE PRZESZŁO i kod wyjścia 0 albo 1.
"""

import os
import re
import sys
import json
import glob
import shutil
import tempfile
import datetime

KATALOG = os.path.dirname(os.path.abspath(__file__))
SZYBKO = "--szybko" in sys.argv

# Własny katalog domowy — testy nie dotykają prawdziwych danych użytkownika.
_TMP_HOME = tempfile.mkdtemp(prefix="pmt_testy_")
os.environ["HOME"] = _TMP_HOME
os.environ["USERPROFILE"] = _TMP_HOME
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, KATALOG)

WYNIKI = []


def sprawdz(nazwa, warunek, szczegol=""):
    WYNIKI.append((bool(warunek), nazwa, szczegol))
    print("  %s  %s%s" % ("[ OK ]" if warunek else "[BŁĄD]", nazwa,
                          ("  — " + szczegol) if szczegol and not warunek else ""))
    return bool(warunek)


def sekcja(tytul):
    print("\n" + tytul)
    print("-" * len(tytul))


# ══════════════════════════════════════════════════════════════════
sekcja("1. Import programu i spójność numerów wersji")

import PMT_Delegacje as P                                    # noqa: E402

sprawdz("program importuje się bez błędu", True)

_wersja_txt = ""
_min_txt = ""
_blok_txt = ""
try:
    with open(os.path.join(KATALOG, "wersja.txt"), encoding="utf-8") as f:
        _linie = [l.strip() for l in f if l.strip()]
    _wersja_txt = _linie[0] if _linie else ""
    for l in _linie[1:]:
        m = l.lower().replace(" ", "")
        if m.startswith("min="):
            _min_txt = l.split("=", 1)[1].strip()
        elif m.startswith("blokada="):
            _blok_txt = l.split("=", 1)[1].strip()
except Exception as e:
    print("   (nie udało się wczytać wersja.txt: %s)" % e)

sprawdz("wersja.txt zgadza się ze źródłem",
        _wersja_txt == P.WERSJA_PROGRAMU,
        "wersja.txt=%s, źródło=%s" % (_wersja_txt, P.WERSJA_PROGRAMU))

_exe_txt = ""
try:
    with open(os.path.join(KATALOG, "wersja_exe.txt"), encoding="utf-8") as f:
        _exe_txt = f.read()
except Exception:
    pass
sprawdz("wersja_exe.txt zawiera bieżący numer",
        P.WERSJA_PROGRAMU in _exe_txt,
        "brak %s w wersja_exe.txt" % P.WERSJA_PROGRAMU)

_krotka = tuple(int(x) for x in P.WERSJA_PROGRAMU.split(".")[:3])
sprawdz("wersja_exe.txt ma zgodne filevers",
        ("filevers=(%d, %d, %d, 0)" % _krotka) in _exe_txt.replace(" ", " "),
        "oczekiwano filevers=(%d, %d, %d, 0)" % _krotka)

sprawdz("min= w wersja.txt nie jest wyższe niż wydawana wersja",
        (not _min_txt) or P._wersja_na_liczbe(_min_txt) <= P._wersja_na_liczbe(P.WERSJA_PROGRAMU),
        "min=%s > %s — ta wersja zablokowałaby sama siebie" % (_min_txt, P.WERSJA_PROGRAMU))

if _blok_txt:
    sprawdz("blokada= ma format RRRR-MM-DD",
            bool(re.match(r"^\d{4}-\d{2}-\d{2}$", _blok_txt)),
            "blokada=%s (Windows/Excel lubi podmieniać na DD.MM.RRRR)" % _blok_txt)


# ══════════════════════════════════════════════════════════════════
sekcja("2. Brak danych osobowych w kodzie")

_PLIKI_TEKSTOWE = []
for wzor in ("*.py", "*.txt", "*.md", "*.bat", "*.gs", "*.json", "*.html", "*.js", "*.yml"):
    _PLIKI_TEKSTOWE += glob.glob(os.path.join(KATALOG, wzor))

# PESEL: 11 cyfr pod rząd (poza oczywistymi atrapami w testach)
_ATRAPY = {"90010112345", "00000000000", "12345678901", "85010112345"}
_pesele = []
_nazwiska = []
# nazwisko przełożonego: dwa słowa z wielkiej litery obok słowa "MENEDŻER"/"przełożony"
for sciezka in _PLIKI_TEKSTOWE:
    if os.path.basename(sciezka) in ("testy_pmt.py",):
        continue
    try:
        with open(sciezka, encoding="utf-8", errors="ignore") as f:
            tresc = f.read()
    except Exception:
        continue
    # Ograniczniki alfanumeryczne, żeby nie łapać fragmentów skrótów SHA,
    # i kontrola sumy kontrolnej — prawdziwy PESEL musi ją mieć poprawną.
    for m in re.finditer(r"(?<![0-9A-Za-z])(\d{11})(?![0-9A-Za-z])", tresc):
        kandydat = m.group(1)
        if kandydat in _ATRAPY:
            continue
        try:
            if not P.waliduj_pesel(kandydat):
                continue
        except Exception:
            pass
        _pesele.append((os.path.basename(sciezka), kandydat))
    for m in re.finditer(r'"([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+ [A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)"', tresc):
        kontekst = tresc[max(0, m.start() - 120):m.start()].lower()
        if any(s in kontekst for s in ("menedżer", "menedzer", "przełożony", "przelozony")):
            _nazwiska.append((os.path.basename(sciezka), m.group(1)))

sprawdz("brak zaszytego numeru PESEL", not _pesele, str(_pesele[:3]))
sprawdz("brak zaszytego nazwiska przełożonego", not _nazwiska, str(_nazwiska[:3]))

# _menedzer() — źródła
P._ustawienia_reset()
sprawdz("_menedzer() bez ustawień i bez pliku zwraca pusty tekst",
        P._menedzer() == "", repr(P._menedzer()))

P.zapisz_ustawienie("menedzer", "Jan Przykładowy")
P._ustawienia_reset()
sprawdz("_menedzer() czyta ustawienie programu",
        P._menedzer() == "Jan Przykładowy", repr(P._menedzer()))
P.zapisz_ustawienie("menedzer", "")
P._ustawienia_reset()

_plik_men = os.path.join(KATALOG, "menedzer.txt")
_bylo = os.path.exists(_plik_men)
if not _bylo:
    for _kod, _opis in (("utf-8", "UTF-8"), ("utf-8-sig", "UTF-8 z BOM"), ("cp1250", "cp1250")):
        try:
            with open(_plik_men, "w", encoding=_kod) as f:
                f.write("  Jan Przykładowy  \r\n")
            P._ustawienia_reset()
            sprawdz("_menedzer() czyta menedzer.txt (%s)" % _opis,
                    P._menedzer() == "Jan Przykładowy", repr(P._menedzer()))
        except Exception as e:
            sprawdz("_menedzer() czyta menedzer.txt (%s)" % _opis, False, str(e))
    try:
        os.remove(_plik_men)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
sekcja("3. Obowiązkowa aktualizacja (min= / blokada=)")


def _wymagania(tresc):
    """Uruchamia prawdziwy parser programu na podanej treści wersja.txt."""
    P.WERSJA_WYMAGANA = ""
    P.TERMIN_BLOKADY = ""
    return P._czytaj_wymagania_z_tekstu(tresc)


_WARIANTY = {
    "numer + opis + min + blokada": "3.99.0\nOpis nowości.\nmin=3.99.0\nblokada=2099-12-01\n",
    "bez linii z opisem": "3.99.0\nmin=3.99.0\nblokada=2099-12-01\n",
    "min przed opisem": "3.99.0\nmin=3.99.0\nOpis nowości.\nblokada=2099-12-01\n",
    "opis w dwóch liniach": "3.99.0\nOpis 1\nOpis 2\nmin=3.99.0\nblokada=2099-12-01\n",
    "spacje i wielkie litery": "3.99.0\nOpis.\nMIN = 3.99.0\nBLOKADA = 2099-12-01\n",
}
for _nazwa, _tresc in _WARIANTY.items():
    _wymagania(_tresc)
    sprawdz("parser wersja.txt: %s" % _nazwa,
            P.WERSJA_WYMAGANA == "3.99.0" and P.TERMIN_BLOKADY == "2099-12-01",
            "min=%r blokada=%r" % (P.WERSJA_WYMAGANA, P.TERMIN_BLOKADY))

_dzis = datetime.date.today()
_PRZYPADKI = [
    ("wersja aktualna", P.WERSJA_PROGRAMU, (_dzis + datetime.timedelta(days=1)).isoformat(), False),
    ("stara wersja, termin za 30 dni", "9.99.9", (_dzis + datetime.timedelta(days=30)).isoformat(), False),
    ("stara wersja, termin minął", "9.99.9", (_dzis - datetime.timedelta(days=1)).isoformat(), True),
    ("stara wersja, termin dzisiaj", "9.99.9", _dzis.isoformat(), True),
]
for _opis, _min, _term, _oczek in _PRZYPADKI:
    P.WERSJA_WYMAGANA, P.TERMIN_BLOKADY = _min, _term
    _zab, _dni = P.wersja_zablokowana()
    sprawdz("blokada: %s" % _opis, _zab == _oczek, "zablokowana=%s (oczekiwano %s)" % (_zab, _oczek))

# data po polsku nie może zablokować całego zespołu
P.WERSJA_WYMAGANA, P.TERMIN_BLOKADY = "9.99.9", (_dzis + datetime.timedelta(days=30)).strftime("%d.%m.%Y")
_zab, _dni = P.wersja_zablokowana()
sprawdz("blokada: data w formacie DD.MM.RRRR jest rozumiana",
        _zab is False and _dni == 30, "zablokowana=%s dni=%s" % (_zab, _dni))

P.WERSJA_WYMAGANA, P.TERMIN_BLOKADY = "9.99.9", "zupełnie-nie-data"
_zab, _dni = P.wersja_zablokowana()
sprawdz("blokada: nieczytelna data NIE odcina programu (fail-open)",
        _zab is False, "zablokowana=%s" % _zab)

P.WERSJA_WYMAGANA, P.TERMIN_BLOKADY = "9.99.9", ""
_zab, _dni = P.wersja_zablokowana()
sprawdz("blokada: brak terminu daje okres przejściowy, nie natychmiastowe odcięcie",
        _zab is False and _dni is not None, "zablokowana=%s dni=%s" % (_zab, _dni))

# trwałość wymagań (blokada działa też bez internetu)
P.WERSJA_WYMAGANA = "9.99.9"
P.TERMIN_BLOKADY = (_dzis + datetime.timedelta(days=3)).isoformat()
P._zapisz_wymagania()
P.WERSJA_WYMAGANA = P.TERMIN_BLOKADY = ""
P._wczytaj_wymagania()
sprawdz("wymagania przeżywają restart bez internetu",
        P.WERSJA_WYMAGANA == "9.99.9", "min=%r" % P.WERSJA_WYMAGANA)

# cofnięcie zegara nie może zdjąć blokady
P.WERSJA_WYMAGANA = "9.99.9"
P.TERMIN_BLOKADY = (_dzis - datetime.timedelta(days=5)).isoformat()
sprawdz("przeterminowana wersja jest zablokowana", P.wersja_zablokowana()[0] is True)

P.WERSJA_WYMAGANA = P.TERMIN_BLOKADY = ""
try:
    os.remove(P.PLIK_WYMAGAN)
except Exception:
    pass


# ══════════════════════════════════════════════════════════════════
sekcja("4. Rozdzielenie danych między kontami")


def _wyczysc_dom():
    for w in glob.glob(os.path.join(_TMP_HOME, ".pmt_*")):
        try:
            os.remove(w)
        except Exception:
            pass
    P._ustawienia_reset()
    P._resetuj_pamiec_kont()


_wyczysc_dom()
P.ustaw_uzytkownika_planu("Anna Kowalska", "11111")
_klucz_a = P.AKTYWNY_UZYTKOWNIK
P.zapisz_ustawienie_osobiste("adres_bazy", "ul. Anny 1, Radom")
P.zapisz_punkty([{"adres": "Sklep A", "siec": "Żabka", "miasto": "Radom"}])
P.ustaw_notatke_dnia(_dzis.isoformat(), "notatka Anny", False)
P.ustaw_odwiedzona(_dzis, "Sklep A", True, "byłam")
with open(P._plik_planu(), "w", encoding="utf-8") as f:
    json.dump({"miesiace": [{"rok": 2026, "miesiac": 10, "dni": []}]}, f)
P._zapisz(P.PLIK_STATUSU, {"kod": "11111", "imie": "Anna Kowalska",
                           "wazne_do": "2099-12-31", "skrot": "xxx"})

P.online_zapisz_kod("22222")          # tak samo jak przy prawdziwym logowaniu
P.ustaw_uzytkownika_planu("Bartosz Nowak", "22222")
_klucz_b = P.AKTYWNY_UZYTKOWNIK
sprawdz("klucze kont są różne", _klucz_a != _klucz_b)
sprawdz("nowe konto nie widzi planu poprzedniej osoby", P.wczytaj_plan() is None)
sprawdz("nowe konto nie widzi adresu bazy poprzedniej osoby",
        P.ustawienie_osobiste("adres_bazy", "") == "",
        repr(P.ustawienie_osobiste("adres_bazy", "")))
sprawdz("nowe konto nie widzi listy punktów poprzedniej osoby",
        P.wczytaj_punkty() == [], repr(P.wczytaj_punkty()))
sprawdz("nowe konto nie widzi notatek dnia poprzedniej osoby",
        P.notatka_dnia(_dzis.isoformat()).get("notatka", "") == "",
        repr(P.notatka_dnia(_dzis.isoformat())))
sprawdz("nowe konto nie widzi dziennika wizyt poprzedniej osoby",
        P.czy_odwiedzona(_dzis, "Sklep A") is False)
_w, _d, _im = P.online_status_sesji()
sprawdz("nowe konto nie dziedziczy sesji poprzedniej osoby",
        not (_w is True and _im == "Anna Kowalska"),
        "status=%s dni=%s imie=%r" % (_w, _d, _im))

# powrót na konto A — dane muszą wrócić
P.online_zapisz_kod("11111")
P.ustaw_uzytkownika_planu("Anna Kowalska", "11111")
sprawdz("powrót na pierwsze konto przywraca jego adres bazy",
        P.ustawienie_osobiste("adres_bazy", "") == "ul. Anny 1, Radom",
        repr(P.ustawienie_osobiste("adres_bazy", "")))
sprawdz("powrót na pierwsze konto przywraca jego punkty",
        len(P.wczytaj_punkty()) == 1)

# klucz konta nie może zależeć od pisowni imienia z arkusza
sprawdz("klucz konta zależy tylko od loginu (zmiana imienia nie gubi danych)",
        P._klucz_konta_dla("Anna Kowalska", "11111") == P._klucz_konta_dla("A. Kowalska", "11111"))


# ══════════════════════════════════════════════════════════════════
sekcja("4b. Przejęcie danych sprzed 3.21.0")


def _stan_sprzed_3210(kody_w_historii):
    """Odtwarza katalog domowy tak, jak zostawiała go wersja 3.20.57."""
    _wyczysc_dom()
    for w in glob.glob(os.path.join(_TMP_HOME, ".pmt_*")):
        try:
            os.remove(w)
        except Exception:
            pass
    P.AKTYWNY_UZYTKOWNIK = ""
    P._ustawienia_reset()
    P._resetuj_pamiec_kont()
    with open(P.PUNKTY_STORE, "w", encoding="utf-8") as f:
        json.dump([{"adres": "Sklep X", "siec": "Żabka", "miasto": "Radom"}], f)
    with open(P.WIZYTY_STORE, "w", encoding="utf-8") as f:
        json.dump({P.klucz_wizyty(_dzis, "Sklep X"): {"czas": "x", "notatka": "n"}}, f)
    with open(P.NOTATKI_DNI_STORE, "w", encoding="utf-8") as f:
        json.dump({_dzis.isoformat(): {"notatka": "urlop", "wolne": True}}, f)
    P.zapisz_ustawienie("adres_bazy", "ul. Wspólna 1, Radom")
    with open(P.PLIK_LOGOWAN, "w", encoding="utf-8") as f:
        json.dump({k: {"imie": "Ktoś %s" % k, "skrot": "x",
                       "ostatnio": "2026-09-01T10:00:00"} for k in kody_w_historii}, f)
    P._ustawienia_reset()


# A. komputer używany dotąd przez JEDNĄ osobę — dane mają przejść na jej konto
_stan_sprzed_3210(["11111"])
P.online_zapisz_kod("11111")
P.ustaw_uzytkownika_planu("Anna Kowalska", "11111")
sprawdz("jedyny użytkownik komputera zachowuje listę punktów",
        len(P.wczytaj_punkty()) == 1, repr(P.wczytaj_punkty()))
sprawdz("jedyny użytkownik komputera zachowuje dziennik wizyt",
        P.czy_odwiedzona(_dzis, "Sklep X") is True)
sprawdz("jedyny użytkownik komputera zachowuje notatki dni",
        P.notatka_dnia(_dzis.isoformat()).get("notatka") == "urlop",
        repr(P.notatka_dnia(_dzis.isoformat())))
sprawdz("jedyny użytkownik komputera zachowuje adres bazy",
        P.ustawienie_osobiste("adres_bazy", "") == "ul. Wspólna 1, Radom",
        repr(P.ustawienie_osobiste("adres_bazy", "")))
sprawdz("wspólne pliki zostają jako kopia .sprzed_3.21.0",
        len(glob.glob(os.path.join(_TMP_HOME, ".*.sprzed_3.21.0"))) >= 3,
        str(sorted(os.path.basename(x) for x in glob.glob(os.path.join(_TMP_HOME, ".*")))[:8]))

# B. komputer WSPÓLNY — nikt nie dostaje cudzych danych
_stan_sprzed_3210(["11111", "22222"])
P.online_zapisz_kod("22222")
P.ustaw_uzytkownika_planu("Bartosz Nowak", "22222")
sprawdz("na wspólnym komputerze nowe konto NIE dostaje cudzych punktów",
        P.wczytaj_punkty() == [], repr(P.wczytaj_punkty()))
sprawdz("na wspólnym komputerze nowe konto NIE dostaje cudzego dziennika",
        P.czy_odwiedzona(_dzis, "Sklep X") is False)
sprawdz("na wspólnym komputerze nowe konto NIE dostaje cudzych notatek",
        P.notatka_dnia(_dzis.isoformat()).get("notatka", "") == "")
sprawdz("na wspólnym komputerze nowe konto NIE dostaje cudzego adresu bazy",
        P.ustawienie_osobiste("adres_bazy", "") == "")
sprawdz("na wspólnym komputerze wspólne pliki zostają nietknięte",
        os.path.exists(P.PUNKTY_STORE) and os.path.exists(P.WIZYTY_STORE))

_wyczysc_dom()

# ══════════════════════════════════════════════════════════════════
sekcja("4c. Kopia zapasowa i odtworzenie")

_wyczysc_dom()
P.online_zapisz_kod("11111")
P.ustaw_uzytkownika_planu("Anna Kowalska", "11111")
P.zapisz_punkty([{"adres": "Sklep Kopia", "siec": "Dino", "miasto": "Radom"}])
P.ustaw_notatke_dnia(_dzis.isoformat(), "notatka do kopii", False)
_zip_nowy = os.path.join(_TMP_HOME, "kopia_nowa.zip")
_ile = P.eksportuj_kopie_zapasowa(_zip_nowy)
sprawdz("kopia zapasowa powstaje", _ile >= 2, "%d plików" % _ile)
sprawdz("kopia zapasowa daje się zweryfikować",
        bool(P.sprawdz_kopie_zapasowa(_zip_nowy)))

# skasuj dane i odtwórz
for w in glob.glob(os.path.join(_TMP_HOME, ".pmt_punkty*")) + \
         glob.glob(os.path.join(_TMP_HOME, ".pmt_notatki*")):
    try:
        os.remove(w)
    except Exception:
        pass
P._resetuj_pamiec_kont()
sprawdz("po skasowaniu danych lista punktów jest pusta", P.wczytaj_punkty() == [])
P.przywroc_z_kopii(_zip_nowy)
P._resetuj_pamiec_kont()
sprawdz("odtworzenie z kopii przywraca punkty", len(P.wczytaj_punkty()) == 1,
        repr(P.wczytaj_punkty()))
sprawdz("odtworzenie z kopii przywraca notatki dni",
        P.notatka_dnia(_dzis.isoformat()).get("notatka") == "notatka do kopii")

# kopia w STARYM formacie (nazwy plików sprzed 3.21.0) też musi się odtworzyć
_zip_stary = os.path.join(_TMP_HOME, "kopia_stara.zip")
import zipfile as _zf
with _zf.ZipFile(_zip_stary, "w") as _z:
    _z.writestr(os.path.basename(P.PUNKTY_STORE),
                json.dumps([{"adres": "Sklep Stary", "siec": "Lewiatan", "miasto": "Kielce"}]))
    _z.writestr("_manifest_pmt.json", json.dumps({"program": "PMT Planer", "pliki": ["punkty"]}))
P.przywroc_z_kopii(_zip_stary)
P._resetuj_pamiec_kont()
sprawdz("odtworzenie kopii sprzed 3.21.0 też działa",
        [x["adres"] for x in P.wczytaj_punkty()] == ["Sklep Stary"],
        repr(P.wczytaj_punkty()))
_wyczysc_dom()

# ══════════════════════════════════════════════════════════════════
sekcja("5. Zachowanie bezpieczne dla zabezpieczeń Windows")

with open(os.path.join(KATALOG, "PMT_Delegacje.py"), encoding="utf-8") as f:
    _zrodlo = f.read()

sprawdz("program nie uruchamia PowerShella przy starcie",
        "ExecutionPolicy" not in _zrodlo and "Unblock-File" not in _zrodlo,
        "znaleziono wywołanie PowerShella — to zapalnik dla Defendera")
sprawdz("program nie kasuje plików poza własnym katalogiem bez zgody",
        P.AUTOMATYCZNE_SPRZATANIE_DYSKU is False,
        "automatyczne skanowanie i kasowanie plików użytkownika jest włączone")


# ══════════════════════════════════════════════════════════════════
if not SZYBKO:
    sekcja("6. Silnik delegacji — kwoty, czas dnia, odległości")

    _BAZY = [
        ("Radom", 51.40, 21.15, "mazowieckie"),
        ("Lublin", 51.25, 22.57, "lubelskie"),
        ("Bydgoszcz", 53.12, 18.01, "kujawsko-pomorskie"),
        ("Białystok", 53.13, 23.16, "podlaskie"),
    ]
    _KWOTY = [1500.0, 3000.0, 4700.0]
    _rok, _mies = 2026, 10
    _dni_robocze = P.pobierz_dni_robocze(_rok, _mies)
    _stawka = 0.89
    _ostatnie = None
    for _nazwa, _lat, _lng, _woj in _BAZY:
        for _kwota in _KWOTY:
            _dni = P.generuj_trasy(_kwota, _nazwa, _lat, _lng, _woj, _dni_robocze,
                                   "90010112345", stawka=_stawka)
            _suma = sum(d.suma for d in _dni)
            _czas_max = 0.0
            _najbl = 1e9
            for _d in _dni:
                _c = P.PRZERWA_JEDZENIE_MIN
                for _e in _d.etapy_surowe:
                    _c += (_e.czas_jazdy_minuty or 0) + (_e.czas_w_sklepie or 0)
                _czas_max = max(_czas_max, _c)
                for _e in _d.etapy_surowe[:-1]:
                    _najbl = min(_najbl, P.oblicz_dystans(_lat, _lng, _e.dokad_lat, _e.dokad_lng))
            _docs = P._podziel_na_dokumenty(sorted(_dni, key=lambda x: x.data))
            _max_doc = max((sum(d.suma for d in doc) for doc in _docs), default=0)
            _max_et = max((sum(len(d.etapy) for d in doc) for doc in _docs), default=0)
            _et = "%s %.0f zł" % (_nazwa, _kwota)
            sprawdz("kwota rozpisana co do grosza: %s" % _et,
                    abs(_suma - _kwota) <= 0.01, "wyszło %.2f zł" % _suma)
            sprawdz("dzień nie przekracza limitu godzin: %s" % _et,
                    _czas_max <= P.LIMIT_CZASU_MINUTY + 0.5, "%.1f min" % _czas_max)
            sprawdz("żaden przystanek nie leży pod domem: %s" % _et,
                    _najbl >= P.MIN_ODLEGLOSC_OD_BAZY - 0.05, "%.1f km" % _najbl)
            sprawdz("dokument mieści się w sufitach: %s" % _et,
                    _max_doc <= P.MAX_KWOTA_DOKUMENTU + 0.01 and _max_et <= P.MAX_ETAPOW_DOKUMENTU,
                    "%.2f zł / %d etapów" % (_max_doc, _max_et))
            _ostatnie = (_dni, _nazwa, _lat, _lng, _woj)

    sekcja("6b. Przypadki krańcowe silnika")

    # Kwota minimalna — musi się rozpisać co do grosza.
    _dni_min = P.generuj_trasy(P.MIN_KWOTA, "Radom", 51.40, 21.15, "mazowieckie",
                               _dni_robocze, "90010112345", stawka=0.89)
    sprawdz("kwota minimalna (%.0f zł) rozpisana co do grosza" % P.MIN_KWOTA,
            abs(sum(d.suma for d in _dni_min) - P.MIN_KWOTA) <= 0.01,
            "%.2f zł" % sum(d.suma for d in _dni_min))

    # Kwota bardzo wysoka — silnik nie musi jej dobić (uczciwie o tym mówi),
    # ale ma wykorzystać miesiąc porządnie. Ten test pilnuje, żeby zmiany
    # w trasie awaryjnej nie obcięły po cichu pokrycia.
    _kwota_duza = 11000.0
    _dni_duze = P.generuj_trasy(_kwota_duza, "Radom", 51.40, 21.15, "mazowieckie",
                                _dni_robocze, "90010112345", stawka=1.15)
    _pokrycie = 100.0 * sum(d.suma for d in _dni_duze) / _kwota_duza
    sprawdz("wysoka kwota (%.0f zł) pokryta w co najmniej 88%%" % _kwota_duza,
            _pokrycie >= 88.0, "pokrycie %.1f%% przy %d dniach" % (_pokrycie, len(_dni_duze)))

    # Rejon rzadko zaludniony — nie może się wysypać ani zbudować pustego planu.
    _dni_rzadkie = P.generuj_trasy(3000.0, "Suwałki", 54.10, 22.93, "podlaskie",
                                   _dni_robocze, "90010112345", stawka=1.15)
    sprawdz("rejon przygraniczny: plan powstaje", len(_dni_rzadkie) > 0)
    sprawdz("rejon przygraniczny: kwota rozpisana",
            abs(sum(d.suma for d in _dni_rzadkie) - 3000.0) <= 0.01,
            "%.2f zł" % sum(d.suma for d in _dni_rzadkie))

    # Dni awaryjne nie mogą być swoimi kopiami — te same miejscowości
    # w tej samej kolejności na kilku datach wyglądają jak dokument
    # przepisany przez kalkę.
    _slady = [tuple(e.dokad for e in d.etapy_surowe) for d in _dni_duze]
    _powtorki = len(_slady) - len(set(_slady))
    sprawdz("dni w planie nie są swoimi kopiami",
            _powtorki <= max(1, len(_slady) // 8),
            "%d powtórzonych tras na %d dni" % (_powtorki, len(_slady)))

    sekcja("7. Dokumenty PDF")
    _dni, _nazwa, _lat, _lng, _woj = _ostatnie
    _prac = P.DanePracownika(imie="Jan Testowy", pesel="90010112345",
                             adres="ul. Kwiatowa 5, 26-600 Radom", stanowisko="KR",
                             kod_pocztowy="26-600", baza_miasto=_nazwa,
                             baza_lat=_lat, baza_lng=_lng, wojewodztwo=_woj)
    _folder = os.path.join(_TMP_HOME, "pdf")
    _pods = P.generuj_pdfy(_dni, _prac, _mies, _rok, _folder, stawka=_stawka)
    _pliki = sorted(glob.glob(os.path.join(_folder, "*.pdf")))
    sprawdz("PDF-y powstały", len(_pliki) >= 2, "%d plików" % len(_pliki))
    _wielostronicowe = []
    for _pl in _pliki:
        if "rozliczenie" in os.path.basename(_pl).lower():
            continue
        with open(_pl, "rb") as f:
            _stron = len(re.findall(rb"/Type\s*/Page[^s]", f.read()))
        if _stron > 1:
            _wielostronicowe.append((os.path.basename(_pl), _stron))
    sprawdz("każda delegacja mieści się na jednej stronie A4",
            not _wielostronicowe, str(_wielostronicowe))
    sprawdz("suma z PDF-ów zgadza się z sumą tras",
            abs(sum(x["kwota"] for x in _pods) - sum(d.suma for d in _dni)) <= 0.02,
            "%.2f vs %.2f" % (sum(x["kwota"] for x in _pods), sum(d.suma for d in _dni)))

    sekcja("8. Okno programu buduje się i zamyka")
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        _app = QApplication.instance() or QApplication(sys.argv)
        _okno = P.App()
        _okno.show()
        QTimer.singleShot(600, _app.quit)
        _app.exec()
        sprawdz("główne okno programu buduje się bez błędu", True)
    except Exception as _e:
        sprawdz("główne okno programu buduje się bez błędu", False, repr(_e))


# ══════════════════════════════════════════════════════════════════
_bledy = [w for w in WYNIKI if not w[0]]
print("\n" + "=" * 62)
print("  WYNIK: %d / %d testów przeszło" % (len(WYNIKI) - len(_bledy), len(WYNIKI)))
if _bledy:
    print("  NIE PRZESZŁY:")
    for _, _n, _s in _bledy:
        print("    · %s%s" % (_n, ("  — " + _s) if _s else ""))
print("=" * 62)

shutil.rmtree(_TMP_HOME, ignore_errors=True)
sys.exit(1 if _bledy else 0)
