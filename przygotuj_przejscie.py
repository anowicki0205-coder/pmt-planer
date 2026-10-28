#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Przejście na aplikację web: z adresu i daty robi gotowe wiersze do wersja.txt oraz gotowe wiadomości.

    python przygotuj_przejscie.py https://adres-aplikacji/ 2026-12-21
    python przygotuj_przejscie.py https://adres-aplikacji/ 2026-12-21 --blokada 2026-11-30

  adres   stały adres aplikacji web (https, bez parametrów)
  data    pierwszy dzień, w którym program na komputerze się już nie uruchomi (RRRR-MM-DD)
  --blokada  dzień, od którego starsze wersje muszą się zaktualizować (domyślnie dziś + 14 dni)

Wynik trafia na ekran i do pliku PRZEJSCIE_gotowe.txt (obok tego skryptu). Skrypt niczego nie wysyła
i niczego nie zmienia w repozytorium — wiersze do wersja.txt wklejasz sam, według PRZEJSCIE_NA_WEB.txt.
"""
import argparse
import datetime
import os
import re
import sys

KATALOG = os.path.dirname(os.path.abspath(__file__))
DNI_OKRESU_PRZEJSCIOWEGO = 14      # tyle program daje po ogłoszeniu nowego progu min= (patrz PMT_Delegacje.py)
MIN_DNI_MIEDZY_BLOKADA_A_WYGASZENIEM = 7
DNI_TYGODNIA = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")
MIESIACE = ("stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia",
            "września", "października", "listopada", "grudnia")
# ten sam wzorzec co _adres_web_poprawny w PMT_Delegacje.py (test pilnuje, żeby się nie rozjechały)
WZORZEC_ADRESU = r"^https://[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}(:\d{1,5})?(/[A-Za-z0-9._~%/-]*)?$"


class BladDanych(Exception):
    """Zły adres albo zła data — komunikat jest po polsku i mówi, co poprawić."""


def numer_wersji(katalog=KATALOG) -> str:
    """Numer wersji programu ze źródła (jedyne miejsce, w którym on jest)."""
    with open(os.path.join(katalog, "PMT_Delegacje.py"), encoding="utf-8") as f:
        m = re.search(r'WERSJA_PROGRAMU\s*=\s*"([^"]+)"', f.read())
    if not m:
        raise BladDanych("Nie znalazłem numeru wersji w PMT_Delegacje.py.")
    return m.group(1)


def sprawdz_adres(adres: str) -> str:
    adres = str(adres or "").strip()
    if not adres.startswith("https://"):
        raise BladDanych("Adres musi zaczynać się od https:// (zwykłe http:// nie jest dozwolone), a dostałem: %r" % adres)
    if len(adres) > 200 or not re.match(WZORZEC_ADRESU, adres):
        raise BladDanych("Adres %r nie wygląda na adres strony: ma być sama nazwa serwera i ewentualnie ścieżka, "
                         "bez ?parametrów, #znaczników, spacji i hasła w adresie." % adres)
    return adres


def czytaj_date(tekst: str, nazwa: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(str(tekst).strip(), "%Y-%m-%d").date()
    except ValueError:
        raise BladDanych("%s: data ma mieć format RRRR-MM-DD (np. 2026-12-21), a dostałem: %r" % (nazwa, tekst))


def opis_daty(d: datetime.date) -> str:
    return "%d %s %d (%s)" % (d.day, MIESIACE[d.month - 1], d.year, DNI_TYGODNIA[d.weekday()])


def poprzedni_roboczy(d: datetime.date) -> datetime.date:
    """Ostatni dzień roboczy (pon–pt) przed dniem d — „do kiedy jeszcze pracujesz w programie”."""
    d = d - datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d


def przygotuj(adres, wygaszenie, dzis=None, blokada=None, wersja=None):
    """Zwraca słownik: wiersze (do wersja.txt), uwagi (ostrzeżenia) i teksty wiadomości."""
    dzis = dzis or datetime.date.today()
    adres = sprawdz_adres(adres)
    wygaszenie = wygaszenie if isinstance(wygaszenie, datetime.date) else czytaj_date(wygaszenie, "Data wyłączenia")
    if blokada is None:
        blokada = dzis + datetime.timedelta(days=DNI_OKRESU_PRZEJSCIOWEGO)
    elif not isinstance(blokada, datetime.date):
        blokada = czytaj_date(blokada, "Data blokady")
    wersja = wersja or numer_wersji()

    if wygaszenie <= dzis:
        raise BladDanych("Data wyłączenia (%s) musi być w przyszłości." % opis_daty(wygaszenie))
    if wygaszenie < blokada + datetime.timedelta(days=MIN_DNI_MIEDZY_BLOKADA_A_WYGASZENIEM):
        raise BladDanych(
            "Data wyłączenia (%s) jest za blisko daty blokady (%s). Starsze wersje muszą mieć czas, żeby się zaktualizować "
            "i zobaczyć informację — wyłączenie ma być co najmniej %d dni PO blokadzie."
            % (opis_daty(wygaszenie), opis_daty(blokada), MIN_DNI_MIEDZY_BLOKADA_A_WYGASZENIEM))

    uwagi = []
    if blokada < dzis + datetime.timedelta(days=DNI_OKRESU_PRZEJSCIOWEGO):
        uwagi.append("Blokada wcześniej niż za %d dni: program i tak da każdemu %d dni od pierwszego zobaczenia nowego progu, "
                     "więc ta data nic nie przyspieszy." % (DNI_OKRESU_PRZEJSCIOWEGO, DNI_OKRESU_PRZEJSCIOWEGO))
    for nazwa, d in (("blokady", blokada), ("wyłączenia", wygaszenie)):
        if d.weekday() >= 5:
            uwagi.append("Dzień %s (%s) wypada w weekend — lepiej, żeby to był dzień roboczy, gdy ktoś jest pod telefonem."
                         % (nazwa, opis_daty(d)))

    wiersze = ["min=%s" % wersja, "blokada=%s" % blokada.isoformat(),
               "web=%s" % adres, "wygaszenie=%s" % wygaszenie.isoformat()]
    ostatni = poprzedni_roboczy(wygaszenie)
    tresc = {"adres": adres, "wygaszenie": opis_daty(wygaszenie), "ostatni": opis_daty(ostatni),
             "blokada": opis_daty(blokada), "wersja": wersja}
    return {"wiersze": wiersze, "uwagi": uwagi, "dane": tresc,
            "krotka": _wiadomosc_krotka(tresc), "dluga": _instrukcja(tresc),
            "przypomnienie": _przypomnienie(tresc), "dzien_wylaczenia": _dzien_wylaczenia(tresc)}


def _wiadomosc_krotka(t):
    return """Temat: PMT Planer — od {wygaszenie} tylko w przeglądarce i na telefonie

