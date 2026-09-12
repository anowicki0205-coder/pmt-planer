# -*- coding: utf-8 -*-
"""PMT PLANER — NOWY WYGLĄD NA PRAWDZIWYM SILNIKU.

Pierwszy krok wdrożenia nowego wyglądu: ekran złożony z widżetów prototypu
(prototyp/proto_*.py), ale zasilany danymi i silnikiem z PMT_Delegacje.py.

    python PMT_Delegacje.py --nowy      (tak uruchamia go program)
    python nowy_wyglad.py               (samodzielnie, do pracy nad wyglądem)
    python nowy_wyglad.py --zrzut       (bez ekranu: zrzuty do plików PNG)

CO JEST PRAWDZIWE
    · pracownik            profil z ~/.pmt_uzytkownicy.json (zapisz_profil)
    · dni robocze          pobierz_dni_robocze + ustaw_tryb_pracy
    · miasta i odległości  zaladuj_baze, coords_z_miasta, oblicz_dystans
    · trasy, km i kwoty    generuj_trasy  (w osobnym wątku, GeneratorThread)
    · dokumenty PDF        generuj_pdfy + generuj_mape_html (ten sam wątek)
    · pliki na tacy        pmt_dokumenty.dokumenty_w_folderze(folder wyniku)

CO JEST SZACUNKIEM (do chwili wygenerowania)
    podglad_miesiaca() — rozkład kwoty na dni liczony tymi samymi wzorami co
    silnik, ale bez układania tras. Po wygenerowaniu podgląd znika, a jego
    miejsce zajmuje prawdziwy wynik przetłumaczony przez dni_widzetow_z_tras().

CZEGO JESZCZE NIE MA — funkcje z przedrostkiem „zastepczy_" i sekcja
„NIEPODŁĄCZONE" na końcu pliku.
"""

import datetime
import math
import os
import sys


# ═══════════════════════════════════════════════════════════════════════
#  DOSTĘP DO PRAWDZIWEGO PROGRAMU I DO WIDŻETÓW PROTOTYPU
# ═══════════════════════════════════════════════════════════════════════

def modul_programu():
    """Moduł PMT_Delegacje — bez wczytywania go drugi raz.

    Gdy to program nas uruchomił (python PMT_Delegacje.py --nowy), jest on
    pod nazwą „__main__". Zwykły import zrobiłby wtedy DRUGĄ kopię modułu
    z własnymi stałymi i własnym cache miast. Rejestrujemy więc ten sam
    moduł pod obiema nazwami."""
    modul = sys.modules.get("PMT_Delegacje")
    if modul is not None:
        return modul
    glowny = sys.modules.get("__main__")
    if glowny is not None and hasattr(glowny, "generuj_trasy") \
            and hasattr(glowny, "WERSJA_PROGRAMU"):
        sys.modules["PMT_Delegacje"] = glowny
        return glowny
    import PMT_Delegacje as modul
    return modul


def katalog_prototypu():
    """Katalog z widżetami nowego wyglądu — działa też po spakowaniu.

    PyInstaller rozpakowuje program do katalogu tymczasowego (sys._MEIPASS)
    i kładzie tam moduły płasko, więc sprawdzamy oba układy: podkatalog
    „prototyp" i katalog obok programu."""
    miejsca = []
    paczka = getattr(sys, "_MEIPASS", "")
    if paczka:
        miejsca += [os.path.join(paczka, "prototyp"), paczka]
    tutaj = os.path.dirname(os.path.abspath(__file__))
    miejsca += [os.path.join(tutaj, "prototyp"), tutaj]
    for katalog in miejsca:
        if os.path.isfile(os.path.join(katalog, "proto_okno.py")):
            return katalog
    return os.path.join(tutaj, "prototyp")


def _wepnij_prototyp():
    katalog = katalog_prototypu()
    if katalog not in sys.path:
        sys.path.insert(0, katalog)
    return katalog


PMT = modul_programu()
KATALOG_PROTOTYPU = _wepnij_prototyp()

from PyQt6.QtCore import Qt                                        # noqa: E402
from PyQt6.QtWidgets import QApplication                           # noqa: E402

import proto_styl as S                                             # noqa: E402
import proto_dane as D                                             # noqa: E402
import proto_okno as OK                                            # noqa: E402
from proto_mapa import MapaDnia                                    # noqa: E402
from proto_okno import OknoPrototypu, arkusz                       # noqa: E402
from proto_taca import PanelPodpisu, PanelWysylki                  # noqa: E402

import pmt_dokumenty as DOK                                        # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  STAŁE PRZEPISANE Z SILNIKA
#  Wszystkie inne bierzemy wprost z modułu (PMT.MAX_KWOTA_DNIA itd.).
#  Te siedzą WEWNĄTRZ generuj_trasy jako zmienne lokalne i nie da się ich
#  stamtąd odczytać — dlatego są tu, każda z adresem oryginału.
# ═══════════════════════════════════════════════════════════════════════
ZL_NA_DZIEN_MIN = 110.0        # PMT_Delegacje.py, generuj_trasy, linia 6200
ZAPAS_DNIA = 0.85              # PMT_Delegacje.py, generuj_trasy, linia 6194
# Ile kilometrów wypada realnie na jeden dzień wyjazdowy. Silnik ma u siebie
# szacunek wstępny 90 km (linia 6191), ale potem sam dokłada i przycina dni,
# aż trasy pokryją kwotę — i kończy zupełnie gdzie indziej. Ta liczba jest
# ZMIERZONA na wynikach generuj_trasy dla czterech baz (Warszawa, Poznań,
# Kraków, Suwałki) i kwot 600/1850/4000/8000 zł: podgląd daje wtedy 3/8/16/22
# dni, a silnik 2-3/8-10/15-17/20-21. Szacunkiem 90 km wychodziłoby dwa razy
# więcej dni, niż silnik naprawdę robi.
KM_NA_DZIEN_PODGLAD = 220.0

