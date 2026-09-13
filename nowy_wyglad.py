# -*- coding: utf-8 -*-
"""PMT PLANER — EKRAN PROGRAMU.

Okno główne programu: widżety prototypu (prototyp/proto_*.py) na danych
i silniku z PMT_Delegacje.py.

    python PMT_Delegacje.py             (program: logowanie → to okno)
    python PMT_Delegacje.py --stary     (awaryjnie dawne okno App)
    python nowy_wyglad.py               (samodzielnie, do pracy nad wyglądem)
    python nowy_wyglad.py --zrzut       (bez ekranu: zrzuty do plików PNG)

CO JEST PRAWDZIWE
    · konto                logowanie programu; imię, ważność i inicjały
                           w pasku górnym z pliku statusu
    · szyna po lewej       dom otwiera ekran startowy, kolejne ikony —
                           panele programu (Nowa wyprawa, Plan wizyt, Bilans
                           miesiąca, Twoja praca, Kopia zapasowa, Ustawienia,
                           O programie). Panele stają NAD tym oknem, w ramie
                           NakladkaDzialu i w materiale nowego systemu
                           (zastosuj_styl_panelu)
    · ekran startowy       dzisiejsza data, dzisiejsza trasa z zapisanego
                           planu, liczby miesiąca i skróty (bilans, wyprawa,
                           mapa tras)
    · mapa tras            Trasy_Mapa.html z folderu wyniku — przycisk na
                           tacy dokumentów i na ekranie startowym
    · pasek górny          dzwonek z historią komunikatów, zgłaszanie błędu,
                           awatar (hasło, karta testera, intro, wylogowanie)
    · animacja startowa    intro_zywa_mapa nad tym oknem (jak dotąd)
    · pracownik            profil z ~/.pmt_uzytkownicy.json (zapisz_profil)
    · dni robocze          pobierz_dni_robocze + ustaw_tryb_pracy
    · miasta i odległości  zaladuj_baze, coords_z_miasta, oblicz_dystans
    · trasy, km i kwoty    generuj_trasy  (w osobnym wątku, GeneratorThread)
    · dokumenty PDF        generuj_pdfy + generuj_mape_html (ten sam wątek)
    · pliki na tacy        pmt_dokumenty.dokumenty_w_folderze(folder wyniku)
    · podpis elektroniczny PMT.DialogPodpis nad modułem pmt_podpis
    · wysyłka pocztą       PMT.DialogWysylka nad modułem pmt_wysylka
    · dane pracownika      pola karty PRACOWNIK ↔ zapisz_profil / _wczytaj_store
    · wybór miesiąca       zakładki paska górnego (także PgUp / PgDn)
    · ustawienia widoku    kwota, tryb, limit dnia i dni bez pracy w
                           ~/.pmt_ustawienia.json (ustawienie / zapisz_ustawienie)
    · stan odległości      stan_zrodla_odleglosci przy kwocie i na tacy

CO JEST SZACUNKIEM (do chwili wygenerowania)
    podglad_miesiaca() — rozkład kwoty na dni liczony tymi samymi wzorami co
    silnik, ale bez układania tras. Po wygenerowaniu podgląd znika, a jego
    miejsce zajmuje prawdziwy wynik przetłumaczony przez dni_widzetow_z_tras().

CZEGO JESZCZE NIE MA — sekcja „NIEPODŁĄCZONE" na końcu pliku.
"""

import datetime
import math
import os
import re
import sys


# ═══════════════════════════════════════════════════════════════════════
#  DOSTĘP DO PRAWDZIWEGO PROGRAMU I DO WIDŻETÓW PROTOTYPU
# ═══════════════════════════════════════════════════════════════════════