Cześć,

program PMT Planer na komputerze przestaje działać. Ostatni dzień roboczy z programem: {ostatni}; od {wygaszenie} już się nie uruchomi.
Od teraz pracujemy w aplikacji w przeglądarce i na telefonie:

    {adres}

Co robisz:
  1. Otwórz ten adres (Chrome, Edge albo Safari).
  2. Zaloguj się tym samym kodem (5 cyfr) i tym samym hasłem co w programie. Nie pamiętasz hasła? Na ekranie logowania jest „Nie pamiętam hasła”.
  3. Przy pierwszym wejściu wpisz swoje dane (Moje dane) i wczytaj listę sklepów z Excela.

Dane zapisane w programie na komputerze nie przenoszą się same. Dokumenty wygenerowane wcześniej zostają na dysku, tam gdzie są.
Jeśli program poprosi o aktualizację do wersji {wersja} — zaktualizuj: to ostatnia wersja i pokaże ten sam adres.

Jeśli coś nie działa albo adres się nie otwiera — napisz do mnie, zanim minie termin.
""".format(**t)


def _instrukcja(t):
    return """PMT Planer — przejście na aplikację w przeglądarce i na telefonie (instrukcja i pytania)

KIEDY
  Ostatni dzień roboczy z programem na komputerze: {ostatni}. Od {wygaszenie} program się nie uruchomi. Starsze wersje muszą zaktualizować się do {wersja} najpóźniej do {blokada}.

GDZIE
  {adres}

JAK SIĘ ZALOGOWAĆ
  Ten sam kod (5 cyfr) i to samo hasło co w programie. Zapomniane hasło: „Nie pamiętam hasła” na ekranie logowania.

TELEFON
  Otwórz ten sam adres w przeglądarce telefonu. W menu konta wybierz „Zainstaluj na telefonie” — aplikacja pojawi się na ekranie głównym.
  (iPhone: Safari → Udostępnij → Dodaj do ekranu początkowego.) Po pierwszym wejściu działa też bez internetu; wtedy kilometry są z szacunku, a dokument to zaznacza.

PIERWSZE WEJŚCIE — CO ZROBIĆ
  1. Moje dane: imię i nazwisko, PESEL, adres, stanowisko. Wpisujesz raz.
  2. Lista sklepów: wczytaj plik z Excela (.xlsx) albo .csv — ten sam, którego używasz w programie. Kolumny rozpoznam po nagłówkach.
  3. Wybierz kwotę i dni, sprawdź podsumowanie i wygeneruj dokumenty, jak dotąd.

