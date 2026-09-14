# -*- coding: utf-8 -*-
"""
PMT PLANER — KOMPLET DOKUMENTÓW

Rozpoznaje pliki PDF, które program sam tworzy w folderze wyjściowym, żeby
po wygenerowaniu można je było od razu pokazać, a nie szukać na dysku.

Wzorce nazw pochodzą wprost z PMT_Delegacje.py:

    generuj_pdfy()          delegacja_01_Jan_Kowalski_styczeń_2026r.pdf
                            rozliczenie_wydatków_Jan_Kowalski_styczeń_2026r.pdf
    eksport planu wizyt     Plan_Wizyt_2026-09-12.pdf

W nazwach siedzą dwie rzeczy zmienne: imię i nazwisko użytkownika oraz polska
nazwa miesiąca — obie z ogonkami. Dlatego dopasowanie porównuje nazwy po
uproszczeniu: bez znaków diakrytycznych (także „ł", które nie ma rozkładu
w Unicode), bez rozróżniania wielkości liter i w formie znormalizowanej
(macOS zapisuje nazwy plików w NFD, Windows i Linux w NFC).

Odczytuje też LICZBY z gotowych plików (tekst_dokumentu, liczby_dokumentu,
liczby_kompletu): kwotę każdej delegacji, kilometry i stawkę z rubryki
„(1) Przejazdy" oraz daty dni — z tego program dociąga do historii miesiące
wygenerowane, zanim historia zaczęła się zapisywać. Odczyt jednego pliku to
1–3 ms (dekompresja strumieni i tablice ToUnicode osadzonych krojów).

Moduł jest samodzielny: wyłącznie biblioteka standardowa, bez PyQt6
i bez importu czegokolwiek z PMT_Delegacje.

Samosprawdzenie:   python pmt_dokumenty.py
"""

import os
import re
import shutil
import sys
import tempfile
import unicodedata
import zlib

ROZSZERZENIE = ".pdf"

RODZAJ_DELEGACJA = "delegacja"
RODZAJ_ROZLICZENIE = "rozliczenie"
RODZAJ_PLAN = "plan"

# Kolejność prezentacji: delegacje po numerach, potem rozliczenie zbiorcze,
# na końcu wykaz planu wizyt.
_KOLEJNOSC = {RODZAJ_DELEGACJA: 0, RODZAJ_ROZLICZENIE: 1, RODZAJ_PLAN: 2}

_RE_DELEGACJA = re.compile(r"^delegacja[ _.-]*(\d+)(?:[ _.-]|$)")
_RE_ROZLICZENIE = re.compile(r"^rozliczenie[ _.-]*wydatkow(?:[ _.-]|$)")
_RE_PLAN = re.compile(r"^plan[ _.-]*wizyt(?:[ _.-]|$)")

# Znaki, których NFKD nie rozkłada na literę + ogonek.
_ZAMIANY = {"ł": "l", "Ł": "L", "ß": "ss", "đ": "d", "Đ": "D"}


def _uproszcz(tekst):
    """Nazwa sprowadzona do postaci porównywalnej: bez ogonków, małymi literami."""
    if not tekst:
        return ""
    tekst = "".join(_ZAMIANY.get(z, z) for z in tekst)
    tekst = unicodedata.normalize("NFKD", tekst)
    tekst = "".join(z for z in tekst if not unicodedata.combining(z))
    return tekst.casefold()


def _rozpoznaj(nazwa):
    """(rodzaj, numer) dla nazwy pliku; (None, 0) gdy to nie nasz dokument."""
    if not nazwa:
        return (None, 0)
    nazwa = os.path.basename(str(nazwa))
    if nazwa.startswith(".") or nazwa.startswith("~$"):
        return (None, 0)            # pliki ukryte i tymczasowe pakietów biurowych
    rdzen, rozszerzenie = os.path.splitext(nazwa)
    if _uproszcz(rozszerzenie) != ROZSZERZENIE:
        return (None, 0)
    klucz = _uproszcz(rdzen)
    dopasowanie = _RE_DELEGACJA.match(klucz)
    if dopasowanie:
        try:
            numer = int(dopasowanie.group(1))
        except (TypeError, ValueError):
            numer = 0
        return (RODZAJ_DELEGACJA, numer)
    if _RE_ROZLICZENIE.match(klucz):
        return (RODZAJ_ROZLICZENIE, 0)
    if _RE_PLAN.match(klucz):
        return (RODZAJ_PLAN, 0)
    return (None, 0)