def modul_programu():
    """Moduł PMT_Delegacje — bez wczytywania go drugi raz.

    Gdy to program nas uruchomił (python PMT_Delegacje.py), jest on pod
    nazwą „__main__". Zwykły import zrobiłby wtedy DRUGĄ kopię modułu
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

from PyQt6.QtCore import (Qt, QEvent, QPoint, QPointF, QRectF,     # noqa: E402
                          QTimer, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QCursor, QPainter,        # noqa: E402
                         QPainterPath, QPen)
from PyQt6.QtWidgets import (QAbstractSpinBox, QApplication,       # noqa: E402
                             QCheckBox, QComboBox, QFrame, QHBoxLayout,
                             QLabel, QLineEdit, QMenu, QMessageBox,
                             QPushButton, QRadioButton, QVBoxLayout, QWidget)

import proto_styl as S                                             # noqa: E402
import proto_dane as D                                             # noqa: E402
import proto_okno as OK                                            # noqa: E402
from proto_mapa import MapaDnia                                    # noqa: E402
from proto_okno import OknoPrototypu, arkusz                       # noqa: E402
from proto_taca import (KafelLiczby, Napis, Panel, PanelPodpisu,   # noqa: E402
                        PanelWysylki, Przycisk)

import pmt_dokumenty as DOK                                        # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  STAŁE WIDOKU
#  Liczby silnika bierzemy wprost z modułu (PMT.MAX_KWOTA_DOKUMENTU,
#  PMT.pojemnosc_dnia_zl, PMT.ile_dokumentow). Tutaj zostają tylko te,
#  które dotyczą samego rysowania i podglądu.
# ═══════════════════════════════════════════════════════════════════════
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
        self.zrodlo = zrodlo          # "profil" (z dysku) albo "pusty"

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


def pusty_profil_pracownika():
    """Program bez ani jednego zapisanego profilu — puste pola do wypełnienia.

    Nowy wygląd nie ma własnego logowania, ale ma komplet pól (imię, PESEL,
    adres, stanowisko): wpisane dane trafiają do tego samego magazynu
    profili, z którego korzysta stary ekran."""
    return ProfilWidoku("", "", "", "KR", 1, "pusty")


def profil_konta():
    """Profil osoby ZALOGOWANEJ w programie albo None.

    Magazyn profili jest wspólny dla komputera, więc po zalogowaniu bierzemy
    wpis tej osoby — nie ostatni z brzegu. Bez wpisu zostaje samo imię z konta
    i puste rubryki do uzupełnienia."""
    imie = PMT.online_imie_uzytkownika()
    if not imie:
        return None
    try:
        wpis = PMT.szukaj_profilu_po_nazwisku(imie)
    except Exception:
        wpis = None
    if wpis:
        return ProfilWidoku(wpis.get("imie", imie), wpis.get("pesel", ""),
                            wpis.get("adres", ""), wpis.get("stanowisko", "KR"),
                            wpis.get("silnik_idx", 1), "profil")
    return ProfilWidoku(imie, "", "", "KR", 1, "konto")


def dane_pracownika():
    """Profil do ekranu: konto, potem dysk, a gdy nic — puste rubryki."""
    profil = profil_konta()
    if profil is not None:
        return profil
    profil = profil_z_programu()
    if profil is None:
        return pusty_profil_pracownika()
    return profil


def inicjaly_konta(imie):
    """Dwie pierwsze litery imienia i nazwiska — do awatara w pasku."""
    czesci = [czesc for czesc in str(imie or "").split() if czesc]
    return "".join(czesc[0] for czesc in czesci[:2]).upper()


def waznosc_konta(pozostalo=None):
    """(napis do paska górnego, czy konto jest jeszcze ważne).

    Data bierze się z tego samego pliku statusu, po którym program decyduje
    o dostępie (kolumna „Ważne do" w arkuszu użytkowników)."""
    try:
        stan = PMT._wczytaj(PMT.PLIK_STATUSU, {}) or {}
    except Exception:
        stan = {}
    zapis = str(stan.get("wazne_do", "") or "")
    if zapis:
        try:
            dzien = datetime.date.fromisoformat(zapis)
        except ValueError:
            dzien = None
        if dzien is not None:
            return ("Konto ważne do %s" % dzien.strftime("%d.%m.%Y"),
                    dzien >= datetime.date.today())
    dni = pozostalo
    if dni is None:
        try:
            _wazne, dni = PMT.demo_status()
        except Exception:
            dni = None
    if dni is None:
        return "Konto bez daty ważności", False
    dni = int(dni)
    if dni <= 0:
        return "Konto ważne tylko dziś", True
    return "Konto ważne jeszcze %d dni" % dni, True


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
        zapamietane = PMT._geo_cache.get(PMT._klucz_geo(adres_geo))
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

    Najpierw dokumenty (kwota przez sufit dokumentu), potem dni w jednym
    dokumencie (kwota dokumentu przez pojemność doby), na końcu dolny próg
    trzech dni — jak w silniku."""
    if kwota <= 0 or stawka <= 0 or dostepnych <= 0:
        return 0
    sufit = max(PMT.pojemnosc_dnia_zl(PMT.POSTOJE_TYPOWE, stawka, limit_dnia),
                PMT.MIN_KWOTA)
    dokumentow = PMT.ile_dokumentow(kwota)
    w_dokumencie = max(1, math.ceil((kwota / dokumentow - 0.005) / sufit))
    return max(1, min(dostepnych, max(3, dokumentow * w_dokumencie)))


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


def maks_kwota_miesiaca(rok, miesiac, tryb, wylaczone, limit_dnia, stawka=None):
    """Górna granica kwoty — walidacja z programu (App.proces).

    Dni robocze × REALNY sufit dnia: fizyka doby (posiłek + jazda + postoje)
    przycięta limitem dnia, a nie sam limit."""
    dni = [d for d in dni_robocze_realne(rok, miesiac, tryb)
           if d.day not in set(wylaczone or ())]
    return PMT.maks_kwota_miesiaca(len(dni), stawka, limit_dnia=float(limit_dnia))


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
#  ETAPY GENEROWANIA: meldunek silnika → plakietka na karcie kompasu
#  Silnik melduje postęp opisem i ułamkiem. Ułamek idzie na łuk kompasu,
#  a etap bierzemy z OPISU — po ułamku wychodziłby fałsz, bo układanie
#  tras dochodzi do 0,78, czyli powyżej progu plakietki „PDF".
# ═══════════════════════════════════════════════════════════════════════
ETAPY_SILNIKA = (
    ("mapa", ("html", "podglądu tras", "mapy")),
    ("PDF", ("pdf", "dokument")),
    # samo „GPS" tu nie wystarcza: „Klastrowanie GPS (Dzień 3/7)" to
    # układanie TRAS, a nie pobieranie danych bazy
    ("dane", ("współrzędn", "lokalizowanie")),
)


def etap_silnika(opis):
    """Nazwa plakietki dla meldunku silnika; wszystko inne to układanie tras."""
    tekst = str(opis or "").lower()
    for nazwa, slowa in ETAPY_SILNIKA:
        for slowo in slowa:
            if slowo in tekst:
                return nazwa
    return "trasy"


# ═══════════════════════════════════════════════════════════════════════
#  MATERIAŁ NOWEGO SYSTEMU NA PANELACH PROGRAMU
#
#  Panele (Nowa wyprawa, Plan wizyt, Twoja praca, Ustawienia, Kopia
#  zapasowa) to gotowe widżety okna App. Ich barwy siedzą w arkuszach
#  rozdawanych przez update_theme (PMT_Delegacje, _apply_theme_srodek
#  i update_theme każdej nakładki). Nie przepisujemy paneli — TŁUMACZYMY
#  te arkusze na materiał nowego ekranu i wkładamy panel w ramę
#  NakladkaDzialu, która stoi nad NOWYM oknem.
# ═══════════════════════════════════════════════════════════════════════

# stara barwa (małymi literami) → barwa nowego systemu
BARWY_PANELU = {
    "#f8fafc": S.TEKST.name(),      "#e2e8f0": S.TEKST.name(),
    "#cbd5e1": S.TEKST_2.name(),    "#94a3b8": S.TEKST_2.name(),
    "#64748b": S.TEKST_3.name(),    "#475569": S.TEKST_3.name(),
    "#ef4444": S.BLAD.name(),       "#dc2626": S.BLAD.name(),
    "#f87171": S.BLAD.name(),       "#fca5a5": S.BLAD.name(),
    "#f59e0b": S.BURSZTYN.name(),   "#fbbf24": S.BURSZTYN.name(),
    "#facc15": S.BURSZTYN.name(),   "#eab308": S.BURSZTYN.name(),
    "#10b981": S.ZIELEN.name(),     "#34d399": S.ZIELEN.name(),
    "#059669": S.ZIELEN.name(),     "#22c55e": S.ZIELEN.name(),
    "#4ade80": S.MIETA.name(),      "#a7f3d0": S.MIETA.name(),
    "#0093e9": S.CYJAN.name(),      "#38bdf8": S.CYJAN.name(),
    "#60a5fa": S.CYJAN.name(),      "#0b1320": "#0F1A2A",
    "#f97316": S.BURSZTYN.name(),   "#fb923c": S.BURSZTYN.name(),
    "#fcd34d": S.BURSZTYN.name(),   "#ea580c": S.BURSZTYN.name(),
}

POWIERZCHNIA_CSS = "rgba(17,28,46,0.72)"     # karta nowego systemu
POWIERZCHNIA_KRYJACA = "#0F1A2A"             # ta sama barwa bez prześwitu
WGLEBIENIE_CSS = "rgba(9,16,28,0.62)"        # pole, rowek, tło wykresu
OBRYS_CSS = "rgba(255,255,255,0.12)"         # krawędź zamiast cyjanowej ramki
MGLA_CSS = "rgba(255,255,255,0.05)"          # delikatne wypełnienie wiersza

# panele-karty, które w nowej ramie są już niepotrzebne (rama rysuje szkło)
KARTY_BEZ_TLA = ("PlanerKarta", "PlanKarta")

_RE_RGBA = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)")
_RE_HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
_RE_PROMIEN = re.compile(r"border-radius\s*:\s*([0-9.]+)px")
_RE_ROZMIAR = re.compile(r"font-size\s*:\s*([0-9.]+)px")
_RE_KROJ = re.compile(r"font-family\s*:\s*['\"]?Segoe UI['\"]?(\s*,\s*sans-serif)?")


def _rgba_nowego_systemu(dopasowanie):
    r, g, b = (int(dopasowanie.group(i)) for i in (1, 2, 3))
    a = float(dopasowanie.group(4))
    if (r, g, b) == (0, 240, 255):           # cyjanowe ramki i mgiełki starego okna
        return MGLA_CSS if a <= 0.12 else OBRYS_CSS
    if (r, g, b) in ((0, 228, 161), (255, 255, 255)):
        return dopasowanie.group(0)
    if (r, g, b) == (148, 163, 184):
        return "rgba(167,180,200,%s)" % dopasowanie.group(4)
    if r + g + b <= 150:                     # ciemne tła: karta albo wgłębienie
        if a >= 0.88:                        # to, co kryło, ma kryć dalej
            return POWIERZCHNIA_KRYJACA
        if a >= 0.75:
            return POWIERZCHNIA_CSS
        if a >= 0.35:
            return WGLEBIENIE_CSS
        return "rgba(9,16,28,0.40)"
    return dopasowanie.group(0)


def przemaluj_arkusz(css, promien=14):
    """Arkusz starego panelu w barwach, krojach i promieniach nowego ekranu."""
    czesci = css.split("}")
    for i, blok in enumerate(czesci):
        znaleziony = _RE_ROZMIAR.search(blok)
        rozmiar = float(znaleziony.group(1)) if znaleziony else 13.0
        rodzina = S.rodzina_naglowek() if rozmiar >= 16 else S.rodzina_tekst()
        blok = _RE_KROJ.sub("font-family:'%s'" % rodzina, blok)
        blok = _RE_HEX.sub(
            lambda m: BARWY_PANELU.get(m.group(0).lower(), m.group(0)), blok)
        blok = _RE_RGBA.sub(_rgba_nowego_systemu, blok)
        blok = _RE_PROMIEN.sub(
            lambda m: "border-radius:%dpx" % (int(float(m.group(1)))
                                              if float(m.group(1)) <= 6 else promien),
            blok)
        czesci[i] = blok
    return "}".join(czesci)


def _promien_widzetu(widget):
    """Przyciski i pola: 10 px. Karty i kafle: 14 px."""
    if isinstance(widget, (QPushButton, QLineEdit, QComboBox, QCheckBox,
                           QRadioButton, QAbstractSpinBox)):
        return 10
    return 14


def zastosuj_styl_panelu(korzen, tlo="transparent"):
    """Nakłada materiał nowego ekranu na gotowy panel programu.

    Idzie po wszystkich widżetach panelu i tłumaczy ich arkusze. Wynik
    zapamiętuje przy widżecie, więc powtórne wywołanie (po przebudowie
    wierszy przez sam panel) kosztuje jedno porównanie napisów.

    ``tlo=None`` zostawia arkusz korzenia na miejscu (tylko go tłumaczy) —
    tak wchodzą okna dialogowe programu, które rysują własną kartę."""
    if tlo is None:
        css = korzen.styleSheet()
        if css and getattr(korzen, "_nowy_styl", None) != css:
            korzen.setStyleSheet(przemaluj_arkusz(css, _promien_widzetu(korzen)))
    else:
        arkusz_korzenia = "%s { background: %s; border: none; }" % (
            type(korzen).__name__, tlo)
        if korzen.styleSheet() != arkusz_korzenia:
            korzen.setStyleSheet(arkusz_korzenia)
    korzen._nowy_styl = korzen.styleSheet()
    for widget in korzen.findChildren(QWidget):
        css = widget.styleSheet()
        if widget.objectName() in KARTY_BEZ_TLA:
            nowy = "#%s { background: transparent; border: none; }" % widget.objectName()
        elif not css or getattr(widget, "_nowy_styl", None) == css:
            continue
        else:
            nowy = przemaluj_arkusz(css, _promien_widzetu(widget))
        if nowy != css:
            widget.setStyleSheet(nowy)
        widget._nowy_styl = widget.styleSheet()
    return korzen


def pilnuj_materialu(panel, metody=("_przerysuj", "odswiez_dane", "ustaw_plan",
                                    "update_theme")):
    """Panel, który sam przebudowuje sobie wiersze, ma je od razu w materiale.

    Opakowujemy metody panelu, po których wracają jego własne arkusze —
    zaraz po nich tłumaczymy je na nowo. Bez tego świeży wiersz świeciłby
    starymi barwami aż do następnego przebiegu zegara."""
    for nazwa in metody:
        metoda = getattr(panel, nazwa, None)
        if metoda is None or getattr(metoda, "_w_materiale", False):
            continue

        def opakuj(_m=metoda, _p=panel):
            def wywolaj(*args, **kwargs):
                wynik = _m(*args, **kwargs)
                zastosuj_styl_panelu(_p)
                rama = _p.parent()
                if isinstance(rama, NakladkaDzialu):
                    rama.odswiez_podtytul()
                return wynik
            wywolaj._w_materiale = True
            return wywolaj

        try:
            setattr(panel, nazwa, opakuj())
        except Exception:
            pass
    return panel


def ukryj_naglowek_panelu(panel):
    """Tytuł, podtytuł i krzyżyk panelu — nagłówek daje teraz rama."""
    for nazwa in ("tytul", "podtytul", "l_tyt", "l_pod", "btn_x"):
        widget = getattr(panel, nazwa, None)
        if isinstance(widget, QWidget):
            widget.hide()


def usun_wywody(panel, poczatki=()):
    """Zdania tłumaczące działanie programu nie należą do tego interfejsu."""
    for etykieta in panel.findChildren(QLabel):
        tekst = etykieta.text().strip()
        if any(tekst.startswith(p) for p in poczatki):
            etykieta.hide()


ARKUSZ_PANELU = """
QLabel { background: transparent; }
QScrollArea { background: transparent; border: none; }
QAbstractScrollArea > QWidget { background: transparent; }
QAbstractScrollArea > QWidget > QWidget { background: transparent; }
QHeaderView { background: %(wglebienie)s; border: none; }
QHeaderView::section { background: %(wglebienie)s; color: %(tekst2)s;
    border: none; padding: 8px; }
QTableCornerButton::section { background: %(wglebienie)s; border: none; }
QTableView, QTableWidget, QAbstractItemView { background: rgba(9,16,28,0.40);
    alternate-background-color: rgba(255,255,255,0.03);
    selection-background-color: rgba(0,240,255,0.18);
    color: %(tekst)s; border: 1px solid %(obrys)s; border-radius: 14px; }
QCheckBox, QRadioButton { background: transparent; }
QToolButton { background: transparent; border: none; color: %(tekst)s; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.16);
    border-radius: 5px; min-height: 30px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: rgba(255,255,255,0.16);
    border-radius: 5px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
""" % {"tekst": S.TEKST.name(), "tekst2": S.TEKST_2.name(),
       "wglebienie": WGLEBIENIE_CSS, "obrys": OBRYS_CSS}


class NakladkaDzialu(Panel):
    """Rama panelu nowego systemu — nad nowym oknem, nie nad starym.

    Materiał i nagłówek bierze z Panel (proto_taca): to samo szkło, ta sama
    krawędź światła u góry, ten sam krzyżyk w prawym górnym rogu, co panele
    podpisu i wysyłki. W środku siedzi gotowy panel programu."""

    zamknieto = pyqtSignal()

    def __init__(self, rodzic=None):
        super().__init__("", "", rodzic)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setModal(False)
        self.setStyleSheet(S.qss() + ARKUSZ_PANELU)
        self._panel = None
        self._podtytul = ""
        self.tresc = QVBoxLayout()
        self.tresc.setContentsMargins(0, 0, 0, 0)
        self.tresc.setSpacing(0)
        self.z.addLayout(self.tresc, 1)
        self.b_zamknij.clicked.disconnect()
        self.b_zamknij.clicked.connect(self.zamknij)
        self.rejected.connect(self.zamknij)
        self.hide()

    # — treść —
    def ustaw_panel(self, widget, tytul, podtytul=""):
        """``podtytul`` może być funkcją — wtedy stan w nagłówku sam się odświeża."""
        self.l_tytul.setText(tytul)
        self._podtytul = podtytul
        self.odswiez_podtytul()
        if widget is not self._panel:
            if self._panel is not None:
                self.tresc.removeWidget(self._panel)
                self._panel.hide()
            self._panel = widget
            if widget is not None:
                if widget.parent() is not self:
                    widget.setParent(self)
                self.tresc.addWidget(widget)
        if widget is not None:
            widget.show()
            # Arkusz ramy nakładamy PONOWNIE: widżety, które wpięły się w nią
            # po jej zbudowaniu (viewporty przewijania!), inaczej zostają
            # z barwą systemową — białą.
            self.setStyleSheet(self.styleSheet())
        return widget

    def panel(self):
        return self._panel

    def odswiez_podtytul(self):
        zrodlo = getattr(self, "_podtytul", "")
        if callable(zrodlo):
            try:
                zrodlo = zrodlo()
            except Exception:
                zrodlo = ""
        self.l_podtytul.setText(str(zrodlo or ""))

    def zamknij(self):
        if self.isVisible():
            self.hide()
        self.zamknieto.emit()

    # — rama nie jest osobnym oknem: nie przesuwamy jej myszą —
    def mousePressEvent(self, zdarzenie):
        QWidget.mousePressEvent(self, zdarzenie)

    def mouseMoveEvent(self, zdarzenie):
        QWidget.mouseMoveEvent(self, zdarzenie)

    def mouseReleaseEvent(self, zdarzenie):
        QWidget.mouseReleaseEvent(self, zdarzenie)

    def resizeEvent(self, zdarzenie):
        """Ciasne okno oddaje najpierw marginesy ramy — panel ma się zmieścić."""
        ciasno = self.height() < 640 or self.width() < 1000
        margines = 12 if ciasno else 20
        if self.MARGINES != margines:
            self.MARGINES = margines
        bok = margines + (2 if ciasno else 16)
        pion = margines + (4 if ciasno else 12)
        marg = self.z.contentsMargins()
        if marg.left() != bok or marg.top() != pion:
            self.z.setContentsMargins(bok, pion, bok, pion)
        super().resizeEvent(zdarzenie)

    def paintEvent(self, zdarzenie):
        malarz = QPainter(self)
        malarz.fillRect(self.rect(), QColor(5, 10, 20, 246))
        malarz.end()
        super().paintEvent(zdarzenie)


# ═══════════════════════════════════════════════════════════════════════
#  EKRAN STARTOWY I MAPA TRAS
# ═══════════════════════════════════════════════════════════════════════

DNI_TYGODNIA = ("poniedziałek", "wtorek", "środa", "czwartek",
                "piątek", "sobota", "niedziela")
MIESIACE_DOPELNIACZ = ("stycznia", "lutego", "marca", "kwietnia", "maja",
                       "czerwca", "lipca", "sierpnia", "września",
                       "października", "listopada", "grudnia")
NAZWA_MAPY = "Trasy_Mapa.html"


def data_slownie(data):
    return "%s, %d %s %d" % (DNI_TYGODNIA[data.weekday()], data.day,
                             MIESIACE_DOPELNIACZ[data.month - 1], data.year)


def plik_mapy_tras(folder):
    """Mapa tras miesiąca w folderze wyniku — albo pusto, gdy jej nie ma."""
    if not folder:
        return ""
    sciezka = os.path.join(folder, NAZWA_MAPY)
    return sciezka if os.path.isfile(sciezka) else ""


def folder_z_mapa_tras():
    """Najświeższy folder rozliczenia z mapą — po ponownym uruchomieniu programu."""
    najlepszy, czas_najlepszego = "", -1.0
    try:
        pulpit = PMT.sciezka_pulpitu()
        for nazwa in os.listdir(pulpit):
            if not nazwa.startswith("Rozliczenie_"):
                continue
            sciezka = plik_mapy_tras(os.path.join(pulpit, nazwa))
            if not sciezka:
                continue
            czas = os.path.getmtime(sciezka)
            if czas > czas_najlepszego:
                najlepszy, czas_najlepszego = os.path.dirname(sciezka), czas
    except Exception:
        return ""
    return najlepszy


def dzis_w_trasie():
    """Dzisiejszy dzień zapisanego planu, najbliższy następny i ile zrobione."""
    dzis = datetime.date.today()
    try:
        plan = PMT.wczytaj_plan()
    except Exception:
        plan = None
    dzien, nastepny = None, None
    for d in (plan or {}).get("dni", []):
        if d.data == dzis:
            dzien = d
        elif d.data > dzis and nastepny is None:
            nastepny = d
    zrobione = 0
    if dzien is not None:
        for wizyta in dzien.wizyty:
            try:
                if PMT.czy_odwiedzona(dzis, wizyta.adres or wizyta.nazwa):
                    zrobione += 1
            except Exception:
                pass
    return dzien, nastepny, zrobione


def liczby_miesiaca():
    try:
        return PMT.oblicz_statystyki_osobiste()
    except Exception:
        return {}


def _wizyty_txt(n):
    if n == 1:
        return "1 wizyta"
    r, s = n % 10, n % 100
    if 2 <= r <= 4 and not (12 <= s <= 14):
        return "%d wizyty" % n
    return "%d wizyt" % n


def _punkty_txt(n):
    if n == 1:
        return "1 punkt"
    r, s = n % 10, n % 100
    if 2 <= r <= 4 and not (12 <= s <= 14):
        return "%d punkty" % n
    return "%d punktów" % n


def _godziny(minuty):
    minuty = max(0, int(minuty or 0))
    return "%d h %02d" % (minuty // 60, minuty % 60)


def wysrodkuj_tresc(widget, maks_szerokosc):
    """Treść trzyma czytelną szerokość także w szerokim oknie."""
    uklad = widget.layout()
    if uklad is None:
        return
    bok = max(0, (widget.width() - int(maks_szerokosc)) // 2)
    marg = uklad.contentsMargins()
    if marg.left() != bok:
        uklad.setContentsMargins(bok, marg.top(), bok, marg.bottom())


class KartaStanu(QWidget):
    """Powierzchnia nowego systemu: szkło, krawędź światła, obrys."""

    def __init__(self, rodzic=None, promien=S.PROMIEN, mocne=False):
        super().__init__(rodzic)
        self._promien = float(promien)
        self._mocne = bool(mocne)

    def paintEvent(self, _zdarzenie):
        malarz = QPainter(self)
        malarz.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pole = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if pole.width() > 4 and pole.height() > 4:
            S.szklo(malarz, pole, self._promien, mocne=self._mocne,
                    sila_krawedzi=1.6)
        malarz.end()


class EkranStartowy(QWidget):
    """Ekran startowy: dzisiejsza data, dzisiejsza trasa, liczby miesiąca,
    skrót do bilansu i do mapy tras. Zbudowany z części nowego systemu."""

    MAKS_PRZYSTANKOW = 5
    MAKS_SZEROKOSC = 1000

    def __init__(self, okno):
        super().__init__(okno)
        self._okno = okno
        z = QVBoxLayout(self)
        z.setContentsMargins(0, 0, 0, 0)
        z.setSpacing(16)

        # ── karta dnia ────────────────────────────────────────────
        self.karta_dnia = KartaStanu(self, S.PROMIEN)
        kd = QHBoxLayout(self.karta_dnia)
        kd.setContentsMargins(24, 20, 24, 20)
        kd.setSpacing(20)
        lewa = QVBoxLayout()
        lewa.setSpacing(4)
        self.l_dzien = Napis("", 21, 700, S.TEKST, naglowek=True)
        self.l_meta = Napis("", 12.5, 600, S.TEKST_2)
        lewa.addWidget(self.l_dzien)
        lewa.addWidget(self.l_meta)
        lewa.addSpacing(6)
        self.przystanki = QVBoxLayout()
        self.przystanki.setSpacing(3)
        lewa.addLayout(self.przystanki)
        lewa.addStretch(1)
        kd.addLayout(lewa, 1)
        prawa = QVBoxLayout()
        prawa.setSpacing(8)
        self.l_postep = Napis("", 15, 700, S.MIETA, mono=True,
                              wyrownanie=Qt.AlignmentFlag.AlignRight)
        prawa.addWidget(self.l_postep)
        self.b_dzien = Przycisk("Plan wizyt", "glowny", 13, self)
        self.b_dzien.clicked.connect(self._klik_dnia)
        prawa.addWidget(self.b_dzien, 0, Qt.AlignmentFlag.AlignRight)
        prawa.addStretch(1)
        kd.addLayout(prawa, 0)
        self.karta_dnia.setMinimumHeight(172)
        z.addStretch(1)
        z.addWidget(self.karta_dnia, 0)

        # ── liczby miesiąca ───────────────────────────────────────
        self.karta_liczb = KartaStanu(self, S.PROMIEN)
        kl = QHBoxLayout(self.karta_liczb)
        kl.setContentsMargins(24, 14, 24, 14)
        kl.setSpacing(22)
        self.k_wizyty = KafelLiczby("WIZYTY", lambda v: "%.0f" % v,
                                    wyrozniony=True, duzy=True, rodzic=self)
        self.k_km = KafelLiczby("KILOMETRY",
                                lambda v: "%s km" % f"{v:,.0f}".replace(",", " "),
                                rodzic=self)
        self.k_passa = KafelLiczby("PASSA", lambda v: "%.0f dni" % v, rodzic=self)
        self.k_punkty = KafelLiczby("PUNKTY", lambda v: "%.0f" % v, rodzic=self)
        for kafel in (self.k_wizyty, self.k_km, self.k_passa, self.k_punkty):
            kl.addWidget(kafel, 0, Qt.AlignmentFlag.AlignVCenter)
        kl.addStretch(1)
        self.l_poprzedni = Napis("", 11.5, 600, S.TEKST_3, mono=True,
                                 wyrownanie=Qt.AlignmentFlag.AlignRight)
        kl.addWidget(self.l_poprzedni, 0, Qt.AlignmentFlag.AlignVCenter)
        self.karta_liczb.setMinimumHeight(92)
        z.addWidget(self.karta_liczb, 0)

        # ── skróty ────────────────────────────────────────────────
        skroty = QHBoxLayout()
        skroty.setSpacing(10)
        self.b_bilans = Przycisk("Bilans miesiąca", "glowny", 13, self)
        self.b_bilans.clicked.connect(lambda: self._okno.otworz_dzial(
            self._okno.NUMER_BILANSU))
        self.b_wyprawa = Przycisk("Nowa wyprawa", "zwykly", 13, self)
        self.b_wyprawa.clicked.connect(lambda: self._okno.otworz_dzial(
            self._okno.NUMER_WYPRAWY))
        self.b_mapa = Przycisk("Mapa tras", "zielony", 13, self)
        self.b_mapa.clicked.connect(self._okno.otworz_mape_tras)
        for przycisk in (self.b_bilans, self.b_wyprawa, self.b_mapa):
            skroty.addWidget(przycisk, 0, Qt.AlignmentFlag.AlignVCenter)
        skroty.addStretch(1)
        self.l_folder = Napis("", 11, 500, S.TEKST_3, mono=True,
                              wyrownanie=Qt.AlignmentFlag.AlignRight)
        skroty.addWidget(self.l_folder, 0, Qt.AlignmentFlag.AlignVCenter)
        z.addLayout(skroty)
        z.addStretch(1)

    # ── dane ──────────────────────────────────────────────────────
    def _animuj(self):
        return bool(getattr(self._okno, "_animacje", True))

    def _wyczysc_przystanki(self):
        while self.przystanki.count():
            pozycja = self.przystanki.takeAt(0)
            widget = pozycja.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def odswiez(self):
        dzis = datetime.date.today()
        dzien, nastepny, zrobione = dzis_w_trasie()
        self._wyczysc_przystanki()
        if dzien is not None and dzien.wizyty:
            ile = len(dzien.wizyty)
            self.l_dzien.setText("Dziś w trasie")
            self.l_meta.setText("%s · %.0f km · %s"
                                % (_wizyty_txt(ile), dzien.km,
                                   _godziny(dzien.minuty)))
            self.l_postep.setText("%d z %d" % (zrobione, ile))
            self.b_dzien.setText("Plan wizyt")
            pierwszy_otwarty = True
            for wizyta in dzien.wizyty[:self.MAKS_PRZYSTANKOW]:
                odwiedzona = False
                try:
                    odwiedzona = PMT.czy_odwiedzona(dzis, wizyta.adres or wizyta.nazwa)
                except Exception:
                    pass
                if odwiedzona:
                    barwa, punkt = S.TEKST_3, S.ZIELEN
                elif pierwszy_otwarty:
                    barwa, punkt = S.TEKST, S.CYJAN
                    pierwszy_otwarty = False
                else:
                    barwa, punkt = S.TEKST_2, S.z_alfa(S.TEKST_3, 150)
                opis = wizyta.nazwa or wizyta.adres
                if wizyta.miasto and wizyta.miasto not in opis:
                    opis = "%s · %s" % (opis, wizyta.miasto)
                self.przystanki.addWidget(Napis(opis, 12, 600, barwa, punkt=punkt))
            reszta = len(dzien.wizyty) - self.MAKS_PRZYSTANKOW
            if reszta > 0:
                self.przystanki.addWidget(
                    Napis("+%d" % reszta, 11.5, 700, S.TEKST_3, mono=True))
        else:
            self.l_dzien.setText("Dziś bez trasy")
            self.l_postep.setText("")
            if nastepny is not None:
                self.l_meta.setText("najbliższy dzień · %02d.%02d · %s"
                                    % (nastepny.data.day, nastepny.data.month,
                                       _wizyty_txt(len(nastepny.wizyty))))
                self.b_dzien.setText("Plan wizyt")
            else:
                self.l_meta.setText("brak planu")
                self.b_dzien.setText("Nowa wyprawa")

        liczby = liczby_miesiaca()
        animuj = self._animuj()
        self.k_wizyty.ustaw_wartosc(liczby.get("w_tym_miesiacu", 0), animuj)
        self.k_km.ustaw_wartosc(liczby.get("suma_km_ukonczone", 0), animuj)
        self.k_passa.ustaw_wartosc(liczby.get("passa_dni", 0), animuj)
        try:
            ile_punktow = len(PMT.wczytaj_punkty() or [])
        except Exception:
            ile_punktow = 0
        self.k_punkty.ustaw_wartosc(ile_punktow, animuj)
        poprzedni = liczby.get("poprzedni_miesiac", 0)
        self.l_poprzedni.setText("poprzedni miesiąc  %d" % poprzedni)
        self.odswiez_mape()

    def odswiez_mape(self):
        """Stan przycisku mapy — bez pliku przycisk stoi i mówi „brak”."""
        sciezka = self._okno.sciezka_mapy_tras()
        self.b_mapa.setEnabled(bool(sciezka))
        self.b_mapa.setText("Mapa tras" if sciezka else "Mapa tras · brak")
        self.l_folder.setText(os.path.basename(os.path.dirname(sciezka))
                              if sciezka else "")

    def resizeEvent(self, zdarzenie):
        super().resizeEvent(zdarzenie)
        wysrodkuj_tresc(self, self.MAKS_SZEROKOSC)

    def _klik_dnia(self):
        dzien, nastepny, _ = dzis_w_trasie()
        if dzien is None and nastepny is None:
            self._okno.otworz_dzial(self._okno.NUMER_WYPRAWY)
        else:
            self._okno.otworz_dzial(self._okno.NUMER_PLANU)

    def zatrzymaj_animacje(self):
        for kafel in (self.k_wizyty, self.k_km, self.k_passa, self.k_punkty):
            kafel.zatrzymaj_animacje()
        for przycisk in (self.b_dzien, self.b_bilans, self.b_wyprawa, self.b_mapa):
            przycisk.zatrzymaj_animacje()

    def showEvent(self, zdarzenie):
        super().showEvent(zdarzenie)
        self.odswiez()


class PanelOProgramie(QWidget):
    """O programie: wersja, silnik, plik, konto — nazwy, liczby i stany."""

    def __init__(self, okno):
        super().__init__(okno)
        self._okno = okno
        z = QVBoxLayout(self)
        z.setContentsMargins(0, 0, 0, 0)
        z.setSpacing(14)

        self.karta = KartaStanu(self, S.PROMIEN)
        kw = QVBoxLayout(self.karta)
        kw.setContentsMargins(24, 20, 24, 20)
        kw.setSpacing(10)
        self._wartosci = {}
        for klucz, etykieta in (("wersja", "WERSJA"), ("silnik", "SILNIK"),
                                ("plik", "PLIK"), ("konto", "KONTO"),
                                ("waznosc", "WAŻNOŚĆ")):
            wiersz = QHBoxLayout()
            wiersz.setSpacing(14)
            opis = Napis(etykieta, 9.5, 800, S.TEKST_3, odstep=0.9)
            opis.setFixedWidth(96)
            wartosc = Napis("", 12.5, 600, S.TEKST, mono=True)
            wiersz.addWidget(opis, 0, Qt.AlignmentFlag.AlignVCenter)
            wiersz.addWidget(wartosc, 1, Qt.AlignmentFlag.AlignVCenter)
            kw.addLayout(wiersz)
            self._wartosci[klucz] = wartosc
        z.addWidget(self.karta, 0)
        z.addStretch(1)

        dol = QHBoxLayout()
        dol.setSpacing(10)
        self.b_test = Przycisk("Test silnika", "zwykly", 13, self)
        self.b_test.clicked.connect(self._test_silnika)
        dol.addWidget(self.b_test, 0, Qt.AlignmentFlag.AlignVCenter)
        self.l_test = Napis("", 12.5, 600, S.TEKST_2, mono=True)
        dol.addWidget(self.l_test, 1, Qt.AlignmentFlag.AlignVCenter)
        z.addLayout(dol)

    def resizeEvent(self, zdarzenie):
        super().resizeEvent(zdarzenie)
        wysrodkuj_tresc(self, 820)

    def odswiez(self):
        napis, wazne = waznosc_konta(getattr(self._okno, "_pozostalo_dni", None))
        self._wartosci["wersja"].setText(PMT.wersja_pelna())
        self._wartosci["silnik"].setText(str(getattr(PMT, "SYGNATURA_SILNIKA", "")))
        try:
            self._wartosci["plik"].setText(os.path.basename(PMT.sciezka_programu()))
        except Exception:
            self._wartosci["plik"].setText("")
        self._wartosci["konto"].setText(self._okno._imie_zal or "—")
        self._wartosci["waznosc"].setText(napis or "—")
        self._wartosci["waznosc"].ustaw_kolor(S.MIETA if wazne else S.BURSZTYN)

    def _test_silnika(self):
        """Kontrolny przebieg silnika — liczby, nie zapewnienia."""
        self.l_test.setText("liczę…")
        QApplication.processEvents()
        try:
            dni = PMT.pobierz_dni_robocze(2026, 9)
            trasy = PMT.generuj_trasy(2000, "Warszawa", 52.23, 21.01,
                                      "mazowieckie", dni, "85010112345", 1.15)
            osiagnieto = getattr(trasy, "kwota_osiagnieta",
                                 sum(d.suma for d in trasy))
            self.l_test.setText("2 000 zł → %d dni · %.0f zł" % (len(trasy), osiagnieto))
            self.l_test.ustaw_kolor(S.MIETA if len(trasy) >= 7 else S.BURSZTYN)
        except Exception as blad:
            self.l_test.setText(str(blad)[:120])
            self.l_test.ustaw_kolor(S.BLAD)

    def showEvent(self, zdarzenie):
        super().showEvent(zdarzenie)
        self.odswiez()


# ═══════════════════════════════════════════════════════════════════════
#  OKNO
# ═══════════════════════════════════════════════════════════════════════

class SzynaDzialow(OK.Szyna):
    """Szyna prototypu z DZIAŁAJĄCYMI ikonami — każda otwiera panel programu.

    Numer w sygnale: 0–6 to ikony górne, 100 — dolna."""

    wybrano = pyqtSignal(int)

    IKONY = ("dom", "pinezka", "kalendarz", "wykres", "trend", "tarcza", "warstwy")
    DOLNE = ("info",)
    NAZWY = ("Ekran startowy", "Nowa wyprawa", "Plan wizyt", "Bilans miesiąca",
             "Twoja praca", "Kopia zapasowa", "Ustawienia")
    NAZWY_DOLNE = ("O programie",)

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._aktywna = 3         # ekran pracy to Bilans miesiąca

    def _pola_dolne(self):
        """Ikony pomocnicze stoją przy dolnej krawędzi — ile by ich nie było."""
        ile = len(self.DOLNE)
        return [QRectF(14, self.height() - 61 - (ile - 1 - i) * 49, 44, 44)
                for i in range(ile)]

    def nazwa(self, numer):
        numer = int(numer)
        if numer >= 100:
            dolny = numer - 100
            return self.NAZWY_DOLNE[dolny] if dolny < len(self.NAZWY_DOLNE) else ""
        return self.NAZWY[numer] if 0 <= numer < len(self.NAZWY) else ""

    def ustaw_aktywna(self, numer):
        self._aktywna = int(numer)
        self.update()

    def mousePressEvent(self, zdarzenie):
        numer = self._trafienie(zdarzenie.position())
        super().mousePressEvent(zdarzenie)
        if numer >= 0:
            self.wybrano.emit(numer)

    def mouseMoveEvent(self, zdarzenie):
        self.setToolTip(self.nazwa(self._trafienie(zdarzenie.position())))
        super().mouseMoveEvent(zdarzenie)

    def _ikona(self, malarz, rodzaj, pole, kolor):
        if rodzaj not in ("dom", "info"):
            super()._ikona(malarz, rodzaj, pole, kolor)
            return
        srodek = pole.center()
        pioro = QPen(kolor, 1.8)
        pioro.setCapStyle(Qt.PenCapStyle.RoundCap)
        pioro.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        malarz.setPen(pioro)
        malarz.setBrush(Qt.BrushStyle.NoBrush)
        if rodzaj == "dom":
            dach = QPainterPath()
            dach.moveTo(srodek.x() - 9.0, srodek.y() + 0.5)
            dach.lineTo(srodek.x(), srodek.y() - 8.5)
            dach.lineTo(srodek.x() + 9.0, srodek.y() + 0.5)
            malarz.drawPath(dach)
            malarz.drawRect(QRectF(srodek.x() - 6.0, srodek.y() + 0.5, 12.0, 8.0))
            return
        malarz.drawEllipse(srodek, 8.4, 8.4)
        malarz.drawLine(QPointF(srodek.x(), srodek.y() - 1.0),
                        QPointF(srodek.x(), srodek.y() + 4.6))
        malarz.setPen(Qt.PenStyle.NoPen)
        malarz.setBrush(QBrush(kolor))
        malarz.drawEllipse(QPointF(srodek.x(), srodek.y() - 4.6), 1.4, 1.4)


class PasekMiesiecy(OK.PasekGorny):
    """Pasek górny prototypu, który MELDUJE kliknięcia.

    Prototyp tylko podświetlał klikniętą zakładkę — miesiąc był ozdobą, a
    prawa strona (konto, dzwonek, zgłoszenie błędu, awatar) tylko rysunkiem.
    Numer w sygnale zakładki: 0 = poprzedni, 1 = pokazywany, 2 = następny."""

    wybrano_zakladke = pyqtSignal(int)
    klik_konta = pyqtSignal()
    klik_dzwonka = pyqtSignal()
    klik_bledu = pyqtSignal()
    klik_awatara = pyqtSignal()

    def mousePressEvent(self, zdarzenie):
        trafiona = None
        for numer, pole in enumerate(self._pola_zakladek()):
            if pole.contains(zdarzenie.position()):
                trafiona = numer
                break
        prawe = self.pole_prawe(zdarzenie.position())
        super().mousePressEvent(zdarzenie)
        if trafiona is not None:
            self.wybrano_zakladke.emit(trafiona)
        sygnal = {"konto": self.klik_konta, "dzwonek": self.klik_dzwonka,
                  "blad": self.klik_bledu, "awatar": self.klik_awatara}.get(prawe)
        if sygnal is not None:
            sygnal.emit()


class OknoNowegoWygladu(OknoPrototypu):
    """Ekran prototypu na prawdziwych danych i prawdziwym silniku."""

    KWOTA_STARTOWA = 1850.0

    # numery ikon szyny (kolejność: SzynaDzialow.IKONY, potem DOLNE)
    NUMER_STARTU = 0
    NUMER_WYPRAWY = 1
    NUMER_PLANU = 2
    NUMER_BILANSU = 3
    NUMER_PRACY = 4
    NUMER_KOPII = 5
    NUMER_USTAWIEN = 6
    NUMER_O_PROGRAMIE = 100

    # klucze w ~/.pmt_ustawienia.json — tym samym plikiem, co reszta programu
    USTAWIENIE_KWOTY = "nowy_kwota"
    USTAWIENIE_TRYBU = "nowy_tryb"
    USTAWIENIE_LIMITU = "nowy_limit_dnia"
    USTAWIENIE_WOLNYCH = "nowy_dni_wolne"
    PAMIEC_MIESIECY = 12          # ile miesięcy dni bez pracy zostaje w pliku

    def __init__(self, profil=None, rok=None, miesiac=None, rodzic=None,
                 stare_okno=None):
        self.profil = profil or dane_pracownika()
        # Imię z konta wiąże TYLKO wtedy, gdy profil nie został podany z
        # zewnątrz (tak robi program po zalogowaniu) — dokument wystawia się
        # na siebie, nie na kolegę.
        self._konto_wiaze = profil is None
        self._stare = stare_okno
        self._kod_uzytkownika = ""
        self._imie_zal = ""
        self._pozostalo_dni = None
        self._nieprzeczytane = 0
        self._intro = None
        self._intro_gra = False
        self._intro_zakonczone = False
        self._dopasowane = False
        biezacy = miesiac_biezacy()
        self.rok = int(rok or biezacy[0])
        self.miesiac = int(miesiac or biezacy[1])

        self.folder_wyniku = ""
        self.pliki_wyniku = []
        self._watek = None
        self._watki_zalegle = []        # wątki, które nie zdążyły się zatrzymać
        self._dialog_podpisu = None
        self._dialog_wysylki = None
        self._watek_wysylki = None
        self._dni_silnika = []
        self._pracownik_silnika = None
        self._powod_bledu = ""
        self._etap_silnika = ""
        self._kwota_zamowiona = 0.0
        self._formularz_zamowiony = None
        self._osiagnieto = 0.0
        self._niepelna = False
        self._pole_pesel = None
        self._nakladka = None           # rama paneli nad nowym oknem
        self._zegar_stylu = None        # pilnuje materiału w panelu
        self._ekran_startowy = None
        self._o_programie = None
        self._kopia = None

        self._ustaw_baze_z_profilu()
        self._ustaw_miesiac_w_prototypie()

        super().__init__(rodzic)

        self.setWindowTitle(PMT.tytul_okna())
        self._uzupelnij_karty()
        self._polacz_nowe()
        self._dodaj_mape_na_tace()
        self._zastosuj_konto()
        self._wolne = self._wolne_z_ustawien()
        self._przelicz_teraz(pierwszy=True)

        # Powiadomienia i komunikaty programu — ten sam mechanizm, co w starym
        # oknie; obie strony dzielą jedną historię (patrz _zepnij_ze_starym).
        self.toast = PMT.ToastNotification(self)
        self.toast.on_nowe_powiadomienie = self._nowe_powiadomienie
        self.panel_powiadomien = PMT.PanelPowiadomien(self)
        self.panel_powiadomien.podepnij_historie(self.toast.historia)
        self.panel_powiadomien.update_theme(True)
        zastosuj_styl_panelu(self.panel_powiadomien, tlo=None)
        zastosuj_styl_panelu(self.toast, tlo=None)
        if stare_okno is not None:
            self._zepnij_ze_starym(stare_okno)
        self._odswiez_pasek_konta()
        try:
            QApplication.instance().focusWindowChanged.connect(
                self._ubierz_okno_programu)
        except Exception:
            pass

    # ── budowa: pasek miesięcy zamiast ozdobnego ─────────────────────
    def _buduj(self):
        """Pasek górny i szynę prototypu wymieniamy na takie, które działają."""
        super()._buduj()
        stary = self.pasek
        self.pasek = PasekMiesiecy(self)
        self.pasek.MIESIACE = self._zakladki_miesiecy()
        self.pasek.ustaw_margines(stary.marg)
        stary.setParent(None)
        stary.deleteLater()
        self.pasek.wybrano_zakladke.connect(self._zakladka_miesiaca)
        self.pasek.klik_konta.connect(self.pokaz_stan_konta)
        self.pasek.klik_dzwonka.connect(self.przelacz_powiadomienia)
        self.pasek.klik_bledu.connect(self.zglos_blad)
        self.pasek.klik_awatara.connect(self.menu_konta)

        stara_szyna = self.szyna
        self.szyna = SzynaDzialow(self)
        self.szyna.setGeometry(stara_szyna.geometry())
        stara_szyna.setParent(None)
        stara_szyna.deleteLater()
        self.szyna.wybrano.connect(self.otworz_dzial)

    def _polacz_nowe(self):
        """Połączenia, których prototyp mieć nie mógł — nie miał co podłączać."""
        self.taca.pas.otwarty.connect(self._otworz_dokument_dnia)
        self.taca.b_folder.clicked.connect(self._otworz_folder)
        # Klik w kompas W TRAKCIE pracy przerywa generowanie. Sygnał „uruchom"
        # leci wyłącznie ze stanów spoczynkowych, więc bierzemy surowe „clicked".
        self.k_kompas.kompas.clicked.connect(self._klik_kompasu)
        karta = self.k_pracownik
        for pole in (karta.imie, karta.adres, self._pole_pesel):
            pole.editingFinished.connect(self._zapisz_pracownika)
        karta.stanowisko.currentIndexChanged.connect(
            lambda _i: self._zapisz_pracownika())

    # ── dane pracownika na ekranie ───────────────────────────────────
    def _adres_rozpoznany(self):
        """Adres pracownika rozłożony na części — walidatorem z programu."""
        try:
            return PMT.waliduj_adres(self.profil.adres)
        except Exception:
            return {}

    def _ustaw_baze_z_profilu(self):
        """Baza, województwo i okoliczne miasta wg adresu z profilu."""
        adres = self._adres_rozpoznany()
        self.baza_miasto = adres.get("baza_miasto") or "Warszawa"
        self.wojewodztwo = PMT.rozpoznaj_wojewodztwo(adres.get("kod_pocztowy", ""))
        self.baza_lat, self.baza_lng = wspolrzedne_bazy(
            self.baza_miasto, adres.get("adres_geo", ""), self.wojewodztwo)
        self.geo = miasta_wokol_bazy(self.baza_miasto, self.baza_lat,
                                     self.baza_lng, self.wojewodztwo)
        ustaw_swiat_mapy(self.geo, self.baza_miasto, self.baza_lat,
                         self.baza_lng, self.profil)

    def _uzupelnij_karty(self):
        """Prawdziwe dane w polach i w zakładkach miesięcy."""
        karta = self.k_pracownik
        karta.nota = "profil"          # dane z magazynu profili, nie z konta
        karta.imie.setText(self.profil.imie)
        karta.imie.setPlaceholderText("imię i nazwisko")
        karta.adres.setText(self.profil.adres)
        karta.adres.setPlaceholderText("ulica, kod pocztowy, miejscowość")
        karta.stanowisko.blockSignals(True)
        karta.stanowisko.clear()
        karta.stanowisko.addItems(STANOWISKA)
        indeks = karta.stanowisko.findText(self.profil.stanowisko)
        karta.stanowisko.setCurrentIndex(max(0, indeks))
        karta.stanowisko.blockSignals(False)

        # Miejsce po prototypowym haśle zajmuje PESEL — bez niego nie da się
        # wystawić delegacji, a nowy wygląd nie ma innego pola na te 11 cyfr.
        self._pole_pesel = karta.haslo
        self._pole_pesel.setEchoMode(QLineEdit.EchoMode.Normal)
        self._pole_pesel.setMaxLength(11)
        self._pole_pesel.setPlaceholderText("PESEL")
        self._pole_pesel.setText(self.profil.pesel)
        self._pole_pesel.show()

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
        # Kafel liczy DNI, a jedno polecenie wyjazdu obejmuje kilka dni —
        # z podpisem „DELEGACJE" liczba kłamałaby (8 dni to 2 delegacje).
        if hasattr(self.taca.k_dni, "_opis"):
            self.taca.k_dni._opis = "DNI W TRASIE"
            self.taca.k_dni.updateGeometry()

    def _zapisz_pracownika(self):
        """Pola karty PRACOWNIK → profil programu (~/.pmt_uzytkownicy.json).

        Zapisujemy dopiero przy komplecie imienia i poprawnego PESEL-u —
        magazyn profili jest po nich kluczowany i wpis bez nich byłby śmieciem."""
        karta = self.k_pracownik
        imie = " ".join(karta.imie.text().split())
        pesel = "".join(self._pole_pesel.text().split())
        adres = karta.adres.text().strip()
        stanowisko = karta.stanowisko.currentText().strip() or "KR"
        adres_inny = adres != self.profil.adres
        zmiana = (imie != self.profil.imie or pesel != self.profil.pesel
                  or adres_inny or stanowisko != self.profil.stanowisko)
        if not zmiana:
            return
        self.profil.imie = imie
        self.profil.pesel = pesel
        self.profil.adres = adres
        self.profil.stanowisko = stanowisko
        if imie and PMT.waliduj_pesel(pesel):
            self.profil.zrodlo = "profil"
            PMT.zapisz_profil(imie, pesel, adres, stanowisko, self.profil.silnik_idx)
        D.PRACOWNIK = imie or "—"
        D.STANOWISKO = stanowisko or "—"
        D.ADRES = adres or "—"
        if adres_inny:
            self._ustaw_baze_z_profilu()      # inny adres = inny rejon na mapie
            self._przebuduj_mape()
        self._przelicz_teraz()

    def _silnik_zmieniony(self, indeks):
        self.profil.silnik_idx = 1 if int(indeks) else 0
        D.STAWKA = self.profil.stawka
        if self.profil.imie and PMT.waliduj_pesel(self.profil.pesel):
            PMT.zapisz_profil(self.profil.imie, self.profil.pesel,
                              self.profil.adres, self.profil.stanowisko,
                              self.profil.silnik_idx)
        self._przelicz_teraz()

    # ── miesiąc: zakładki w pasku naprawdę przełączają ───────────────
    def _zakladki_miesiecy(self):
        poprzedni = (self.miesiac - 2) % 12 + 1
        nastepny = self.miesiac % 12 + 1
        return (PMT.MIESIACE_PL[poprzedni - 1],
                "%s %d" % (PMT.MIESIACE_PL[self.miesiac - 1], self.rok),
                PMT.MIESIACE_PL[nastepny - 1])

    def _ustaw_miesiac_w_prototypie(self):
        """Widżety prototypu czytają rok i miesiąc jako stałe modułu."""
        OK.ROK, OK.MIESIAC = self.rok, self.miesiac
        OK.DZIS = (datetime.date.today().day
                   if miesiac_biezacy() == (self.rok, self.miesiac) else 0)

    def _zakladka_miesiaca(self, indeks):
        krok = {0: -1, 2: 1}.get(int(indeks))
        if krok:
            self.ustaw_miesiac_o(krok)

    def ustaw_miesiac_o(self, krok):
        """Miesiąc w przód albo w tył — zakładkami paska albo klawiaturą."""
        numer = self.rok * 12 + (self.miesiac - 1) + int(krok)
        self.ustaw_miesiac(numer // 12, numer % 12 + 1)

    def ustaw_miesiac(self, rok, miesiac):
        """Przestawia cały ekran na inny miesiąc.

        Wynik silnika dotyczył POPRZEDNIEGO miesiąca, więc znika razem z tacą;
        dni bez pracy każdy miesiąc ma swoje."""
        rok, miesiac = int(rok), int(miesiac)
        if (rok, miesiac) == (self.rok, self.miesiac):
            return
        self.zatrzymaj_watek()
        self._zapamietaj_wolne()
        self.rok, self.miesiac = rok, miesiac
        self._dni_silnika = []
        self._pracownik_silnika = None
        self.folder_wyniku = ""
        self.pliki_wyniku = []
        self._kwota_zamowiona = 0.0
        self._formularz_zamowiony = None
        self._osiagnieto = 0.0
        self._niepelna = False
        self._powod_bledu = ""
        self._etap_silnika = ""
        self._po_generacji = False
        self._schowaj_tace()
        self._ustaw_miesiac_w_prototypie()
        self.pasek.MIESIACE = self._zakladki_miesiecy()
        self.pasek._aktywny = 1
        self.pasek.update()
        self._wolne = self._wolne_z_ustawien()
        self.k_kompas.kompas.ustaw_stan("gotowy")
        self.k_kompas.kompas.ustaw_postep(0.0)
        self.k_kompas.ustaw_etapy({n: "czeka" for n in OK.ETAPY})
        self.k_kompas.TYTUL = "Generuj dokumenty"
        self.tasma.ustaw_stan("zwykly")
        self.mapa.ustaw_stan("zwykly")
        self._przelicz_teraz()

    # ── ustawienia widoku zapisane na dysku ──────────────────────────
    def _klucz_wolnych(self):
        return "%04d-%02d" % (self.rok, self.miesiac)

    def _wolne_zapisane(self):
        zapis = PMT.ustawienie(self.USTAWIENIE_WOLNYCH, {})
        return dict(zapis) if isinstance(zapis, dict) else {}

    def _wolne_z_ustawien(self):
        dni = set()
        for wpis in (self._wolne_zapisane().get(self._klucz_wolnych()) or []):
            try:
                numer = int(wpis)
            except (TypeError, ValueError):
                continue
            if 1 <= numer <= 31:
                dni.add(numer)
        return dni

    def _zapamietaj_wolne(self):
        zapis = self._wolne_zapisane()
        nowy = dict(zapis)
        klucz = self._klucz_wolnych()
        if self._wolne:
            nowy[klucz] = sorted(self._wolne)
        else:
            nowy.pop(klucz, None)
        for stary in sorted(nowy)[:-self.PAMIEC_MIESIECY]:
            nowy.pop(stary, None)          # plik ustawień nie puchnie bez końca
        if nowy != zapis:
            PMT.zapisz_ustawienie(self.USTAWIENIE_WOLNYCH, nowy)

    def _wczytaj_widok(self):
        """Kwota, tryb pracy i limit dnia z ostatniego uruchomienia."""
        limit = PMT.ustawienie(self.USTAWIENIE_LIMITU, None)
        try:
            limit = float(limit)
        except (TypeError, ValueError):
            limit = None
        if limit is not None:
            for dopuszczalny in OK.LIMITY_DNIA:
                if abs(dopuszczalny - limit) < 0.005:
                    self._limit_dnia = dopuszczalny
        tryb = str(PMT.ustawienie(self.USTAWIENIE_TRYBU, "") or "")
        if tryb in self.k_parametry.tryb.pozycje:
            self.k_parametry.tryb.ustaw_aktywna(tryb)
        try:
            kwota = float(PMT.ustawienie(self.USTAWIENIE_KWOTY, 0) or 0)
        except (TypeError, ValueError):
            kwota = 0.0
        return kwota if kwota >= PMT.MIN_KWOTA else self.KWOTA_STARTOWA

    def _zapamietaj_widok(self):
        pary = ((self.USTAWIENIE_KWOTY, round(self._kwota(), 2)),
                (self.USTAWIENIE_TRYBU, self.k_parametry.tryb.aktywna()),
                (self.USTAWIENIE_LIMITU, round(float(self._limit_dnia), 2)))
        for klucz, wartosc in pary:
            if PMT.ustawienie(klucz, None) != wartosc:
                PMT.zapisz_ustawienie(klucz, wartosc)

    def _przelacz_wolny(self, numer):
        super()._przelacz_wolny(numer)
        self._zapamietaj_wolne()

    # ── podgląd (zamiast uproszczonego silnika prototypu) ────────────
    def _maks_miesiaca(self, tryb):
        return maks_kwota_miesiaca(self.rok, self.miesiac, tryb,
                                   self._wolne, self._limit_dnia,
                                   self.profil.stawka)

    def _przelicz_teraz(self, pierwszy=False):
        self._zegar_kwoty.stop()
        self._powod_bledu = ""        # powód odmowy dotyczył poprzednich danych
        if pierwszy:
            self.k_parametry.kwota.ustaw_tekst(
                D.zl(self._wczytaj_widok(), grosze=False))
            self.k_parametry.limit.ustaw_wartosc(self._limit_dnia)
        tryb = self.k_parametry.tryb.aktywna()
        self._maks_kwota = self._maks_miesiaca(tryb)
        self._za_duzo = bool(self._maks_kwota
                             and self._kwota() > self._maks_kwota + 0.005)

        pasuje = self._wynik_pasuje()
        if pasuje:
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
        if pasuje and self.folder_wyniku:
            # dni powstały od nowa — pieczęć podpisu czytamy z manifestu,
            # inaczej przeliczenie ekranu gasiłoby ją bez powodu
            self._wczytaj_podpisy(odswiez=False)

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
        # Prototyp cofał ekran po KAŻDYM przeliczeniu; tutaj wynik silnika
        # znika dopiero wtedy, gdy naprawdę przestał opisywać formularz —
        # i wraca, gdy wrócą dane, przy których powstały dokumenty.
        if self._po_generacji and not pierwszy and not pasuje:
            self._po_zmianie_danych()
        elif pasuje and self.folder_wyniku and not self._po_generacji:
            self._po_generacji = True
            self.tasma.ustaw_stan("po_generacji")
            self.mapa.ustaw_stan("sukces")
        if not pierwszy:
            self._zapamietaj_widok()
        self._odswiez_liczby()
        self._odswiez_dzien()
        self._odswiez_stan_kompasu()
        self._zegar_kwoty.stop()

    def _po_zmianie_danych(self):
        """Dokumenty przestały pasować — znika też ślad po ich kwocie."""
        super()._po_zmianie_danych()
        self._niepelna = False
        self._osiagnieto = 0.0

    def _snapshot_formularza(self):
        """Dane, po zmianie których gotowe dokumenty przestają być prawdziwe."""
        if self._pole_pesel is None:
            return None
        return (" ".join(self.k_pracownik.imie.text().split()),
                "".join(self._pole_pesel.text().split()),
                self.k_pracownik.adres.text().strip(),
                self.k_pracownik.stanowisko.currentText().strip(),
                int(self.profil.silnik_idx))

    def _wynik_pasuje(self):
        """Czy wynik silnika wciąż opisuje to, co stoi w formularzu."""
        if not self._dni_silnika:
            return False
        if abs(self._kwota_zamowiona - round(self._kwota(), 2)) >= 0.01:
            return False
        if self._formularz_zamowiony != self._snapshot_formularza():
            return False
        tryb = self.k_parametry.tryb.aktywna()
        for dzien in self._dni_silnika:
            if (dzien.data.year, dzien.data.month) != (self.rok, self.miesiac):
                return False
            if dzien.data.day in self._wolne:
                return False
            if tryb == "Tydzień" and dzien.data.weekday() >= 5:
                return False
            if dzien.suma > self._limit_dnia + 0.005:
                return False
        return True

    def _odswiez_liczby(self):
        super()._odswiez_liczby()
        if self._za_duzo:
            return
        if self._powod_bledu:
            self.k_parametry.kwota.ustaw_note(self._powod_bledu, True)
            return
        # STAN ŹRÓDŁA ODLEGŁOŚCI przy liczbach: „realne drogi",
        # „drogi z pamięci" albo „szacunek". Prototyp wpisywał tu
        # „realne drogi" na sztywno — także wtedy, gdy kilometry
        # pochodziły z linii prostej, i zanim cokolwiek policzono.
        z = D.podsumowanie(self._dni_w_trasie())
        stan = PMT.stan_zrodla_odleglosci()
        napis = OK._dni_txt(z["dni"])
        if self._niepelna and self._osiagnieto:
            # silnik nie dobił do zamówionej kwoty — na dokumentach jest ta
            napis += " · %s zł" % D.zl(self._osiagnieto, grosze=False)
        if stan["odcinki"]:
            napis += " · %s" % stan["etykieta"]
        self.k_parametry.kwota.ustaw_note(
            napis, stan["stan"] == PMT.ZRODLO_SZACUNEK or self._niepelna)

    # ── generowanie: PRAWDZIWE, w osobnym wątku ──────────────────────
    def _dane_do_generacji(self):
        """Parametry dla GeneratorThread albo (None, powód odmowy).

        Kontrola jest ta sama, co w App.proces: PESEL, adres, kwota, liczba
        dni roboczych i limit delegacji na dzień."""
        self._zapisz_pracownika()
        imie = " ".join(self.k_pracownik.imie.text().split())
        pesel = "".join(self._pole_pesel.text().split())
        adres = self.k_pracownik.adres.text().strip()
        kwota = self._kwota()
        if not imie:
            return None, "imię i nazwisko"
        if not PMT.waliduj_pesel(pesel):
            return None, "PESEL"
        if not adres:
            return None, "adres"
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
        maks = PMT.maks_kwota_miesiaca(len(dni), self.profil.stawka,
                                       limit_dnia=self._limit_dnia)
        if kwota > maks:
            return None, "maks. %s zł" % D.zl(maks, grosze=False)

        stanowisko = self.k_pracownik.stanowisko.currentText().strip() or "KR"
        woj = PMT.rozpoznaj_wojewodztwo(adres_d["kod_pocztowy"])
        PMT.zapisz_profil(imie, pesel, adres_d["adres_caly"], stanowisko,
                          self.profil.silnik_idx)
        return {
            "imie": imie, "pesel": pesel,
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
        self._niepelna = False
        self._osiagnieto = 0.0
        self._kwota_zamowiona = round(parametry["kwota_cel"], 2)
        self._formularz_zamowiony = self._snapshot_formularza()
        self._etap_silnika = "dane"
        self.k_kompas.TYTUL = "Przerwij"
        self.k_kompas.kompas.ustaw_stan("praca")
        self.ustaw_postep_pokazu(0.02)

        self._watek = PMT.GeneratorThread(parametry)
        self._watek.postep.connect(self._postep_generacji)
        self._watek.sukces.connect(self._sukces_generacji)
        self._watek.blad.connect(self._blad_generacji)
        if hasattr(self._watek, "anulowano"):
            self._watek.anulowano.connect(self._anulowano_generacji)
        self._watek.start()

    def _klik_kompasu(self):
        if self._watek is not None and self.k_kompas.kompas.stan() == "praca":
            self.anuluj_generowanie()

    def anuluj_generowanie(self):
        """Przerywa pracę silnika. Dokumenty powstają na samym końcu, więc
        przerwane generowanie nie zostawia po sobie ani jednego pliku."""
        watek = self._watek
        if watek is None:
            return False
        try:
            watek.anuluj()
        except AttributeError:
            watek.requestInterruption()
        self.k_kompas.kompas.ustaw_etap("przerywanie")
        return True

    def _odmowa(self, powod, blad=False):
        """Stan „nie da się" — nazwa albo liczba, bez zdań instruktażowych."""
        self._powod_bledu = str(powod or "")
        self._etap_silnika = ""
        self.k_kompas.TYTUL = "Generuj dokumenty"
        self.k_kompas.kompas.ustaw_stan("blad" if blad else "ostrzezenie")
        self.k_kompas.kompas.setToolTip(self._powod_bledu)
        self.k_kompas.ustaw_etapy({n: "czeka" for n in OK.ETAPY})
        self.k_parametry.kwota.ustaw_note(self._powod_bledu, True)

    def _postep_generacji(self, tekst, ulamek):
        self._etap_silnika = etap_silnika(tekst)
        self.ustaw_postep_pokazu(float(ulamek))

    def ustaw_postep_pokazu(self, t):
        """Łuk kompasu i plakietki etapów z meldunków silnika.

        Prototyp odgadywał etap z samego ułamka, a silnik dochodzi w trasach
        do 0,78 — plakietka „PDF" zapalałaby się, zanim powstanie pierwsza
        strona. Etap bierzemy więc z opisu, a ułamek zostaje na łuk."""
        if not self._etap_silnika:
            super().ustaw_postep_pokazu(t)
            return
        kompas = self.k_kompas.kompas
        kompas.ustaw_postep(max(0.0, min(1.0, float(t))))
        kompas.ustaw_azymut(None)
        try:
            biezacy = OK.ETAPY.index(self._etap_silnika)
        except ValueError:
            biezacy = 0
        self.k_kompas.ustaw_etapy(
            {nazwa: ("gotowe" if i < biezacy else
                     ("w_toku" if i == biezacy else "czeka"))
             for i, nazwa in enumerate(OK.ETAPY)})
        kompas.ustaw_etap(OK.ETAPY[biezacy])

    def _blad_generacji(self, wiadomosc):
        self._watek = None
        krotko = str(wiadomosc or "").strip().splitlines()[0][:40] or "błąd"
        self._odmowa(krotko, blad=True)

    def _anulowano_generacji(self):
        """Przerwane generowanie — ekran wraca do stanu sprzed kliknięcia."""
        self._watek = None
        self._etap_silnika = ""
        self._kwota_zamowiona = 0.0
        self._formularz_zamowiony = None
        self.k_kompas.TYTUL = "Generuj dokumenty"
        self.k_kompas.kompas.ustaw_stan("gotowy")
        self.k_kompas.kompas.ustaw_postep(0.0)
        self.k_kompas.kompas.ustaw_etap("")
        self.k_kompas.ustaw_etapy({n: "czeka" for n in OK.ETAPY})
        self._odswiez_stan_kompasu()

    def _sukces_generacji(self, finalne_dni, pracownik, folder):
        """Wynik silnika wchodzi na ekran: mapa, taśma, kartka, taca."""
        watek = self._watek
        self._watek = None
        self._etap_silnika = ""
        self._dni_silnika = list(finalne_dni)
        self._pracownik_silnika = pracownik
        self.folder_wyniku = folder
        self.pliki_wyniku = dokumenty_w_wyniku(folder)
        self._osiagnieto = round(sum(d.suma for d in finalne_dni), 2)
        self._niepelna = bool(getattr(watek, "_kwota_niepelna", False)) \
            or abs(self._osiagnieto - self._kwota_zamowiona) >= 0.01

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
        self._wczytaj_podpisy(odswiez=False)
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
    def _skrot_folderu(self):
        """Folder wyniku w zapisie z prototypu: „Pulpit / Rozliczenie_…"."""
        if not self.folder_wyniku:
            return ""
        sciezka = self.folder_wyniku.rstrip(os.sep)
        rodzic = os.path.basename(os.path.dirname(sciezka))
        nazwa = os.path.basename(sciezka)
        return "%s / %s" % (rodzic, nazwa) if rodzic else nazwa

    def _opisz_tace(self):
        """Podpisy i kafle tacy: prawdziwe pliki, folder i stan odległości."""
        if not self.folder_wyniku:
            return
        self.pliki_wyniku = dokumenty_w_wyniku(self.folder_wyniku)
        self.taca.l_sciezka.setText(
            "%s %d · %s" % (PMT.MIESIACE_PL[self.miesiac - 1], self.rok,
                            PMT._odmiana_plikow(len(self.pliki_wyniku))))
        self.taca.l_folder.setText(self._skrot_folderu())
        self.taca.l_folder.setToolTip(self.folder_wyniku)
        # Kafel kilometrów nosił na sztywno podpis „REALNE DROGI" — także
        # wtedy, gdy kilometry były szacunkiem z linii prostej.
        stan = PMT.stan_zrodla_odleglosci()
        opis = stan["etykieta"].upper() if stan["odcinki"] else "KILOMETRY"
        kafel = self.taca.k_km
        if getattr(kafel, "_opis", "") != opis:
            kafel._opis = opis
            kafel.updateGeometry()
            kafel.update()
        self._odswiez_stan_mapy()

    def _pokaz_tace(self, animacja=True):
        super()._pokaz_tace(animacja)
        self._opisz_tace()

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
        if not self.folder_wyniku:
            super()._odswiez_stan_tacy()
            return
        w_trasie = self._dni_w_trasie()
        podpisane = [d for d in w_trasie if d.podpisany]
        if podpisane:
            self.taca.l_stan.setText("%d z %d podpisanych"
                                     % (len(podpisane), len(w_trasie)))
        else:
            self.taca.l_stan.setText(DOK.opis_kompletu(self.folder_wyniku))

    # ── podpis i wysyłka: okna programu, nie makiety ─────────────────
    def _wczytaj_podpisy(self, odswiez=True):
        """Które dni są już podpisane — z manifestu paczki podpisowej.

        Manifest prowadzi pmt_podpis: dla każdej kopii PDF trzyma nazwę
        źródła i status. Numer delegacji z nazwy pliku wskazuje dokument,
        a dzień zna numer swojego dokumentu — stąd pieczęć na kartce."""
        if not self.folder_wyniku:
            return 0
        modul = PMT.modul_pomocniczy("pmt_wysylka")
        dane = None
        if modul is not None:
            try:
                dane, _katalog = modul.wczytaj_manifest(self.folder_wyniku)
            except Exception:
                dane = None
        modul_podpisu = PMT.modul_pomocniczy("pmt_podpis")
        podpisane = set()
        for wpis in ((dane or {}).get("pliki") or []):
            if not isinstance(wpis, dict):
                continue
            if wpis.get("status") != getattr(modul, "STATUS_PODPISANY", "podpisany"):
                continue
            nazwa = wpis.get("plik_zrodlowy") or wpis.get("plik") or ""
            if not self._to_ten_sam_plik(modul_podpisu, nazwa, wpis.get("skrot")):
                continue
            numer = DOK.numer_delegacji(nazwa)
            if numer:
                podpisane.add(numer)
        for dzien in self.dni:
            dzien.podpisany = getattr(dzien, "dokument", 0) in podpisane
        if odswiez:
            self.taca.ustaw_dni(self.dni_widoczne)
            self._opisz_tace()
            self.tasma.ustaw_dni(self.dni_widoczne)
            self.tasma.ustaw_dzis(OK.DZIS)
            self.tasma.ustaw_wybrany(self._wybrany)
            self._odswiez_dzien()
        return len(podpisane)

    def _to_ten_sam_plik(self, modul_podpisu, nazwa, skrot):
        """Czy pieczęć z manifestu dotyczy PLIKU, KTÓRY TERAZ LEŻY W FOLDERZE.

        Po ponownym generowaniu w tym samym folderze nazwy się powtarzają,
        a treść nie — bez porównania sumy kontrolnej świeży, niepodpisany
        dokument dostawałby pieczęć po poprzedniku."""
        if not nazwa or not skrot or modul_podpisu is None:
            return True          # stary manifest bez sumy — wierzymy statusowi
        zrodlo = os.path.join(self.folder_wyniku, nazwa)
        if not os.path.isfile(zrodlo):
            return True          # plik źródłowy zniknął — nie ma z czym równać
        try:
            return modul_podpisu.suma_sha256(zrodlo) == skrot
        except Exception:
            return True

    def _panel_podpisu(self):
        """Prawdziwy podpis elektroniczny — DialogPodpis nad pmt_podpis."""
        if not self.folder_wyniku or not os.path.isdir(self.folder_wyniku):
            return
        okno = PMT.DialogPodpis(self, folder=self.folder_wyniku, is_dark=True)
        self._dialog_podpisu = okno
        try:
            okno.exec()
        finally:
            try:
                okno.zatrzymaj_zegar()
            except Exception:
                pass
            self._dialog_podpisu = None
        self._wczytaj_podpisy()
        self._odswiez_stan_tacy()

    def _panel_wysylki(self):
        """Prawdziwa wysyłka pocztą — DialogWysylka nad pmt_wysylka."""
        if not self.folder_wyniku or not os.path.isdir(self.folder_wyniku):
            return
        okno = PMT.DialogWysylka(self, folder=self.folder_wyniku,
                                 imie=self.profil.imie, miesiac=self.miesiac,
                                 rok=self.rok, is_dark=True)
        self._dialog_wysylki = okno
        try:
            okno.exec()
        finally:
            try:
                okno.zakoncz_watek()
            except Exception:
                pass
            self._watek_wysylki = getattr(okno, "watek", None)
            self._dialog_wysylki = None
        self._wczytaj_podpisy()
        self._odswiez_stan_tacy()

    # ═══════════════════════════════════════════════════════════════
    #  KONTO ZALOGOWANEJ OSOBY (pasek górny, prawa strona)
    # ═══════════════════════════════════════════════════════════════

    @property
    def _imie_zalogowany(self):
        return self._imie_zal

    @_imie_zalogowany.setter
    def _imie_zalogowany(self, imie):
        self._imie_zal = str(imie or "")
        self._zastosuj_konto()
        self._odswiez_pasek_konta()

    @property
    def _demo_pozostalo(self):
        return self._pozostalo_dni

    @_demo_pozostalo.setter
    def _demo_pozostalo(self, dni):
        self._pozostalo_dni = dni
        if self._stare is not None:
            self._stare._demo_pozostalo = dni
        self._odswiez_pasek_konta()

    def _zastosuj_konto(self):
        """Imię z konta w karcie PRACOWNIK — i zamknięte na klucz.

        Ta sama zasada, co w starym oknie: pole z imieniem jest wypełnione
        z konta i nieedytowalne."""
        if not self._konto_wiaze or not hasattr(self, "k_pracownik"):
            return
        imie = PMT.online_imie_uzytkownika() or self._imie_zal
        if not imie:
            return
        pole = self.k_pracownik.imie
        if pole.text().strip() != imie:
            pole.blockSignals(True)
            pole.setText(imie)
            pole.blockSignals(False)
            self.profil.imie = imie
            D.PRACOWNIK = imie
        pole.setReadOnly(True)
        pole.setToolTip("Konto %s" % (PMT.online_kod_uzytkownika() or "?"))
        self.k_pracownik.nota = "konto"
        self.k_pracownik.update()

    def _odswiez_pasek_konta(self):
        """Prawa strona paska: ważność konta, licznik dzwonka, inicjały."""
        pasek = getattr(self, "pasek", None)
        if pasek is None:
            return
        napis, wazne = waznosc_konta(self._pozostalo_dni)
        pasek.konto_napis = napis
        pasek.konto_ok = bool(wazne)
        pasek.inicjaly = inicjaly_konta(
            PMT.online_imie_uzytkownika() or self._imie_zal or self.profil.imie)
        pasek.powiadomienia = self._nieprzeczytane
        pasek.update()

    def _nowe_powiadomienie(self, _tytul="", _opis="", _sukces=True):
        self._nieprzeczytane += 1
        # dymek maluje się od nowa przy każdym komunikacie — materiał też
        zastosuj_styl_panelu(self.toast, tlo=None)
        if getattr(self, "panel_powiadomien", None) is not None \
                and self.panel_powiadomien.isVisible():
            self.panel_powiadomien.odswiez()
            zastosuj_styl_panelu(self.panel_powiadomien, tlo=None)
        self._odswiez_pasek_konta()

    def pokaz_stan_konta(self):
        """Kto jest zalogowany i do kiedy — prosto z pliku statusu."""
        kod = self._kod_uzytkownika or PMT.online_kod_uzytkownika() or "—"
        imie = PMT.online_imie_uzytkownika() or self._imie_zal or "—"
        napis, wazne = waznosc_konta(self._pozostalo_dni)
        self.toast.show_toast("Konto %s" % kod, "%s\n%s" % (imie, napis),
                              success=bool(wazne))

    def przelacz_powiadomienia(self):
        """Dzwonek: lista ostatnich komunikatów pod paskiem górnym."""
        panel = self.panel_powiadomien
        if panel.isVisible():
            panel.hide()
            return
        self._nieprzeczytane = 0
        panel.update_theme(True)
        panel.odswiez()
        zastosuj_styl_panelu(panel, tlo=None)
        pole = self.pasek._pola_prawe.get("dzwonek")
        x = self.width() - panel.width() - 24
        y = OK.PASEK_H + 8
        if pole is not None:
            x = int(self.pasek.x() + pole.right() - panel.width())
            y = int(self.pasek.y() + pole.bottom() + 8)
        panel.move(max(8, min(x, self.width() - panel.width() - 8)), max(8, y))
        panel.raise_()
        panel.show()
        self._odswiez_pasek_konta()

    def zglos_blad(self):
        import webbrowser
        webbrowser.open("mailto:" + PMT._adres_zgloszen())

    def menu_konta(self):
        """Awatar: hasło, karta testera, animacja startowa, wylogowanie."""
        menu, akcje = self.buduj_menu_konta()
        pole = self.pasek._pola_prawe.get("awatar")
        if pole is not None:
            punkt = self.pasek.mapToGlobal(QPoint(int(pole.x()) - 90,
                                                  int(pole.bottom()) + 8))
        else:
            punkt = QCursor.pos()
        wybor = menu.exec(punkt)
        if wybor is None:
            return
        akcja = akcje.get(wybor)
        if akcja is not None:
            akcja()

    def buduj_menu_konta(self):
        """Menu awatara i akcje pod jego pozycjami — jedno miejsce prawdy."""
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background:#0E1726; color:#E8EEF8; border:1px solid "
            "rgba(255,255,255,0.14); border-radius:10px; padding:6px; }"
            "QMenu::item { padding:7px 18px; border-radius:7px; }"
            "QMenu::item:selected { background:rgba(0,240,255,0.16); }"
            "QMenu::separator { height:1px; background:rgba(255,255,255,0.10);"
            " margin:5px 8px; }")
        akcja_haslo = menu.addAction("Zmień hasło")
        akcja_tester = menu.addAction("Karta testera")
        akcja_intro = menu.addAction("Animacja startowa")
        akcja_intro.setCheckable(True)
        akcja_intro.setChecked(not bool(PMT.ustawienie("bez_intra", False)))
        menu.addSeparator()
        akcja_wyloguj = menu.addAction("Wyloguj")
        return menu, {akcja_haslo: self.zmien_haslo,
                      akcja_tester: lambda: PMT.uruchom_karte_testera(self),
                      akcja_intro: lambda: self.przelacz_intro(akcja_intro.isChecked()),
                      akcja_wyloguj: self.wyloguj}

    def zmien_haslo(self):
        PMT.zmien_haslo_w_programie(
            self, self._kod_uzytkownika or PMT.online_kod_uzytkownika(), True)

    def przelacz_intro(self, wlaczona):
        PMT.zapisz_ustawienie("bez_intra", not bool(wlaczona))

    def wyloguj(self):
        """Wylogowanie i logowanie na inne konto — bez zamykania programu."""
        kod = PMT.online_kod_uzytkownika() or "—"
        pytanie = QMessageBox(self)
        pytanie.setWindowTitle("Wylogowanie")
        pytanie.setText("Wylogować użytkownika %s?" % kod)
        pytanie.setInformativeText("Pojawi się ekran logowania — możesz od razu "
                                   "zalogować się na inne konto. Plany i dokumenty "
                                   "zostają nienaruszone.")
        pytanie.setIcon(QMessageBox.Icon.Question)
        pytanie.setStandardButtons(QMessageBox.StandardButton.Yes
                                   | QMessageBox.StandardButton.No)
        pytanie.setDefaultButton(QMessageBox.StandardButton.No)
        pytanie.button(QMessageBox.StandardButton.Yes).setText("Wyloguj")
        pytanie.button(QMessageBox.StandardButton.No).setText("Anuluj")
        if pytanie.exec() != QMessageBox.StandardButton.Yes:
            return
        try:
            minuty = 0.0
            start = getattr(PMT, "_START_SESJI", None)
            if start is not None:
                minuty = (datetime.datetime.now() - start).total_seconds() / 60.0
            PMT.online_zdarzenie_sesji("wylogowanie", minuty)
            PMT.online_synchronizuj()
        except Exception:
            pass
        PMT.online_wyloguj()
        self.hide()
        if self._stare is not None:
            self._stare.hide()
        kod, imie = PMT.dialog_logowania()
        if not kod:
            QApplication.quit()
            return
        PMT.online_zapisz_kod(kod)
        try:
            PMT.ustaw_uzytkownika_planu(imie or "", kod or "")
        except Exception:
            pass
        self._kod_uzytkownika = kod
        self._imie_zal = imie or ""
        if self._stare is not None:
            self._stare._kod_uzytkownika = kod
            self._stare._imie_zalogowany = imie or ""
            try:
                PMT.App._po_zmianie_konta(self._stare, imie or "")
            except Exception:
                pass
        self.przejmij_konto()
        PMT.online_zdarzenie(uruchomienia=1)
        PMT.online_synchronizuj_w_tle()
        self.show()
        self.raise_()
        self.activateWindow()
        self.toast.show_toast(
            "Zalogowano",
            ("Witaj, " + imie.split()[0] + "!") if imie else ("Kod " + str(kod)),
            success=True)

    def przejmij_konto(self):
        """Po zmianie konta ekran pokazuje dane NOWEJ osoby, nie poprzedniej."""
        self.zatrzymaj_watek()
        self.profil = dane_pracownika()
        self._konto_wiaze = True
        self._ustaw_baze_z_profilu()
        self._odswiez_karte_pracownika()
        self._zastosuj_konto()
        self.folder_wyniku = ""
        self.pliki_wyniku = []
        self._dni_silnika = []
        self._po_generacji = False
        self._przebuduj_mape()
        self._wolne = self._wolne_z_ustawien()
        self._przelicz_teraz()
        self._odswiez_pasek_konta()

    def _odswiez_karte_pracownika(self):
        """Pola karty PRACOWNIK z bieżącego profilu (bez budzenia zapisu)."""
        karta = self.k_pracownik
        for pole, tekst in ((karta.imie, self.profil.imie),
                            (karta.adres, self.profil.adres),
                            (self._pole_pesel, self.profil.pesel)):
            if pole is None:
                continue
            pole.blockSignals(True)
            pole.setReadOnly(False)
            pole.setText(tekst)
            pole.blockSignals(False)
        karta.stanowisko.blockSignals(True)
        karta.stanowisko.setCurrentIndex(
            max(0, karta.stanowisko.findText(self.profil.stanowisko)))
        karta.stanowisko.blockSignals(False)
        self.k_parametry.pojemnosc.blockSignals(True)
        self.k_parametry.pojemnosc.setCurrentIndex(self.profil.silnik_idx)
        self.k_parametry.pojemnosc.blockSignals(False)
        D.PRACOWNIK = self.profil.imie or "—"
        D.STANOWISKO = self.profil.stanowisko or "—"
        D.ADRES = self.profil.adres or "—"
        D.STAWKA = self.profil.stawka

    # ═══════════════════════════════════════════════════════════════
    #  SZYNA: KAŻDA IKONA OTWIERA PRAWDZIWY PANEL
    # ═══════════════════════════════════════════════════════════════

    def akcje_szyny(self):
        """Numer ikony → akcja. Żadna ikona nie może zostać bez wpisu."""
        return {self.NUMER_STARTU: self.dzial_ekran_startowy,
                self.NUMER_WYPRAWY: self.dzial_nowa_wyprawa,
                self.NUMER_PLANU: self.dzial_plan_wizyt,
                self.NUMER_BILANSU: self.dzial_bilans_miesiaca,
                self.NUMER_PRACY: self.dzial_twoja_praca,
                self.NUMER_KOPII: self.dzial_kopia_zapasowa,
                self.NUMER_USTAWIEN: self.dzial_ustawienia,
                self.NUMER_O_PROGRAMIE: self.dzial_o_programie}

    def otworz_dzial(self, numer):
        akcja = self.akcje_szyny().get(int(numer))
        if akcja is not None:
            akcja()

    def stare_okno(self):
        """Egzemplarz App — magazyn paneli, których nowy ekran sam nie rysuje.

        Panele (Planer, Plan Wizyt, Twoja praca, Ustawienia) to widżety potomne
        tamtego okna, spięte z jego dymkami, paskiem postępu i Trybem Trasy.
        Trzymamy więc jeden egzemplarz — ale POKAZUJE je rama nowego ekranu
        (pokaz_panel), a samo okno App zostaje ukryte przez cały czas."""
        if self._stare is None:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            try:
                self._stare = PMT.App()
            finally:
                QApplication.restoreOverrideCursor()
            self._zepnij_ze_starym(self._stare)
        return self._stare

    def _zepnij_ze_starym(self, stare):
        """Jedno konto, jedna historia powiadomień, jedna ścieżka wylogowania."""
        try:
            stare._kod_uzytkownika = self._kod_uzytkownika or PMT.online_kod_uzytkownika()
            stare._imie_zalogowany = self._imie_zal
            stare._demo_pozostalo = self._pozostalo_dni
            # Okno aktualizacji czeka na koniec animacji startowej — ta gra
            # teraz w nowym oknie, więc stare musi o niej wiedzieć.
            stare._intro_gra = not self._intro_zakonczone
            stare._intro_zakonczone = self._intro_zakonczone
        except Exception:
            pass
        try:
            stare.toast.historia = self.toast.historia
            stare.panel_powiadomien.podepnij_historie(self.toast.historia)
            poprzednie = stare.toast.on_nowe_powiadomienie

            def _obie_strony(tytul, opis, sukces, _p=poprzednie):
                if _p is not None:
                    _p(tytul, opis, sukces)
                self._nowe_powiadomienie(tytul, opis, sukces)

            stare.toast.on_nowe_powiadomienie = _obie_strony
        except Exception:
            pass
        try:
            # Ekran powitalny tamtego okna animuje się w ukryciu — gasimy go
            # na stałe: jego miejsce zajął ekran startowy nowego systemu.
            QTimer.singleShot(0, stare.ekran_powitalny.stop)
        except Exception:
            pass
        try:
            oryginalne = stare._wyloguj_uzytkownika

            def _wylogowanie(_o=oryginalne):
                _o()
                self.przejmij_konto()

            stare._wyloguj_uzytkownika = _wylogowanie
            stare.btn_wyloguj.clicked.disconnect()
            stare.btn_wyloguj.clicked.connect(_wylogowanie)
        except Exception:
            pass

    # ── rama paneli nad nowym oknem ──────────────────────────────────
    def nakladka(self):
        """Rama, w której panele programu stają NAD nowym ekranem."""
        if self._nakladka is None:
            self._nakladka = NakladkaDzialu(self)
            self._nakladka.zamknieto.connect(self.dzial_bilans_miesiaca)
            self._zegar_stylu = QTimer(self)
            self._zegar_stylu.setInterval(1200)
            self._zegar_stylu.timeout.connect(self._pilnuj_stylu)
            self._ustaw_geometrie_nakladki()
        return self._nakladka

    def _ustaw_geometrie_nakladki(self):
        """Panel zakrywa wszystko poza szyną i paskiem górnym."""
        if self._nakladka is None:
            return
        self._nakladka.setGeometry(OK.SZYNA_W, OK.PASEK_H,
                                   max(320, self.width() - OK.SZYNA_W),
                                   max(240, self.height() - OK.PASEK_H))

    def resizeEvent(self, zdarzenie):
        super().resizeEvent(zdarzenie)
        self._ustaw_geometrie_nakladki()

    def pokaz_panel(self, widget, tytul, podtytul="", numer=None):
        """Gotowy panel programu w materiale nowego systemu, nad nowym oknem."""
        rama = self.nakladka()
        if numer is not None:
            self.szyna.ustaw_aktywna(numer)
        if self.panel_powiadomien.isVisible():
            self.panel_powiadomien.hide()
        if widget is not None and not getattr(widget, "_nowy_system", False):
            ukryj_naglowek_panelu(widget)
            zastosuj_styl_panelu(widget)
            pilnuj_materialu(widget)
            widget.installEventFilter(self)
        rama.ustaw_panel(widget, tytul, podtytul)
        self._ustaw_geometrie_nakladki()
        rama.show()
        rama.raise_()
        if self._zegar_stylu is not None and not self._zegar_stylu.isActive():
            self._zegar_stylu.start()
        return widget

    def _pilnuj_stylu(self):
        """Panel, który przebudował sobie wiersze, dostaje materiał na nowo."""
        rama = self._nakladka
        if rama is None or not rama.isVisible():
            if self._zegar_stylu is not None:
                self._zegar_stylu.stop()
            return
        rama.odswiez_podtytul()
        panel = rama.panel()
        if panel is not None and not getattr(panel, "_nowy_system", False):
            zastosuj_styl_panelu(panel)

    def eventFilter(self, obiekt, zdarzenie):
        rodzaj = zdarzenie.type()
        if rodzaj == QEvent.Type.Hide and self._nakladka is not None \
                and obiekt is self._nakladka.panel():
            QTimer.singleShot(0, self._panel_sam_sie_zamknal)
        elif rodzaj == QEvent.Type.Resize and obiekt is self.taca:
            przycisk = getattr(self.taca, "b_mapa", None)
            if przycisk is not None:
                przycisk.setVisible(self.taca.width() >= 1060)
        return super().eventFilter(obiekt, zdarzenie)

    def _ubierz_okno_programu(self, okno_qt):
        """Okno dialogowe programu otwarte z panelu — w materiale nowego ekranu.

        Ustawienia planowania, cykle, notatki czy potwierdzenia to osobne
        okna klas z PMT_Delegacje. Nie przepisujemy ich — tłumaczymy arkusze
        tak samo jak w panelach, gdy okno staje na wierzchu."""
        if okno_qt is None:
            return
        try:
            for widget in QApplication.topLevelWidgets():
                if widget.windowHandle() is not okno_qt:
                    continue
                if widget is self or isinstance(widget, (Panel, PMT.App)):
                    return
                if getattr(widget, "_nowy_system", False):
                    return
                if type(widget).__module__ not in ("PMT_Delegacje", "__main__"):
                    return
                widget.setStyleSheet(widget.styleSheet() + ARKUSZ_PANELU)
                zastosuj_styl_panelu(widget, tlo=None)
                return
        except Exception:
            pass

    def _panel_sam_sie_zamknal(self):
        """Panel zamknięty własnym przyciskiem — rama schodzi razem z nim."""
        rama = self._nakladka
        if rama is not None and rama.isVisible():
            panel = rama.panel()
            if panel is None or not panel.isVisible():
                rama.zamknij()

    # ── działy szyny ─────────────────────────────────────────────────
    def dzial_ekran_startowy(self):
        """Ekran startowy: dzisiejsza trasa, liczby miesiąca, skróty."""
        if self._ekran_startowy is None:
            self._ekran_startowy = EkranStartowy(self)
            self._ekran_startowy._nowy_system = True
        self._ekran_startowy.odswiez()
        return self.pokaz_panel(self._ekran_startowy, "Ekran startowy",
                                data_slownie(datetime.date.today()),
                                self.NUMER_STARTU)

    def dzial_nowa_wyprawa(self):
        """Planer Nowej Wyprawy — przystanki, import z Excela, planowanie."""
        okno = self.stare_okno()
        PMT.App._pokaz_planer(okno)
        return self.pokaz_panel(
            okno.overlay_planer, "Nowa wyprawa",
            lambda p=okno.overlay_planer: _punkty_txt(
                len(getattr(p, "_przystanki", None) or [])),
            self.NUMER_WYPRAWY)

    def dzial_plan_wizyt(self):
        okno = self.stare_okno()
        plan = getattr(okno, "_gotowy_plan", None) or PMT.wczytaj_plan()
        if plan is not None:
            okno._gotowy_plan = plan
            PMT.App._pokaz_ostatni_plan(okno)
            dni = plan.get("dni", []) or []
            ile = plan.get("suma_wizyt") or sum(len(d.wizyty) for d in dni)
            podtytul = "%d dni · %s" % (len(dni), _wizyty_txt(int(ile)))
        else:
            podtytul = "brak planu"
        return self.pokaz_panel(okno.overlay_plan, "Plan wizyt", podtytul,
                                self.NUMER_PLANU)

    def dzial_bilans_miesiaca(self):
        """Bilans miesiąca to sam ekran pracy — kwota, dni, mapa, kompas."""
        if self._nakladka is not None and self._nakladka.isVisible():
            self._nakladka.hide()
        if self._stare is not None and self._stare.isVisible():
            self._stare.hide()
        self.szyna.ustaw_aktywna(self.NUMER_BILANSU)
        self.show()
        self.raise_()
        self.activateWindow()

    def dzial_twoja_praca(self):
        okno = self.stare_okno()
        PMT.App._pokaz_statystyki(okno)
        liczby = liczby_miesiaca()
        return self.pokaz_panel(
            okno.overlay_staty, "Twoja praca",
            "%s w tym miesiącu" % _wizyty_txt(int(liczby.get("w_tym_miesiacu", 0))),
            self.NUMER_PRACY)

    def dzial_kopia_zapasowa(self):
        okno = self.stare_okno()
        if self._kopia is None:
            self._kopia = PMT.DialogKopiaZapasowa(okno, is_dark=True)
            self._kopia.setWindowFlags(Qt.WindowType.Widget)
            self._kopia.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            usun_wywody(self._kopia, ("Wszystko, co masz w programie", "🛡"))
            for ramka in self._kopia.findChildren(QFrame, "KopBox"):
                self._kopia.layout().setAlignment(ramka, Qt.AlignmentFlag.AlignCenter)
        return self.pokaz_panel(self._kopia, "Kopia zapasowa", "", self.NUMER_KOPII)

    def dzial_ustawienia(self):
        okno = self.stare_okno()
        PMT.App._pokaz_panel_admina(okno)
        return self.pokaz_panel(okno.overlay_admin, "Ustawienia", "",
                                self.NUMER_USTAWIEN)

    def dzial_o_programie(self):
        if self._o_programie is None:
            self._o_programie = PanelOProgramie(self)
            self._o_programie._nowy_system = True
        self._o_programie.odswiez()
        return self.pokaz_panel(self._o_programie, "O programie", "",
                                self.NUMER_O_PROGRAMIE)

    def dzial_ekran_glowny(self):
        """Powrót na ekran pracy — panel schodzi ze sceny."""
        self.dzial_bilans_miesiaca()

    # ── mapa tras miesiąca ───────────────────────────────────────────
    def sciezka_mapy_tras(self):
        """Plik mapy tras: z folderu tej sesji albo z ostatniego rozliczenia."""
        return plik_mapy_tras(self.folder_wyniku) or \
            plik_mapy_tras(folder_z_mapa_tras())

    def otworz_mape_tras(self):
        """Mapa tras w przeglądarce — tym samym mechanizmem, co dokumenty."""
        sciezka = self.sciezka_mapy_tras()
        if not sciezka:
            self._odswiez_stan_mapy()
            return ""
        PMT.otworz_w_systemie(sciezka)
        self.taca.l_stan.setText(os.path.basename(sciezka))
        self._zegar_stanu.start()
        return sciezka

    def _odswiez_stan_mapy(self):
        """Bez pliku przycisk stoi i pokazuje stan — bez tłumaczenia dlaczego."""
        jest = bool(self.sciezka_mapy_tras())
        przycisk = getattr(self.taca, "b_mapa", None)
        if przycisk is not None:
            przycisk.setEnabled(jest)
            przycisk.setText("Mapa tras" if jest else "Mapa tras · brak")
        if self._ekran_startowy is not None:
            self._ekran_startowy.odswiez_mape()
        return jest

    def _dodaj_mape_na_tace(self):
        """Przycisk mapy tras na tacy dokumentów — obok „Otwórz folder”."""
        self.taca.b_mapa = Przycisk("Mapa tras", "zwykly", 13, self.taca)
        self.taca.b_mapa.clicked.connect(self.otworz_mape_tras)
        uklad = self.taca.layout()
        for i in range(uklad.count()):
            wiersz = uklad.itemAt(i).layout()
            if wiersz is not None and wiersz.indexOf(self.taca.b_folder) >= 0:
                wiersz.insertWidget(wiersz.indexOf(self.taca.b_folder) + 1,
                                    self.taca.b_mapa, 0,
                                    Qt.AlignmentFlag.AlignVCenter)
                break
        self.taca.installEventFilter(self)
        self._odswiez_stan_mapy()

    # ═══════════════════════════════════════════════════════════════
    #  ANIMACJA STARTOWA (ta sama, co w starym oknie)
    # ═══════════════════════════════════════════════════════════════

    def intro_po_sprawdzeniu(self, imie="", limit_ms=0):
        if imie:
            self._imie_zalogowany = imie
        self.pokaz_intro(imie or self._imie_zal)

    def pokaz_intro(self, imie=""):
        """Animacja startowa jako nakładka — teraz nad nowym ekranem."""
        try:
            PMT._dziennik_animacji("nowy wygląd: start intro w wersji %s"
                                   % PMT.WERSJA_PROGRAMU)
        except Exception:
            pass
        self._intro = None
        self._intro_gra = False
        self._intro_zakonczone = False
        QTimer.singleShot(50000, self._intro_straznik)
        katalog = PMT._katalog_programu()
        if bool(PMT.ustawienie("bez_intra", False)) \
                or PMT._intro_wylaczone_plikiem(katalog):
            self._intro_koniec()
            return
        try:
            from intro_zywa_mapa import sprobuj_intro
            dane = PMT.dane_intra_z_dysku(imie or "")
            if imie:
                dane["imie"] = str(imie).split()[0]
            self._intro_gra = True
            if sprobuj_intro(self, dane=dane, po_zakonczeniu=self._intro_koniec,
                             katalog_zasobow=katalog, ciemny=True):
                return
            self._intro_gra = False
        except Exception:
            self._intro_gra = False
        try:
            self._intro = PMT.AnimacjaStartowa(imie, is_dark=True, parent=self)
            self._intro.zakonczony.connect(self._intro_koniec)
            self._intro.setGeometry(self.rect())
            self._intro.raise_()
            self._intro.show()
        except Exception:
            self._intro_koniec()

    def _intro_koniec(self):
        if self._intro_zakonczone:
            return
        self._intro_gra = False
        self._intro_zakonczone = True
        nakladka = self._intro
        self._intro = None
        if nakladka is not None:
            try:
                nakladka._zapisz_diag()
            except Exception:
                pass
            nakladka.hide()
            nakladka.deleteLater()
        self._zdejmij_intro_zywej_mapy()
        if self._stare is not None:
            self._stare._intro_gra = False
            self._stare._intro_zakonczone = True
        try:
            PMT._dziennik_animacji("nowy wygląd: intro zakończone — ekran główny")
        except Exception:
            pass
        QTimer.singleShot(900, lambda: PMT.zaproszenie_testera(
            self, self._imie_zal or "", True))

    def _zdejmij_intro_zywej_mapy(self):
        for dziecko in self.findChildren(QWidget):
            if type(dziecko).__name__ != "IntroZywaMapa":
                continue
            try:
                dziecko._koniec_wyslany = True
                dziecko._timer.stop()
            except Exception:
                pass
            dziecko.hide()
            dziecko.deleteLater()

    def _intro_straznik(self):
        """Gdy animacja nie zgłosi końca, i tak odsłaniamy program."""
        if not self._intro_zakonczone:
            self._intro_koniec()

    # ── okno jako główne okno programu ───────────────────────────────
    def show(self):
        if not self._dopasowane and self.parent() is None:
            self._dopasowane = True
            self.dopasuj_do_ekranu()
        super().show()

    # ── klawiatura ───────────────────────────────────────────────────
    def keyPressEvent(self, zdarzenie):
        klucz = zdarzenie.key()
        if klucz == Qt.Key.Key_Escape and self._watek is not None:
            self.anuluj_generowanie()
            return
        if klucz == Qt.Key.Key_Escape and self._nakladka is not None \
                and self._nakladka.isVisible():
            self._nakladka.zamknij()
            return
        if klucz == Qt.Key.Key_PageUp:
            self.ustaw_miesiac_o(-1)
            return
        if klucz == Qt.Key.Key_PageDown:
            self.ustaw_miesiac_o(1)
            return
        super().keyPressEvent(zdarzenie)

    # ── sprzątanie ───────────────────────────────────────────────────
    def zatrzymaj_watek(self, czas_ms=6000):
        """Wątek generowania nie może przeżyć okna ani zmiany miesiąca."""
        watek = self._watek
        self._watek = None
        if watek is None:
            return
        try:
            watek.anuluj()
        except AttributeError:
            watek.requestInterruption()
        if watek.isRunning() and not watek.wait(int(czas_ms)):
            # Wciąż pracuje: TRZYMAMY referencję. Odśmiecony QThread w biegu
            # ubija cały proces („QThread: Destroyed while still running").
            self._watki_zalegle.append(watek)

    def zamknij_okna_pomocnicze(self):
        """Podpis i wysyłka mają własny zegar i własny wątek — gasimy oba."""
        okno = self._dialog_podpisu
        self._dialog_podpisu = None
        if okno is not None:
            try:
                okno.zatrzymaj_zegar()
                okno.reject()
            except Exception:
                pass
        okno = self._dialog_wysylki
        self._dialog_wysylki = None
        if okno is not None:
            try:
                okno.zakoncz_watek()
                okno.reject()
            except Exception:
                pass
        watek = self._watek_wysylki
        self._watek_wysylki = None
        if watek is not None and watek.isRunning():
            watek.wait(4000)
        if self._zegar_stylu is not None:
            self._zegar_stylu.stop()

    def closeEvent(self, zdarzenie):
        self.zamknij_okna_pomocnicze()
        self.zatrzymaj_watek()
        stare = self._stare
        self._stare = None
        if stare is not None:
            try:
                stare.close()
            except Exception:
                pass
        super().closeEvent(zdarzenie)


