# -*- coding: utf-8 -*-
"""
PMT PLANER — WYSYŁKA PODPISANYCH DOKUMENTÓW

Komplet podpisanych plików idzie na wskazany adres BEZ otwierania klienta
poczty: program łączy się z serwerem poczty wychodzącej skrzynki użytkownika
(port 587 ze STARTTLS albo 465 z SSL) i podaje wiadomość tak, jak zrobiłby to
Outlook czy Thunderbird. Żadnej usługi pośredniej, żadnego konta u dostawcy,
żadnego abonamentu — używamy skrzynki, którą użytkownik i tak ma.

Dlaczego nie „mailto:": schemat mailto (RFC 6068) nie ma pola na załącznik,
więc wysyłka sześciu delegacji tą drogą jest niewykonalna, a nie „trudna".

Port 25 (bez szyfrowania) jest odrzucany — to hasło i dokumenty z PESEL-em
w otwartym tekście. Kontekst TLS zawsze z ssl.create_default_context(),
z weryfikacją certyfikatu i nazwy hosta; nigdy CERT_NONE.

HASŁO DO SKRZYNKI NIE JEST NIGDZIE ZAPISYWANE. Przychodzi w słowniku ustawień,
żyje wyłącznie w pamięci przez czas jednej wysyłki i nie trafia ani do pliku
ustawień, ani do kopii zapasowej, ani do komunikatów błędów (patrz bez_hasla).

Moduł jest samodzielny: wyłącznie biblioteka standardowa (smtplib, ssl, email,
mimetypes), bez PyQt6 i bez importu czegokolwiek z PMT_Delegacje — dzięki temu
nadaje się do wątku roboczego, a w wątku GUI nie wolno robić nic sieciowego.

Samosprawdzenie:   python pmt_wysylka.py
"""

import collections
import datetime
import email.message
import email.policy
import email.utils
import json
import mimetypes
import os
import re
import shutil
import smtplib
import socket
import ssl
import string
import sys
import tempfile
import time
import unicodedata

# --- STAŁE ------------------------------------------------------------------

SZABLON_TEMATU = "Delegacje — {imie} — {miesiac} {rok}"

# Pola do podstawienia w szablonie tematu. Nieznane pole daje pusty ciąg,
# nie wyjątek — literówka użytkownika nie może wysypać wysyłki.
POLA_TEMATU = ("imie", "miesiac", "miesiac_nr", "rok", "liczba", "folder")

# Temat MUSI nieść imię i nazwisko oraz miesiąc i rok. Szablon bez tych pól
# jest odrzucany i wraca wzór domyślny — żadna konfiguracja tego nie usunie.
POLA_KONIECZNE = ("imie", "rok")
POLA_MIESIACA = ("miesiac", "miesiac_nr")

TRESC_WIADOMOSCI = "W załączeniu dokumenty delegacyjne."

LIMIT_ZALACZNIKOW_B = 20 * 1024 * 1024
# Base64 powiększa załącznik o ok. 33%, do tego nagłówki części MIME.
# Liczymy rozmiar PO narzucie, inaczej program przepuści paczkę,
# którą serwer odrzuci.
NARZUT_KODOWANIA = 1.37

LIMIT_CZASU_S = 20
PORTY_SMTP = ((587, "starttls"), (465, "ssl"))
PORT_DOMYSLNY = 587
SZYFROWANIE_DOMYSLNE = "starttls"

NAZWA_MANIFESTU = "manifest_podpisu.json"
PODFOLDER_PODPISU = "Do_podpisu"
PODFOLDER_PODPISANE = "Podpisane"
STATUS_PODPISANY = "podpisany"
STATUS_DO_PODPISU = "do_podpisu"
STATUS_NIEAKTUALNY = "nieaktualny"

ROZSZERZENIA_DOKUMENTOW = (".pdf",)
# Podpis odłączony (XAdES) — sam plik podpisu bez PDF-a jest bezwartościowy,
# a sam PDF jest niepodpisany, więc para leci zawsze razem.
ROZSZERZENIA_PODPISU = (".xades", ".xml", ".sig", ".p7s", ".p7m")
# Sufiksy, po których pmt_podpis rozpoznaje podpisany egzemplarz — TA SAMA
# lista co pmt_podpis.SUFIKSY_PODPISU (testy pilnują zgodności; moduł nie
# importuje pmt_podpis, bo ma zostać samodzielny).
SUFIKSY_PODPISU = ("-podpisany", "_podpisany", "-signed", "_signed", "-sig", "-xades")

MIESIACE = ("styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
            "lipiec", "sierpień", "wrzesień", "październik", "listopad",
            "grudzień")

# Krótkie komunikaty po polsku: co się stało i co zrobić. Bez tłumaczenia
# mechanizmu — w programie nie ma opisów działania.
KOMUNIKATY = {
    "logowanie": "Skrzynka nie przyjęła hasła. Sprawdź login i hasło. "
                 "Przy logowaniu dwuskładnikowym wpisz hasło aplikacji.",
    "polaczenie": "Nie połączyłem się ze skrzynką. Sprawdź internet "
                  "i adres serwera poczty.",
    "certyfikat": "Serwer poczty ma nieprawidłowy certyfikat.",
    "rozmiar": "Załączniki są za duże — serwer ich nie przyjmie.",
    "adres": "Serwer nie przyjął adresu. Sprawdź pisownię.",
    "serwer": "Serwer poczty odrzucił wiadomość.",
    "konfiguracja": "Podaj adres skrzynki, serwer poczty i hasło.",
    "plik": "Nie znalazłem pliku do wysłania.",
    "brak": "Nie ma czego wysłać.",
    "przerwano": "Nic nie zostało wysłane.",
}

Zalaczniki = collections.namedtuple(
    "Zalaczniki", "pliki rozmiar rozmiar_surowy za_duze niepodpisane limit")

WynikWysylki = collections.namedtuple(
    "WynikWysylki", "ok odbiorcy czas sekundy zalacznikow odrzucone komunikat")

WynikProby = collections.namedtuple("WynikProby", "ok rodzaj komunikat sekundy")


class BladWysylki(Exception):
    """Błąd wysyłki przetłumaczony na polski.

    Pole `rodzaj` (logowanie, polaczenie, rozmiar, adres, …) wybiera tekst
    w warstwie GUI; bez niego GUI musiałoby rozpoznawać przyczynę po treści
    komunikatu, a to się zawsze rozjeżdża.
    """

    def __init__(self, rodzaj, komunikat=""):
        self.rodzaj = rodzaj or "serwer"
        self.komunikat = komunikat or KOMUNIKATY.get(self.rodzaj, "Nie udało się wysłać.")
        Exception.__init__(self, self.komunikat)


# --- TEMAT ------------------------------------------------------------------

_ZAMIANY = {"ł": "l", "Ł": "L"}


def _uproszcz(tekst):
    """Tekst bez ogonków, małymi literami — do porównań nazw miesięcy."""
    if not tekst:
        return ""
    tekst = "".join(_ZAMIANY.get(z, z) for z in str(tekst))
    tekst = unicodedata.normalize("NFKD", tekst)
    return "".join(z for z in tekst if not unicodedata.combining(z)).casefold()


class _Pola(dict):
    """Mapa pól tematu: nieznane pole daje pusty ciąg zamiast KeyError."""

    def __missing__(self, klucz):
        return ""