def rodzaj_dokumentu(nazwa):
    """"delegacja" / "rozliczenie" / "plan" albo None."""
    return _rozpoznaj(nazwa)[0]


def numer_delegacji(nazwa):
    """Numer z nazwy delegacji (0, gdy plik nie jest delegacją)."""
    rodzaj, numer = _rozpoznaj(nazwa)
    return numer if rodzaj == RODZAJ_DELEGACJA else 0


def czy_dokument(nazwa):
    """Czy ten plik powstał z programu."""
    return _rozpoznaj(nazwa)[0] is not None


def dokumenty_w_folderze(folder):
    """Posortowane ścieżki do plików PDF wygenerowanych przez program.

    Kolejność: delegacje rosnąco wg numeru, dalej rozliczenie zbiorcze,
    na końcu wykaz planu wizyt. Folder nieistniejący albo niedostępny daje
    pustą listę — nigdy wyjątek.
    """
    if not folder:
        return []
    try:
        nazwy = os.listdir(folder)
    except (OSError, TypeError, ValueError):
        return []
    znalezione = []
    for nazwa in nazwy:
        rodzaj, numer = _rozpoznaj(nazwa)
        if rodzaj is None:
            continue
        sciezka = os.path.join(folder, nazwa)
        try:
            if not os.path.isfile(sciezka):
                continue
        except OSError:
            continue
        znalezione.append((_KOLEJNOSC.get(rodzaj, 9), numer, _uproszcz(nazwa), sciezka))
    znalezione.sort()
    return [pozycja[-1] for pozycja in znalezione]


def podsumowanie(folder):
    """Ścieżka do pliku, który warto otworzyć jako pierwszy, albo None.

    Najpierw rozliczenie zbiorcze, w razie jego braku pierwsza delegacja,
    a gdyby i tej nie było — pierwszy rozpoznany dokument.
    """
    pliki = dokumenty_w_folderze(folder)
    if not pliki:
        return None
    for wybrany_rodzaj in (RODZAJ_ROZLICZENIE, RODZAJ_DELEGACJA):
        for sciezka in pliki:
            if _rozpoznaj(sciezka)[0] == wybrany_rodzaj:
                return sciezka
    return pliki[0]


def _odmiana(ile, pojedyncza, mnoga, dopelniacz):
    """Polska odmiana liczebnika: 1 delegacja, 2 delegacje, 5 delegacji."""
    ile = abs(int(ile))
    if ile == 1:
        return "1 %s" % pojedyncza
    if ile % 10 in (2, 3, 4) and ile % 100 not in (12, 13, 14):
        return "%d %s" % (ile, mnoga)
    return "%d %s" % (ile, dopelniacz)


def _rozmiar(bajty):
    """Rozmiar po ludzku, z polskim przecinkiem dziesiętnym."""
    wartosc = float(max(0, int(bajty)))
    jednostka = "B"
    for jednostka in ("B", "kB", "MB", "GB"):
        if wartosc < 1024 or jednostka == "GB":
            break
        wartosc /= 1024.0
    if jednostka == "B" or wartosc >= 100:
        return "%d %s" % (int(round(wartosc)), jednostka)
    return ("%.1f %s" % (wartosc, jednostka)).replace(".", ",")


def opis_kompletu(folder):
    """Krótka informacja liczbowa o komplecie: ile delegacji, ile innych
    plików, łączny rozmiar. Np. „4 delegacje · 2 inne pliki · 1,3 MB"."""
    pliki = dokumenty_w_folderze(folder)
    if not pliki:
        return "brak plików"
    delegacje = 0
    inne = 0
    bajty = 0
    for sciezka in pliki:
        if _rozpoznaj(sciezka)[0] == RODZAJ_DELEGACJA:
            delegacje += 1
        else:
            inne += 1
        try:
            bajty += os.path.getsize(sciezka)
        except OSError:
            pass
    czesci = []
    if delegacje:
        czesci.append(_odmiana(delegacje, "delegacja", "delegacje", "delegacji"))
    if inne:
        czesci.append(_odmiana(inne, "inny plik", "inne pliki", "innych plików"))
    czesci.append(_rozmiar(bajty))
    return " · ".join(czesci)


