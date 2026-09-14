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
import importlib
import zlib
import math
import time
import base64
import json
import datetime
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


def same_piksele(obraz):
    """Surowe bajty obrazu BEZ dopychania wierszy — do porównań co do bajta.

    Qt dopycha każdy wiersz obrazu do pełnych czterech bajtów. W tym
    dopychaniu leży pamięć, której nikt nie zapisał, więc dwa NAPRAWDĘ
    identyczne zrzuty potrafiły dać różne bajty i sprawdzenie padało bez
    powodu. Dzieje się to tylko wtedy, gdy szerokość razy trzy nie dzieli
    się przez cztery — czyli zależnie od rozmiaru okna i skalowania ekranu:
    mapa w oknie 1920 px ma 1404 px szerokości i dopychania nie ma wcale,
    ale w oknie 1601 px ma 1085 px i dopychanie to jeden bajt na wiersz.
    Bierzemy więc z każdego wiersza dokładnie tyle bajtów, ile jest pikseli."""
    szerokosc_bajtow = obraz.width() * 3
    krok = obraz.bytesPerLine()
    surowe = obraz.constBits().asstring(obraz.sizeInBytes())
    if krok == szerokosc_bajtow:
        return surowe
    return b"".join(surowe[y * krok:y * krok + szerokosc_bajtow]
                    for y in range(obraz.height()))


def _teksty_pdf(sciezka):
    """Treść PDF-u odczytana przez tablice /ToUnicode — po jednym odczycie na
    osadzony krój (kroje mają własne numery glifów, wspólny słownik by je
    pomieszał). Fraza z dokumentu jest w którymś z odczytów."""
    dane = open(sciezka, "rb").read()
    strumienie = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", dane, re.S):
        surowy = m.group(1)
        try:
            strumienie.append(zlib.decompress(surowy))
        except Exception:
            strumienie.append(surowy)
    mapy = []
    for st in strumienie:
        mapa = {}
        for bf in re.finditer(rb"beginbfchar(.*?)endbfchar", st, re.S):
            for a, b in re.findall(rb"<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]{4,})>", bf.group(1)):
                mapa[int(a, 16)] = chr(int(b[:4], 16))
        if mapa:
            mapy.append(mapa)
    napisy = []
    for st in strumienie:
        if b" Tj" not in st:
            continue
        for m in re.finditer(rb"\((.*?)\)\s*Tj", st, re.S):
            napisy.append(re.sub(rb"\\(.)", rb"\1", m.group(1)))
    odczyty = []
    for mapa in mapy:
        odczyty.append("\n".join(
            "".join(mapa.get(n[i] * 256 + n[i + 1], "") for i in range(0, len(n) - 1, 2))
            for n in napisy))
    return odczyty


def _w_pdf(sciezka, fraza):
    return any(fraza in t for t in _teksty_pdf(sciezka))


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