def _pola_szablonu(szablon):
    """Nazwy pól użytych w szablonie; None, gdy szablon jest niepoprawny."""
    try:
        nazwy = set()
        for _, pole, _, _ in string.Formatter().parse(szablon):
            if not pole:
                continue
            pole = str(pole).split(".")[0].split("[")[0].strip()
            if pole:
                nazwy.add(pole)
        return nazwy
    except Exception:
        return None


def szablon_poprawny(szablon):
    """Czy szablon wolno użyć — musi mieć {imie}, {rok} i {miesiac}."""
    if not szablon or not isinstance(szablon, str):
        return False
    nazwy = _pola_szablonu(szablon)
    if nazwy is None:
        return False
    if not all(p in nazwy for p in POLA_KONIECZNE):
        return False
    return any(p in nazwy for p in POLA_MIESIACA)


def rozbij_miesiac(miesiac):
    """(nazwa słowna, numer dwucyfrowo) dla liczby albo nazwy miesiąca."""
    if miesiac is None:
        return ("", "")
    if isinstance(miesiac, bool):
        return ("", "")
    numer = None
    if isinstance(miesiac, (int, float)):
        numer = int(miesiac)
    else:
        tekst = str(miesiac).strip()
        if not tekst:
            return ("", "")
        if tekst.isdigit():
            numer = int(tekst)
        else:
            klucz = _uproszcz(tekst)
            for i, nazwa in enumerate(MIESIACE):
                if _uproszcz(nazwa) == klucz:
                    return (nazwa, "%02d" % (i + 1))
            return (tekst, "")
    if numer and 1 <= numer <= 12:
        return (MIESIACE[numer - 1], "%02d" % numer)
    return ("", "")


def _sprzataj(temat):
    """Usuwa ślady po pustych polach: podwójne spacje i osierocone myślniki."""
    temat = " ".join(str(temat or "").split())
    temat = re.sub(r"(?:[—–-]\s*){2,}", "— ", temat)
    return temat.strip(" —–-").strip()


def temat_wiadomosci(imie, miesiac, rok, szablon=None, liczba=None):
    """Temat wiadomości — JEDYNE miejsce, które go składa.

    Szablon użytkownika wchodzi tylko wtedy, gdy zawiera {imie}, {rok}
    i {miesiac} (albo {miesiac_nr}); w przeciwnym razie wraca wzór domyślny.
    Nieznane pole w szablonie daje pusty ciąg, nie wyjątek.
    """
    nazwa_m, numer_m = rozbij_miesiac(miesiac)
    pola = _Pola({
        "imie": ("" if imie is None else str(imie)).strip(),
        "miesiac": nazwa_m,
        "miesiac_nr": numer_m,
        "rok": ("" if rok is None else str(rok)).strip(),
        "liczba": ("" if liczba is None else str(liczba)),
        "folder": "",
    })
    wzor = szablon if szablon_poprawny(szablon) else SZABLON_TEMATU
    try:
        temat = _sprzataj(wzor.format_map(pola))
    except Exception:
        temat = ""
    if not temat:
        try:
            temat = _sprzataj(SZABLON_TEMATU.format_map(pola))
        except Exception:
            temat = ""
    return temat or "Delegacje"


# --- ADRESY -----------------------------------------------------------------

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+$")


def waliduj_email(adres):
    """Zgrubna kontrola adresu: jedna @, kropka w domenie, bez spacji.

    Świadomie zgrubna — pełna zgodność z RFC 5322 to wyrażenie na kilka
    linijek, które i tak nie sprawdzi, czy skrzynka istnieje. Ostatecznie
    adres weryfikuje serwer.
    """
    if not adres or not isinstance(adres, str):
        return False
    adres = adres.strip()
    if not adres or len(adres) > 254:
        return False
    if not _RE_EMAIL.match(adres):
        return False
    if any(z.isspace() for z in adres):
        return False
    try:
        adres.encode("ascii")
    except UnicodeEncodeError:
        return False
    domena = adres.split("@")[1]
    if "." not in domena or domena.startswith(".") or domena.endswith("."):
        return False
    if ".." in adres:
        return False
    return len(domena.rsplit(".", 1)[-1]) >= 2


def lista_adresow(zrodlo):
    """Adresy z tekstu (przecinki, średniki) albo z listy — bez powtórzeń."""
    if not zrodlo:
        return []
    if isinstance(zrodlo, str):
        czesci = re.split(r"[,;]", zrodlo)
    else:
        czesci = []
        for element in zrodlo:
            czesci.extend(re.split(r"[,;]", str(element or "")))
    wynik = []
    widziane = set()
    for czesc in czesci:
        czesc = czesc.strip()
        if czesc and czesc.casefold() not in widziane:
            widziane.add(czesc.casefold())
            wynik.append(czesc)
    return wynik


# --- ZAŁĄCZNIKI -------------------------------------------------------------


def _dokument(nazwa):
    return os.path.splitext(nazwa)[1].casefold() in ROZSZERZENIA_DOKUMENTOW


def _podpis(nazwa):
    return os.path.splitext(nazwa)[1].casefold() in ROZSZERZENIA_PODPISU


def _katalogi_szukania(folder):
    """Miejsca, w których mogą leżeć pliki paczki — od najbardziej wprost."""
    katalogi = [folder,
                os.path.join(folder, PODFOLDER_PODPISANE),
                os.path.join(folder, PODFOLDER_PODPISU),
                os.path.join(folder, PODFOLDER_PODPISU, PODFOLDER_PODPISANE)]
    if os.path.basename(folder.rstrip(os.sep)).casefold() == PODFOLDER_PODPISANE.casefold():
        katalogi.append(os.path.dirname(folder.rstrip(os.sep)))
    return [k for k in katalogi if os.path.isdir(k)]


def _rozwin(wartosc, katalogi):
    """Ścieżka wpisu manifestu → istniejący plik na dysku albo None."""
    if not wartosc:
        return None
    wartosc = str(wartosc)
    if os.path.isabs(wartosc) and os.path.isfile(wartosc):
        return wartosc
    nazwa = os.path.basename(wartosc.replace("\\", "/"))
    for katalog in katalogi:
        sciezka = os.path.join(katalog, nazwa)
        if os.path.isfile(sciezka):
            return sciezka
    return None


def _pary_podpisu(sciezka):
    """Pliki podpisu odłączonego leżące obok dokumentu (ten sam rdzeń nazwy)."""
    katalog = os.path.dirname(sciezka)
    rdzen = os.path.splitext(os.path.basename(sciezka))[0].casefold()
    wynik = []
    try:
        for nazwa in sorted(os.listdir(katalog)):
            if not _podpis(nazwa):
                continue
            if os.path.splitext(nazwa)[0].casefold() == rdzen:
                wynik.append(os.path.join(katalog, nazwa))
    except OSError:
        pass
    return wynik


def wczytaj_manifest(folder):
    """Manifest paczki (dane, katalog manifestu) albo (None, "")."""
    if not folder:
        return (None, "")
    kandydaci = [os.path.join(folder, NAZWA_MANIFESTU),
                 os.path.join(folder, PODFOLDER_PODPISU, NAZWA_MANIFESTU),
                 os.path.join(os.path.dirname(folder.rstrip(os.sep)), NAZWA_MANIFESTU)]
    for sciezka in kandydaci:
        if not os.path.isfile(sciezka):
            continue
        try:
            with open(sciezka, encoding="utf-8") as f:
                dane = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(dane, dict):
            return (dane, os.path.dirname(sciezka))
    return (None, "")