# ───────────────────────── liczby z gotowych plików ─────────────────────────
# PDF-y programu rysuje fpdf2 z osadzonymi krojami: każdy napis to ciąg
# dwubajtowych numerów glifów, a znaczenie glifu podaje tablica ToUnicode
# danego kroju. Odczyt idzie więc tak: obiekty → strumienie (zlib) → tablice
# krojów → treść strony z pilnowaniem, który krój jest właśnie wybrany (Tf).

_RE_OBIEKT = re.compile(rb"(\d+)\s+0\s+obj\b(.*?)\bendobj", re.S)
_RE_STRUMIEN = re.compile(rb"\bstream\r?\n(.*?)\r?\nendstream", re.S)
_RE_TOUNICODE = re.compile(rb"/ToUnicode\s+(\d+)\s+0\s+R")
_RE_ZASOB_KROJU = re.compile(rb"/(F\d+)\s+(\d+)\s+0\s+R")
_RE_BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
_RE_BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
_RE_PARA_HEX = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
_RE_ZAKRES_HEX = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
_RE_TOKEN_TRESCI = re.compile(rb"/(F\d+)\s+[\d.]+\s+Tf|\(((?:\\.|[^\\)])*)\)\s*Tj", re.S)
_RE_UCIECZKA = re.compile(rb"\\([0-7]{1,3}|.)", re.S)
_UCIECZKI = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f",
             b"(": b"(", b")": b")", b"\\": b"\\"}

_RE_KWOTA = re.compile(r"^\d+\.\d\d$")
_RE_DATA = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})r?\.?$")
_RE_GODZINA = re.compile(r"^\d{1,2}:\d{2}$")
_RE_PRZEJAZDY = re.compile(r"([\d\s]+(?:,\d+)?)\s*km\s*[×x]\s*([\d\s]+(?:,\d+)?)\s*z")
_ETYKIETA_ODLEGLOSCI = "odleglosci:"          # „Odległości: szacunek" po uproszczeniu


def _odkoduj_ucieczki(surowy):
    """Napis PDF w nawiasach → bajty: \( \) \\ \r \n \t \b \f i ósemkowe \ddd."""
    def _zamien(m):
        znak = m.group(1)
        if znak.isdigit():
            return bytes([int(znak, 8) & 0xFF])
        return _UCIECZKI.get(znak, znak)
    return _RE_UCIECZKA.sub(_zamien, surowy)


def _strumien(obiekt):
    m = _RE_STRUMIEN.search(obiekt)
    if not m:
        return b""
    try:
        return zlib.decompress(m.group(1))
    except zlib.error:
        return m.group(1)


def _znak_z_hex(szesnastkowo):
    try:
        return bytes.fromhex(szesnastkowo.decode("ascii")).decode("utf-16-be", "replace")
    except (ValueError, UnicodeError):
        return ""


def _mapa_tounicode(cmap):
    """Tablica ToUnicode kroju → {numer glifu: znak}. bfchar i bfrange."""
    mapa = {}
    for blok in _RE_BFCHAR.finditer(cmap):
        for zrodlo, cel in _RE_PARA_HEX.findall(blok.group(1)):
            mapa[int(zrodlo, 16)] = _znak_z_hex(cel)
    for blok in _RE_BFRANGE.finditer(cmap):
        for dol, gora, cel in _RE_ZAKRES_HEX.findall(blok.group(1)):
            start = _znak_z_hex(cel)
            if not start:
                continue
            pierwszy = ord(start[0])
            for numer in range(int(dol, 16), min(int(gora, 16), int(dol, 16) + 65535) + 1):
                mapa[numer] = chr(pierwszy + numer - int(dol, 16))
    return mapa


