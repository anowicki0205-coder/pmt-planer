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

        # ── kwota, tryb i limit dnia przeżywają zamknięcie okna ───────
        _okno8c.k_parametry.kwota.ustaw_tekst("2 500")
        _okno8c._przelicz_teraz()
        sprawdz("kwota, tryb pracy i limit dnia idą do ~/.pmt_ustawienia.json",
                abs(float(P.ustawienie(_NW.OknoNowegoWygladu.USTAWIENIE_KWOTY, 0)) - 2500.0) < 0.01
                and P.ustawienie(_NW.OknoNowegoWygladu.USTAWIENIE_TRYBU, "")
                == _okno8c.k_parametry.tryb.aktywna()
                and abs(float(P.ustawienie(_NW.OknoNowegoWygladu.USTAWIENIE_LIMITU, 0))
                        - _okno8c._limit_dnia) < 0.01)
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
    sprawdz("animacja startowa nadal rusza po zalogowaniu",
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
    sprawdz("menu pod inicjałami ma hasło, kartę testera, animację i wylogowanie",
            _pozycje10 == ["Zmień hasło", "Karta testera", "Animacja startowa",
                           "Wyloguj"], str(_pozycje10))
    sprawdz("każda pozycja menu awatara ma podpiętą akcję",
            all(callable(_akcje_menu10.get(a)) for a in _menu10.actions() if a.text()))
    _intro_akcja10 = [a for a in _menu10.actions() if a.text() == "Animacja startowa"][0]
    sprawdz("pozycja „Animacja startowa” pokazuje stan ustawienia bez_intra",
            _intro_akcja10.isChecked() == (not bool(P.ustawienie("bez_intra", False))))
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