def _szukaj_podpisanego(nazwa_zrodla, katalogi):
    """Podpisany egzemplarz w podfolderze Podpisane, po rdzeniu nazwy źródła."""
    if not nazwa_zrodla:
        return None
    rdzen = os.path.splitext(os.path.basename(
        str(nazwa_zrodla).replace("\\", "/")))[0].casefold()
    if not rdzen:
        return None
    for katalog in katalogi:
        if os.path.basename(katalog.rstrip(os.sep)).casefold() != PODFOLDER_PODPISANE.casefold():
            continue
        try:
            nazwy = sorted(os.listdir(katalog))
        except OSError:
            continue
        for nazwa in nazwy:
            if not _dokument(nazwa):
                continue
            if os.path.splitext(nazwa)[0].casefold().startswith(rdzen):
                sciezka = os.path.join(katalog, nazwa)
                if os.path.isfile(sciezka):
                    return sciezka
    return None


def _z_manifestu(dane, katalogi, tylko_podpisane):
    """(lista plików, ile niepodpisanych) wg reguł paczki podpisowej."""
    pliki = []
    niepodpisane = 0
    wpisy = dane.get("pliki")
    if not isinstance(wpisy, list):
        return (pliki, niepodpisane)
    for wpis in wpisy:
        if not isinstance(wpis, dict):
            continue
        status = str(wpis.get("status") or "").strip().casefold()
        if status == STATUS_NIEAKTUALNY:
            continue                      # dokument z poprzedniej generacji
        if status == STATUS_PODPISANY:
            sciezka = _rozwin(wpis.get("podpisany_plik"), katalogi)
            if sciezka is None:
                # Wpis mówi „podpisany", ale nie wskazuje pliku. Szukamy
                # egzemplarza w Podpisane po rdzeniu nazwy — NIGDY nie
                # podstawiamy w to miejsce kopii niepodpisanej, bo do kadr
                # poszedłby dokument bez podpisu opisany jako podpisany.
                sciezka = _szukaj_podpisanego(wpis.get("plik")
                                              or wpis.get("plik_zrodlowy"), katalogi)
            if sciezka:
                pliki.append(sciezka)
                for pole in ("podpis_plik", "plik_podpisu", "podpis"):
                    towarzysz = _rozwin(wpis.get(pole), katalogi)
                    if towarzysz:
                        pliki.append(towarzysz)
                pliki.extend(_pary_podpisu(sciezka))
                continue
            status = STATUS_DO_PODPISU      # nie ma czego wysłać jako podpisane
        niepodpisane += 1
        if not tylko_podpisane:
            sciezka = _rozwin(wpis.get("plik"), katalogi)
            if sciezka is None:
                sciezka = _rozwin(wpis.get("plik_zrodlowy"), katalogi)
            if sciezka:
                pliki.append(sciezka)
    return (pliki, niepodpisane)


def _rdzen(nazwa):
    """Rdzeń nazwy do porównań — jak _normalizuj w pmt_podpis: bez ogonków,
    małymi literami, tylko litery i cyfry."""
    rdzen = os.path.splitext(os.path.basename(str(nazwa or "")))[0]
    return "".join(z for z in _uproszcz(rdzen) if z.isalnum())


def _podpisany_po_nazwie(sciezka):
    """Dokument poza podfolderem Podpisane uchodzi za podpisany tylko wtedy,
    gdy rozpoznałby go tak pmt_podpis: nazwa niesie sufiks podpisu
    („-podpisany", „_signed", …) albo obok leży plik podpisu odłączonego
    o tym samym rdzeniu."""
    plaska = _uproszcz(os.path.splitext(os.path.basename(sciezka))[0])
    if any(s in plaska for s in SUFIKSY_PODPISU):
        return True
    return bool(_pary_podpisu(sciezka))


def _ze_skanu(folder, tylko_podpisane):
    """Bez manifestu: podpisany jest egzemplarz z podfolderu Podpisane, a poza
    nim dokument, który pmt_podpis rozpoznałby po nazwie (_podpisany_po_nazwie).
    Każdy inny dokument z folderu to dokument BEZ podpisu: liczy się do
    `niepodpisane` i leci wyłącznie przy tylko_podpisane=False.

    Dotąd bez podfolderu Podpisane cały folder leciał niezależnie od
    przełącznika, a licznik stał na zerze — „tylko podpisane" nic nie
    filtrowało. Folder, który SAM jest podfolderem Podpisane, ma same
    egzemplarze podpisane."""
    pliki = []
    niepodpisane = 0
    podpisane = ""
    for kandydat in (os.path.join(folder, PODFOLDER_PODPISANE),
                     os.path.join(folder, PODFOLDER_PODPISU, PODFOLDER_PODPISANE)):
        if os.path.isdir(kandydat):
            podpisane = kandydat
            break
    sam_podpisane = (os.path.basename(folder.rstrip("\\/")).casefold()
                     == PODFOLDER_PODPISANE.casefold())
    rdzenie_podpisanych = []
    if podpisane:
        try:
            nazwy = sorted(os.listdir(podpisane))
        except OSError:
            nazwy = []
        for nazwa in nazwy:
            sciezka = os.path.join(podpisane, nazwa)
            if os.path.isfile(sciezka) and (_dokument(nazwa) or _podpis(nazwa)):
                pliki.append(sciezka)
                rdzenie_podpisanych.append(_rdzen(nazwa))
    try:
        nazwy = sorted(os.listdir(folder))
    except OSError:
        nazwy = []
    for nazwa in nazwy:
        sciezka = os.path.join(folder, nazwa)
        if not os.path.isfile(sciezka) or not _dokument(nazwa):
            continue
        rdzen = _rdzen(nazwa)
        # podpisany egzemplarz tego dokumentu już leży w Podpisane — jak
        # w pmt_podpis: rdzeń oryginału zawiera się w nazwie podpisanego
        if rdzen and any(rdzen in r for r in rdzenie_podpisanych):
            continue
        if sam_podpisane or _podpisany_po_nazwie(sciezka):
            pliki.append(sciezka)
            pliki.extend(_pary_podpisu(sciezka))
            continue
        niepodpisane += 1
        if not tylko_podpisane:
            pliki.append(sciezka)
    return (pliki, niepodpisane)