# ═══════════════════════════════════════════════════════════════════════
#  URUCHOMIENIE
# ═══════════════════════════════════════════════════════════════════════

def poczekaj_na_generacje(app, okno, sekundy=240):
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
    # kadr z PRACUJĄCEGO kompasu: łuk w połowie drogi i plakietki etapów
    granica = datetime.datetime.now() + datetime.timedelta(seconds=120)
    while (okno._watek is not None and datetime.datetime.now() < granica
           and okno.k_kompas.kompas.postep() < 0.5):
        app.processEvents()
    if okno._watek is not None:
        zapisz("zrzut_nowy_2_praca.png")
    if poczekaj_na_generacje(app, okno):
        zapisz("zrzut_nowy_3_taca.png")
        print("folder wyniku:", okno.folder_wyniku)
        for sciezka in okno.pliki_wyniku:
            print("   plik:", os.path.basename(sciezka))
    else:
        print("generowanie nie doszło do skutku:", okno._powod_bledu or "?")

    for nazwa in zapisane:
        print("zapisano", nazwa)
    return 0


def main(argv=None):
    """Samodzielne uruchomienie — do pracy nad samym wyglądem.

    Program uruchamia nowy wygląd przez PMT_Delegacje.zbuduj_okno_glowne()
    (po zalogowaniu i z egzemplarzem starego okna pod panele)."""
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
    okno.zamknij_okna_pomocnicze()
    okno.zatrzymaj_watek()
    return kod