PYTANIA
  Czy moje dane z programu przeniosą się same?  Nie. Moje dane i listę sklepów wpisujesz raz. Wygenerowane wcześniej dokumenty zostają na dysku.
  Gdzie są moje PESEL i dokumenty?  Na Twoim urządzeniu, w przeglądarce, zaszyfrowane Twoim hasłem. Nie wysyłamy ich na serwer. Do map wychodzą tylko adresy potrzebne do policzenia kilometrów (bez imienia i PESEL-u).
  Zmieniłem hasło na innym urządzeniu — i co?  Aplikacja zapyta o poprzednie hasło albo pozwoli zacząć od nowa na tym urządzeniu (dokumenty wygenerujesz ponownie). Zapomniane hasło oznacza utratę danych zapisanych na TYM urządzeniu.
  Sieć w firmie blokuje adres.  Napisz do mnie — poszukamy innego sposobu. Spróbuj też na telefonie w sieci komórkowej.
  Kiedy mogę usunąć stare dane z komputera?  Dopiero gdy pracujesz w aplikacji i masz w niej swoje dane. Wtedy: Eksplorator → wpisz %USERPROFILE% → usuń pliki, których nazwa zaczyna się od .pmt_ (leży w nich zapisany w programie PESEL i plan). Dokumentów w folderach nie ruszaj.
""".format(**t)


def _przypomnienie(t):
    return """Temat: PMT Planer — przypominam: ostatni dzień roboczy z programem to {ostatni}

Cześć,

przypominam: ostatni dzień roboczy z programem PMT Planer na komputerze to {ostatni}, od {wygaszenie} się nie uruchomi. Aplikacja w przeglądarce i na telefonie:

    {adres}

Kod i hasło masz te same co w programie. Jeśli jeszcze nie logujesz się do aplikacji, zrób to dziś: wpisz Moje dane i wczytaj listę sklepów, żeby nie zostawiać tego na ostatni dzień.
Jak coś nie działa — napisz.
""".format(**t)


def _dzien_wylaczenia(t):
    return """Temat: PMT Planer — od dziś tylko aplikacja w przeglądarce

Cześć,

od dziś program PMT Planer na komputerze się nie uruchamia. Pracujemy w aplikacji:

    {adres}

Kod i hasło te same. Gdyby coś nie działało — dzwoń albo pisz od razu.
""".format(**t)


def zloz_plik(wynik) -> str:
    podziel = "=" * 78
    linie = [
        "PMT Planer — przejście na aplikację web: GOTOWE TEKSTY",
        "Wygenerowane przez przygotuj_przejscie.py. Niczego nie wysłano i nic w repozytorium nie zmieniono.",
        "",
        podziel, "1. WIERSZE DO wersja.txt (GitHub → wersja.txt → Edit)", podziel,
        "Dwóch pierwszych linii pliku (numer wersji i opis) NIE ruszaj. Wszystko od trzeciej linii zamień na:", ""]
    linie += ["    " + w for w in wynik["wiersze"]]
    linie += ["", "Po zapisie sprawdź (1–5 min): https://raw.githubusercontent.com/anowicki0205-coder/pmt-planer/main/wersja.txt — ma być 6 linii, "
              "a pierwsza to numer wersji.", ""]
    if wynik["uwagi"]:
        linie += ["UWAGI:"] + ["  · " + u for u in wynik["uwagi"]] + [""]
    for tytul, klucz in (("2. WIADOMOŚĆ DO ZESPOŁU (wyślij w dniu wydania — e-mail albo komunikator)", "krotka"),
                         ("3. INSTRUKCJA I PYTANIA (jako załącznik albo druga wiadomość)", "dluga"),
                         ("4. PRZYPOMNIENIE (tydzień przed terminem wyłączenia)", "przypomnienie"),
                         ("5. DZIEŃ WYŁĄCZENIA", "dzien_wylaczenia")):
        linie += [podziel, tytul, podziel, "", wynik[klucz].rstrip(), ""]
    return "\n".join(linie)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gotowe wiersze do wersja.txt i wiadomości dla zespołu.")
    ap.add_argument("adres", help="stały adres aplikacji web, https://…")
    ap.add_argument("data", help="pierwszy dzień bez programu na komputerze, RRRR-MM-DD")
    ap.add_argument("--blokada", help="dzień obowiązkowej aktualizacji, RRRR-MM-DD (domyślnie dziś + 14 dni)")
    ap.add_argument("--dzis", help=argparse.SUPPRESS)
    ap.add_argument("--wyjscie", help="plik wynikowy (domyślnie PRZEJSCIE_gotowe.txt obok skryptu)")
    arg = ap.parse_args(argv)
    try:
        dzis = czytaj_date(arg.dzis, "--dzis") if arg.dzis else None
        wynik = przygotuj(arg.adres, arg.data, dzis=dzis, blokada=arg.blokada)
    except BladDanych as e:
        print("BŁĄD: %s" % e, file=sys.stderr)
        return 2
    tekst = zloz_plik(wynik)
    wyjscie = arg.wyjscie or os.path.join(KATALOG, "PRZEJSCIE_gotowe.txt")
    with open(wyjscie, "w", encoding="utf-8", newline="\n") as f:
        f.write(tekst + "\n")
    print(tekst)
    print("\nZapisano też w pliku: %s" % wyjscie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