def zalaczniki(folder, tylko_podpisane=True, limit_bajtow=LIMIT_ZALACZNIKOW_B):
    """Pliki do wysłania z paczki `folder`.

    Zwraca krotkę nazwaną: pliki, rozmiar (PO narzucie kodowania),
    rozmiar_surowy, za_duze (czy próg przekroczony), niepodpisane, limit.

    Domyślnie lecą wyłącznie dokumenty podpisane: wpisy manifestu ze statusem
    `podpisany` (wraz z plikiem podpisu odłączonego), a bez manifestu —
    zawartość podfolderu Podpisane i dokumenty, które pmt_podpis rozpoznałby
    po nazwie jako podpisane. Wpisy `nieaktualny` nie lecą nigdy. Dokument
    bez podpisu liczy się w `niepodpisane` i leci tylko przy
    tylko_podpisane=False — także wtedy, gdy nie ma ani manifestu, ani
    podfolderu Podpisane.
    """
    folder = str(folder or "")
    limit = int(limit_bajtow or 0)
    if not folder or not os.path.isdir(folder):
        return Zalaczniki([], 0, 0, False, 0, limit)
    dane, katalog_manifestu = wczytaj_manifest(folder)
    katalogi = _katalogi_szukania(folder)
    if katalog_manifestu and os.path.isdir(katalog_manifestu):
        for dodatkowy in (os.path.join(katalog_manifestu, PODFOLDER_PODPISANE),
                          katalog_manifestu):
            if os.path.isdir(dodatkowy) and dodatkowy not in katalogi:
                katalogi.insert(0, dodatkowy)
    if dane is not None:
        pliki, niepodpisane = _z_manifestu(dane, katalogi, tylko_podpisane)
    else:
        pliki, niepodpisane = _ze_skanu(folder, tylko_podpisane)

    wybrane = []
    widziane = set()
    surowy = 0
    for sciezka in pliki:
        klucz = os.path.normcase(os.path.abspath(sciezka))
        if klucz in widziane or not os.path.isfile(sciezka):
            continue
        widziane.add(klucz)
        wybrane.append(sciezka)
        try:
            surowy += os.path.getsize(sciezka)
        except OSError:
            pass
    rozmiar = int(surowy * NARZUT_KODOWANIA)
    za_duze = bool(limit > 0 and rozmiar > limit)
    return Zalaczniki(wybrane, rozmiar, surowy, za_duze, niepodpisane, limit)


def rozmiar_po_ludzku(bajty):
    """„12,3 MB" — do komunikatu o przekroczonym rozmiarze."""
    try:
        bajty = float(bajty)
    except (TypeError, ValueError):
        return "0 B"
    if bajty < 1024:
        return "%d B" % int(bajty)
    if bajty < 1024 * 1024:
        return ("%.1f kB" % (bajty / 1024)).replace(".", ",")
    return ("%.1f MB" % (bajty / (1024 * 1024))).replace(".", ",")


# --- WIADOMOŚĆ --------------------------------------------------------------


def _typ_zalacznika(sciezka):
    """(maintype, subtype) dla pliku — domyślnie application/octet-stream."""
    typ, _ = mimetypes.guess_type(sciezka)
    if not typ or "/" not in typ:
        return ("application", "octet-stream")
    glowny, podtyp = typ.split("/", 1)
    if glowny == "text":
        # Załączniki dokładamy bajtowo (podpis musi zostać bit w bit),
        # więc nie oddajemy ich obsłudze tekstu.
        return ("application", podtyp if podtyp == "xml" else "octet-stream")
    return (glowny, podtyp)


def zbuduj_wiadomosc(nadawca, odbiorcy, temat, pliki, dw=None):
    """Wiadomość z załącznikami — EmailMessage z polityką SMTP.

    Kodowanie nagłówka robi biblioteka, więc polskie znaki w temacie
    zakodują się same (RFC 2047) i nie trzeba niczego uciekać ręcznie.
    """
    nadawca = str(nadawca or "").strip()
    if not waliduj_email(nadawca):
        raise BladWysylki("adres", "Sprawdź adres %s — brakuje w nim znaku @ "
                                   "albo nazwy domeny." % (nadawca or "nadawcy"))
    do = lista_adresow(odbiorcy)
    kopia = lista_adresow(dw)
    if not do:
        raise BladWysylki("adres", "Podaj adres odbiorcy.")
    for adres in do + kopia:
        if not waliduj_email(adres):
            raise BladWysylki("adres", "Sprawdź adres %s — brakuje w nim znaku @ "
                                       "albo nazwy domeny." % adres)

    wiadomosc = email.message.EmailMessage(policy=email.policy.SMTP)
    wiadomosc["From"] = nadawca
    wiadomosc["To"] = ", ".join(do)
    if kopia:
        wiadomosc["Cc"] = ", ".join(kopia)
    wiadomosc["Subject"] = str(temat or "").strip() or "Delegacje"
    wiadomosc["Date"] = email.utils.localtime()
    try:
        wiadomosc["Message-ID"] = email.utils.make_msgid(domain=nadawca.split("@")[1])
    except Exception:
        pass
    wiadomosc.set_content(TRESC_WIADOMOSCI + "\n")

    for sciezka in (pliki or []):
        sciezka = str(sciezka)
        try:
            with open(sciezka, "rb") as f:
                dane = f.read()
        except OSError:
            raise BladWysylki("plik", "Nie znalazłem pliku %s."
                              % os.path.basename(sciezka))
        glowny, podtyp = _typ_zalacznika(sciezka)
        wiadomosc.add_attachment(dane, maintype=glowny, subtype=podtyp,
                                 filename=os.path.basename(sciezka))
    return wiadomosc


def rozmiar_wiadomosci(wiadomosc):
    """Rozmiar gotowej wiadomości w bajtach — tyle naprawdę idzie na serwer."""
    try:
        return len(wiadomosc.as_bytes())
    except Exception:
        return 0


# --- USTAWIENIA SKRZYNKI ----------------------------------------------------


def _tekst(zrodlo, *klucze):
    for klucz in klucze:
        wartosc = zrodlo.get(klucz)
        if wartosc is None:
            continue
        wartosc = str(wartosc).strip()
        if wartosc:
            return wartosc
    return ""


def przygotuj_ustawienia(zrodlo):
    """Ustawienia skrzynki sprowadzone do jednego kształtu.

    Klucze: serwer, port, szyfrowanie, login, haslo, nadawca, limit_bajtow.
    Hasło zostaje w tym słowniku i nigdzie indziej.
    """
    zrodlo = dict(zrodlo or {})
    ust = {
        "serwer": _tekst(zrodlo, "serwer", "host", "smtp", "wysylka_serwer"),
        "login": _tekst(zrodlo, "login", "uzytkownik", "user", "wysylka_login"),
        "haslo": _tekst(zrodlo, "haslo", "password", "haslo_skrzynki"),
        "nadawca": _tekst(zrodlo, "nadawca", "od", "from", "adres", "wysylka_nadawca"),
    }
    szyfrowanie = _tekst(zrodlo, "szyfrowanie", "tls", "zabezpieczenie").casefold()
    try:
        port = int(str(_tekst(zrodlo, "port", "wysylka_port") or 0).strip() or 0)
    except ValueError:
        port = 0
    if not port:
        port = 465 if szyfrowanie in ("ssl", "smtps") else PORT_DOMYSLNY
    if szyfrowanie not in ("ssl", "starttls"):
        szyfrowanie = "ssl" if port == 465 else SZYFROWANIE_DOMYSLNE
    ust["port"] = port
    ust["szyfrowanie"] = szyfrowanie
    if not ust["nadawca"]:
        ust["nadawca"] = ust["login"] if waliduj_email(ust["login"]) else ""
    if not ust["login"]:
        ust["login"] = ust["nadawca"]
    try:
        ust["limit_bajtow"] = int(zrodlo.get("limit_bajtow") or LIMIT_ZALACZNIKOW_B)
    except (TypeError, ValueError):
        ust["limit_bajtow"] = LIMIT_ZALACZNIKOW_B
    return ust


def bez_hasla(ustawienia):
    """Kopia ustawień bez hasła — do dziennika, komunikatu i diagnostyki."""
    ust = dict(ustawienia or {})
    for klucz in ("haslo", "password", "haslo_skrzynki"):
        if klucz in ust:
            ust[klucz] = ""
    return ust