# ═══════════════════════════════════════════════════════════════════════
#  NIEPODŁĄCZONE — stan na dziś, uczciwie
#
#  1. Panele (Nowa wyprawa, Plan wizyt, Twoja praca, Ustawienia, Kopia
#     zapasowa) to wciąż widżety okna App — nowy jest materiał i rama, nie
#     ich wnętrze. Wykresy i siatki rysowane pędzlem w PMT_Delegacje
#     (WykresSlupkowy, WykresDonut, SiatkaMiesiacaPlan, PierscienPostepu)
#     mają barwy wypalone w paintEvent i tłumaczenie arkuszy ich nie sięga.
#  2. Te panele mówią o sobie całymi zdaniami („kliknij Zaplanuj wizyty,
#     aby ułożyć trasy") — teksty zostają, bo są częścią ich logiki.
#  3. Podgląd przed generowaniem to szacunek (podglad_miesiaca) — prawdziwe
#     trasy powstają dopiero po naciśnięciu kompasu.
#  4. Motyw jasny nie dotyczy nowego ekranu — panele w nim otwierane są
#     zawsze ciemne (materiał nowego systemu).
#  5. W oknie o minimalnym rozmiarze (1040×660) karta planera ma własne
#     minimum szersze niż rama i przycina się o kilkanaście pikseli.
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