STANOWISKA = ("merchandiser", "KR")   # te same pozycje, co w App (linia 19188)
MIAST_NA_MAPIE = 28            # ile miast rysuje mapa (reszta tylko zaśmieca)
MIAST_PRZY_BAZIE = 10          # z tego tyle spod samej bazy — tam jeżdżą krótkie dni
KM_NA_JEDNOSTKE = 235.0        # 1,0 w układzie mapy = tyle kilometrów
GODZINA_STARTU = 7 * 60        # podgląd: wyjazd z bazy


# ═══════════════════════════════════════════════════════════════════════
#  DANE PRACOWNIKA
# ═══════════════════════════════════════════════════════════════════════

class ProfilWidoku:
    """Komplet danych pracownika, którymi karmimy ekran i silnik."""

    def __init__(self, imie, pesel, adres, stanowisko, silnik_idx=1,
                 zrodlo="profil"):
        self.imie = str(imie or "")
        self.pesel = str(pesel or "")
        self.adres = str(adres or "")
        self.stanowisko = str(stanowisko or "KR")
        self.silnik_idx = int(silnik_idx if silnik_idx in (0, 1) else 1)
        self.zrodlo = zrodlo          # "profil" albo "zastepczy"

    @property
    def stawka(self):
        """Ta sama reguła co w programie (App.proces, linia 21219)."""
        return 0.89 if self.silnik_idx == 0 else 1.15

    @property
    def prawdziwy(self):
        return self.zrodlo == "profil"


def profil_z_programu():
    """Ostatnio używany profil z magazynu programu albo None.

    Magazyn (~/.pmt_uzytkownicy.json) trzyma wpisy {profil, historia}.
    Bierzemy ten, którego historia generowań jest najświeższa."""
    try:
        magazyn = PMT._wczytaj_store()
    except Exception:
        return None
    najlepszy, najlepsza_data = None, None
    for wpis in (magazyn or {}).values():
        if not isinstance(wpis, dict):
            continue
        profil = wpis.get("profil")
        if not isinstance(profil, dict) or not profil.get("imie"):
            continue
        data = None
        for pozycja in (wpis.get("historia") or []):
            if not isinstance(pozycja, dict):
                continue
            try:
                data = datetime.datetime.strptime(str(pozycja.get("data", "")),
                                                  "%d.%m.%Y %H:%M")
            except (TypeError, ValueError):
                data = None
            break
        if najlepszy is None or (data is not None
                                 and (najlepsza_data is None or data > najlepsza_data)):
            najlepszy, najlepsza_data = profil, data
    if najlepszy is None:
        return None
    return ProfilWidoku(najlepszy.get("imie", ""), najlepszy.get("pesel", ""),
                        najlepszy.get("adres", ""), najlepszy.get("stanowisko", "KR"),
                        najlepszy.get("silnik_idx", 1), "profil")


def zastepczy_profil_pracownika():
    """ZASTĘPNIK. Program bez ani jednego zapisanego profilu — nowy wygląd
    nie ma jeszcze własnego logowania, więc pokazuje dane przykładowe
    i odmawia generowania (patrz OknoNowegoWygladu._dane_do_generacji)."""
    return ProfilWidoku("BRAK PROFILU", "", "", "KR", 1, "zastepczy")


def dane_pracownika():
    """Profil do ekranu: prawdziwy, a gdy go nie ma — zastępczy."""
    profil = profil_z_programu()
    if profil is None:
        return zastepczy_profil_pracownika()
    imie = PMT.online_imie_uzytkownika()
    if imie and not profil.imie:
        profil.imie = imie
    return profil


def miesiac_biezacy():
    dzis = datetime.date.today()
    return dzis.year, dzis.month


# ═══════════════════════════════════════════════════════════════════════
#  ŚWIAT MAPY: prawdziwe miasta w układzie, którego oczekuje prototyp
# ═══════════════════════════════════════════════════════════════════════

def _km_wzgledem_bazy(lat, lng, baza_lat, baza_lng):
    """Przesunięcie miasta względem bazy w kilometrach (x w prawo, y w dół)."""
    x = (lng - baza_lng) * 111.32 * math.cos(math.radians(baza_lat))
    y = -(lat - baza_lat) * 110.57
    return x, y


def miasta_w_ukladzie_mapy(geo, baza_nazwa, baza_lat, baza_lng):
    """{nazwa: (x, y)} w ułamkach 0..1 — tak prototyp trzyma MIASTA.

    Skala jest ta sama, co w proto_dane (1,0 = 235 km), więc odległości na
    mapie zgadzają się z kilometrami. Gdy rejon jest tak rozległy, że nie
    mieści się w kadrze, cała mapa jest proporcjonalnie zmniejszana —
    kilometry na ekranie pochodzą wtedy i tak z silnika, nie z rysunku."""
    punkty = {baza_nazwa: (0.0, 0.0)}
    for nazwa, (lat, lng) in geo.items():
        if nazwa == baza_nazwa:
            continue
        punkty[nazwa] = _km_wzgledem_bazy(lat, lng, baza_lat, baza_lng)
    zasieg = max([max(abs(x), abs(y)) for x, y in punkty.values()] or [1.0])
    skala = 1.0 / KM_NA_JEDNOSTKE
    if zasieg * skala > 0.46:                     # 0,5 to krawędź kadru
        skala = 0.46 / max(zasieg, 1.0)
    return {n: (0.5 + x * skala, 0.5 + y * skala) for n, (x, y) in punkty.items()}


def _petle_z_miast(miasta, baza_nazwa):
    """Kilka pętli dziennych dla podglądu — miasta pogrupowane kierunkami."""
    inne = [n for n in miasta if n != baza_nazwa]
    if not inne:
        return [[]]
    bx, by = miasta.get(baza_nazwa, (0.5, 0.5))
    inne.sort(key=lambda n: math.atan2(miasta[n][1] - by, miasta[n][0] - bx))
    petle, biezaca = [], []
    for nazwa in inne:
        biezaca.append(nazwa)
        if len(biezaca) >= 4:
            petle.append(biezaca)
            biezaca = []
    if biezaca:
        petle.append(biezaca)
    return petle or [[inne[0]]]