def ustawienia_kompletne(ustawienia):
    """(czy można wysyłać, czego brakuje)."""
    ust = przygotuj_ustawienia(ustawienia)
    braki = []
    if not ust["serwer"]:
        braki.append("serwer poczty")
    if not ust["nadawca"]:
        braki.append("adres skrzynki")
    if not ust["haslo"]:
        braki.append("hasło")
    return (not braki, braki)


# --- POŁĄCZENIE -------------------------------------------------------------


def _odrzucony_adres(adres):
    adres = str(adres or "").strip()
    if not adres:
        return KOMUNIKATY["adres"]
    return "Serwer nie przyjął adresu %s. Sprawdź pisownię." % adres


def opisz_wyjatek(wyjatek):
    """Wyjątek biblioteczny → (rodzaj, krótki komunikat po polsku)."""
    if isinstance(wyjatek, BladWysylki):
        return (wyjatek.rodzaj, wyjatek.komunikat)
    if isinstance(wyjatek, smtplib.SMTPAuthenticationError):
        return ("logowanie", KOMUNIKATY["logowanie"])
    if isinstance(wyjatek, smtplib.SMTPRecipientsRefused):
        adresy = ", ".join(sorted(getattr(wyjatek, "recipients", {}) or {}))
        return ("adres", _odrzucony_adres(adresy))
    if isinstance(wyjatek, smtplib.SMTPSenderRefused):
        return ("adres", _odrzucony_adres(getattr(wyjatek, "sender", "")))
    if isinstance(wyjatek, (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected,
                            smtplib.SMTPNotSupportedError, smtplib.SMTPHeloError)):
        return ("polaczenie", KOMUNIKATY["polaczenie"])
    if isinstance(wyjatek, (smtplib.SMTPDataError, smtplib.SMTPResponseException)):
        kod = getattr(wyjatek, "smtp_code", 0)
        tresc = str(getattr(wyjatek, "smtp_error", "") or "").lower()
        if kod in (523, 552, 554) and any(s in tresc for s in
                                          ("size", "large", "exceed", "limit", "big")):
            return ("rozmiar", KOMUNIKATY["rozmiar"])
        if kod in (534, 535, 530):
            return ("logowanie", KOMUNIKATY["logowanie"])
        return ("serwer", KOMUNIKATY["serwer"])
    if isinstance(wyjatek, ssl.SSLCertVerificationError):
        return ("certyfikat", KOMUNIKATY["certyfikat"])
    if isinstance(wyjatek, ssl.SSLError):
        return ("polaczenie", KOMUNIKATY["polaczenie"])
    if isinstance(wyjatek, (socket.gaierror, socket.herror, socket.timeout,
                            TimeoutError, ConnectionError, OSError)):
        return ("polaczenie", KOMUNIKATY["polaczenie"])
    return ("serwer", KOMUNIKATY["serwer"])


def _krok(postep, frakcja, opis):
    """Zgłoszenie postępu — nigdy nie wywraca wysyłki."""
    if postep is None:
        return
    try:
        postep(float(frakcja), opis)
    except Exception:
        pass


def _przerwano(przerwij):
    if przerwij is None:
        return False
    try:
        return bool(przerwij())
    except Exception:
        return False


def _polacz(ust):
    """Połączenie z serwerem: 587 + STARTTLS albo 465 + SSL. Port 25 — nie."""
    if int(ust["port"]) == 25:
        raise BladWysylki("konfiguracja", "Wybierz port 587 albo 465.")
    kontekst = ssl.create_default_context()
    if ust["szyfrowanie"] == "ssl":
        return smtplib.SMTP_SSL(ust["serwer"], int(ust["port"]),
                                context=kontekst, timeout=LIMIT_CZASU_S)
    serwer = smtplib.SMTP(ust["serwer"], int(ust["port"]), timeout=LIMIT_CZASU_S)
    try:
        serwer.ehlo()
        serwer.starttls(context=kontekst)
        serwer.ehlo()
    except Exception:
        try:
            serwer.close()
        except Exception:
            pass
        raise
    return serwer


def wyslij(ustawienia, wiadomosc, postep=None, przerwij=None):
    """Łączy się, loguje i wysyła gotową wiadomość.

    `postep(frakcja, opis)` jest wołane po każdym kroku, `przerwij()` pytane
    między krokami. Po wejściu w wysyłkę przerwać się już nie da — SMTP nie
    ma „cofnij". Zwraca WynikWysylki z czasem wysłania; błędy rzuca jako
    BladWysylki z rodzajem i polskim komunikatem.

    Hasło z `ustawienia` służy wyłącznie do zalogowania się na serwerze,
    który użytkownik sam wpisał. Nie jest nigdzie zapisywane.
    """
    ust = przygotuj_ustawienia(ustawienia)
    gotowe, braki = ustawienia_kompletne(ust)
    if not gotowe:
        raise BladWysylki("konfiguracja", "Brakuje: %s." % ", ".join(braki))
    if wiadomosc is None:
        raise BladWysylki("brak", KOMUNIKATY["brak"])
    limit = int(ust.get("limit_bajtow") or 0)
    rozmiar = rozmiar_wiadomosci(wiadomosc)
    if limit > 0 and rozmiar > limit:
        raise BladWysylki("rozmiar", "Łącznie %s, a skrzynka przyjmuje zwykle do %s."
                          % (rozmiar_po_ludzku(rozmiar), rozmiar_po_ludzku(limit)))
    if _przerwano(przerwij):
        raise BladWysylki("przerwano", KOMUNIKATY["przerwano"])

    odbiorcy = lista_adresow(wiadomosc.get("To", "")) + lista_adresow(wiadomosc.get("Cc", ""))
    zalacznikow = len(list(wiadomosc.iter_attachments()))
    start = time.monotonic()
    serwer = None
    try:
        _krok(postep, 0.05, "Łączę ze skrzynką…")
        serwer = _polacz(ust)
        _krok(postep, 0.25, "Loguję się…")
        if _przerwano(przerwij):
            raise BladWysylki("przerwano", KOMUNIKATY["przerwano"])
        serwer.login(ust["login"], ust["haslo"])
        _krok(postep, 0.90, "Wysyłam…")
        if _przerwano(przerwij):
            raise BladWysylki("przerwano", KOMUNIKATY["przerwano"])
        odrzucone = serwer.send_message(wiadomosc) or {}
    except BladWysylki:
        raise
    except Exception as wyjatek:
        rodzaj, komunikat = opisz_wyjatek(wyjatek)
        raise BladWysylki(rodzaj, komunikat)
    finally:
        if serwer is not None:
            try:
                serwer.quit()
            except Exception:
                try:
                    serwer.close()
                except Exception:
                    pass
    sekundy = round(time.monotonic() - start, 2)
    _krok(postep, 1.0, "Wysłano")
    czas = datetime.datetime.now().replace(microsecond=0).isoformat()
    przyjete = [a for a in odbiorcy if a not in (odrzucone or {})]
    return WynikWysylki(True, przyjete, czas, sekundy, zalacznikow,
                        sorted(odrzucone or {}),
                        "Dokumenty poszły na %s." % ", ".join(przyjete or odbiorcy))