def tekst_dokumentu(sciezka):
    """Napisy z PDF-u programu, po jednym na rubrykę, w kolejności rysowania.

    Każdy napis jest odkodowany tablicą TEGO kroju, którym go narysowano
    (fpdf2 osadza osobny krój dla zwykłego i pogrubionego pisma). Plik
    nieczytelny, cudzy albo nieistniejący daje pustą listę — nigdy wyjątek.
    """
    try:
        with open(sciezka, "rb") as f:
            dane = f.read()
    except (OSError, TypeError, ValueError):
        return []
    obiekty = {}
    for m in _RE_OBIEKT.finditer(dane):
        obiekty[int(m.group(1))] = m.group(2)
    kroje = {}
    for numer, tresc in obiekty.items():
        naglowek = tresc.split(b"stream", 1)[0]
        m = _RE_TOUNICODE.search(naglowek)
        if m and b"/Font" in naglowek:
            kroje[numer] = _mapa_tounicode(_strumien(obiekty.get(int(m.group(1)), b"")))
    nazwy = {}
    for m in _RE_ZASOB_KROJU.finditer(dane):
        nazwy.setdefault(m.group(1), int(m.group(2)))
    napisy = []
    for numer in sorted(obiekty):
        strumien = _strumien(obiekty[numer])
        if b" Tf" not in strumien or b"BT" not in strumien:
            continue
        mapa = {}
        for token in _RE_TOKEN_TRESCI.finditer(strumien):
            if token.group(1) is not None:
                mapa = kroje.get(nazwy.get(token.group(1)), {})
                continue
            bajty = _odkoduj_ucieczki(token.group(2))
            napisy.append("".join(mapa.get(bajty[i] * 256 + bajty[i + 1], "")
                                  for i in range(0, len(bajty) - 1, 2)))
    return napisy


def _liczba_pl(tekst):
    return float(str(tekst).replace(" ", "").replace("\xa0", "").replace(",", "."))


def _liczby_z_napisow(napisy):
    """Kwota, kilometry, stawka i daty z listy napisów jednego dokumentu.

    Kwota to wartość rubryki „Suma wydatków" (w rozliczeniu zbiorczym:
    „Suma wydatków global:") — pierwszy napis w formacie 0.00 po PIERWSZEJ
    takiej etykiecie; kolejne etykiety nie nadpisują odczytu.
    Kilometry i stawka z „Prywatny samochód: 312,4 km × 1,15 zł/km" — pliki
    sprzed tej rubryki dają None. Daty: każdy napis „dd.mm.rrrrr" (ISO, bez
    powtórzeń, rosnąco). Bez kwoty w pliku — kwota None, NIGDY zero.
    """
    kwota = None
    km = None
    stawka = None
    daty = set()
    czekam_na_kwote = False
    for napis in napisy:
        czysty = napis.strip()
        if not czysty:
            continue
        if czekam_na_kwote and _RE_KWOTA.match(czysty):
            if kwota is None:
                kwota = float(czysty)       # pierwsza rubryka „Suma wydatków" wygrywa
            czekam_na_kwote = False
            continue
        if _uproszcz(czysty).startswith("suma wydatk"):
            czekam_na_kwote = True
            continue
        m = _RE_DATA.match(czysty)
        if m:
            dzien, miesiac, rok = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if 1 <= miesiac <= 12 and 1 <= dzien <= 31:
                daty.add("%04d-%02d-%02d" % (rok, miesiac, dzien))
            continue
        m = _RE_PRZEJAZDY.search(czysty)
        if m and km is None:
            try:
                km = _liczba_pl(m.group(1))
                stawka = _liczba_pl(m.group(2))
            except ValueError:
                km = stawka = None
    return {"kwota": kwota, "km": km, "stawka": stawka, "daty": sorted(daty)}


def _etykieta_odleglosci(napisy):
    """Etykieta źródła odległości z nagłówka dokumentu („Odległości: szacunek"
    → „szacunek"; „realne drogi", „drogi z pamięci") albo pusty napis."""
    for napis in napisy:
        czysty = str(napis).strip()
        if _uproszcz(czysty).startswith(_ETYKIETA_ODLEGLOSCI):
            return czysty.split(":", 1)[1].strip()
    return ""