def ustaw_swiat_mapy(geo, baza_nazwa, baza_lat, baza_lng, profil=None):
    """Wkłada prawdziwe miasta i prawdziwego pracownika do proto_dane.

    Widżety prototypu (mapa, kartka delegacji, pasek górny) czytają te
    nazwy jako zwykłe stałe modułu — to jest miejsce, w którym prototypowa
    Warszawa Anny Nowak zamienia się w rejon prawdziwego użytkownika."""
    D.MIASTA = miasta_w_ukladzie_mapy(geo, baza_nazwa, baza_lat, baza_lng)
    D.BAZA = baza_nazwa
    D.PETLE = _petle_z_miast(D.MIASTA, baza_nazwa)
    if profil is not None:
        D.PRACOWNIK = profil.imie or "—"
        D.STANOWISKO = profil.stanowisko or "—"
        D.ADRES = profil.adres or "—"
        D.STAWKA = profil.stawka
    try:
        D.MENEDZER = PMT._menedzer() or "(brak pliku menedzer.txt)"
    except Exception:
        D.MENEDZER = "(brak pliku menedzer.txt)"
    return D.MIASTA


PROMIEN_MAPY_KM = 115.0        # tyle terenu pokazuje mapa wokół bazy


def miasta_wokol_bazy(baza_nazwa, baza_lat, baza_lng, woj, ile=MIAST_NA_MAPIE,
                      promien=PROMIEN_MAPY_KM):
    """Miasta z PRAWDZIWEJ bazy programu wokół bazy: {nazwa: (lat, lng)}.

    Bierzemy je z całego promienia, a nie same najbliższe — inaczej wszystkie
    wypadłyby w jednym punkcie mapy. Gdy w promieniu jest ich więcej, niż mapa
    ma pokazać, wybieramy co któreś z listy ułożonej odległością, więc zostają
    i te pod bazą, i te na obrzeżu."""
    geo = {baza_nazwa: (baza_lat, baza_lng)}
    try:
        baza = PMT.zaladuj_baze(baza_lat, baza_lng)
    except Exception:
        return geo
    sasiednie = [w for w in PMT.SASIEDZI_WOJ.get(woj, []) if w != woj]
    kandydaci, widziane = [], {baza_nazwa}
    for obszar in [woj] + sasiednie:
        for miasto in baza.get(obszar, []):
            if miasto.n in widziane:
                continue
            odleglosc = PMT.oblicz_dystans(baza_lat, baza_lng, miasto.lat, miasto.lng)
            if odleglosc < PMT.MIN_ODLEGLOSC_OD_BAZY or odleglosc > promien:
                continue
            widziane.add(miasto.n)
            kandydaci.append((odleglosc, miasto))
    kandydaci.sort(key=lambda para: para[0])
    brakuje = max(0, int(ile) - 1)
    if brakuje > 1 and len(kandydaci) > brakuje:
        # komplet spod bazy (krótkie dni jeżdżą właśnie tam) plus równomierna
        # próbka reszty aż po najdalsze miasto — mapa nie kończy się w połowie
        blisko = min(MIAST_PRZY_BAZIE, brakuje - 1)
        dalej = kandydaci[blisko:]
        ile_dalej = brakuje - blisko
        ostatni = len(dalej) - 1
        wybrane = sorted({int(round(i * ostatni / max(1.0, ile_dalej - 1.0)))
                          for i in range(ile_dalej)})
        kandydaci = kandydaci[:blisko] + [dalej[i] for i in wybrane]
    for _odleglosc, miasto in kandydaci[:brakuje]:
        geo[miasto.n] = (miasto.lat, miasto.lng)
    return geo


def wspolrzedne_bazy(baza_miasto, adres_geo, woj):
    """Współrzędne bazy BEZ sięgania do internetu.

    Kolejność: pamięć podręczna geokodowania → offline'owy indeks miast
    programu → stolica województwa. Dokładne współrzędne (z Nominatim)
    wyznacza dopiero wątek generowania — tam wolno czekać na sieć."""
    try:
        zapamietane = PMT._geo_cache.get(str(adres_geo or "").lower().strip())
        if zapamietane:
            return float(zapamietane[0]), float(zapamietane[1])
    except Exception:
        pass
    try:
        z_bazy = PMT.coords_z_miasta(baza_miasto)
        if z_bazy:
            return float(z_bazy[0]), float(z_bazy[1])
    except Exception:
        pass
    return PMT.STOLICE.get(woj, (52.23, 21.01))


# ═══════════════════════════════════════════════════════════════════════
#  PODGLĄD — zanim cokolwiek zostanie wygenerowane
# ═══════════════════════════════════════════════════════════════════════

def dni_robocze_realne(rok, miesiac, tryb):
    """Dni robocze z programu; tryb ustawiany tak jak przed generowaniem."""
    PMT.ustaw_tryb_pracy("wieczory" if str(tryb).lower().startswith("wiecz")
                         else "tydzien")
    return PMT.pobierz_dni_robocze(rok, miesiac)


def ile_dni_wyjazdowych(kwota, stawka, dostepnych, limit_dnia):
    """Liczba dni wyjazdowych — ten sam rachunek co w generuj_trasy.

    Kolejno: z kilometrów (kwota/stawka podzielone przez dzienny szacunek),
    z limitu delegacji (kwota / 85% limitu) i sufit z dolnego progu dnia."""
    if kwota <= 0 or stawka <= 0 or dostepnych <= 0:
        return 0
    z_km = math.ceil((kwota / stawka) / KM_NA_DZIEN_PODGLAD)
    z_limitu = math.ceil(kwota / (float(limit_dnia) * ZAPAS_DNIA))
    potrzeba = max(3, z_km, z_limitu)
    potrzeba = min(potrzeba, max(3, math.floor(kwota / ZL_NA_DZIEN_MIN)))
    return max(1, min(dostepnych, potrzeba))


def _rozdziel_rowno(kwota, ile):
    grosze = int(round(kwota * 100))
    baza, reszta = divmod(grosze, max(1, ile))
    return [(baza + (1 if i < reszta else 0)) / 100.0 for i in range(ile)]


def _rozloz_rownomiernie(kandydaci, ile):
    if ile >= len(kandydaci):
        return list(kandydaci)
    krok = len(kandydaci) / float(ile)
    indeksy = sorted({int(i * krok) for i in range(ile)})
    i = 0
    while len(indeksy) < ile and i < len(kandydaci):
        if i not in indeksy:
            indeksy.append(i)
            indeksy.sort()
        i += 1
    return [kandydaci[i] for i in indeksy[:ile]]