def sprawdz_polaczenie(ustawienia):
    """Samo logowanie, bez wysyłki — do przycisku sprawdzania.

    Nie rzuca wyjątków: zwraca WynikProby(ok, rodzaj, komunikat, sekundy).
    """
    ust = przygotuj_ustawienia(ustawienia)
    gotowe, braki = ustawienia_kompletne(ust)
    if not gotowe:
        return WynikProby(False, "konfiguracja", "Brakuje: %s." % ", ".join(braki), 0.0)
    start = time.monotonic()
    serwer = None
    try:
        serwer = _polacz(ust)
        serwer.login(ust["login"], ust["haslo"])
    except Exception as wyjatek:
        rodzaj, komunikat = opisz_wyjatek(wyjatek)
        return WynikProby(False, rodzaj, komunikat, round(time.monotonic() - start, 2))
    finally:
        if serwer is not None:
            try:
                serwer.quit()
            except Exception:
                try:
                    serwer.close()
                except Exception:
                    pass
    return WynikProby(True, "", "Skrzynka odpowiada.", round(time.monotonic() - start, 2))


# --- SAMOSPRAWDZENIE --------------------------------------------------------

_BLEDY = []


def _sprawdz(opis, warunek, szczegol=""):
    if warunek:
        print("  OK   %s" % opis)
    else:
        _BLEDY.append(opis)
        print("  BŁĄD %s%s" % (opis, ("  — " + szczegol) if szczegol else ""))


def _utworz(folder, nazwa, bajtow=1024):
    sciezka = os.path.join(folder, nazwa)
    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    with open(sciezka, "wb") as f:
        f.write(b"%PDF-1.4\n" + b"x" * max(0, bajtow - 9))
    return sciezka


