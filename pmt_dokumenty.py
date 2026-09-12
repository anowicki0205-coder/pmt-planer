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
    finally:
        shutil.rmtree(katalog, ignore_errors=True)

    if _BLEDY:
        print("NIE PRZESZŁO: %d" % len(_BLEDY))
        return 1
    print("WSZYSTKO PRZESZŁO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