SEKTOROW_PODGLADU = 8          # na tyle kierunków dzielimy okolicę bazy


def _sektor_miasta(lat, lng, baza_lat, baza_lng):
    kat = math.degrees(math.atan2(lng - baza_lng, lat - baza_lat)) % 360.0
    return int(kat // (360.0 / SEKTOROW_PODGLADU))


def _trasa_podgladu(cel_km, geo, baza_nazwa, ziarno):
    """Pętla z prawdziwych miast o długości zbliżonej do celu.

    Najpierw kierunek (kolejne dni jadą w kolejne strony świata — tak jak
    silnik rozdziela sektory), potem zachłannie najbliższy jeszcze
    nieodwiedzony sąsiad, dopóki powrót do bazy mieści się w kilometrach
    dnia. Prawdziwy dobór (sieci, karencja miast, limit czasu) robi
    generuj_trasy — tu chodzi wyłącznie o skalę i kierunek."""
    if cel_km <= 1.0 or baza_nazwa not in geo:
        return []
    baza_lat, baza_lng = geo[baza_nazwa]
    inne = [n for n in geo if n != baza_nazwa]
    if not inne:
        return []
    sektor = int(ziarno) % SEKTOROW_PODGLADU
    w_sektorze = [n for n in inne
                  if _sektor_miasta(geo[n][0], geo[n][1], baza_lat, baza_lng) == sektor]
    pula = w_sektorze or inne
    start = min(pula, key=lambda n: PMT.oblicz_dystans(baza_lat, baza_lng, *geo[n]))

    trasa, biezacy = [start], start
    przebyte = PMT.oblicz_dystans(baza_lat, baza_lng, *geo[start])
    while len(trasa) < PMT.MAX_MIEJSCOWOSCI_DZIEN:
        lat, lng = geo[biezacy]
        wolne = [n for n in inne if n not in trasa]
        if not wolne:
            break
        nastepny = min(wolne, key=lambda n: PMT.oblicz_dystans(lat, lng, *geo[n]))
        skok = PMT.oblicz_dystans(lat, lng, *geo[nastepny])
        powrot = PMT.oblicz_dystans(geo[nastepny][0], geo[nastepny][1],
                                    baza_lat, baza_lng)
        if przebyte + skok + powrot > cel_km:
            break
        przebyte += skok
        trasa.append(nastepny)
        biezacy = nastepny
    return trasa


def _hhmm(minuty):
    minuty = int(min(max(minuty, 0), 23 * 60 + 59))
    return "%02d:%02d" % (minuty // 60, minuty % 60)


def _godziny_podgladu(km, postoje):
    postoj = (PMT.POSTOJ_MIN_MIN + PMT.POSTOJ_MAX_MIN) / 2.0
    jazda = (km / max(1.0, PMT.SREDNIA_PREDKOSC)) * 60.0
    koniec = GODZINA_STARTU + jazda + postoje * postoj + PMT.PRZERWA_JEDZENIE_MIN
    return _hhmm(GODZINA_STARTU), _hhmm(koniec)


def podglad_miesiaca(kwota, rok, miesiac, tryb, wylaczone, stawka, geo,
                     baza_nazwa, limit_dnia):
    """SZACUNEK miesiąca przed generowaniem — obiekty dla widżetów.

    Liczba dni i górna granica kwoty są liczone wzorami z silnika, trasy są
    tylko poglądowe. Prawdziwy rozkład powstaje w generuj_trasy i wchodzi tu
    przez dni_widzetow_z_tras()."""
    ile_w_miesiacu = PMT.calendar.monthrange(rok, miesiac)[1]
    wylaczone = set(wylaczone or ())
    wszystkie = {}
    for numer in range(1, ile_w_miesiacu + 1):
        dzien = D.Dzien(datetime.date(rok, miesiac, numer), wolny=True)
        dzien.wylaczony = numer in wylaczone
        wszystkie[numer] = dzien
    lista = [wszystkie[n] for n in range(1, ile_w_miesiacu + 1)]

    kwota = max(0.0, float(kwota or 0.0))
    if kwota < PMT.MIN_KWOTA:
        return lista
    kandydaci = [d for d in dni_robocze_realne(rok, miesiac, tryb)
                 if d.day not in wylaczone]
    if not kandydaci:
        return lista

    ile = ile_dni_wyjazdowych(kwota, stawka, len(kandydaci), limit_dnia)
    if not ile:
        return lista
    daty = _rozloz_rownomiernie(kandydaci, ile)
    kwoty = _rozdziel_rowno(kwota, len(daty))
    for numer, (data, kwota_dnia) in enumerate(zip(daty, kwoty)):
        km = kwota_dnia / stawka
        dzien = wszystkie[data.day]
        dzien.wolny = False
        dzien.przystanki = _trasa_podgladu(km, geo, baza_nazwa, numer)
        dzien.km = round(km, 1)
        dzien.kwota = round(kwota_dnia, 2)
        dzien.dokument = 0
        dzien.start, dzien.koniec = _godziny_podgladu(km, dzien.postoje)
    return lista


def maks_kwota_miesiaca(rok, miesiac, tryb, wylaczone, limit_dnia):
    """Górna granica kwoty — walidacja z programu (App.proces, linia 21211)."""
    dni = [d for d in dni_robocze_realne(rok, miesiac, tryb)
           if d.day not in set(wylaczone or ())]
    return round(len(dni) * float(limit_dnia), 2)


# ═══════════════════════════════════════════════════════════════════════
#  WARSTWA TŁUMACZĄCA: wynik silnika → obiekty widżetów
# ═══════════════════════════════════════════════════════════════════════

def dni_widzetow_z_tras(finalne_dni, rok, miesiac, wylaczone=()):
    """PRAWDZIWY wynik generuj_trasy → lista proto_dane.Dzien na cały miesiąc.

    DzienTrasy niesie etapy (skąd, dokąd, godziny, kwota) i etapy surowe
    (kilometry, współrzędne). Widżety chcą czegoś innego: listy przystanków
    bez bazy, sumy kilometrów, kwoty dnia, godzin i numeru dokumentu.
    Numer dokumentu bierzemy z tego samego podziału, który chwilę później
    rozdziela dni na pliki PDF."""
    ile_w_miesiacu = PMT.calendar.monthrange(rok, miesiac)[1]
    wylaczone = set(wylaczone or ())
    wszystkie = {}
    for numer in range(1, ile_w_miesiacu + 1):
        dzien = D.Dzien(datetime.date(rok, miesiac, numer), wolny=True)
        dzien.wylaczony = numer in wylaczone
        wszystkie[numer] = dzien

    uporzadkowane = sorted(finalne_dni, key=lambda d: d.data)
    numer_dokumentu = {}
    try:
        for nr, grupa in enumerate(PMT._podziel_na_dokumenty(uporzadkowane), start=1):
            for dzien_trasy in grupa:
                numer_dokumentu[dzien_trasy.data] = nr
    except Exception:
        pass

    for dzien_trasy in uporzadkowane:
        if dzien_trasy.data.year != rok or dzien_trasy.data.month != miesiac:
            continue
        dzien = wszystkie.get(dzien_trasy.data.day)
        if dzien is None:
            continue
        przystanki = [etap.dokad for etap in dzien_trasy.etapy_surowe]
        if przystanki:
            przystanki = przystanki[:-1]          # ostatni etap to powrót do bazy
        km = sum(getattr(etap, "dystans_rzeczywisty", etap.d_line)
                 for etap in dzien_trasy.etapy_surowe)
        dzien.wolny = False
        dzien.przystanki = przystanki
        dzien.km = round(km, 1)
        dzien.kwota = round(dzien_trasy.suma, 2)
        dzien.dokument = numer_dokumentu.get(dzien_trasy.data, 0)
        if dzien_trasy.etapy:
            dzien.start = dzien_trasy.etapy[0].godz_wyj
            dzien.koniec = dzien_trasy.etapy[-1].godz_przyj
    return [wszystkie[n] for n in range(1, ile_w_miesiacu + 1)]


def miasta_z_tras(finalne_dni, baza_nazwa, baza_lat, baza_lng):
    """{nazwa: (lat, lng)} dla wszystkich miast odwiedzonych w miesiącu."""
    geo = {baza_nazwa: (baza_lat, baza_lng)}
    for dzien_trasy in finalne_dni:
        for etap in dzien_trasy.etapy_surowe:
            if etap.dokad and etap.dokad != baza_nazwa:
                geo[etap.dokad] = (etap.dokad_lat, etap.dokad_lng)
            if etap.skad and etap.skad != baza_nazwa:
                geo.setdefault(etap.skad, (etap.skad_lat, etap.skad_lng))
    return geo


def dokumenty_w_wyniku(folder):
    """Prawdziwe pliki PDF z folderu wyniku — modułem pmt_dokumenty."""
    return DOK.dokumenty_w_folderze(folder)


def plik_dokumentu(folder, numer):
    """Ścieżka do delegacji o tym numerze albo do pliku zbiorczego."""
    for sciezka in dokumenty_w_wyniku(folder):
        if DOK.numer_delegacji(sciezka) == int(numer or 0):
            return sciezka
    return DOK.podsumowanie(folder)


# ═══════════════════════════════════════════════════════════════════════
#  OKNO
# ═══════════════════════════════════════════════════════════════════════

class OknoNowegoWygladu(OknoPrototypu):
    """Ekran prototypu na prawdziwych danych i prawdziwym silniku."""

    KWOTA_STARTOWA = 1850.0

    def __init__(self, profil=None, rok=None, miesiac=None, rodzic=None):
        self.profil = profil or dane_pracownika()
        biezacy = miesiac_biezacy()
        self.rok = int(rok or biezacy[0])
        self.miesiac = int(miesiac or biezacy[1])

        self.folder_wyniku = ""
        self.pliki_wyniku = []
        self._watek = None
        self._dni_silnika = []
        self._pracownik_silnika = None
        self._powod_bledu = ""

        adres = self._adres_rozpoznany()
        self.baza_miasto = adres.get("baza_miasto") or "Warszawa"
        self.wojewodztwo = PMT.rozpoznaj_wojewodztwo(adres.get("kod_pocztowy", ""))
        self.baza_lat, self.baza_lng = wspolrzedne_bazy(
            self.baza_miasto, adres.get("adres_geo", ""), self.wojewodztwo)
        self.geo = miasta_wokol_bazy(self.baza_miasto, self.baza_lat,
                                     self.baza_lng, self.wojewodztwo)
        ustaw_swiat_mapy(self.geo, self.baza_miasto, self.baza_lat,
                         self.baza_lng, self.profil)

        OK.ROK, OK.MIESIAC = self.rok, self.miesiac
        OK.DZIS = datetime.date.today().day if biezacy == (self.rok, self.miesiac) else 0

        super().__init__(rodzic)

        self.setWindowTitle("PMT Planer %s — nowy wygląd" % PMT.WERSJA_PROGRAMU)
        self._uzupelnij_karty()
        self._wolne = set()
        self._przelicz_teraz(pierwszy=True)

    # ── dane pracownika na ekranie ───────────────────────────────────
    def _adres_rozpoznany(self):
        """Adres pracownika rozłożony na części — walidatorem z programu."""
        try:
            return PMT.waliduj_adres(self.profil.adres)
        except Exception:
            return {}

    def _uzupelnij_karty(self):
        """Prawdziwe dane w polach i w zakładkach miesięcy."""
        karta = self.k_pracownik
        karta.imie.setText(self.profil.imie)
        karta.adres.setText(self.profil.adres)
        karta.stanowisko.blockSignals(True)
        karta.stanowisko.clear()
        karta.stanowisko.addItems(STANOWISKA)
        indeks = karta.stanowisko.findText(self.profil.stanowisko)
        karta.stanowisko.setCurrentIndex(max(0, indeks))
        karta.stanowisko.blockSignals(False)
        karta.haslo.hide()                    # nowy wygląd nie ma jeszcze logowania

        # pojemność silnika — dokładnie te dwie pozycje, co w programie
        parametry = self.k_parametry
        parametry.POJEMNOSCI = ("poniżej 900 cm³", "powyżej 900 cm³")
        parametry.POJEMNOSCI_KROTKIE = ("< 900 cm³", "> 900 cm³")
        parametry._krotkie = False
        parametry.pojemnosc.blockSignals(True)
        parametry.pojemnosc.clear()
        parametry.pojemnosc.addItems(parametry.POJEMNOSCI)
        parametry.pojemnosc.setCurrentIndex(self.profil.silnik_idx)
        parametry.pojemnosc.blockSignals(False)
        parametry.pojemnosc.currentIndexChanged.connect(self._silnik_zmieniony)

        self.pasek.MIESIACE = self._zakladki_miesiecy()
        self.taca.pas.otwarty.connect(self._otworz_dokument_dnia)
        self.taca.b_folder.clicked.connect(self._otworz_folder)
        # Kafel liczy DNI, a jedno polecenie wyjazdu obejmuje kilka dni —
        # z podpisem „DELEGACJE" liczba kłamałaby (8 dni to 2 delegacje).
        if hasattr(self.taca.k_dni, "_opis"):
            self.taca.k_dni._opis = "DNI W TRASIE"
            self.taca.k_dni.updateGeometry()

    def _zakladki_miesiecy(self):
        poprzedni = (self.miesiac - 2) % 12 + 1
        nastepny = self.miesiac % 12 + 1
        return (PMT.MIESIACE_PL[poprzedni - 1],
                "%s %d" % (PMT.MIESIACE_PL[self.miesiac - 1], self.rok),
                PMT.MIESIACE_PL[nastepny - 1])

    def _silnik_zmieniony(self, indeks):
        self.profil.silnik_idx = 1 if int(indeks) else 0
        D.STAWKA = self.profil.stawka
        self._przelicz_teraz()

    # ── podgląd (zamiast uproszczonego silnika prototypu) ────────────
    def _maks_miesiaca(self, tryb):
        return maks_kwota_miesiaca(self.rok, self.miesiac, tryb,
                                   self._wolne, self._limit_dnia)

    def _przelicz_teraz(self, pierwszy=False):
        self._zegar_kwoty.stop()
        self._powod_bledu = ""        # powód odmowy dotyczył poprzednich danych
        if pierwszy:
            self.k_parametry.kwota.ustaw_tekst(D.zl(self.KWOTA_STARTOWA, grosze=False))
            self.k_parametry.limit.ustaw_wartosc(self._limit_dnia)
        tryb = self.k_parametry.tryb.aktywna()
        self._maks_kwota = self._maks_miesiaca(tryb)
        self._za_duzo = bool(self._maks_kwota
                             and self._kwota() > self._maks_kwota + 0.005)

        if self._dni_silnika and not self._po_zmianie_wymaga_przeliczenia():
            self.dni = dni_widzetow_z_tras(self._dni_silnika, self.rok,
                                           self.miesiac, self._wolne)
        else:
            self.dni = podglad_miesiaca(self._kwota(), self.rok, self.miesiac,
                                        tryb, self._wolne, self.profil.stawka,
                                        self.geo, self.baza_miasto,
                                        self._limit_dnia)
        if tryb == "Tydzień":
            self.dni_widoczne = [d for d in self.dni if d.data.weekday() < 5]
        else:
            self.dni_widoczne = list(self.dni)

        self.tasma.ustaw_dni(self.dni_widoczne)
        self.tasma.ustaw_dzis(OK.DZIS)

        w_trasie = self._dni_w_trasie()
        widoczne = [d.data.day for d in self.dni_widoczne]
        if w_trasie and self._wybrany not in [d.data.day for d in w_trasie]:
            self._wybrany = w_trasie[0].data.day
        elif not w_trasie and self._wybrany not in widoczne:
            self._wybrany = widoczne[0] if widoczne else 1
        self.tasma.ustaw_wybrany(self._wybrany)

        self.k_parametry.wolne.ustaw_dni(self._wolne)
        if self._po_generacji and not pierwszy:
            self._po_zmianie_danych()
        self._odswiez_liczby()
        self._odswiez_dzien()
        self._odswiez_stan_kompasu()
        self._zegar_kwoty.stop()

    def _po_zmianie_wymaga_przeliczenia(self):
        """Czy wynik silnika przestał pasować do tego, co jest na ekranie."""
        if not self._po_generacji:
            return True
        suma = round(sum(d.suma for d in self._dni_silnika), 2)
        return abs(suma - round(self._kwota(), 2)) >= 0.01

    def _odswiez_liczby(self):
        super()._odswiez_liczby()
        if self._powod_bledu and not self._za_duzo:
            self.k_parametry.kwota.ustaw_note(self._powod_bledu, True)

    # ── generowanie: PRAWDZIWE, w osobnym wątku ──────────────────────
    def _dane_do_generacji(self):
        """Parametry dla GeneratorThread albo (None, powód odmowy).

        Kontrola jest ta sama, co w App.proces: PESEL, adres, kwota, liczba
        dni roboczych i limit delegacji na dzień."""
        imie = " ".join(self.k_pracownik.imie.text().split())
        adres = self.k_pracownik.adres.text().strip()
        kwota = self._kwota()
        if not self.profil.prawdziwy or not self.profil.pesel:
            return None, "brak profilu"
        if not PMT.waliduj_pesel(self.profil.pesel):
            return None, "PESEL"
        if not imie or not adres:
            return None, "dane pracownika"
        if kwota < PMT.MIN_KWOTA:
            return None, "min. %s zł" % D.zl(PMT.MIN_KWOTA, grosze=False)
        try:
            adres_d = PMT.waliduj_adres(adres)
        except ValueError:
            return None, "adres"
        tryb = self.k_parametry.tryb.aktywna()
        dni = [d for d in dni_robocze_realne(self.rok, self.miesiac, tryb)
               if d.day not in self._wolne]
        if not dni:
            return None, "brak dni"
        maks = round(len(dni) * PMT.MAX_KWOTA_DNIA, 2)
        if kwota > maks:
            return None, "maks. %s zł" % D.zl(maks, grosze=False)

        stanowisko = self.k_pracownik.stanowisko.currentText().strip() or "KR"
        woj = PMT.rozpoznaj_wojewodztwo(adres_d["kod_pocztowy"])
        PMT.zapisz_profil(imie, self.profil.pesel, adres_d["adres_caly"],
                          stanowisko, self.profil.silnik_idx)
        return {
            "imie": imie, "pesel": self.profil.pesel,
            "adres_caly": adres_d["adres_caly"],
            "adres_geo": adres_d.get("adres_geo", adres_d["adres_caly"]),
            "kod_pocztowy": adres_d["kod_pocztowy"],
            "baza_miasto": adres_d["baza_miasto"], "stanowisko": stanowisko,
            "kwota_cel": kwota, "miesiac": self.miesiac, "rok": self.rok,
            "miesiac_slownie": PMT.MIESIACE_PL[self.miesiac - 1],
            "woj": woj, "dni_robocze": dni, "is_dark": True,
            "stawka": self.profil.stawka,
        }, ""

    def uruchom_pokaz(self):
        """Przycisk kompasu → prawdziwe generowanie dokumentów."""
        if self.k_kompas.kompas.stan() == "praca":
            return
        if self._po_generacji:
            self._pokaz_tace()
            return
        parametry, powod = self._dane_do_generacji()
        if parametry is None:
            self._odmowa(powod)
            return
        self._powod_bledu = ""
        self._po_generacji = False
        self.k_kompas.TYTUL = "Generuj dokumenty"
        self.k_kompas.kompas.ustaw_stan("praca")
        self.ustaw_postep_pokazu(0.02)

        self._watek = PMT.GeneratorThread(parametry)
        self._watek.postep.connect(self._postep_generacji)
        self._watek.sukces.connect(self._sukces_generacji)
        self._watek.blad.connect(self._blad_generacji)
        self._watek.start()

    def _odmowa(self, powod):
        """Stan „nie da się" — nazwa albo liczba, bez zdań instruktażowych."""
        self._powod_bledu = str(powod or "")
        self.k_kompas.kompas.ustaw_stan("ostrzezenie")
        self.k_kompas.kompas.setToolTip(self._powod_bledu)
        self.k_parametry.kwota.ustaw_note(self._powod_bledu, True)

    def _postep_generacji(self, _tekst, ulamek):
        self.ustaw_postep_pokazu(float(ulamek))

    def _blad_generacji(self, wiadomosc):
        self._watek = None
        krotko = str(wiadomosc or "").strip().splitlines()[0][:40] or "błąd"
        self._odmowa(krotko)

    def _sukces_generacji(self, finalne_dni, pracownik, folder):
        """Wynik silnika wchodzi na ekran: mapa, taśma, kartka, taca."""
        self._watek = None
        self._dni_silnika = list(finalne_dni)
        self._pracownik_silnika = pracownik
        self.folder_wyniku = folder
        self.pliki_wyniku = dokumenty_w_wyniku(folder)

        self.baza_miasto = pracownik.baza_miasto
        self.baza_lat, self.baza_lng = pracownik.baza_lat, pracownik.baza_lng
        self.geo = miasta_z_tras(finalne_dni, self.baza_miasto,
                                 self.baza_lat, self.baza_lng)
        okolica = miasta_wokol_bazy(self.baza_miasto, self.baza_lat,
                                    self.baza_lng, pracownik.wojewodztwo,
                                    MIAST_NA_MAPIE)
        for nazwa, wspolrzedne in okolica.items():
            self.geo.setdefault(nazwa, wspolrzedne)
        ustaw_swiat_mapy(self.geo, self.baza_miasto, self.baza_lat,
                         self.baza_lng, self.profil)
        self._przebuduj_mape()

        self.dni = dni_widzetow_z_tras(finalne_dni, self.rok, self.miesiac,
                                       self._wolne)
        if self.k_parametry.tryb.aktywna() == "Tydzień":
            self.dni_widoczne = [d for d in self.dni if d.data.weekday() < 5]
        else:
            self.dni_widoczne = list(self.dni)
        self.tasma.ustaw_dni(self.dni_widoczne)
        self.tasma.ustaw_dzis(OK.DZIS)
        w_trasie = self._dni_w_trasie()
        if w_trasie:
            self._wybrany = w_trasie[0].data.day
        self.tasma.ustaw_wybrany(self._wybrany)
        self._odswiez_liczby()
        self._odswiez_dzien()
        self.zakoncz_pokaz(animacja=self._animacje)

    def _przebuduj_mape(self):
        """Mapa buduje świat w konstruktorze — po zmianie miast stawiamy nową."""
        stara = self.mapa
        nowa = MapaDnia(self)
        nowa.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        nowa.setGeometry(stara.geometry())
        nowa.ustaw_stan(stara._stan)
        nowa.klikniete_miasto.connect(self._klik_miasto)
        nowa.ustaw_animacje(self._animacje)
        self.mapa = nowa
        stara.ustaw_animacje(False)
        stara.setParent(None)
        stara.deleteLater()
        nowa.lower()
        nowa.show()
        for widget in (self.kartka, self.pigulka, self.zakres, self.taca):
            widget.raise_()
        self._przelicz_kotwice()

    # ── taca z prawdziwymi plikami ───────────────────────────────────
    def _pokaz_tace(self, animacja=True):
        super()._pokaz_tace(animacja)
        if not self.folder_wyniku:
            return
        self.pliki_wyniku = dokumenty_w_wyniku(self.folder_wyniku)
        self.taca.l_sciezka.setText(
            "%s %d · %s" % (PMT.MIESIACE_PL[self.miesiac - 1], self.rok,
                            PMT._odmiana_plikow(len(self.pliki_wyniku))))
        self.taca.l_folder.setText(DOK.opis_kompletu(self.folder_wyniku))
        self.taca.l_folder.setToolTip(self.folder_wyniku)

    def _otworz_folder(self):
        if self.folder_wyniku:
            PMT.otworz_w_systemie(self.folder_wyniku)

    def _otworz_wszystkie(self):
        """Prawdziwe pliki PDF otwierane w systemie."""
        if not self.folder_wyniku:
            return
        self.pliki_wyniku = dokumenty_w_wyniku(self.folder_wyniku)
        for sciezka in self.pliki_wyniku:
            PMT.otworz_w_systemie(sciezka)
        self.taca.l_stan.setText(
            "otwarto %s" % PMT._odmiana_plikow(len(self.pliki_wyniku)))
        self._zegar_stanu.start()

    def _otworz_dokument_dnia(self, dzien):
        """Kliknięcie kartki na tacy otwiera PDF z jej dniem."""
        if not self.folder_wyniku:
            return
        sciezka = plik_dokumentu(self.folder_wyniku, getattr(dzien, "dokument", 0))
        if sciezka:
            PMT.otworz_w_systemie(sciezka)
            self.taca.l_stan.setText(os.path.basename(sciezka))
            self._zegar_stanu.start()

    def _odswiez_stan_tacy(self):
        if self.folder_wyniku:
            self.taca.l_stan.setText(DOK.opis_kompletu(self.folder_wyniku))
            return
        super()._odswiez_stan_tacy()

    # ── panele, które czekają na podłączenie ─────────────────────────
    def _panel_podpisu(self):
        self.zastepczy_panel_podpisu()

    def _panel_wysylki(self):
        self.zastepczy_panel_wysylki()

    def zastepczy_panel_podpisu(self):
        """ZASTĘPNIK. Panel z prototypu — prawdziwy podpis (pmt_podpis.py,
        DialogPodpis w PMT_Delegacje) nie jest jeszcze podłączony."""
        dni = self._dni_w_trasie()
        if not dni:
            return
        panel = PanelPodpisu(dni, self)
        panel.setStyleSheet(arkusz())
        if panel.exec() == 1:
            for dzien in dni:
                dzien.podpisany = True
            self.taca.ustaw_dni(self.dni_widoczne)
            self.tasma.ustaw_dni(self.dni_widoczne)
            self.tasma.ustaw_wybrany(self._wybrany)
            self._odswiez_dzien()
        self._odswiez_stan_tacy()

    def zastepczy_panel_wysylki(self):
        """ZASTĘPNIK. Panel z prototypu — prawdziwa wysyłka (pmt_wysylka.py,
        DialogWysylka w PMT_Delegacje) nie jest jeszcze podłączona."""
        dni = self._dni_w_trasie()
        if not dni:
            return
        panel = PanelWysylki(dni, self)
        panel.setStyleSheet(arkusz())
        panel.exec()

    # ── sprzątanie ───────────────────────────────────────────────────
    def zatrzymaj_watek(self):
        """Wątek generowania nie może przeżyć okna."""
        watek = self._watek
        self._watek = None
        if watek is not None and watek.isRunning():
            watek.wait(4000)

    def closeEvent(self, zdarzenie):
        self.zatrzymaj_watek()
        super().closeEvent(zdarzenie)


# ═══════════════════════════════════════════════════════════════════════
#  URUCHOMIENIE
# ═══════════════════════════════════════════════════════════════════════

def poczekaj_na_generacje(app, okno, sekundy=90):
    """Czeka na wątek generowania, mieląc zdarzenia — na potrzeby zrzutów."""
    koniec = datetime.datetime.now() + datetime.timedelta(seconds=sekundy)
    while okno._watek is not None and datetime.datetime.now() < koniec:
        app.processEvents()
    for _ in range(12):
        app.processEvents()
    return okno._po_generacji


def _zrzuty(app, okno):
    zapisane = []

    def zapisz(nazwa):
        okno.zamroz()
        for _ in range(6):
            app.processEvents()
        okno.grab().save(nazwa)
        zapisane.append(nazwa)

    okno.resize(*OK.ROZMIAR_DOCELOWY)
    for _ in range(8):
        app.processEvents()
    zapisz("zrzut_nowy_1_start.png")

    okno.ustaw_animacje(False)
    okno.uruchom_pokaz()
    if poczekaj_na_generacje(app, okno):
        zapisz("zrzut_nowy_2_taca.png")
        print("folder wyniku:", okno.folder_wyniku)
        for sciezka in okno.pliki_wyniku:
            print("   plik:", os.path.basename(sciezka))
    else:
        print("generowanie nie doszło do skutku:", okno._powod_bledu or "?")

    for nazwa in zapisane:
        print("zapisano", nazwa)
    return 0


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(argv)
    app.setFont(S.czcionka(13))
    app.setStyleSheet(arkusz())
    okno = OknoNowegoWygladu()
    okno.dopasuj_do_ekranu()
    okno.show()
    if "--zrzut" in argv:
        kod = _zrzuty(app, okno)
        okno.close()
        return kod
    if "--pelny" in argv:
        okno.showFullScreen()
    kod = app.exec()
    okno.zamroz()
    okno.zatrzymaj_watek()
    return kod


# ═══════════════════════════════════════════════════════════════════════
#  NIEPODŁĄCZONE — stan na dziś, uczciwie
#
#  1. Logowanie i konto. Nowy wygląd nie ma okna logowania; pracownika bierze
#     z profilu zapisanego przez stary ekran. Bez ani jednego profilu wchodzi
#     zastepczy_profil_pracownika() i generowanie odmawia („brak profilu").
#     Pole hasła w karcie PRACOWNIK jest ukryte, a napis „Konto ważne do…"
#     w pasku górnym to nadal tekst z prototypu.
#  2. PESEL. Nie ma dla niego pola w nowym układzie — idzie z profilu.
#  3. Podpis i wysyłka. zastepczy_panel_podpisu() / zastepczy_panel_wysylki()
#     pokazują panele prototypu. pmt_podpis.py i pmt_wysylka.py czekają.
#  4. Plan wizyt, statystyki, kalendarz, aktualizacje, panel administratora —
#     w nowym wyglądzie nie istnieją; szyna ikon po lewej nic nie przełącza.
#  5. Zakładki miesięcy w pasku górnym pokazują prawdziwe nazwy, ale nie da
#     się nimi zmienić miesiąca (okno liczy bieżący).
#  6. Podgląd przed generowaniem to szacunek (podglad_miesiaca) — prawdziwe
#     trasy powstają dopiero po naciśnięciu kompasu.
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