def main():
    print("pmt_wysylka — samosprawdzenie")
    print("(wysyłki na żywo nie próbujemy — testujemy temat, załączniki "
          "i gotową wiadomość)")

    print("\n1. Temat wiadomości")
    temat = temat_wiadomosci("Jan Kowalski", "lipiec", 2026)
    _sprawdz("wzór domyślny", temat == "Delegacje — Jan Kowalski — lipiec 2026", temat)
    temat_pl = temat_wiadomosci("Łukasz Ćwikliński", 7, "2026")
    _sprawdz("nazwisko z polskimi znakami i miesiąc liczbą",
             temat_pl == "Delegacje — Łukasz Ćwikliński — lipiec 2026", temat_pl)
    _sprawdz("miesiąc bez ogonków rozpoznany",
             temat_wiadomosci("Jan Kowalski", "wrzesien", 2026)
             == "Delegacje — Jan Kowalski — wrzesień 2026",
             temat_wiadomosci("Jan Kowalski", "wrzesien", 2026))
    for zly in ("Delegacje {miesiac} {rok}", "Dokumenty {imie}", "", None,
                "Delegacje {imie} {miesiac} {rok", "{0} {imie} {miesiac} {rok}"):
        wynik = temat_wiadomosci("Jan Kowalski", "lipiec", 2026, szablon=zly)
        _sprawdz("szablon bez wymaganych pól wraca do domyślnego: %r" % (zly,),
                 wynik == "Delegacje — Jan Kowalski — lipiec 2026", wynik)
    wlasny = temat_wiadomosci("Jan Kowalski", "lipiec", 2026,
                              szablon="{rok}-{miesiac_nr} {imie} ({liczba})",
                              liczba=6)
    _sprawdz("własny poprawny szablon działa", wlasny == "2026-07 Jan Kowalski (6)", wlasny)
    dziwny = temat_wiadomosci("Jan Kowalski", "lipiec", 2026,
                              szablon="{imie} {miesiac} {rok} {czegos_takiego_nie_ma}")
    _sprawdz("nieznane pole daje pusty ciąg, nie wyjątek",
             dziwny == "Jan Kowalski lipiec 2026", dziwny)
    _sprawdz("temat zawsze niepusty",
             bool(temat_wiadomosci(None, None, None)),
             repr(temat_wiadomosci(None, None, None)))

    print("\n2. Adresy")
    for dobry in ("a@b.pl", "jan.kowalski@pmt.com.pl", "kadry+delegacje@pmt.com.pl"):
        _sprawdz("adres poprawny: %s" % dobry, waliduj_email(dobry))
    for zly in ("a@b", "a b@c.pl", "ab.pl", "a@@b.pl", "", None, "a@b.p",
                "ćma@pmt.pl", "a@b..pl"):
        _sprawdz("adres odrzucony: %r" % (zly,), not waliduj_email(zly))
    _sprawdz("lista adresów z przecinków i średników",
             lista_adresow("a@b.pl, c@d.pl; a@b.pl") == ["a@b.pl", "c@d.pl"],
             repr(lista_adresow("a@b.pl, c@d.pl; a@b.pl")))

    katalog = tempfile.mkdtemp(prefix="pmt_wysylka_test_")
    try:
        print("\n3. Załączniki")
        paczka = os.path.join(katalog, "Rozliczenie_Jan_Kowalski_Lipiec_2026r")
        podpisu = os.path.join(paczka, PODFOLDER_PODPISU)
        podpisane = os.path.join(podpisu, PODFOLDER_PODPISANE)
        _utworz(podpisane, "delegacja_01_Jan_Kowalski_Lipiec_2026r-podpisany.pdf", 50000)
        _utworz(podpisane, "delegacja_02_Jan_Kowalski_Lipiec_2026r-podpisany.pdf", 50000)
        with open(os.path.join(
                podpisane,
                "delegacja_02_Jan_Kowalski_Lipiec_2026r-podpisany.xades"), "wb") as f:
            f.write(b"<xades/>")
        _utworz(podpisu, "delegacja_03_Jan_Kowalski_Lipiec_2026r.pdf", 50000)
        _utworz(podpisu, "delegacja_09_Jan_Kowalski_Lipiec_2026r.pdf", 50000)
        manifest = {
            "program": "PMT Planer",
            "pliki": [
                {"plik": "delegacja_01_Jan_Kowalski_Lipiec_2026r.pdf",
                 "status": STATUS_PODPISANY,
                 "podpisany_plik": "delegacja_01_Jan_Kowalski_Lipiec_2026r-podpisany.pdf"},
                {"plik": "delegacja_02_Jan_Kowalski_Lipiec_2026r.pdf",
                 "status": STATUS_PODPISANY,
                 "podpisany_plik": "delegacja_02_Jan_Kowalski_Lipiec_2026r-podpisany.pdf"},
                {"plik": "delegacja_03_Jan_Kowalski_Lipiec_2026r.pdf",
                 "status": STATUS_DO_PODPISU, "podpisany_plik": None},
                {"plik": "delegacja_09_Jan_Kowalski_Lipiec_2026r.pdf",
                 "status": STATUS_NIEAKTUALNY, "podpisany_plik": None},
            ],
        }
        with open(os.path.join(podpisu, NAZWA_MANIFESTU), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False)

        wynik = zalaczniki(paczka)
        nazwy = [os.path.basename(p) for p in wynik.pliki]
        _sprawdz("lecą tylko wpisy podpisane",
                 all("-podpisany" in n for n in nazwy), repr(nazwy))
        _sprawdz("wpis nieaktualny nie leci nigdy",
                 not any("delegacja_09" in n for n in nazwy), repr(nazwy))
        _sprawdz("podpis odłączony leci razem z PDF-em",
                 "delegacja_02_Jan_Kowalski_Lipiec_2026r-podpisany.xades" in nazwy,
                 repr(nazwy))
        _sprawdz("niepodpisane policzone", wynik.niepodpisane == 1,
                 str(wynik.niepodpisane))
        _sprawdz("rozmiar liczony PO narzucie kodowania",
                 wynik.rozmiar == int(wynik.rozmiar_surowy * NARZUT_KODOWANIA)
                 and wynik.rozmiar > wynik.rozmiar_surowy,
                 "%d / %d" % (wynik.rozmiar, wynik.rozmiar_surowy))
        _sprawdz("próg nieprzekroczony przy zwykłej paczce", not wynik.za_duze)
        maly = zalaczniki(paczka, limit_bajtow=wynik.rozmiar_surowy + 1)
        _sprawdz("próg przekroczony przez sam narzut base64, nie surowe bajty",
                 maly.za_duze, "%d > %d" % (maly.rozmiar, maly.limit))
        _sprawdz("limit zerowy = bez progu", not zalaczniki(paczka, limit_bajtow=0).za_duze)
        z_niepodpisanymi = zalaczniki(paczka, tylko_podpisane=False)
        _sprawdz("wyłączone tylko-podpisane dokłada oryginał do podpisu",
                 any("delegacja_03" in os.path.basename(p)
                     for p in z_niepodpisanymi.pliki),
                 repr([os.path.basename(p) for p in z_niepodpisanymi.pliki]))
        _sprawdz("nieistniejący folder nie wywraca funkcji",
                 zalaczniki(os.path.join(katalog, "nie_ma")).pliki == []
                 and zalaczniki(None).pliki == [] and zalaczniki("").pliki == [])

        bez_manifestu = os.path.join(katalog, "bez_manifestu")
        _utworz(os.path.join(bez_manifestu, PODFOLDER_PODPISANE), "a-podpisany.pdf")
        _utworz(bez_manifestu, "b.pdf")
        skan = zalaczniki(bez_manifestu)
        _sprawdz("bez manifestu bierzemy podfolder Podpisane",
                 [os.path.basename(p) for p in skan.pliki] == ["a-podpisany.pdf"],
                 repr([os.path.basename(p) for p in skan.pliki]))
        _sprawdz("bez manifestu dokument spoza Podpisane liczy się jako niepodpisany",
                 skan.niepodpisane == 1, str(skan.niepodpisane))

        # Ani manifestu, ani podfolderu Podpisane: „tylko podpisane" MUSI
        # filtrować, a licznik ma mówić prawdę — dotąd leciało wszystko, a licznik
        # stał na zerze.
        goly = os.path.join(katalog, "Rozliczenie_Anna_Nowak_maj_2026r")
        for n in ("delegacja_01_Anna_Nowak_maj_2026r.pdf",
                  "delegacja_02_Anna_Nowak_maj_2026r.pdf",
                  "rozliczenie_wydatków_Anna_Nowak_maj_2026r.pdf"):
            _utworz(goly, n)
        with open(os.path.join(goly, "Trasy_Mapa.html"), "w", encoding="utf-8") as f:
            f.write("<html></html>")
        tylko = zalaczniki(goly, tylko_podpisane=True)
        wszystko = zalaczniki(goly, tylko_podpisane=False)
        _sprawdz("bez śladu podpisu „tylko podpisane” nie wysyła niczego",
                 tylko.pliki == [], repr([os.path.basename(p) for p in tylko.pliki]))
        _sprawdz("bez śladu podpisu licznik niepodpisanych = liczba dokumentów",
                 tylko.niepodpisane == 3 and wszystko.niepodpisane == 3,
                 "%d / %d" % (tylko.niepodpisane, wszystko.niepodpisane))
        _sprawdz("po wyłączeniu „tylko podpisane” lecą wszystkie dokumenty (bez HTML)",
                 len(wszystko.pliki) == 3
                 and all(p.endswith(".pdf") for p in wszystko.pliki),
                 repr([os.path.basename(p) for p in wszystko.pliki]))
        # egzemplarz z sufiksem podpisu obok oryginału — podpisany po nazwie,
        # jak rozpoznaje to pmt_podpis; oryginał zostaje niepodpisany
        _utworz(goly, "delegacja_02_Anna_Nowak_maj_2026r-podpisany.pdf")
        z_sufiksem = zalaczniki(goly, tylko_podpisane=True)
        _sprawdz("dokument z sufiksem podpisu leci jako podpisany, oryginał nie",
                 [os.path.basename(p) for p in z_sufiksem.pliki]
                 == ["delegacja_02_Anna_Nowak_maj_2026r-podpisany.pdf"]
                 and z_sufiksem.niepodpisane == 3,
                 "%r / %d" % ([os.path.basename(p) for p in z_sufiksem.pliki],
                              z_sufiksem.niepodpisane))
        # podpisany egzemplarz w Podpisane „pokrywa" oryginał o tym samym rdzeniu
        # (nazwa podpisanego ZAWIERA rdzeń oryginału, jak w pmt_podpis)
        os.remove(os.path.join(goly, "delegacja_02_Anna_Nowak_maj_2026r-podpisany.pdf"))
        _utworz(os.path.join(goly, PODFOLDER_PODPISU, PODFOLDER_PODPISANE),
                "delegacja_01_Anna_Nowak_maj_2026r-podpisany.pdf")
        pokryty = zalaczniki(goly, tylko_podpisane=False)
        _sprawdz("oryginał, którego podpisany egzemplarz leży w Podpisane, nie leci drugi raz",
                 [os.path.basename(p) for p in pokryty.pliki]
                 == ["delegacja_01_Anna_Nowak_maj_2026r-podpisany.pdf",
                     "delegacja_02_Anna_Nowak_maj_2026r.pdf",
                     "rozliczenie_wydatków_Anna_Nowak_maj_2026r.pdf"]
                 and pokryty.niepodpisane == 2,
                 "%r / %d" % ([os.path.basename(p) for p in pokryty.pliki],
                              pokryty.niepodpisane))

        luzny = os.path.join(katalog, "luzny_manifest")
        luzne_podpisane = os.path.join(luzny, PODFOLDER_PODPISANE)
        _utworz(luzne_podpisane, "delegacja_01_Anna_Nowak_maj_2026r-podpisany.pdf")
        with open(os.path.join(luzny, NAZWA_MANIFESTU), "w", encoding="utf-8") as f:
            json.dump({"pliki": [
                {"plik": "delegacja_01_Anna_Nowak_maj_2026r.pdf",
                 "status": STATUS_PODPISANY, "podpisany_plik": None},
                {"plik": "delegacja_02_Anna_Nowak_maj_2026r.pdf",
                 "status": STATUS_PODPISANY, "podpisany_plik": None},
            ]}, f, ensure_ascii=False)
        luzne = zalaczniki(luzny)
        _sprawdz("wpis podpisany bez wskazanej nazwy: szukamy w Podpisane",
                 [os.path.basename(x) for x in luzne.pliki]
                 == ["delegacja_01_Anna_Nowak_maj_2026r-podpisany.pdf"],
                 repr([os.path.basename(x) for x in luzne.pliki]))
        _sprawdz("brak podpisanego egzemplarza: nie podstawiamy kopii bez podpisu",
                 luzne.niepodpisane == 1, str(luzne.niepodpisane))

        print("\n4. Wiadomość")
        temat_pl = temat_wiadomosci("Łukasz Ćwikliński", "lipiec", 2026, liczba=2)
        wiad = zbuduj_wiadomosc("jan.kowalski@pmt.com.pl", "kadry@pmt.com.pl",
                                temat_pl, wynik.pliki, dw="jan.kowalski@pmt.com.pl")
        _sprawdz("załączniki dołożone",
                 len(list(wiad.iter_attachments())) == len(wynik.pliki),
                 "%d z %d" % (len(list(wiad.iter_attachments())), len(wynik.pliki)))
        _sprawdz("nazwy załączników bez zmian",
                 sorted(c.get_filename() for c in wiad.iter_attachments())
                 == sorted(os.path.basename(p) for p in wynik.pliki))
        _sprawdz("adresat i kopia w nagłówkach",
                 wiad["To"] == "kadry@pmt.com.pl"
                 and wiad["Cc"] == "jan.kowalski@pmt.com.pl",
                 "%s / %s" % (wiad["To"], wiad["Cc"]))
        _sprawdz("adresy dają się odczytać z gotowych nagłówków",
                 lista_adresow(wiad["To"]) + lista_adresow(wiad["Cc"])
                 == ["kadry@pmt.com.pl", "jan.kowalski@pmt.com.pl"],
                 repr(lista_adresow(wiad["To"]) + lista_adresow(wiad["Cc"])))
        _sprawdz("treść to jedno zdanie rzeczowe",
                 wiad.get_body(("plain",)).get_content().strip() == TRESC_WIADOMOSCI)

        surowe = wiad.as_bytes()
        naglowki = surowe.split(b"\r\n\r\n", 1)[0]
        _sprawdz("nagłówek tematu zakodowany (RFC 2047), nie surowe UTF-8",
                 b"=?utf-8?" in naglowki.lower()
                 and "Ćwikliński".encode("utf-8") not in naglowki,
                 repr(naglowki[:200]))
        odczytane = email.message_from_bytes(surowe, policy=email.policy.SMTP)
        _sprawdz("temat po odczytaniu z powrotem jest ten sam",
                 str(odczytane["Subject"]) == temat_pl,
                 "%r != %r" % (str(odczytane["Subject"]), temat_pl))
        _sprawdz("załącznik PDF ma typ application/pdf",
                 any(c.get_content_type() == "application/pdf"
                     for c in odczytane.iter_attachments()))
        _sprawdz("podpis .xades nie idzie jako tekst",
                 all(c.get_content_maintype() != "text"
                     for c in odczytane.iter_attachments()))
        _sprawdz("rozmiar gotowej wiadomości większy od surowych bajtów",
                 rozmiar_wiadomosci(wiad) > wynik.rozmiar_surowy,
                 "%d / %d" % (rozmiar_wiadomosci(wiad), wynik.rozmiar_surowy))

        for zly in ("kadry", "kadry@", "kadry pmt@pmt.pl"):
            try:
                zbuduj_wiadomosc("jan@pmt.pl", zly, "Temat", [])
                _sprawdz("zły adres odbiorcy odrzucony: %r" % zly, False)
            except BladWysylki as b:
                _sprawdz("zły adres odbiorcy odrzucony: %r" % zly, b.rodzaj == "adres",
                         b.rodzaj)
        try:
            zbuduj_wiadomosc("jan@pmt.pl", "kadry@pmt.pl", "Temat",
                             [os.path.join(katalog, "nie_ma_takiego.pdf")])
            _sprawdz("brakujący plik zgłoszony", False)
        except BladWysylki as b:
            _sprawdz("brakujący plik zgłoszony", b.rodzaj == "plik", b.rodzaj)

        print("\n5. Ustawienia, hasło i błędy")
        ust = przygotuj_ustawienia({"serwer": "smtp.pmt.com.pl",
                                    "login": "jan.kowalski@pmt.com.pl",
                                    "haslo": "TAJNE-HASLO"})
        _sprawdz("domyślnie port 587 ze STARTTLS",
                 ust["port"] == 587 and ust["szyfrowanie"] == "starttls",
                 "%s %s" % (ust["port"], ust["szyfrowanie"]))
        _sprawdz("port 465 przełącza na SSL",
                 przygotuj_ustawienia({"port": 465})["szyfrowanie"] == "ssl")
        _sprawdz("nadawca uzupełniony z loginu",
                 ust["nadawca"] == "jan.kowalski@pmt.com.pl", ust["nadawca"])
        _sprawdz("hasła nie ma w kopii do zapisu",
                 "TAJNE-HASLO" not in json.dumps(bez_hasla(ust), ensure_ascii=False),
                 json.dumps(bez_hasla(ust), ensure_ascii=False))
        _sprawdz("brakujące ustawienia wypisane po imieniu",
                 ustawienia_kompletne({"serwer": "smtp.pmt.com.pl"})[1]
                 == ["adres skrzynki", "hasło"],
                 repr(ustawienia_kompletne({"serwer": "smtp.pmt.com.pl"})[1]))
        proba = sprawdz_polaczenie({"serwer": "smtp.pmt.com.pl"})
        _sprawdz("sprawdzanie połączenia bez kompletu ustawień nie łączy się",
                 proba.ok is False and proba.rodzaj == "konfiguracja", repr(proba))

        _sprawdz("błędne dane logowania",
                 opisz_wyjatek(smtplib.SMTPAuthenticationError(535, b"nope"))[0]
                 == "logowanie")
        _sprawdz("brak połączenia",
                 opisz_wyjatek(socket.gaierror(-2, "Name or service not known"))[0]
                 == "polaczenie"
                 and opisz_wyjatek(TimeoutError("timed out"))[0] == "polaczenie"
                 and opisz_wyjatek(smtplib.SMTPConnectError(421, b"x"))[0] == "polaczenie")
        _sprawdz("serwer odrzucił załącznik za duży",
                 opisz_wyjatek(smtplib.SMTPDataError(552, b"message size exceeds limit"))[0]
                 == "rozmiar")
        _sprawdz("serwer nie przyjął adresu",
                 opisz_wyjatek(smtplib.SMTPRecipientsRefused(
                     {"kadry@pmt.com.pl": (550, b"no such user")}))[0] == "adres")
        _sprawdz("nieprawidłowy certyfikat rozpoznany osobno",
                 opisz_wyjatek(ssl.SSLCertVerificationError("bad cert"))[0] == "certyfikat")
        _sprawdz("każdy komunikat po polsku i krótki",
                 all(t and len(t) < 160 for t in KOMUNIKATY.values()))

        przekroczone = None
        try:
            wyslij({"serwer": "smtp.pmt.com.pl", "login": "jan@pmt.pl",
                    "haslo": "x", "limit_bajtow": 1000}, wiad)
        except BladWysylki as b:
            przekroczone = b
        _sprawdz("przekroczony rozmiar zatrzymuje wysyłkę przed połączeniem",
                 przekroczone is not None and przekroczone.rodzaj == "rozmiar",
                 repr(przekroczone))
        przerwane = None
        slad = []
        try:
            wyslij({"serwer": "smtp.pmt.com.pl", "login": "jan@pmt.pl", "haslo": "x"},
                   wiad, postep=lambda f, o: slad.append((f, o)),
                   przerwij=lambda: True)
        except BladWysylki as b:
            przerwane = b
        _sprawdz("przerwanie zatrzymuje wysyłkę bez łączenia",
                 przerwane is not None and przerwane.rodzaj == "przerwano" and not slad,
                 repr(przerwane))
    finally:
        shutil.rmtree(katalog, ignore_errors=True)

    print("")
    if _BLEDY:
        print("NIE PRZESZŁO: %d" % len(_BLEDY))
        for opis in _BLEDY:
            print("   - %s" % opis)
        return 1
    print("WSZYSTKO PRZESZŁO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