# wersja.txt podbija się SAMO po zbudowaniu paczki (job „wersja" w build.yml),
# więc może być O KROK ZA źródłem — ale nigdy PRZED nim: numer bez gotowej
# paczki to pętla „pobierz–zainstaluj–znów jest aktualizacja" u użytkowników.
sprawdz("wersja.txt nie wyprzedza źródła (numer bez paczki = pętla aktualizacji)",
        P._wersja_na_liczbe(_wersja_txt) <= P._wersja_na_liczbe(P.WERSJA_PROGRAMU),
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
sekcja("1b. Moduły towarzyszące: intro z kulą ziemską, karta testera, głębia 3D")
for _mod in ("intro_zywa_mapa", "karta_testera", "wyglad_3d"):
    try:
        importlib.import_module(_mod)
        sprawdz("moduł %s importuje się" % _mod, True)
    except Exception as _e:
        sprawdz("moduł %s importuje się" % _mod, False, repr(_e))
try:
    import intro_zywa_mapa as _izm
    _izm._DZWIEK_ON = False            # testy bez dźwięku
    sprawdz("intro ma wtopione logotypy sieci (nie potrzebuje plików PNG)",
            len(json.loads(zlib.decompress(base64.b64decode(_izm._LOGO_B64)).decode("utf-8"))) >= 6)
    sprawdz("intro ma wtopione kontury geograficzne", len(_izm._geo()) >= 2)
except Exception as _e:
    sprawdz("intro: dane wtopione w moduł", False, repr(_e))
sprawdz("_siec_ma_logo: Żabka / Biedronka Codziennie / nieznana sieć",
        P._siec_ma_logo("Żabka") and P._siec_ma_logo("BIEDRONKA Codziennie") and not P._siec_ma_logo("Carrefour"))
_di = P.dane_intra_z_dysku("Jan Testowy")
sprawdz("dane intra bez historii: losowa trasa naszych sieci i środek Polski",
        isinstance(_di, dict) and len(_di.get("wezly") or []) >= 4
        and all(P._siec_ma_logo(w["siec"]) for w in _di["wezly"])
        and 49.0 < float(_di.get("lat", 0)) < 55.0 and 14.0 < float(_di.get("lon", 0)) < 24.5,
        str({k: v for k, v in _di.items() if k != "wezly"}))
sprawdz("dane intra nie podstawiają cudzego profilu, gdy imię się nie zgadza",
        str(_di.get("imie", "")).strip().lower() in ("", "jan"), str(_di.get("imie")))
sprawdz("dane intra bez historii: zera zamiast danych pokazowych modułu (bez cudzego imienia)",
        "dni" in _di and int(_di.get("dni", 0)) == 0 and int(_di.get("wizyty", 0)) == 0
        and str(_di.get("imie", "")).strip().lower() in ("", "jan"), str({k: v for k, v in _di.items() if k != "wezly"}))
_bez_intra = os.path.join(_TMP_HOME, "BEZ_INTRA.txt")
open(_bez_intra, "w").close()
_wyl1 = P._intro_wylaczone_plikiem(_TMP_HOME)
os.remove(_bez_intra)
sprawdz("BEZ_INTRA.txt w katalogu użytkownika wyłącza intro (a bez pliku nie)",
        _wyl1 is True and P._intro_wylaczone_plikiem(_TMP_HOME) is False)
_dz = datetime.date(2026, 9, 10)
sprawdz("logowanie offline: świeży wpis (30 dni) — wolno",
        P._logowanie_offline_dozwolone({"ostatnio": "2026-08-11T10:00:00"}, _dz) is True)
sprawdz("logowanie offline: stary wpis (60 dni) — trzeba zalogować się online",
        P._logowanie_offline_dozwolone({"ostatnio": "2026-07-12T10:00:00"}, _dz) is False)
sprawdz("logowanie offline: wpis sprzed tej wersji (bez daty) — wolno",
        P._logowanie_offline_dozwolone({"skrot": "x"}, _dz) is True)
sprawdz("MNOZNIK_MIN ma sens fizyczny (1,1–1,4)", 1.1 <= P.MNOZNIK_MIN <= 1.4, str(P.MNOZNIK_MIN))


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
sprawdz("_menedzer() NIE czyta ustawień programu — tylko menedzer.txt z sekretu",
        P._menedzer() == "", repr(P._menedzer()))
P.zapisz_ustawienie("menedzer", "")
P._ustawienia_reset()
sprawdz("okna zmiany i resetu hasła mają własny arkusz stylu (nieprzezroczysta karta)",
        "#PmtKarta" in P._styl_okna_logowania(True) and "#PmtKarta" in P._styl_okna_logowania(False)
        and "_styl_okna_logowania(ciemny)" in open(os.path.join(KATALOG, "PMT_Delegacje.py"), encoding="utf-8").read().split("def _okno_zmiany_hasla")[1].split("def _okno_resetu_hasla")[0]
        and "_styl_okna_logowania(ciemny)" in open(os.path.join(KATALOG, "PMT_Delegacje.py"), encoding="utf-8").read().split("def _okno_resetu_hasla")[1][:3000])

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

# adres „Zgłoś błąd" — domyślny, gdy brak pliku; z pliku, gdy jest
_plik_kontakt = os.path.join(KATALOG, "pmt_kontakt.txt")
if not os.path.exists(_plik_kontakt):
    sprawdz("_adres_zgloszen() bez pliku zwraca adres domyślny",
            P._adres_zgloszen() == P.ADRES_ZGLOSZEN_DOMYSLNY, repr(P._adres_zgloszen()))
    try:
        with open(_plik_kontakt, "w", encoding="utf-8") as f:
            f.write(" pomoc@przyklad.pl \n")
        sprawdz("_adres_zgloszen() czyta pmt_kontakt.txt",
                P._adres_zgloszen() == "pomoc@przyklad.pl", repr(P._adres_zgloszen()))
        with open(_plik_kontakt, "w", encoding="utf-8") as f:
            f.write("to nie jest adres\n")
        sprawdz("_adres_zgloszen() odrzuca wpis bez @ i wraca do domyślnego",
                P._adres_zgloszen() == P.ADRES_ZGLOSZEN_DOMYSLNY, repr(P._adres_zgloszen()))
    finally:
        try:
            os.remove(_plik_kontakt)
        except Exception:
            pass


# autologowanie: hasło znane z poprzedniego logowania na tym komputerze
_kod_t, _haslo_t = "12345", "Tajne1234"
sprawdz("autologowanie: nieznane konto → False",
        P._haslo_znane_lokalnie(_kod_t, _haslo_t) is False)
P._zapisz_logowanie(_kod_t, "Jan Testowy", P._hash_hasla(_kod_t, _haslo_t))
sprawdz("autologowanie: zgodne hasło → True",
        P._haslo_znane_lokalnie(_kod_t, _haslo_t) is True)
sprawdz("autologowanie: literówka w haśle → False",
        P._haslo_znane_lokalnie(_kod_t, _haslo_t + "x") is False)
sprawdz("autologowanie: to samo hasło, inne konto → False",
        P._haslo_znane_lokalnie("54321", _haslo_t) is False)
sprawdz("autologowanie: za krótkie hasło nigdy nie loguje",
        P._haslo_znane_lokalnie(_kod_t, "Taj") is False)
try:
    os.remove(P.PLIK_LOGOWAN)
except Exception:
    pass

# ── 1c. logowanie BEZ SIECI: status, ważność konta, werdykt sesji ─────────
# (łańcuch ze zgłoszenia „dane się nie pojawiają… po chwili program się
# wyłącza": logowanie offline nie zapisywało statusu → puste imię, brak
# przejęcia danych, sesja bez ważności → zasada demo → zamknięcie)
import urllib.request as _ur
_kod_o, _haslo_o = "23456", "Haslo12345"
for _w in (P.PLIK_STATUSU, P.PLIK_LOGOWAN):
    try:
        os.remove(_w)
    except Exception:
        pass
P._zapisz_logowanie(_kod_o, "Jan Testowy", P._hash_hasla(_kod_o, _haslo_o))
P._zapamietaj_waznosc_konta(_kod_o, (datetime.date.today() + datetime.timedelta(days=200)).isoformat())
_hist = P._wczytaj(P.PLIK_LOGOWAN, {}).get(_kod_o, {})
sprawdz("historia urządzenia pamięta ważność konta PER KONTO",
        bool(_hist.get("wazne_do")) and bool(_hist.get("skrot")), str(_hist))
P._zapisz_logowanie(_kod_o, "", P._hash_hasla(_kod_o, _haslo_o))
_hist = P._wczytaj(P.PLIK_LOGOWAN, {}).get(_kod_o, {})
sprawdz("ponowne logowanie nie kasuje ważności ani imienia w historii",
        bool(_hist.get("wazne_do")) and _hist.get("imie") == "Jan Testowy", str(_hist))
P._zapisz(P.PLIK_STATUSU, {"kod": "99999", "imie": "Anna Kowalska",
                           "wazne_do": "2020-01-01", "skrot": "x"})
_orig_urlopen = _ur.urlopen
def _bez_sieci(*a, **k):
    raise OSError("brak sieci (test)")
_ur.urlopen = _bez_sieci
try:
    _ok_o, _imie_o, _kom_o = P.online_zaloguj(_kod_o, _haslo_o)
    _ok_zle = P.online_zaloguj(_kod_o, _haslo_o + "x")[0]
finally:
    _ur.urlopen = _orig_urlopen
_st_o = P._wczytaj(P.PLIK_STATUSU, {})
sprawdz("logowanie bez sieci: wpuszcza po skrócie i ZAPISUJE status (kod, imię, ważność tego konta)",
        _ok_o and _imie_o == "Jan Testowy" and _st_o.get("kod") == _kod_o
        and _st_o.get("imie") == "Jan Testowy" and bool(_st_o.get("wazne_do"))
        and _st_o.get("wazne_do") != "2020-01-01", str((_ok_o, _imie_o, _kom_o, _st_o)))
sprawdz("logowanie bez sieci: złe hasło nie wchodzi", _ok_zle is False)
_w_s, _d_s, _im_s = P.online_status_sesji()
sprawdz("po logowaniu bez sieci sesja jest ważna (bez zasady demo)", _w_s is True and _d_s > 100, str((_w_s, _d_s)))
P._zapisz(P.PLIK_STATUSU, {"kod": _kod_o, "imie": "Jan Testowy", "skrot": P._hash_hasla(_kod_o, _haslo_o)})
_w_h, _d_h, _p_h = P._sesja_z_historii_urzadzenia()
sprawdz("werdykt sesji z historii urządzenia: ważność konta", _w_h is True and _d_h > 100, str((_w_h, _d_h, _p_h)))
_hist_all = P._wczytaj(P.PLIK_LOGOWAN, {})
_hist_all[_kod_o].pop("wazne_do", None)
P._zapisz(P.PLIK_LOGOWAN, _hist_all)
_w_h2, _d_h2, _p_h2 = P._sesja_z_historii_urzadzenia()
sprawdz("werdykt: świeże zweryfikowane logowanie bez ważności = do %d dni pracy bez sieci" % P.OFFLINE_LOGOWANIE_DNI,
        _w_h2 is True and 0 < _d_h2 <= P.OFFLINE_LOGOWANIE_DNI, str((_w_h2, _d_h2, _p_h2)))
_hist_all[_kod_o]["ostatnio"] = (datetime.datetime.now()
                                 - datetime.timedelta(days=P.OFFLINE_LOGOWANIE_DNI + 3)).isoformat(timespec="seconds")
P._zapisz(P.PLIK_LOGOWAN, _hist_all)
_w_h3, _d_h3, _p_h3 = P._sesja_z_historii_urzadzenia()
sprawdz("werdykt: logowanie starsze niż limit = odmowa z nazwanym powodem",
        _w_h3 is False and "offline" in str(_p_h3), str((_w_h3, _d_h3, _p_h3)))
P._zapamietaj_waznosc_konta(_kod_o, "2099-12-31")
P._zapisz(P.PLIK_STATUSU, {"kod": "99999", "imie": "Anna Kowalska", "wazne_do": "2020-01-01"})
P.online_zapisz_kod(_kod_o)
_st_z = P._wczytaj(P.PLIK_STATUSU, {})
sprawdz("zmiana konta: status dostaje imię i ważność TEGO konta, nie poprzedniej osoby",
        _st_z.get("imie") == "Jan Testowy" and _st_z.get("wazne_do") == "2099-12-31", str(_st_z))
sprawdz("komunikaty logowania: sieć/limit dni/blokada pokazywane po próbie automatycznej, złe hasło — podpowiedź",
        P._komunikat_logowania_wazny("Serwer nie odpowiedział w wyznaczonym czasie.")
        and P._komunikat_logowania_wazny("Minęło ponad 45 dni od ostatniego logowania z internetem.")
        and P._komunikat_logowania_wazny("Konto zablokowane przez administratora")
        and not P._komunikat_logowania_wazny("Błędne hasło."))
_pusty = os.path.join(_TMP_HOME, "_pusty_test.json")
with open(_pusty, "w") as _f:
    _f.write("[]")
_pusty_ok = P._plik_ma_tresc(_pusty) is False
with open(_pusty, "w") as _f:
    _f.write('[{"adres": "x"}]')
_pelny_ok = P._plik_ma_tresc(_pusty) is True
os.remove(_pusty)
sprawdz("_plik_ma_tresc: pusta lista = jak brak pliku, lista z wpisem = treść", _pusty_ok and _pelny_ok)
# serwer odsyła OK z PUSTYM imieniem (wiersz założony przez puls) — logowanie ma przejść
class _OdpSerwera:
    def __init__(self, dane):
        self._d = json.dumps(dane).encode("utf-8")
    def read(self):
        return self._d
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
_ur.urlopen = lambda *a, **k: _OdpSerwera({"status": "ok", "imie": "", "wazne_do": "2099-06-30"})
try:
    _ok_p, _imie_p, _kom_p = P.online_zaloguj(_kod_o, _haslo_o)
finally:
    _ur.urlopen = _orig_urlopen
sprawdz("logowanie online z pustym imieniem z serwera przechodzi (bez KeyError)",
        _ok_p is True and _imie_p in ("", "Jan Testowy") and P._wczytaj(P.PLIK_STATUSU, {}).get("wazne_do") == "2099-06-30",
        str((_ok_p, _imie_p, _kom_p)))
# pusta rubryka „Ważne do” w arkuszu = status „wygasla” → program NIE żyje na zapamiętanej dacie
P._zapamietaj_waznosc_konta(_kod_o, "2099-06-30")
P._zapamietaj_waznosc_konta(_kod_o, "", z_serwera=True)
sprawdz("puls z pustą datą kasuje zapamiętaną ważność konta",
        not (P._wczytaj(P.PLIK_LOGOWAN, {}).get(_kod_o) or {}).get("wazne_do"))
P._zapisz(P.PLIK_STATUSU, {"kod": _kod_o, "imie": "Jan Testowy", "status": "wygasla",
                           "skrot": P._hash_hasla(_kod_o, _haslo_o)})
_w_w, _d_w, _p_w = P._sesja_z_historii_urzadzenia()
sprawdz("status „wygasla” z serwera = odmowa z powodem (mimo skrótu hasła)",
        _w_w is False and "wazne_do=" in str(_p_w), str((_w_w, _d_w, _p_w)))
# historia bez daty ostatniego logowania online = brak podstaw, decyduje zasada demo
P._zapisz(P.PLIK_STATUSU, {"kod": _kod_o, "imie": "Jan Testowy", "skrot": P._hash_hasla(_kod_o, _haslo_o)})
_h = P._wczytaj(P.PLIK_LOGOWAN, {}); _h[_kod_o] = {"imie": "Jan Testowy", "skrot": P._hash_hasla(_kod_o, _haslo_o)}
P._zapisz(P.PLIK_LOGOWAN, _h)
sprawdz("historia bez daty logowania nie daje bezterminowego dostępu",
        P._sesja_z_historii_urzadzenia()[0] is None)
# wspólny komputer: raz zapamiętany kod sprzed aktualizacji decyduje, nie „kto logował się ostatnio”
P._ustawienia_reset()
P._zapisz(P.PLIK_LOGOWAN, {"11111": {"imie": "A"}, "22222": {"imie": "B"}})
P._zapisz(P.PLIK_STATUSU, {"kod": "11111"})
P._zapamietaj_kod_przed_logowaniem()
P._zapisz(P.PLIK_STATUSU, {"kod": "22222"})
_kp = P._zapamietaj_kod_przed_logowaniem()
sprawdz("kod sprzed aktualizacji zapamiętany na stałe: drugi start nie oddaje danych ostatnio zalogowanemu",
        _kp == "11111" and P._wolno_przejac_wspolne("11111") and not P._wolno_przejac_wspolne("22222"),
        str((_kp, P.KOD_PRZED_LOGOWANIEM)))
P.KOD_PRZED_LOGOWANIEM = ""
P._ustawienia_reset()
try:
    os.remove(P.USTAWIENIA_STORE)
except Exception:
    pass
for _w in (P.PLIK_STATUSU, P.PLIK_LOGOWAN):
    try:
        os.remove(_w)
    except Exception:
        pass

# magazyn profili zaśmiecony przez lokalną 3.21.0 (linia PMT_NOWY): tekst
# „_tester_zaproszenie" obok profili wywalał program przy wpisaniu nazwiska
_store_brudny = {P._klucz_uzytkownika("Jan Testowy", "90010112345"):
                 {"profil": {"imie": "Jan Testowy", "pesel": "90010112345", "adres": "ul. Kwiatowa 5, 26-600 Radom",
                             "stanowisko": "KR", "silnik_idx": 1}, "historia": []},
                 "_tester_zaproszenie": "2026-09-01", "_tester_zaproszenia_ile": 2}
with open(P.USER_STORE, "w", encoding="utf-8") as f:
    json.dump(_store_brudny, f)
try:
    _prof = P.szukaj_profilu_po_nazwisku("Jan Testowy")
    _st = P.statystyki_administratora()
    _di2 = P.dane_intra_z_dysku("Jan Testowy")
    sprawdz("zaśmiecony magazyn profili (3.21.0 lokalna) nie wywraca podpowiedzi, panelu ani intra",
            isinstance(_prof, dict) and _prof.get("pesel") == "90010112345" and isinstance(_st, dict)
            and _di2.get("miasto") == "RADOM", "profil=%s miasto=%s" % (bool(_prof), _di2.get("miasto")))
except Exception as _e:
    sprawdz("zaśmiecony magazyn profili (3.21.0 lokalna) nie wywraca podpowiedzi, panelu ani intra", False, repr(_e))
sprawdz("obce wpisy znikają z magazynu przy odczycie",
        all(isinstance(v, dict) for v in P._wczytaj_store().values()) and len(P._wczytaj_store()) == 1)
try:
    os.remove(P.USER_STORE)
except Exception:
    pass

# biblioteka PDF: weszła, a gdy nie wejdzie — czytelny komunikat, nie wywrotka
sprawdz("fpdf2 (biblioteka PDF) załadowana bez błędu",
        P.FPDF_BLAD == "", repr(P.FPDF_BLAD)[:160])
try:
    import fontTools as _ft, glob as _glob
    _d = os.path.dirname(_ft.__file__)
    _nat = _glob.glob(_d + "/**/*.pyd", recursive=True) + _glob.glob(_d + "/**/*.so", recursive=True)
    sprawdz("fontTools bez modułów natywnych (requirements: --no-binary fonttools)",
            not _nat, "; ".join(os.path.relpath(x, _d) for x in _nat)[:200])
except Exception as e:
    sprawdz("fontTools bez modułów natywnych (requirements: --no-binary fonttools)", False, str(e))
_bylo_fpdf_blad = P.FPDF_BLAD
try:
    P.FPDF_BLAD = "ImportError: DLL load failed while importing iup: Zasady kontroli aplikacji zablokowały ten plik."
    try:
        P.generuj_pdfy([], None, 1, 2026, os.path.join(_TMP_HOME, "pdf_test"))
        sprawdz("bez biblioteki PDF generowanie zgłasza czytelny błąd", False, "brak wyjątku")
    except ValueError as e:
        sprawdz("bez biblioteki PDF generowanie zgłasza czytelny błąd",
                "Biblioteka do tworzenia PDF" in str(e) and "3.21.4" in str(e), str(e)[:160])
finally:
    P.FPDF_BLAD = _bylo_fpdf_blad

# ══════════════════════════════════════════════════════════════════
sekcja("2b. Przełożony w układzie ZBUDOWANEGO programu (_internal)")

# Udajemy program zbudowany PyInstallerem: PMT_Planer.exe + podkatalog
# _internal z dołączonymi plikami. Tak wygląda paczka u każdego użytkownika.
_udawany = os.path.join(_TMP_HOME, "PMT_Planer")
os.makedirs(os.path.join(_udawany, "_internal"), exist_ok=True)
_bylo_frozen = getattr(sys, "frozen", None)
_bylo_exe = sys.executable
_bylo_meipass = getattr(sys, "_MEIPASS", None)
try:
    sys.frozen = True
    sys.executable = os.path.join(_udawany, "PMT_Planer.exe")
    sys._MEIPASS = os.path.join(_udawany, "_internal")
    P._ustawienia_reset()

    with open(os.path.join(_udawany, "_internal", "menedzer.txt"), "w", encoding="utf-8") as f:
        f.write("Anna Zbudowana\n")
    sprawdz("menedzer.txt dołączony do paczki (_internal) jest znajdowany",
            P._menedzer() == "Anna Zbudowana", repr(P._menedzer()))
    os.remove(os.path.join(_udawany, "_internal", "menedzer.txt"))

    with open(os.path.join(_udawany, "menedzer.txt"), "w", encoding="utf-8") as f:
        f.write("Anna Obok\n")
    sprawdz("menedzer.txt obok pliku .exe jest znajdowany",
            P._menedzer() == "Anna Obok", repr(P._menedzer()))
    os.remove(os.path.join(_udawany, "menedzer.txt"))

    with open(os.path.join(_TMP_HOME, "menedzer.txt"), "w", encoding="utf-16") as f:
        f.write("Anna Domowa\n")
    sprawdz("menedzer.txt w katalogu użytkownika, zapisany jako UTF-16, jest czytany",
            P._menedzer() == "Anna Domowa", repr(P._menedzer()))
    os.remove(os.path.join(_TMP_HOME, "menedzer.txt"))

    sprawdz("bez żadnego pliku — puste, a źródło mówi, gdzie szukano",
            P._menedzer() == "" and "BRAK" in P._menedzer_zrodlo(), P._menedzer_zrodlo()[:80])

    # tła i logo w tym samym układzie
    with open(os.path.join(_udawany, "_internal", "ciemny.png"), "wb") as f:
        f.write(b"x")
    sprawdz("zasob_sciezka() znajduje tło w _internal",
            P.zasob_sciezka("ciemny.png") == os.path.join(_udawany, "_internal", "ciemny.png"),
            P.zasob_sciezka("ciemny.png"))
finally:
    if _bylo_frozen is None:
        del sys.frozen
    else:
        sys.frozen = _bylo_frozen
    sys.executable = _bylo_exe
    if _bylo_meipass is None:
        del sys._MEIPASS
    else:
        sys._MEIPASS = _bylo_meipass
    P._ustawienia_reset()

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

# C. komputer WSPÓLNY, ale loguje się TA SAMA osoba, która była zalogowana
#    przed aktualizacją — dane są jej (zgłoszenie „dane się nie pojawiają")
_stan_sprzed_3210(["11111", "22222"])
P._zapisz(P.PLIK_STATUSU, {"kod": "11111", "imie": "Anna Kowalska"})
P._zapamietaj_kod_przed_logowaniem()
P.online_zapisz_kod("11111")
P.ustaw_uzytkownika_planu("Anna Kowalska", "11111")
sprawdz("osoba zalogowana przed aktualizacją odzyskuje punkty mimo drugiego konta w historii",
        len(P.wczytaj_punkty()) == 1, repr(P.wczytaj_punkty()))
sprawdz("osoba zalogowana przed aktualizacją odzyskuje adres bazy",
        P.ustawienie_osobiste("adres_bazy", "") == "ul. Wspólna 1, Radom")
P.online_zapisz_kod("22222")
P.ustaw_uzytkownika_planu("Bartosz Nowak", "22222")
sprawdz("…a druga osoba nadal NIE dostaje cudzych punktów",
        P.wczytaj_punkty() == [], repr(P.wczytaj_punkty()))
P.KOD_PRZED_LOGOWANIEM = ""

# D. plan zapisany przez 3.21.0 pod starym kluczem (imię|kod) + stub w pliku
#    wspólnym — po aktualizacji plan ma wrócić pod nowy klucz
_stan_sprzed_3210(["11111", "22222"])
_stary_klucz = P._klucz_uzytkownika("Anna Kowalska", "11111")
with open(os.path.join(_TMP_HOME, ".pmt_plan_%s.json" % _stary_klucz), "w", encoding="utf-8") as f:
    json.dump({"miesiace": [{"rok": 2026, "miesiac": 9, "dni": []}], "wlasciciel": _stary_klucz}, f)
with open(P.PLAN_STORE, "w", encoding="utf-8") as f:
    json.dump({"wlasciciel": _stary_klucz, "przeniesiony": True}, f)      # stub z 3.21.0
P.zapisz_ustawienie("adres_bazy__" + _stary_klucz, "ul. Stara 3, Radom")
P.online_zapisz_kod("11111")
P.ustaw_uzytkownika_planu("Anna Kowalska", "11111")
with open(P._plik_planu(), encoding="utf-8") as f:
    _plan_po = json.load(f)
sprawdz("plan spod klucza 3.21.0 (imię|kod) wraca pod nowy klucz konta",
        P._plan_ma_tresc(P._plik_planu()) and _plan_po.get("miesiace", [{}])[0].get("miesiac") == 9,
        "plik: %s, treść: %s" % (os.path.basename(P._plik_planu()), str(_plan_po)[:80]))
sprawdz("stary plik planu zostaje jako kopia .sprzed_3.22.0",
        os.path.exists(os.path.join(_TMP_HOME, ".pmt_plan_%s.json.sprzed_3.22.0" % _stary_klucz)))
sprawdz("adres bazy spod klucza 3.21.0 wraca na konto",
        P.ustawienie_osobiste("adres_bazy", "") == "ul. Stara 3, Radom",
        repr(P.ustawienie_osobiste("adres_bazy", "")))
sprawdz("stub {przeniesiony: true} nie jest traktowany jak plan",
        P._plan_ma_tresc(P.PLAN_STORE) is False)

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
sekcja("5b. Odległości: źródło, pamięć podręczna, klucz Google")

# Ta sekcja NIE RUSZA SIECI. Tam, gdzie sprawdzamy zachowanie wobec serwera,
# podstawiamy własną atrapę urllib i liczymy zapytania.
_ROAD_ORYG = P.ROAD_CACHE_FILE
_GEO_ORYG = P.GEO_CACHE
_BRAKI_ORYG = P.GEO_BRAKI
_OSRM_ORYG = P._osrm_dostepny
_KAT_CACHE = os.path.join(_TMP_HOME, "cache_odleglosci")
os.makedirs(_KAT_CACHE, exist_ok=True)

P.ROAD_CACHE_FILE = os.path.join(_KAT_CACHE, "road.json")
P.GEO_CACHE = os.path.join(_KAT_CACHE, "geo.json")
P.GEO_BRAKI = os.path.join(_KAT_CACHE, "geo_braki.json")

# --- klucz pamięci obejmuje OBA KIERUNKI ---
sprawdz("klucz pamięci odległości jest ten sam w obie strony",
        P._klucz_drogi(52.23, 21.01, 51.40, 21.15)
        == P._klucz_drogi(51.40, 21.15, 52.23, 21.01),
        P._klucz_drogi(52.23, 21.01, 51.40, 21.15))

# --- stan źródła: szacunek, gdy nie ma z czego wziąć realnej drogi ---
P._osrm_dostepny = False
P._road_cache.clear()
P.zeruj_zrodlo_odleglosci()
_km_szac = P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
_stan = P.stan_zrodla_odleglosci()
sprawdz("bez sieci stanem rozliczenia jest szacunek (nie cisza)",
        _stan["stan"] == P.ZRODLO_SZACUNEK and _stan["realne"] is False
        and _stan["etykieta"] == "szacunek", str(_stan))
sprawdz("szacunek nie trafia do pamięci podręcznej",
        P._klucz_drogi(52.23, 21.01, 51.40, 21.15) not in P._road_cache)
sprawdz("stan liczy odcinki, nie tylko rodzaj",
        _stan["odcinki"] == 1 and _stan[P.ZRODLO_SZACUNEK] == 1, str(_stan))

# --- stan źródła: pamięć podręczna ---
P._road_cache[P._klucz_drogi(52.23, 21.01, 51.40, 21.15)] = 103.4
P.zeruj_zrodlo_odleglosci()
_km_pam = P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
_stan_pam = P.stan_zrodla_odleglosci()
sprawdz("odcinek z pamięci ma własny stan i własną liczbę",
        _km_pam == 103.4 and _stan_pam["stan"] == P.ZRODLO_PAMIEC
        and _stan_pam["realne"] is True, str(_stan_pam))
sprawdz("droga zapisana w jedną stronę działa też w drugą",
        P.dystans_drogowy(51.40, 21.15, 52.23, 21.01) == 103.4)
sprawdz("jeden odcinek szacunkiem przestawia stan CAŁEGO rozliczenia",
        (P.dystans_drogowy(50.06, 19.94, 54.35, 18.65),
         P.stan_zrodla_odleglosci()["stan"])[1] == P.ZRODLO_SZACUNEK)

# --- pamięć podręczna przeżywa ponowne uruchomienie ---
P._zapisz_road_cache()
sprawdz("plik pamięci odległości powstaje", os.path.exists(P.ROAD_CACHE_FILE))
P._road_cache.clear()
P._wczytaj_road_cache()
sprawdz("pamięć odległości przeżywa ponowne uruchomienie programu",
        P._road_cache.get(P._klucz_drogi(52.23, 21.01, 51.40, 21.15)) == 103.4,
        str(P._road_cache)[:200])
P.zeruj_zrodlo_odleglosci()
sprawdz("po ponownym wczytaniu odcinek idzie z pamięci, nie z szacunku",
        P.dystans_drogowy(51.40, 21.15, 52.23, 21.01) == 103.4
        and P.stan_zrodla_odleglosci()["stan"] == P.ZRODLO_PAMIEC)

# --- uszkodzony plik pamięci nie wywraca programu ---
for _opis, _tresc in (("ucięty w połowie", '{"52.0000,21.0000;51.0'),
                      ("nie ten kształt (lista)", '[1, 2, 3]'),
                      ("puste śmieci", 'xxxxx'),
                      ("wpisy nie do użycia", '{"bez-srednika": "tak", "a;b": "nie-liczba"}')):
    with open(P.ROAD_CACHE_FILE, "w", encoding="utf-8") as _f:
        _f.write(_tresc)
    try:
        os.remove(P.ROAD_CACHE_FILE + ".bak")
    except OSError:
        pass
    try:
        P._road_cache.clear()
        P._wczytaj_road_cache()
        P.zeruj_zrodlo_odleglosci()
        _km = P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
        _ok = (P._road_cache == {} and _km > 0
               and P.stan_zrodla_odleglosci()["stan"] == P.ZRODLO_SZACUNEK)
    except Exception as _e:
        _ok = False
        _km = repr(_e)
    sprawdz("uszkodzony plik pamięci odległości (%s) nie wywraca programu" % _opis,
            _ok, str(_km))

# --- kopia .bak ratuje pamięć po uszkodzeniu głównego pliku ---
P._road_cache.clear()
P._road_cache[P._klucz_drogi(52.23, 21.01, 51.40, 21.15)] = 103.4
P._zapisz_road_cache()          # tworzy plik główny
P._road_cache[P._klucz_drogi(52.23, 21.01, 51.40, 21.15)] = 103.4
P._zapisz_road_cache()          # poprzedni ląduje w .bak
with open(P.ROAD_CACHE_FILE, "w", encoding="utf-8") as _f:
    _f.write('{"uciety')
P._road_cache.clear()
P._wczytaj_road_cache()
sprawdz("po uszkodzeniu pliku pamięć wraca z kopii .bak",
        P._road_cache.get(P._klucz_drogi(52.23, 21.01, 51.40, 21.15)) == 103.4,
        str(P._road_cache)[:200])

# --- wcześniejsze policzenie odcinków miesiąca ---
P._road_cache.clear()
P._road_cache[P._klucz_drogi(52.23, 21.01, 51.40, 21.15)] = 103.4
P._road_cache[P._klucz_drogi(51.40, 21.15, 51.25, 22.57)] = 140.0
_postepy = []
_stan_przyg = P.przygotuj_odleglosci(
    [(52.23, 21.01, 51.40, 21.15),
     (51.40, 21.15, 52.23, 21.01),          # ten sam odcinek w drugą stronę
     (51.40, 21.15, 51.25, 22.57),
     (51.40, 21.15, 51.40, 21.15)],         # odcinek zerowy — pomijany
    lambda t, v: _postepy.append(v))
sprawdz("wcześniejsze liczenie odcinków: powtórki i oba kierunki liczą się raz",
        _stan_przyg["odcinki"] == 2, str(_stan_przyg))
sprawdz("wcześniejsze liczenie odcinków raportuje stan źródła",
        _stan_przyg["stan"] == P.ZRODLO_PAMIEC and _stan_przyg["etykieta"] == "drogi z pamięci",
        str(_stan_przyg))
sprawdz("wcześniejsze liczenie odcinków melduje postęp", len(_postepy) == 2 and _postepy[-1] == 1.0,
        str(_postepy))

class _PunktT:
    def __init__(self, lat, lng):
        self.lat = lat; self.lng = lng

class _DzienT:
    def __init__(self, wizyty):
        self.wizyty = wizyty

_plan_t = {"dni": [_DzienT([_PunktT(51.40, 21.15), _PunktT(51.25, 22.57)]),
                   _DzienT([]),
                   _DzienT([_PunktT(52.55, 19.71)])]}
_pary = P.pary_odcinkow_planu(_plan_t, 52.23, 21.01)
sprawdz("odcinki miesiąca z planu: baza → punkty → baza, dzień bez wizyt pomijany",
        len(_pary) == 3 + 2 and _pary[0][:2] == (52.23, 21.01)
        and _pary[2][2:] == (52.23, 21.01), str(len(_pary)))

# --- klucz Google: opcjonalny, nigdy w kodzie ---
for _z in (P.GOOGLE_KLUCZ_ENV, P.GOOGLE_KLUCZ_ENV_ALT):
    os.environ.pop(_z, None)
P.zapisz_ustawienie(P.GOOGLE_KLUCZ_USTAWIENIE, "")
P._ustawienia_reset()
sprawdz("bez klucza i bez zmiennej środowiskowej klucza Google nie ma",
        P.google_klucz() == "", repr(P.google_klucz()))
sprawdz("w kodzie programu nie ma wpisanego klucza Google",
        "maps.googleapis.com" in _zrodlo and "AIza" not in _zrodlo)

P.zapisz_ustawienie(P.GOOGLE_KLUCZ_USTAWIENIE, "klucz-z-ustawien")
P._ustawienia_reset()
sprawdz("klucz Google czytany z ustawień", P.google_klucz() == "klucz-z-ustawien")
os.environ[P.GOOGLE_KLUCZ_ENV] = "klucz-ze-srodowiska"
sprawdz("zmienna środowiskowa ma pierwszeństwo przed ustawieniem",
        P.google_klucz() == "klucz-ze-srodowiska")

# bez klucza Google NIE JEST pytany (program działa dokładnie jak dotąd)
_google_oryg = P._google_km
_wolania_google = []
P._google_km = lambda *a, **k: (_wolania_google.append(a) or 12.5)
os.environ.pop(P.GOOGLE_KLUCZ_ENV, None)
P.zapisz_ustawienie(P.GOOGLE_KLUCZ_USTAWIENIE, "")
P._ustawienia_reset()
P._road_cache.clear()
P.zeruj_zrodlo_odleglosci()
P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
sprawdz("bez klucza program nie odpytuje Google", not _wolania_google)
sprawdz("bez klucza wynik bez sieci to nadal szacunek",
        P.stan_zrodla_odleglosci()["stan"] == P.ZRODLO_SZACUNEK)

# z kluczem odległości liczy Google
P.zapisz_ustawienie(P.GOOGLE_KLUCZ_USTAWIENIE, "klucz-testowy")
P._ustawienia_reset()
P._road_cache.clear()
P.zeruj_zrodlo_odleglosci()
_km_g = P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
sprawdz("z kluczem odległość liczy Google", _km_g == 12.5 and len(_wolania_google) == 1,
        "%s / %d" % (_km_g, len(_wolania_google)))
sprawdz("odpowiedź Google trafia do pamięci i ma stan „realne drogi”",
        P.stan_zrodla_odleglosci()["stan"] == P.ZRODLO_DROGI
        and P._road_cache.get(P._klucz_drogi(52.23, 21.01, 51.40, 21.15)) == 12.5)

# niedziałający klucz nie blokuje programu: Google pytamy RAZ, dalej OSRM/szacunek
_proby_zle = []
def _google_zly(*a, **k):
    _proby_zle.append(a)
    raise OSError("brak odpowiedzi Google")
P._google_km = _google_zly
P._google_dostepny = None
P._road_cache.clear()
P.zeruj_zrodlo_odleglosci()
P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
P.dystans_drogowy(50.06, 19.94, 54.35, 18.65)
P.dystans_drogowy(53.13, 23.16, 54.10, 22.93)
sprawdz("niedziałający klucz Google pytany raz, nie przy każdym odcinku",
        len(_proby_zle) == 1, "%d prób" % len(_proby_zle))
sprawdz("po nieudanym Google odległości wracają do źródła bezpłatnego",
        P.stan_zrodla_odleglosci()["stan"] == P.ZRODLO_SZACUNEK)

P._google_km = _google_oryg
P._google_dostepny = None
P.zapisz_ustawienie(P.GOOGLE_KLUCZ_USTAWIENIE, "")
P._ustawienia_reset()

# ══════════════════════════════════════════════════════════════════
sekcja("5c. Rozpoznawanie adresów i pamięć geolokalizacji")

sprawdz("numer lokalu odcięty na potrzeby mapy (Zamiejska 5/58 → 5)",
        P._bez_numeru_lokalu("ul. Zamiejska 5/58, 03-580 Warszawa")
        == "ul. Zamiejska 5, 03-580 Warszawa",
        P._bez_numeru_lokalu("ul. Zamiejska 5/58, 03-580 Warszawa"))
sprawdz("kod pocztowy NIE jest brany za numer lokalu",
        P._bez_numeru_lokalu("Dębowa Wola 12, 26-660 Jedlińsk")
        == "Dębowa Wola 12, 26-660 Jedlińsk")
_ad = P.waliduj_adres("ul. Zamiejska 5/58, 03-580 Warszawa")
sprawdz("dokument zachowuje pełny numer z lokalem",
        _ad["adres_caly"] == "ul. Zamiejska 5/58, 03-580 Warszawa", _ad["adres_caly"])
sprawdz("do mapy idzie adres bez numeru lokalu",
        _ad["adres_geo"] == "ul. Zamiejska 5, 03-580 Warszawa", _ad["adres_geo"])
_war = P._warianty_geo("ul. Zamiejska 5/58, 03-580 Warszawa", "Warszawa")
sprawdz("warianty adresu bez powtórek: pełny → bez lokalu → miejscowość",
        _war == ["ul. Zamiejska 5/58, 03-580 Warszawa",
                 "ul. Zamiejska 5, 03-580 Warszawa", "Warszawa"], str(_war))
sprawdz("adres bez lokalu nie rodzi drugiego, tego samego zapytania",
        len(P._warianty_geo("Kowalczyka 12, 03-193 Warszawa", "Warszawa")) == 2)
sprawdz("klucz adresu jest odporny na wielkość liter i podwójne odstępy",
        P._klucz_geo("  UL.  Kwiatowa 5,  26-600 Radom ")
        == P._klucz_geo("ul. Kwiatowa 5, 26-600 Radom"))

# pamięć geolokalizacji przeżywa restart
P._geo_cache.clear()
P._geo_cache[P._klucz_geo("ul. Kwiatowa 5, 26-600 Radom")] = [51.40, 21.15]
P.zapisz_geo_cache()
P._geo_cache.clear()
P._wczytaj_geo_cache()
sprawdz("pamięć geolokalizacji przeżywa ponowne uruchomienie",
        P._geo_cache.get(P._klucz_geo("UL. KWIATOWA 5, 26-600 RADOM")) == [51.40, 21.15],
        str(P._geo_cache)[:200])

for _opis, _tresc in (("ucięty w połowie", '{"adres": [51.4'),
                      ("nie ten kształt (lista)", '["a","b"]'),
                      ("wpisy nie do użycia", '{"adres": "51.4,21.1", "inny": [999, 999]}')):
    with open(P.GEO_CACHE, "w", encoding="utf-8") as _f:
        _f.write(_tresc)
    try:
        os.remove(P.GEO_CACHE + ".bak")
    except OSError:
        pass
    try:
        P._geo_cache.clear()
        P._wczytaj_geo_cache()
        _ok = (P._geo_cache == {})
    except Exception as _e:
        _ok = False
    sprawdz("uszkodzony plik pamięci geolokalizacji (%s) nie wywraca programu" % _opis, _ok,
            str(P._geo_cache)[:120])

# o ten sam adres nie pytamy serwera dwa razy (atrapa serwera, ZERO sieci)
class _OdpowiedzT:
    def __init__(self, tresc):
        self._tresc = tresc
    def read(self):
        return self._tresc
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False

_zapytania = []
_urlopen_oryg = P.urllib.request.urlopen

def _urlopen_atrapa(req, *a, **k):
    _zapytania.append(getattr(req, "full_url", str(req)))
    return _OdpowiedzT(b"[]")            # serwer odpowiada: nie znam

P.urllib.request.urlopen = _urlopen_atrapa
try:
    P._geo_cache.clear()
    P._geo_braki = {}
    P._geo_pytane.clear()
    _c1 = P.pobierz_coords("ul. Nieistniejąca 999, 26-600 Radom", "Radom", "mazowieckie")
    _ile1 = len(_zapytania)
    _c2 = P.pobierz_coords("ul. Nieistniejąca 999, 26-600 Radom", "Radom", "mazowieckie")
    _ile2 = len(_zapytania)
    sprawdz("nieznany adres pytany raz, potem już nie", _ile1 > 0 and _ile2 == _ile1,
            "%d → %d zapytań" % (_ile1, _ile2))
    sprawdz("odpowiedź „nie znam” zapisana trwale",
            os.path.exists(P.GEO_BRAKI)
            and P._klucz_geo("ul. Nieistniejąca 999, 26-600 Radom") in P._wczytaj_geo_braki())
    P._geo_braki = None
    P._geo_pytane.clear()
    _ile3 = len(_zapytania)
    P.pobierz_coords("ul. Nieistniejąca 999, 26-600 Radom", "Radom", "mazowieckie")
    sprawdz("po ponownym uruchomieniu nieznany adres też nie idzie do serwera",
            len(_zapytania) == _ile3, "%d → %d" % (_ile3, len(_zapytania)))

    # awaria sieci NIE jest zapamiętywana jako „adres nie istnieje”
    def _urlopen_awaria(req, *a, **k):
        _zapytania.append("awaria")
        raise OSError("brak sieci")
    P.urllib.request.urlopen = _urlopen_awaria
    P._geo_braki = {}
    P._geo_pytane.clear()
    P.pobierz_coords("ul. Inna 1, 26-600 Radom", "Radom", "mazowieckie")
    sprawdz("awaria sieci nie zostaje zapamiętana jako „adres nie istnieje”",
            P._klucz_geo("ul. Inna 1, 26-600 Radom") not in P._wczytaj_geo_braki())

    # znany adres: jedno zapytanie, wynik trafia do pamięci
    def _urlopen_zna(req, *a, **k):
        _zapytania.append(getattr(req, "full_url", str(req)))
        return _OdpowiedzT(b'[{"lat": "51.4000", "lon": "21.1500"}]')
    P.urllib.request.urlopen = _urlopen_zna
    P._geo_cache.clear()
    P._geo_braki = {}
    P._geo_pytane.clear()
    _przed = len(_zapytania)
    _w1 = P.pobierz_coords("ul. Kwiatowa 5, 26-600 Radom", "Radom", "mazowieckie")
    _po_pierwszym = len(_zapytania)
    _w2 = P.pobierz_coords("UL. KWIATOWA 5,  26-600 Radom", "Radom", "mazowieckie")
    sprawdz("znany adres pytany raz — drugi zapis tego samego adresu idzie z pamięci",
            _w1 == _w2 == (51.4, 21.15) and _po_pierwszym - _przed == 1
            and len(_zapytania) == _po_pierwszym,
            "%d zapytań" % (len(_zapytania) - _przed))
finally:
    P.urllib.request.urlopen = _urlopen_oryg

# stan wyjściowy dla dalszych sekcji
P.ROAD_CACHE_FILE = _ROAD_ORYG
P.GEO_CACHE = _GEO_ORYG
P.GEO_BRAKI = _BRAKI_ORYG
P._osrm_dostepny = _OSRM_ORYG
P._google_dostepny = None
P._road_cache.clear()
P._geo_cache.clear()
P._geo_braki = None
P._geo_pytane.clear()


# ══════════════════════════════════════════════════════════════════
if not SZYBKO:
    sekcja("6. Silnik delegacji — kwoty, czas dnia, odległości")
    # Testy silnika liczą ZAWSZE offline (linia prosta × krętość), niezależnie
    # od tego, czy maszyna ma dostęp do serwera OSRM. Inaczej ten sam kod dawał
    # inne liczby lokalnie i na GitHubie (realne drogi = dalsze dni odpadają
    # z limitu 8 h), a test pokrycia był loterią zależną od sieci.
    P._osrm_dostepny = False
    P._road_cache.clear()

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

    # Kwota PONAD możliwości miesiąca. Punktem odniesienia nie jest już sama
    # zamówiona kwota (dawny próg „82% z 11 000 zł" betonował dzisiejszy wynik
    # silnika), tylko REALNA granica miesiąca: dni robocze × pojemność doby
    # (posiłek + jazda + postoje). Silnik ma wykorzystać miesiąc do tej granicy
    # i uczciwie zgłosić, że kwota się nie zmieściła — a nie dopisywać
    # kilometrów, których nie da się przejechać.
    _kwota_duza = 11000.0
    _granica_mies = P.maks_kwota_miesiaca(len(_dni_robocze), 1.15)
    _dni_duze = P.generuj_trasy(_kwota_duza, "Radom", 51.40, 21.15, "mazowieckie",
                                _dni_robocze, "90010112345", stawka=1.15)
    _suma_duza = sum(d.suma for d in _dni_duze)
    sprawdz("kwota ponad granicę miesiąca (%.0f zł > %.0f zł) jest zgłoszona jako niepełna"
            % (_kwota_duza, _granica_mies),
            _kwota_duza > _granica_mies and bool(_dni_duze.kwota_niepelna),
            "granica %.2f zł, wyszło %.2f zł, niepelna=%s"
            % (_granica_mies, _suma_duza, getattr(_dni_duze, "kwota_niepelna", None)))
    sprawdz("wysoka kwota: wykorzystane co najmniej 88%% realnej granicy miesiąca",
            _suma_duza >= _granica_mies * 0.88,
            "%.2f zł z %.2f zł (%.1f%%) przy %d dniach"
            % (_suma_duza, _granica_mies, 100.0 * _suma_duza / _granica_mies, len(_dni_duze)))
    sprawdz("suma nigdy nie przekracza zamówionej kwoty",
            _suma_duza <= _kwota_duza + 0.01, "%.2f zł" % _suma_duza)

    # Rejon rzadko zaludniony — nie może się wysypać ani zbudować pustego planu.
    _dni_rzadkie = P.generuj_trasy(3000.0, "Suwałki", 54.10, 22.93, "podlaskie",
                                   _dni_robocze, "90010112345", stawka=1.15)
    sprawdz("rejon przygraniczny: plan powstaje", len(_dni_rzadkie) > 0)
    sprawdz("rejon przygraniczny: kwota rozpisana",
            abs(sum(d.suma for d in _dni_rzadkie) - 3000.0) <= 0.01,
            "%.2f zł" % sum(d.suma for d in _dni_rzadkie))

    # DROGA NIGDY KRÓTSZA NIŻ LINIA PROSTA (zgłoszenie: Warszawa→Bolimów
    # 20 km / 18 min u jednej osoby, 45 km / 41 min u drugiej).
    def _floor_ok(dni):
        return all(e.dystans_rzeczywisty >= e.d_line * P.MNOZNIK_MIN - 0.01
                   for d in dni for e in d.etapy_surowe)
    def _max_min(dni):
        return max((P.PRZERWA_JEDZENIE_MIN + sum((e.czas_jazdy_minuty or 0) + (e.czas_w_sklepie or 0)
                                                for e in d.etapy_surowe) for d in dni), default=0)
    sprawdz("żaden odcinek nie jest krótszy niż %.2f × linia prosta (kwota minimalna)" % P.MNOZNIK_MIN,
            _floor_ok(_dni_min))
    sprawdz("żaden odcinek nie jest krótszy niż %.2f × linia prosta (11 000 zł)" % P.MNOZNIK_MIN,
            _floor_ok(_dni_duze))
    sprawdz("żaden odcinek nie jest krótszy niż %.2f × linia prosta (Suwałki)" % P.MNOZNIK_MIN,
            _floor_ok(_dni_rzadkie))
    # MAŁA KWOTA — teraz liczona z modelu, a nie z zabetonowanego „najwyżej
    # 2 dni": 80 zł mieści się w jednym dokumencie i w jednym dniu (kwota jest
    # mniejsza od pojemności doby), więc tyle dni ma wyjść. Reszta warunków bez
    # zmian: kwota co do grosza, doba w limicie, odcinki nie krótsze niż droga.
    _dni_male = P.generuj_trasy(80.0, "Radom", 51.40, 21.15, "mazowieckie",
                                _dni_robocze, "90010112345", stawka=0.89)
    _dni_z_modelu = P.ile_dokumentow(80.0) * max(1, math.ceil(
        80.0 / P.pojemnosc_dnia_zl(P.POSTOJE_TYPOWE, 0.89)))
    sprawdz("mała kwota (80 zł): jeden dokument i tyle dni, ile wynika z modelu (%d)"
            % _dni_z_modelu,
            P.ile_dokumentow(80.0) == 1
            and 0 < len(_dni_male) <= _dni_z_modelu and _floor_ok(_dni_male)
            and abs(sum(d.suma for d in _dni_male) - 80.0) <= 0.01
            and _max_min(_dni_male) <= P.LIMIT_CZASU_MINUTY + 0.5,
            "%d dni, %.2f zł, %.0f min" % (len(_dni_male), sum(d.suma for d in _dni_male), _max_min(_dni_male)))
    sprawdz("po przycięciu każdy dzień ma co najmniej 2 postoje i powrót",
            all(len(d.etapy_surowe) >= 3 for d in _dni_male + _dni_min + _dni_rzadkie))
    sprawdz("silnik zgłasza kwotę za małą tylko, gdy najkrótszy realny dzień jej nie mieści",
            hasattr(_dni_male, "kwota_za_mala")
            and ((not _dni_male.kwota_za_mala) or _dni_male.kwota_min_realna > 80.0)
            and not getattr(_dni_duze, "kwota_za_mala", False),
            "za_mala=%s min=%.2f" % (getattr(_dni_male, "kwota_za_mala", None), getattr(_dni_male, "kwota_min_realna", 0)))

    # Dni awaryjne nie mogą być swoimi kopiami — te same miejscowości
    # w tej samej kolejności na kilku datach wyglądają jak dokument
    # przepisany przez kalkę.
    _slady = [tuple(e.dokad for e in d.etapy_surowe) for d in _dni_duze]
    _powtorki = len(_slady) - len(set(_slady))
    sprawdz("dni w planie nie są swoimi kopiami",
            _powtorki <= max(1, len(_slady) // 8),
            "%d powtórzonych tras na %d dni" % (_powtorki, len(_slady)))

    # ══════════════════════════════════════════════════════════════════
    sekcja("6c. Model: kwota → dokumenty → dni")

    # Sufit 986,34 zł dotyczy JEDNEGO DOKUMENTU (jednego polecenia wyjazdu),
    # a dokument obejmuje kilka dni. Liczba dokumentów wynika więc z kwoty,
    # a dopiero wewnątrz dokumentu kwota dzieli się na dni — każdy ograniczony
    # fizyką doby: posiłek + jazda + postoje.

    sprawdz("liczba dokumentów to sufit z kwoty przez sufit dokumentu",
            (P.ile_dokumentow(50.0), P.ile_dokumentow(P.MAX_KWOTA_DOKUMENTU),
             P.ile_dokumentow(P.MAX_KWOTA_DOKUMENTU + 0.01),
             P.ile_dokumentow(3000.0)) == (1, 1, 2, 4),
            str([P.ile_dokumentow(x) for x in (50.0, P.MAX_KWOTA_DOKUMENTU,
                                               P.MAX_KWOTA_DOKUMENTU + 0.01, 3000.0)]))
    _czesci = P.rozdziel_rowno(1000.0, 3)
    sprawdz("kwota dzieli się na części równe co do grosza",
            abs(sum(_czesci) - 1000.0) < 1e-9 and max(_czesci) - min(_czesci) <= 0.01,
            str(_czesci))

    # Każdy przystanek zjada kilkanaście minut z tych samych ośmiu godzin,
    # więc im więcej wizyt, tym mniej kilometrów mieści się w dniu.
    _poj = [P.pojemnosc_dnia_km(n) for n in (3, 5, 7)]
    _ubytek = 2 * P.POSTOJ_SREDNI_MIN / 60.0 * P.SREDNIA_PREDKOSC
    sprawdz("każdy przystanek zabiera dniu kilometry",
            _poj[0] > _poj[1] > _poj[2] > 0
            and abs((_poj[0] - _poj[1]) - _ubytek) < 0.01
            and abs((_poj[1] - _poj[2]) - _ubytek) < 0.01,
            "3/5/7 postojów: %.0f / %.0f / %.0f km" % tuple(_poj))
    sprawdz("sufit dnia to mniejsza z dwóch wartości: fizyczna i regulaminowa",
            P.pojemnosc_dnia_zl(5, 0.89) == round(P.pojemnosc_dnia_km(5) * 0.89, 2)
            and P.pojemnosc_dnia_zl(5, 99.0) == P.MAX_KWOTA_DNIA,
            "%.2f zł przy 0,89 / %.2f zł przy 99,00" % (P.pojemnosc_dnia_zl(5, 0.89),
                                                        P.pojemnosc_dnia_zl(5, 99.0)))
    sprawdz("granica miesiąca to dni robocze × sufit dnia",
            P.maks_kwota_miesiaca(22, 0.89) == round(22 * P.pojemnosc_dnia_zl(5, 0.89), 2)
            and P.maks_kwota_miesiaca(0, 0.89) == 0.0,
            "%.2f zł" % P.maks_kwota_miesiaca(22, 0.89))

    # Dni rozpisane dokładnie wg modelu (3000 zł → 4 dokumenty po 750 zł,
    # po 3 dni każdy) muszą złożyć się na dokumenty bez reszty.
    def _dzien_modelowy(numer, kwota, etapow=5):
        d = P.DzienTrasy(data=datetime.date(2026, 10, 1) + datetime.timedelta(days=numer))
        d.etapy = [P.Etap(skad="Baza", dokad="Miasto", data="01.10.2026r",
                          godz_wyj="07:00", godz_przyj="08:00", kwota=k)
                   for k in P.rozdziel_rowno(kwota, etapow)]
        return d
    _dni_model = [_dzien_modelowy(i, 250.0) for i in range(12)]
    _docs_model = P._podziel_na_dokumenty(_dni_model)
    sprawdz("dni z modelu składają się na dokumenty po sufit (12 × 250 zł → 4 × 750 zł)",
            [round(sum(d.suma for d in doc), 2) for doc in _docs_model] == [750.0] * 4,
            str([round(sum(d.suma for d in doc), 2) for doc in _docs_model]))
    sprawdz("każdy dzień zna numer swojego dokumentu",
            [d.dokument for d in _dni_model] == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
            str([d.dokument for d in _dni_model]))

    # …i to samo na prawdziwym wyniku silnika.
    _kwota_dok = 3000.0
    _dni_dok = P.generuj_trasy(_kwota_dok, "Radom", 51.40, 21.15, "mazowieckie",
                               _dni_robocze, "90010112345", stawka=0.89)
    _docs_dok = P._podziel_na_dokumenty(sorted(_dni_dok, key=lambda d: d.data))
    _sumy_dok = [round(sum(d.suma for d in doc), 2) for doc in _docs_dok]
    _wiersze_dok = [sum(len(d.etapy) for d in doc) for doc in _docs_dok]
    sprawdz("suma dokumentów równa się kwocie co do grosza",
            abs(sum(_sumy_dok) - _kwota_dok) <= 0.005,
            "%.2f zł w %d dokumentach" % (sum(_sumy_dok), len(_docs_dok)))
    sprawdz("żaden dokument nie przekracza sufitu kwoty",
            all(s <= P.MAX_KWOTA_DOKUMENTU + 0.01 for s in _sumy_dok), str(_sumy_dok))
    sprawdz("żaden dokument nie przekracza liczby wierszy strony A4",
            all(w <= P.MAX_ETAPOW_DOKUMENTU for w in _wiersze_dok), str(_wiersze_dok))
    sprawdz("dokumentów nie mniej, niż wynika z kwoty",
            len(_docs_dok) >= P.ile_dokumentow(sum(_sumy_dok)),
            "%d dokumentów, z kwoty %d" % (len(_docs_dok), P.ile_dokumentow(sum(_sumy_dok))))
    # „dobijają do sufitu" = żadnych dwóch sąsiednich nie da się połączyć
    _do_polaczenia = [i for i in range(len(_docs_dok) - 1)
                      if _sumy_dok[i] + _sumy_dok[i + 1] <= P.MAX_KWOTA_DOKUMENTU + 0.01
                      and _wiersze_dok[i] + _wiersze_dok[i + 1] <= P.MAX_ETAPOW_DOKUMENTU]
    sprawdz("dokumenty dobijają do sufitu — sąsiednich nie da się połączyć",
            not _do_polaczenia, "do połączenia: %s z %s" % (_do_polaczenia, _sumy_dok))
    # dzień ograniczony fizycznie — z UWZGLĘDNIENIEM swoich postojów
    _ponad_dobe = []
    for _d in _dni_dok:
        _postoje = sum((e.czas_w_sklepie or 0) for e in _d.etapy_surowe)
        _mieszczace = (P.LIMIT_CZASU_MINUTY - P.PRZERWA_JEDZENIE_MIN - _postoje) / 60.0 * P.SREDNIA_PREDKOSC
        if sum(e.dystans_rzeczywisty for e in _d.etapy_surowe) > _mieszczace + 0.5:
            _ponad_dobe.append(_d.data)
    sprawdz("żaden dzień nie przekracza kilometrów, które mieszczą się z jego postojami",
            not _ponad_dobe, "dni ponad dobę: %s" % _ponad_dobe)
    sprawdz("żaden dzień nie przekracza regulaminowego sufitu dnia",
            all(d.suma <= P.MAX_KWOTA_DNIA + 0.01 for d in _dni_dok),
            "najdroższy dzień %.2f zł" % max((d.suma for d in _dni_dok), default=0))

    sekcja("7. Dokumenty PDF")
    _dni, _nazwa, _lat, _lng, _woj = _ostatnie
    _prac = P.DanePracownika(imie="Jan Testowy", pesel="90010112345",
                             adres="ul. Kwiatowa 5, 26-600 Radom", stanowisko="KR",
                             kod_pocztowy="26-600", baza_miasto=_nazwa,
                             baza_lat=_lat, baza_lng=_lng, wojewodztwo=_woj)
    _folder = os.path.join(_TMP_HOME, "pdf")
    # „5/58" w adresie: ukośnik rozbijał adres w linku Google Maps na DWA
    # przystanki („Zamiejska 5" i „58, 03-580 Warszawa" → obcy adres)
    try:
        _prac_m = P.DanePracownika(imie="Jan Testowy", pesel="90010112345",
                                   adres="ul. Zamiejska 5/58, 03-580 Warszawa", stanowisko="KR",
                                   kod_pocztowy="03-580", baza_miasto=_nazwa,
                                   baza_lat=_lat, baza_lng=_lng, wojewodztwo=_woj)
        _folder_m = os.path.join(_TMP_HOME, "mapa_ukosnik"); os.makedirs(_folder_m, exist_ok=True)
        P.generuj_mape_html(_dni, _prac_m, "wrzesień", 2026, _folder_m, True)
        with open(os.path.join(_folder_m, "Trasy_Mapa.html"), encoding="utf-8") as _f:
            _html_m = _f.read()
        _linki = re.findall(r'maps/dir/([^"]+)"', _html_m)
        sprawdz("mapa: adres z numerem mieszkania (5/58) to JEDEN przystanek w linku Google Maps",
                _linki and all("5%2F58" in l and "5/58" not in l for l in _linki), str(_linki[:1])[:200])
    except Exception as _e:
        sprawdz("mapa: adres z numerem mieszkania (5/58) to JEDEN przystanek w linku Google Maps", False, repr(_e))
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

    # ŹRÓDŁO ODLEGŁOŚCI NA DOKUMENCIE. Testy liczą bez sieci, więc stanem
    # jest szacunek — i dokument ma to mówić wprost, a nie milczeć.
    _stan_pdf = P.stan_zrodla_odleglosci()
    sprawdz("stan źródła odległości po zbudowaniu tras to szacunek (testy bez sieci)",
            _stan_pdf["stan"] == P.ZRODLO_SZACUNEK, str(_stan_pdf))
    _delegacje = [x for x in _pliki if "rozliczenie" not in os.path.basename(x).lower()]
    _bez_zrodla = [os.path.basename(x) for x in _delegacje
                   if not _w_pdf(x, "Odległości: szacunek")]
    sprawdz("każde polecenie wyjazdu odnotowuje źródło odległości",
            _delegacje and not _bez_zrodla, str(_bez_zrodla))
    _zbiorcze = [x for x in _pliki if "rozliczenie" in os.path.basename(x).lower()]
    sprawdz("rozliczenie zbiorcze odnotowuje źródło odległości",
            _zbiorcze and _w_pdf(_zbiorcze[0], "szacunek"),
            str([os.path.basename(x) for x in _zbiorcze]))

    # ten sam stan na podglądzie tras
    _folder_z = os.path.join(_TMP_HOME, "mapa_zrodlo"); os.makedirs(_folder_z, exist_ok=True)
    P.generuj_mape_html(_dni, _prac, "październik", _rok, _folder_z, True)
    with open(os.path.join(_folder_z, "Trasy_Mapa.html"), encoding="utf-8") as _f:
        _html_z = _f.read()
    sprawdz("podgląd tras pokazuje stan źródła odległości",
            "Odległości: szacunek" in _html_z)

    # z pamięci podręcznej dokument mówi co innego — i mówi prawdę
    _stan_udawany = {"stan": P.ZRODLO_PAMIEC, "etykieta": "drogi z pamięci",
                     "odcinki": 5, "realne": True}
    _folder_r = os.path.join(_TMP_HOME, "pdf_realne")
    P.generuj_pdfy(_dni[:1], _prac, _mies, _rok, _folder_r, stawka=_stawka,
                   zrodlo=_stan_udawany)
    _pl_r = [x for x in sorted(glob.glob(os.path.join(_folder_r, "*.pdf")))
             if "rozliczenie" not in os.path.basename(x).lower()]
    sprawdz("przy realnych drogach dokument nie mówi „szacunek”",
            _pl_r and _w_pdf(_pl_r[0], "Odległości: drogi z pamięci")
            and not _w_pdf(_pl_r[0], "szacunek"),
            str([os.path.basename(x) for x in _pl_r]))

    sekcja("7b. Aktualizacja: użytkownik zawsze ma wybór")

    # bezpiecznik pętli aktualizacji: paczka z serwera musi być NOWSZA od programu
    _pk = os.path.join(_TMP_HOME, "paczka_test")
    os.makedirs(os.path.join(_pk, "_internal"), exist_ok=True)
    sprawdz("paczka bez znacznika wersji (wydanie sprzed 3.21.0) — instalujemy",
            P._paczka_nie_nowsza(_pk, "3.21.1") == "", repr(P._paczka_nie_nowsza(_pk, "3.21.1")))
    for _w, _oczek, _opis in (("3.21.1", False, "w tej samej wersji — STOP (koniec pętli aktualizacji)"),
                              ("3.9.9", False, "starsza — STOP"),
                              ("3.21.2", True, "nowsza — instalujemy"),
                              ("3.22.0\r\n", True, "nowsza, znacznik z CRLF — instalujemy")):
        with open(os.path.join(_pk, "pmt_wersja.txt"), "w", encoding="utf-8") as f:
            f.write(_w)
        _kom = P._paczka_nie_nowsza(_pk, "3.21.1")
        sprawdz("paczka %s" % _opis, (_kom == "") == _oczek, repr(_kom))
    sprawdz("komunikat o starej paczce mówi, która wersja leży na serwerze i którą masz",
            "3.22.0" in P._paczka_nie_nowsza(_pk, "3.22.5") and "3.22.5" in P._paczka_nie_nowsza(_pk, "3.22.5"),
            repr(P._paczka_nie_nowsza(_pk, "3.22.5")))
    shutil.rmtree(_pk, ignore_errors=True)

    # start z wnętrza ZIP-a / z folderu tymczasowego (zdjęcie od użytkownika, 3.21.1:
    # Eksplorator wypakował do %TEMP% sam PMT_Planer.exe, bez _internal)
    _tmp_w = r"C:\Users\uzytkownik\AppData\Local\Temp"
    _sc_zip = (_tmp_w + r"\cf2513eb-845c-47ed-a4e5-09fbc9158e96_PMT_Planer.Windows.zip.e96"
               r"\PMT_Planer\PMT_Planer.exe")
    sprawdz("start z wnętrza archiwum ZIP (ścieżka ze zdjęcia) jest rozpoznawany jako 'zip'",
            P._uruchomiono_z_folderu_tymczasowego(_sc_zip, _tmp_w) == "zip",
            repr(P._uruchomiono_z_folderu_tymczasowego(_sc_zip, _tmp_w)))
    sprawdz("stary Eksplorator (Temp1_nazwa.zip) też jest rozpoznawany jako 'zip'",
            P._uruchomiono_z_folderu_tymczasowego(_tmp_w + r"\Temp1_PMT_Planer.Windows.zip\PMT_Planer\PMT_Planer.exe", _tmp_w) == "zip")
    sprawdz("start z %TEMP% bez archiwum w ścieżce = 'temp'",
            P._uruchomiono_z_folderu_tymczasowego(_tmp_w + r"\PMT_Planer\PMT_Planer.exe", _tmp_w) == "temp")
    sprawdz("%TEMP% przeniesiony przez użytkownika (D:\\Tymczasowe) też jest wykrywany",
            P._uruchomiono_z_folderu_tymczasowego(r"D:\Tymczasowe\x_PMT_Planer.Windows.zip.1ab\PMT_Planer\PMT_Planer.exe", r"D:\Tymczasowe") == "zip")
    sprawdz("zwykła instalacja C:\\PMT nie jest zgłaszana",
            P._uruchomiono_z_folderu_tymczasowego(r"C:\PMT\PMT_Planer\PMT_Planer.exe", _tmp_w) == "")
    sprawdz("folder o nazwie Temp POZA katalogiem tymczasowym nie jest zgłaszany",
            P._uruchomiono_z_folderu_tymczasowego(r"C:\Temp\PMT_Planer\PMT_Planer.exe", _tmp_w) == "")
    sprawdz("instalacja w OneDrive/Pulpit nie jest zgłaszana",
            P._uruchomiono_z_folderu_tymczasowego(r"C:\Users\uzytkownik\OneDrive\Pulpit\PMT_Planer\PMT_Planer.exe", _tmp_w) == "")
    sprawdz("TEMP ustawiony na korzeń dysku (D:\\) nie zgłasza instalacji na tym dysku",
            P._uruchomiono_z_folderu_tymczasowego(r"D:\PMT\PMT_Planer\PMT_Planer.exe", "D:\\") == "")
    sprawdz("TMP i TEMP różne: wykrywanie działa dla każdego z nich",
            P._uruchomiono_z_folderu_tymczasowego(r"E:\tmp2\x_PMT_Planer.Windows.zip.abc\PMT_Planer\PMT_Planer.exe",
                                                  [r"C:\Users\a\AppData\Local\Temp", r"E:\tmp2"]) == "zip")
    _bylo_frozen_7b = getattr(sys, "frozen", None); _bylo_exe_7b = sys.executable
    try:
        sys.frozen = True
        sys.executable = os.path.join(tempfile.gettempdir(), "x_PMT_Planer.Windows.zip.e96", "PMT_Planer", "PMT_Planer.exe")
        if os.name == "nt":
            _odp = P.zainstaluj_aktualizacje_i_zamknij(os.path.join(_TMP_HOME, "nie_ma.zip"))
            sprawdz("instalator z %TEMP% zwraca wyjaśnienie zamiast podmieniać",
                    isinstance(_odp, str) and "tymczasowego" in _odp, repr(_odp)[:120])
        else:
            sprawdz("poza Windows ostrzeżenie o folderze tymczasowym się nie pojawia",
                    P._uruchomiono_z_folderu_tymczasowego() == "")
    finally:
        sys.executable = _bylo_exe_7b
        if _bylo_frozen_7b is None:
            try:
                del sys.frozen
            except Exception:
                pass
        else:
            sys.frozen = _bylo_frozen_7b
    if not getattr(sys, "frozen", False):
        sprawdz("uruchomienie ze źródeł nigdy nie ostrzega",
                P._uruchomiono_z_folderu_tymczasowego() == "")

    # aktualizator: luźny plik w korzeniu archiwum nie może zatrzymać aktualizacji
    import zipfile as _zf
    for _z_nazwa, _luzny, _opis in (("paczka_czysta.zip", False, "korzeń = jeden folder (układ z GitHuba)"),
                                    ("paczka_z_instrukcja.zip", True, "korzeń = folder + luźny plik")):
        _zr = os.path.join(_TMP_HOME, _z_nazwa)
        with _zf.ZipFile(_zr, "w") as _z:
            _z.writestr("PMT_Planer/PMT_Planer.exe", b"x" * 64)
            _z.writestr("PMT_Planer/_internal/python313.dll", b"y")
            if _luzny:
                _z.writestr("0_NAJPIERW_ROZPAKUJ_CALY_FOLDER.txt", "czytaj")
        _wynik = P.PobieranieAktualizacjiThread()._rozpakuj_folder(_zr)
        sprawdz("aktualizator trafia do folderu z _internal: %s" % _opis,
                bool(_wynik) and os.path.isdir(os.path.join(_wynik, "_internal")), repr(_wynik))
    shutil.rmtree(os.path.join(tempfile.gettempdir(), "PMT_Planer_nowa_wersja"), ignore_errors=True)

    try:
        from PyQt6.QtWidgets import QApplication as _QA
        from PyQt6.QtCore import QTimer as _QT
        _app0 = _QA.instance() or _QA(sys.argv)

        # Okno zwykłej aktualizacji — dwie opcje: zaktualizuj albo później.
        _d1 = P.OknoAktualizacji(None, wersja_stara="3.21.0", wersja_nowa="3.22.0",
                                 opis="Nowości.", is_dark=True, on_instaluj=lambda x: None)
        sprawdz("aktualizacja dobrowolna: jest przycisk instalacji",
                "Zaktualizuj" in _d1.btn_akt.text(), _d1.btn_akt.text())
        sprawdz("aktualizacja dobrowolna: da się odłożyć na później",
                "Przypomnij" in _d1.btn_pozniej.text(), _d1.btn_pozniej.text())
        _QT.singleShot(150, _d1.reject); _d1.exec()

        # Okno blokady — też z działającą instalacją, nie tylko „OK".
        _d2 = P.OknoAktualizacji(None, wersja_stara="3.20.57", wersja_nowa="3.21.0",
                                 opis="Wersja nieobsługiwana.", is_dark=True,
                                 on_instaluj=lambda x: None, wymagana=True)
        sprawdz("wymagana aktualizacja: jest przycisk instalacji, nie samo OK",
                "Zaktualizuj" in _d2.btn_akt.text(), _d2.btn_akt.text())
        sprawdz("wymagana aktualizacja: druga opcja mówi wprost, co się stanie",
                "Zamknij" in _d2.btn_pozniej.text(), _d2.btn_pozniej.text())
        _QT.singleShot(150, _d2.reject); _d2.exec()

        sprawdz("instalator działa też przed zalogowaniem (funkcja modułowa)",
                callable(getattr(P, "zainstaluj_aktualizacje_i_zamknij", None)))
    except Exception as _e:
        sprawdz("okna aktualizacji budują się bez błędu", False, repr(_e))

    sekcja("8. Okno programu buduje się i zamyka")
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import QTimer
        _app = QApplication.instance() or QApplication(sys.argv)
        _okno = P.App()
        _okno.show()
        QTimer.singleShot(600, _app.quit)
        _app.exec()
        sprawdz("główne okno programu buduje się bez błędu", True)
        sprawdz("pasek górny ma przyciski: karta testera ★ i hasło; bez ⋯ i bez pola przełożonego",
                all(hasattr(_okno, n) for n in ("btn_tester", "btn_haslo"))
                and not hasattr(_okno, "btn_wyglad") and not hasattr(_okno, "e_menedzer"))
        # wiersz PARAMETRY TRASY: przy wąskiej karcie (rozwinięte menu) dwa rzędy
        try:
            _okno.card_bot_frame.width = lambda: 900
            _okno._parametry_waskie = None; _okno._uloz_parametry()
            _waski_ok = (_okno._row2_b.count() == 2 and _okno._parametry_waskie is True
                         and _okno.card_bot_frame.minimumHeight() >= _okno.card_bot_frame.layout().sizeHint().height())
            _okno.card_bot_frame.width = lambda: 1200
            _okno._uloz_parametry()
            _szeroki_ok = (_okno._row2_b.count() == 0 and _okno._parametry_waskie is False
                           and 118 <= _okno.card_bot_frame.minimumHeight() < 160)
            sprawdz("parametry trasy: tryb pracy i dni bez pracy schodzą do 2. wiersza przy wąskiej karcie i wracają",
                    _waski_ok and _szeroki_ok, str((_waski_ok, _szeroki_ok)))
        except Exception as _e:
            sprawdz("parametry trasy: tryb pracy i dni bez pracy schodzą do 2. wiersza przy wąskiej karcie i wracają", False, repr(_e))
        # start: intro rusza od razu, bez czarnej „kurtyny" pod paskiem
        try:
            _okno._intro_zakonczone = False; _okno._intro_gra = False
            _okno.intro_po_sprawdzeniu("Jan Testowy")
            _kurt = getattr(_okno, "_kurtyna_start", "brak")
            _intro_od_razu = bool(getattr(_okno, "_intro_gra", False)) or bool(getattr(_okno, "_intro_zakonczone", False))
            sprawdz("start programu: intro rusza od razu, bez czarnej kurtyny", _kurt is None and _intro_od_razu,
                    str((_kurt, getattr(_okno, "_intro_gra", None), getattr(_okno, "_intro_zakonczone", None))))
            _okno._intro_koniec()
        except Exception as _e:
            sprawdz("start programu: intro rusza od razu, bez czarnej kurtyny", False, repr(_e))
        sprawdz("dymek Rozpoznano pracownika czeka na koniec intra",
                "_dymek_po_intrze" in open(os.path.join(KATALOG, "PMT_Delegacje.py"), encoding="utf-8").read().split("def _podpowiedz_profil")[1][:2500])
        sprawdz("ikona okna i intro używają logo retro (spójnie z logo po intrze)",
                os.path.basename(P.znajdz_ikone() or "").startswith("pmt_logo_retro")
                and '"pmt_logo_retro.png"' in open(os.path.join(KATALOG, "intro_zywa_mapa.py"), encoding="utf-8").read())
        # głębia 3D: nakłada się bez błędu i trzyma limit efektów
        import wyglad_3d as _w3d
        _ile3d = P.zastosuj_glebie_interfejsu(_okno)
        sprawdz("głębia 3D nakłada się (0 < elementów ≤ limit %d)" % _w3d.LIMIT_EFEKTOW,
                0 < _ile3d <= _w3d.LIMIT_EFEKTOW, str(_ile3d))
        P.zapisz_ustawienie("wyglad_3d", False)
        sprawdz("głębia 3D wyłączona w ustawieniach = 0 elementów", P.zastosuj_glebie_interfejsu(_okno) == 0)
        P.zapisz_ustawienie("wyglad_3d", True)
        # intro „z orbity do trasy" jako nakładka w oknie: startuje, rysuje klatki, kończy się sygnałem
        import intro_zywa_mapa as _izm
        _izm._DZWIEK_ON = False
        _stan = {"koniec": 0}
        _ok_intro = _izm.sprobuj_intro(_okno, dane=P.dane_intra_z_dysku("Jan Testowy"),
                                       po_zakonczeniu=lambda: _stan.__setitem__("koniec", _stan["koniec"] + 1),
                                       katalog_zasobow=KATALOG, ciemny=True)
        sprawdz("intro z kulą ziemską startuje jako nakładka w oknie", bool(_ok_intro))
        _nakl = [c for c in _okno.findChildren(QWidget) if type(c).__name__ == "IntroZywaMapa"]
        QTimer.singleShot(700, _app.quit)
        _app.exec()                                  # kilkanaście klatek animacji
        sprawdz("nakładka intra istnieje, jest pokazana po pierwszych klatkach i zakrywa okno",
                len(_nakl) == 1 and _nakl[0].isVisibleTo(_okno) and not _nakl[0].isHidden()
                and _nakl[0].width() >= _okno.width() - 2 and float(getattr(_nakl[0], "_t", 0) or 0) > 0.3,
                str([(c.isVisibleTo(_okno), c.width(), _okno.width(), getattr(c, "_t", None)) for c in _nakl]))
        _blad_klatek = None
        try:
            _nakl[0]._zakoncz()                      # jak klik/klawisz użytkownika
            _app.processEvents()
        except Exception as _e:
            _blad_klatek = repr(_e)
        sprawdz("kliknięcie kończy intro i wywołuje po_zakonczeniu dokładnie raz",
                _blad_klatek is None and _stan["koniec"] == 1, _blad_klatek or str(_stan))
        # strażnik: po zdjęciu nakładki przez program intro nie zgłasza końca drugi raz
        _okno._intro_gra = True
        _izm.sprobuj_intro(_okno, dane=P.dane_intra_z_dysku(""), po_zakonczeniu=_okno._intro_koniec,
                           katalog_zasobow=KATALOG, ciemny=True)
        _okno._intro_straznik()
        _app.processEvents()
        _zywe = [c for c in _okno.findChildren(QWidget)
                 if type(c).__name__ == "IntroZywaMapa" and c.isVisible()]
        sprawdz("strażnik zdejmuje żywą mapę i zatrzymuje jej zegar", not _zywe and _okno._intro_zakonczone)
        # karta testera buduje się (osobne okno)
        import karta_testera as _kt
        _kt_ok = _kt.pokaz_karte(_okno)
        sprawdz("karta testera otwiera się z programu", bool(_kt_ok) and _kt._OKNO is not None and _kt._OKNO.isVisible())
        try:
            _kt._OKNO.close()
        except Exception:
            pass
    except Exception as _e:
        sprawdz("główne okno programu buduje się bez błędu", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    sekcja("8b. Nowy wygląd: stan źródła odległości przy liczbach")

    try:
        import nowy_wyglad as _NW
        _app = QApplication.instance() or QApplication(sys.argv)
        _prof_nw = _NW.ProfilWidoku("Jan Testowy", "90010112345",
                                    "ul. Kwiatowa 5, 26-600 Radom", "KR")
        _okno_nw = _NW.OknoNowegoWygladu(profil=_prof_nw, rok=2026, miesiac=10)

        def _nota_nw():
            _okno_nw._odswiez_liczby()
            return _okno_nw.k_parametry.kwota.l_nota.text()

        P._osrm_dostepny = False
        P._road_cache.clear()
        P.zeruj_zrodlo_odleglosci()
        P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
        _nota_szac = _nota_nw()
        sprawdz("nowy wygląd pokazuje „szacunek” przy liczbach, gdy odległości są szacowane",
                _nota_szac.endswith("szacunek"), repr(_nota_szac))

        P.zeruj_zrodlo_odleglosci()
        P._road_cache[P._klucz_drogi(52.23, 21.01, 51.40, 21.15)] = 103.4
        P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
        _nota_real = _nota_nw()
        sprawdz("nowy wygląd pokazuje stan realnych dróg, gdy odległości są realne",
                _nota_real.endswith("drogi z pamięci"), repr(_nota_real))

        P.zeruj_zrodlo_odleglosci()
        _nota_pusto = _nota_nw()
        sprawdz("przed policzeniem czegokolwiek nowy wygląd nie udaje realnych dróg",
                "drogi" not in _nota_pusto and "szacunek" not in _nota_pusto,
                repr(_nota_pusto))
        P._road_cache.clear()
        _okno_nw.close()
    except Exception as _e:
        sprawdz("nowy wygląd pokazuje stan źródła odległości", False, repr(_e))

    # ══════════════════════════════════════════════════════════════════
    sekcja("8c. Nowy wygląd: generowanie, podpis, wysyłka, miesiąc, profil")

    try:
        import nowy_wyglad as _NW
        from PyQt6.QtCore import QTimer as _QTimer
        _app = QApplication.instance() or QApplication(sys.argv)

        # ── etapy kompasu biorą się z MELDUNKU silnika, nie z ułamka ──
        _MELDUNKI = (("Pobieranie współrzędnych GPS...", "dane"),
                     ("Lokalizowanie bazy...", "dane"),
                     ("Generowanie tras...", "trasy"),
                     ("Klastrowanie GPS (Dzień 3/7)...", "trasy"),
                     ("Skalowanie wektorów do budżetu...", "trasy"),
                     ("Wyznaczanie realnych tras drogowych...", "trasy"),
                     ("Odcinki 12/40", "trasy"),
                     ("Rysowanie dokumentów PDF...", "PDF"),
                     ("Generowanie podglądu tras HTML...", "mapa"))
        _zle_etapy = [(t, _NW.etap_silnika(t), e) for t, e in _MELDUNKI
                      if _NW.etap_silnika(t) != e]
        sprawdz("etapy kompasu biorą się z meldunku silnika (wszystkie 9 meldunków trafia we właściwą plakietkę)",
                not _zle_etapy, str(_zle_etapy))
        sprawdz("meldunek z ułamkiem 0,78 to nadal etap TRAS, a nie PDF (próg prototypu kłamał)",
                _NW.etap_silnika("Wyznaczanie realnych tras drogowych...") == "trasy")

        # ── przerwanie generowania ────────────────────────────────────
        sprawdz("GeneratorThread ma anulowanie: metodę anuluj i sygnał anulowano",
                hasattr(P.GeneratorThread, "anuluj") and hasattr(P.GeneratorThread, "anulowano"))
        sprawdz("przerwanie nie jest zwykłym wyjątkiem, więc żaden except Exception w silniku go nie połknie",
                issubclass(P.PrzerwanoGenerowanie, BaseException)
                and not issubclass(P.PrzerwanoGenerowanie, Exception))

        def _czy_przerywa(watek):
            try:
                watek._sprawdz_przerwanie()
                return False
            except P.PrzerwanoGenerowanie:
                return True

        _watek_probny = P.GeneratorThread({})
        _cisza_przed = _czy_przerywa(_watek_probny)
        _watek_probny.anuluj()
        _przerwane_po = _czy_przerywa(_watek_probny)
        _watek_probny._punkt_bez_powrotu = True
        _przerwane_w_pdf = _czy_przerywa(_watek_probny)
        sprawdz("anuluj() przerywa pracę przy najbliższym meldunku, a przed nim nic się nie dzieje",
                _cisza_przed is False and _przerwane_po is True,
                str((_cisza_przed, _przerwane_po)))
        sprawdz("od chwili rysowania PDF-ów przerwanie już nie działa — komplet nie zostaje niepełny",
                _przerwane_w_pdf is False)

        # ── okno na prawdziwym profilu ────────────────────────────────
        P.zapisz_ustawienie(_NW.OknoNowegoWygladu.USTAWIENIE_KWOTY, 0)
        _prof_8c = _NW.ProfilWidoku("Jan Testowy", "85010112345",
                                    "ul. Kwiatowa 5, 26-600 Radom", "KR")
        _okno8c = _NW.OknoNowegoWygladu(profil=_prof_8c, rok=2026, miesiac=10)
        _okno8c.ustaw_animacje(False)

        # ── dane pracownika: pola ↔ magazyn profili programu ──────────
        _okno8c.k_pracownik.imie.setText("Anna Próbna")
        _okno8c._pole_pesel.setText("85010112345")
        _okno8c.k_pracownik.adres.setText("ul. Polna 7, 26-600 Radom")
        _okno8c._zapisz_pracownika()
        _wpis8c = (P._wczytaj_store().get(
            P._klucz_uzytkownika("Anna Próbna", "85010112345")) or {}).get("profil", {})
        sprawdz("karta PRACOWNIK zapisuje dane do magazynu profili programu (~/.pmt_uzytkownicy.json)",
                _wpis8c.get("imie") == "Anna Próbna"
                and _wpis8c.get("adres") == "ul. Polna 7, 26-600 Radom"
                and _wpis8c.get("pesel") == "85010112345", str(_wpis8c))
        sprawdz("PESEL ma w nowym wyglądzie własne pole, widoczne i na 11 cyfr",
                _okno8c._pole_pesel is not None
                and not _okno8c._pole_pesel.isHidden()
                and _okno8c._pole_pesel.maxLength() == 11)
        sprawdz("profil zapisany z nowego wyglądu wraca z dysku przy kolejnym wejściu",
                _NW.profil_z_programu() is not None)
        _okno8c._pole_pesel.setText("11111111111")      # suma kontrolna się nie zgadza
        _okno8c._zapisz_pracownika()
        sprawdz("profil z błędnym PESEL-em nie trafia do magazynu",
                P._klucz_uzytkownika("Anna Próbna", "11111111111") not in P._wczytaj_store())
        _param8c, _powod8c = _okno8c._dane_do_generacji()
        sprawdz("z błędnym PESEL-em nowy wygląd odmawia generowania i nazywa powód",
                _param8c is None and _powod8c == "PESEL", str(_powod8c))
        _okno8c._pole_pesel.setText("85010112345")
        _okno8c.k_pracownik.imie.setText("")
        _param8c, _powod8c = _okno8c._dane_do_generacji()
        sprawdz("bez imienia nowy wygląd odmawia generowania",
                _param8c is None and "imię" in _powod8c, str(_powod8c))
        _okno8c.k_pracownik.imie.setText("Jan Testowy")
        _okno8c.k_pracownik.adres.setText("ul. Kwiatowa 5, 26-600 Radom")
        _okno8c._zapisz_pracownika()
        _param8c, _powod8c = _okno8c._dane_do_generacji()
        sprawdz("komplet danych daje parametry dla wątku silnika (te same klucze, co w App.proces)",
                _param8c is not None
                and _param8c["pesel"] == "85010112345"
                and _param8c["rok"] == _okno8c.rok
                and _param8c["miesiac"] == _okno8c.miesiac
                and _param8c["stawka"] == _okno8c.profil.stawka
                and _param8c["dni_robocze"], str(_powod8c))

        # ── miesiąc: zakładki naprawdę przełączają ────────────────────
        _okno8c.ustaw_miesiac(2026, 10)
        _okno8c._zakladka_miesiaca(0)
        sprawdz("zakładka miesiąca w pasku górnym naprawdę przestawia miesiąc",
                (_okno8c.rok, _okno8c.miesiac) == (2026, 9)
                and _okno8c.pasek.MIESIACE[1] == "wrzesień 2026"
                and _NW.OK.MIESIAC == 9,
                str((_okno8c.rok, _okno8c.miesiac, _okno8c.pasek.MIESIACE)))
        _okno8c.ustaw_miesiac(2026, 12)
        _okno8c.ustaw_miesiac_o(1)
        sprawdz("przełączanie miesiąca przechodzi przez granicę roku",
                (_okno8c.rok, _okno8c.miesiac) == (2027, 1)
                and _okno8c.pasek.MIESIACE[1] == "styczeń 2027",
                str((_okno8c.rok, _okno8c.miesiac, _okno8c.pasek.MIESIACE)))
        sprawdz("taśma pokazuje dni WYBRANEGO miesiąca, co do jednego",
                len(_okno8c.dni) == P.calendar.monthrange(2027, 1)[1]
                and all(d.data.year == 2027 and d.data.month == 1 for d in _okno8c.dni))

        # ── dni bez pracy: osobne dla każdego miesiąca, zapisane na dysk ──
        _okno8c.ustaw_miesiac(2026, 11)
        _okno8c._wolne = {5, 6}
        _okno8c._zapamietaj_wolne()
        _okno8c.ustaw_miesiac(2026, 12)
        _wolne_grudnia = set(_okno8c._wolne)
        _okno8c.ustaw_miesiac(2026, 11)
        sprawdz("dni bez pracy zapisują się w ustawieniach programu i wracają dla SWOJEGO miesiąca",
                _wolne_grudnia == set() and _okno8c._wolne == {5, 6}
                and P.ustawienie(_NW.OknoNowegoWygladu.USTAWIENIE_WOLNYCH, {}).get("2026-11") == [5, 6],
                str((_wolne_grudnia, _okno8c._wolne)))

        # ── kwota i tryb przeżywają zamknięcie okna ───────────────────
        _okno8c.k_parametry.kwota.ustaw_tekst("2 500")
        _okno8c._przelicz_teraz()
        sprawdz("kwota i tryb pracy idą do ~/.pmt_ustawienia.json",
                abs(float(P.ustawienie(_NW.OknoNowegoWygladu.USTAWIENIE_KWOTY, 0)) - 2500.0) < 0.01
                and P.ustawienie(_NW.OknoNowegoWygladu.USTAWIENIE_TRYBU, "")
                == _okno8c.k_parametry.tryb.aktywna())
        # Limit dnia zniknął z okna, więc nie jest już ani zapisywany, ani
        # wczytywany — program liczy zawsze kwotą z przepisów.
        P.zapisz_ustawienie("nowy_limit_dnia", 999.0)
        _okno8d = _NW.OknoNowegoWygladu(profil=_prof_8c, rok=2026, miesiac=11)
        _limit_po_wznowieniu = _okno8d._limit_dnia
        _okno8d.close()
        sprawdz("limit dnia nie da się już zapisać ani odziedziczyć — zawsze kwota z przepisów",
                abs(_limit_po_wznowieniu - P.MAX_KWOTA_DNIA) < 0.005
                and not hasattr(_NW.OknoNowegoWygladu, "USTAWIENIE_LIMITU"),
                str(_limit_po_wznowieniu))
        _okno_wznowione = _NW.OknoNowegoWygladu(profil=_prof_8c, rok=2026, miesiac=11)
        _kwota_wznowiona = _okno_wznowione._kwota()
        _okno_wznowione.close()
        sprawdz("kolejne okno wstaje z zapamiętaną kwotą, a nie z liczbą z prototypu",
                abs(_kwota_wznowiona - 2500.0) < 0.01, str(_kwota_wznowiona))

        # ── taca: prawdziwe pliki z folderu wyniku ────────────────────
        _folder8c = os.path.join(_TMP_HOME, "Rozliczenie_Jan_Testowy_listopad_2026r")
        os.makedirs(_folder8c, exist_ok=True)
        for _nazwa8c in ("delegacja_01_Jan_Testowy_listopad_2026r.pdf",
                         "delegacja_02_Jan_Testowy_listopad_2026r.pdf",
                         "rozliczenie_wydatków_Jan_Testowy_listopad_2026r.pdf"):
            with open(os.path.join(_folder8c, _nazwa8c), "wb") as _f8c:
                _f8c.write(b"%PDF-1.4\n" + _nazwa8c.encode("utf-8") + b"\n%%EOF\n")
        _okno8c.folder_wyniku = _folder8c
        _okno8c._po_generacji = True
        _okno8c._pokaz_tace(animacja=False)
        sprawdz("taca pokazuje PRAWDZIWE pliki z folderu wyniku (przez pmt_dokumenty)",
                len(_okno8c.pliki_wyniku) == 3
                and _okno8c.taca.l_sciezka.text().startswith("listopad 2026")
                and "3 pliki" in _okno8c.taca.l_sciezka.text()
                and _okno8c.taca.l_folder.toolTip() == _folder8c,
                str((len(_okno8c.pliki_wyniku), _okno8c.taca.l_sciezka.text())))
        sprawdz("kartka dnia na tacy prowadzi do PDF-u SWOJEGO dokumentu",
                os.path.basename(_NW.plik_dokumentu(_folder8c, 2))
                == "delegacja_02_Jan_Testowy_listopad_2026r.pdf",
                str(_NW.plik_dokumentu(_folder8c, 2)))
        P.zeruj_zrodlo_odleglosci()
        P._road_cache.clear()
        P._osrm_dostepny = False
        P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
        _okno8c._opisz_tace()
        _opis_km = _okno8c.taca.k_km._opis
        P.zeruj_zrodlo_odleglosci()
        P._road_cache[P._klucz_drogi(52.23, 21.01, 51.40, 21.15)] = 103.4
        P.dystans_drogowy(52.23, 21.01, 51.40, 21.15)
        _okno8c._opisz_tace()
        _opis_km2 = _okno8c.taca.k_km._opis
        P._road_cache.clear()
        sprawdz("kafel kilometrów na tacy nosi STAN ŹRÓDŁA, a nie sztywne REALNE DROGI",
                _opis_km == "SZACUNEK" and _opis_km2 == "DROGI Z PAMIĘCI",
                str((_opis_km, _opis_km2)))

        # ── podpis i wysyłka: okna programu, nie panele makiety ───────
        _slad8c = {}

        class _AtrapaOknaPmt:
            def __init__(self, rodzic=None, **reszta):
                _slad8c.update(reszta)
                _slad8c["klasa"] = type(self).__name__

            def exec(self):
                return 0

            def zatrzymaj_zegar(self):
                _slad8c["zegar"] = "zatrzymany"

            def zakoncz_watek(self):
                _slad8c["watek"] = "zakonczony"

        _stary_podpis, _stara_wysylka = P.DialogPodpis, P.DialogWysylka
        P.DialogPodpis = type("AtrapaPodpisu", (_AtrapaOknaPmt,), {})
        P.DialogWysylka = type("AtrapaWysylki", (_AtrapaOknaPmt,), {})
        try:
            _okno8c._panel_podpisu()
            _slad_podpisu = dict(_slad8c)
            _slad8c.clear()
            _okno8c._panel_wysylki()
            _slad_wysylki = dict(_slad8c)
        finally:
            P.DialogPodpis, P.DialogWysylka = _stary_podpis, _stara_wysylka
        sprawdz("przycisk podpisu otwiera okno podpisu PROGRAMU (nad pmt_podpis) z folderem wyniku",
                _slad_podpisu.get("klasa") == "AtrapaPodpisu"
                and _slad_podpisu.get("folder") == _folder8c
                and _slad_podpisu.get("zegar") == "zatrzymany", str(_slad_podpisu))
        sprawdz("przycisk wysyłki otwiera okno wysyłki PROGRAMU (nad pmt_wysylka) z folderem, imieniem i miesiącem",
                _slad_wysylki.get("klasa") == "AtrapaWysylki"
                and _slad_wysylki.get("folder") == _folder8c
                and _slad_wysylki.get("miesiac") == _okno8c.miesiac
                and _slad_wysylki.get("rok") == _okno8c.rok
                and _slad_wysylki.get("watek") == "zakonczony", str(_slad_wysylki))
        sprawdz("w nowym wyglądzie nie ma już zastępczych paneli podpisu i wysyłki z prototypu",
                "zastepczy_panel_podpisu" not in open(
                    os.path.join(KATALOG, "nowy_wyglad.py"), encoding="utf-8").read())

        # ── pieczęć podpisu z manifestu paczki ────────────────────────
        _mod_podpisu = P.modul_pomocniczy("pmt_podpis")
        _paczka8c, _wpisy8c = _mod_podpisu.przygotuj_paczke(_folder8c)
        _sciezka_man = _mod_podpisu.sciezka_manifestu(_paczka8c)
        _manifest8c = _mod_podpisu.wczytaj_manifest(_sciezka_man)
        for _w8c in _manifest8c.get("pliki", []):
            if _NW.DOK.numer_delegacji(_w8c.get("plik_zrodlowy", "")) == 2:
                _w8c["status"] = _mod_podpisu.STATUS_PODPISANY
        _mod_podpisu.zapisz_manifest(_paczka8c, _manifest8c)
        for _i8c, _d8c in enumerate(_okno8c.dni):
            _d8c.dokument = 2 if _i8c % 2 else 1
        _ile_podpisanych = _okno8c._wczytaj_podpisy()
        sprawdz("pieczęć podpisu bierze się z manifestu paczki podpisowej, nie z klikania w makietę",
                _ile_podpisanych == 1
                and all(_d8c.podpisany == (_d8c.dokument == 2) for _d8c in _okno8c.dni),
                str(_ile_podpisanych))
        with open(os.path.join(_folder8c,
                               "delegacja_02_Jan_Testowy_listopad_2026r.pdf"), "wb") as _f8c:
            _f8c.write(b"%PDF-1.4\nnowa tresc po ponownym generowaniu\n%%EOF\n")
        _ile_po_zmianie = _okno8c._wczytaj_podpisy()
        sprawdz("po ponownym wygenerowaniu dokumentu pieczęć po poprzedniku NIE przechodzi na nowy plik",
                _ile_po_zmianie == 0
                and not any(_d8c.podpisany for _d8c in _okno8c.dni),
                str(_ile_po_zmianie))

        # ── zamknięcie: ani jednego chodzącego zegara, ani wątku ──────
        _okno8c.close()
        _chodzace = [t for t in _okno8c.findChildren(_QTimer) if t.isActive()]
        sprawdz("zamknięte okno nowego wyglądu nie zostawia chodzących zegarów ani wątku",
                not _chodzace and _okno8c._watek is None and not _okno8c._watki_zalegle,
                str((len(_chodzace), _okno8c._watek, _okno8c._watki_zalegle)))
    except Exception as _e:
        sprawdz("nowy wygląd: generowanie, podpis, wysyłka, miesiąc, profil", False, repr(_e))


if not SZYBKO:
    sekcja("8d. Nowy wygląd: kompas naprawdę generuje dokumenty")
    # Okno programu z sekcji 8 zostaje żywe i ma ODŁOŻONE zegary, które
    # otwierają okna MODALNE: zaproszenie do testów (900 ms po intrze) oraz
    # okno aktualizacji. Ta sekcja jako pierwsza mieli zdarzenia przez dłuższą
    # chwilę, więc to ona doczekałaby się ich exec() — i testy stanęłyby
    # na zawsze. Na czas sekcji podstawiamy atrapy; oryginały wracają w finally.
    _stare_okno_akt = P.OknoAktualizacji
    _stare_zaproszenie = P.zaproszenie_testera

    class _AtrapaAktualizacji:
        def __init__(self, *args, **reszta):
            pass

        def exec(self):
            return 0

    P.OknoAktualizacji = _AtrapaAktualizacji
    P.zaproszenie_testera = lambda *args, **reszta: False
    try:
        import nowy_wyglad as _NW2
        from PyQt6.QtWidgets import QApplication
        _app = QApplication.instance() or QApplication(sys.argv)
        _prof8d = _NW2.ProfilWidoku("Jan Testowy", "85010112345",
                                    "ul. Kwiatowa 5, 26-600 Radom", "KR")
        _okno8d = _NW2.OknoNowegoWygladu(profil=_prof8d, rok=2026, miesiac=6)
        _okno8d.ustaw_animacje(False)
        _okno8d.k_parametry.kwota.ustaw_tekst("700")
        _okno8d._przelicz_teraz()
        # Etapy podglądamy próbkowaniem, a nie podmianą slotu: sygnał leci
        # z wątku roboczego, a zwykła funkcja podpięta pod sygnał wykonałaby
        # się PO TAMTEJ stronie i dotykała widżetów spoza wątku okna.
        _etapy_w_toku = []

        def _zanotuj_etap():
            etap = _okno8d._etap_silnika
            if etap and (not _etapy_w_toku or _etapy_w_toku[-1] != etap):
                _etapy_w_toku.append(etap)

        _okno8d.uruchom_pokaz()
        _zanotuj_etap()
        sprawdz("kliknięcie kompasu uruchamia PRAWDZIWY wątek silnika programu",
                isinstance(_okno8d._watek, P.GeneratorThread)
                and _okno8d.k_kompas.kompas.stan() == "praca"
                and _okno8d.k_kompas.TYTUL == "Przerwij", str(_okno8d._watek))
        _koniec8d = datetime.datetime.now() + datetime.timedelta(seconds=300)
        while _okno8d._watek is not None and datetime.datetime.now() < _koniec8d:
            _app.processEvents()
            _zanotuj_etap()
        for _ in range(12):
            _app.processEvents()
        sprawdz("po zakończeniu ekran jest w stanie sukcesu, a kompas otwiera dokumenty",
                _okno8d._po_generacji is True
                and _okno8d.k_kompas.kompas.stan() == "sukces"
                and _okno8d.k_kompas.TYTUL == "Otwórz dokumenty",
                str((_okno8d._po_generacji, _okno8d.k_kompas.kompas.stan())))
        sprawdz("łuk kompasu przeszedł przez etapy silnika: dane → trasy → PDF",
                _etapy_w_toku[:1] == ["dane"] and "trasy" in _etapy_w_toku
                and "PDF" in _etapy_w_toku, str(sorted(set(_etapy_w_toku))))
        _pliki8d = _NW2.dokumenty_w_wyniku(_okno8d.folder_wyniku)
        _delegacje8d = [p for p in _pliki8d
                        if _NW2.DOK.rodzaj_dokumentu(p) == _NW2.DOK.RODZAJ_DELEGACJA]
        sprawdz("w folderze wyniku leżą PRAWDZIWE pliki PDF: delegacje i rozliczenie zbiorcze",
                os.path.isdir(_okno8d.folder_wyniku) and len(_delegacje8d) >= 1
                and any(_NW2.DOK.rodzaj_dokumentu(p) == _NW2.DOK.RODZAJ_ROZLICZENIE
                        for p in _pliki8d)
                and all(os.path.getsize(p) > 1000 for p in _pliki8d),
                str([os.path.basename(p) for p in _pliki8d]))
        sprawdz("taca pokazuje dokładnie te pliki, które powstały",
                _okno8d.pliki_wyniku == _pliki8d and _okno8d._taca_widoczna is True,
                str((len(_okno8d.pliki_wyniku), len(_pliki8d))))
        sprawdz("kwota na tacy zgadza się co do grosza z sumą dni silnika",
                abs(round(sum(d.suma for d in _okno8d._dni_silnika), 2)
                    - _okno8d._osiagnieto) < 0.005 and _okno8d._osiagnieto > 0,
                str(_okno8d._osiagnieto))
        sprawdz("dni na tacy znają numer swojego polecenia wyjazdu",
                all(d.dokument >= 1 for d in _okno8d.dni if not d.wolny),
                str(sorted({d.dokument for d in _okno8d.dni if not d.wolny})))
        # zmiana danych gasi wynik, powrót do tej samej kwoty go NIE gasi
        _okno8d._przelicz_teraz()
        _po_przeliczeniu = _okno8d._po_generacji
        _okno8d.k_parametry.kwota.ustaw_tekst("900")
        _okno8d._przelicz_teraz()
        sprawdz("samo przeliczenie ekranu nie gasi gotowego wyniku, a zmiana kwoty — tak",
                _po_przeliczeniu is True and _okno8d._po_generacji is False
                and _okno8d.k_kompas.kompas.stan() == "zmieniono",
                str((_po_przeliczeniu, _okno8d._po_generacji)))
        _okno8d.close()
    except Exception as _e:
        sprawdz("nowy wygląd: kompas naprawdę generuje dokumenty", False, repr(_e))
    finally:
        P.OknoAktualizacji = _stare_okno_akt
        P.zaproszenie_testera = _stare_zaproszenie


# ══════════════════════════════════════════════════════════════════
sekcja("9. Wersja testowa: dokumenty, podpis, wysyłka, udogodnienia")

# Cała sekcja pracuje na katalogach tymczasowych pod _TMP_HOME: bez internetu,
# bez serwera poczty, bez dotykania folderu programu i danych użytkownika.
_S9 = os.path.join(_TMP_HOME, "sekcja9")
_S9_DOK = os.path.join(_S9, "Rozliczenie_Jan_Testowy_lipiec_2026")
os.makedirs(_S9_DOK, exist_ok=True)


def _s9_pdf(sciezka, tresc, mtime=None):
    """Najmniejszy plik udający PDF — testy sprawdzają nazwy i sumy, nie treść."""
    with open(sciezka, "wb") as f:
        f.write(b"%PDF-1.4\n" + tresc + b"\n%%EOF\n")
    if mtime is not None:
        os.utime(sciezka, (mtime, mtime))
    return sciezka


# Nazwy dokładnie takie, jakie składa generuj_pdfy (delegacja_NN_imię_miesiąc_rok
# oraz rozliczenie_wydatków_…) — numer 10 pilnuje, że kolejność idzie po LICZBIE,
# a nie alfabetycznie (alfabetycznie „10" wypadłoby przed „02").
_S9_DELEGACJE = ("delegacja_01_Jan_Testowy_lipiec_2026r.pdf",
                 "delegacja_02_Jan_Testowy_lipiec_2026r.pdf",
                 "delegacja_10_Jan_Testowy_lipiec_2026r.pdf")
for _i, _nazwa in enumerate(_S9_DELEGACJE):
    _s9_pdf(os.path.join(_S9_DOK, _nazwa), b"delegacja numer %d" % (_i + 1))
_S9_ROZL = _s9_pdf(os.path.join(_S9_DOK, "rozliczenie_wydatków_Jan_Testowy_lipiec_2026r.pdf"),
                   b"zbiorcze rozliczenie miesiaca")
_s9_pdf(os.path.join(_S9_DOK, "faktura_ze_skanera.pdf"), b"obcy plik uzytkownika")
with open(os.path.join(_S9_DOK, "Trasy_Mapa.html"), "w", encoding="utf-8") as _f:
    _f.write("<html></html>")
_S9_PUSTY = os.path.join(_S9, "pusty")
os.makedirs(_S9_PUSTY, exist_ok=True)

# ── moduł dokumentów ──────────────────────────────────────────────
_PD = None
try:
    import pmt_dokumenty as _PD
    sprawdz("moduł pmt_dokumenty importuje się", True)
except Exception as _e:
    sprawdz("moduł pmt_dokumenty importuje się", False, repr(_e))

if _PD is not None:
    _s9_lista = [os.path.basename(x) for x in _PD.dokumenty_w_folderze(_S9_DOK)]
    sprawdz("dokumenty: rozpoznane wszystkie nasze PDF-y, delegacje po numerze (01, 02, 10)",
            _s9_lista == list(_S9_DELEGACJE) + [os.path.basename(_S9_ROZL)], str(_s9_lista))
    sprawdz("dokumenty: obcy PDF i podgląd tras nie trafiają na listę",
            "faktura_ze_skanera.pdf" not in _s9_lista
            and not any(n.lower().endswith(".html") for n in _s9_lista), str(_s9_lista))
    sprawdz("dokumenty: podsumowaniem jest rozliczenie zbiorcze",
            _PD.podsumowanie(_S9_DOK) == _S9_ROZL, repr(_PD.podsumowanie(_S9_DOK)))
    # bez zbiorczego podsumowaniem zostaje delegacja o NAJNIŻSZYM numerze
    _S9_BEZ = os.path.join(_S9, "bez_zbiorczego")
    os.makedirs(_S9_BEZ, exist_ok=True)
    for _nazwa in ("delegacja_10_Jan_Testowy_lipiec_2026r.pdf",
                   "delegacja_02_Jan_Testowy_lipiec_2026r.pdf"):
        _s9_pdf(os.path.join(_S9_BEZ, _nazwa), b"delegacja bez zbiorczego")
    sprawdz("dokumenty: bez rozliczenia podsumowaniem jest delegacja o najniższym numerze",
            os.path.basename(_PD.podsumowanie(_S9_BEZ) or "")
            == "delegacja_02_Jan_Testowy_lipiec_2026r.pdf",
            repr(_PD.podsumowanie(_S9_BEZ)))
    sprawdz("dokumenty: pusty folder = brak dokumentów i brak podsumowania",
            _PD.dokumenty_w_folderze(_S9_PUSTY) == [] and _PD.podsumowanie(_S9_PUSTY) is None
            and _PD.opis_kompletu(_S9_PUSTY) == "brak plików",
            repr(_PD.opis_kompletu(_S9_PUSTY)))
    sprawdz("dokumenty: folder nieistniejący i None nie wywracają programu",
            _PD.dokumenty_w_folderze(os.path.join(_S9, "nie ma takiego")) == []
            and _PD.podsumowanie(None) is None)
    _s9_opis = _PD.opis_kompletu(_S9_DOK)
    sprawdz("dokumenty: opis kompletu to same liczby (3 delegacje · 1 inny plik · rozmiar)",
            _s9_opis.startswith("3 delegacje") and "1 inny plik" in _s9_opis
            and _s9_opis.count("·") == 2 and "." not in _s9_opis, repr(_s9_opis))

# ── moduł podpisu ─────────────────────────────────────────────────
_PS = None
try:
    import pmt_podpis as _PS
    sprawdz("moduł pmt_podpis importuje się", True)
except Exception as _e:
    sprawdz("moduł pmt_podpis importuje się", False, repr(_e))

if _PS is not None:
    import time as _time
    _s9_teraz = _time.time()
    _s9_otwarcie = _s9_teraz - 120          # moment otwarcia strony usługi
    _s9_swiezo = _s9_teraz - 10
    try:
        _s9_paczka, _s9_wpisy = _PS.przygotuj_paczke(_S9_DOK)
        _s9_manifest = _PS.sciezka_manifestu(_s9_paczka)
        _s9_dane = _PS.wczytaj_manifest(_s9_manifest)
    except Exception as _e:
        _s9_paczka, _s9_wpisy, _s9_manifest, _s9_dane = "", [], "", {}
        sprawdz("podpis: paczka Do_podpisu powstaje bez błędu", False, repr(_e))
    if _s9_dane:
        sprawdz("podpis: paczka to podfolder Do_podpisu z manifestem",
                os.path.basename(_s9_paczka) == "Do_podpisu" and os.path.isfile(_s9_manifest),
                repr(_s9_paczka))
        # Do paczki idzie KAŻDY plik .pdf z folderu (także dołożony przez
        # użytkownika skan) — podpisać można wszystko, co ma iść do przełożonego.
        # Podglądu tras (.html) nie podpisujemy.
        _s9_pdfy = sorted(n for n in os.listdir(_S9_DOK) if n.lower().endswith(".pdf"))
        sprawdz("podpis: kopia każdego PDF-u w paczce, oryginały nietknięte, bez .html",
                len(_s9_wpisy) == len(_s9_pdfy)
                and all(os.path.isfile(os.path.join(_s9_paczka, w["plik"])) for w in _s9_wpisy)
                and not any(w["plik"].lower().endswith(".html") for w in _s9_wpisy)
                and all(os.path.isfile(os.path.join(_S9_DOK, n)) for n in _s9_pdfy),
                str([w.get("plik") for w in _s9_wpisy]))
        sprawdz("podpis: kopia zbiorczego bez ogonków w nazwie (portale nie lubią diakrytyków)",
                os.path.isfile(os.path.join(_s9_paczka,
                                            "rozliczenie_wydatkow_Jan_Testowy_lipiec_2026r.pdf")))
        sprawdz("podpis: manifest ma imię, miesiąc i rok odczytane z nazwy folderu",
                (_s9_dane.get("imie"), _s9_dane.get("miesiac"), _s9_dane.get("rok"))
                == ("Jan Testowy", 7, 2026),
                str((_s9_dane.get("imie"), _s9_dane.get("miesiac"), _s9_dane.get("rok"))))
        _s9_sumy_ok = []
        for _w in _s9_dane.get("pliki", []):
            _kopia = os.path.join(_s9_paczka, _w.get("plik", ""))
            _s9_sumy_ok.append(len(str(_w.get("skrot", ""))) == 64
                               and _w["skrot"] == _PS.suma_sha256(_kopia)
                               and int(_w.get("rozmiar", 0)) == os.path.getsize(_kopia))
        sprawdz("podpis: każdy wpis manifestu ma sumę SHA-256 i rozmiar zgodne z plikiem",
                bool(_s9_sumy_ok) and all(_s9_sumy_ok), str(_s9_sumy_ok))
        sprawdz("podpis: świeża paczka czeka na podpis (żaden wpis nie udaje podpisanego)",
                all(w.get("status") == "do_podpisu" for w in _s9_dane["pliki"]),
                str([w.get("status") for w in _s9_dane["pliki"]]))

        # WETO: użytkownik pobrał z powrotem TĘ SAMĄ, niepodpisaną kopię.
        # Nazwa, świeży czas i rozszerzenie dają komplet przesłanek, a mimo to
        # identyczna suma kontrolna musi taki plik odrzucić — podpisany PDF
        # z definicji ma inną sumę.
        _S9_POB = os.path.join(_S9, "Pobrane_weto")
        os.makedirs(_S9_POB, exist_ok=True)
        _s9_weto = os.path.join(_S9_POB, "delegacja_01_Jan_Testowy_lipiec_2026r-podpisany.pdf")
        shutil.copyfile(os.path.join(_S9_DOK, _S9_DELEGACJE[0]), _s9_weto)
        os.utime(_s9_weto, (_s9_swiezo, _s9_swiezo))
        _s9_w = _PS.znajdz_podpisane(_s9_manifest, [_S9_POB], _s9_otwarcie)
        sprawdz("podpis: plik o identycznej sumie kontrolnej odrzucony jako NIEPODPISANY",
                len(_s9_w) == 1 and _s9_w[0]["decyzja"] == "odrzuc" and _s9_w[0]["plik"] is None,
                str([(x["decyzja"], x["punkty"], x["plik"]) for x in _s9_w]))
        _s9_blad = None
        try:
            _PS.oznacz_podpisany(_s9_manifest, _s9_dane["pliki"][0]["plik"], _s9_w[0])
        except ValueError as _e:
            _s9_blad = _e
        sprawdz("podpis: plikiem z wetem nie da się oznaczyć wpisu jako podpisanego",
                isinstance(_s9_blad, ValueError))

        # REMIS: neutralna nazwa pasuje tak samo do każdego wpisu — nie zgadujemy.
        _S9_POB2 = os.path.join(_S9, "Pobrane_remis")
        os.makedirs(_S9_POB2, exist_ok=True)
        _s9_pdf(os.path.join(_S9_POB2, "dokument_podpisany.pdf"),
                b"zupelnie inna tresc", _s9_swiezo)
        _s9_r = _PS.znajdz_podpisane(_s9_manifest, [_S9_POB2], _s9_otwarcie)
        sprawdz("podpis: remis punktowy nie daje dopasowania (żaden wpis nie jest zgadywany)",
                len(_s9_r) == 1 and _s9_r[0]["decyzja"] == "remis"
                and _s9_r[0]["plik"] is None and len(_s9_r[0]["kandydaci"]) > 1,
                str([(x["decyzja"], x["punkty"], x["plik"], x["kandydaci"]) for x in _s9_r]))
        sprawdz("podpis: kopie z paczki i oryginały pomijane w ciszy (bez pytań co 2 s)",
                _PS.znajdz_podpisane(_s9_manifest, [_s9_paczka, _S9_DOK], _s9_otwarcie) == [])

# ── moduł wysyłki ─────────────────────────────────────────────────
_PW = None
try:
    import pmt_wysylka as _PW
    sprawdz("moduł pmt_wysylka importuje się", True)
except Exception as _e:
    sprawdz("moduł pmt_wysylka importuje się", False, repr(_e))

if _PW is not None:
    _s9_temat = _PW.temat_wiadomosci("Jan Testowy", 7, 2026)
    sprawdz("wysyłka: temat zawiera imię, nazwisko, miesiąc słownie i rok",
            "Jan" in _s9_temat and "Testowy" in _s9_temat
            and "lipiec" in _s9_temat and "2026" in _s9_temat, repr(_s9_temat))
    sprawdz("wysyłka: miesiąc podany słownie daje ten sam temat co numer",
            _PW.temat_wiadomosci("Jan Testowy", "lipiec", "2026") == _s9_temat,
            repr(_PW.temat_wiadomosci("Jan Testowy", "lipiec", "2026")))
    sprawdz("wysyłka: szablon bez wymaganych pól wraca do domyślnego",
            _PW.szablon_poprawny("Dokumenty do podpisu") is False
            and _PW.temat_wiadomosci("Jan Testowy", 7, 2026,
                                     szablon="Dokumenty do podpisu") == _s9_temat,
            repr(_PW.temat_wiadomosci("Jan Testowy", 7, 2026, szablon="Dokumenty do podpisu")))
    sprawdz("wysyłka: szablon z kompletem pól jest respektowany",
            _PW.szablon_poprawny("{imie} / {miesiac} / {rok}") is True
            and _PW.temat_wiadomosci("Jan Testowy", 7, 2026,
                                     szablon="{imie} / {miesiac} / {rok}")
            == "Jan Testowy / lipiec / 2026",
            repr(_PW.temat_wiadomosci("Jan Testowy", 7, 2026, szablon="{imie} / {miesiac} / {rok}")))
    sprawdz("wysyłka: urwany nawias w szablonie nie wywraca tematu",
            _PW.temat_wiadomosci("Jan Testowy", 7, 2026, szablon="{imie} {miesiac") == _s9_temat,
            repr(_PW.temat_wiadomosci("Jan Testowy", 7, 2026, szablon="{imie} {miesiac")))

    # Temat z ogonkami MUSI wyjść z nagłówka taki, jaki wszedł. Nagłówek idzie
    # przez sieć jako czyste ASCII (RFC 2047) — surowe UTF-8 rozjeżdża temat
    # w skrzynce odbiorcy.
    _s9_temat_pl = _PW.temat_wiadomosci("Łukasz Żółć-Ćwiąkała", 9, 2026)
    sprawdz("wysyłka: polskie znaki w imieniu wchodzą do tematu bez zniekształceń",
            "Łukasz Żółć-Ćwiąkała" in _s9_temat_pl and "wrzesień" in _s9_temat_pl,
            repr(_s9_temat_pl))
    _s9_wiad = None
    try:
        _s9_wiad = _PW.zbuduj_wiadomosc("nadawca@przyklad.pl", "odbiorca@przyklad.pl",
                                        _s9_temat_pl, [_S9_ROZL])
    except Exception as _e:
        sprawdz("wysyłka: wiadomość z załącznikiem składa się bez błędu", False, repr(_e))
    if _s9_wiad is not None:
        import email as _email
        import email.policy as _email_policy
        _s9_bajty = _s9_wiad.as_bytes()
        _s9_naglowki = _s9_bajty.split(b"\r\n\r\n", 1)[0]
        _s9_odczyt = _email.message_from_bytes(_s9_bajty, policy=_email_policy.SMTP)
        sprawdz("wysyłka: temat z ogonkami zakodowany w nagłówku (czyste ASCII, RFC 2047)",
                all(b < 128 for b in _s9_naglowki)
                and b"=?utf-8?" in _s9_naglowki.lower(),
                repr(_s9_naglowki.split(b"Subject:")[-1][:80]))
        sprawdz("wysyłka: odczytany z powrotem temat jest identyczny z wysłanym",
                str(_s9_odczyt["Subject"]) == _s9_temat_pl, repr(str(_s9_odczyt["Subject"])))
        sprawdz("wysyłka: załącznik dołączony pod własną nazwą",
                [os.path.basename(_S9_ROZL)]
                == [a.get_filename() for a in _s9_odczyt.iter_attachments()],
                str([a.get_filename() for a in _s9_odczyt.iter_attachments()]))
    # Zasada: program nie przechowuje haseł do usług zewnętrznych. Hasło żyje
    # tylko w słowniku na czas jednej wysyłki; kopia idąca do zapisu i dziennika
    # nie może go nieść.
    _s9_ust = _PW.przygotuj_ustawienia({"nadawca": "nadawca@przyklad.pl",
                                        "login": "nadawca@przyklad.pl",
                                        "haslo": "TAJNE-HASLO-TESTOWE",
                                        "serwer": "smtp.przyklad.pl"})
    _s9_ust_bez = _PW.bez_hasla(_s9_ust)
    sprawdz("wysyłka: kopia ustawień do zapisu i dziennika nie niesie hasła",
            _s9_ust.get("haslo") == "TAJNE-HASLO-TESTOWE"
            and not _s9_ust_bez.get("haslo")
            and "TAJNE-HASLO-TESTOWE" not in json.dumps(_s9_ust_bez, ensure_ascii=False),
            str(sorted(_s9_ust_bez)))

# ── etykieta wydania a czysty numer wersji ────────────────────────
# testy_pmt.py robi int() na członach numeru POZA blokiem obsługi wyjątków —
# dopisek w rodzaju „3.22.0-TEST" wysypałby cały skrypt, a nie jeden test.
sprawdz("numer wersji jest czystym zapisem X.Y.Z (int() na członach nie wysypie testów)",
        bool(re.match(r"^\d+\.\d+\.\d+$", P.WERSJA_PROGRAMU))
        and all(str(int(_c)) == _c for _c in P.WERSJA_PROGRAMU.split(".")),
        repr(P.WERSJA_PROGRAMU))
_s9_etykieta = getattr(P, "ETYKIETA_WYDANIA", None)
sprawdz("etykieta wydania jest OSOBNĄ stałą, poza numerem wersji",
        isinstance(_s9_etykieta, str)
        and (not _s9_etykieta or _s9_etykieta not in P.WERSJA_PROGRAMU),
        repr(_s9_etykieta))
_s9_stara_etykieta = getattr(P, "ETYKIETA_WYDANIA", "")
try:
    P.ETYKIETA_WYDANIA = "WERSJA TESTOWA"
    _s9_z = (P.wersja_pelna(), P.tytul_okna())
    P.ETYKIETA_WYDANIA = ""
    _s9_bez = (P.wersja_pelna(), P.tytul_okna())
finally:
    P.ETYKIETA_WYDANIA = _s9_stara_etykieta
sprawdz("etykieta wydania widoczna w wersji i w tytule okna",
        _s9_z == ("%s — WERSJA TESTOWA" % P.WERSJA_PROGRAMU, "PMT Planer — WERSJA TESTOWA"),
        str(_s9_z))
sprawdz("wyzerowanie etykiety zdejmuje oznaczenie ze wszystkich miejsc naraz",
        _s9_bez == (P.WERSJA_PROGRAMU, "PMT Planer"), str(_s9_bez))

# ── ubezpieczenie paczki testowej: BEZ_AKTUALIZACJI.txt ───────────
_S9_PROG = os.path.join(_S9, "udaje_katalog_programu")
os.makedirs(_S9_PROG, exist_ok=True)
_s9_brak = P._aktualizacje_wylaczone_plikiem(_S9_PROG)
_s9_dom = os.path.join(_TMP_HOME, "BEZ_AKTUALIZACJI.txt")
open(_s9_dom, "w").close()
_s9_u_uzytkownika = P._aktualizacje_wylaczone_plikiem(_S9_PROG)
_s9_domyslny = P._aktualizacje_wylaczone_plikiem()      # domyślnie katalog programu
_s9_obok = os.path.join(_S9_PROG, "BEZ_AKTUALIZACJI.txt")
open(_s9_obok, "w").close()
_s9_u_programu = P._aktualizacje_wylaczone_plikiem(_S9_PROG)
os.remove(_s9_obok)
_s9_po_usunieciu = P._aktualizacje_wylaczone_plikiem(_S9_PROG)
os.remove(_s9_dom)
sprawdz("BEZ_AKTUALIZACJI.txt obok programu wyłącza aktualizacje (a bez pliku nie)",
        _s9_u_programu is True and _s9_brak is False and _s9_po_usunieciu is False,
        str((_s9_brak, _s9_u_programu, _s9_po_usunieciu)))
sprawdz("BEZ_AKTUALIZACJI.txt w katalogu UŻYTKOWNIKA niczego nie wyłącza "
        "(inaczej zostałby trwałym obejściem blokady wersji)",
        _s9_u_uzytkownika is False and _s9_domyslny is False,
        str((_s9_u_uzytkownika, _s9_domyslny)))

# ── wyłącznik animacji startowej ──────────────────────────────────
_s9_bylo_intro = P.ustawienie("bez_intra", False)
try:
    P.zapisz_ustawienie("bez_intra", True)
    P._ustawienia_reset()                 # tak samo jak świeży start programu
    _s9_zapisane = P.ustawienie("bez_intra", False)
    with open(P.USTAWIENIA_STORE, encoding="utf-8") as _f:
        _s9_na_dysku = json.load(_f).get("bez_intra")
    P.zapisz_ustawienie("bez_intra", False)
    P._ustawienia_reset()
    _s9_cofniete = P.ustawienie("bez_intra", True)
finally:
    P.zapisz_ustawienie("bez_intra", _s9_bylo_intro)
    P._ustawienia_reset()
sprawdz("ustawienie bez_intra zapisuje się na dysk i wraca przy kolejnym odczycie",
        _s9_zapisane is True and _s9_na_dysku is True and _s9_cofniete is False,
        str((_s9_zapisane, _s9_na_dysku, _s9_cofniete)))
sprawdz("przełącznik animacji ma obsługę w oknie (stan przycisku i zapis ustawienia)",
        callable(getattr(P.App, "_przelacz_intro", None))
        and callable(getattr(P.App, "_odswiez_btn_intro", None)))
sprawdz("animacja startowa czyta dokładnie ten klucz, który zapisuje przycisk",
        '"bez_intra"' in _zrodlo.split("def pokaz_intro")[1][:4000]
        or "'bez_intra'" in _zrodlo.split("def pokaz_intro")[1][:4000])

shutil.rmtree(_S9, ignore_errors=True)

# ══════════════════════════════════════════════════════════════════
sekcja("10. Nowy wygląd jako JEDYNY interfejs programu")

_s10_status_byl = None
try:
    if os.path.exists(P.PLIK_STATUSU):
        _s10_status_byl = open(P.PLIK_STATUSU, encoding="utf-8").read()
except Exception:
    _s10_status_byl = None

try:
    from PyQt6.QtWidgets import QApplication as _QA10, QWidget as _QW10
    import nowy_wyglad as _NW10
    _app10 = _QA10.instance() or _QA10(sys.argv)

    _zrodlo10 = open(os.path.join(KATALOG, "PMT_Delegacje.py"), encoding="utf-8").read()
    _blok10 = _zrodlo10.split('if __name__ == "__main__":')[1]

    # ── sekwencja startowa NIETKNIĘTA ─────────────────────────────
    sprawdz("start programu wciąż rozgrzewa zaplecze, sprawdza wersję i ŻĄDA LOGOWANIA",
            "_rozgrzej_backend()" in _blok10 and "wersja_zablokowana()" in _blok10
            and "dialog_logowania()" in _blok10 and "sys.exit(0)" in _blok10)
    sprawdz("sekwencja startowa nadal woła intro_po_sprawdzeniu "
            "(samo intro jest w tej wersji wyłączone — patrz sekcja 11)",
            "intro_po_sprawdzeniu" in _blok10)
    sprawdz("okno główne powstaje na końcu sekwencji, przez zbuduj_okno_glowne()",
            "window = zbuduj_okno_glowne()" in _blok10)
    sprawdz("przełącznik --nowy zniknął jako droga wejścia",
            "--nowy" not in _zrodlo10)
    sprawdz("wyjście awaryjne --stary istnieje, ale nigdzie się nim nie chwalimy "
            "(jedno wystąpienie: sama decyzja w zbuduj_okno_glowne)",
            _zrodlo10.count('"--stary"') == 1)

    # ── które okno powstaje ───────────────────────────────────────
    _okno10 = P.zbuduj_okno_glowne(["prog"])
    sprawdz("program domyślnie buduje NOWE okno",
            type(_okno10).__name__ == "OknoNowegoWygladu", type(_okno10).__name__)
    sprawdz("stare okno żyje pod nim jako gospodarz paneli (nic nie ginie)",
            isinstance(getattr(_okno10, "_stare", None), P.App))
    _okno10_stare = P.zbuduj_okno_glowne(["prog", "--stary"])
    sprawdz("argument awaryjny --stary nadal oddaje dawne okno",
            isinstance(_okno10_stare, P.App), type(_okno10_stare).__name__)
    try:
        _okno10_stare.close()
    except Exception:
        pass

    # ── szyna: żadnej martwej ikony ───────────────────────────────
    _szyna10 = _okno10.szyna
    _akcje10 = _okno10.akcje_szyny()
    _numery10 = list(range(len(_szyna10.IKONY))) + \
                [100 + i for i in range(len(_szyna10.DOLNE))]
    _martwe10 = [n for n in _numery10 if not callable(_akcje10.get(n))]
    sprawdz("każda ikona szyny ma podpiętą akcję (żadnej martwej)",
            not _martwe10 and len(_akcje10) == len(_numery10), str(_martwe10))
    sprawdz("każda ikona szyny ma nazwę pod kursorem",
            all(_szyna10.nazwa(n) for n in _numery10))
    sprawdz("szyna melduje kliknięcie sygnałem, a nie tylko się podświetla",
            hasattr(_szyna10, "wybrano"))

    # ── panele z szyny: nad NOWYM oknem i w jego materiale ────────
    _stare10 = _okno10.stare_okno()
    _okno10.show()
    _app10.processEvents()

    def _panel_nowego(widget):
        """Panel siedzi w ramie nowego okna, jest w niej widoczny, a stare
        okno zostaje schowane (użytkownik nie widzi jego kawałka)."""
        rama = getattr(_okno10, "_nakladka", None)
        return (rama is not None and rama.panel() is widget
                and widget.window() is _okno10
                and rama.isVisible() and widget.isVisible()
                and not _stare10.isVisible())

    _okno10.dzial_twoja_praca()
    _app10.processEvents()
    sprawdz("ikona „Twoja praca” otwiera prawdziwy panel statystyk w nowym oknie",
            _panel_nowego(_stare10.overlay_staty))
    _okno10.dzial_nowa_wyprawa()
    _app10.processEvents()
    sprawdz("ikona „Nowa wyprawa” otwiera planer przystanków w nowym oknie",
            _panel_nowego(_stare10.overlay_planer))
    _okno10.dzial_plan_wizyt()
    _app10.processEvents()
    sprawdz("ikona „Plan wizyt” otwiera plan w nowym oknie",
            _panel_nowego(_stare10.overlay_plan))
    _okno10.dzial_ustawienia()
    _app10.processEvents()
    sprawdz("ikona „Ustawienia” otwiera panel administratora w nowym oknie",
            _panel_nowego(_stare10.overlay_admin))
    _okno10.dzial_kopia_zapasowa()
    _app10.processEvents()
    sprawdz("ikona „Kopia zapasowa” otwiera kopię w nowym oknie, bez własnego okna",
            _panel_nowego(_okno10._kopia)
            and not _okno10._kopia.isModal())
    _okno10.dzial_o_programie()
    _app10.processEvents()
    sprawdz("ikona „O programie” otwiera panel programu w nowym oknie",
            _panel_nowego(_okno10._o_programie))

    # ── żaden panel nie zostaje w starym stylu ────────────────────
    _stary_kroj = [w for w in _stare10.overlay_staty.findChildren(_QW10)
                   if "Segoe UI" in w.styleSheet()]
    sprawdz("panel po otwarciu nie ma już kroju starego okna (Segoe UI)",
            not _stary_kroj, str([w.objectName() for w in _stary_kroj][:4]))
    _cyjanowe_ramki = [w for w in _stare10.overlay_planer.findChildren(_QW10)
                       if "rgba(0,240,255,0.25)" in w.styleSheet().replace(" ", "")]
    sprawdz("panel po otwarciu nie ma już cyjanowych ramek starego okna",
            not _cyjanowe_ramki, str([w.objectName() for w in _cyjanowe_ramki][:4]))
    sprawdz("nagłówek panelu daje rama nowego systemu, nie panel",
            not _stare10.overlay_planer.tytul.isVisible()
            and not _stare10.overlay_planer.btn_x.isVisible()
            and _okno10._nakladka.b_zamknij.isVisible())
    sprawdz("rama panelu zakrywa ekran pracy poza szyną i paskiem górnym",
            _okno10._nakladka.x() == _NW10.OK.SZYNA_W
            and _okno10._nakladka.y() == _NW10.OK.PASEK_H
            and _okno10._nakladka.width() == _okno10.width() - _NW10.OK.SZYNA_W)

    # ── ekran startowy ───────────────────────────────────────────
    _okno10.dzial_ekran_startowy()
    _app10.processEvents()
    _start10 = _okno10._ekran_startowy
    sprawdz("ekran startowy istnieje i otwiera się z szyny",
            _start10 is not None and _panel_nowego(_start10))
    sprawdz("ikona domu jest PIERWSZA w szynie i prowadzi do ekranu startowego",
            _okno10.szyna.IKONY[0] == "dom"
            and _okno10.NUMER_STARTU == 0
            and _okno10.akcje_szyny()[0] == _okno10.dzial_ekran_startowy
            and _okno10.szyna.nazwa(0) == "Ekran startowy")
    sprawdz("ekran startowy pokazuje dzisiejszą datę w nagłówku",
            _okno10._nakladka.l_podtytul.text()
            == _NW10.data_slownie(datetime.date.today()),
            _okno10._nakladka.l_podtytul.text())
    sprawdz("ekran startowy ma kartę dnia, liczby miesiąca i skrót do bilansu",
            _start10.l_dzien.text() in ("Dziś w trasie", "Dziś bez trasy")
            and _start10.k_wizyty.isVisible() and _start10.b_bilans.isVisible()
            and _start10.b_bilans.text() == "Bilans miesiąca")
    _okno10.b_start_bilans_klik = _start10.b_bilans.click()
    _app10.processEvents()
    sprawdz("skrót „Bilans miesiąca” wraca na ekran pracy",
            not _okno10._nakladka.isVisible()
            and _okno10.szyna._aktywna == _okno10.NUMER_BILANSU)

    # ── mapa tras ────────────────────────────────────────────────
    _folder10 = tempfile.mkdtemp(prefix="pmt_mapa_")
    _okno10.folder_wyniku = _folder10
    sprawdz("przycisk mapy tras stoi na tacy dokumentów",
            getattr(_okno10.taca, "b_mapa", None) is not None)
    # bez żadnej mapy na dysku (także bez tej z wcześniejszych sekcji)
    _szukajka10 = _NW10.folder_z_mapa_tras
    _NW10.folder_z_mapa_tras = lambda: ""
    try:
        _bez_mapy10 = (_okno10._odswiez_stan_mapy() is False
                       and not _okno10.taca.b_mapa.isEnabled()
                       and _okno10.taca.b_mapa.text() == "Mapa tras · brak"
                       and _okno10.otworz_mape_tras() == "")
        _bez_mapy_start10 = (_start10.b_mapa.text() == "Mapa tras · brak"
                             and not _start10.b_mapa.isEnabled())
    finally:
        _NW10.folder_z_mapa_tras = _szukajka10
    sprawdz("bez pliku mapy przycisk stoi i pokazuje stan", _bez_mapy10)
    sprawdz("ekran startowy też pokazuje brak mapy", _bez_mapy_start10)
    with open(os.path.join(_folder10, "Trasy_Mapa.html"), "w", encoding="utf-8") as _f10:
        _f10.write("<html></html>")
    _otwarte10 = []
    _stare_otworz10 = P.otworz_w_systemie
    P.otworz_w_systemie = lambda sciezka: _otwarte10.append(sciezka)
    try:
        _wynik10 = _okno10.otworz_mape_tras()
    finally:
        P.otworz_w_systemie = _stare_otworz10
    sprawdz("z plikiem mapy przycisk otwiera Trasy_Mapa.html istniejącym mechanizmem",
            _okno10._odswiez_stan_mapy() is True
            and _okno10.taca.b_mapa.isEnabled()
            and _okno10.taca.b_mapa.text() == "Mapa tras"
            and _otwarte10 == [os.path.join(_folder10, "Trasy_Mapa.html")]
            and _wynik10 == _otwarte10[0], str(_otwarte10))
    _okno10.folder_wyniku = ""
    shutil.rmtree(_folder10, ignore_errors=True)

    _okno10.dzial_ekran_glowny()
    _app10.processEvents()
    sprawdz("powrót na ekran pracy zdejmuje panel i nie odsłania starego okna",
            not _stare10.isVisible() and _okno10.isVisible()
            and not _okno10._nakladka.isVisible())

    # ── pasek górny: prawdziwe konto ──────────────────────────────
    json.dump({"kod": "12345", "imie": "Jan Kowalski", "wazne_do": "2031-03-31"},
              open(P.PLIK_STATUSU, "w", encoding="utf-8"))
    _napis10, _wazne10 = _NW10.waznosc_konta()
    sprawdz("pasek górny bierze ważność konta z pliku statusu, nie z prototypu",
            _napis10 == "Konto ważne do 31.03.2031" and _wazne10 is True, repr(_napis10))
    _okno10._imie_zalogowany = "Jan Kowalski"
    sprawdz("inicjały w pasku to inicjały ZALOGOWANEJ osoby",
            _okno10.pasek.inicjaly == "JK", repr(_okno10.pasek.inicjaly))
    sprawdz("pasek górny ma podpięte: konto, dzwonek, zgłoszenie błędu i awatar",
            all(callable(getattr(_okno10, m, None)) for m in
                ("pokaz_stan_konta", "przelacz_powiadomienia", "zglos_blad",
                 "menu_konta", "wyloguj", "zmien_haslo")))
    sprawdz("kliknięcia prawej strony paska mają własne sygnały",
            all(hasattr(_okno10.pasek, s10) for s10 in
                ("klik_konta", "klik_dzwonka", "klik_bledu", "klik_awatara")))

    # ── menu awatara: hasło, tester, intro, wylogowanie ───────────
    _menu10, _akcje_menu10 = _okno10.buduj_menu_konta()
    _pozycje10 = [a.text() for a in _menu10.actions() if a.text()]
    _oczekiwane10 = ["Zmień hasło", "Karta testera"]
    if bool(getattr(P, "INTRO_NA_STARCIE", True)):
        _oczekiwane10.append("Animacja startowa")
    _oczekiwane10.append("Wyloguj")
    sprawdz("menu pod inicjałami ma hasło, kartę testera i wylogowanie",
            _pozycje10 == _oczekiwane10, str(_pozycje10))
    sprawdz("każda pozycja menu awatara ma podpiętą akcję",
            all(callable(_akcje_menu10.get(a)) for a in _menu10.actions() if a.text()))
    # Przełącznik animacji pojawia się TYLKO wtedy, gdy animacja startuje —
    # przy wyłączonym intrze byłby martwą pozycją.
    _intro_akcje10 = [a for a in _menu10.actions() if a.text() == "Animacja startowa"]
    sprawdz("przełącznik animacji jest w menu wtedy i tylko wtedy, gdy intro startuje",
            bool(_intro_akcje10) == bool(getattr(P, "INTRO_NA_STARCIE", True)))
    if _intro_akcje10:
        sprawdz("pozycja „Animacja startowa” pokazuje stan ustawienia bez_intra",
                _intro_akcje10[0].isChecked()
                == (not bool(P.ustawienie("bez_intra", False))))
    _menu10.deleteLater()

    # ── dzwonek: jedna historia powiadomień dla obu okien ─────────
    _ile10 = _okno10._nieprzeczytane
    _stare10.toast.show_toast("Próba", "Komunikat kontrolny", success=True)
    _app10.processEvents()
    sprawdz("komunikat ze starego okna trafia do dzwonka nowego ekranu",
            _okno10._nieprzeczytane > _ile10
            and _okno10.toast.historia is _stare10.toast.historia)
    _okno10.przelacz_powiadomienia()
    _app10.processEvents()
    sprawdz("dzwonek rozwija panel powiadomień z historią komunikatów",
            _okno10.panel_powiadomien.isVisible()
            and _okno10._nieprzeczytane == 0)
    _okno10.przelacz_powiadomienia()
    _app10.processEvents()

    # ── konto wiąże dane pracownika ───────────────────────────────
    _prof10 = _NW10.dane_pracownika()
    sprawdz("pracownik na nowym ekranie bierze się z ZALOGOWANEGO konta",
            _prof10.imie == "Jan Kowalski", repr(_prof10.imie))

    try:
        _okno10.close()
    except Exception:
        pass
except Exception as _e10:
    sprawdz("nowy wygląd jest jedynym interfejsem programu", False, repr(_e10))
finally:
    try:
        if _s10_status_byl is None:
            if os.path.exists(P.PLIK_STATUSU):
                os.remove(P.PLIK_STATUSU)
        else:
            open(P.PLIK_STATUSU, "w", encoding="utf-8").write(_s10_status_byl)
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════
sekcja("11. Okno bez ramy i bez intra, bez limitu dnia, z dniami bez pracy")

try:
    from PyQt6.QtWidgets import QApplication as _QA11, QWidget as _QW11
    from PyQt6.QtCore import Qt as _Qt11, QEvent as _QE11, QPointF as _QP11
    from PyQt6.QtGui import QKeyEvent as _QKE11, QMouseEvent as _QME11
    import nowy_wyglad as _NW11
    import proto_okno as _OK11
    _app11 = _QA11.instance() or _QA11(sys.argv)
    _app11.setStyleSheet(_NW11.arkusz())

    _prof11 = _NW11.ProfilWidoku("Jan Testowy", "85010112345",
                                 "ul. Kwiatowa 5, 26-600 Radom", "KR")
    _okno11 = _NW11.OknoNowegoWygladu(profil=_prof11, rok=2026, miesiac=10)
    _okno11._pole_pesel.setText("85010112345")
    _okno11.show()
    _app11.processEvents()

    # ── 1. INTRO NIE STARTUJE ─────────────────────────────────────
    sprawdz("intro startowe jest w tej wersji wyłączone przełącznikiem",
            P.INTRO_NA_STARCIE is False, repr(P.INTRO_NA_STARCIE))
    _okno11.intro_po_sprawdzeniu("Jan Testowy")
    _app11.processEvents()
    _zywe11 = [c for c in _okno11.findChildren(_QW11)
               if type(c).__name__ in ("IntroZywaMapa", "AnimacjaStartowa")]
    sprawdz("po starcie nie ma ani żywej mapy, ani klasycznej animacji",
            not _zywe11 and _okno11._intro is None
            and _okno11._intro_gra is False, str([type(c).__name__ for c in _zywe11]))
    sprawdz("nic nie czeka na koniec intra: ekran główny jest od razu odsłonięty",
            _okno11._intro_zakonczone is True)
    _stare11 = _okno11.stare_okno()
    _okno11._zepnij_ze_starym(_stare11)
    sprawdz("okno aktualizacji nie wisi na sygnale końca intra",
            _stare11._intro_gra is False and _stare11._intro_zakonczone is True)
    _stare11._akt_czekanie = 0
    _stare11._intro_gra = True          # nawet z zapomnianą flagą
    _stare11._dialog_akt_byl = True     # (dalej i tak nie budujemy dialogu)
    _stare11._pokaz_okno_aktualizacji()
    sprawdz("okno aktualizacji rusza od razu, choćby flaga intra została zapalona",
            getattr(_stare11, "_akt_czekanie", 0) == 0)
    _stare11._intro_gra = False
    sprawdz("kod intra zostaje w programie — wróci przy generowaniu dokumentów",
            callable(getattr(_okno11, "pokaz_intro", None))
            and callable(getattr(P, "pokaz_intro", None) or P.App.pokaz_intro)
            and os.path.exists(os.path.join(KATALOG, "intro_zywa_mapa.py")))

    # ── 2. OKNO BEZ RAMY SYSTEMU, NA PEŁNYM EKRANIE ───────────────
    sprawdz("okno programu nie ma ramy systemowej",
            bool(_okno11.windowFlags() & _Qt11.WindowType.FramelessWindowHint))
    sprawdz("okno programu wstaje na pełnym ekranie", _okno11.isFullScreen())
    sprawdz("pasek górny ma własne sterowanie oknem po prawej stronie",
            all(n in _okno11.pasek._pola_prawe
                for n in ("zamknij", "minimalizuj", "pelny_ekran")),
            str(list(_okno11.pasek._pola_prawe)))
    sprawdz("sterowanie oknem melduje kliknięcia osobnymi sygnałami",
            all(hasattr(_okno11.pasek, s11) for s11 in
                ("klik_zamkniecia", "klik_minimalizacji", "klik_pelnego_ekranu")))

    def _klik_paska(nazwa, punkt=None):
        pole = _okno11.pasek._pola_prawe.get(nazwa)
        pkt = punkt if punkt is not None else pole.center()
        glob = _okno11.pasek.mapToGlobal(pkt.toPoint()).toPointF()
        _okno11.pasek.mousePressEvent(
            _QME11(_QE11.Type.MouseButtonPress, pkt, glob,
                   _Qt11.MouseButton.LeftButton, _Qt11.MouseButton.LeftButton,
                   _Qt11.KeyboardModifier.NoModifier))
        _app11.processEvents()

    _klik_paska("pelny_ekran")
    _po_kliku11 = _okno11.isFullScreen()
    _klik_paska("pelny_ekran")
    sprawdz("przycisk w pasku wychodzi z pełnego ekranu i wraca na niego",
            _po_kliku11 is False and _okno11.isFullScreen() is True)

    _okno11.keyPressEvent(_QKE11(_QE11.Type.KeyPress, _Qt11.Key.Key_F11,
                                 _Qt11.KeyboardModifier.NoModifier))
    _app11.processEvents()
    _po_f11 = _okno11.isFullScreen()
    _okno11.keyPressEvent(_QKE11(_QE11.Type.KeyPress, _Qt11.Key.Key_F11,
                                 _Qt11.KeyboardModifier.NoModifier))
    _app11.processEvents()
    _okno11.keyPressEvent(_QKE11(_QE11.Type.KeyPress, _Qt11.Key.Key_Escape,
                                 _Qt11.KeyboardModifier.NoModifier))
    _app11.processEvents()
    sprawdz("F11 i Esc wychodzą z pełnego ekranu",
            _po_f11 is False and _okno11.isFullScreen() is False)

    # przeciąganie okna za pusty kawałek paska (tylko poza pełnym ekranem)
    _okno11.resize(1200, 700)
    _okno11.move(120, 120)
    _app11.processEvents()
    _skad11 = _okno11.frameGeometry().topLeft()
    _lewo11 = _okno11.pasek._pola_zakladek()[-1].right() + 12
    _prawo11 = min(r.x() for r in _okno11.pasek._pola_prawe.values()) - 12
    _pusty11 = _QP11((_lewo11 + _prawo11) / 2.0, 18.0)
    sprawdz("w pasku został pusty kawałek do chwytania okna",
            _prawo11 > _lewo11 and not _okno11.pasek.pole_prawe(_pusty11),
            str((_lewo11, _prawo11)))
    _glob11 = _okno11.pasek.mapToGlobal(_pusty11.toPoint()).toPointF()
    _okno11.pasek.mousePressEvent(
        _QME11(_QE11.Type.MouseButtonPress, _pusty11, _glob11,
               _Qt11.MouseButton.LeftButton, _Qt11.MouseButton.LeftButton,
               _Qt11.KeyboardModifier.NoModifier))
    _okno11.pasek.mouseMoveEvent(
        _QME11(_QE11.Type.MouseMove, _pusty11,
               _QP11(_glob11.x() + 60, _glob11.y() + 40),
               _Qt11.MouseButton.NoButton, _Qt11.MouseButton.LeftButton,
               _Qt11.KeyboardModifier.NoModifier))
    _app11.processEvents()
    _dokad11 = _okno11.frameGeometry().topLeft()
    _okno11.pasek.mouseReleaseEvent(
        _QME11(_QE11.Type.MouseButtonRelease, _pusty11, _glob11,
               _Qt11.MouseButton.LeftButton, _Qt11.MouseButton.NoButton,
               _Qt11.KeyboardModifier.NoModifier))
    sprawdz("okno bez ramy przesuwa się za pasek górny",
            (_dokad11.x() - _skad11.x(), _dokad11.y() - _skad11.y()) == (60, 40),
            str((_skad11, _dokad11)))

    sprawdz("panel działu nadal daje się zamknąć krzyżykiem i Esc",
            callable(getattr(_okno11.nakladka(), "zamknij", None))
            and _okno11.nakladka().b_zamknij is not None)

    # ── 3. LIMIT DNIA ZNIKA Z INTERFEJSU ──────────────────────────
    _kp11 = _okno11.k_parametry
    sprawdz("karta parametrów nie ma już przełącznika limitu dnia",
            not hasattr(_kp11, "limit") and not hasattr(_OK11, "WierszLimitu"))
    _zrodlo11 = open(os.path.join(KATALOG, "prototyp", "proto_okno.py"),
                     encoding="utf-8").read()
    sprawdz("w interfejsie nie ma napisu o limicie dnia",
            '"limit dnia"' not in _zrodlo11 and "'limit dnia'" not in _zrodlo11)
    _pola11 = [_kp11.kwota, _kp11.pojemnosc, _kp11.tryb, _kp11.wolne]
    sprawdz("karta parametrów domyka się bez dziury po usuniętym wierszu",
            _kp11.layout().count() == 4          # kwota, wiersz, dni bez pracy, rozciągnięcie
            and _kp11.wolne.geometry().bottom() + 26 >= _kp11.layout().sizeHint().height(),
            str((_kp11.layout().count(), _kp11.wolne.geometry(),
                 _kp11.layout().sizeHint().height())))
    sprawdz("reguła limitu dnia zostaje w silniku, tylko bez pokazywania jej",
            abs(_okno11._limit_dnia - _OK11.LIMITY_DNIA[0]) < 0.005
            and abs(_NW11.maks_kwota_miesiaca(2026, 10, "Tydzień", (), 200.0, 1.15)
                    - _NW11.maks_kwota_miesiaca(2026, 10, "Tydzień", (), 999.0, 1.15)) > 1.0)

    # ── 4. DNI BEZ PRACY DZIAŁAJĄ ─────────────────────────────────
    sprawdz("wiersz „Dni bez pracy” melduje kliknięcie i otwiera wybór dni",
            hasattr(_kp11.wolne, "kliknieto")
            and callable(getattr(_okno11, "_wybierz_dni_bez_pracy", None)))
    _okno11._ustaw_dni_bez_pracy({5, 6, 7, 12, 13})
    _app11.processEvents()
    _wylaczone11 = {d.data.day for d in _okno11.dni if getattr(d, "wylaczony", False)}
    _z_trasa11 = {d.data.day for d in _okno11._dni_w_trasie()}
    sprawdz("wskazane dni bez pracy wypadają z rozliczenia: są wyłączone i bez tras",
            _wylaczone11 == {5, 6, 7, 12, 13} and not (_z_trasa11 & {5, 6, 7, 12, 13}),
            str((sorted(_wylaczone11), sorted(_z_trasa11))))
    sprawdz("wybrane dni widać w wierszu karty parametrów",
            _kp11.wolne.dni() == [5, 6, 7, 12, 13], str(_kp11.wolne.dni()))
    _dane11, _powod11 = _okno11._dane_do_generacji()
    sprawdz("silnik nie dostaje dni bez pracy do rozliczenia",
            _dane11 is not None
            and not ({d.day for d in _dane11["dni_robocze"]} & {5, 6, 7, 12, 13}),
            _powod11 or "")
    sprawdz("dni bez pracy zapisują się na dysk od razu po wyborze",
            P.ustawienie(_NW11.OknoNowegoWygladu.USTAWIENIE_WOLNYCH, {}).get("2026-10")
            == [5, 6, 7, 12, 13])
    # licznik w nagłówku taśmy liczy dni DO WYKORZYSTANIA — dzień wyłączony
    # przez użytkownika nie jest już dniem, w którym można jechać
    _kafle11 = list(_okno11.tasma._dni)
    _wszystkie11 = _okno11.tasma._zbior["dni_wszystkie"]
    _do_uzycia11 = len([d for d in _kafle11 if not getattr(d, "wylaczony", False)])
    # kwota z groszami ma być widoczna w nagłówku taśmy — inaczej po wpisaniu
    # 1 850,55 zł użytkownik widziałby 1 851 zł i pomyślałby, że program zmienił
    # mu kwotę
    _kp11.kwota.ustaw_tekst("1 850,55")
    _okno11._przelicz_teraz()
    _app11.processEvents()
    _suma11 = round(sum(d.kwota for d in _okno11._dni_w_trasie()), 2)
    sprawdz("kwota z groszami dochodzi do taśmy co do grosza",
            abs(_suma11 - 1850.55) < 0.005 and _okno11.tasma.kwota_z_groszami(),
            str(_suma11))
    _kp11.kwota.ustaw_tekst("1 850")
    _okno11._przelicz_teraz()
    _app11.processEvents()
    sprawdz("kwota bez groszy nie dokleja „,00” w nagłówku taśmy",
            not _okno11.tasma.kwota_z_groszami(),
            str(round(sum(d.kwota for d in _okno11._dni_w_trasie()), 2)))

    sprawdz("nagłówek taśmy „z N dni” nie liczy dni bez pracy",
            _wszystkie11 == _do_uzycia11 and _wszystkie11 == len(_kafle11) - 5,
            str((_wszystkie11, _do_uzycia11, len(_kafle11))))

    # taśma ↔ wiersz: w obie strony
    for _d11 in _okno11.dni:
        if _d11.data.day == 20:
            _d11.wylaczony = True
    _okno11._przelacz_wolny(20)
    _app11.processEvents()
    _po_prawym11 = _kp11.wolne.dni()
    for _d11 in _okno11.dni:
        if _d11.data.day == 20:
            _d11.wylaczony = False
    _okno11._przelacz_wolny(20)
    _app11.processEvents()
    sprawdz("prawy przycisk na taśmie i wiersz karty pokazują tę samą listę",
            _po_prawym11 == [5, 6, 7, 12, 13, 20]
            and _kp11.wolne.dni() == [5, 6, 7, 12, 13],
            str((_po_prawym11, _kp11.wolne.dni())))
    _okno11._ustaw_dni_bez_pracy({8})
    _app11.processEvents()
    sprawdz("wybór z kalendarza wyłącza dzień także na taśmie",
            {d.data.day for d in _okno11.dni if getattr(d, "wylaczony", False)} == {8}
            and _kp11.wolne.dni() == [8])

    # panel wyboru dni — kalendarz miesiąca w stylu nowego systemu
    _panel11 = _OK11.PanelDniBezPracy(2026, 10, {8}, _okno11)
    _panel11.setStyleSheet(_OK11.arkusz())
    _panel11.resize(470, max(420, _panel11.sizeHint().height()))
    _app11.processEvents()
    _siatka11 = _panel11.siatka
    sprawdz("wybór dni pokazuje cały miesiąc z zaznaczonymi dniami",
            len(_siatka11._siatka()) == P.calendar.monthrange(2026, 10)[1]
            and _siatka11.wybrane == {8}
            and _panel11.l_podtytul.text() == "październik 2026",
            str((len(_siatka11._siatka()), _siatka11.wybrane,
                 _panel11.l_podtytul.text())))
    _pole11 = _siatka11._siatka()[15]
    _siatka11.mousePressEvent(
        _QME11(_QE11.Type.MouseButtonPress, _pole11.center(),
               _siatka11.mapToGlobal(_pole11.center().toPoint()).toPointF(),
               _Qt11.MouseButton.LeftButton, _Qt11.MouseButton.LeftButton,
               _Qt11.KeyboardModifier.NoModifier))
    _app11.processEvents()
    sprawdz("klik w dzień kalendarza dopisuje go do dni bez pracy",
            _panel11.dni() == {8, 15} and _panel11.l_licznik.text() == "2",
            str((_panel11.dni(), _panel11.l_licznik.text())))
    _panel11.b_wyczysc.click()
    _app11.processEvents()
    sprawdz("„Wyczyść” zdejmuje wszystkie dni bez pracy",
            _panel11.dni() == set() and _panel11.l_licznik.text() == "0")
    _panel11.close()
    _okno11._ustaw_dni_bez_pracy(set())
    _okno11.close()
except Exception as _e11:
    sprawdz("okno bez ramy, bez intra, bez limitu dnia i z dniami bez pracy",
            False, repr(_e11))

# ══════════════════════════════════════════════════════════════════
sekcja("12. Mapa na prawdziwych współrzędnych i podziałka, która mierzy prawdę")

try:
    from PyQt6.QtWidgets import QApplication as _QA12
    from PyQt6.QtGui import QPixmap as _QPix12, QPainter as _QPaint12
    import nowy_wyglad as _NW12
    import proto_mapa as _PM12
    import proto_dane as _PD12
    _app12 = _QA12.instance() or _QA12(sys.argv)
    _app12.setStyleSheet(_NW12.arkusz())

    # ── 1. RANGA I WSPÓŁRZĘDNE Z DANYCH PROGRAMU ──────────────────
    _rangi12 = _NW12.rangi_miast_programu()
    sprawdz("rangi miejscowości biorą się z bazy miast silnika, a nie z nazwy",
            len(_rangi12) > 500
            and set(_rangi12.values()) <= {_NW12.RANGA_WIES, _NW12.RANGA_MIASTO},
            str((len(_rangi12), sorted(set(_rangi12.values())))))

    _geo12 = {"Radom": (51.40, 21.15), "Warszawa": (52.23, 21.01),
              "Zakrzew": (51.44, 20.98)}
    _dla12 = _NW12.miasta_dla_mapy(_geo12, "Radom")
    sprawdz("miasta dla mapy niosą szerokość, długość i rangę",
            set(_dla12) == set(_geo12)
            and _dla12["Radom"][:2] == (51.40, 21.15)
            and _dla12["Radom"][2] == _NW12.RANGA_BAZA
            and _dla12["Warszawa"][2] == _NW12.RANGA_MIASTO
            and _dla12["Zakrzew"][2] == _NW12.RANGA_WIES,
            str(_dla12))

    for _opis12, _wej12 in (("napis zamiast pary liczb", {"A": "51.4, 21.1"}),
                            ("za krótka krotka", {"A": (51.4,)}),
                            ("zera po nieudanym geokodowaniu",
                             {"A": (52.2, 21.0), "B": (0.0, 0.0)}),
                            ("współrzędne spoza globu",
                             {"A": (52.2, 21.0), "B": (999.0, 21.0)}),
                            ("pusty słownik", {}), ("brak danych", None)):
        sprawdz("bez pewnych współrzędnych mapa zostaje przy swoim układzie: %s"
                % _opis12, _NW12.miasta_dla_mapy(_wej12, "A") == {},
                str(_NW12.miasta_dla_mapy(_wej12, "A")))

    # ── 2. OKNO PODAJE MAPIE PRAWDZIWY REJON ──────────────────────
    _prof12 = _NW12.ProfilWidoku("Jan Testowy", "85010112345",
                                 "ul. Kwiatowa 5, 26-600 Radom", "KR")
    _okno12 = _NW12.OknoNowegoWygladu(profil=_prof12, rok=2026, miesiac=10)
    _okno12.showNormal()
    _okno12.resize(1440, 900)
    for _ in range(6):
        _app12.processEvents()
    _okno12.ustaw_animacje(False)
    for _ in range(6):
        _app12.processEvents()
    _mapa12 = _okno12.mapa

    sprawdz("mapa dostaje te miejscowości, które zna silnik",
            set(_mapa12._miasta) == set(_okno12.geo)
            and _mapa12._baza == _okno12.baza_miasto
            and len(_mapa12._miasta) > 5,
            str((len(_mapa12._miasta), len(_okno12.geo), _mapa12._baza)))
    sprawdz("baza pracownika jest na mapie bazą",
            _mapa12._rangi.get(_okno12.baza_miasto) == _NW12.RANGA_BAZA,
            str(_mapa12._rangi.get(_okno12.baza_miasto)))

    # ── 3. ODLEGŁOŚCI NA MAPIE TO ODLEGŁOŚCI Z SILNIKA ────────────
    _pary12 = []
    _nazwy12 = sorted(_okno12.geo)
    for _i12 in range(len(_nazwy12)):
        for _j12 in range(_i12 + 1, len(_nazwy12)):
            _a12, _b12 = _nazwy12[_i12], _nazwy12[_j12]
            _la, _ga = _okno12.geo[_a12]
            _lb, _gb = _okno12.geo[_b12]
            _prawda12 = P.oblicz_dystans(_la, _ga, _lb, _gb)
            _ax, _ay = _mapa12._miasta[_a12]
            _bx, _by = _mapa12._miasta[_b12]
            _swiat12 = math.hypot(_bx - _ax, _by - _ay) / _mapa12._jedn_na_km
            _pary12.append((abs(_swiat12 - _prawda12), _a12, _b12,
                            _prawda12, _swiat12))
    _najgorsza12 = max(_pary12)
    sprawdz("odległości w świecie mapy zgadzają się z kilometrami silnika",
            len(_pary12) > 100 and _najgorsza12[0] < 4.0,
            "%s–%s: %.1f km na mapie wobec %.1f km naprawdę"
            % (_najgorsza12[1], _najgorsza12[2], _najgorsza12[4],
               _najgorsza12[3]))

    _blat12, _blng12 = _okno12.geo[_okno12.baza_miasto]
    _pb12 = _mapa12._punkt(_okno12.baza_miasto)
    _rzut12 = _mapa12.rzut()
    _ox12, _oy12, _sx12, _sy12 = _mapa12._obszar_swiata()
    _cx12, _cy12 = _ox12 + _sx12 * 0.5, _oy12 + _sy12 * 0.5
    _poziom12 = (_rzut12.k / max(1.0, _rzut12.glebokosc(_cx12, _cy12, 0.0))
                 * _mapa12._jedn_na_km)
    _pol12 = 50.0 * _mapa12._jedn_na_km * 0.5
    _wglab12 = abs(_rzut12.ekran(_cx12, _cy12 + _pol12, 0.0).y()
                   - _rzut12.ekran(_cx12, _cy12 - _pol12, 0.0).y()) / 50.0
    _krzywe12 = []
    for _n12 in _nazwy12:
        if _n12 == _okno12.baza_miasto:
            continue
        _lat12, _lng12 = _okno12.geo[_n12]
        _az12 = (math.degrees(math.atan2(
            (_lng12 - _blng12) * math.cos(math.radians(_blat12)),
            _lat12 - _blat12)) + 360) % 360
        _p12 = _mapa12._punkt(_n12)
        _aze12 = (math.degrees(math.atan2(
            _p12.x() - _pb12.x(),
            (_pb12.y() - _p12.y()) * _poziom12 / _wglab12)) + 360) % 360
        if abs((_az12 - _aze12 + 180) % 360 - 180) > 6.0:
            _krzywe12.append(_n12)
    sprawdz("miejscowości leżą na mapie w tym kierunku, co naprawdę",
            not _krzywe12, str(_krzywe12))

    # ── 4. PODZIAŁKA MA DWA RAMIONA I OBA MÓWIĄ PRAWDĘ ────────────
    _linie12 = []

    class _Szpieg12(_QPaint12):
        def drawLine(self, *a):
            if len(a) == 2:
                _linie12.append((a[0].x(), a[0].y(), a[1].x(), a[1].y()))
            return _QPaint12.drawLine(self, *a)

    _napisy12 = []
    _oryg12 = _PM12._napis

    def _podsluch12(p, x, y, napis, *a, **k):
        _wynik12 = _oryg12(p, x, y, napis, *a, **k)
        _napisy12.append(napis)
        return _wynik12

    _PM12._napis = _podsluch12
    _pix12 = _QPix12(_mapa12.width(), _mapa12.height())
    _mal12 = _Szpieg12(_pix12)
    _mapa12._rysuj_podzialke(_mal12, _mapa12.rzut(),
                             __import__("PyQt6.QtCore", fromlist=["QRectF"])
                             .QRectF(_mapa12.rect()))
    _mal12.end()
    _PM12._napis = _oryg12

    _dlugie12 = [l for l in _linie12
                 if abs(l[2] - l[0]) > 25 or abs(l[3] - l[1]) > 25]
    _poziome12 = [l for l in _dlugie12 if abs(l[3] - l[1]) < 0.5]
    _pionowe12 = [l for l in _dlugie12 if abs(l[2] - l[0]) < 0.5]
    _km12 = [n for n in _napisy12 if n.endswith(" km")]
    sprawdz("podziałka ma ramię w poprzek kadru i ramię w głąb",
            len(_poziome12) == 1 and len(_pionowe12) == 1 and len(_km12) == 2
            and _km12[0] == _km12[1], str((len(_poziome12), len(_pionowe12),
                                           _km12)))
    _krok12 = int(_km12[0].split()[0])
    _mierzy_poziom12 = abs(_poziome12[0][2] - _poziome12[0][0]) / _krok12
    _mierzy_pion12 = abs(_pionowe12[0][3] - _pionowe12[0][1]) / _krok12
    sprawdz("ramię w poprzek kadru mierzy tyle, ile kamera pokazuje w tę stronę",
            abs(_mierzy_poziom12 - _poziom12) < _poziom12 * 0.02,
            "%.4f wobec %.4f px/km" % (_mierzy_poziom12, _poziom12))
    sprawdz("ramię w głąb mierzy tyle, ile kamera pokazuje w głąb",
            abs(_mierzy_pion12 - _wglab12) < _wglab12 * 0.02,
            "%.4f wobec %.4f px/km" % (_mierzy_pion12, _wglab12))
    sprawdz("ramię w głąb jest krótsze — teren jest pochylony do widza",
            _mierzy_pion12 < _mierzy_poziom12 * 0.95,
            "%.4f / %.4f" % (_mierzy_pion12, _mierzy_poziom12))

    _zmierzone12 = []
    for _roznica12, _a12, _b12, _prawda12, _swiat12 in _pary12:
        if _prawda12 < 20.0:
            continue
        _pa12 = _mapa12._punkt(_a12)
        _pb2_12 = _mapa12._punkt(_b12)
        _odczyt12 = math.hypot((_pb2_12.x() - _pa12.x()) / _mierzy_poziom12,
                               (_pb2_12.y() - _pa12.y()) / _mierzy_pion12)
        _zmierzone12.append((abs(_odczyt12 - _prawda12) / _prawda12 * 100.0,
                             _a12, _b12, _prawda12, _odczyt12))
    _zmierzone12.sort()
    _srodek12 = _zmierzone12[len(_zmierzone12) // 2]
    sprawdz("typowa para miast zmierzona podziałką trafia w prawdę z zapasem",
            _srodek12[0] < 10.0,
            "mediana %.1f%% (%s–%s: %.1f km wobec %.1f km)"
            % (_srodek12[0], _srodek12[1], _srodek12[2], _srodek12[4],
               _srodek12[3]))
    sprawdz("dziewięć par na dziesięć mieści się w dziesięciu procentach",
            _zmierzone12[int(len(_zmierzone12) * 0.9)][0] < 10.0,
            "90. centyl %.1f%%" % _zmierzone12[int(len(_zmierzone12) * 0.9)][0])

    # ── 5. TEN SAM DZIEŃ, TEN SAM OBRAZ; INNY DZIEŃ, INNY ─────────
    _dni12 = [d for d in _okno12.dni if not d.wolny and len(d.trasa) >= 3]
    if len(_dni12) >= 2:
        _mapa12.ustaw_dzien(_dni12[0])
        _ziarno_a12 = _mapa12._ziarno
        _uklad_a12 = [(e["napis"], round(e["pole"].x(), 2),
                       round(e["pole"].y(), 2))
                      for e in _mapa12._geometria()["etykiety"]]
        _mapa12.ustaw_dzien(_dni12[1])
        _ziarno_b12 = _mapa12._ziarno
        _mapa12.ustaw_dzien(_dni12[0])
        _mapa12._geo = None
        _mapa12._geo_klucz = None
        _uklad_c12 = [(e["napis"], round(e["pole"].x(), 2),
                       round(e["pole"].y(), 2))
                      for e in _mapa12._geometria()["etykiety"]]
        sprawdz("inny dzień to inny krajobraz, ten sam dzień to ten sam",
                _ziarno_a12 != _ziarno_b12
                and _mapa12._ziarno == _ziarno_a12,
                str((_ziarno_a12, _ziarno_b12, _mapa12._ziarno)))
        sprawdz("podpisy miast nie skaczą: ta sama trasa, ten sam układ tabliczek",
                _uklad_a12 == _uklad_c12 and len(_uklad_a12) > 1,
                str(len(_uklad_a12)))

    # ── 6. PRZYSTANEK, KTÓREGO MAPA NIE ZNA, NIE WYWRACA RYSUNKU ──
    _dzien12 = _dni12[0] if _dni12 else None
    if _dzien12 is not None:
        import copy as _copy12
        _widmo12 = _copy12.deepcopy(_dzien12)
        _widmo12.przystanki = list(_widmo12.przystanki) + ["Miasto-Widmo"]
        _mapa12.ustaw_dzien(_widmo12)
        _mapa12.ustaw_animacje(False)
        _mapa12.grab()
        sprawdz("nieznany przystanek nie wywraca rysowania mapy",
                "Miasto-Widmo" not in _mapa12._miasta)
        _mapa12.ustaw_dzien(_dzien12)

    _okno12.close()
except Exception as _e12:
    sprawdz("mapa na prawdziwych współrzędnych z uczciwą podziałką",
            False, repr(_e12))

# ══════════════════════════════════════════════════════════════════
sekcja("13. Kadr należy do trasy dnia, miejscowości widać, tabliczki się rozchodzą")

try:
    import subprocess as _sub13
    from PyQt6.QtWidgets import QApplication as _QA13
    from PyQt6.QtGui import QPixmap as _QPix13, QPainter as _QPaint13
    from PyQt6.QtCore import QPointF as _QP13, QRectF as _QR13
    import nowy_wyglad as _NW13          # dokłada katalog prototypu do ścieżki
    import proto_mapa as _PM13
    _app13 = _QA13.instance() or _QA13(sys.argv)

    # ── UKŁAD DO BADANIA: baza, przystanki i kilkadziesiąt wsi wokół ──
    _BAZA13 = "Radom"
    _BLISKO13 = {"Radom": (51.4025, 21.1471), "Jedlińsk": (51.5352, 21.0842),
                 "Skaryszew": (51.3131, 21.2500), "Kozłów": (51.4650, 21.3300),
                 "Gózd": (51.4092, 21.3200), "Głowaczów": (51.5560, 21.2900),
                 "Stromiec": (51.6167, 21.1500), "Kazanów": (51.2650, 21.4200)}
    _DALEKO13 = {"Warszawa": (52.2297, 21.0122), "Lublin": (51.2465, 22.5684),
                 "Kielce": (50.8661, 20.6286), "Łódź": (51.7592, 19.4560),
                 "Puławy": (51.4167, 21.9690), "Piotrków Tryb.": (51.4050, 19.6930),
                 "Starachowice": (51.0500, 21.0700)}


    def _spis_miast13():
        """Spis miast, jaki dostaje mapa od programu: przystanki i kilkadziesiąt wsi.

        Wsie stoją w kratce co trzydzieści kilometrów, z dala od siebie —
        dzięki temu badanie wielkości znaku nie trafia na parę sąsiadek, którym
        znak celowo przycina granica sąsiedztwa.
        """
        miasta = {}
        for _n, (_la, _lg) in _BLISKO13.items():
            miasta[_n] = (_la, _lg,
                          _PM13.RANGA_BAZA if _n == _BAZA13 else _PM13.RANGA_MIASTO)
        for _n, (_la, _lg) in _DALEKO13.items():
            miasta[_n] = (_la, _lg, _PM13.RANGA_MIASTO)
        _lat0, _lng0 = _BLISKO13[_BAZA13]
        _nr = 0
        for _i in range(-6, 7):
            for _j in range(-6, 7):
                _kmx = (_i + (0.5 if _j % 2 else 0.0)) * 30.0
                _kmy = _j * 30.0
                if math.hypot(_kmx, _kmy) > 150.0:
                    continue
                _la = _lat0 + _kmy / 110.57
                _lg = _lng0 + _kmx / (111.32 * math.cos(math.radians(_lat0)))
                if any(abs(_la - _a) * 110.57 < 26.0
                       and abs(_lg - _b) * 69.5 < 26.0
                       for (_a, _b) in list(_BLISKO13.values())
                       + list(_DALEKO13.values())):
                    continue
                _nr += 1
                miasta["Wólka %02d" % _nr] = (_la, _lg, _PM13.RANGA_WIES)
        return miasta

    _MIASTA13 = _spis_miast13()


    class _Dzien13:
        """Dzień w takiej postaci, w jakiej mapa go czyta: data, przystanki, trasa."""

        def __init__(self, dzien, przystanki, wolny=False):
            self.data = datetime.date(2026, 10, dzien)
            self.przystanki = list(przystanki)
            self.wolny = wolny
            self.wylaczony = False

        @property
        def trasa(self):
            return [_BAZA13] + list(self.przystanki) + [_BAZA13]

    _CIASNY13 = _Dzien13(1, [n for n in _BLISKO13 if n != _BAZA13])
    _SZEROKI13 = _Dzien13(8, list(_DALEKO13))
    _WOLNY13 = _Dzien13(11, [], wolny=True)
    _KOTWICA13 = (588.0, 68.0)          # kartka delegacji tak, jak stawia ją okno


    def _mapa13(dzien, szer=1200, wys=760, kotwica=None, miasta=None, rysuj=False):
        m = _PM13.MapaDnia()
        m.ustaw_animacje(False)
        m.ustaw_miasta(miasta or _MIASTA13, baza=_BAZA13)
        m.resize(szer, wys)
        m.ustaw_dzien(dzien)
        m.ustaw_kotwice_kartki(_QP13(*kotwica) if kotwica else None)
        m.ustaw_animacje(False)
        if rysuj:
            m.grab()                     # cała droga rysowania, jak przy zrzucie
        return m


    def _trasa_na_ekranie13(m):
        """Prostokąt, jaki zajmują na ekranie najdalsze punkty trasy dnia."""
        pkt = [m._punkt(n) for n in dict.fromkeys(m._dzien.trasa) if n in m._miasta]
        return (max(p.x() for p in pkt) - min(p.x() for p in pkt),
                max(p.y() for p in pkt) - min(p.y() for p in pkt),
                (max(p.x() for p in pkt) + min(p.x() for p in pkt)) * 0.5)


    def _zasieg_znaku13(m, nazwa, znaki):
        """Najdalszy punkt narysowanego znaku od środka osady, w kilometrach."""
        mm = [x for x in m._miejscowosci if x["nazwa"] == nazwa][0]
        wsp = znaki.get(nazwa, 1.0)
        return max(math.hypot(x - mm["x"], y - mm["y"])
                   for (x, y) in mm["obrys"]) * wsp / m._jedn_na_km


    def _srednica_znaku13(m, nazwa, znaki, odn):
        """Szerokość znaku miejscowości w pikselach, mierzona w środku kadru."""
        mm = [x for x in m._miejscowosci if x["nazwa"] == nazwa][0]
        return 2.0 * mm["promien"] * znaki.get(nazwa, 1.0) * odn


    def _odniesienie13(m):
        """Ile pikseli ma jednostka świata w środku kadru."""
        _ox, _oy, _sx, _sy = m._obszar_swiata()
        r = m.rzut()
        return r.k / max(1.0, r.glebokosc(_ox + _sx * 0.5, _oy + _sy * 0.5, 0.0))


    def _ramie_podzialki13(m):
        """Długość poziomego ramienia podziałki i jej podpis — prosto z rysowania."""
        _linie13 = []

        class _Szpieg13(_QPaint13):
            def drawLine(self, *a):
                if len(a) == 2:
                    _linie13.append((a[0].x(), a[0].y(), a[1].x(), a[1].y()))
                return _QPaint13.drawLine(self, *a)

        _napisy13 = []
        _oryg13 = _PM13._napis

        def _podsluch13(p, x, y, napis, *a, **k):
            _napisy13.append(napis)
            return _oryg13(p, x, y, napis, *a, **k)

        _PM13._napis = _podsluch13
        _pix13 = _QPix13(m.width(), m.height())     # w osobnej zmiennej: malujemy po nim
        _mal13 = _Szpieg13(_pix13)
        m._rysuj_podzialke(_mal13, m.rzut(), _QR13(m.rect()))
        _mal13.end()
        _PM13._napis = _oryg13
        _poziome13 = [l for l in _linie13
                      if abs(l[2] - l[0]) > 25 and abs(l[3] - l[1]) < 0.5]
        _km13 = [n for n in _napisy13 if n.endswith(" km")]
        return (round(_poziome13[0][2] - _poziome13[0][0], 4) if _poziome13 else None,
                _km13[0] if _km13 else None)

    # ── 1. KADR IDZIE ZA TRASĄ, A NIE ZA SPISEM MIAST ─────────────
    _sam13 = _mapa13(_CIASNY13, miasta={n: _MIASTA13[n] for n in _BLISKO13})
    _pelny13 = _mapa13(_CIASNY13)

    def _kadr_km13(m):
        """Kadr w kilometrach: rozmiar i położenie środka względem bazy.

        Liczony względem bazy, bo początek układu świata siedzi w środku
        SPISU miast — a właśnie o to chodzi, żeby kadr od spisu nie zależał.
        """
        _ox, _oy, _sx, _sy = m._obszar_swiata()
        _bx, _by = m._miasta[_BAZA13]
        return tuple(round(v / m._jedn_na_km, 2)
                     for v in (_sx, _sy, _ox + _sx * 0.5 - _bx, _oy + _sy * 0.5 - _by))

    _kadr_sam13 = _kadr_km13(_sam13)
    _kadr_pelny13 = _kadr_km13(_pelny13)
    sprawdz("kadr obejmuje trasę dnia, a nie kilkaset miejscowości wokół bazy",
            len(_pelny13._miasta) > len(_sam13._miasta) + 40
            and max(abs(a - b) for a, b in zip(_kadr_sam13, _kadr_pelny13)) < 0.5,
            "%s wobec %s (km)" % (_kadr_sam13, _kadr_pelny13))

    _region13 = _mapa13(_SZEROKI13)
    _widzet13 = _QR13(0.0, 0.0, float(_region13.width()), float(_region13.height()))
    _w_kadrze13 = [n for n in _region13._miasta
                   if _widzet13.contains(_region13._punkt(n))]
    _obce13 = [n for n in _w_kadrze13 if n not in _SZEROKI13.trasa]
    sprawdz("miejscowości spoza trasy dalej stoją w kadrze — krajobraz jest zamieszkany",
            len(_obce13) > 20, "%d miejscowości spoza trasy w kadrze" % len(_obce13))

    _kadry13 = []
    for _opis13, _dz13, _sz13, _wy13, _kot13 in (
            ("dzień ciasny 1200×760", _CIASNY13, 1200, 760, None),
            ("dzień rozrzucony 1200×760", _SZEROKI13, 1200, 760, None),
            ("dzień ciasny w oknie z kartką", _CIASNY13, 940, 640, _KOTWICA13),
            ("dzień rozrzucony w oknie z kartką", _SZEROKI13, 940, 640, _KOTWICA13),
            ("dzień ciasny 520×380", _CIASNY13, 520, 380, None),
            ("dzień rozrzucony 520×380", _SZEROKI13, 520, 380, None)):
        _m13 = _mapa13(_dz13, _sz13, _wy13, _kot13, rysuj=True)
        _dx13, _dy13, _srx13 = _trasa_na_ekranie13(_m13)
        # kartka delegacji leży NA mapie, więc trasa ma wypełnić to, co po niej
        # zostaje — mierzymy udział w kadrze dostępnym, nie w zasłoniętym
        _dost13 = _sz13 if _kot13 is None else _kot13[0]
        _kadry13.append((_opis13, _m13, _dx13, _dy13, _srx13,
                         max(_dx13 / _dost13, _dy13 / _wy13)))
    _najciasniej13 = min(_kadry13, key=lambda z: z[5])
    sprawdz("najdalsze punkty trasy zajmują ponad połowę kadru przy każdym rozmiarze",
            all(z[5] >= 0.55 for z in _kadry13),
            "najgorszy: %s — %.0f%% kadru" % (_najciasniej13[0],
                                              100.0 * _najciasniej13[5]))

    _bliziutko13 = _Dzien13(15, ["Wólka bliska", "Wólka bliższa"])
    _lat13, _lng13 = _BLISKO13[_BAZA13]
    _male13 = dict(_MIASTA13)
    _male13["Wólka bliska"] = (_lat13 + 0.030, _lng13 + 0.020, _PM13.RANGA_WIES)
    _male13["Wólka bliższa"] = (_lat13 - 0.020, _lng13 + 0.040, _PM13.RANGA_WIES)
    _m_blisko13 = _mapa13(_bliziutko13, miasta=_male13, rysuj=True)
    _rozpietosc13 = max(_m_blisko13._obszar_swiata()[2:]) / _m_blisko13._jedn_na_km
    sprawdz("dzień z przystankami o rzut beretem nie daje absurdalnego zbliżenia",
            25.0 <= _rozpietosc13 <= 42.0, "kadr ma %.1f km" % _rozpietosc13)

    _m_wolny13 = _mapa13(_WOLNY13, rysuj=True)
    _poza13 = [n for n in _m_wolny13._miasta
               if not _QR13(*_m_wolny13._obszar_swiata()).contains(
                   _QP13(*_m_wolny13._miasta[n]))]
    sprawdz("dzień bez trasy zostawia kadr całemu układowi miast, jak dotąd",
            not _poza13, str(_poza13[:4]))

    # ── 2. KARTKA DELEGACJI NIE ZASŁANIA TRASY ───────────────────
    _z_kartka13 = [z for z in _kadry13 if z[1]._kotwica is not None]
    _srodki13 = [(z[0], z[4], z[1]._kotwica.x()) for z in _z_kartka13]
    sprawdz("środek trasy wypada w tej części kadru, której kartka nie zasłania",
            all(_sr13 < _kx13 - 20.0 for (_o13, _sr13, _kx13) in _srodki13),
            str([(o, round(s), round(k)) for (o, s, k) in _srodki13]))

    _kolizje13 = []
    for _opis13, _m13, _dx13, _dy13, _srx13, _udzial13 in _kadry13:
        _kar13 = _m13._pole_kartki()
        _widzet13 = _QR13(0.0, 0.0, float(_m13.width()), float(_m13.height()))
        for _e13 in _m13._geometria()["etykiety"]:
            if not _widzet13.contains(_e13["pole"]):
                _kolizje13.append((_opis13, _e13["napis"], "poza widżetem"))
            if _kar13 is not None and not _e13["pole"].intersected(_kar13).isEmpty():
                _kolizje13.append((_opis13, _e13["napis"], "pod kartką"))
    sprawdz("żadna tabliczka nie wychodzi poza widżet ani nie wchodzi pod kartkę",
            not _kolizje13, str(_kolizje13[:4]))

    # ── 3. MIEJSCOWOŚCI WIDAĆ, A SĄSIADKI SIĘ NIE ZLEWAJĄ ────────
    _m_region13 = [z[1] for z in _kadry13 if z[0] == "dzień rozrzucony 1200×760"][0]
    _odn13 = _odniesienie13(_m_region13)
    _znaki13 = _m_region13._znaki_miejscowosci(_m_region13.rzut())
    _wies13 = sorted(n for n in _m_region13._miasta if n.startswith("Wólka"))[0]
    _miary13 = {"baza": _srednica_znaku13(_m_region13, _BAZA13, _znaki13, _odn13),
                "miasto": _srednica_znaku13(_m_region13, "Lublin", _znaki13, _odn13),
                "wieś": _srednica_znaku13(_m_region13, _wies13, _znaki13, _odn13)}
    sprawdz("w kadrze regionu baza, miasto powiatowe i wieś mają czytelne znaki",
            40.0 <= _miary13["baza"] <= 60.0
            and 22.0 <= _miary13["miasto"] <= 32.0
            and 12.0 <= _miary13["wieś"] <= 18.0,
            "baza %.0f px, miasto %.0f px, wieś %.0f px"
            % (_miary13["baza"], _miary13["miasto"], _miary13["wieś"]))

    _m_ciasny13 = [z[1] for z in _kadry13 if z[0] == "dzień ciasny 1200×760"][0]
    _znaki_c13 = _m_ciasny13._znaki_miejscowosci(_m_ciasny13.rzut())
    # znak wolno przyciąć TYLKO sąsiadce; z daleka od innych osad ma być
    # co najmniej tak duży, jak prawdziwy obrys miejscowości
    _samotne13 = [n for n in _m_ciasny13._miasta
                  if _m_ciasny13._sasiedztwo.get(n, [(0.0, "")])[0][0]
                  / _m_ciasny13._jedn_na_km > 30.0]
    _skurczone13 = [n for n in _samotne13 if _znaki_c13.get(n, 1.0) < 1.0]
    sprawdz("znak nie schodzi poniżej prawdziwego obrysu — zmniejsza go tylko sąsiad",
            not _skurczone13 and len(_samotne13) > 10,
            "%d z %d" % (len(_skurczone13), len(_samotne13)))

    _pary13 = []
    _nazwy13 = sorted(_m_ciasny13._miasta)
    for _i13 in range(len(_nazwy13)):
        _ax13, _ay13 = _m_ciasny13._miasta[_nazwy13[_i13]]
        for _j13 in range(_i13 + 1, len(_nazwy13)):
            _bx13, _by13 = _m_ciasny13._miasta[_nazwy13[_j13]]
            _d13 = math.hypot(_bx13 - _ax13, _by13 - _ay13) / _m_ciasny13._jedn_na_km
            _pary13.append((_d13, _nazwy13[_i13], _nazwy13[_j13]))
    _pary13.sort()
    _trasa13 = [n for n in dict.fromkeys(_CIASNY13.trasa) if n in _m_ciasny13._miasta]
    _para_trasy13 = min((p for p in _pary13
                         if p[1] in _trasa13 and p[2] in _trasa13), key=lambda z: z[0])
    _luka13 = (_para_trasy13[0]
               - _zasieg_znaku13(_m_ciasny13, _para_trasy13[1], _znaki_c13)
               - _zasieg_znaku13(_m_ciasny13, _para_trasy13[2], _znaki_c13))
    sprawdz("znaki dwóch najbliższych miejscowości trasy nie zachodzą na siebie",
            _luka13 > 0.0, "%s–%s: %.1f km odstępu przy %.1f km odległości"
            % (_para_trasy13[1], _para_trasy13[2], _luka13, _para_trasy13[0]))

    _zlane13 = []
    for _d13, _a13, _b13 in _pary13[:400]:
        if (_zasieg_znaku13(_m_ciasny13, _a13, _znaki_c13)
                + _zasieg_znaku13(_m_ciasny13, _b13, _znaki_c13)) >= _d13:
            _zlane13.append((_a13, _b13, round(_d13, 1)))
    sprawdz("żadne dwa znaki na mapie nie zlewają się w jedną plamę zabudowy",
            not _zlane13, str(_zlane13[:4]))

    _ramie_przed13 = _ramie_podzialki13(_m_region13)
    _progi13 = dict(_PM13.PROG_ZNAKU_PX)
    try:
        for _r13 in _PM13.PROG_ZNAKU_PX:
            _PM13.PROG_ZNAKU_PX[_r13] = _progi13[_r13] * 2.0
        _m_region13._znaki = None
        _znaki_po13 = _m_region13._znaki_miejscowosci(_m_region13.rzut())
        _ramie_po13 = _ramie_podzialki13(_m_region13)
    finally:
        _PM13.PROG_ZNAKU_PX.update(_progi13)
        _m_region13._znaki = None
    sprawdz("podziałka mierzy teren: próg czytelności znaku nie rusza jej ani o piksel",
            _ramie_przed13 == _ramie_po13
            and _znaki_po13[_wies13] > _znaki13[_wies13] * 1.9,
            "%s wobec %s; znak wsi ×%.2f" % (_ramie_przed13, _ramie_po13,
                                             _znaki_po13[_wies13] / _znaki13[_wies13]))

    # ── 4. TABLICZKI ROZCHODZĄ SIĘ I NIE SKACZĄ ──────────────────
    _nachodzace13 = []
    for _opis13, _m13, _dx13, _dy13, _srx13, _udzial13 in _kadry13:
        _pola13 = [(e["napis"], e["pole"]) for e in _m13._geometria()["etykiety"]]
        for _i13 in range(len(_pola13)):
            for _j13 in range(_i13 + 1, len(_pola13)):
                if not _pola13[_i13][1].intersected(_pola13[_j13][1]).isEmpty():
                    _nachodzace13.append((_opis13, _pola13[_i13][0], _pola13[_j13][0]))
    sprawdz("żadne dwie tabliczki nie mają części wspólnej — ani ciasny dzień, ani szeroki",
            not _nachodzace13 and len(_kadry13) == 6, str(_nachodzace13[:4]))

    _uklad13 = [(e["napis"], round(e["pole"].x(), 2), round(e["pole"].y(), 2))
                for e in _mapa13(_CIASNY13, 940, 640, _KOTWICA13)
                ._geometria()["etykiety"]]
    _plik13 = os.path.join(_TMP_HOME, "uklad_mapy.json")
    with open(_plik13, "w", encoding="utf-8") as _f13:
        json.dump({"miasta": {k: list(v) for k, v in _MIASTA13.items()},
                   "przystanki": list(_CIASNY13.przystanki), "dzien": 1},
                  _f13)
    _skrypt13 = os.path.join(_TMP_HOME, "uklad_mapy.py")
    with open(_skrypt13, "w", encoding="utf-8") as _f13:
        _f13.write(
            "# -*- coding: utf-8 -*-\n"
            "import os, sys, json, datetime\n"
            "sys.path.insert(0, %r)\n"
            "sys.path.insert(0, %r)\n"
            "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')\n"
            "from PyQt6.QtWidgets import QApplication\n"
            "from PyQt6.QtCore import QPointF\n"
            "app = QApplication([])\n"
            "import proto_mapa as PM\n"
            "d = json.load(open(sys.argv[1], encoding='utf-8'))\n"
            "class Dzien:\n"
            "    data = datetime.date(2026, 10, d['dzien'])\n"
            "    wolny = False\n"
            "    przystanki = d['przystanki']\n"
            "    @property\n"
            "    def trasa(self):\n"
            "        return ['Radom'] + list(self.przystanki) + ['Radom']\n"
            "m = PM.MapaDnia()\n"
            "m.ustaw_animacje(False)\n"
            "m.ustaw_miasta({k: tuple(v) for k, v in d['miasta'].items()},"
            " baza='Radom')\n"
            "m.resize(940, 640)\n"
            "m.ustaw_dzien(Dzien())\n"
            "m.ustaw_kotwice_kartki(QPointF(588.0, 68.0))\n"
            "m.ustaw_animacje(False)\n"
            "print(json.dumps([[e['napis'], round(e['pole'].x(), 2),"
            " round(e['pole'].y(), 2)] for e in m._geometria()['etykiety']]))\n"
            % (KATALOG, os.path.join(KATALOG, "prototyp")))
    _srodowisko13 = dict(os.environ)
    _srodowisko13["PYTHONHASHSEED"] = "31337"
    _wynik13 = _sub13.run([sys.executable, _skrypt13, _plik13], env=_srodowisko13,
                          capture_output=True, text=True, timeout=180)
    _obcy13 = [tuple(w) for w in json.loads(_wynik13.stdout.strip().splitlines()[-1])] \
        if _wynik13.returncode == 0 and _wynik13.stdout.strip() else []
    sprawdz("ta sama trasa daje ten sam układ tabliczek przy innym PYTHONHASHSEED",
            _obcy13 == _uklad13 and len(_uklad13) > 4,
            (_wynik13.stderr or "")[-200:] if _obcy13 != _uklad13 else "")
except Exception as _e13:
    sprawdz("kadr za trasą, widoczne miejscowości i rozstawione tabliczki",
            False, repr(_e13))

# ══════════════════════════════════════════════════════════════════
sekcja("14. Pole kwoty: grosze takie, jakie naprawdę wpisano")

try:
    from PyQt6.QtWidgets import QApplication as _QA14
    from PyQt6.QtCore import Qt as _Qt14, QEvent as _QE14, QPointF as _QP14
    from PyQt6.QtGui import QKeyEvent as _QKE14, QMouseEvent as _QME14
    import proto_okno as _OK14
    import nowy_wyglad as _NW14
    _app14 = _QA14.instance() or _QA14(sys.argv)

    def _klaw14(pole, tekst="", klucz=None, mod=None):
        """Jedno naciśnięcie klawisza wprost w pole kwoty."""
        zdarzenie = _QKE14(_QE14.Type.KeyPress, klucz or _Qt14.Key.Key_unknown,
                           mod or _Qt14.KeyboardModifier.NoModifier, tekst)
        pole.keyPressEvent(zdarzenie)
        return zdarzenie

    def _pisz14(pole, ciag, od_nowa=True):
        if od_nowa:
            pole.ustaw_tekst("")
        for _znak14 in ciag:
            _klaw14(pole, _znak14)
        return pole

    def _obraz14(pole):
        return (pole.zlote_napis(), pole.grosze_napis(), pole.wartosc())

    _pole14 = _OK14.PoleKwoty()
    _pole14.resize(344, 52)

    # ── 1. GROSZE POKAZUJĄ TO, CO WPISANO ─────────────────────────
    sprawdz("wpisane „1850” to „1 850” i „,00 zł”",
            _obraz14(_pisz14(_pole14, "1850")) == ("1 850", ",00 zł", 1850.0),
            str(_obraz14(_pole14)))
    sprawdz("wpisane „1850,5” to „1 850” i „,50 zł”",
            _obraz14(_pisz14(_pole14, "1850,5")) == ("1 850", ",50 zł", 1850.5),
            str(_obraz14(_pole14)))
    sprawdz("wpisane „1850,55” to „1 850” i „,55 zł”",
            _obraz14(_pisz14(_pole14, "1850,55")) == ("1 850", ",55 zł", 1850.55),
            str(_obraz14(_pole14)))
    _pisz14(_pole14, "1850,")
    sprawdz("sam przecinek po złotych jeszcze nie wymyśla groszy",
            _obraz14(_pole14) == ("1 850", ",00 zł", 1850.0), str(_obraz14(_pole14)))
    sprawdz("grosze z przykładu nie zostają w polu — nie ma osobnej etykiety „,00 zł”",
            not hasattr(_pole14, "l_grosze")
            and 'QLabel(",00 zł"' not in open(
                os.path.join(KATALOG, "prototyp", "proto_okno.py"),
                encoding="utf-8").read())
    sprawdz("złote są duże, grosze mniejsze — jedna liczba, dwa kroje",
            _pole14.ROZMIAR_GROSZY < _pole14._rozmiar
            and _pole14._szer_zlotych() > _pole14._szer_groszy() > 0,
            str((_pole14._rozmiar, _pole14.ROZMIAR_GROSZY)))

    # ── 2. KROPKA, PRZECINEK, SPACJE ──────────────────────────────
    _pisz14(_pole14, "1850.55")
    _kropka14 = _pole14._tresc
    _pisz14(_pole14, "1850,55")
    sprawdz("kropka trafia w to samo miejsce, co przecinek",
            _kropka14 == _pole14._tresc == "1850,55", repr(_kropka14))
    sprawdz("spacje w tysiącach nie przeszkadzają w pisaniu",
            _obraz14(_pisz14(_pole14, "1 8 5 0")) == ("1 850", ",00 zł", 1850.0),
            str(_obraz14(_pole14)))
    _pisz14(_pole14, "1850")
    _pole14._ustaw_kursor(2)
    _klaw14(_pole14, "9")
    sprawdz("cyfra dopisana w środku liczby ląduje tam, gdzie stał kursor",
            _pole14.zlote_napis() == "18 950" and _pole14._kursor == 3,
            str((_pole14.zlote_napis(), _pole14._kursor)))
    sprawdz("trzecia cyfra groszy już się nie mieści",
            _obraz14(_pisz14(_pole14, "1850,555")) == ("1 850", ",55 zł", 1850.55),
            str(_obraz14(_pole14)))

    # ── 3. PRZYPADKI BRZEGOWE ─────────────────────────────────────
    _pole14.ustaw_tekst("")
    sprawdz("puste pole jest puste: bez liczby, bez groszy, bez złotówki",
            (_pole14.tekst(), _pole14.grosze_napis(), _pole14.wartosc()) == ("", "", 0.0),
            str((_pole14.tekst(), _pole14.grosze_napis())))
    sprawdz("sam przecinek daje „0” i „,00 zł”",
            _obraz14(_pisz14(_pole14, ",")) == ("0", ",00 zł", 0.0),
            str(_obraz14(_pole14)))
    sprawdz("„0,00” zostaje zerem co do grosza",
            _obraz14(_pisz14(_pole14, "0,00")) == ("0", ",00 zł", 0.0),
            str(_obraz14(_pole14)))
    sprawdz("zera wiodące znikają: „007” to 7 zł",
            _obraz14(_pisz14(_pole14, "007")) == ("7", ",00 zł", 7.0),
            str(_obraz14(_pole14)))
    _pisz14(_pole14, "1850,55")
    for _ in range(3):
        _klaw14(_pole14, klucz=_Qt14.Key.Key_Backspace)
    sprawdz("kasowanie groszy razem z przecinkiem wraca do samych złotych",
            _obraz14(_pole14) == ("1 850", ",00 zł", 1850.0), str(_obraz14(_pole14)))

    # ── 4. SCHOWEK: KROPKA, SPACJE, ZŁOTÓWKA ──────────────────────
    _schowek14 = _QA14.clipboard()
    _wklejone14 = []
    for _co14, _ile14 in (("1 850.50 zł", 1850.5), ("2 254,50", 2254.5),
                          ("1850.5", 1850.5), ("12 zł", 12.0)):
        _schowek14.setText(_co14)
        _pole14.ustaw_tekst("")
        _pole14._ze_schowka()
        _wklejone14.append((_co14, _pole14.wartosc(), _ile14))
    sprawdz("wklejona kwota z kropką, spacjami i złotówką trafia w grosze",
            all(abs(w - o) < 0.005 for _, w, o in _wklejone14), str(_wklejone14))

    # ── 5. DŁUGA LICZBA I MIEJSCE W KARCIE ────────────────────────
    _pisz14(_pole14, "123456789,99")
    _luzno14 = (_pole14._rozmiar,
                _pole14._szer_zlotych() + _pole14._szer_groszy(),
                _pole14._obszar.width())
    _pole14.ustaw_note("maks. 9 935 zł", True)      # nota zabiera miejsce
    _ciasno14 = (_pole14._rozmiar,
                 _pole14._szer_zlotych() + _pole14._szer_groszy(),
                 _pole14._obszar.width())
    _pole14.ustaw_note("")
    sprawdz("bardzo długa kwota zmniejsza czcionkę i nadal mieści się w polu",
            _ciasno14[0] < _luzno14[0] <= _OK14.PoleKwoty.ROZMIARY[0]
            and _luzno14[1] <= _luzno14[2] + 0.5
            and _ciasno14[1] <= _ciasno14[2] + 0.5
            and _obraz14(_pole14) == ("123 456 789", ",99 zł", 123456789.99),
            str((_luzno14, _ciasno14)))

    # ── 6. KURSOR I ZAZNACZANIE ───────────────────────────────────
    _pisz14(_pole14, "1850,55")
    _x14 = _pole14._obszar.x() + _pole14._x_indeksu(2)
    _punkt14 = _QP14(_x14, _pole14.height() / 2.0)
    _pole14.mousePressEvent(_QME14(_QE14.Type.MouseButtonPress, _punkt14, _punkt14,
                                   _Qt14.MouseButton.LeftButton,
                                   _Qt14.MouseButton.LeftButton,
                                   _Qt14.KeyboardModifier.NoModifier))
    sprawdz("kliknięcie stawia kursor tam, gdzie pokazała mysz",
            _pole14._kursor == 2, str(_pole14._kursor))
    _x_gr14 = _pole14._obszar.x() + _pole14._x_indeksu(6)
    _punkt_gr14 = _QP14(_x_gr14, _pole14.height() / 2.0)
    _pole14.mousePressEvent(_QME14(_QE14.Type.MouseButtonPress, _punkt_gr14,
                                   _punkt_gr14, _Qt14.MouseButton.LeftButton,
                                   _Qt14.MouseButton.LeftButton,
                                   _Qt14.KeyboardModifier.NoModifier))
    sprawdz("kursor wchodzi też między grosze",
            _pole14._kursor == 6 and _pole14._x_indeksu(6) > _pole14._szer_zlotych(),
            str(_pole14._kursor))
    _rosnie14 = [_pole14._x_indeksu(i) for i in range(len(_pole14._tresc) + 1)]
    sprawdz("kursor idzie w prawo przez całą liczbę, także przez odstęp tysięcy",
            all(b > a for a, b in zip(_rosnie14, _rosnie14[1:])),
            str([round(x, 1) for x in _rosnie14]))
    _pisz14(_pole14, "1850,55")
    _pole14._ustaw_kursor(0)
    for _ in range(4):
        _klaw14(_pole14, "", _Qt14.Key.Key_Right,
                _Qt14.KeyboardModifier.ShiftModifier)
    _zazn14 = _pole14._zakres()
    _klaw14(_pole14, "", _Qt14.Key.Key_Left)
    _zdjete14 = _pole14._zakres()
    _klaw14(_pole14, "", _Qt14.Key.Key_End)
    sprawdz("Shift ze strzałką zaznacza, sama strzałka zdejmuje, End idzie na koniec",
            _zazn14 == (0, 4) and _zdjete14 == (0, 0)
            and _pole14._kursor == len("1850,55"),
            str((_zazn14, _zdjete14, _pole14._kursor)))
    _klaw14(_pole14, "a", klucz=_Qt14.Key.Key_A,
            mod=_Qt14.KeyboardModifier.ControlModifier)
    sprawdz("Ctrl+A bierze całą kwotę razem z groszami",
            _pole14._zakres() == (0, len("1850,55")), str(_pole14._zakres()))
    _klaw14(_pole14, "7")
    sprawdz("pisanie po zaznaczeniu zastępuje całą kwotę",
            _obraz14(_pole14) == ("7", ",00 zł", 7.0), str(_obraz14(_pole14)))
    _pisz14(_pole14, "1850,55")
    _pole14._kotwica, _pole14._kursor = 0, 4
    _klaw14(_pole14, klucz=_Qt14.Key.Key_Backspace)
    sprawdz("skasowanie zaznaczonych złotych zostawia same grosze",
            _obraz14(_pole14) == ("0", ",55 zł", 0.55), str(_obraz14(_pole14)))

    # ── 7. KLAWISZE POLA NIE UCIEKAJĄ DO OKNA ─────────────────────
    _pisz14(_pole14, "1850")
    _moje14 = [_klaw14(_pole14, "5").isAccepted(),
               _klaw14(_pole14, "", _Qt14.Key.Key_Left).isAccepted(),
               _klaw14(_pole14, "", _Qt14.Key.Key_Right).isAccepted(),
               _klaw14(_pole14, "\r", _Qt14.Key.Key_Return).isAccepted()]
    _cudze14 = [_klaw14(_pole14, "", _Qt14.Key.Key_Escape).isAccepted(),
                _klaw14(_pole14, "", _Qt14.Key.Key_PageDown).isAccepted()]
    sprawdz("cyfry, strzałki i Enter należą do pola, a Esc i PageDown do okna",
            all(_moje14) and not any(_cudze14), str((_moje14, _cudze14)))
    _echo14 = {"zmian": 0, "zatwierdzen": 0}
    _pole14.zmieniono.connect(lambda: _echo14.__setitem__("zmian", _echo14["zmian"] + 1))
    _pole14.zatwierdzono.connect(
        lambda: _echo14.__setitem__("zatwierdzen", _echo14["zatwierdzen"] + 1))
    _pisz14(_pole14, "125", od_nowa=False)
    _klaw14(_pole14, "\r", _Qt14.Key.Key_Return)
    sprawdz("pole melduje każdą zmianę i osobno zatwierdzenie Enterem",
            _echo14["zmian"] >= 3 and _echo14["zatwierdzen"] == 1, str(_echo14))

    # ── 8. KWOTA DOCHODZI DO SILNIKA CO DO GROSZA ─────────────────
    _prof14 = _NW14.ProfilWidoku("Jan Testowy", "85010112345",
                                 "ul. Kwiatowa 5, 26-600 Radom", "KR")
    _okno14 = _NW14.OknoNowegoWygladu(profil=_prof14, rok=2026, miesiac=10)
    _okno14._pole_pesel.setText("85010112345")
    _app14.processEvents()
    _pisz14(_okno14.k_parametry.kwota, "1850,55")
    _okno14._przelicz_teraz()
    _dane14, _powod14 = _okno14._dane_do_generacji()
    sprawdz("kwota z groszami idzie z pola do silnika bez zaokrąglenia",
            abs(_okno14._kwota() - 1850.55) < 0.0005 and _dane14 is not None
            and abs(_dane14["kwota_cel"] - 1850.55) < 0.0005,
            str((_okno14._kwota(), _powod14)))
    sprawdz("grosze zapisują się w ustawieniach i wracają po ponownym otwarciu",
            abs(float(P.ustawienie(_NW14.OknoNowegoWygladu.USTAWIENIE_KWOTY, 0))
                - 1850.55) < 0.0005, str(P.ustawienie(
                    _NW14.OknoNowegoWygladu.USTAWIENIE_KWOTY, 0)))
    _okno14b = _NW14.OknoNowegoWygladu(profil=_prof14, rok=2026, miesiac=10)
    _wrocila14 = (_okno14b._kwota(), _okno14b.k_parametry.kwota.tekst())
    _okno14b.close()
    sprawdz("wznowione okno pokazuje te same grosze, co przed zamknięciem",
            abs(_wrocila14[0] - 1850.55) < 0.0005 and _wrocila14[1] == "1 850,55",
            str(_wrocila14))

    _okno14.k_parametry.kwota.ustaw_tekst("")
    _okno14._przelicz_teraz()
    sprawdz("puste pole to zero, a nie ostatnia kwota",
            abs(_okno14._kwota()) < 0.0005 and not _okno14._za_duzo,
            str(_okno14._kwota()))
    _okno14.k_parametry.kwota.ustaw_tekst("%.2f" % (P.MIN_KWOTA - 0.01))
    _okno14._przelicz_teraz()
    _malo14 = _okno14._dane_do_generacji()[1]
    sprawdz("grosz poniżej progu to wciąż za mało — program mówi o minimum",
            _okno14._dane_do_generacji()[0] is None and _malo14.startswith("min."),
            repr(_malo14))
    _okno14.k_parametry.kwota.ustaw_tekst("%.2f" % (P.MIN_KWOTA,))
    _okno14._przelicz_teraz()
    sprawdz("dokładnie kwota minimalna już przechodzi",
            _okno14._dane_do_generacji()[0] is not None
            and abs(_okno14._kwota() - P.MIN_KWOTA) < 0.0005,
            str(_okno14._kwota()))
    _maks14 = _okno14._maks_miesiaca(_okno14.k_parametry.tryb.aktywna())
    _okno14.k_parametry.kwota.ustaw_tekst("%.2f" % (_maks14 + 1.0))
    _okno14._przelicz_teraz()
    _duzo14 = _okno14._dane_do_generacji()[1]
    sprawdz("grosz ponad miesiąc to już za dużo — program podaje maksimum",
            _okno14._za_duzo and _duzo14.startswith("maks.")
            and _okno14.k_parametry.kwota.l_nota.text().startswith("maks."),
            str((_duzo14, _okno14.k_parametry.kwota.l_nota.text())))
    _okno14.close()

    if not SZYBKO:
        P._osrm_dostepny = False
        P._road_cache.clear()
        _dni_gr14 = P.generuj_trasy(1850.55, "Radom", 51.40, 21.15, "mazowieckie",
                                    P.pobierz_dni_robocze(2026, 10), "90010112345",
                                    stawka=0.89)
        _suma_gr14 = sum(_d14.suma for _d14 in _dni_gr14)
        sprawdz("silnik rozpisuje kwotę z groszami co do grosza",
                abs(_suma_gr14 - 1850.55) <= 0.01, "wyszło %.2f zł" % _suma_gr14)
        P._road_cache.clear()
except Exception as _e14:
    sprawdz("pole kwoty pokazuje grosze, które wpisano", False, repr(_e14))

# ══════════════════════════════════════════════════════════════════
sekcja("15. Podgląd miesiąca mówi prawdę: dni, kwoty, kilometry, miasta, dokumenty")

# Zanim cokolwiek zostanie wygenerowane, taśma pokazuje SZACUNEK. Do 3.22
# szacunek dzielił kwotę na dni RÓWNO CO DO GROSZA, kilometry liczył
# z pieniędzy, a przystanki brał z 28 miejscowości bez pamięci między dniami —
# więc każdy dzień miał tę samą kwotę, tę samą liczbę kilometrów, siedem
# postojów i tę samą wieś po kilkanaście razy w miesiącu. Ta sekcja pilnuje,
# żeby podgląd trzymał się reguł silnika.
try:
    import nowy_wyglad as _NW15
    import proto_tasma as _PT15
    from PyQt6.QtWidgets import QApplication as _QA15

    _ROK15, _MIES15, _STAWKA15 = 2026, 10, 1.15
    _PESEL15 = "44051401359"
    _BAZY15 = (("Radom", "mazowieckie"), ("Piaseczno", "mazowieckie"),
               ("Warszawa", "mazowieckie"))

    def _geo15(baza, woj):
        lat, lng = _NW15.wspolrzedne_bazy(baza, baza, woj)
        return (lat, lng,
                _NW15.miasta_wokol_bazy(baza, lat, lng, woj, _NW15.MIAST_PODGLADU))

    def _plan15(baza, woj, kwota, stawka=_STAWKA15, wolne=()):
        _lat, _lng, geo = _geo15(baza, woj)
        return geo, _NW15.plan_podgladu(kwota, _ROK15, _MIES15, "Tydzień", wolne,
                                        stawka, geo, baza, P.MAX_KWOTA_DNIA)

    def _licznik15(plan):
        lic = {}
        for dzien in plan:
            for nazwa in dzien["przystanki"]:
                lic[nazwa] = lic.get(nazwa, 0) + 1
        return lic

    # ── 1. SUMA CO DO GROSZA ──────────────────────────────────────
    _zle_sumy15 = []
    for _b15, _w15 in _BAZY15:
        for _k15 in (300.0, 900.0, 1850.55, 3000.0, 5000.0):
            _g15, _p15 = _plan15(_b15, _w15, _k15)
            _s15 = round(sum(d["kwota"] for d in _p15), 2)
            if abs(_s15 - _k15) > 0.005:
                _zle_sumy15.append((_b15, _k15, _s15))
    sprawdz("kwoty dni podglądu sumują się do zamówionej kwoty CO DO GROSZA (15 przebiegów)",
            not _zle_sumy15, str(_zle_sumy15[:3]))

    # ── 2. ŻADEN DZIEŃ PONAD SUFIT ────────────────────────────────
    # Objaw właściciela: „kwoty każdego dnia wyświetlają się jako 321 zł" —
    # podgląd malował dzień, którego nie da się przejechać, gdy kwota
    # przekraczała maksimum miesiąca.
    _nad_sufit15, _pod_droga15 = [], []
    for _b15, _w15 in _BAZY15:
        for _k15 in (300.0, 1850.0, 5000.0, 9000.0, 15000.0, 30000.0):
            _g15, _p15 = _plan15(_b15, _w15, _k15)
            for _d15 in _p15:
                _post15 = len(_d15["przystanki"])
                _fiz15 = P.pojemnosc_dnia_zl(_post15, _STAWKA15, P.MAX_KWOTA_DNIA)
                if (_d15["kwota"] > _fiz15 + 0.005
                        or _d15["kwota"] > P.MAX_KWOTA_DNIA + 0.005):
                    _nad_sufit15.append((_b15, _k15, round(_d15["kwota"], 2),
                                         _fiz15, _post15))
                _linia15 = _NW15.km_petli_podgladu(_g15, _b15, _d15["przystanki"])
                if _d15["km"] < _linia15 * P.MNOZNIK_MIN - 0.5:
                    _pod_droga15.append((_b15, _k15, round(_d15["km"], 1),
                                         round(_linia15, 1)))
    sprawdz("żaden dzień podglądu nie przekracza pojemności doby ani limitu dnia — także przy kwocie ponad miesiąc",
            not _nad_sufit15, str(_nad_sufit15[:3]))
    sprawdz("kilometry dnia podglądu nigdy nie są krótsze niż narysowana pętla razy krętość dróg",
            not _pod_droga15, str(_pod_droga15[:3]))

    # ── 3. POWTARZALNOŚĆ ──────────────────────────────────────────
    _pow_a15 = _plan15("Radom", "mazowieckie", 1850.55)[1]
    _pow_b15 = _plan15("Radom", "mazowieckie", 1850.55)[1]
    sprawdz("ten sam podgląd za każdym razem — taśma nie miga przy przeliczaniu",
            _pow_a15 == _pow_b15 and len(_pow_a15) > 1,
            "%d / %d dni" % (len(_pow_a15), len(_pow_b15)))
    _pow_c15 = _plan15("Radom", "mazowieckie", 1851.55)[1]
    sprawdz("inna kwota to inny podgląd — szacunek nie jest tapetą",
            _pow_c15 != _pow_a15)
    _pow_d15 = _plan15("Radom", "mazowieckie", 1850.55, wolne=(5, 6, 7))[1]
    sprawdz("dni bez pracy naprawdę wypadają z podglądu",
            not [d for d in _pow_d15 if d["data"].day in (5, 6, 7)],
            str([d["data"].day for d in _pow_d15]))

    # ── 4. ROZRZUT KWOT I KILOMETRÓW ──────────────────────────────
    # Rozrzutu wymagamy tam, gdzie jest na niego MIEJSCE. Przy kwocie bliskiej
    # maksimum miesiąca każdy dzień musi stanąć pod sufitem doby i wtedy dni są
    # z konieczności podobne — wymaganie różnic byłoby wymaganiem niemożliwego.
    # Dla takich miesięcy sprawdzamy co innego: że dni NAPRAWDĘ stoją pod
    # sufitem, a nie że są równe z lenistwa.
    _DNI_ROB15 = _NW15.dni_robocze_realne(_ROK15, _MIES15, "Tydzień")
    _MAKS_MIES15 = P.maks_kwota_miesiaca(len(_DNI_ROB15), _STAWKA15)
    _SUFIT_DNIA15 = P.pojemnosc_dnia_zl(P.POSTOJE_TYPOWE, _STAWKA15, P.MAX_KWOTA_DNIA)
    _rowne15, _rowne_km15, _nie_pod_sufitem15 = [], [], []
    for _b15, _w15 in _BAZY15:
        for _k15 in (900.0, 1850.55, 3000.0, 5000.0, 9000.0):
            _g15, _p15 = _plan15(_b15, _w15, _k15)
            _ile15 = len(_p15)
            _r_kwot15 = len({round(d["kwota"], 2) for d in _p15})
            _r_km15 = len({round(d["km"], 1) for d in _p15})
            if _k15 >= 0.8 * _MAKS_MIES15:          # miesiąc nasycony
                _srednia15 = sum(d["kwota"] for d in _p15) / max(1, _ile15)
                if _srednia15 < 0.8 * _SUFIT_DNIA15:
                    _nie_pod_sufitem15.append((_b15, _k15, round(_srednia15, 2),
                                               _SUFIT_DNIA15))
                continue
            if _r_kwot15 < max(2, _ile15 // 2):
                _rowne15.append((_b15, _k15, _ile15, _r_kwot15))
            if _r_km15 < max(2, _ile15 // 2):
                _rowne_km15.append((_b15, _k15, _ile15, _r_km15))
    sprawdz("kwoty dni się RÓŻNIĄ — miesiąc nie jest jedną kwotą powieloną 22 razy",
            not _rowne15, str(_rowne15[:3]))
    sprawdz("kilometry dni też się różnią — nie są przeliczoną kwotą tego samego dnia",
            not _rowne_km15, str(_rowne_km15[:3]))
    sprawdz("miesiąc nasycony: dni stoją pod sufitem doby, a nie są równe z lenistwa",
            not _nie_pod_sufitem15, str(_nie_pod_sufitem15[:3]))

    # ── 5. MIEJSCOWOŚCI SIĘ NIE POWTARZAJĄ ────────────────────────
    _powtorki15 = []
    for _b15, _w15 in _BAZY15:
        for _k15 in (900.0, 1850.55, 3000.0, 5000.0, 9000.0):
            _g15, _p15 = _plan15(_b15, _w15, _k15)
            _lic15 = _licznik15(_p15)
            _wizyt15 = sum(_lic15.values())
            _naj15 = max(_lic15.values()) if _lic15 else 0
            if _naj15 > 5 or len(_lic15) < len(_p15) or _wizyt15 > 4 * len(_lic15):
                _powtorki15.append((_b15, _k15, len(_p15), _wizyt15,
                                    len(_lic15), _naj15))
    sprawdz("miejscowości nie wracają co drugi dzień: najczęstsza najwyżej 5 razy w miesiącu",
            not _powtorki15, str(_powtorki15[:3]))

    # ── 6. DOKUMENTY ──────────────────────────────────────────────
    _zle_dok15 = []
    for _b15, _w15 in _BAZY15:
        for _k15 in (900.0, 1850.55, 3000.0, 5000.0, 9000.0):
            _g15, _p15 = _plan15(_b15, _w15, _k15)
            _numery15 = sorted({d["dokument"] for d in _p15})
            if _numery15 != list(range(1, len(_numery15) + 1)):
                _zle_dok15.append((_b15, _k15, "numery", _numery15))
                continue
            for _nr15 in _numery15:
                _dni15 = [d for d in _p15 if d["dokument"] == _nr15]
                _suma15 = sum(d["kwota"] for d in _dni15)
                _wiersze15 = sum(len(d["przystanki"]) + 1 for d in _dni15)
                if (_suma15 > P.MAX_KWOTA_DOKUMENTU + 0.005
                        or _wiersze15 > P.MAX_ETAPOW_DOKUMENTU):
                    _zle_dok15.append((_b15, _k15, _nr15, round(_suma15, 2),
                                       _wiersze15))
    sprawdz("dni podglądu są ponumerowane dokumentami 1..N, a żaden dokument nie łamie sufitu kwoty ani strony A4",
            not _zle_dok15, str(_zle_dok15[:3]))

    # ── 7. TAŚMA POKAZUJE DOKUMENTY BEZ ANI JEDNEGO NAPISU ────────
    _app15 = _QA15.instance() or _QA15(sys.argv)
    _g15, _p15 = _plan15("Radom", "mazowieckie", 5000.0)
    _dni_w15 = _NW15.podglad_miesiaca(5000.0, _ROK15, _MIES15, "Tydzień", (),
                                      _STAWKA15, _g15, "Radom", P.MAX_KWOTA_DNIA)
    _widoczne15 = [d for d in _dni_w15 if d.data.weekday() < 5]
    _tasma15 = _PT15.TasmaMiesiaca()
    _tasma15.resize(1300, _PT15.H_TASMY)
    _tasma15.ustaw_dni(_widoczne15)
    _zakresy15 = _tasma15._zakresy_dokumentow(_tasma15._kafle())
    _ile_dok15 = max((d["dokument"] for d in _p15), default=0)
    sprawdz("taśma rysuje tyle klamer, ile będzie poleceń wyjazdu",
            len(_zakresy15) == _ile_dok15 and _ile_dok15 > 1,
            "%d klamer wobec %d dokumentów" % (len(_zakresy15), _ile_dok15))
    sprawdz("klamry idą po kolei i nie zachodzą na siebie",
            all(_zakresy15[i][2] < _zakresy15[i + 1][1]
                for i in range(len(_zakresy15) - 1)), str(_zakresy15))
    _tasma15.zatrzymaj_animacje()
    _tasma15.deleteLater()

    # ── 8. PODGLĄD NIE UDAJE REALNYCH DRÓG ────────────────────────
    P.zeruj_zrodlo_odleglosci()
    _plan15("Radom", "mazowieckie", 1850.55)
    sprawdz("policzenie podglądu nie dotyka źródła odległości — nota przy kwocie nie kłamie",
            P.stan_zrodla_odleglosci()["odcinki"] == 0,
            str(P.stan_zrodla_odleglosci()))

    # ── 9. TYLE SAMO DNI I DOKUMENTÓW, CO W SILNIKU ───────────────
    if not SZYBKO:
        _osrm15 = P._osrm_dostepny
        P._osrm_dostepny = False
        P._road_cache.clear()
        _rozjazd15 = []
        for _b15, _w15 in _BAZY15:
            _lat15, _lng15, _g15 = _geo15(_b15, _w15)
            for _k15 in (900.0, 1850.55, 3000.0, 5000.0):
                _p15 = _NW15.plan_podgladu(_k15, _ROK15, _MIES15, "Tydzień", (),
                                           _STAWKA15, _g15, _b15, P.MAX_KWOTA_DNIA)
                P.ustaw_tryb_pracy("tydzien")
                _dni_s15 = P.generuj_trasy(_k15, _b15, _lat15, _lng15, _w15,
                                           P.pobierz_dni_robocze(_ROK15, _MIES15),
                                           _PESEL15, stawka=_STAWKA15)
                _grupy15 = P._podziel_na_dokumenty(sorted(_dni_s15,
                                                          key=lambda d: d.data))
                _dok_p15 = max((d["dokument"] for d in _p15), default=0)
                if (abs(len(_p15) - len(_dni_s15)) > 4
                        or abs(_dok_p15 - len(_grupy15)) > 1):
                    _rozjazd15.append((_b15, _k15, len(_p15), len(_dni_s15),
                                       _dok_p15, len(_grupy15)))
                P._road_cache.clear()
        sprawdz("podgląd i silnik zgadzają się co do liczby dni (±4) i dokumentów (±1) na 12 przebiegach",
                not _rozjazd15, str(_rozjazd15[:3]))
        P._osrm_dostepny = _osrm15
except Exception as _e15:
    sprawdz("podgląd miesiąca liczy się regułami silnika", False, repr(_e15))


# ══════════════════════════════════════════════════════════════════
sekcja("16. Kartka delegacji nigdy nie zasłania trasy")

try:
    from PyQt6.QtWidgets import QApplication as _QA16
    from PyQt6.QtCore import (Qt as _Qt16, QRectF as _QR16, QPointF as _QP16,
                              QEvent as _QE16)
    from PyQt6.QtGui import QImage as _QI16, QMouseEvent as _QME16
    import nowy_wyglad as _NW16
    import proto_okno as _OK16
    import proto_mapa as _PM16
    _app16 = _QA16.instance() or _QA16(sys.argv)
    _app16.setStyleSheet(_NW16.arkusz())

    # ── PODGLĄDANIE PIERWSZEGO WEJŚCIA DO PROGRAMU ────────────────
    # Kadr liczył się kiedyś ZANIM okno ustawiło kartkę: mapa malowała trasę
    # wciśniętą w pasek przy lewej krawędzi i dopiero pierwszy resizeEvent
    # wrzucał ją na miejsce. Podsłuchujemy więc KAŻDE malowanie od konstruktora
    # do pierwszego pokazania okna.
    _klatki16 = []
    _stary_paint16 = _PM16.MapaDnia.paintEvent

    def _paint16(self, zdarzenie):
        pole = self._pole()
        kar = self._pole_kartki()
        _klatki16.append({
            "szer": self.width(), "wys": self.height(),
            "kadr_prawy": pole.right(), "kadr_szer": pole.width(),
            "kadr_wys": pole.height(), "trasa": self._czynny(),
            "kartka_lewa": None if kar is None else kar.left(),
            "kartka_prawa": None if kar is None else kar.right()})
        return _stary_paint16(self, zdarzenie)

    _PM16.MapaDnia.paintEvent = _paint16
    try:
        _okno16 = _NW16.OknoNowegoWygladu(
            profil=_NW16.ProfilWidoku("Jan Testowy", "85010112345",
                                      "ul. Kwiatowa 5, 26-600 Radom", "KR"),
            rok=2026, miesiac=10)
        _okno16.show()
        for _ in range(12):
            _app16.processEvents()
    finally:
        _PM16.MapaDnia.paintEvent = _stary_paint16

    def _miel16(ile=6):
        for _ in range(ile):
            _app16.processEvents()

    def _rozmiar16(szer, wys):
        _okno16.showNormal()
        _okno16.setMinimumSize(min(_OK16.ROZMIAR_MIN[0], szer),
                               min(_OK16.ROZMIAR_MIN[1], wys))
        _okno16.resize(szer, wys)
        _miel16(10)
        _okno16.ustaw_animacje(False)
        _miel16(4)

    def _kartka16():
        """Prostokąt kartki we współrzędnych mapy — tam naprawdę leży papier."""
        k, m = _okno16.kartka.geometry(), _okno16.mapa.geometry()
        return _QR16(k.x() - m.x(), k.y() - m.y(), k.width(), k.height())

    def _trasowy16(r, g, b):
        """Czy piksel należy do świecącej trasy: jasny, błękit albo zieleń.

        Krajobraz jest ciemny i zimny, drogi są szare, światła w oknach ciepłe
        — tylko trasa, jej blask i słupy przystanków mają tak wyraźną przewagę
        zieleni i błękitu nad czerwienią przy tej jasności.
        """
        return g - r >= 30 and b - r >= 20 and max(g, b) >= 150

    def _piksele_trasy16(pole, widzet=None):
        """Ile pikseli trasy wypada w zadanym prostokącie SAMEJ MAPY.

        Mapę bierzemy bez kartki na wierzchu — kartka jest osobnym widżetem —
        więc widać dokładnie to, co narysowałaby się pod papierem.
        """
        widzet = widzet if widzet is not None else _okno16.mapa
        obraz = widzet.grab().toImage().convertToFormat(_QI16.Format.Format_RGB888)
        skala = obraz.width() / float(max(1, widzet.width()))
        bajty = obraz.constBits().asstring(obraz.sizeInBytes())
        wiersz = obraz.bytesPerLine()
        lewy = max(0, int(pole.left() * skala))
        prawy = min(obraz.width(), int(math.ceil(pole.right() * skala)))
        gora = max(0, int(pole.top() * skala))
        dol = min(obraz.height(), int(math.ceil(pole.bottom() * skala)))
        ile = 0
        for y in range(gora, dol):
            baza = y * wiersz + lewy * 3
            for x in range(prawy - lewy):
                i = baza + x * 3
                if _trasowy16(bajty[i], bajty[i + 1], bajty[i + 2]):
                    ile += 1
        return ile

    _w_trasie16 = [d for d in _okno16.dni_widoczne if not d.wolny and not d.wylaczony]
    _bliski16 = min(_w_trasie16, key=lambda d: (d.km, d.data.day)).data.day
    _daleki16 = max(_w_trasie16, key=lambda d: (d.km, d.data.day)).data.day
    sprawdz("miesiąc ma dzień blisko bazy i dzień daleko — jest co sprawdzać",
            len(_w_trasie16) >= 3 and _bliski16 != _daleki16,
            "dzień %02d i dzień %02d z %d dni" % (_bliski16, _daleki16,
                                                  len(_w_trasie16)))

    # ── 1. NA PIKSELACH: POD KARTKĄ NIE ŚWIECI NIC Z TRASY ────────
    _brud16 = []
    for _sz16, _wy16 in ((1040, 660), (1440, 900), (1920, 1080)):
        _rozmiar16(_sz16, _wy16)
        for _tryb16 in ("ten dzień", "wszystkie dni"):
            _okno16.zakres.ustaw_aktywna(_tryb16)
            for _dz16 in (_bliski16, _daleki16):
                _okno16._wybierz_dzien(_dz16)
                _okno16.ustaw_animacje(False)
                _miel16(4)
                _ile16 = _piksele_trasy16(_kartka16())
                if _ile16:
                    _brud16.append(("%dx%d %s d%02d" % (_sz16, _wy16, _tryb16, _dz16),
                                    _ile16))
    sprawdz("na pikselach: pod kartką delegacji nie świeci ani jeden punkt trasy"
            " — trzy rozmiary okna, oba zakresy, dzień bliski i daleki",
            not _brud16, str(_brud16[:4]))

    # ── 2. TO SAMO W POŁOWIE RYSOWANIA TRASY ──────────────────────
    _rozmiar16(1440, 900)
    _okno16.zakres.ustaw_aktywna("ten dzień")
    _brud_anim16 = []
    for _dz16 in (_bliski16, _daleki16):
        for _tryb16 in ("ten dzień", "wszystkie dni"):
            _okno16.zakres.ustaw_aktywna(_tryb16)
            _okno16._wybierz_dzien(_dz16)
            _okno16.ustaw_animacje(False)
            _miel16(4)
            for _t16 in (0.25, 0.5, 0.75):
                _okno16.mapa.ustaw_postep_rysowania(_t16)
                _miel16(3)
                _ile16 = _piksele_trasy16(_kartka16())
                if _ile16:
                    _brud_anim16.append((_dz16, _tryb16, _t16, _ile16))
            _okno16.mapa.ustaw_postep_rysowania(1.0)
            _miel16(2)
    _okno16.zakres.ustaw_aktywna("ten dzień")
    sprawdz("w połowie rysowania trasy pod kartką też nie ma ani jednego punktu"
            " — świecąca głowa nie wjeżdża pod papier",
            not _brud_anim16, str(_brud_anim16[:4]))

    # ── 3. GEOMETRIA: ANI PUNKT POD KARTKĄ, ANI POZA KADREM ───────
    _uciekinierzy16 = []
    for _sz16, _wy16 in ((1040, 660), (1440, 900), (1920, 1080)):
        _rozmiar16(_sz16, _wy16)
        for _tryb16 in ("ten dzień", "wszystkie dni"):
            _okno16.zakres.ustaw_aktywna(_tryb16)
            for _d16 in _w_trasie16:
                _okno16._wybierz_dzien(_d16.data.day)
                _okno16.ustaw_animacje(False)
                _miel16(2)
                _m16 = _okno16.mapa
                _kar16 = _kartka16()
                _pole16 = _m16._pole()
                _geo16 = _m16._geometria()
                _pkt16 = _geo16["pkt_glowna"] + _geo16["pkt_powrot"] + _geo16["probki"]
                _opis16 = "%dx%d %s d%02d" % (_sz16, _wy16, _tryb16, _d16.data.day)
                if any(_kar16.contains(q) for q in _pkt16):
                    _uciekinierzy16.append((_opis16, "pod kartką"))
                if any(not _pole16.contains(q) for q in _pkt16):
                    _uciekinierzy16.append((_opis16, "poza kadrem"))
    _okno16.zakres.ustaw_aktywna("ten dzień")
    sprawdz("żaden punkt narysowanej trasy nie wypada pod kartką ani poza kadrem"
            " — cały miesiąc, trzy rozmiary okna, oba zakresy",
            not _uciekinierzy16, str(_uciekinierzy16[:4]))

    # ── 4. KADR NALEŻY DO RYSOWANEJ DROGI, NIE DO PRZYSTANKÓW ─────
    _rozmiar16(1440, 900)
    _szersze16 = 0
    _poza_obszarem16 = []
    for _d16 in _w_trasie16:
        _okno16._wybierz_dzien(_d16.data.day)
        _okno16.ustaw_animacje(False)
        _miel16(2)
        _m16 = _okno16.mapa
        _droga16 = [p for o in _m16._sciezka_swiata()["odcinki"] for p in o]
        _obszar16 = _QR16(*_m16._obszar_swiata())
        _poza_obszarem16 += [(_d16.data.day, p) for p in _droga16
                             if not _obszar16.contains(_QP16(*p))]
        _stoje16 = [_m16._miasta[n] for n in dict.fromkeys(_d16.trasa)
                    if n in _m16._miasta]
        _szer_drogi16 = max(x for x, _ in _droga16) - min(x for x, _ in _droga16)
        _szer_stoi16 = max(x for x, _ in _stoje16) - min(x for x, _ in _stoje16)
        if _szer_drogi16 > _szer_stoi16 + 1e-6:
            _szersze16 += 1
    sprawdz("kadr obejmuje CAŁY przebieg drogi — objazd i wygięcie też są w kadrze",
            not _poza_obszarem16, str(_poza_obszarem16[:3]))
    sprawdz("i nie jest to sprawdzenie puste: droga bywa szersza niż sami przystankowie",
            _szersze16 > 0, "%d z %d dni" % (_szersze16, len(_w_trasie16)))

    # ── 5. PIGUŁKA I PRZEŁĄCZNIK ZAKRESU TEŻ SĄ ZASŁONAMI ─────────
    _pod_zaslona16 = []
    for _sz16, _wy16 in ((1040, 660), (1440, 900), (1920, 1080)):
        _rozmiar16(_sz16, _wy16)
        for _tryb16 in ("ten dzień", "wszystkie dni"):
            _okno16.zakres.ustaw_aktywna(_tryb16)
            _okno16._wybierz_dzien(_daleki16)
            _okno16.ustaw_animacje(False)
            _miel16(2)
            _m16 = _okno16.mapa
            _strefy16 = list(_m16._zaslony) + [_kartka16()]
            for _e16 in _m16._geometria()["etykiety"]:
                for _z16 in _strefy16:
                    if not _e16["pole"].intersected(_z16).isEmpty():
                        _pod_zaslona16.append(("%dx%d %s" % (_sz16, _wy16, _tryb16),
                                               _e16["napis"]))
    _okno16.zakres.ustaw_aktywna("ten dzień")
    sprawdz("mapa wie o pigułce dnia i o przełączniku zakresu — żadna tabliczka"
            " nie chowa się pod nimi ani pod kartką",
            not _pod_zaslona16, str(_pod_zaslona16[:4]))
    _rozmiar16(1440, 900)
    sprawdz("mapa dostaje prawdziwy prostokąt kartki, a nie zgadywany",
            [round(v) for v in (_okno16.mapa._pole_kartki().x(),
                                _okno16.mapa._pole_kartki().y(),
                                _okno16.mapa._pole_kartki().width(),
                                _okno16.mapa._pole_kartki().height())]
            == [round(v) for v in (_kartka16().x(), _kartka16().y(),
                                   _kartka16().width(), _kartka16().height())],
            "%s wobec %s" % (_okno16.mapa._pole_kartki(), _kartka16()))

    # ── 6. CHOREOGRAFIA: NAJPIERW TRASA, POTEM KARTKA ─────────────
    _okno16.ustaw_animacje(True)
    _okno16._wybierz_dzien(_bliski16)
    _miel16(4)
    _okno16._wybierz_dzien(_daleki16)
    _miel16(3)
    _rysuje16 = _okno16.mapa.rysuje_trase()
    _ustapila16 = _okno16.kartka.obecnosc() < 0.9
    sprawdz("zmiana dnia: trasa rysuje się od nowa, a kartka ustępuje jej miejsca",
            _rysuje16 and _ustapila16,
            "postęp %.2f, kartka %.2f" % (_okno16.mapa.postep_rysowania(),
                                          _okno16.kartka.obecnosc()))
    _kadr_w_ruchu16 = _okno16.mapa._klucz_kadru()
    _okno16.mapa._odslona.dokoncz()
    _miel16(4)
    _wraca16 = _okno16.kartka._obecnosc.cel() >= 0.999
    _okno16.kartka._obecnosc.dokoncz()
    _miel16(3)
    sprawdz("kartka wraca dopiero wtedy, gdy trasa dobiegnie do bazy",
            _wraca16 and _okno16.kartka.obecnosc() >= 0.999,
            "cel %.2f, teraz %.2f" % (_okno16.kartka._obecnosc.cel(),
                                      _okno16.kartka.obecnosc()))
    sprawdz("kadr ani drgnie, kiedy kartka ustępuje i wraca — trasa nie skacze w bok",
            _kadr_w_ruchu16 == _okno16.mapa._klucz_kadru())
    _okno16.ustaw_animacje(False)
    _miel16(3)
    _nitka16 = _okno16.mapa._geometria()["nitka"]
    _kar16 = _kartka16()
    _koniec16 = _nitka16.pointAtPercent(1.0)
    _start16 = _nitka16.pointAtPercent(0.0)
    _przystanki16 = [_okno16.mapa._punkt(n)
                     for n in _okno16.mapa._dzien.przystanki
                     if n in _okno16.mapa._miasta]
    _blisko16 = min(math.hypot(q.x() - _start16.x(), q.y() - _start16.y())
                    for q in _przystanki16) if _przystanki16 else 1e9
    sprawdz("nitka wychodzi z przystanku trasy i dobiega do krawędzi kartki,"
            " ale pod papier już nie wchodzi",
            _blisko16 < 40.0 and not _kar16.contains(_koniec16)
            and _koniec16.x() >= _kar16.left() - 30.0,
            "od przystanku %.1f px, koniec x=%.1f przy krawędzi %.1f"
            % (_blisko16, _koniec16.x(), _kar16.left()))

    # ── 7. PIERWSZE WEJŚCIE DO PROGRAMU ───────────────────────────
    _ciasne16 = [k for k in _klatki16
                 if k["kadr_szer"] < _PM16.UDZIAL_MIN_KADRU * k["szer"] - 0.5
                 or k["kadr_wys"] < _PM16.UDZIAL_MIN_KADRU * k["wys"] - 0.5]
    sprawdz("przy budowie i pokazywaniu okna kadr ani razu nie ściska się"
            " do skrawka przy krawędzi",
            not _ciasne16 and len(_klatki16) > 0,
            "%d klatek, najgorsza %s" % (len(_klatki16), _ciasne16[:1]))
    _zle_wejscie16 = [k for k in _klatki16
                      if k["trasa"] and k["kartka_lewa"] is not None
                      and k["kartka_prawa"] >= k["szer"] - 0.08 * k["szer"]
                      and k["kadr_prawy"] > k["kartka_lewa"] + 0.5]
    sprawdz("mapa dostaje kartkę ZANIM narysuje trasę — żadna klatka nie maluje"
            " trasy w kadrze sięgającym pod papier",
            not _zle_wejscie16, str(_zle_wejscie16[:2]))

    # ── 8. KLIK W KARTKĘ ZWIJA JĄ DO BRZEGU ───────────────────────
    _rozmiar16(1440, 900)
    _okno16._wybierz_dzien(_daleki16)
    _okno16.ustaw_animacje(False)
    _miel16(3)
    _kadr_przed16 = _okno16.mapa._pole().width()

    def _klik_kartki16():
        pkt = _QP16(_okno16.kartka.width() * 0.5, _okno16.kartka.height() * 0.5)
        glob = _okno16.kartka.mapToGlobal(pkt.toPoint()).toPointF()
        _okno16.kartka.mousePressEvent(
            _QME16(_QE16.Type.MouseButtonPress, pkt, glob,
                   _Qt16.MouseButton.LeftButton, _Qt16.MouseButton.LeftButton,
                   _Qt16.KeyboardModifier.NoModifier))
        _okno16.ustaw_animacje(False)
        _miel16(6)

    _klik_kartki16()
    _kadr_po16 = _okno16.mapa._pole().width()
    sprawdz("klik w kartkę zwija ją do paska przy brzegu i oddaje mapie miejsce",
            _okno16.kartka.zwinieta()
            and _okno16.kartka.width() == _PM16.KartkaDelegacji.SZEROKOSC_ZWINIETA
            and _kadr_po16 > _kadr_przed16 * 1.4,
            "kadr %.0f → %.0f px, kartka %d px"
            % (_kadr_przed16, _kadr_po16, _okno16.kartka.width()))
    sprawdz("zwinięta kartka też nie przykrywa trasy — na pikselach",
            _piksele_trasy16(_kartka16()) == 0,
            "%d pikseli" % _piksele_trasy16(_kartka16()))
    sprawdz("zwinięcie kartki jest zapamiętane w ustawieniach programu",
            P.ustawienie(_NW16.OknoNowegoWygladu.USTAWIENIE_KARTKI, False) is True,
            repr(P.ustawienie(_NW16.OknoNowegoWygladu.USTAWIENIE_KARTKI, False)))
    _klik_kartki16()
    sprawdz("drugi klik rozwija kartkę z powrotem, a kadr wraca na swoje miary",
            not _okno16.kartka.zwinieta()
            and abs(_okno16.mapa._pole().width() - _kadr_przed16) < 0.5
            and P.ustawienie(_NW16.OknoNowegoWygladu.USTAWIENIE_KARTKI, True) is False,
            "kadr %.0f wobec %.0f" % (_okno16.mapa._pole().width(), _kadr_przed16))

    # ── 9. TEN SAM DZIEŃ DAJE TEN SAM OBRAZ ───────────────────────
    def _odcisk16():
        """Odcisk obrazu mapy — po nim poznajemy, że dzień wygląda tak samo."""
        obraz = _okno16.mapa.grab().toImage().convertToFormat(_QI16.Format.Format_RGB888)
        return "%08x" % zlib.crc32(same_piksele(obraz))

    _okno16._wybierz_dzien(_daleki16)
    _okno16.ustaw_animacje(False)
    _miel16(3)
    _odcisk_a16 = _odcisk16()
    _okno16._wybierz_dzien(_bliski16)
    _okno16.ustaw_animacje(False)
    _miel16(3)
    _okno16._wybierz_dzien(_daleki16)
    _okno16.ustaw_animacje(False)
    _miel16(3)
    _odcisk_b16 = _odcisk16()
    _okno16.kartka.przelacz_zwiniecie()
    _okno16.ustaw_animacje(False)
    _miel16(4)
    _okno16.kartka.przelacz_zwiniecie()
    _okno16.ustaw_animacje(False)
    _miel16(4)
    _odcisk_c16 = _odcisk16()
    sprawdz("ten sam dzień daje ten sam obraz — po przełączeniu dni i po"
            " zwinięciu oraz rozwinięciu kartki",
            _odcisk_a16 == _odcisk_b16 == _odcisk_c16,
            "%s / %s / %s" % (_odcisk_a16, _odcisk_b16, _odcisk_c16))

    # ── 10. PODZIAŁKA DALEJ MIERZY PRAWDĘ ─────────────────────────
    # Kamera cofa się po to, żeby zmieściła się cała rysowana trasa. Wolno jej
    # to zrobić tylko RÓWNO w obu osiach — inaczej kilometr na wschód znaczyłby
    # na mapie co innego niż kilometr na północ, a podziałka kłamałaby.
    _zle_miary16 = []
    for _sz16, _wy16 in ((1040, 660), (1440, 900), (1920, 1080)):
        _rozmiar16(_sz16, _wy16)
        for _zwin16 in (False, True):
            if _okno16.kartka.zwinieta() != _zwin16:
                _okno16.kartka.przelacz_zwiniecie()
                _okno16.ustaw_animacje(False)
                _miel16(4)
            _m16 = _okno16.mapa
            _ox16, _oy16, _sx16, _sy16 = _m16._obszar_swiata()
            _cx16, _cy16 = _ox16 + _sx16 * 0.5, _oy16 + _sy16 * 0.5
            _r16 = _m16.rzut()
            # tyle pikseli na kilometr liczy podziałka w środku rejonu
            _na_km16 = (_r16.k / max(1.0, _r16.glebokosc(_cx16, _cy16, 0.0))
                        * _m16._jedn_na_km)
            _dl16 = 10.0 * _m16._jedn_na_km
            _px16 = abs(_r16.ekran(_cx16 + _dl16, _cy16, 0.0).x()
                        - _r16.ekran(_cx16 - _dl16, _cy16, 0.0).x())
            _ocena16 = _px16 / max(1e-6, 20.0 * _na_km16)
            if abs(_ocena16 - 1.0) > 0.01:
                _zle_miary16.append((_sz16, _wy16, _zwin16, round(_ocena16, 4)))
    if _okno16.kartka.zwinieta():
        _okno16.kartka.przelacz_zwiniecie()
        _okno16.ustaw_animacje(False)
        _miel16(4)
    sprawdz("po wpasowaniu kamery podziałka dalej mierzy prawdę: dwadzieścia"
            " kilometrów w poprzek kadru ma dokładnie tyle pikseli, ile mówi"
            " — przy każdym rozmiarze okna i przy kartce zwiniętej",
            not _zle_miary16, str(_zle_miary16[:3]))

    _okno16.zamroz()
    _okno16.close()
except Exception as _e16:
    sprawdz("kartka delegacji nigdy nie zasłania trasy", False, repr(_e16))

# ══════════════════════════════════════════════════════════════════
sekcja("17. Okno powitalne i logowanie — nowa oprawa")

# Okno logowania kończy się d.exec(): modalna pętla stałaby, dopóki ktoś go
# nie zamknie. Podmieniamy więc QDialog na wersję, która okno POKAZUJE,
# oddaje je do obejrzenia i wraca. Sieci w testach nie ma — tak samo jak na
# komputerze bez internetu, i dokładnie to chcemy sprawdzić.
_stan17 = {}
try:
    import time as _time17
    import urllib.request as _ur17
    from PyQt6 import QtWidgets as _QW17
    from PyQt6.QtWidgets import (QApplication as _QA17, QLineEdit as _QLE17,
                                 QLabel as _QL17, QPushButton as _QPB17)
    from PyQt6.QtCore import Qt as _Qt17, QEvent as _QE17
    from PyQt6.QtGui import QKeyEvent as _QKE17, QValidator as _QV17
    import okno_logowania as _OL17

    _app17 = _QA17.instance() or _QA17(sys.argv)
    _stan17["dialog"] = _QW17.QDialog
    _stan17["urlopen"] = _ur17.urlopen
    _stan17["zaloguj"] = P.online_zaloguj
    _stan17["historia"] = P.historia_logowan
    _stan17["rozgrzej"] = P._rozgrzej_backend
    _stan17["tlo"] = _OL17.zywe_tlo_wlaczone

    def _bez_sieci17(*a, **k):
        raise OSError("brak sieci (test)")

    _ur17.urlopen = _bez_sieci17

    _ZADANIE17 = {"fn": None}

    class _DialogTestowy17(_stan17["dialog"]):
        def exec(self):
            self.show()
            for _ in range(20):
                _app17.processEvents()
            fn = _ZADANIE17.get("fn")
            if fn is not None:
                fn(self)
                for _ in range(20):
                    _app17.processEvents()
            return self.result()

    _QW17.QDialog = _DialogTestowy17

    def _pole17(okno, nazwa):
        return next((w for w in okno.findChildren(_QLE17)
                     if w.objectName() == nazwa), None)

    def _etyk17(okno, nazwa):
        return [w for w in okno.findChildren(_QL17) if w.objectName() == nazwa]

    def _prz17(okno, nazwa):
        return [w for w in okno.findChildren(_QPB17) if w.objectName() == nazwa]

    def _czekaj17(warunek, sekund=4.0):
        koniec = _time17.time() + sekund
        while not warunek() and _time17.time() < koniec:
            _app17.processEvents()
            _time17.sleep(0.005)
        return warunek()

    _HISTORIA17 = [
        {"kod": "10001", "imie": "Anna Testowa", "ostatnio": "2026-09-12T08:00:00"},
        {"kod": "20002", "imie": "Marek Testowy", "ostatnio": "2026-09-10T08:00:00"},
        {"kod": "30003", "imie": "", "ostatnio": "2026-09-09T08:00:00"},
        {"kod": "40004", "imie": "Ktos Testowy", "ostatnio": "2026-09-08T08:00:00"},
    ]
    P.historia_logowan = lambda limit=3: _HISTORIA17[:limit]
    P._rozgrzej_backend = lambda: None

    # ── 17a. oprawa istnieje i nie wciąga programu w kółko ────────
    sprawdz("oprawa powitania (okno_logowania) wczytuje się",
            P._oprawa_powitania() is _OL17)
    _zrodlo17 = open(os.path.join(KATALOG, "okno_logowania.py"),
                     encoding="utf-8").read()
    sprawdz("oprawa nie wczytuje programu drugi raz (bez importu w kolko)",
            "\nimport PMT_Delegacje" not in _zrodlo17
            and "sys.modules.get(\"PMT_Delegacje\")" in _zrodlo17)

    _zbuduj17 = open(os.path.join(KATALOG, "zbuduj.py"), encoding="utf-8").read()
    sprawdz("oprawa powitania i logo retro wchodzą do paczki PyInstallera",
            '"okno_logowania.py"' in _zbuduj17 and '"logo_retro.py"' in _zbuduj17
            and '"okno_logowania"' in _zbuduj17 and '"logo_retro"' in _zbuduj17)
    _blok17 = open(os.path.join(KATALOG, "PMT_Delegacje.py"),
                   encoding="utf-8").read().split('if __name__ == "__main__":')[1]
    sprawdz("scena powitalna schodzi dopiero, gdy okno programu już stoi",
            "window.show()\n    _zdejmij_kurtyne_powitania()" in _blok17)

    # ── 17b. budowa okna: wszystko na swoim miejscu ───────────────
    def _obejrzyj17(d):
        _flagi = d.windowFlags()
        sprawdz("okno powitalne bez ramy systemowej",
                bool(_flagi & _Qt17.WindowType.FramelessWindowHint))
        sprawdz("okno powitalne ma wpis na pasku zadań (typ Window)",
                (_flagi & _Qt17.WindowType.Window) == _Qt17.WindowType.Window)
        sprawdz("okno powitalne stoi na wierzchu otwartych kart",
                bool(_flagi & _Qt17.WindowType.WindowStaysOnTopHint))
        sprawdz("okno powitalne zajmuje cały ekran, jak okno programu",
                d.isFullScreen(), str(d.size()))
        _tlo = getattr(d, "_tlo_powitania", None)
        sprawdz("scena powitalna to okno_logowania.Tlo",
                isinstance(_tlo, _OL17.Tlo))
        sprawdz("zywa mapa doklada sie DOPIERO po pokazaniu karty",
                _tlo is not None and _tlo.mapa is not None
                and "dolacz_zywe_tlo" in _zrodlo17
                and "_po_pierwszej_klatce" in _zrodlo17)
        sprawdz("mapa w tle rysuje dane POKAZOWE, nie trase zalogowanej osoby",
                "import proto_dane" in _zrodlo17
                and "oblicz_miesiac" in _zrodlo17)
        sprawdz("karta logowania to szkło nowego systemu",
                bool(d.findChildren(_OL17.Karta))
                and d.findChildren(_OL17.Karta)[0].objectName() == "PmtKarta")
        sprawdz("logo retro stoi nad kartą",
                bool(d.findChildren(_OL17.Znak)))
        _k, _h = _pole17(d, "kod"), _pole17(d, "haslo")
        sprawdz("pole LOGIN: pięć znaków, wyśrodkowane",
                _k is not None and _k.maxLength() == 5
                and bool(_k.alignment() & _Qt17.AlignmentFlag.AlignHCenter))
        _wal = _k.validator() if _k is not None else None
        sprawdz("pole LOGIN przyjmuje wyłącznie pięć cyfr",
                _wal is not None
                and _wal.validate("12345", 5)[0] == _QV17.State.Acceptable
                and _wal.validate("ab12x", 5)[0] == _QV17.State.Invalid
                and _wal.validate("123456", 6)[0] == _QV17.State.Invalid)
        sprawdz("pole HASŁO zakryte kropkami",
                _h is not None and _h.echoMode() == _QLE17.EchoMode.Password)
        sprawdz("etykiety LOGIN i HASŁO na miejscu",
                [w.text() for w in _etyk17(d, "etyk")][-2:] == ["LOGIN", "HASŁO"],
                str([w.text() for w in _etyk17(d, "etyk")]))
        sprawdz("rezerwa na komunikat błędu — układ nie skacze",
                bool(_etyk17(d, "blad"))
                and _etyk17(d, "blad")[0].minimumHeight() >= 30)
        sprawdz("w karcie nie ma zdań objaśniających",
                not _etyk17(d, "pod"))
        _rogi = _prz17(d, "chipmin")
        sprawdz("minimalizuj i zamknij w prawym górnym rogu ekranu",
                len(_rogi) == 2
                and all(p.x() > d.width() - 100 and p.y() < 40 for p in _rogi),
                str([(p.text(), p.x(), p.y()) for p in _rogi]))
        _pomoc = _prz17(d, "pomoc")
        sprawdz("zmiana hasła, reset i test połączenia — z podpowiedziami",
                len(_pomoc) == 3 and all(p.toolTip() for p in _pomoc),
                str([p.text() for p in _pomoc]))
        sprawdz("żaden napis pomocy nie jest ucinany",
                all(p.width() >= p.fontMetrics().horizontalAdvance(p.text())
                    for p in _pomoc),
                str([(p.text(), p.width()) for p in _pomoc]))
        sprawdz("historia kont: najwyżej trzy podpowiedzi",
                len(_prz17(d, "chip")) == 3, str(len(_prz17(d, "chip"))))
        _ok = _prz17(d, "ok")[0]
        sprawdz("przycisk Zaloguj startuje wyłączony", not _ok.isEnabled())
        _k.setText("10001"); _h.setText("abc")
        sprawdz("przycisk Zaloguj milczy przy haśle krótszym niż 4 znaki",
                not _ok.isEnabled())
        _h.setText("abcd")
        sprawdz("przycisk Zaloguj budzi się przy 5 cyfrach i 4 znakach",
                _ok.isEnabled())
        _k.setText("100")
        sprawdz("przycisk Zaloguj gaśnie, gdy kod nie ma pięciu cyfr",
                not _ok.isEnabled())
        sprawdz("Enter znaczy Zaloguj, a nie Zmień hasło",
                _ok.isDefault() and not any(p.autoDefault() for p in _pomoc))
        _prz17(d, "chip")[1].click()
        sprawdz("klik konta z historii wstawia kod, CZYŚCI hasło i skacze do niego",
                _pole17(d, "kod").text() == "20002"
                and _pole17(d, "haslo").text() == ""
                and _pole17(d, "haslo").hasFocus())
        d.reject()

    _ZADANIE17["fn"] = _obejrzyj17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("przycisk Zamknij nie wpuszcza nikogo do programu",
            _kod17 is None and _imie17 == "")

    # ── 17c. Esc zamyka okno ──────────────────────────────────────
    def _esc17(d):
        _QA17.sendEvent(d, _QKE17(_QE17.Type.KeyPress, _Qt17.Key.Key_Escape,
                                  _Qt17.KeyboardModifier.NoModifier))

    _ZADANIE17["fn"] = _esc17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("Esc zamyka okno powitalne bez logowania",
            _kod17 is None and _imie17 == "")

    # ── 17d. udane logowanie: karta ustępuje, scena zostaje ───────
    P.online_zaloguj = lambda k, h: (True, "Anna Testowa", "")

    def _zaloguj17(d):
        _pole17(d, "kod").setText("10001")
        _pole17(d, "haslo").setText("dobrehaslo")
        _prz17(d, "ok")[0].click()
        _czekaj17(lambda: d.result() != 0, 5.0)

    _ZADANIE17["fn"] = _zaloguj17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("udane logowanie oddaje kod i imię",
            _kod17 == "10001" and _imie17 == "Anna Testowa",
            str((_kod17, _imie17)))
    sprawdz("po zalogowaniu scena zostaje kurtyną — przejście bez błysku pulpitu",
            _OL17._KURTYNA.get("okno") is not None)
    sprawdz("kurtyna schodzi, gdy okno programu już stoi",
            P._zdejmij_kurtyne_powitania() and _czekaj17(
                lambda: _OL17._KURTYNA.get("okno") is None, 2.0))

    # ── 17e. odmowa serwera ───────────────────────────────────────
    P.online_zaloguj = lambda k, h: (False, "", "Błędne hasło.")

    def _odmowa17(d):
        _pole17(d, "kod").setText("10001")
        _pole17(d, "haslo").setText("zlehaslo")
        _prz17(d, "ok")[0].click()
        _czekaj17(lambda: _etyk17(d, "blad")[0].text().strip() != "", 5.0)
        sprawdz("odmowa serwera pokazana w karcie",
                _etyk17(d, "blad")[0].text() == "Błędne hasło.",
                _etyk17(d, "blad")[0].text())
        sprawdz("po odmowie przycisk wraca do napisu Zaloguj, a pola są czynne",
                _prz17(d, "ok")[0].text() == "Zaloguj"
                and _pole17(d, "kod").isEnabled()
                and _pole17(d, "haslo").isEnabled())
        sprawdz("odmowa nie kasuje wpisanego kodu",
                _pole17(d, "kod").text() == "10001")
        d.reject()

    _ZADANIE17["fn"] = _odmowa17
    P.dialog_logowania()

    # ── 17f. życie podczas weryfikacji ────────────────────────────
    def _wolno17(k, h):
        _time17.sleep(0.5)
        return (False, "", "Błędne hasło.")

    P.online_zaloguj = _wolno17

    def _wtoku17(d):
        _pole17(d, "kod").setText("77777")
        _pole17(d, "haslo").setText("cokolwiek")
        _prz17(d, "ok")[0].click()
        for _ in range(6):
            _app17.processEvents()
        _ok = _prz17(d, "ok")[0]
        sprawdz("podczas weryfikacji przycisk mówi Sprawdzam…",
                _ok.text().startswith("Sprawdzam"), _ok.text())
        sprawdz("ręczna próba blokuje pola i przycisk Zamknij",
                not _pole17(d, "kod").isEnabled()
                and not _pole17(d, "haslo").isEnabled()
                and not [p for p in _prz17(d, "anuluj")
                         if p.text() == "Zamknij"][0].isEnabled())
        _czekaj17(lambda: bool(_ok.styleSheet()), 1.5)
        sprawdz("pasek światła na przycisku w barwach nowego systemu",
                "00F0FF" in _ok.styleSheet().upper()
                and "00E4A1" in _ok.styleSheet().upper(),
                _ok.styleSheet()[:90])
        _czekaj17(lambda: _ok.text() == "Zaloguj", 5.0)
        sprawdz("po weryfikacji okno wraca do stanu wyjściowego",
                _pole17(d, "kod").isEnabled()
                and _pole17(d, "haslo").isEnabled()
                and _ok.styleSheet() == "")
        d.reject()

    _ZADANIE17["fn"] = _wtoku17
    P.dialog_logowania()

    # ── 17g. autologowanie bez Entera ─────────────────────────────
    P.historia_logowan = lambda limit=3: []
    _kodA17, _hasA17 = "55555", "znanehaslo"
    P._zapisz_logowanie(_kodA17, "Jan Testowy", P._hash_hasla(_kodA17, _hasA17))
    _wolania17 = []

    def _licz17(k, h):
        _wolania17.append((k, h))
        return (True, "Jan Testowy", "")

    P.online_zaloguj = _licz17

    def _znane17(d):
        _pole17(d, "kod").setText(_kodA17)
        _pole17(d, "haslo").setText(_hasA17)      # nikt nie naciska Entera
        _czekaj17(lambda: bool(_wolania17), 4.0)
        _czekaj17(lambda: d.result() != 0, 4.0)

    _ZADANIE17["fn"] = _znane17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("hasło znane z poprzedniego logowania wchodzi BEZ Entera",
            _wolania17 == [(_kodA17, _hasA17)] and _kod17 == _kodA17,
            str((_wolania17, _kod17)))
    P._zdejmij_kurtyne_powitania()
    _czekaj17(lambda: _OL17._KURTYNA.get("okno") is None, 2.0)

    _wolania2_17 = []

    def _licz2_17(k, h):
        _wolania2_17.append((k, h))
        return (False, "", "Błędne hasło.")

    P.online_zaloguj = _licz2_17

    def _pauza17(d):
        _pole17(d, "kod").setText("66666")
        _pole17(d, "haslo").setText("nieznanehaslo")
        sprawdz("nieznane hasło nie wychodzi do serwera od razu",
                not _wolania2_17)
        _czekaj17(lambda: bool(_wolania2_17), 4.0)
        sprawdz("nieznane hasło idzie do serwera po pauzie w pisaniu",
                _wolania2_17 == [("66666", "nieznanehaslo")], str(_wolania2_17))
        _czekaj17(lambda: _etyk17(d, "blad")[0].text().strip() != "", 4.0)
        sprawdz("próba automatyczna NIE kasuje wpisanego hasła",
                _pole17(d, "haslo").text() == "nieznanehaslo")
        sprawdz("po próbie automatycznej złe hasło daje tylko łagodną podpowiedź",
                "Dokończ" in _etyk17(d, "blad")[0].text(),
                _etyk17(d, "blad")[0].text())
        d.reject()

    _ZADANIE17["fn"] = _pauza17
    P.dialog_logowania()

    # ── 17h. logowanie BEZ SIECI przez okno ───────────────────────
    P.online_zaloguj = _stan17["zaloguj"]        # prawdziwa droga logowania
    _kodB17, _hasB17 = "91234", "HasloOffline1"
    P._zapisz_logowanie(_kodB17, "Jan Testowy", P._hash_hasla(_kodB17, _hasB17))
    P._zapamietaj_waznosc_konta(
        _kodB17, (datetime.date.today() + datetime.timedelta(days=200)).isoformat())

    def _offline17(d):
        _pole17(d, "kod").setText(_kodB17)
        _pole17(d, "haslo").setText(_hasB17)
        _prz17(d, "ok")[0].click()
        _czekaj17(lambda: d.result() != 0, 6.0)

    _ZADANIE17["fn"] = _offline17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("bez internetu okno wpuszcza po skrócie hasła z tego komputera",
            _kod17 == _kodB17 and _imie17 == "Jan Testowy",
            str((_kod17, _imie17)))
    P._zdejmij_kurtyne_powitania()
    _czekaj17(lambda: _OL17._KURTYNA.get("okno") is None, 2.0)

    def _offline_zle17(d):
        _pole17(d, "kod").setText(_kodB17)
        _pole17(d, "haslo").setText(_hasB17 + "x")
        _prz17(d, "ok")[0].click()
        _czekaj17(lambda: _etyk17(d, "blad")[0].text().strip() != "", 6.0)
        sprawdz("bez internetu złe hasło NIE wchodzi do programu",
                d.result() == 0 and _etyk17(d, "blad")[0].text().strip() != "",
                _etyk17(d, "blad")[0].text())
        d.reject()

    _ZADANIE17["fn"] = _offline_zle17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("bez internetu złe hasło nie oddaje konta", _kod17 is None)

    # pierwszy raz na tym sprzęcie: bez sieci nie ma wejścia
    _kodC17 = "81234"
    def _obcy17(d):
        _pole17(d, "kod").setText(_kodC17)
        _pole17(d, "haslo").setText("cokolwiek1")
        _prz17(d, "ok")[0].click()
        _czekaj17(lambda: _etyk17(d, "blad")[0].text().strip() != "", 6.0)
        sprawdz("pierwsze logowanie na nowym sprzęcie WYMAGA sieci",
                d.result() == 0, _etyk17(d, "blad")[0].text())
        d.reject()

    _ZADANIE17["fn"] = _obcy17
    P.dialog_logowania()

    # przekroczone 45 dni bez sieci — brama się zamyka
    _dane17 = P._wczytaj(P.PLIK_LOGOWAN, {})
    _dane17[_kodB17]["ostatnio"] = (datetime.date.today()
                                    - datetime.timedelta(days=P.OFFLINE_LOGOWANIE_DNI + 5)
                                    ).isoformat() + "T08:00:00"
    P._zapisz(P.PLIK_LOGOWAN, _dane17)

    def _stary17(d):
        _pole17(d, "kod").setText(_kodB17)
        _pole17(d, "haslo").setText(_hasB17)
        _prz17(d, "ok")[0].click()
        _czekaj17(lambda: _etyk17(d, "blad")[0].text().strip() != "", 6.0)
        sprawdz("po %d dniach bez internetu okno nie wpuszcza i mówi dlaczego"
                % P.OFFLINE_LOGOWANIE_DNI,
                d.result() == 0 and "dni" in _etyk17(d, "blad")[0].text(),
                _etyk17(d, "blad")[0].text())
        d.reject()

    _ZADANIE17["fn"] = _stary17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("blokada 45 dni nie oddaje konta", _kod17 is None)

    # ── 17i. wyłączniki żywego tła ────────────────────────────────
    P.online_zaloguj = lambda k, h: (True, "Anna Testowa", "")
    sprawdz("żywe tło domyślnie działa", _OL17.zywe_tlo_wlaczone() is True)
    _stop17 = os.path.join(os.path.expanduser("~"), "BEZ_3D.txt")
    open(_stop17, "w").close()
    sprawdz("BEZ_3D.txt wyłącza żywe tło — ten sam wyłącznik, co reszta głębi",
            _OL17.zywe_tlo_wlaczone() is False)
    os.remove(_stop17)
    P.zapisz_ustawienie(_OL17.USTAWIENIE_TLA, False)
    sprawdz("ustawienie %s wyłącza żywe tło" % _OL17.USTAWIENIE_TLA,
            _OL17.zywe_tlo_wlaczone() is False)
    P.zapisz_ustawienie(_OL17.USTAWIENIE_TLA, True)
    P.zapisz_ustawienie("wyglad_3d", False)
    sprawdz("wyłączona głębia 3D wyłącza też żywe tło",
            _OL17.zywe_tlo_wlaczone() is False)
    P.zapisz_ustawienie("wyglad_3d", True)
    sprawdz("po włączeniu z powrotem żywe tło wraca",
            _OL17.zywe_tlo_wlaczone() is True)

    _OL17.zywe_tlo_wlaczone = lambda: False

    def _bez_tla17(d):
        _tlo = getattr(d, "_tlo_powitania", None)
        sprawdz("przy wyłączonym tle mapa się nie pojawia",
                _tlo is not None and _tlo.mapa is None)
        sprawdz("przy wyłączonym tle karta i logo dalej stoją",
                bool(d.findChildren(_OL17.Karta)))
        _pole17(d, "kod").setText("10001")
        _pole17(d, "haslo").setText("dobrehaslo")
        sprawdz("przy wyłączonym tle logowanie działa tak samo",
                _prz17(d, "ok")[0].isEnabled())
        _prz17(d, "ok")[0].click()
        _czekaj17(lambda: d.result() != 0, 5.0)

    _ZADANIE17["fn"] = _bez_tla17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("bez żywego tła logowanie kończy się wejściem do programu",
            _kod17 == "10001")
    P._zdejmij_kurtyne_powitania()
    _OL17.zywe_tlo_wlaczone = _stan17["tlo"]

    # ── 17j. mapa sama ustępuje, gdy rysuje się za wolno ──────────
    def _wolna17(d):
        _tlo = getattr(d, "_tlo_powitania", None)
        _tlo.mapa.czasy = [_OL17.BUDZET_KLATKI + 5] * _OL17.KLATEK_DO_OCENY
        _tlo._ocen_plynnosc()
        sprawdz("wolne klatki gaszą animację tła, mapa zostaje",
                _tlo.mapa is not None and not _tlo.mapa.animacje_wlaczone())
        _tlo._oceny = 0
        _tlo.mapa.czasy = [_OL17.BUDZET_KRYTYCZNY + 50] * _OL17.KLATEK_DO_OCENY
        _tlo._ocen_plynnosc()
        sprawdz("przy naprawdę wolnym rysowaniu mapa znika sama",
                _tlo.mapa is None and _tlo.zaslona is None)
        sprawdz("po zdjęciu mapy karta logowania dalej stoi",
                bool(d.findChildren(_OL17.Karta)))
        d.reject()

    _ZADANIE17["fn"] = _wolna17
    P.dialog_logowania()

    # ── 17k. brak nowej oprawy = stare okno, ta sama kontrola dostępu ──
    P._OPRAWA_POWITANIA["modul"] = None          # tak wygląda stara paczka
    P.historia_logowan = lambda limit=3: _HISTORIA17[:limit]
    P.online_zaloguj = lambda k, h: (True, "Anna Testowa", "")

    def _stara17(d):
        sprawdz("bez nowej oprawy okno logowania nadal staje",
                bool(_pole17(d, "kod")) and bool(_pole17(d, "haslo"))
                and bool(_prz17(d, "ok")))
        sprawdz("stara oprawa ma swój rozmiar i nie jest na pełnym ekranie",
                not d.isFullScreen() and d.width() == 470 and d.height() == 410,
                str(d.size()))
        sprawdz("stara oprawa też jest bez ramy systemowej",
                bool(d.windowFlags() & _Qt17.WindowType.FramelessWindowHint))
        _pole17(d, "kod").setText("10001")
        _pole17(d, "haslo").setText("dobrehaslo")
        _prz17(d, "ok")[0].click()
        _czekaj17(lambda: d.result() != 0, 5.0)

    _ZADANIE17["fn"] = _stara17
    _kod17, _imie17 = P.dialog_logowania()
    sprawdz("bez nowej oprawy logowanie kończy się tak samo",
            _kod17 == "10001" and _imie17 == "Anna Testowa",
            str((_kod17, _imie17)))
    P._OPRAWA_POWITANIA.pop("modul", None)
    sprawdz("po przywróceniu oprawa wraca", P._oprawa_powitania() is _OL17)

except Exception as _e17:
    sprawdz("okno powitalne i logowanie działa", False, repr(_e17))
finally:
    try:
        if "dialog" in _stan17:
            _QW17.QDialog = _stan17["dialog"]
            _ur17.urlopen = _stan17["urlopen"]
            P.online_zaloguj = _stan17["zaloguj"]
            P.historia_logowan = _stan17["historia"]
            P._rozgrzej_backend = _stan17["rozgrzej"]
            _OL17.zywe_tlo_wlaczone = _stan17["tlo"]
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════
sekcja("18. Warstwa WOW: da się ją zgasić, a zgaszona nie zostawia śladu")

try:
    from PyQt6.QtWidgets import QApplication as _QA18, QLabel as _QL18
    from PyQt6.QtWidgets import QVBoxLayout as _QV18, QWidget as _QW18
    from PyQt6.QtGui import QImage as _QIM18
    import nowy_wyglad as _NW18
    import proto_okno as _OK18
    import proto_mapa as _PM18
    import proto_tasma as _PT18
    import proto_kompas as _PK18
    _app18 = _QA18.instance() or _QA18(sys.argv)
    _app18.setStyleSheet(_NW18.arkusz())

    _okno18 = _NW18.OknoNowegoWygladu(
        profil=_NW18.ProfilWidoku("Jan Testowy", "85010112345",
                                  "ul. Kwiatowa 5, 26-600 Radom", "KR"),
        rok=2026, miesiac=10)
    _okno18.showNormal()
    _okno18.setMinimumSize(900, 600)
    _okno18.resize(1920, 1080)

    def _miel18(ile=8):
        for _ in range(ile):
            _app18.processEvents()

    _miel18(20)
    _mapa18 = _okno18.mapa
    _tasma18 = _okno18.tasma
    _kompas18 = _okno18.k_kompas.kompas

    def _bajty18(widzet):
        """Zrzut widżetu jako surowe bajty — do porównań co do bajta.

        Bez dopychania wierszy (same_piksele): inaczej porównywalibyśmy
        pamięć, której nikt nie zapisał, i sprawdzenie padałoby zależnie od
        rozmiaru okna, a nie od tego, czy coś się rusza."""
        obraz = widzet.grab().toImage().convertToFormat(_QIM18.Format.Format_RGB888)
        return same_piksele(obraz)

    # ── 18a. wyłącznik gasi KAŻDY nowy efekt ─────────────────────────
    _okno18.ustaw_animacje(False)
    _miel18(6)
    sprawdz("zgaszone animacje: mapa nie ma czym żyć (zegar życia na zerze)",
            _mapa18._czas_zycia == 0.0 and not _mapa18.animacje_wlaczone(),
            str(_mapa18._czas_zycia))
    sprawdz("zgaszone animacje: taśma nie pokazuje pracy silnika",
            _tasma18.praca() is None)
    sprawdz("zgaszone animacje: igła kompasu stoi (zero stopni na sekundę)",
            _kompas18.obrot_igly() == 0.0, str(_kompas18.obrot_igly()))
    sprawdz("zgaszone animacje: żaden panel nie wyrasta",
            _okno18._wyrastanie is None or not _okno18._wyrastanie.gra())
    sprawdz("zgaszone animacje: mapa nie ściszyła się sama (nie ma czego ściszać)",
            not _mapa18.efekty_ciche())
    _zegary18 = [z for z in (_mapa18._zegar, _tasma18._zegar, _kompas18._zegar)
                 if z.isActive()]
    sprawdz("zgaszone animacje: żaden zegar ruchu już nie chodzi",
            not _zegary18, str(len(_zegary18)))

    # ── 18b. zgaszenie przywraca DOKŁADNIE stary obraz ───────────────
    _spokoj18 = _bajty18(_mapa18)
    _mapa18.ustaw_animacje(True)
    _mapa18._czas_zycia = 9000.0            # chwila, w której życie na pewno widać
    _mapa18._faza = 0.30
    _mapa18.repaint()
    _zycie18 = _bajty18(_mapa18)
    sprawdz("włączone życie mapy naprawdę coś zmienia na ekranie",
            _zycie18 != _spokoj18)
    _mapa18.ustaw_animacje(False)
    _miel18(4)
    sprawdz("zgaszenie przywraca obraz sprzed warstwy WOW — co do bajta",
            _bajty18(_mapa18) == _spokoj18)

    # ...a mapa ŚCISZONA SAMA (bo klatka się nie mieściła) ma przestać żyć:
    # zegar życia może iść dalej, a na ekranie nie zmienia się nic. Blask
    # trasy i płynące kreski powrotu to nie jest warstwa WOW — te chodziły
    # przed nią i chodzą dalej, bo kosztują ułamek klatki.
    _mapa18.ustaw_animacje(True)
    _mapa18._odslona.zatrzymaj()
    _mapa18._odslona.ustaw(1.0)
    _mapa18._odslonieta = _mapa18._klucz_trasy()
    _mapa18._faza = _PM18.MapaDnia.FAZA_ZRZUTU
    _mapa18._ciche = True
    _mapa18._czas_zycia = 1000.0
    _mapa18.repaint()
    _cicha_a18 = _bajty18(_mapa18)
    _mapa18._czas_zycia = 12000.0
    _mapa18.repaint()
    sprawdz("ściszona mapa stoi, choć zegar życia idzie dalej",
            _bajty18(_mapa18) == _cicha_a18)
    _mapa18._ciche = False
    _mapa18.repaint()
    sprawdz("...a ta sama chwila z życiem wygląda już inaczej",
            _bajty18(_mapa18) != _cicha_a18)
    _mapa18._koszt_klatki = 0.0
    _mapa18._pod_rzad = 0
    _mapa18.ustaw_animacje(False)
    _miel18(4)

    # ── 18c. powtarzalność zrzutów ───────────────────────────────────
    _mapa18.ustaw_animacje(False)
    _a18 = _bajty18(_mapa18)
    _miel18(10)
    _b18 = _bajty18(_mapa18)
    sprawdz("przy zgaszonych animacjach dwa zrzuty mapy są identyczne",
            _a18 == _b18)
    _okno18.ustaw_animacje(True)
    _miel18(10)
    _okno18.ustaw_animacje(False)
    _miel18(6)
    sprawdz("zrzut jest ten sam także po włączeniu i zgaszeniu animacji",
            _bajty18(_mapa18) == _a18)
    _tasma_a18 = _bajty18(_tasma18)
    _tasma18.ustaw_prace(0.5)               # praca silnika przy zgaszonych ruchach
    _miel18(4)
    sprawdz("zgaszona taśma nie daje się rozświetlić pracą silnika",
            _bajty18(_tasma18) == _tasma_a18 and _tasma18.praca() is None)

    # ── 18d. budżet klatki przy 1920x1080 ────────────────────────────
    _okno18.ustaw_animacje(True)
    _miel18(10)

    def _klatka18(widzet, ile=25):
        from PyQt6.QtGui import QPixmap as _QPX18
        px = _QPX18(widzet.size())
        for _ in range(5):
            widzet.render(px)
        czasy = []
        for _ in range(ile):
            if widzet is _mapa18:
                _mapa18._tik()
            t0 = time.perf_counter()
            widzet.render(px)
            czasy.append((time.perf_counter() - t0) * 1000.0)
        czasy.sort()
        return czasy[len(czasy) // 2]

    _mapa18.odnotuj_klatke = lambda _ms: None
    try:
        _ms_mapy18 = _klatka18(_mapa18)
        _ms_okna18 = _klatka18(_okno18, ile=6)
    finally:
        del _mapa18.odnotuj_klatke
    print("      klatka mapy %.2f ms (%dx%d), całe okno %.2f ms (%dx%d)"
          % (_ms_mapy18, _mapa18.width(), _mapa18.height(),
             _ms_okna18, _okno18.width(), _okno18.height()))
    sprawdz("klatka mapy przy 1920x1080 mieści się w suficie 16 ms",
            _ms_mapy18 <= _PM18.SUFIT_KLATKI_MS, "%.2f ms" % _ms_mapy18)
    # na czas pomiaru wyłączamy samoczynne ściszanie: inaczej mapa w połowie
    # mierzenia sama zapala życie z powrotem i wychodzi z tego bzdura
    _mapa18._ciche = True
    _mapa18.odnotuj_klatke = lambda _ms: None
    try:
        _ms_bez18 = _klatka18(_mapa18)
    finally:
        del _mapa18.odnotuj_klatke
    _mapa18._ciche = False
    print("      z życiem %.2f ms, ściszona %.2f ms — życie kosztuje %.2f ms"
          % (_ms_mapy18, _ms_bez18, _ms_mapy18 - _ms_bez18))
    sprawdz("całe życie na mapie kosztuje mniej niż cztery milisekundy klatki",
            _ms_mapy18 - _ms_bez18 <= 4.0, "%.2f ms" % (_ms_mapy18 - _ms_bez18))
    sprawdz("sufit klatki i próg powrotu zostawiają zapas większy niż koszt efektów",
            _PM18.SUFIT_KLATKI_MS - _PM18.PROG_POWROTU_MS >= 3.0)

    # ── 18e. za wolna klatka sama ścisza efekty ──────────────────────
    _mapa18._koszt_klatki = 0.0
    _mapa18._ciche = False
    _mapa18._pod_rzad = 0
    for _ in range(60):
        _mapa18.odnotuj_klatke(34.0)        # komputer zupełnie nie wyrabia
    sprawdz("klatka ponad sufitem ścisza życie mapy sama, bez pytania",
            _mapa18.efekty_ciche(), "%.1f ms" % _mapa18.koszt_klatki())
    # blask trasy nie jest częścią warstwy WOW i przy zgaszonych animacjach
    # stoi w stałym miejscu — żeby porównać sam brak życia, stawiamy go tam
    for _ in range(60):
        _mapa18.odnotuj_klatke(9.0)         # klatka znowu się mieści
    sprawdz("kiedy klatka znowu się mieści, życie wraca samo",
            not _mapa18.efekty_ciche(), "%.1f ms" % _mapa18.koszt_klatki())
    _mapa18._ciche = False
    _mapa18._koszt_klatki = 0.0
    _mapa18._pod_rzad = 0

    # ── 18f. nic nie miga: każdy ruch trwa sekundy, nie ułamki ───────
    _okresy18 = {"światła na drogach": _PM18.OKRES_DROGI_MS,
                 "połysk rzeki": _PM18.OKRES_RZEKI_MS,
                 "blask trasy": _PM18.MapaDnia.OKRES_BLASKU,
                 "oddech dnia dzisiejszego": _PT18.OKRES_PULSU}
    _szybkie18 = [n for n, ms in _okresy18.items() if ms < 2000.0]
    sprawdz("żaden ruch w tle nie trwa krócej niż dwie sekundy",
            not _szybkie18, str(_szybkie18))
    sprawdz("światła na drogach są cieplejsze od trasy — widać, co jest twoje",
            _PM18.BARWA_SWIATLA_DROGI.red() > _PM18.BARWA_SWIATLA_DROGI.blue())
    sprawdz("świateł na drogach jest garść, a nie rój",
            1 <= _PM18.SWIATEL_DROG <= 8, str(_PM18.SWIATEL_DROG))

    # ── 18g. sekwencja generowania idzie z MELDUNKÓW SILNIKA ─────────
    sprawdz("z meldunku „Klastrowanie GPS (Dzień 3/7)…” wychodzi 3 z 7",
            _NW18.postep_etapu("Klastrowanie GPS (Dzień 3/7)...") == (3, 7))
    sprawdz("z meldunku o plikach PDF wychodzi numer pliku",
            _NW18.postep_etapu("Dokumenty PDF: październik 2026 (2/6)...") == (2, 6))
    sprawdz("meldunek bez liczb nie udaje postępu",
            _NW18.postep_etapu("Układanie tras...") is None)
    sprawdz("meldunek z zerem w mianowniku nie wywraca sekwencji",
            _NW18.postep_etapu("Dziwny (3/0)...") is None)

    _okno18.ustaw_animacje(True)
    _miel18(6)
    _okno18._etap_silnika = "trasy"
    _okno18._praca_dni = None
    _okno18._praca_dokumenty = None
    _widziane18 = []
    for _txt18 in ("Klastrowanie GPS (Dzień 1/8)...",
                   "Klastrowanie GPS (Dzień 4/8)...",
                   "Układanie tras...",
                   "Klastrowanie GPS (Dzień 8/8)..."):
        _okno18._etap_silnika = _NW18.etap_silnika(_txt18)
        _okno18._postep_tasmy(_txt18)
        _widziane18.append(_tasma18.praca())
    sprawdz("taśma zapala dokładnie tyle dni, ile silnik zameldował",
            _widziane18 == [0.125, 0.5, 0.5, 1.0], str(_widziane18))
    sprawdz("taśma nigdy się nie cofa — meldunek bez liczb jej nie gasi",
            all(_widziane18[i] <= _widziane18[i + 1]
                for i in range(len(_widziane18) - 1)))

    _dni18 = _tasma18._dni_z_trasa()
    _tasma18.ustaw_prace(0.0)
    sprawdz("na początku pracy żaden dzień nie jest jeszcze policzony",
            all(_tasma18._stan_pracy(n) < 1.0 for n in _dni18), str(_dni18))
    _tasma18.ustaw_prace(1.0)
    sprawdz("na końcu pracy policzone są wszystkie dni z trasą",
            _dni18 and all(_tasma18._stan_pracy(n) == 1.0 for n in _dni18))
    _tasma18.ustaw_prace(0.5)
    _polowa18 = [_tasma18._stan_pracy(n) for n in _dni18]
    sprawdz("w połowie pracy zapalona jest dokładnie pierwsza połowa dni",
            sum(1 for x in _polowa18 if x == 1.0) == len(_dni18) // 2,
            str(_polowa18))
    sprawdz("dzień bez trasy nigdy nie udaje policzonego",
            all(_tasma18._stan_pracy(d.data.day) is None
                for d in _tasma18.dni if d.wolny or d.postoje == 0))

    _okno18._koniec_sekwencji()
    sprawdz("koniec pracy zdejmuje z taśmy wszystkie ślady postępu",
            _tasma18.praca() is None and _okno18._praca_dni is None)

    # ── 18h. kompas rozpędza się w rytm prawdziwych meldunków ────────
    _kompas18.wznow_animacje()
    _kompas18.ustaw_stan("gotowy")
    _kompas18.ustaw_stan("praca")
    _kompas18.ustaw_postep(0.05)
    _wolno18 = _kompas18._obrot_cel
    _kompas18._postep_czas = time.monotonic() - 4.0      # meldunki rzadkie
    _kompas18.ustaw_postep(0.10)
    _rzadko18 = _kompas18._obrot_cel
    _kompas18._postep_czas = time.monotonic() - 0.05     # meldunki gęste
    _kompas18.ustaw_postep(0.40)
    _gesto18 = _kompas18._obrot_cel
    sprawdz("igła kręci się szybciej, kiedy silnik melduje gęściej",
            _gesto18 > _rzadko18, "%.0f vs %.0f" % (_gesto18, _rzadko18))
    sprawdz("przy rzadkich meldunkach igła zwalnia, ale nie staje",
            _PK18.OBROT_MIN <= _rzadko18 < _PK18.OBROT_MAX,
            "%.0f" % _rzadko18)
    sprawdz("rozpęd igły ma sufit — nie zamienia się w migotanie",
            _gesto18 <= _PK18.OBROT_MAX and _wolno18 > 0.0)
    for _ in range(80):
        _kompas18._tik()
    sprawdz("po chwili pracy igła naprawdę się kręci",
            _kompas18.obrot_igly() > 0.0, "%.0f" % _kompas18.obrot_igly())
    _kompas18.ustaw_stan("sukces")
    for _ in range(120):
        _kompas18._tik()
    sprawdz("po skończonej pracy igła wyhamowuje i wraca na północ",
            _kompas18.obrot_igly() == 0.0
            and abs(_kompas18._azymut_biez - _kompas18.azymut()) < 1.0,
            "%.1f" % _kompas18._azymut_biez)
    _kompas18.zatrzymaj_animacje()
    sprawdz("zgaszony kompas ma igłę nieruchomą",
            _kompas18.obrot_igly() == 0.0)

    # ── 18i. spoczynek: klatek tylko tyle, ile widać ─────────────────
    _kompas18.wznow_animacje()
    _kompas18.ustaw_stan("gotowy")
    _malowania18 = {"ile": 0}
    _stary_up18 = _kompas18.update

    def _liczaca18(*a, **k):
        _malowania18["ile"] += 1
        return _stary_up18(*a, **k)

    _kompas18.update = _liczaca18
    try:
        for _ in range(60):                  # 60 tyknięć = dwie sekundy spoczynku
            _kompas18._tik()
    finally:
        _kompas18.update = _stary_up18
    sprawdz("kompas w spoczynku rysuje się rzadziej, niż tyka",
            _malowania18["ile"] < 40, "%d na 60" % _malowania18["ile"])
    sprawdz("...ale nie zamiera zupełnie — oddech dalej idzie",
            _malowania18["ile"] > 0)

    _tasma18.wznow_animacje()
    _tasma18.ustaw_prace(None)
    _mal_t18 = {"ile": 0}
    _stary_ut18 = _tasma18.update

    def _liczaca_t18(*a, **k):
        _mal_t18["ile"] += 1
        return _stary_ut18(*a, **k)

    _tasma18.update = _liczaca_t18
    try:
        for _ in range(50):                  # 50 tyknięć = dwie sekundy
            _tasma18._tik()
    finally:
        _tasma18.update = _stary_ut18
    sprawdz("taśma w spoczynku też rysuje się rzadziej, niż tyka",
            _mal_t18["ile"] < 34, "%d na 50" % _mal_t18["ile"])

    # ── 18j. panel wyrasta z klikniętej ikony ────────────────────────
    _okno18.ustaw_animacje(True)
    _miel18(6)
    _pole18 = _okno18._pole_ikony(2)
    _ikony18 = _okno18.szyna._pola()
    sprawdz("okno wie, gdzie na szynie leży ikona klikniętego działu",
            _pole18 is not None
            and abs(_pole18.width() - _ikony18[2].width()) < 0.5
            and _pole18.x() >= 0 and _pole18.y() >= 0, str(_pole18))

    _tresc18 = _QW18()
    _ukl18 = _QV18(_tresc18)
    _ukl18.addWidget(_QL18("Plan wizyt"))
    _tresc18._nowy_system = True
    _okno18.pokaz_panel(_tresc18, "Plan wizyt", "", numer=2)
    _rama18 = _okno18.nakladka()
    _ruch18 = _okno18._wyrastanie
    sprawdz("kliknięcie działu zaczyna wyrastanie panelu z ikony",
            _ruch18 is not None and _ruch18.gra())
    sprawdz("panel jest otwarty od pierwszej chwili, a nie dopiero po ruchu",
            _rama18.isVisible() and _tresc18.isVisible()
            and _rama18.panel() is _tresc18)
    sprawdz("ruch startuje z pola ikony i kończy na polu panelu",
            _ruch18._skad == _pole18
            and _ruch18._dokad.width() == _rama18.width(), str(_ruch18._skad))
    _okno18._wyrastanie.przerwij()
    _okno18._po_wyrastaniu()
    _miel18(4)
    sprawdz("po ruchu panel stoi dokładnie tam, gdzie ma stać",
            _rama18.x() == _OK18.SZYNA_W and _rama18.y() == _OK18.PASEK_H
            and _rama18.width() == _okno18.width() - _OK18.SZYNA_W,
            str(_rama18.geometry()))

    _okno18.ustaw_animacje(False)
    _miel18(4)
    _rama18.zamknij()
    _miel18(2)
    _okno18.pokaz_panel(_tresc18, "Plan wizyt", "", numer=2)
    _miel18(2)
    sprawdz("przy zgaszonych animacjach panel staje od razu, bez wyrastania",
            not _okno18._wyrastanie.gra() and _rama18.isVisible()
            and _rama18.x() == _OK18.SZYNA_W)
    _rama18.zamknij()
    _miel18(2)

    # ── 18k. zaczep na intro podczas generowania ─────────────────────
    class _Film18:
        slad = []

        def __init__(self, okno):
            _Film18.slad.append("start")
            self.okno = okno

        def ustaw_postep(self, t):
            _Film18.slad.append("postep")

        def zakoncz(self):
            _Film18.slad.append("koniec")

    sprawdz("bez wstawki intro sekwencja generowania nic o nim nie wie",
            _NW18.OknoNowegoWygladu.INTRO_GENEROWANIA is None)
    _NW18.OknoNowegoWygladu.INTRO_GENEROWANIA = _Film18
    try:
        _okno18.ustaw_animacje(True)
        _okno18._zacznij_intro_generowania()
        _okno18._etap_silnika = "trasy"
        _okno18._postep_tasmy("Klastrowanie GPS (Dzień 2/8)...")
        _okno18._koniec_sekwencji()
    finally:
        _NW18.OknoNowegoWygladu.INTRO_GENEROWANIA = None
    sprawdz("intro dostaje zaczep na starcie, w trakcie i na końcu generowania",
            _Film18.slad == ["start", "postep", "koniec"], str(_Film18.slad))
    _okno18._zacznij_intro_generowania()
    sprawdz("po zdjęciu wstawki zaczep znowu nic nie robi",
            getattr(_okno18, "_intro_generowania", None) is None)

    _okno18.ustaw_animacje(False)
    _okno18.close()

except Exception as _e18:
    sprawdz("warstwa WOW: efekty, wyłącznik i budżet klatki", False, repr(_e18))
    import traceback as _tb18
    _tb18.print_exc()

# ══════════════════════════════════════════════════════════════════
sekcja("19. Scalenie: paczka ma wszystkie pliki, a porównania obrazu mówią prawdę")

# Pięć poprzednich kroków dołożyło nowe moduły i nowe sprawdzenia obrazu.
# Ta sekcja pilnuje dwóch rzeczy, które rozjechały się przy scalaniu i które
# widać dopiero na CAŁOŚCI: (1) plik, o którym wie zbuduj.py, ale o którym
# nie wie repozytorium, nie wejdzie do paczki i program po cichu wróci do
# starego okna logowania; (2) porównanie zrzutu „co do bajta" porównywało
# także dopychanie wierszy, czyli pamięć, której nikt nie zapisał.
try:
    import zbuduj as _ZB19
    from PyQt6.QtWidgets import QApplication as _QA19, QWidget as _QW19
    from PyQt6.QtGui import QImage as _QIM19, QPainter as _QP19, QColor as _QC19

    # ── 19a. każdy plik z listy paczki NAPRAWDĘ leży w repozytorium ──
    _brak19 = [n for n in _ZB19.WYMAGANE
               if not os.path.exists(os.path.join(KATALOG, n))]
    sprawdz("każdy plik z listy WYMAGANE leży na dysku",
            not _brak19, "brakuje: " + ", ".join(_brak19))

    # moduł ukryty bez pliku = PyInstaller zbuduje paczkę, która wywali się
    # dopiero u użytkownika, przy pierwszym imporcie
    _bez_pliku19 = []
    for _m19 in _ZB19.UKRYTE:
        if _m19 in ("winsound",) or _m19.startswith("PyQt6"):
            continue          # moduły systemowe i biblioteczne
        if not (os.path.exists(os.path.join(KATALOG, _m19 + ".py"))
                or os.path.exists(os.path.join(KATALOG, "prototyp", _m19 + ".py"))):
            _bez_pliku19.append(_m19)
    sprawdz("każdy moduł z listy UKRYTE ma swój plik",
            not _bez_pliku19, "bez pliku: " + ", ".join(_bez_pliku19))

    # ── 19b. pliki, które program otwiera, a które NIE są w repozytorium ──
    # (menedzer.txt jest tu świadomie: nazwisko przełożonego nie trafia do
    # repozytorium, dokłada się je przy budowaniu paczki dla zespołu)
    _spis19 = os.popen("cd %s && git ls-files 2>/dev/null"
                       % KATALOG.replace('"', '')).read().split()
    if _spis19:
        _poza19 = [n for n in _ZB19.WYMAGANE if n.replace("\\", "/") not in _spis19]
        sprawdz("każdy plik z listy WYMAGANE jest w repozytorium — inaczej "
                "nie wejdzie do paczki",
                not _poza19, "poza repozytorium: " + ", ".join(_poza19))

    # ── 19c. porównanie obrazu liczy SAME PIKSELE, bez dopychania ──
    _app19 = _QA19.instance() or _QA19(sys.argv)

    def _obraz19(szer, wys, barwa):
        o = _QIM19(szer, wys, _QIM19.Format.Format_RGB888)
        o.fill(_QC19(*barwa))
        return o

    # szerokość 122 px: 122 × 3 = 366, a wiersz ma 368 bajtów — dwa bajty
    # dopychania, których nikt nie zapisał (tyle ma kompas w oknie programu)
    _o19 = _obraz19(122, 40, (10, 20, 30))
    sprawdz("obraz o szerokości niepodzielnej przez 4 NAPRAWDĘ ma dopychanie",
            _o19.bytesPerLine() > _o19.width() * 3,
            "%d bajtów na wiersz wobec %d pikseli"
            % (_o19.bytesPerLine(), _o19.width() * 3))
    sprawdz("same_piksele oddaje dokładnie tyle bajtów, ile jest pikseli",
            len(same_piksele(_o19)) == _o19.width() * 3 * _o19.height(),
            "%d wobec %d" % (len(same_piksele(_o19)),
                             _o19.width() * 3 * _o19.height()))
    sprawdz("dwa jednakowe obrazy dają te same bajty",
            same_piksele(_o19) == same_piksele(_obraz19(122, 40, (10, 20, 30))))
    sprawdz("obraz różniący się JEDNYM pikselem daje inne bajty",
            same_piksele(_o19) != same_piksele(_obraz19(122, 40, (10, 20, 31))))
    # szerokość bez dopychania musi przechodzić tą samą drogą
    _r19 = _obraz19(120, 40, (10, 20, 30))
    sprawdz("obraz bez dopychania też oddaje same piksele",
            _r19.bytesPerLine() == _r19.width() * 3
            and len(same_piksele(_r19)) == _r19.width() * 3 * _r19.height())

except Exception as _e19:
    sprawdz("scalenie: paczka i porównania obrazu", False, repr(_e19))
    import traceback as _tb19
    _tb19.print_exc()

sekcja("20. Baza miejscowości: nic nie ginie po drodze i nic się nie dubluje")

try:
    import collections as _col20

    _surowe20 = sum(len(_v) for _v in P.MIASTA_RAW.values())
    P.zaladuj_baze(52.2297, 21.0122)
    _wczytane20 = sum(len(_v) for _v in P._baza_miast.values())
    sprawdz("każda miejscowość ze źródła dociera do silnika — żadna nie ginie na filtrze",
            _wczytane20 == _surowe20, "%d ze źródła, %d w silniku" % (_surowe20, _wczytane20))
    sprawdz("baza ma co najmniej 1300 miejscowości",
            _wczytane20 >= 1300, str(_wczytane20))

    _nazwy20 = [_m.n for _v in P._baza_miast.values() for _m in _v]
    # "n." w nazwie znaczy "nad" — rozwinięte na "Nowy" dawało miejscowości,
    # których nie ma na mapie Polski
    _zmyslone20 = [_n for _n in _nazwy20
                   if " Nowy " in _n or " Nowa " in _n and _n.split()[-1].endswith("ą")]
    sprawdz("skrót „n.” rozwija się na „nad”, a nie na „Nowy”",
            "Kostrzyn nad Odrą" in _nazwy20 and "Nakło nad Notecią" in _nazwy20
            and "Dobrzyń nad Wisłą" in _nazwy20 and not _zmyslone20,
            str(_zmyslone20[:3]))
    sprawdz("nazwy z długim przymiotnikiem są w bazie w całości",
            all(_n in _nazwy20 for _n in
                ("Piotrków Trybunalski", "Grodzisk Mazowiecki", "Tomaszów Mazowiecki",
                 "Aleksandrów Kujawski", "Ostrów Mazowiecka", "Wysokie Mazowieckie")),
            str([_n for _n in ("Piotrków Trybunalski", "Grodzisk Mazowiecki",
                               "Tomaszów Mazowiecki", "Aleksandrów Kujawski",
                               "Ostrów Mazowiecka", "Wysokie Mazowieckie")
                 if _n not in _nazwy20]))

    # ta sama miejscowość zapisana dwa razy potrafiła trafić do JEDNEJ trasy
    _bliskie20 = []
    for _woj20, _lista20 in P._baza_miast.items():
        for _i20, _a20 in enumerate(_lista20):
            for _b20 in _lista20[_i20 + 1:]:
                if P._rdzen_nazwy(_a20.n) == P._rdzen_nazwy(_b20.n) \
                        and P.oblicz_dystans(_a20.lat, _a20.lng, _b20.lat, _b20.lng) < 12.0:
                    _bliskie20.append((_a20.n, _b20.n))
    sprawdz("żadna miejscowość nie siedzi w bazie dwa razy pod dwiema nazwami",
            not _bliskie20, str(_bliskie20[:3]))

    # najkrótsza możliwa delegacja: droga nigdy krótsza niż linia prosta
    import datetime as _dt20, calendar as _cal20
    _dni20 = [_dt20.date(2026, 10, _d) for _d in range(1, _cal20.monthrange(2026, 10)[1] + 1)
              if _dt20.date(2026, 10, _d).weekday() < 5]
    for _baza20, _la20, _ln20 in (("Radom", 51.40, 21.15), ("Warszawa", 52.2297, 21.0122)):
        _plan20 = P.generuj_trasy(P.MIN_KWOTA, _baza20, _la20, _ln20, "mazowieckie",
                                  _dni20, "90010112345", stawka=1.15)
        _pod20 = [(_e20.skad, _e20.dokad) for _d20 in _plan20 for _e20 in _d20.etapy_surowe
                  if _e20.dystans_rzeczywisty < _e20.d_line * P.MNOZNIK_MIN - 0.01]
        sprawdz("kwota minimalna z bazy %s: żaden odcinek nie jest krótszy niż linia prosta" % _baza20,
                bool(_plan20) and not _pod20, str(_pod20[:2]))
        _powtorki20 = [_n for _n, _k in _col20.Counter(
            _e20.dokad for _d20 in _plan20 for _e20 in _d20.etapy_surowe).items() if _k > 1]
        sprawdz("kwota minimalna z bazy %s: jedna trasa nie odwiedza miejscowości dwa razy" % _baza20,
                len(_powtorki20) <= 1, str(_powtorki20[:3]))

    # ── nazwa MIEŚCI SIĘ w rubryce dokumentu ──────────────────────
    # To był powód, dla którego długie nazwy kiedyś w ogóle wyrzucono z bazy:
    # nie mieściły się w kratce „miejscowość" na poleceniu wyjazdu. Rubryka ma
    # 30 mm przy Arial 8, a fpdf nie przycina tekstu — wyłaził poza kreskę.
    _pdf20 = P.PDFReport()
    _pdf20.add_page()
    _pdf20.set_font("Arial", "", 8)
    _za_szerokie20, _skracane20 = [], []
    for _n20 in sorted({_m20.n for _v20 in P._baza_miast.values() for _m20 in _v20}):
        _t20 = P.nazwa_do_rubryki(_pdf20, _n20, 30.0)
        _w20 = _pdf20.get_string_width(_t20)
        if _w20 > 30.0 - 1.0:
            _za_szerokie20.append((_n20, _t20, round(_w20, 1)))
        if _t20 != _n20:
            _skracane20.append((_n20, _t20))
    sprawdz("każda nazwa z bazy mieści się w rubryce „miejscowość” na dokumencie",
            not _za_szerokie20, str(_za_szerokie20[:3]))
    sprawdz("skracanie idzie przez normalny polski skrót, a nie przez wielokropek",
            all(not _t20.endswith("...") for _n20, _t20 in _skracane20),
            str([x for x in _skracane20 if x[1].endswith("...")][:3]))
    sprawdz("nazwa krótka zostaje nietknięta",
            P.nazwa_do_rubryki(_pdf20, "Otwock", 30.0) == "Otwock"
            and P.nazwa_do_rubryki(_pdf20, "Nowy Dwór Mazowiecki", 30.0) == "Nowy Dwór Maz.")

    # ── dwie miejscowości o tej samej nazwie nie mogą leżeć obok siebie ──
    # (uwaga właściciela: pod Warszawą są dwa Józefowy — od północy i od
    # południa; taka para jest na dokumencie nie do rozróżnienia)
    _sasiedzi20 = []
    _wszystkie20 = [_m20 for _v20 in P._baza_miast.values() for _m20 in _v20]
    for _i20 in range(len(_wszystkie20)):
        for _j20 in range(_i20 + 1, len(_wszystkie20)):
            _a20, _b20 = _wszystkie20[_i20], _wszystkie20[_j20]
            if P._rdzen_nazwy(_a20.n) != P._rdzen_nazwy(_b20.n):
                continue
            _d20 = P.oblicz_dystans(_a20.lat, _a20.lng, _b20.lat, _b20.lng)
            if _d20 < 100.0:
                _sasiedzi20.append((_a20.n, _b20.n, round(_d20)))
    sprawdz("żadne dwie miejscowości o tej samej nazwie nie leżą w zasięgu jednej trasy",
            not _sasiedzi20, str(_sasiedzi20[:3]))

except Exception as _e20:
    sprawdz("baza miejscowości", False, repr(_e20))
    import traceback as _tb20
    _tb20.print_exc()

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