def _dni_z_napisow(napisy):
    """Dni z tabeli przejazdów jednego polecenia wyjazdu.

    Wiersz tabeli to osiem kolejnych napisów: skąd, data, godzina wyjazdu,
    dokąd, data, godzina przyjazdu, środek lokomocji, kwota etapu. Etapy
    tego samego dnia składają się w jeden dzień: przystanki (bez powrotu
    do bazy), kwota dnia co do grosza, pierwszy wyjazd i ostatni przyjazd.
    Zwraca listę {"data" ISO, "przystanki", "kwota", "start", "koniec"}
    w kolejności z dokumentu; bez tabeli — pusta lista.
    """
    dni = {}
    kolejnosc = []
    i = 0
    while i + 7 < len(napisy):
        w = [str(x).strip() for x in napisy[i:i + 8]]
        m_wyj = _RE_DATA.match(w[1])
        m_przyj = _RE_DATA.match(w[4])
        if not (m_wyj and m_przyj and w[0] and w[3]
                and _RE_GODZINA.match(w[2]) and _RE_GODZINA.match(w[5])
                and _RE_KWOTA.match(w[7])):
            i += 1
            continue
        data = "%04d-%02d-%02d" % (int(m_wyj.group(3)), int(m_wyj.group(2)), int(m_wyj.group(1)))
        dzien = dni.get(data)
        if dzien is None:
            dzien = dni[data] = {"data": data, "przystanki": [], "kwota": 0.0,
                                 "start": w[2], "koniec": w[5], "_baza": w[0]}
            kolejnosc.append(data)
        dzien["przystanki"].append(w[3])
        dzien["kwota"] += float(w[7])
        dzien["koniec"] = w[5]
        i += 8
    wynik = []
    for data in kolejnosc:
        dzien = dni[data]
        baza = dzien.pop("_baza")
        # ostatni etap dnia to powrót do bazy — nie jest przystankiem
        if len(dzien["przystanki"]) > 1 and _uproszcz(dzien["przystanki"][-1]) == _uproszcz(baza):
            dzien["przystanki"].pop()
        dzien["kwota"] = round(dzien["kwota"], 2)
        wynik.append(dzien)
    return wynik


def _dni_i_liczby(sciezka):
    """(dni, liczby) z JEDNEGO odczytu pliku — dni tylko wtedy, gdy ich kwoty
    sumują się CO DO GROSZA do rubryki „Suma wydatków"; inaczej pusta lista,
    bo kartka z niepewną kwotą byłaby kłamstwem."""
    napisy = tekst_dokumentu(sciezka)
    liczby = _liczby_z_napisow(napisy)
    liczby["odleglosci"] = _etykieta_odleglosci(napisy)
    dni = _dni_z_napisow(napisy)
    if dni and (liczby["kwota"] is None
                or abs(sum(d["kwota"] for d in dni) - liczby["kwota"]) >= 0.005):
        dni = []
    return dni, liczby


def dni_dokumentu(sciezka):
    """Dni jednego polecenia wyjazdu z jego tabeli przejazdów (patrz
    _dni_z_napisow), zgodne co do grosza z „Sumą wydatków" pliku."""
    return _dni_i_liczby(sciezka)[0]


def dni_kompletu(folder):
    """Dni całego miesiąca z gotowych poleceń wyjazdu w folderze — kartki na
    tacę dla miesiąca z dysku, bez generowania czegokolwiek.

    Każdy dzień: „data" ISO, „przystanki", „kwota" co do grosza, „start",
    „koniec", „dokument" (numer delegacji z nazwy pliku) i „km" — kilometry
    dokumentu z rubryki „(1) Przejazdy" rozłożone na dni w proporcji kwot
    (etap w dokumencie ma kwotę, nie kilometry) albo None w starszych
    plikach bez tej rubryki. Lista rosnąco po dacie; folder bez czytelnych
    dokumentów daje pustą listę.
    """
    wynik = []
    for sciezka in dokumenty_w_folderze(folder):
        if rodzaj_dokumentu(sciezka) != RODZAJ_DELEGACJA:
            continue
        dni, liczby = _dni_i_liczby(sciezka)
        if not dni:
            continue
        suma = sum(d["kwota"] for d in dni)
        for d in dni:
            d["dokument"] = numer_delegacji(sciezka)
            if liczby["km"] is not None and suma > 0:
                d["km"] = round(float(liczby["km"]) * d["kwota"] / suma, 1)
            else:
                d["km"] = None
            wynik.append(d)
    wynik.sort(key=lambda d: d["data"])
    return wynik


def liczby_dokumentu(sciezka):
    """{"rodzaj", "kwota", "km", "stawka", "daty", "odleglosci"} z treści
    jednego PDF-u.

    rodzaj jak w rodzaj_dokumentu(); kwota to float co do grosza albo None,
    gdy pliku nie da się odczytać (_liczby_z_napisow); odleglosci to
    etykieta źródła odległości z nagłówka albo „" (_etykieta_odleglosci).
    """
    napisy = tekst_dokumentu(sciezka)
    wynik = _liczby_z_napisow(napisy)
    wynik["odleglosci"] = _etykieta_odleglosci(napisy)
    wynik["rodzaj"] = rodzaj_dokumentu(sciezka)
    return wynik


def liczby_kompletu(folder):
    """Liczby całego miesiąca z gotowych plików w folderze.

    Zwraca słownik:
        delegacje  liczba plików delegacja_NN
        kwota      suma kwot delegacji zaokrąglona do grosza; None, gdy choć
                   jednej delegacji nie dało się odczytać (wtedy bierzemy
                   kwotę z rozliczenia zbiorczego, jeśli jest)
        zbiorcza   kwota z rozliczenia zbiorczego albo None
        zgodne     True, gdy suma delegacji równa się kwocie zbiorczej co do
                   grosza (albo brak zbiorczej / brak sumy — nie ma czego
                   porównać)
        km         suma kilometrów z rubryk „(1) Przejazdy" albo None, gdy
                   choć jedna delegacja jej nie ma (starsze pliki)
        stawka     stawka z dokumentów (pierwsza napotkana) albo None
        daty       daty dni wyjazdowych ze wszystkich delegacji (ISO, rosnąco)
        odleglosci etykieta źródła odległości z pierwszej delegacji, która ją
                   ma („szacunek", „realne drogi", „drogi z pamięci") albo „"
    Folder pusty albo nieistniejący: delegacje 0, kwota None.
    """
    delegacje = 0
    kwota = 0.0
    kwota_znana = True
    km = 0.0
    km_znane = True
    stawka = None
    zbiorcza = None
    odleglosci = ""
    daty = set()
    for sciezka in dokumenty_w_folderze(folder):
        rodzaj = rodzaj_dokumentu(sciezka)
        if rodzaj == RODZAJ_DELEGACJA:
            delegacje += 1
            liczby = liczby_dokumentu(sciezka)
            if liczby["kwota"] is None:
                kwota_znana = False
            else:
                kwota += liczby["kwota"]
            if liczby["km"] is None:
                km_znane = False
            else:
                km += liczby["km"]
            if stawka is None and liczby["stawka"]:
                stawka = liczby["stawka"]
            if not odleglosci and liczby.get("odleglosci"):
                odleglosci = liczby["odleglosci"]
            daty.update(liczby["daty"])
        elif rodzaj == RODZAJ_ROZLICZENIE:
            zbiorcza = liczby_dokumentu(sciezka)["kwota"]
    suma = round(kwota, 2) if (delegacje and kwota_znana) else None
    if suma is None:
        wynik_kwota = zbiorcza
        zgodne = True
    else:
        wynik_kwota = suma
        zgodne = zbiorcza is None or abs(zbiorcza - suma) < 0.005
    return {"delegacje": delegacje, "kwota": wynik_kwota, "zbiorcza": zbiorcza,
            "zgodne": zgodne, "km": (round(km, 1) if (delegacje and km_znane) else None),
            "stawka": stawka, "daty": sorted(daty), "odleglosci": odleglosci}


# ────────────────────────────── samosprawdzenie ──────────────────────────────

_BLEDY = []


def _sprawdz(opis, warunek, szczegol=""):
    if warunek:
        print("  OK   %s" % opis)
    else:
        _BLEDY.append(opis)
        print("  BŁĄD %s%s" % (opis, ("  — " + szczegol) if szczegol else ""))


def _utworz(folder, nazwa, bajtow=1024):
    sciezka = os.path.join(folder, nazwa)
    with open(sciezka, "wb") as f:
        f.write(b"%PDF-1.4\n" + b"x" * max(0, bajtow - 9))
    return sciezka


def main():
    print("pmt_dokumenty — samosprawdzenie")
    katalog = tempfile.mkdtemp(prefix="pmt_dok_")
    try:
        komplet = os.path.join(katalog, "komplet")
        os.makedirs(komplet)
        _utworz(komplet, "delegacja_02_Jan_Kowalski_styczeń_2026r.pdf")
        _utworz(komplet, "delegacja_01_Jan_Kowalski_styczeń_2026r.pdf")
        _utworz(komplet, "delegacja_10_Jan_Kowalski_styczeń_2026r.pdf")
        _utworz(komplet, "DELEGACJA_03_ŁUKASZ_ŻÓŁW_grudzień_2026r.PDF")
        _utworz(komplet, "rozliczenie_wydatków_Jan_Kowalski_styczeń_2026r.pdf")
        _utworz(komplet, "Plan_Wizyt_2026-09-12.pdf")
        _utworz(komplet, "faktura_z_hotelu.pdf")
        _utworz(komplet, ".delegacja_99_ukryta.pdf")
        with open(os.path.join(komplet, "notatki.txt"), "w", encoding="utf-8") as f:
            f.write("nie PDF")
        os.makedirs(os.path.join(komplet, "delegacja_77_folder.pdf"))

        pliki = dokumenty_w_folderze(komplet)
        nazwy = [os.path.basename(p) for p in pliki]
        _sprawdz("rozpoznane tylko dokumenty programu (6 z 10 pozycji)",
                 len(pliki) == 6, repr(nazwy))
        _sprawdz("delegacje idą po numerach, nie alfabetycznie",
                 [numer_delegacji(n) for n in nazwy[:4]] == [1, 2, 3, 10], repr(nazwy))
        _sprawdz("wielkość liter i ogonki nie przeszkadzają",
                 "DELEGACJA_03_ŁUKASZ_ŻÓŁW_grudzień_2026r.PDF" in nazwy)
        _sprawdz("rozliczenie zbiorcze za delegacjami",
                 rodzaj_dokumentu(nazwy[4]) == RODZAJ_ROZLICZENIE, repr(nazwy))
        _sprawdz("wykaz planu wizyt na końcu",
                 rodzaj_dokumentu(nazwy[5]) == RODZAJ_PLAN, repr(nazwy))
        _sprawdz("obcy PDF pominięty", "faktura_z_hotelu.pdf" not in nazwy)
        _sprawdz("plik ukryty pominięty", ".delegacja_99_ukryta.pdf" not in nazwy)
        _sprawdz("folder o nazwie pliku pominięty",
                 "delegacja_77_folder.pdf" not in nazwy)
        _sprawdz("ta sama lista przy powtórnym wywołaniu",
                 dokumenty_w_folderze(komplet) == pliki)

        pierwszy = podsumowanie(komplet)
        _sprawdz("podsumowanie wskazuje rozliczenie zbiorcze",
                 pierwszy is not None
                 and rodzaj_dokumentu(pierwszy) == RODZAJ_ROZLICZENIE,
                 repr(pierwszy))

        opis = opis_kompletu(komplet)
        _sprawdz("opis liczy 4 delegacje i 2 inne pliki",
                 "4 delegacje" in opis and "2 inne pliki" in opis, opis)
        _sprawdz("opis podaje rozmiar", "kB" in opis or "MB" in opis or "B" in opis, opis)
        print("     opis kompletu: %s" % opis)

        # Folder bez rozliczenia zbiorczego — pierwsza delegacja.
        same_delegacje = os.path.join(katalog, "same_delegacje")
        os.makedirs(same_delegacje)
        _utworz(same_delegacje, "delegacja_05_Anna_Nowak_maj_2026r.pdf")
        _utworz(same_delegacje, "delegacja_04_Anna_Nowak_maj_2026r.pdf")
        wybrany = podsumowanie(same_delegacje)
        _sprawdz("bez rozliczenia wskazana pierwsza delegacja",
                 wybrany is not None and numer_delegacji(wybrany) == 4, repr(wybrany))
        _sprawdz("opis dla dwóch delegacji bez innych plików",
                 opis_kompletu(same_delegacje).startswith("2 delegacje")
                 and "inne" not in opis_kompletu(same_delegacje),
                 opis_kompletu(same_delegacje))

        # Nazwa zapisana w rozkładzie NFD (tak robi macOS).
        nfd = os.path.join(katalog, "nfd")
        os.makedirs(nfd)
        nazwa_nfd = unicodedata.normalize(
            "NFD", "rozliczenie_wydatków_Zofia_Wiśniewska_październik_2026r.pdf")
        _utworz(nfd, nazwa_nfd)
        _sprawdz("nazwa w rozkładzie NFD też rozpoznana",
                 len(dokumenty_w_folderze(nfd)) == 1,
                 repr(os.listdir(nfd)))

        # Folder pusty i folder nieistniejący.
        pusty = os.path.join(katalog, "pusty")
        os.makedirs(pusty)
        _sprawdz("pusty folder: pusta lista", dokumenty_w_folderze(pusty) == [])
        _sprawdz("pusty folder: brak podsumowania", podsumowanie(pusty) is None)
        _sprawdz("pusty folder: opis bez wyjątku", bool(opis_kompletu(pusty)))
        nieistniejacy = os.path.join(katalog, "nie_ma_takiego")
        _sprawdz("nieistniejący folder nie wywraca funkcji",
                 dokumenty_w_folderze(nieistniejacy) == []
                 and podsumowanie(nieistniejacy) is None
                 and bool(opis_kompletu(nieistniejacy)))
        _sprawdz("pusta ścieżka i None nie wywracają funkcji",
                 dokumenty_w_folderze("") == [] and dokumenty_w_folderze(None) == []
                 and podsumowanie(None) is None)

        _sprawdz("odmiana liczebnika",
                 _odmiana(1, "delegacja", "delegacje", "delegacji") == "1 delegacja"
                 and _odmiana(3, "delegacja", "delegacje", "delegacji") == "3 delegacje"
                 and _odmiana(5, "delegacja", "delegacje", "delegacji") == "5 delegacji"
                 and _odmiana(12, "delegacja", "delegacje", "delegacji") == "12 delegacji"
                 and _odmiana(22, "delegacja", "delegacje", "delegacji") == "22 delegacje")
        _sprawdz("rozmiar po ludzku",
                 _rozmiar(512) == "512 B" and _rozmiar(1536) == "1,5 kB"
                 and _rozmiar(5 * 1024 * 1024) == "5,0 MB",
                 "%s %s %s" % (_rozmiar(512), _rozmiar(1536), _rozmiar(5 * 1024 * 1024)))

        # Dni z tabeli przejazdów: dwa dni, trzy etapy; powrót do bazy to
        # nie przystanek, kwota dnia to suma etapów co do grosza.
        napisy = ["Odległości: szacunek", "WYJAZD", "PRZYJAZD",
                  "Radom", "02.03.2026r", "07:52", "Skaryszew", "02.03.2026r", "08:07",
                  "samochód osobowy", "15.22",
                  "Skaryszew", "02.03.2026r", "08:20", "Radom", "02.03.2026r", "08:40",
                  "samochód osobowy", "19.07",
                  "Radom", "03.03.2026r", "07:14", "Rusinów", "03.03.2026r", "08:11",
                  "samochód osobowy", "54.98",
                  "Suma wydatków", "89.27"]
        dni = _dni_z_napisow(napisy)
        _sprawdz("dni z tabeli przejazdów: dwa dni, przystanki bez powrotu, kwota co do grosza, godziny",
                 [d["data"] for d in dni] == ["2026-03-02", "2026-03-03"]
                 and dni[0]["przystanki"] == ["Skaryszew"] and dni[0]["kwota"] == 34.29
                 and dni[0]["start"] == "07:52" and dni[0]["koniec"] == "08:40"
                 and dni[1]["przystanki"] == ["Rusinów"] and dni[1]["kwota"] == 54.98,
                 repr(dni))
        _sprawdz("etykieta źródła odległości czytana z nagłówka dokumentu",
                 _etykieta_odleglosci(napisy) == "szacunek" and _etykieta_odleglosci([]) == ""
                 and "odleglosci" not in _liczby_z_napisow(napisy),
                 repr(_etykieta_odleglosci(napisy)))
        _sprawdz("bez tabeli przejazdów — pusta lista, nie wyjątek",
                 _dni_z_napisow(["Suma wydatków", "10.00"]) == [] and _dni_z_napisow([]) == []
                 and dni_dokumentu(os.path.join(komplet, "faktura_z_hotelu.pdf")) == []
                 and dni_kompletu(komplet) == [] and dni_kompletu(nieistniejacy) == [])
    finally:
        shutil.rmtree(katalog, ignore_errors=True)

    if _BLEDY:
        print("NIE PRZESZŁO: %d" % len(_BLEDY))
        return 1
    print("WSZYSTKO PRZESZŁO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
