# -*- coding: utf-8 -*-
"""PMT PLANER — EKRAN PROGRAMU.

Okno główne programu: widżety prototypu (prototyp/proto_*.py) na danych
i silniku z PMT_Delegacje.py.

    python PMT_Delegacje.py             (program: logowanie → to okno)
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
                           awatar (hasło, karta testera, wylogowanie)
    · po starcie           po_starcie: dymek „Rozpoznano pracownika"
                           i zaproszenie testera (bez animacji startowej)
    · pracownik            profil z ~/.pmt_uzytkownicy.json (zapisz_profil)
    · dni robocze          pobierz_dni_robocze + ustaw_tryb_pracy
    · miasta i odległości  zaladuj_baze, coords_z_miasta, oblicz_dystans
    · rejon na mapie       prawdziwa szerokość i długość każdej miejscowości
                           (miasta_dla_mapy → MapaDnia.ustaw_miasta), ranga
                           z liczby sieci w bazie miast i ze STOLICE
    · trasy, km i kwoty    generuj_trasy  (w osobnym wątku, GeneratorThread;
                           w tym czasie ekran to przelot nad rejonem —
                           proto_mapa.PrzelotRejonu, zaczep INTRO_GENEROWANIA)
    · dokumenty PDF        generuj_pdfy + generuj_mape_html (ten sam wątek)
    · pliki na tacy        pmt_dokumenty.dokumenty_w_folderze(folder wyniku)
    · podpis elektroniczny PMT.DialogPodpis nad modułem pmt_podpis
    · wysyłka pocztą       PMT.DialogWysylka nad modułem pmt_wysylka
    · dane pracownika      pola karty PRACOWNIK ↔ zapisz_profil / _wczytaj_store
    · wybór miesiąca       zakładki paska górnego (także PgUp / PgDn); zakładka
                           miesiąca, który minął bez wpisu w historii i bez
                           folderu z dokumentami, nosi kropkę (PasekMiesiecy.kropki)
                           — JEDNĄ regułą miesiac_nierozliczony / stan_miesiaca,
                           tą samą, co kratka roku i taca; miesiąc wpisu ustala
                           PMT._rok_miesiac_wpisu (także wpisy starszych wersji)
    · kratka roku          na ekranie startowym: 12 pól z kwotą, km i dniami
                           z historii miesięcy (historia_okna = wpisy + foldery
                           na dysku); pole przestawia program na ten miesiąc
    · dni bez pracy        kalendarz PanelDniBezPracy z dniami zablokowanymi
                           z silnika (_dni_zablokowane → PMT.dni_zablokowane_miesiaca:
                           święta i dni poza tygodniem roboczym w danym trybie)
    · PESEL                pole karty PRACOWNIK pod znakami; oko odsłania cyfry
                           na CZAS_PODGLADU_PESEL albo do utraty fokusu
    · zgłoś błąd           PMT.mailto_zgloszenia (adres oczyszczony, jawny temat,
                           bez cc/bcc) otwierany przez otworz_adres (Qt)
    · taca miesięcy        pasek nad kartkami: miesiące z gotowymi dokumentami;
                           pigułka wczytuje kartki z TAMTEGO folderu (tabele
                           przejazdów PDF-ów, pmt_dokumenty.dni_kompletu) bez
                           generowania; folder, mapa, podpis i wysyłka działają
                           na wybranym miesiącu
    · ustawienia widoku    kwota, tryb i dni bez pracy w ~/.pmt_ustawienia.json
                           (ustawienie / zapisz_ustawienie)
    · stan odległości      stan_zrodla_odleglosci przy kwocie i na tacy
    · odwrót kartki        klik w kartkę nad mapą obraca ją: odwrót to dzień
                           taki, jaki był naprawdę — godziny z dokumentu,
                           postoje, kilometry każdego odcinka z jego źródłem
                           (RawEtap.zrodlo: drogi / pamięć / szacunek) i linią
                           prostą (etapy_widzetu → Dzien.etapy); uchwyt przy
                           prawym brzegu zwija kartkę
    · białe plamy rejonu   mapa pod delikatną mgłą; miejscowości ze śladem
                           obecności (pole „miejsca" historii miesięcy —
                           _miejsca_odkryte → MapaDnia.ustaw_odkryte) są
                           odsłonięte i świecą, trasa dnia zawsze; w rogu
                           mapy licznik odkryte / w zasięgu

CO JEST SZACUNKIEM (do chwili wygenerowania)
    podglad_miesiaca() — miesiąc rozpisany REGUŁAMI silnika, ale na sucho:
    bez sieci, bez pamięci dróg i bez skutków ubocznych generuj_trasy.
    Przeniesione reguły: liczba dokumentów i dni (ile_dni_wyjazdowych),
    kierunek dnia z rotacji sektorów, pierścień startu, karencja
    miejscowości, pojemność doby jako sufit dnia, rozciąganie kilometrów do
    kwoty mnożnikiem z przedziału [MNOZNIK_MIN, sufit dnia] osobnym dla
    każdego dnia, przycinanie najdłuższych dni i podział dni na dokumenty
    (PMT._podziel_na_dokumenty). Dlatego dni podglądu mają RÓŻNE kwoty,
    różne kilometry i różne miejscowości, a żaden nie przekracza tego, co
    da się przejechać w ciągu doby. Losowanie jest zasiane wejściem, więc
    to samo wejście daje ten sam podgląd. Po wygenerowaniu podgląd znika,
    a jego miejsce zajmuje prawdziwy wynik przetłumaczony przez
    dni_widzetow_z_tras().

CZEGO JESZCZE NIE MA — sekcja „NIEPODŁĄCZONE" na końcu pliku.
"""

import datetime
import math
import os
import random
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
                          QSize, QTimer, QUrl, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QCursor, QDesktopServices,  # noqa: E402
                         QIcon, QLinearGradient, QPainter, QPainterPath,
                         QPen, QPixmap)
from PyQt6.QtWidgets import (QAbstractSpinBox, QApplication,       # noqa: E402
                             QCheckBox, QComboBox, QFrame, QHBoxLayout,
                             QLabel, QLineEdit, QMenu, QMessageBox,
                             QPushButton, QRadioButton, QSizePolicy,
                             QVBoxLayout, QWidget)

import proto_styl as S                                             # noqa: E402
import proto_dane as D                                             # noqa: E402
import proto_okno as OK                                            # noqa: E402
from proto_mapa import (MapaDnia, PrzelotRejonu, RANGA_BAZA, RANGA_MIASTO,  # noqa: E402
                        RANGA_WIES)
from proto_spektakl import SpektaklMiesiaca                        # noqa: E402
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
MIAST_NA_MAPIE = 28            # tyle miast dokłada mapa do gotowego wyniku
# Podgląd wybiera przystanki z TEJ puli. Przy 28 miastach ta sama wieś
# wracała po kilkanaście razy w miesiącu; silnik ma w tym samym miejscu
# 96–104 miejscowości w promieniu pętli, więc tyle bierzemy i tutaj.
MIAST_PODGLADU = 96            # pula miast podglądu (i świata mapy przed generowaniem)
# 64 miejscowości starczały, dopóki podgląd rozpisywał kwotę na kilkanaście
# dni. Odkąd liczba dni bierze się z przeciętnego dnia, a nie z sufitu doby,
# miesiąc bywa dwudziestodniowy — przy ciaśniejszej puli najczęstsza
# miejscowość wracała sześć razy.
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


def ikona_oka(odsloniete, bok=18):
    """Oko do pola PESEL rysowane QPainterem: zamknięte — kontur z kreską
    (cyfry pod znakami), otwarte — kontur ze źrenicą w cyjanie (cyfry widać).
    Żadnego pliku graficznego, żadnego tekstu."""
    dpr = 2
    pix = QPixmap(bok * dpr, bok * dpr)
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    kolor = S.CYJAN if odsloniete else S.TEKST_3
    pioro = QPen(kolor, 1.5)
    pioro.setCapStyle(Qt.PenCapStyle.RoundCap)
    pioro.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pioro)
    p.setBrush(Qt.BrushStyle.NoBrush)
    sx, sy = bok / 2.0, bok / 2.0
    szer, wys = bok * 0.40, bok * 0.24
    oko = QPainterPath(QPointF(sx - szer, sy))
    oko.quadTo(QPointF(sx, sy - wys * 2.0), QPointF(sx + szer, sy))
    oko.quadTo(QPointF(sx, sy + wys * 2.0), QPointF(sx - szer, sy))
    p.drawPath(oko)
    if odsloniete:
        p.setBrush(QBrush(kolor))
        p.drawEllipse(QPointF(sx, sy), bok * 0.11, bok * 0.11)
    else:
        p.drawLine(QPointF(sx - szer * 0.85, sy + wys * 1.55),
                   QPointF(sx + szer * 0.85, sy - wys * 1.55))
    p.end()
    return QIcon(pix)


def otworz_adres(odnosnik):
    """Odnośnik (mailto:, https:) w programie wskazanym przez system —
    jedno miejsce, które testy podmieniają atrapą."""
    try:
        return bool(QDesktopServices.openUrl(QUrl(str(odnosnik))))
    except Exception as blad:
        PMT.log_error(blad)
        return False


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


# ── ranga miejscowości: z bazy miast programu, a nie z nazwy ─────────
PROG_SIECI_MIASTA = 4          # tyle sieci handlowych ma już miasto, nie wieś
_RANGI_Z_BAZY = {}


def rangi_miast_programu():
    """{nazwa: ranga} z bazy miast silnika — liczone raz i pamiętane.

    Wielkości miejscowości program nigdzie nie trzyma wprost. Ma za to przy
    każdym mieście liczbę sieci handlowych i typ jednostki — i to jedyna
    miara, jaką da się uczciwie podać mapie: cztery sieci albo miasto
    powiatowe rysują się plamą miasta, mniej — plamą wsi."""
    if _RANGI_Z_BAZY:
        return _RANGI_Z_BAZY
    try:
        for lista in PMT.MIASTA_RAW.values():
            for miasto in lista:
                nazwa = miasto.get("n")
                if not nazwa:
                    continue
                duze = (str(miasto.get("typ", "")) == "powiat"
                        or int(miasto.get("sieci", 0) or 0) >= PROG_SIECI_MIASTA)
                ranga = RANGA_MIASTO if duze else RANGA_WIES
                _RANGI_Z_BAZY[nazwa] = max(ranga, _RANGI_Z_BAZY.get(nazwa, 0))
    except Exception:
        _RANGI_Z_BAZY.clear()
    return _RANGI_Z_BAZY


PROMIEN_STOLICY = 0.10         # stopnia szerokości — tyle wystarczy na stolicę


def _stolica_wojewodztwa(lat, lng):
    """Czy ten punkt to stolica województwa.

    Baza miast silnika to miejscowości DO OBJAZDU — wielkich miast w niej nie
    ma wcale, więc sama Warszawa czy Kraków wypadłyby na mapie jako wieś.
    Rozpoznajemy je po współrzędnych z PMT.STOLICE."""
    try:
        for (slat, slng) in PMT.STOLICE.values():
            if (abs(lat - slat) <= PROMIEN_STOLICY
                    and abs(lng - slng) <= PROMIEN_STOLICY * 1.6):
                return True
    except Exception:
        pass
    return False


def miasta_dla_mapy(geo, baza_nazwa):
    """{nazwa: (szerokość, długość, ranga)} — to, co przyjmuje MapaDnia.

    Współrzędne są te same, z których silnik liczy kilometry: pamięć
    geokodowania i offline'owy indeks miast programu. Gdy choć jednej
    miejscowości ich brakuje, zwracamy pusty słownik — mapa zostaje wtedy
    przy układzie z proto_dane i nie ma prawa trafić na nazwę, której nie zna."""
    rangi = rangi_miast_programu()
    wynik = {}
    for nazwa, wspolrzedne in (geo or {}).items():
        if isinstance(wspolrzedne, (str, bytes)):
            return {}          # napis rozpadłby się na znaki: "52.2" → 5 i 2
        try:
            lat = float(wspolrzedne[0])
            lng = float(wspolrzedne[1])
        except (TypeError, ValueError, IndexError, KeyError):
            return {}
        if not (-90.0 < lat < 90.0 and -180.0 < lng < 180.0):
            return {}
        if abs(lat) < 0.001 and abs(lng) < 0.001:
            return {}      # zera wpisuje silnik tam, gdzie adres się nie zgeokodował
        if nazwa == baza_nazwa:
            ranga = RANGA_BAZA
        else:
            ranga = rangi.get(nazwa, RANGA_WIES)
            if ranga < RANGA_MIASTO and _stolica_wojewodztwa(lat, lng):
                ranga = RANGA_MIASTO
        wynik[nazwa] = (lat, lng, ranga)
    return wynik


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


def przelot_generowania(okno):
    """Wstawka INTRO_GENEROWANIA: spektakl nad rejonem na czas pracy silnika
    (proto_spektakl.SpektaklMiesiaca — przelot z choreografią: noc, nitki
    światła po drogach ułożonych dni, kartki dokumentów, lądowanie).

    Nakładka staje dokładnie na mapie, nad kartką i pigułką, pod tacą
    i dymkami. Rejon to te same miejscowości, które dostała mapa, i ten sam
    krajobraz; obraz sprzed przelotu (mapa z kartką, tak jak leży na
    ekranie) odchodzi w tył w pierwszych klatkach. Uderzenie pieczęci
    rozpędza kompas; pominięty kliknięciem pokaz zgłasza się oknu
    (zakonczono → _intro_zeszlo). Zwraca widżet albo None."""
    mapa = getattr(okno, "mapa", None)
    if mapa is None or not mapa.isVisible():
        return None
    miasta = miasta_dla_mapy(getattr(okno, "geo", None),
                             getattr(okno, "baza_miasto", ""))
    try:
        data = datetime.date(int(okno.rok), int(okno.miesiac), 1)
    except (AttributeError, TypeError, ValueError):
        data = None
    film = SpektaklMiesiaca.nad_mapa(mapa, miasta, baza=getattr(okno, "baza_miasto", None),
                                     mapa_pod=lambda: okno.mapa, rodzic=okno, data=data,
                                     na_stempel=getattr(okno, "_uderzenie_pieczeci", None))
    film.ustaw_start(okno.grab(mapa.geometry()))
    zeszlo = getattr(okno, "_intro_zeszlo", None)
    if zeszlo is not None:
        film.zakonczono.connect(lambda: zeszlo(film))
    film.show()
    film.raise_()
    for nazwa in ("taca", "toast"):
        widget = getattr(okno, nazwa, None)
        if widget is not None:
            widget.raise_()
    return film


def miasta_wokol_bazy(baza_nazwa, baza_lat, baza_lng, woj, ile=MIAST_PODGLADU,
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
    dokumencie (kwota dokumentu przez pojemność doby), potem sufit wierszy
    strony A4 — jeśli dni się na niej nie mieszczą, dokumentów musi być
    więcej — a na końcu dolny próg trzech dni. Kolejność jak w silniku."""
    if kwota <= 0 or stawka <= 0 or dostepnych <= 0:
        return 0
    # Liczba dni bierze się z PRZECIĘTNEGO dnia, nie z sufitu doby — sufit
    # odpowiada na inne pytanie („ile najwyżej"), a podgląd ma powiedzieć, ile
    # dni zajmie ta kwota. Przy suficie podgląd pokazywał 14 dni tam, gdzie
    # silnik rozpisywał 19.
    sufit = max(PMT.kwota_typowego_dnia(stawka, limit_dnia), PMT.MIN_KWOTA)
    z_wierszy = max(1, PMT.MAX_ETAPOW_DOKUMENTU // (PMT.POSTOJE_TYPOWE + 1))
    dokumentow = PMT.ile_dokumentow(kwota)
    w_dokumencie = max(1, math.ceil((kwota / dokumentow - 0.005) / sufit))
    if w_dokumencie > z_wierszy:
        w_dokumencie = z_wierszy
        dokumentow = max(dokumentow,
                         math.ceil((kwota - 0.005) / (w_dokumencie * sufit)))
    return max(1, min(dostepnych, max(3, dokumentow * w_dokumencie)))


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


# ═══════════════════════════════════════════════════════════════════════
#  PODGLĄD DNI — REGUŁY SILNIKA NA SUCHO
#
#  Podgląd NIE woła generuj_trasy: jedno wywołanie to 36–145 zapytań
#  o drogi, a zegar kwoty odpala przeliczenie po każdym klawiszu — okno
#  stanęłoby przy pisaniu. Zamiast tego przenosimy tu te reguły silnika,
#  które widać na ekranie:
#    · kierunek dnia z rotacji sektorów i pierścień, z którego rusza dzień,
#    · karencję miejscowości (ta sama wieś nie wraca co drugi dzień),
#    · pojemność doby (posiłek + postoje + jazda) jako sufit dnia,
#    · rozciąganie kilometrów do kwoty mnożnikiem z przedziału
#      [MNOZNIK_MIN, sufit dnia] — osobnym dla każdego dnia,
#    · przycinanie najdłuższych dni, gdy kilometrów wyszło za dużo,
#    · podział dni na dokumenty sufitem kwoty i wierszy strony A4.
#  Losowanie jest zasiane wejściem (kwota, miesiąc, tryb, baza, stawka,
#  dni bez pracy), więc to samo wejście daje ten sam podgląd i taśma nie
#  miga przy przeliczaniu.
# ═══════════════════════════════════════════════════════════════════════

KARENCJA_PODGLADU = (35, 14, 8)   # drabinka odpoczynku miejscowości z silnika
ZAPAS_DNI_PODGLADU = 2            # tyle dni ponad plan rozpisuje silnik
ZAPAS_KM_PODGLADU = 1.04          # ... i tyle pojemności ponad kwotę
CELE_DNIA_PODGLADU = (5, 7)       # tylu przystanków szuka dzień (zakres silnika)
MIN_POSTOJOW_DNIA = 2             # niżej silnik już nie schodzi przy przycinaniu
PROB_DNIA_PODGLADU = 8            # tyle podejść do ułożenia jednego dnia


def _karencja_podgladu(ile_miast, ile_dni):
    """Ile dni miejscowość odpoczywa, zanim wolno ją powtórzyć.

    Ta sama drabinka co w generuj_trasy: gdy miast starczy na wszystkie dni
    bez powtórek — 35 dni, czyli cały miesiąc; gdy jest ciaśniej — 14, a
    w najrzadszych rejonach 8."""
    ile_dni = max(1, int(ile_dni))
    if ile_miast >= ile_dni * 6:
        return KARENCJA_PODGLADU[0]
    if ile_miast >= ile_dni * 3:
        return KARENCJA_PODGLADU[1]
    return KARENCJA_PODGLADU[2]


def _ziarno_podgladu(kwota, rok, miesiac, tryb, stawka, baza_nazwa, wylaczone):
    """Klucz losowania: to samo wejście → ten sam podgląd (taśma nie miga)."""
    return "|".join(("%d" % int(round(float(kwota) * 100)),
                     "%04d-%02d" % (int(rok), int(miesiac)), str(tryb),
                     "%d" % int(round(float(stawka) * 10000)), str(baza_nazwa),
                     ",".join("%d" % n for n in sorted(wylaczone or ()))))


def _miasta_podgladu(geo, baza_nazwa, promien):
    """Miasta w zasięgu pętli dziennej: (nazwa, lat, lng, odległość, sektor)."""
    if baza_nazwa not in geo:
        return []
    baza_lat, baza_lng = geo[baza_nazwa]
    wynik = []
    for nazwa, wspolrzedne in geo.items():
        if nazwa == baza_nazwa:
            continue
        lat, lng = wspolrzedne[0], wspolrzedne[1]
        odleglosc = PMT.oblicz_dystans(baza_lat, baza_lng, lat, lng)
        if odleglosc < PMT.MIN_ODLEGLOSC_OD_BAZY or odleglosc > promien:
            continue
        wynik.append((nazwa, lat, lng, odleglosc,
                      PMT.wyznacz_sektor(lat, lng, baza_lat, baza_lng)))
    wynik.sort(key=lambda m: (m[3], m[0]))     # stała kolejność = powtarzalność
    return wynik


def _promien_podgladu(miasta_blisko, ile_dni):
    """Promień pętli: ciasny tam, gdzie miast pod bazą dużo — jak w silniku."""
    return PMT.MAX_PROMIEN_PETLI_KM if miasta_blisko >= max(12, ile_dni) \
        else PROMIEN_MAPY_KM


def _petla_podgladu(miasta, sektor, pierscien, max_skok, ile_celow,
                    zajete, rng):
    """Jedna pętla dzienna: start w zadanym kierunku, potem najbliższy wolny
    sąsiad — łańcuch „po drodze" z generuj_trasy.

    Pierścień ogranicza CAŁY dzień, nie sam punkt startowy: dzień „gniazdo"
    ma być ciasną pętlą pod bazą, a nie łańcuchem, który krótkimi skokami
    wywędrował na drugi koniec województwa.

    `zajete` to miejscowości na karencji. Gdy karencja nie zostawia nic,
    wracamy do pełnej puli: lepiej powtórzyć wieś niż pokazać pusty dzień."""
    w_zasiegu = [m for m in miasta if m[3] <= pierscien[1]] or list(miasta)
    wolne = [m for m in w_zasiegu if m[0] not in zajete] or list(w_zasiegu)
    if not wolne:
        return []
    obok = (PMT.SEKTORY_KOLEJNOSC[(PMT.SEKTORY_KOLEJNOSC.index(sektor) - 1) % 8],
            PMT.SEKTORY_KOLEJNOSC[(PMT.SEKTORY_KOLEJNOSC.index(sektor) + 1) % 8])
    srodek = (pierscien[0] + pierscien[1]) / 2.0
    wagi = []
    for _n, _la, _lg, odleglosc, sek in wolne:
        waga = 0.001 if odleglosc < pierscien[0] - 8.0 \
            else 1000.0 / (abs(odleglosc - srodek) + 8.0)
        if sek == sektor:
            waga *= 1000.0
        elif sek in obok:
            waga *= 12.0
        else:
            waga *= 0.05
        wagi.append(waga)
    trasa = [rng.choices(wolne, weights=wagi, k=1)[0]]
    uzyte = {trasa[0][0]}
    while len(trasa) < ile_celow:
        _n, lat, lng, _o, _s = trasa[-1]
        najlepszy, najlepsza = None, max_skok
        for kandydat in wolne:
            if kandydat[0] in uzyte:
                continue
            skok = PMT.oblicz_dystans(lat, lng, kandydat[1], kandydat[2])
            if skok < 4.0 or skok >= najlepsza:
                continue          # to praktycznie ten sam punkt albo za daleko
            najlepszy, najlepsza = kandydat, skok
        if najlepszy is None:
            break
        trasa.append(najlepszy)
        uzyte.add(najlepszy[0])
    return [m[0] for m in trasa]


def km_petli_podgladu(geo, baza_nazwa, przystanki):
    """Kilometry pętli baza → przystanki → baza, w linii prostej."""
    if not przystanki or baza_nazwa not in geo:
        return 0.0
    baza_lat, baza_lng = geo[baza_nazwa][0], geo[baza_nazwa][1]
    lat, lng, km = baza_lat, baza_lng, 0.0
    for nazwa in przystanki:
        cel = geo.get(nazwa)
        if not cel:
            continue
        km += PMT.oblicz_dystans(lat, lng, cel[0], cel[1])
        lat, lng = cel[0], cel[1]
    return km + PMT.oblicz_dystans(lat, lng, baza_lat, baza_lng)


def _uporzadkuj_petle(geo, baza_nazwa, przystanki):
    """Kolejność przystanków bez przeplotów — dwuoptymalizacja pętli.

    Silnik szuka najlepszej kolejności przeglądem wszystkich permutacji
    (optymalizuj_tsp): przy siedmiu punktach to pięć tysięcy przebiegów na
    jeden dzień, a podgląd przelicza się po każdym klawiszu. Dwuoptymalizacja
    (odwracanie odcinków, dopóki pętla się skraca) daje ten sam efekt —
    trasa nie krzyżuje samej siebie — za ułamek pracy."""
    kolejnosc = list(przystanki)
    if len(kolejnosc) < 3:
        return kolejnosc
    najkrotsza = km_petli_podgladu(geo, baza_nazwa, kolejnosc)
    for _ in range(6):
        poprawiono = False
        for i in range(len(kolejnosc) - 1):
            for j in range(i + 1, len(kolejnosc)):
                proba = kolejnosc[:i] + kolejnosc[i:j + 1][::-1] + kolejnosc[j + 1:]
                dlugosc = km_petli_podgladu(geo, baza_nazwa, proba)
                if dlugosc < najkrotsza - 0.01:
                    kolejnosc, najkrotsza, poprawiono = proba, dlugosc, True
        if not poprawiono:
            break
    return kolejnosc


def _wolne_minuty_dnia(postoje):
    """Ile minut doby zostaje na jazdę po posiłku i postojach."""
    return (PMT.LIMIT_CZASU_MINUTY - PMT.PRZERWA_JEDZENIE_MIN
            - max(0, int(postoje)) * PMT.POSTOJ_SREDNI_MIN)


def _mnoznik_max_podgladu(km, postoje, stawka, limit_dnia):
    """Do ilu wolno rozciągnąć dzień: godziny doby i sufit kwoty dnia.

    Ten sam rachunek, co _mnoznik_max_dnia w silniku — z tą różnicą, że
    sufit kwoty bierzemy z ustawienia okna, a nie zawsze z MAX_KWOTA_DNIA."""
    wolne = _wolne_minuty_dnia(postoje)
    if wolne <= 0 or km <= 0 or stawka <= 0:
        return PMT.MNOZNIK_MIN
    z_godzin = (wolne / 60.0) * PMT.SREDNIA_PREDKOSC / km
    z_limitu = (float(limit_dnia) / float(stawka)) / km
    return max(PMT.MNOZNIK_MIN, min(z_godzin, z_limitu))


def _przytnij_do_doby(geo, baza_nazwa, przystanki):
    """Zdejmuje ostatnie postoje, dopóki dzień nie mieści się w dobie przy
    realnej drodze (MNOZNIK_MIN) — krok 0 przycinania z silnika."""
    przystanki = list(przystanki)
    while len(przystanki) > MIN_POSTOJOW_DNIA:
        km = km_petli_podgladu(geo, baza_nazwa, przystanki)
        wolne = _wolne_minuty_dnia(len(przystanki))
        if wolne > 0 and km * PMT.MNOZNIK_MIN <= (wolne / 60.0) * PMT.SREDNIA_PREDKOSC:
            break
        przystanki.pop()
    return przystanki


class _DzienDoDokumentu:
    """Atrapa dnia dla PMT._podziel_na_dokumenty — ten sam podział, co w PDF."""
    __slots__ = ("suma", "etapy", "dokument")

    def __init__(self, suma, etapow):
        self.suma = float(suma)
        self.etapy = [None] * max(1, int(etapow))
        self.dokument = 0


def numery_dokumentow(kwoty, etapy):
    """Numer polecenia wyjazdu dla każdego dnia — regułą z generowania PDF-ów.

    Sufit kwoty dokumentu i sufit wierszy strony A4 liczy sam silnik
    (_podziel_na_dokumenty), więc podgląd rozpada się na tyle samo
    dokumentów, ile wyjdzie plików."""
    atrapy = [_DzienDoDokumentu(k, e) for k, e in zip(kwoty, etapy)]
    if not atrapy:
        return []
    try:
        PMT._podziel_na_dokumenty(atrapy)
    except Exception:
        return [1] * len(atrapy)
    return [a.dokument or 1 for a in atrapy]


def _hhmm(minuty):
    minuty = int(min(max(minuty, 0), 23 * 60 + 59))
    return "%02d:%02d" % (minuty // 60, minuty % 60)


def _godziny_podgladu(km, postoje):
    postoj = (PMT.POSTOJ_MIN_MIN + PMT.POSTOJ_MAX_MIN) / 2.0
    jazda = (km / max(1.0, PMT.SREDNIA_PREDKOSC)) * 60.0
    koniec = GODZINA_STARTU + jazda + postoje * postoj + PMT.PRZERWA_JEDZENIE_MIN
    return _hhmm(GODZINA_STARTU), _hhmm(koniec)


def _rozciagnij_dni(plan, cel_km):
    """Mnożnik każdego dnia — dokładnie tak, jak skaluje kilometry silnik.

    Wszystkie dni ruszają tym samym mnożnikiem (kilometry tego samego
    odcinka nie mogą zależeć od dnia), dzień bez godzin zatrzymuje się na
    swoim suficie, a brakujące kilometry dolewamy tam, gdzie zapas został."""
    if not plan:
        return
    suma_km = max(sum(d["km"] for d in plan), 1.0)
    start = max(PMT.MNOZNIK_MIN, cel_km / suma_km)
    for d in plan:
        d["mn"] = max(PMT.MNOZNIK_MIN, min(start, d["max"]))
    for _ in range(24):
        brak = cel_km - sum(d["km"] * d["mn"] for d in plan)
        if brak <= 0.5:
            break
        zapas = [d for d in plan if d["max"] - d["mn"] > 1e-6 and d["km"] > 0]
        if not zapas:
            break
        pojemnosc = sum((d["max"] - d["mn"]) * d["km"] for d in zapas)
        if pojemnosc <= 0:
            break
        udzial = min(1.0, brak / pojemnosc)
        for d in zapas:
            d["mn"] += (d["max"] - d["mn"]) * udzial


def _dosyp_grosze(plan, brak):
    """Grosze brakujące do zamówionej kwoty rozdaje tam, gdzie dzień ma
    jeszcze zapas do swojego sufitu; nadmiar zdejmuje tak samo.

    Kolejność jest stała, więc podgląd tej samej kwoty wychodzi zawsze tak
    samo. Gdy zapasu nie ma — kwota nie mieści się w miesiącu — zostaje
    reszta, której podgląd świadomie NIE dorysowuje."""
    if not plan or not brak:
        return brak
    znak = 1 if brak > 0 else -1
    brak = abs(int(brak))
    for _ in range(8):
        if not brak:
            break
        luz = [(d, (d["sufit_gr"] - d["gr"]) if znak > 0 else (d["gr"] - d["dol_gr"]))
               for d in plan]
        luz = [(d, ile) for d, ile in luz if ile > 0]
        if not luz:
            break
        razem = sum(ile for _d, ile in luz)
        if razem <= brak:
            for d, ile in luz:
                d["gr"] += znak * ile
            brak -= razem
            continue
        rozdane = 0
        for d, ile in luz:
            porcja = int(brak * ile // razem)
            d["gr"] += znak * porcja
            rozdane += porcja
        reszta = brak - rozdane
        for d, ile in luz:
            if reszta <= 0:
                break
            if (d["sufit_gr"] - d["gr"]) if znak > 0 else (d["gr"] - d["dol_gr"]):
                d["gr"] += znak
                reszta -= 1
        brak = reszta
    return znak * brak


def plan_podgladu(kwota, rok, miesiac, tryb, wylaczone, stawka, geo,
                  baza_nazwa, limit_dnia):
    """Dni podglądu jako słowniki — serce podglądu, bez widżetów.

    Zwraca listę {data, przystanki, km, kwota, dokument} ułożoną datami.
    Osobno od podglad_miesiaca, bo tego samego rachunku pilnują testy."""
    kwota = max(0.0, float(kwota or 0.0))
    stawka = float(stawka or 0.0)
    if kwota < PMT.MIN_KWOTA or stawka <= 0 or baza_nazwa not in (geo or {}):
        return []
    wylaczone = set(wylaczone or ())
    kandydaci = [d for d in dni_robocze_realne(rok, miesiac, tryb)
                 if d.day not in wylaczone]
    if not kandydaci:
        return []
    ile = ile_dni_wyjazdowych(kwota, stawka, len(kandydaci), limit_dnia)
    if not ile:
        return []

    baza_lat, baza_lng = geo[baza_nazwa][0], geo[baza_nazwa][1]
    blisko = sum(1 for nazwa, wsp in geo.items()
                 if nazwa != baza_nazwa
                 and PMT.oblicz_dystans(baza_lat, baza_lng, wsp[0], wsp[1])
                 <= PMT.MAX_PROMIEN_PETLI_KM)
    promien = _promien_podgladu(blisko, len(kandydaci))
    miasta = _miasta_podgladu(geo, baza_nazwa, promien)
    if not miasta:
        return []
    karencja = _karencja_podgladu(len(miasta), len(kandydaci))
    max_skok = PMT.max_skok_bazowy(promien)
    rng = random.Random(_ziarno_podgladu(kwota, rok, miesiac, tryb, stawka,
                                         baza_nazwa, wylaczone))

    # dni budowane: plan plus dwa dni zapasu — dokładnie jak w silniku
    budowane = min(len(kandydaci), ile + (ZAPAS_DNI_PODGLADU if ile > 1 else 0))
    wybrane = _rozloz_rownomiernie(kandydaci, budowane)
    kolejnosc = wybrane + [d for d in kandydaci if d not in wybrane]

    cel_km = kwota / stawka
    plan, ostatnie, pojemnosc = [], {}, 0.0
    for numer, data in enumerate(kolejnosc):
        if len(plan) >= budowane and pojemnosc >= cel_km * ZAPAS_KM_PODGLADU:
            break         # dość dni ORAZ pojemności na całą kwotę
        sektor = PMT.SEKTORY_KOLEJNOSC[(numer * 3) % len(PMT.SEKTORY_KOLEJNOSC)]
        if numer % 3 == 0:            # ciasna pętla pod bazą
            pierscien, skok = (15.0, min(45.0, promien)), min(24.0, max_skok)
        elif numer % 3 == 1:          # dojazd w dalszy rejon
            pierscien, skok = (min(45.0, promien * 0.6), promien), max_skok
        else:                         # dzień „po drodze"
            pierscien, skok = (25.0, promien * 0.75), max_skok
        zajete = {nazwa for nazwa, kiedy in ostatnie.items()
                  if (data - kiedy).days < karencja}
        # kilka podejść, jak w silniku: każde nieudane rozluźnia maksymalny
        # skok, bo start trafiony w pustkę nie ma dokąd pojechać
        przystanki = []
        for proba in range(PROB_DNIA_PODGLADU):
            kandydat = _przytnij_do_doby(geo, baza_nazwa, _uporzadkuj_petle(
                geo, baza_nazwa, _petla_podgladu(
                    miasta, sektor, pierscien, skok * (1.0 + proba * 0.15),
                    rng.randint(*CELE_DNIA_PODGLADU), zajete, rng)))
            if len(kandydat) >= MIN_POSTOJOW_DNIA:
                przystanki = kandydat
                break
        if not przystanki:
            continue
        km = km_petli_podgladu(geo, baza_nazwa, przystanki)
        if km <= 1.0:
            continue
        sufit = _mnoznik_max_podgladu(km, len(przystanki), stawka, limit_dnia)
        plan.append({"data": data, "przystanki": przystanki, "km": km,
                     "max": sufit, "mn": PMT.MNOZNIK_MIN})
        pojemnosc += km * sufit
        for nazwa in przystanki:
            ostatnie[nazwa] = data

    if not plan:
        return []

    # za dużo kilometrów na tę kwotę: odpadają najdłuższe dni, a gdy reszta
    # przestałaby kwotę udźwignąć — najdłuższy dzień traci ostatni postój
    while len(plan) > 1 and \
            sum(d["km"] for d in plan) * PMT.MNOZNIK_MIN > cel_km + 0.5:
        najdluzszy = max(plan, key=lambda d: (d["km"], -len(d["przystanki"])))
        moc_reszty = sum(d["km"] * d["max"] for d in plan if d is not najdluzszy)
        if moc_reszty >= cel_km:
            plan.remove(najdluzszy)
            continue
        if len(najdluzszy["przystanki"]) <= MIN_POSTOJOW_DNIA:
            break
        najdluzszy["przystanki"] = najdluzszy["przystanki"][:-1]
        najdluzszy["km"] = km_petli_podgladu(geo, baza_nazwa,
                                             najdluzszy["przystanki"])
        najdluzszy["max"] = _mnoznik_max_podgladu(
            najdluzszy["km"], len(najdluzszy["przystanki"]), stawka, limit_dnia)

    # został jeden dzień i nadal jest za długi: mniej postojów — krok 2
    # przycinania z silnika. Bez tego najmniejsze kwoty wychodziły WYŻSZE
    # od zamówionej, bo krótszej trasy niż jedna pętla już nie ma.
    if len(plan) == 1:
        jedyny = plan[0]
        while (jedyny["km"] * PMT.MNOZNIK_MIN > cel_km + 0.5
               and len(jedyny["przystanki"]) > MIN_POSTOJOW_DNIA):
            jedyny["przystanki"] = jedyny["przystanki"][:-1]
            jedyny["km"] = km_petli_podgladu(geo, baza_nazwa, jedyny["przystanki"])
        if (jedyny["km"] * PMT.MNOZNIK_MIN > cel_km + 0.5
                and len(miasta) >= MIN_POSTOJOW_DNIA):
            # najkrótsza pętla, jaka w ogóle istnieje: dwie najbliższe
            # miejscowości (miasta są ułożone odległością od bazy)
            najblizsze = [m[0] for m in miasta[:MIN_POSTOJOW_DNIA]]
            krocej = km_petli_podgladu(geo, baza_nazwa, najblizsze)
            if 0 < krocej < jedyny["km"]:
                jedyny["przystanki"], jedyny["km"] = najblizsze, krocej
        jedyny["max"] = _mnoznik_max_podgladu(
            jedyny["km"], len(jedyny["przystanki"]), stawka, limit_dnia)

    _rozciagnij_dni(plan, cel_km)

    # kwoty w groszach: dzień nie przekracza swojego sufitu ani nie schodzi
    # poniżej realnej drogi, a suma dobija co do grosza do zamówionej kwoty
    for d in plan:
        d["dol_gr"] = int(math.ceil(d["km"] * PMT.MNOZNIK_MIN * stawka * 100 - 1e-6))
        d["sufit_gr"] = int(math.floor(d["km"] * d["max"] * stawka * 100 + 1e-6))
        if d["sufit_gr"] < d["dol_gr"]:
            d["sufit_gr"] = d["dol_gr"]
        d["gr"] = min(max(int(round(d["km"] * d["mn"] * stawka * 100)),
                          d["dol_gr"]), d["sufit_gr"])
    _dosyp_grosze(plan, int(round(kwota * 100)) - sum(d["gr"] for d in plan))

    plan.sort(key=lambda d: d["data"])
    numery = numery_dokumentow([d["gr"] / 100.0 for d in plan],
                               [len(d["przystanki"]) + 1 for d in plan])
    wynik = []
    for d, nr in zip(plan, numery):
        kwota_dnia = d["gr"] / 100.0
        wynik.append({"data": d["data"], "przystanki": list(d["przystanki"]),
                      "km": kwota_dnia / stawka, "kwota": kwota_dnia,
                      "dokument": int(nr)})
    return wynik


def podglad_miesiaca(kwota, rok, miesiac, tryb, wylaczone, stawka, geo,
                     baza_nazwa, limit_dnia):
    """SZACUNEK miesiąca przed generowaniem — obiekty dla widżetów.

    Liczba dni, kwoty, kilometry i numery dokumentów wychodzą z reguł
    silnika (plan_podgladu); trasy są poglądowe. Prawdziwy rozkład powstaje
    w generuj_trasy i wchodzi tu przez dni_widzetow_z_tras()."""
    ile_w_miesiacu = PMT.calendar.monthrange(rok, miesiac)[1]
    wylaczone = set(wylaczone or ())
    wszystkie = {}
    for numer in range(1, ile_w_miesiacu + 1):
        dzien = D.Dzien(datetime.date(rok, miesiac, numer), wolny=True)
        dzien.wylaczony = numer in wylaczone
        wszystkie[numer] = dzien
    lista = [wszystkie[n] for n in range(1, ile_w_miesiacu + 1)]

    for wpis in plan_podgladu(kwota, rok, miesiac, tryb, wylaczone, stawka,
                              geo, baza_nazwa, limit_dnia):
        dzien = wszystkie.get(wpis["data"].day)
        if dzien is None:
            continue
        dzien.wolny = False
        dzien.przystanki = wpis["przystanki"]
        dzien.km = round(wpis["km"], 1)
        dzien.kwota = round(wpis["kwota"], 2)
        dzien.dokument = wpis["dokument"]
        dzien.start, dzien.koniec = _godziny_podgladu(dzien.km, dzien.postoje)
    return lista


def min_kwota_wyjazdu(geo, baza_nazwa, stawka=None):
    """Najtańszy PRAWDZIWY wyjazd z tej bazy — dolna granica kwoty.

    Najkrótsza możliwa pętla to baza → dwie najbliższe miejscowości → baza,
    a każdy odcinek ma fizyczną podłogę: linia prosta × PMT.MNOZNIK_MIN.
    Poniżej tej kwoty program nie narysuje przejazdu, który dałoby się odbyć —
    w rejonach o rzadkiej siatce miast (góry, wybrzeże) wychodzi z tego nawet
    kilkaset złotych. Zwraca 0.0, gdy nie ma z czego policzyć."""
    stawka = float(stawka or PMT.STAWKA_ZA_KM)
    if not geo or baza_nazwa not in geo or stawka <= 0:
        return 0.0
    b_lat, b_lng = geo[baza_nazwa]
    inne = sorted(((PMT.oblicz_dystans(b_lat, b_lng, la, lg), n, la, lg)
                   for n, (la, lg) in geo.items() if n != baza_nazwa),
                  key=lambda x: (x[0], x[1]))
    inne = [x for x in inne if x[0] > 3.0][:8]
    if not inne:
        return 0.0
    if len(inne) == 1:
        linia = 2.0 * inne[0][0]
    else:
        linia = min(
            a[0] + PMT.oblicz_dystans(a[2], a[3], b[2], b[3]) + b[0]
            for i, a in enumerate(inne) for b in inne[i + 1:])
    # Odcinek liczy się drogą, nie w linii prostej — nawet bez sieci program
    # bierze linię prostą × krętość dróg. To wciąż DOLNA granica: silnik
    # zwykle wychodzi wyżej, bo nie zawsze może wziąć dwie najbliższe
    # miejscowości. Dokładną liczbę podaje dopiero po wygenerowaniu.
    return round(linia * max(PMT.MNOZNIK_MIN, PMT.TEST_MNOZNIK_TRASY) * stawka, 2)


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
        dzien.etapy = etapy_widzetu(dzien_trasy)
    return [wszystkie[n] for n in range(1, ile_w_miesiacu + 1)]


def etapy_widzetu(dzien_trasy, stan_zrodla=None):
    """Odcinki dnia na odwrót kartki delegacji — z PRAWDZIWEGO wyniku silnika.

    Każdy odcinek: skąd, dokąd, godziny z dokumentu (Etap), kilometry
    (dystans_rzeczywisty), linia prosta (RawEtap.linia_prosta, None gdy
    silnik jej nie zapamiętał) i źródło kilometrów (RawEtap.zrodlo). Odcinek
    bez własnego źródła bierze stan całego rozliczenia
    (stan_zrodla_odleglosci) — to samo, co stoi na dokumencie; a gdy i ten
    milczy (ZRODLO_BRAK), źródło zostaje puste."""
    surowe = list(getattr(dzien_trasy, "etapy_surowe", None) or [])
    godziny = list(getattr(dzien_trasy, "etapy", None) or [])
    if not surowe:
        return []
    zapas = ""
    try:
        stan = stan_zrodla if stan_zrodla is not None else PMT.stan_zrodla_odleglosci()
        if stan.get("stan") in (PMT.ZRODLO_DROGI, PMT.ZRODLO_PAMIEC, PMT.ZRODLO_SZACUNEK):
            zapas = str(stan["stan"])
    except Exception:
        zapas = ""
    wynik = []
    suma_km = 0.0
    for i, etap in enumerate(surowe):
        godz = godziny[i] if i < len(godziny) else None
        try:
            km = float(getattr(etap, "dystans_rzeczywisty", etap.d_line) or 0.0)
        except (TypeError, ValueError):
            km = 0.0
        try:
            prosta = float(getattr(etap, "linia_prosta", 0.0) or 0.0)
        except (TypeError, ValueError):
            prosta = 0.0
        suma_km += km
        wynik.append({
            "z": str(etap.skad or ""), "do": str(etap.dokad or ""),
            "wyj": str(getattr(godz, "godz_wyj", "") or ""),
            "przyj": str(getattr(godz, "godz_przyj", "") or ""),
            "km": round(km, 1),
            "prosta": round(prosta, 1) if prosta > 0 else None,
            "zrodlo": str(getattr(etap, "zrodlo", "") or zapas),
        })
    # domknięcie sumy jak w odcinki_dnia: odcinki zaokrąglone do 0,1 km mają
    # sumować się DOKŁADNIE do kilometrów dnia z przodu kartki (round(suma, 1)),
    # więc ostatni odcinek bierze resztę zaokrągleń
    if wynik:
        wynik[-1]["km"] = round(round(suma_km, 1) - sum(e["km"] for e in wynik[:-1]), 1)
    return wynik


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
#  MIESIĄCE OSOBY: HISTORIA + FOLDERY NA DYSKU
#  Z tego żyją trzy rzeczy: kropka na zakładce nierozliczonego miesiąca,
#  kratka roku na ekranie startowym i pasek miesięcy na tacy.
# ═══════════════════════════════════════════════════════════════════════

def miesiace_z_dysku(imie, katalog=None):
    """{(rok, miesiąc): folder} — komplety TEJ osoby w folderze wyników.

    Tylko foldery generatora („Rozliczenie_Imię_Nazwisko_miesiąc_RRRRr",
    rozbierane przez PMT._rozbierz_folder_wyniku) z choć jednym plikiem PDF
    programu. Dwa foldery tego samego miesiąca — wygrywa świeższy."""
    imie = " ".join(str(imie or "").split())
    if not imie:
        return {}
    katalog = katalog or PMT.sciezka_pulpitu()
    try:
        nazwy = os.listdir(katalog)
    except OSError:
        return {}
    cel = PMT._nazwa_porownawcza(PMT.nazwa_do_pliku(imie).replace("_", " "))
    wynik = {}
    czasy = {}
    for nazwa in nazwy:
        kto, miesiac, rok = PMT._rozbierz_folder_wyniku(nazwa)
        if not kto or PMT._nazwa_porownawcza(kto) != cel:
            continue
        folder = os.path.join(katalog, nazwa)
        if not dokumenty_w_wyniku(folder):
            continue
        try:
            czas = os.path.getmtime(folder)
        except OSError:
            czas = 0.0
        klucz = (int(rok), int(miesiac))
        if klucz in wynik and czasy[klucz] >= czas:
            continue
        wynik[klucz] = folder
        czasy[klucz] = czas
    return wynik


def stan_miesiaca(klucz, miesiace, biezacy):
    """„dokumenty" / „pusty" / „przyszly" — JEDNA reguła dla kropki na
    zakładce, kratki roku i tacy. ``miesiace`` to historia_okna(): miesiąc
    z kluczem ma wpis albo folder, czyli COKOLWIEK — liczby, bez kropki."""
    klucz = (int(klucz[0]), int(klucz[1]))
    if klucz in miesiace:
        return "dokumenty"
    return "przyszly" if klucz > tuple(biezacy) else "pusty"


def miesiac_nierozliczony(klucz, miesiace, biezacy):
    """Miesiąc już minął, a nie ma dla niego ANI wpisu w historii, ANI
    folderu z dokumentami — kropka. Bieżący i przyszłe nigdy jej nie mają."""
    klucz = (int(klucz[0]), int(klucz[1]))
    return klucz < tuple(biezacy) and klucz not in miesiace


def historia_okna(imie, pesel, katalog=None):
    """Miesiące osoby: {(rok, miesiąc): {...}} jak PMT.historia_miesiecy,
    dołożone o foldery leżące na dysku.

    Wpis historii daje liczby (kwota co do grosza, km, dni, dokumenty).
    Folder z dysku bez wpisu (PDF-y, których nie dało się odczytać) daje
    miesiąc z dokumentami, ale bez liczb — pola liczb są wtedy None, nigdy
    zero. Gdy folder z wpisu zniknął, a inny folder tego miesiąca leży na
    dysku, „folder" wskazuje ten z dysku."""
    wynik = {}
    if imie and pesel:
        try:
            wynik = {k: dict(v) for k, v in PMT.historia_miesiecy(imie, pesel).items()}
        except Exception as blad:
            PMT.log_error(blad)
            wynik = {}
    for klucz, folder in miesiace_z_dysku(imie, katalog).items():
        wpis = wynik.get(klucz)
        if wpis is None:
            wynik[klucz] = {"kwota": None, "km": None, "dni": None, "dni_daty": [],
                            "dokumenty": None, "folder": folder, "istnieje": True,
                            "data": "", "podpisany": False, "wyslany": False,
                            "zrodlo": "", "miejsca": {}}
        elif not wpis.get("istnieje"):
            wpis["folder"], wpis["istnieje"] = folder, True
    return wynik


def dni_z_folderu(folder, rok, miesiac):
    """Kartki tacy dla miesiąca Z DYSKU: dni z tabel przejazdów gotowych
    PDF-ów (pmt_dokumenty.dni_kompletu) przetłumaczone na proto_dane.Dzien
    całego miesiąca — jak dni_widzetow_z_tras, tylko bez silnika."""
    rok, miesiac = int(rok), int(miesiac)
    ile_w_miesiacu = PMT.calendar.monthrange(rok, miesiac)[1]
    wszystkie = {numer: D.Dzien(datetime.date(rok, miesiac, numer), wolny=True)
                 for numer in range(1, ile_w_miesiacu + 1)}
    for wpis in DOK.dni_kompletu(folder):
        try:
            data = datetime.date.fromisoformat(wpis["data"])
        except (TypeError, ValueError):
            continue
        dzien = wszystkie.get(data.day) if (data.year, data.month) == (rok, miesiac) else None
        if dzien is None:
            continue
        dzien.wolny = False
        dzien.przystanki = list(wpis.get("przystanki") or [])
        dzien.km = round(float(wpis.get("km") or 0.0), 1)
        dzien.kwota = round(float(wpis.get("kwota") or 0.0), 2)
        dzien.dokument = int(wpis.get("dokument") or 0)
        if wpis.get("start"):
            dzien.start = wpis["start"]
        if wpis.get("koniec"):
            dzien.koniec = wpis["koniec"]
    return [wszystkie[n] for n in range(1, ile_w_miesiacu + 1)]


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


# „(Dzień 3/7)" i „(12/40)" — liczby biorą się z ostatniego nawiasu
_ULAMEK_ETAPU = re.compile(r"(\d+)\s*/\s*(\d+)\s*\)")


def postep_etapu(opis):
    """Para (ile, z ilu) z meldunku silnika — np. „(Dzień 3/7)" → (3, 7).

    Silnik sam liczy, przy którym dniu i przy którym pliku stoi. Taśma
    bierze te liczby wprost od niego, zamiast zgadywać rytm z zegara.
    """
    m = _ULAMEK_ETAPU.search(str(opis or ""))
    if m is None:
        return None
    ile, z_ilu = int(m.group(1)), int(m.group(2))
    if z_ilu <= 0:
        return None
    return min(ile, z_ilu), z_ilu


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

    # Okno może wpiąć się tu na chwilę PRZED schowaniem panelu — tyle
    # wystarczy, żeby zdjąć z niego obraz i pokazać, jak wsiąka w ikonę.
    przed_zamknieciem = None

    def zamknij(self):
        if self.isVisible():
            hak = self.przed_zamknieciem
            if hak is not None:
                try:
                    hak()
                except Exception:
                    pass
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


class WyrastaniePanelu(QWidget):
    """Panel wyrasta z klikniętej ikony na szynie i tam wraca.

    Żeby wyrastanie kosztowało jedną klatkę, a nie przebudowę całego
    panelu dwadzieścia razy na sekundę, panel jest raz przerysowywany do
    pixmapy, a potem już tylko skalowany. Widżet leży NAD ramą panelu:
    kiedy dobiega do końca, gaśnie i spod niego wychodzi prawdziwy panel,
    który stał tam przez cały czas — dlatego nic nie mruga.
    """

    skonczone = pyqtSignal()

    CZAS_WEJSCIA = 280            # ms — panel wychodzi z ikony
    CZAS_WYJSCIA = 210            # ...i wraca do niej szybciej
    ZASLONA = 246                 # tyle kryje tło ramy panelu (NakladkaDzialu)

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._obraz = None
        self._skad = QRectF()
        self._dokad = QRectF()
        self._wstecz = False
        self._ruch = S.Plynnie(0.0, czas=self.CZAS_WEJSCIA, krzywa="wyjscie",
                               rodzic=self, przy_zmianie=self.update, klatka=16)
        self._ruch.koniec.connect(self._koniec)
        self.hide()

    def gra(self):
        return self.isVisible() and not self._ruch.gotowe()

    def zacznij(self, obraz, skad, dokad, wstecz=False):
        """``skad`` to pole ikony na szynie, ``dokad`` — pole gotowego panelu."""
        self._obraz = obraz
        self._skad = QRectF(skad)
        self._dokad = QRectF(dokad)
        self._wstecz = bool(wstecz)
        self._ruch.ustaw_czas(self.CZAS_WYJSCIA if wstecz else self.CZAS_WEJSCIA)
        self._ruch.zatrzymaj()
        self._ruch.ustaw(0.0)
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self._ruch.do(1.0)

    def przerwij(self):
        self._ruch.zatrzymaj()
        self._obraz = None
        self.hide()

    def _koniec(self):
        self._obraz = None
        self.hide()
        self.skonczone.emit()

    @staticmethod
    def _miedzy(a, b, t):
        return QRectF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t,
                      a.width() + (b.width() - a.width()) * t,
                      a.height() + (b.height() - a.height()) * t)

    def paintEvent(self, _zdarzenie):
        if self._obraz is None:
            return
        t = max(0.0, min(1.0, self._ruch.teraz()))
        widok = 1.0 - t if self._wstecz else t
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # zasłona kładzie się TYLKO tam, gdzie stanie panel: szyna i pasek
        # górny zostają jasne, bo one nigdzie nie znikają
        p.fillRect(self._dokad, QColor(5, 10, 20, int(self.ZASLONA * widok)))
        pole = self._miedzy(self._skad, self._dokad, widok)
        promien = 6.0 + 12.0 * widok
        obrys = QPainterPath()
        obrys.addRoundedRect(pole, promien, promien)
        p.save()
        p.setClipPath(obrys)
        p.setOpacity(0.10 + 0.90 * widok)
        p.drawPixmap(pole, self._obraz, QRectF(self._obraz.rect()))
        p.setOpacity(1.0)
        # światło przechodzące po szkle — jeden przejazd na całe wyrastanie
        self._polysk(p, pole, widok)
        p.restore()
        p.setPen(QPen(S.z_alfa(S.CYJAN, int(40 + 90 * (1.0 - widok))), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(obrys)
        p.end()

    def _polysk(self, p, pole, t):
        """Pasmo światła przejeżdżające po szkle dokładnie raz."""
        if t <= 0.02 or t >= 0.98 or pole.width() < 8.0:
            return
        szer = pole.width() * 0.42
        x = pole.left() - szer + (pole.width() + szer * 2.0) * t
        g = QLinearGradient(QPointF(x - szer * 0.5, pole.top()),
                            QPointF(x + szer * 0.5, pole.bottom()))
        moc = int(46 * math.sin(t * math.pi))
        g.setColorAt(0.0, S.z_alfa(QColor(255, 255, 255), 0))
        g.setColorAt(0.5, S.z_alfa(QColor(210, 240, 255), moc))
        g.setColorAt(1.0, S.z_alfa(QColor(255, 255, 255), 0))
        p.fillRect(pole, QBrush(g))


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
    """Powierzchnia nowego systemu: szkło, krawędź światła, obrys.

    Szkło (gradienty, krawędzie światła, obrys) rysuje się raz na rozmiar
    i zostaje w pixmapie — klatka ekranu startowego to trzy położenia
    obrazu, nie trzy karty malowane od nowa (szkło szerokiej karty to
    ponad milisekunda na klatkę)."""

    def __init__(self, rodzic=None, promien=S.PROMIEN, mocne=False):
        super().__init__(rodzic)
        self._promien = float(promien)
        self._mocne = bool(mocne)
        self._pix = None
        self._klucz_pix = None

    def _pixmapa(self):
        dpr = self.devicePixelRatioF()
        klucz = (self.width(), self.height(), round(dpr, 2))
        if self._pix is not None and self._klucz_pix == klucz:
            return self._pix
        pix = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        malarz = QPainter(pix)
        malarz.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pole = QRectF(0, 0, self.width(), self.height()).adjusted(0.5, 0.5, -0.5, -0.5)
        if pole.width() > 4 and pole.height() > 4:
            S.szklo(malarz, pole, self._promien, mocne=self._mocne,
                    sila_krawedzi=1.6)
        malarz.end()
        self._pix, self._klucz_pix = pix, klucz
        return pix

    def resizeEvent(self, zdarzenie):
        self._pix = None
        super().resizeEvent(zdarzenie)

    def paintEvent(self, _zdarzenie):
        malarz = QPainter(self)
        malarz.drawPixmap(0, 0, self._pixmapa())
        malarz.end()


class KratkaRoku(QWidget):
    """Dwanaście pól roku — po jednym na miesiąc — z historii rozliczeń.

    W polu trzy liczby: kwota co do grosza, kilometry, dni w trasie.
    Miesiąc z dokumentami świeci (szkło, cyjan i mięta), bez dokumentów
    stoi wygaszony (a gdy już minął — z kropką ostrzeżenia, tą samą co na
    zakładce paska), przyszły jest ledwo widoczny; bieżący ma obwódkę.
    Strzałki przełączają rok, kliknięcie pola melduje miesiąc (okno
    przestawia na niego cały program). Na dole sumy roku.

    Obraz kratki jest buforowany: klatka ekranu startowego to jedno
    położenie pixmapy, a nie dwanaście kart ze szkła."""

    wybrano_miesiac = pyqtSignal(int, int)
    zmieniono_rok = pyqtSignal(int)

    KOLUMNY, WIERSZE = 6, 2
    ODSTEP = 8.0
    NAGLOWEK = 24.0            # rząd ze strzałkami i rokiem
    STOPKA = 22.0              # rząd z sumami roku
    PRZERWA = 6.0
    POLE_MIN, POLE_WZOR, POLE_MAKS = 58.0, 78.0, 92.0    # 58: trzy wiersze liczb jeszcze się mieszczą
    PROMIEN_POLA = 12.0
    STRZALKA = 26.0

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._rok = datetime.date.today().year
        self._miesiace = {}
        self._biezacy = miesiac_biezacy()
        self._wersja = 0
        self._pod = None            # ("pole", (rok, miesiąc)) / ("wstecz",) / ("dalej",)
        self._pix = None
        self._klucz_pix = None
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # ── dane ──────────────────────────────────────────────────────
    def ustaw_dane(self, miesiace, biezacy=None, rok=None):
        """miesiace: {(rok, miesiąc): {...}} z historia_okna()."""
        self._miesiace = dict(miesiace or {})
        if biezacy:
            self._biezacy = (int(biezacy[0]), int(biezacy[1]))
        if rok:
            self._rok = int(rok)
        self._wersja += 1
        self.update()

    def ustaw_rok(self, rok):
        rok = int(rok)
        if rok == self._rok:
            return
        self._rok = rok
        self.update()
        self.zmieniono_rok.emit(rok)

    def rok(self):
        return self._rok

    def miesiac(self, numer):
        return self._miesiace.get((self._rok, int(numer)))

    def stan_miesiaca(self, klucz):
        """„dokumenty" / „pusty" / „przyszly" — regułą wspólną z zakładkami."""
        return stan_miesiaca(klucz, self._miesiace, self._biezacy)

    def nierozliczony(self, klucz):
        """Miesiąc już minął, a nie ma ani wpisu, ani folderu — kropka."""
        return miesiac_nierozliczony(klucz, self._miesiace, self._biezacy)

    def sumy_roku(self, rok=None):
        """(kwota, km, dni, miesiące z liczbami) — sumy pól z liczbami."""
        rok = int(rok or self._rok)
        kwota, km, dni, ile = 0.0, 0, 0, 0
        for (r, _m), wpis in self._miesiace.items():
            if r != rok or wpis.get("kwota") is None:
                continue
            kwota += float(wpis.get("kwota") or 0.0)
            km += int(wpis.get("km") or 0)
            dni += int(wpis.get("dni") or 0)
            ile += 1
        return round(kwota, 2), km, dni, ile

    # ── miary ─────────────────────────────────────────────────────
    @classmethod
    def wysokosc_dla(cls, pole):
        return (pole * cls.WIERSZE + cls.ODSTEP * (cls.WIERSZE - 1)
                + cls.NAGLOWEK + cls.STOPKA + 2 * cls.PRZERWA)

    def sizeHint(self):
        return QSize(720, int(self.wysokosc_dla(self.POLE_WZOR)))

    def minimumSizeHint(self):
        return QSize(420, int(self.wysokosc_dla(self.POLE_MIN)))

    def _pola(self):
        """Prostokąty strzałek i dwunastu pól — liczone z rozmiaru."""
        szer, wys = float(self.width()), float(self.height())
        pola = {}
        rok = str(self._rok)
        szer_roku = OK._szerokosc(rok, 13, 700, mono=True)
        pola["wstecz"] = QRectF(0.0, 0.0, self.STRZALKA, self.NAGLOWEK)
        pola["rok"] = QRectF(self.STRZALKA + 4.0, 0.0, szer_roku + 8.0, self.NAGLOWEK)
        pola["dalej"] = QRectF(pola["rok"].right() + 4.0, 0.0, self.STRZALKA, self.NAGLOWEK)
        y0 = self.NAGLOWEK + self.PRZERWA
        wys_pol = max(1.0, wys - y0 - self.PRZERWA - self.STOPKA)
        pole_h = (wys_pol - self.ODSTEP * (self.WIERSZE - 1)) / self.WIERSZE
        pole_w = (szer - self.ODSTEP * (self.KOLUMNY - 1)) / self.KOLUMNY
        lista = []
        for numer in range(12):
            kol, wiersz = numer % self.KOLUMNY, numer // self.KOLUMNY
            lista.append(((self._rok, numer + 1),
                          QRectF(kol * (pole_w + self.ODSTEP), y0 + wiersz * (pole_h + self.ODSTEP),
                                 pole_w, pole_h)))
        pola["pola"] = lista
        pola["stopka"] = QRectF(0.0, wys - self.STOPKA, szer, self.STOPKA)
        return pola

    def _trafienie(self, punkt):
        pola = self._pola()
        for nazwa in ("wstecz", "dalej"):
            if pola[nazwa].contains(punkt):
                return (nazwa,)
        for klucz, pole in pola["pola"]:
            if pole.contains(punkt):
                return ("pole", klucz)
        return None

    # ── zdarzenia ─────────────────────────────────────────────────
    def mousePressEvent(self, zdarzenie):
        if zdarzenie.button() == Qt.MouseButton.LeftButton:
            trafione = self._trafienie(zdarzenie.position())
            if trafione == ("wstecz",):
                self.ustaw_rok(self._rok - 1)
            elif trafione == ("dalej",):
                self.ustaw_rok(self._rok + 1)
            elif trafione is not None:
                self.wybrano_miesiac.emit(trafione[1][0], trafione[1][1])
        super().mousePressEvent(zdarzenie)

    def mouseMoveEvent(self, zdarzenie):
        trafione = self._trafienie(zdarzenie.position())
        if trafione != self._pod:
            self._pod = trafione
            self.setCursor(Qt.CursorShape.PointingHandCursor if trafione
                           else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(zdarzenie)

    def leaveEvent(self, zdarzenie):
        self._pod = None
        self.update()
        super().leaveEvent(zdarzenie)

    def resizeEvent(self, zdarzenie):
        self._pix = None
        super().resizeEvent(zdarzenie)

    # ── rysowanie ─────────────────────────────────────────────────
    @staticmethod
    def _kwota_txt(kwota):
        return "%s zł" % D.zl(float(kwota))

    @staticmethod
    def _km_txt(km):
        return "%s km" % f"{float(km):,.0f}".replace(",", " ")

    def _rysuj_strzalke(self, p, pole, w_prawo, kolor):
        c = pole.center()
        pioro = QPen(kolor, 1.6)
        pioro.setCapStyle(Qt.PenCapStyle.RoundCap)
        pioro.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pioro)
        p.setBrush(Qt.BrushStyle.NoBrush)
        dx = 2.6 if w_prawo else -2.6
        sciezka = QPainterPath()
        sciezka.moveTo(c.x() - dx, c.y() - 4.6)
        sciezka.lineTo(c.x() + dx, c.y())
        sciezka.lineTo(c.x() - dx, c.y() + 4.6)
        p.drawPath(sciezka)

    def _rysuj_pole(self, p, klucz, r):
        stan = self.stan_miesiaca(klucz)
        wpis = self._miesiace.get(klucz) or {}
        sciezka = QPainterPath()
        sciezka.addRoundedRect(r, self.PROMIEN_POLA, self.PROMIEN_POLA)
        if stan == "dokumenty":
            S.szklo(p, r, self.PROMIEN_POLA, mocne=True, sila_krawedzi=1.2, refleks=False)
            # krawędź światła u góry: cyjan przechodzący w miętę
            g = QLinearGradient(QPointF(r.x(), r.y()), QPointF(r.right(), r.y()))
            g.setColorAt(0.00, S.z_alfa(S.CYJAN, 0))
            g.setColorAt(0.20, S.z_alfa(S.CYJAN, 150))
            g.setColorAt(0.80, S.z_alfa(S.MIETA, 150))
            g.setColorAt(1.00, S.z_alfa(S.MIETA, 0))
            p.fillRect(QRectF(r.x() + 8.0, r.y() + 0.6, r.width() - 16.0, 1.4), QBrush(g))
            kolor_etykiety = S.TEKST_2
        elif stan == "przyszly":
            p.fillPath(sciezka, S.z_alfa(S.POWIERZCHNIA_CIEMNA, 60))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(S.z_alfa(S.OBRYS, 70), 1.0))
            p.drawPath(sciezka)
            kolor_etykiety = S.z_alfa(S.TEKST_3, 110)
        else:
            p.fillPath(sciezka, S.z_alfa(S.POWIERZCHNIA_CIEMNA, 160))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(S.OBRYS, 1.0))
            p.drawPath(sciezka)
            kolor_etykiety = S.TEKST_3
        if klucz == self._biezacy:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(S.z_alfa(S.CYJAN, 120), 1.2))
            p.drawPath(sciezka)
            if stan != "dokumenty":
                kolor_etykiety = S.TEKST_2

        duze = r.height() >= 68.0
        lewy = r.x() + 10.0
        rozm_etykiety = 11.5 if duze else 10.5
        S.tekst(p, lewy, r.y() + 8.0 + rozm_etykiety, PMT.MIESIACE_PL[klucz[1] - 1],
                kolor_etykiety, rozm_etykiety, 600)
        if self.nierozliczony(klucz):
            srodek = QPointF(r.right() - 9.0, r.y() + 9.0)
            S.punkt_swiatla(p, srodek, 8.0, S.BURSZTYN, 110)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(S.BURSZTYN))
            p.drawEllipse(srodek, 2.8, 2.8)
        if stan != "dokumenty" or wpis.get("kwota") is None:
            return
        rozm_kwoty = 15.0 if duze else 13.0
        rozm_linii = 10.5 if duze else 9.5
        y_kwoty = r.y() + 8.0 + rozm_etykiety + 7.0 + rozm_kwoty
        # kilometry i dni tuż pod kwotą — jedna grupa liczb, nie dwa brzegi pola
        y_linii = min(r.bottom() - 8.0, y_kwoty + 7.0 + rozm_linii)
        if y_linii - y_kwoty < rozm_linii + 2.0:
            y_kwoty = y_linii - rozm_linii - 2.0
        S.tekst(p, lewy, y_kwoty, self._kwota_txt(wpis["kwota"]), S.MIETA,
                rozm_kwoty, 700, mono=True, poswiata=0.5)
        linia = "%s · %s" % (self._km_txt(wpis.get("km") or 0),
                             OK._dni_txt(int(wpis.get("dni") or 0)))
        S.tekst(p, lewy, y_linii, linia, S.TEKST_2, rozm_linii, 600, mono=True)

    def _rysuj(self, p):
        pola = self._pola()
        self._rysuj_strzalke(p, pola["wstecz"], False, S.TEKST_2)
        S.tekst(p, pola["rok"].x() + 4.0, pola["rok"].center().y() + 5.0, str(self._rok),
                S.TEKST, 13, 700, mono=True)
        self._rysuj_strzalke(p, pola["dalej"], True, S.TEKST_2)
        for klucz, pole in pola["pola"]:
            self._rysuj_pole(p, klucz, pole)
        # sumy roku, od prawej: dni · km · kwota
        kwota, km, dni, ile = self.sumy_roku()
        stopka = pola["stopka"]
        y = stopka.center().y() + 5.0
        x = stopka.right()
        for napis, kolor, rozm, waga, poswiata in (
                (OK._dni_txt(dni), S.TEKST_2, 12, 600, 0.0),
                (" · ", S.TEKST_3, 12, 600, 0.0),
                (self._km_txt(km), S.TEKST_2, 12, 600, 0.0),
                (" · ", S.TEKST_3, 12, 600, 0.0),
                (self._kwota_txt(kwota), S.MIETA, 13, 700, 0.5)):
            x -= OK._szerokosc(napis, rozm, waga, mono=True)
            S.tekst(p, x, y, napis, kolor, rozm, waga, mono=True, poswiata=poswiata)
        if ile:
            napis = "%d z 12" % ile
            S.tekst(p, stopka.x(), y, napis, S.TEKST_3, 11.5, 600, mono=True)

    def _pixmapa(self):
        dpr = self.devicePixelRatioF()
        klucz = (self.width(), self.height(), round(dpr, 2), self._rok, self._wersja,
                 self._biezacy)
        if self._pix is not None and self._klucz_pix == klucz:
            return self._pix
        pix = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self._rysuj(p)
        p.end()
        self._pix, self._klucz_pix = pix, klucz
        return pix

    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.drawPixmap(0, 0, self._pixmapa())
        if self._pod is not None:
            pola = self._pola()
            if self._pod[0] == "pole":
                for klucz, pole in pola["pola"]:
                    if klucz == self._pod[1]:
                        sciezka = QPainterPath()
                        sciezka.addRoundedRect(pole, self.PROMIEN_POLA, self.PROMIEN_POLA)
                        p.fillPath(sciezka, QColor(255, 255, 255, 12))
                        break
            else:
                self._rysuj_strzalke(p, pola[self._pod[0]], self._pod[0] == "dalej", S.TEKST)
        p.end()


class EkranStartowy(QWidget):
    """Ekran startowy: dzisiejsza data, dzisiejsza trasa, kratka roku,
    liczby miesiąca, skrót do bilansu i do mapy tras. Zbudowany z części
    nowego systemu."""

    MAKS_PRZYSTANKOW = 5
    MAKS_PRZYSTANKOW_CIASNO = 3      # w niskim oknie kratka roku musi się zmieścić
    MAKS_SZEROKOSC = 1000
    PROG_CIASNY = 600                # wysokość ekranu, poniżej której układ się zagęszcza

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

        # ── kratka roku ───────────────────────────────────────────
        self.karta_roku = KartaStanu(self, S.PROMIEN)
        kr = QVBoxLayout(self.karta_roku)
        kr.setContentsMargins(18, 12, 18, 12)
        self.kratka = KratkaRoku(self.karta_roku)
        self.kratka.wybrano_miesiac.connect(self._klik_miesiaca)
        kr.addWidget(self.kratka)
        self.karta_roku.setMaximumHeight(int(KratkaRoku.wysokosc_dla(KratkaRoku.POLE_MAKS)) + 24)
        z.addWidget(self.karta_roku, 3)

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
        self._ciasno = None
        self._uloz_ciasno(False)

    # ── układ: w niskim oknie wszystko ma się zmieścić bez przewijania ─
    def _uloz_ciasno(self, ciasno):
        ciasno = bool(ciasno)
        if ciasno == self._ciasno:
            return
        self._ciasno = ciasno
        self.layout().setSpacing(8 if ciasno else 16)
        # karta dnia rośnie z przystankami sama — w ciasnym oknie startuje niżej
        self.karta_dnia.setMinimumHeight(120 if ciasno else 172)
        kl = self.karta_liczb.layout()
        kl.setContentsMargins(24, 8 if ciasno else 14, 24, 8 if ciasno else 14)
        self.karta_liczb.setMinimumHeight(80 if ciasno else 92)

    def _maks_przystankow(self):
        return self.MAKS_PRZYSTANKOW_CIASNO if self._ciasno else self.MAKS_PRZYSTANKOW

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
            maks = self._maks_przystankow()
            for wizyta in dzien.wizyty[:maks]:
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
            reszta = len(dzien.wizyty) - maks
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
        self.odswiez_kratke()
        self.odswiez_mape()

    def odswiez_kratke(self):
        """Kratka roku z miesięcy osoby (historia + foldery), rok z paska."""
        try:
            miesiace = self._okno._miesiace_historii()
        except Exception:
            miesiace = {}
        self.kratka.ustaw_dane(miesiace, miesiac_biezacy(), rok=self._okno.rok)

    def _klik_miesiaca(self, rok, miesiac):
        """Pole kratki przestawia cały program na ten miesiąc."""
        self._okno.przejdz_do_miesiaca(rok, miesiac)

    def odswiez_mape(self):
        """Stan przycisku mapy — bez pliku przycisk stoi i mówi „brak”."""
        sciezka = self._okno.sciezka_mapy_tras()
        self.b_mapa.setEnabled(bool(sciezka))
        self.b_mapa.setText("Mapa tras" if sciezka else "Mapa tras · brak")
        self.l_folder.setText(os.path.basename(os.path.dirname(sciezka))
                              if sciezka else "")

    def resizeEvent(self, zdarzenie):
        super().resizeEvent(zdarzenie)
        bylo = self._ciasno
        self._uloz_ciasno(self.height() < self.PROG_CIASNY)
        if bylo is not None and bylo != self._ciasno and self.isVisible():
            self.odswiez()                  # inna liczba przystanków na karcie dnia
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
    klik_zamkniecia = pyqtSignal()
    klik_minimalizacji = pyqtSignal()
    klik_pelnego_ekranu = pyqtSignal()

    PROMIEN_KROPKI = 3.0

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._ciagniecie = None       # okno przeciągane za pasek górny
        # Kropka ostrzeżenia na zakładce: miesiąc już minął, a nie ma dla
        # niego ani wpisu w historii, ani folderu z dokumentami. Liczy ją
        # okno (_odswiez_kropki) — pasek tylko rysuje.
        self.kropki = (False, False, False)

    def pole_kropki(self, numer):
        """Środek kropki na zakładce o tym numerze (współrzędne paska)."""
        pole = self._pola_zakladek()[int(numer)]
        return QPointF(pole.right() - 7.0, pole.y() + 7.0)

    def paintEvent(self, zdarzenie):
        super().paintEvent(zdarzenie)
        if not any(self.kropki):
            return
        malarz = QPainter(self)
        malarz.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for numer, kropka in enumerate(self.kropki[:len(self.MIESIACE)]):
            if not kropka:
                continue
            srodek = self.pole_kropki(numer)
            S.punkt_swiatla(malarz, srodek, 9.0, S.BURSZTYN, 120)
            malarz.setPen(Qt.PenStyle.NoPen)
            malarz.setBrush(QBrush(S.BURSZTYN))
            malarz.drawEllipse(srodek, self.PROMIEN_KROPKI, self.PROMIEN_KROPKI)
        malarz.end()

    def _sygnaly(self):
        return {"konto": self.klik_konta, "dzwonek": self.klik_dzwonka,
                "blad": self.klik_bledu, "awatar": self.klik_awatara,
                "zamknij": self.klik_zamkniecia,
                "minimalizuj": self.klik_minimalizacji,
                "pelny_ekran": self.klik_pelnego_ekranu}

    def mousePressEvent(self, zdarzenie):
        trafiona = None
        for numer, pole in enumerate(self._pola_zakladek()):
            if pole.contains(zdarzenie.position()):
                trafiona = numer
                break
        prawe = self.pole_prawe(zdarzenie.position())
        # Okno nie ma ramy systemowej — pustym miejscem paska się je przesuwa.
        okno = self.window()
        if (zdarzenie.button() == Qt.MouseButton.LeftButton and trafiona is None
                and not prawe and okno is not None and not okno.isFullScreen()):
            self._ciagniecie = (zdarzenie.globalPosition().toPoint()
                                - okno.frameGeometry().topLeft())
        super().mousePressEvent(zdarzenie)
        if trafiona is not None:
            self.wybrano_zakladke.emit(trafiona)
        sygnal = self._sygnaly().get(prawe)
        if sygnal is not None:
            sygnal.emit()

    def mouseMoveEvent(self, zdarzenie):
        okno = self.window()
        if self._ciagniecie is not None and okno is not None \
                and zdarzenie.buttons() & Qt.MouseButton.LeftButton:
            if okno.isFullScreen():
                self._ciagniecie = None
            else:
                okno.move(zdarzenie.globalPosition().toPoint() - self._ciagniecie)
        super().mouseMoveEvent(zdarzenie)

    def mouseReleaseEvent(self, zdarzenie):
        self._ciagniecie = None
        super().mouseReleaseEvent(zdarzenie)

    def mouseDoubleClickEvent(self, zdarzenie):
        """Podwójny klik w pasek — jak w każdym oknie: pełny ekran i z powrotem."""
        if zdarzenie.button() == Qt.MouseButton.LeftButton \
                and not self.pole_prawe(zdarzenie.position()):
            self._ciagniecie = None
            self.klik_pelnego_ekranu.emit()
        super().mouseDoubleClickEvent(zdarzenie)


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
    USTAWIENIE_WOLNYCH = "nowy_dni_wolne"
    USTAWIENIE_KARTKI = "nowy_kartka_zwinieta"
    PAMIEC_MIESIECY = 12          # ile miesięcy dni bez pracy zostaje w pliku
    CZAS_PODGLADU_PESEL = 4000    # ms: tyle cyfry PESEL stoją odsłonięte po kliknięciu oka

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
        self._praca_dni = None          # ile dni silnik zameldował jako gotowe
        self._praca_dokumenty = None    # ...i ile plików PDF już napisał
        self._kwota_zamowiona = 0.0
        self._formularz_zamowiony = None
        self._parametry_generacji = None  # parametry wątku — do wpisu historii
        self._osiagnieto = 0.0
        self._niepelna = False
        self._pole_pesel = None
        self._nakladka = None           # rama paneli nad nowym oknem
        self._wyrastanie = None         # panel wyrastający z ikony na szynie
        self._rama_w_ruchu = None       # rama schowana na czas wyrastania
        self._zegar_stylu = None        # pilnuje materiału w panelu
        self._ekran_startowy = None
        self._o_programie = None
        self._kopia = None
        self._miesiace = None           # historia + foldery osoby (historia_okna), liczone leniwie
        # Taca pamięta poprzednie miesiące: który miesiąc na niej leży i skąd
        # są kartki — z silnika (wynik tej sesji) albo z folderu na dysku.
        self._taca_miesiac = None       # (rok, miesiąc) miesiąca na tacy
        self._taca_folder = ""          # folder miesiąca z dysku ("" = wynik tej sesji)
        self._taca_dni = []             # kartki miesiąca z dysku (proto_dane.Dzien)
        self._taca_liczby = {}          # liczby jego PDF-ów (pmt_dokumenty.liczby_kompletu)
        self._pliki_tacy = []

        self._ustaw_baze_z_profilu()
        self._ustaw_miesiac_w_prototypie()

        super().__init__(rodzic)

        # Okno programu nie ma ramy systemowej (górnego paska Windows) —
        # tytuł, przesuwanie i sterowanie oknem są w pasku nowego systemu.
        if rodzic is None:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle(PMT.tytul_okna())
        self._podaj_miasta_mapie()
        self._uzupelnij_karty()
        self._polacz_nowe()
        self._dodaj_mape_na_tace()
        self._zastosuj_konto()
        self._wolne = self._wolne_z_ustawien()
        self.kartka.ustaw_zwiniecie(self._kartka_zwinieta_z_ustawien(), zglos=False)
        self._uklad_mapy()
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
        self._dociagnij_historie()
        self._odswiez_kropki()
        QTimer.singleShot(0, self._dymek_rozpoznania)
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
        # okno bez ramy systemowej: własne sterowanie po prawej stronie paska
        self.pasek.klik_zamkniecia.connect(self.close)
        self.pasek.klik_minimalizacji.connect(self.showMinimized)
        self.pasek.klik_pelnego_ekranu.connect(self.przelacz_pelny_ekran)

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
        self.taca.wybrano_miesiac.connect(self._wybrano_miesiac_tacy)
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
                                     self.baza_lng, self.wojewodztwo,
                                     MIAST_PODGLADU)
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
        # Cyfry stoją pod znakami jak hasło; oko w polu odsłania je na chwilę
        # (_przelacz_podglad_pesel), a utrata fokusu chowa z powrotem.
        self._pole_pesel = karta.haslo
        self._pole_pesel.setEchoMode(QLineEdit.EchoMode.Password)
        self._pole_pesel.setMaxLength(11)
        self._pole_pesel.setPlaceholderText("PESEL")
        self._pole_pesel.setText(self.profil.pesel)
        self._pole_pesel.show()
        self._zegar_pesel = QTimer(self)
        self._zegar_pesel.setSingleShot(True)
        self._zegar_pesel.setInterval(self.CZAS_PODGLADU_PESEL)
        self._zegar_pesel.timeout.connect(self._ukryj_pesel)
        self._oko_pesel = self._pole_pesel.addAction(
            ikona_oka(False), QLineEdit.ActionPosition.TrailingPosition)
        self._oko_pesel.setToolTip("")
        self._oko_pesel.triggered.connect(self._przelacz_podglad_pesel)
        self._pole_pesel.installEventFilter(self)

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

    # ── PESEL pod znakami ─────────────────────────────────────────────
    def pesel_odsloniety(self):
        pole = self._pole_pesel
        return pole is not None and pole.echoMode() == QLineEdit.EchoMode.Normal

    def _przelacz_podglad_pesel(self):
        """Oko w polu: cyfry na chwilę widać, potem wracają pod znaki."""
        if self.pesel_odsloniety():
            self._ukryj_pesel()
        else:
            self._pokaz_pesel()

    def _pokaz_pesel(self):
        pole = self._pole_pesel
        if pole is None:
            return
        pole.setEchoMode(QLineEdit.EchoMode.Normal)
        self._oko_pesel.setIcon(ikona_oka(True))
        self._zegar_pesel.start()

    def _ukryj_pesel(self):
        pole = self._pole_pesel
        if pole is None:
            return
        self._zegar_pesel.stop()
        if pole.echoMode() != QLineEdit.EchoMode.Password:
            pole.setEchoMode(QLineEdit.EchoMode.Password)
            self._oko_pesel.setIcon(ikona_oka(False))

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
        self._uniewaznij_historie()           # inna osoba = inne miesiące

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
        self._zdejmij_miesiac_z_tacy()
        self._ustaw_miesiac_w_prototypie()
        self.pasek.MIESIACE = self._zakladki_miesiecy()
        self.pasek._aktywny = 1
        self._odswiez_kropki()
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
    def _kartka_zwinieta_z_ustawien(self):
        """Czy kartka delegacji ma być zwinięta do brzegu — jak ją zostawiono."""
        return bool(PMT.ustawienie(self.USTAWIENIE_KARTKI, False))

    def _zapamietaj_zwiniecie_kartki(self, zwinieta):
        """Zwinięcie kartki zostaje na następne uruchomienie."""
        zwinieta = bool(zwinieta)
        if bool(PMT.ustawienie(self.USTAWIENIE_KARTKI, False)) != zwinieta:
            PMT.zapisz_ustawienie(self.USTAWIENIE_KARTKI, zwinieta)

    def _przelacz_zwiniecie_kartki(self, zwinieta=False):
        super()._przelacz_zwiniecie_kartki(zwinieta)
        self._zapamietaj_zwiniecie_kartki(zwinieta)

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
        """Kwota i tryb pracy z ostatniego uruchomienia.

        Limitu dnia nie wczytujemy: nie ma go już w oknie, więc pracujemy
        zawsze na kwocie z przepisów (OK.LIMITY_DNIA[0] = PMT.MAX_KWOTA_DNIA).
        Inaczej zostałby na stałe ten, kto raz zapisał sobie inny.
        """
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
                (self.USTAWIENIE_TRYBU, self.k_parametry.tryb.aktywna()))
        for klucz, wartosc in pary:
            if PMT.ustawienie(klucz, None) != wartosc:
                PMT.zapisz_ustawienie(klucz, wartosc)

    def _rok_miesiac(self):
        """Dni bez pracy dotyczą miesiąca POKAZYWANEGO, nie miesiąca prototypu."""
        return self.rok, self.miesiac

    def _przelacz_wolny(self, numer):
        """Prawy przycisk na taśmie — ta sama lista, co w karcie parametrów."""
        super()._przelacz_wolny(numer)
        self._zapamietaj_wolne()

    def _ustaw_dni_bez_pracy(self, dni):
        """Wybór z kalendarza — ta sama lista, co prawy przycisk na taśmie."""
        super()._ustaw_dni_bez_pracy(dni)
        self._zapamietaj_wolne()

    def _dni_zablokowane(self, rok, miesiac):
        """Kalendarz „Dni bez pracy" blokuje z góry święta i dni poza
        tygodniem roboczym w bieżącym trybie — z tej samej listy, z której
        silnik bierze dni robocze (PMT.pobierz_dni_robocze)."""
        tryb = self.k_parametry.tryb.aktywna()
        PMT.ustaw_tryb_pracy("wieczory" if str(tryb).lower().startswith("wiecz")
                             else "tydzien")
        return PMT.dni_zablokowane_miesiaca(int(rok), int(miesiac))

    # ── podgląd (zamiast uproszczonego silnika prototypu) ────────────
    def _maks_miesiaca(self, tryb):
        return maks_kwota_miesiaca(self.rok, self.miesiac, tryb,
                                   self._wolne, self._limit_dnia,
                                   self.profil.stawka)

    def _przelicz_teraz(self, pierwszy=False):
        self._zegar_kwoty.stop()
        self._powod_bledu = ""        # powód odmowy dotyczył poprzednich danych
        if pierwszy:
            # kwota wraca z groszami — zapisano ją co do grosza
            self.k_parametry.kwota.ustaw_tekst(D.zl(self._wczytaj_widok()))
        tryb = self.k_parametry.tryb.aktywna()
        self._maks_kwota = self._maks_miesiaca(tryb)
        self._za_duzo = bool(self._maks_kwota
                             and self._kwota() > self._maks_kwota + 0.005)
        # dolna granica: najtańszy prawdziwy wyjazd z TEJ bazy
        self._min_kwota = min_kwota_wyjazdu(getattr(self, "geo", None),
                                            self.baza_miasto, self.profil.stawka)
        self._za_malo = bool(self._min_kwota
                             and self._kwota() < self._min_kwota - 0.005)

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

        self.k_parametry.wolne.ustaw_dni(self._wolne, self.miesiac)
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
        if getattr(self, "_za_malo", False):
            # Kwota niższa niż najtańszy prawdziwy wyjazd z tej bazy.
            # Ostrzegamy liczbą i pozwalamy generować — dokumenty wyjdą
            # wtedy na tę właśnie kwotę minimalną, nie na wpisaną.
            self.k_parametry.kwota.ustaw_note(
                "min. %s zł" % D.zl(self._min_kwota, grosze=False), True)
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
        # Rubryka PRZEŁOŻONY na każdym dokumencie bierze się WYŁĄCZNIE z pliku
        # menedzer.txt. Bez pliku wyszłaby pusta — stare okno zatrzymywało
        # wtedy użytkownika przed generowaniem, nowe robi to samo: krótka
        # etykieta przy kompasie, bez zdań.
        if not PMT._menedzer():
            return None, "brak menedzer.txt"

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
        if self._taca_folder:
            # na tacy leżał miesiąc z dysku — schodzi, wynik silnika idzie na jego miejsce
            self._schowaj_tace()
            self._zdejmij_miesiac_z_tacy()
        self._powod_bledu = ""
        self._po_generacji = False
        self._niepelna = False
        self._osiagnieto = 0.0
        self._kwota_zamowiona = round(parametry["kwota_cel"], 2)
        self._parametry_generacji = dict(parametry)
        self._formularz_zamowiony = self._snapshot_formularza()
        self._etap_silnika = "dane"
        self._praca_dni = 0.0
        self._praca_dokumenty = None
        self.tasma.ustaw_prace(0.0)       # taśma czeka na pierwszy meldunek
        self._zacznij_intro_generowania()
        self.k_kompas.TYTUL = "Przerwij"
        self.k_kompas.kompas.ustaw_stan("praca")
        self.ustaw_postep_pokazu(0.02)

        self._watek = PMT.GeneratorThread(parametry)
        self._watek.postep.connect(self._postep_generacji)
        self._watek.sukces.connect(self._sukces_generacji)
        self._watek.blad.connect(self._blad_generacji)
        if hasattr(self._watek, "anulowano"):
            self._watek.anulowano.connect(self._anulowano_generacji)
        if hasattr(self._watek, "dzien_gotowy"):
            self._watek.dzien_gotowy.connect(self._dzien_gotowy_generacji)
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
        # wątek przerwie się dopiero na najbliższym meldunku — przelot nie czeka
        self._zakoncz_intro_generowania(natychmiast=True)
        return True

    def _odmowa(self, powod, blad=False):
        """Stan „nie da się" — nazwa albo liczba, bez zdań instruktażowych."""
        self._powod_bledu = str(powod or "")
        self._etap_silnika = ""
        self._koniec_sekwencji()
        self.k_kompas.TYTUL = "Generuj dokumenty"
        self.k_kompas.kompas.ustaw_stan("blad" if blad else "ostrzezenie")
        self.k_kompas.kompas.setToolTip(self._powod_bledu)
        self.k_kompas.ustaw_etapy({n: "czeka" for n in OK.ETAPY})
        self.k_parametry.kwota.ustaw_note(self._powod_bledu, True)

    def _postep_generacji(self, tekst, ulamek):
        self._etap_silnika = etap_silnika(tekst)
        self._postep_tasmy(tekst)
        self.ustaw_postep_pokazu(float(ulamek))
        self._dokumenty_przelotu(tekst)

    def _dokumenty_przelotu(self, tekst):
        """Pisany dokument (i/n) stempluje trasy swoich dni na przelocie."""
        film = getattr(self, "_intro_generowania", None)
        if film is None or self._etap_silnika != "PDF":
            return
        ile = postep_etapu(tekst)
        if ile is None or not hasattr(film, "ustaw_dokumenty"):
            return
        try:
            film.ustaw_dokumenty(ile[0], ile[1])
        except Exception:
            pass

    def _dzien_gotowy_generacji(self, slad):
        """Silnik ułożył dzień (PMT.slad_dnia) — jego trasa zapala się na
        przelocie. Sygnał idzie z wątku silnika jako gotowa krotka; silnik
        na nic tu nie czeka."""
        film = getattr(self, "_intro_generowania", None)
        if film is None or not hasattr(film, "dodaj_trase"):
            return
        try:
            data, punkty = slad
            film.dodaj_trase(punkty, data=data)
        except Exception:
            pass

    def _postep_tasmy(self, tekst):
        """Kafle dni i klamry dokumentów zapalają się Z MELDUNKÓW SILNIKA.

        Nie z zegara i nie z samego ułamka postępu: silnik mówi wprost
        „Dzień 3/7" przy układaniu tras i „(2/6)" przy pisaniu plików, więc
        taśma pokazuje dokładnie to, co się właśnie policzyło. Gdy akurat
        melduje coś innego, ostatnia znana wartość zostaje — taśma nigdy
        się nie cofa i nie miga.
        """
        film = getattr(self, "_intro_generowania", None)
        if film is not None:
            try:
                film.ustaw_postep(self.k_kompas.kompas.postep())
            except Exception:
                pass
        ile = postep_etapu(tekst)
        dolny = str(tekst or "").lower()
        if ile is not None and "dzień" in dolny:
            self._praca_dni = ile[0] / float(ile[1])
        elif self._etap_silnika == "PDF":
            self._praca_dni = 1.0
            if ile is not None:
                self._praca_dokumenty = ile[0] / float(ile[1])
        elif self._etap_silnika == "mapa":
            self._praca_dni = 1.0
            self._praca_dokumenty = 1.0
        elif self._praca_dni is None:
            self._praca_dni = 0.0
        self.tasma.ustaw_prace(self._praca_dni, self._praca_dokumenty)

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

    def ustaw_animacje(self, wlaczone):
        """Jeden przełącznik gasi też to, co dokłada nowy wygląd.

        Po zgaszeniu ekran ma wyglądać dokładnie tak, jak wyglądał przed
        warstwą efektów: bez wyrastania paneli, bez fali pracy na taśmie
        i bez życia na mapie. Na tym stoją powtarzalne zrzuty.
        """
        super().ustaw_animacje(wlaczone)
        if wlaczone:
            return
        if self._wyrastanie is not None:
            self._wyrastanie.przerwij()
            self._po_wyrastaniu()
        self._praca_dni = None
        self._praca_dokumenty = None
        try:
            self.tasma.ustaw_prace(None)
        except AttributeError:
            pass
        self._zakoncz_intro_generowania(natychmiast=True)

    def _koniec_sekwencji(self):
        """Koniec pracy silnika — taśma przestaje pokazywać postęp."""
        self._praca_dni = None
        self._praca_dokumenty = None
        try:
            self.tasma.ustaw_prace(None)
        except AttributeError:
            pass
        self._zakoncz_intro_generowania()

    # ── zaczep na intro: przelot w czasie generowania ────────────────
    #  Intro gra wtedy, gdy silnik pracuje i jest na co patrzeć — nie na
    #  starcie programu. Sekwencja generowania woła tylko te dwa punkty
    #  i o wstawce wie tyle: dostaje okno, zwraca widżet (albo None)
    #  z metodami ``zakoncz`` (silnik skończył — lądowanie) i, jeśli je ma,
    #  ``przerwij`` (koniec natychmiast), ``ustaw_postep`` (ułamek postępu),
    #  ``dodaj_trase`` (dzień ułożony) i ``ustaw_dokumenty`` (pisany plik).
    #  Domyślna wstawka to przelot nad rejonem (proto_mapa.PrzelotRejonu);
    #  ``INTRO_GENEROWANIA = None`` wyłącza intro w ogóle. Przy zgaszonych
    #  animacjach wstawka nie jest wołana — zostaje sam postęp na kompasie.
    INTRO_GENEROWANIA = staticmethod(przelot_generowania)

    def _zacznij_intro_generowania(self):
        wstawka = type(self).INTRO_GENEROWANIA
        self._intro_generowania = None
        if wstawka is None or not self._animacje:
            return
        try:
            self._intro_generowania = wstawka(self)
        except Exception as blad:
            PMT.log_error(blad)
            self._intro_generowania = None

    def _intro_zeszlo(self, film):
        """Wstawka zeszła sama (pominięta kliknięciem albo wylądowała) —
        okno przestaje ją karmić meldunkami; silnik pracuje jak pracował."""
        if getattr(self, "_intro_generowania", None) is film:
            self._intro_generowania = None

    def _uderzenie_pieczeci(self):
        """Kartka dokumentu osiadła na stosie pokazu — kompas dostaje rozpęd."""
        try:
            self.k_kompas.kompas.impuls()
        except AttributeError:
            pass

    def _zakoncz_intro_generowania(self, natychmiast=False):
        """``natychmiast`` — bez lądowania (przerwanie, zgaszone animacje)."""
        film = getattr(self, "_intro_generowania", None)
        if film is None:
            return
        self._intro_generowania = None
        try:
            if natychmiast and hasattr(film, "przerwij"):
                film.przerwij()
            else:
                film.zakoncz()
        except Exception:
            pass

    def _blad_generacji(self, wiadomosc):
        self._watek = None
        krotko = str(wiadomosc or "").strip().splitlines()[0][:40] or "błąd"
        self._odmowa(krotko, blad=True)

    def _anulowano_generacji(self):
        """Przerwane generowanie — ekran wraca do stanu sprzed kliknięcia."""
        self._watek = None
        self._etap_silnika = ""
        self._koniec_sekwencji()
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
        self._koniec_sekwencji()
        self._dni_silnika = list(finalne_dni)
        self._pracownik_silnika = pracownik
        self.folder_wyniku = folder
        self.pliki_wyniku = dokumenty_w_wyniku(folder)
        self._zapisz_historie(finalne_dni, folder)
        self._osiagnieto = round(sum(d.suma for d in finalne_dni), 2)
        self._niepelna = bool(getattr(watek, "_kwota_niepelna", False)) \
            or abs(self._osiagnieto - self._kwota_zamowiona) >= 0.01
        # Silnik potrafi policzyć minimum dokładniej niż szacunek z puli miast
        # — jeśli je podał, to ono jest prawdą i ono ma stać przy kwocie.
        _min_silnika = float(getattr(watek, "_kwota_min_realna", 0.0) or 0.0)
        if _min_silnika > 0:
            self._min_kwota = round(_min_silnika, 2)
            self._za_malo = self._kwota_zamowiona < self._min_kwota - 0.005

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

    # ── historia miesięcy ────────────────────────────────────────────
    def _zapisz_historie(self, finalne_dni, folder):
        """Wpis historii po udanym generowaniu — ten sam format, co w starym
        oknie (PMT.wpis_historii_generacji). Z tej historii żyją wykresy
        „Twoja praca → Delegacje", Archiwum i historia_miesiecy()."""
        parametry = self._parametry_generacji
        if not parametry:
            return False
        try:
            wpis = PMT.wpis_historii_generacji(parametry, finalne_dni, folder)
            PMT.dodaj_do_historii(parametry["imie"], parametry["pesel"], wpis)
        except Exception as blad:
            PMT.log_error(blad)
            self._uniewaznij_historie()       # folder i tak leży na dysku
            return False
        self._uniewaznij_historie()
        return True

    def _dane_uzytkownika(self):
        """(imię, PESEL) osoby z karty PRACOWNIK — pod tym kluczem leży jej
        historia. Panele starego okna czytały je z JEGO formularza, który w
        nowym systemie stoi pusty: wykresy delegacji wychodziły zerowe."""
        imie = ""
        pesel = ""
        try:
            imie = " ".join(self.k_pracownik.imie.text().split())
            if self._pole_pesel is not None:
                pesel = "".join(self._pole_pesel.text().split())
        except Exception:
            imie, pesel = "", ""
        return (imie or self.profil.imie or "",
                pesel or self.profil.pesel or "")

    def _dociagnij_historie(self):
        """Miesiące, które leżą gotowe na dysku, a historia ich nie zna —
        raz przy starcie, przy zmianie konta i przy otwieraniu „Twojej pracy".
        Gdy nic nowego, kosztuje tyle, co przegląd Pulpitu."""
        imie, pesel = self._dane_uzytkownika()
        if not (imie and pesel):
            self._uniewaznij_historie()
            return 0
        try:
            return PMT.dociagnij_historie_z_folderow(imie, pesel)
        except Exception as blad:
            PMT.log_error(blad)
            return 0
        finally:
            self._uniewaznij_historie()

    # ── miesiące osoby: kropka na zakładce, kratka roku, pasek tacy ──
    def _miesiace_historii(self):
        """{(rok, miesiąc): {...}} — historia + foldery na dysku (historia_okna),
        liczone raz i trzymane do najbliższej zmiany (generowanie, dociągnięcie,
        inna osoba). Żaden paintEvent tego nie liczy — tylko czyta wynik."""
        if self._miesiace is None:
            imie, pesel = self._dane_uzytkownika()
            try:
                self._miesiace = historia_okna(imie, pesel)
            except Exception as blad:
                PMT.log_error(blad)
                self._miesiace = {}
        return self._miesiace

    def _uniewaznij_historie(self):
        self._miesiace = None
        self._odswiez_kropki()
        self._odswiez_odkryte()

    # ── białe plamy rejonu: ślad obecności z historii na mapie ───────
    def _miejsca_odkryte(self):
        """Nazwy miejscowości ze śladem obecności programu — suma pól
        „miejsca" wszystkich miesięcy osoby (PMT.historia_miesiecy)."""
        nazwy = set()
        for wpis in self._miesiace_historii().values():
            for nazwa in (wpis.get("miejsca") or {}):
                if nazwa:
                    nazwy.add(str(nazwa))
        return nazwy

    def _odswiez_odkryte(self):
        """Mapa dostaje ślad obecności; bez historii — wszystko pod mgłą."""
        mapa = getattr(self, "mapa", None)
        if mapa is None or not hasattr(mapa, "ustaw_odkryte"):
            return
        try:
            mapa.ustaw_odkryte(self._miejsca_odkryte())
        except Exception as blad:
            PMT.log_error(blad)

    def _folder_miesiaca(self, rok, miesiac):
        """Folder z gotowymi dokumentami tego miesiąca albo pusty napis:
        wynik tej sesji, a poza nim komplet z dysku (historia + foldery)."""
        klucz = (int(rok), int(miesiac))
        if klucz == (self.rok, self.miesiac) and self.folder_wyniku \
                and dokumenty_w_wyniku(self.folder_wyniku):
            return self.folder_wyniku
        wpis = self._miesiace_historii().get(klucz) or {}
        folder = str(wpis.get("folder") or "")
        if wpis.get("istnieje") and folder and dokumenty_w_wyniku(folder):
            return folder
        return ""

    def _kropki_zakladek(self):
        """Które zakładki paska dostają kropkę: miesiąc już się skończył,
        a nie ma dla niego ani wpisu w historii, ani folderu z dokumentami."""
        if not hasattr(self, "pasek"):
            return (False, False, False)
        biezacy = miesiac_biezacy()
        znane = self._miesiace_historii()
        numer = self.rok * 12 + self.miesiac - 1
        kropki = []
        for krok in (-1, 0, 1):
            n = numer + krok
            kropki.append(miesiac_nierozliczony((n // 12, n % 12 + 1), znane, biezacy))
        return tuple(kropki)

    def _odswiez_kropki(self):
        pasek = getattr(self, "pasek", None)
        if pasek is None:
            return
        kropki = self._kropki_zakladek()
        if kropki != pasek.kropki:
            pasek.kropki = kropki
            pasek.update()

    def przejdz_do_miesiaca(self, rok, miesiac):
        """Kratka roku: cały program na ten miesiąc — jak zakładka paska —
        z panelu z powrotem na ekran pracy, a komplet z dysku od razu na
        tacę. Zwraca folder miesiąca albo pusty napis."""
        rok, miesiac = int(rok), int(miesiac)
        self.ustaw_miesiac(rok, miesiac)
        if self._nakladka is not None and self._nakladka.isVisible():
            self._nakladka.zamknij()          # → dzial_bilans_miesiaca
        else:
            self.dzial_bilans_miesiaca()
        return self.pokaz_tace_miesiaca(rok, miesiac)

    def _podaj_miasta_mapie(self):
        """Prawdziwe współrzędne i rangi miejscowości do mapy.

        Mapa dostawała dotąd same ułamki 0..1 z proto_dane i sama nic nie
        wiedziała o kilometrach. Teraz bierze szerokość i długość wprost z
        geokodowania silnika, więc odległości na rysunku i podziałka
        odpowiadają kilometrom, które program liczy do rozliczenia. Bez
        współrzędnych nic się nie dzieje — mapa rysuje tak jak dotąd."""
        miasta = miasta_dla_mapy(getattr(self, "geo", None),
                                 getattr(self, "baza_miasto", ""))
        if not miasta:
            return False
        try:
            self.mapa.ustaw_miasta(miasta, baza=self.baza_miasto)
        except Exception:
            return False
        return True

    def _przebuduj_mape(self):
        """Mapa buduje świat w konstruktorze — po zmianie miast stawiamy nową."""
        stara = self.mapa
        nowa = MapaDnia(self)
        nowa.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        nowa.setGeometry(stara.geometry())
        nowa.ustaw_stan(stara._stan)
        nowa.klikniete_miasto.connect(self._klik_miasto)
        nowa.trasa_rysuje_sie.connect(self.kartka.ustap)
        nowa.trasa_gotowa.connect(self._kartka_na_miejsce)
        nowa.ustaw_obecnosc_kartki(self.kartka.obecnosc())
        nowa.ustaw_animacje(self._animacje)
        self.mapa = nowa
        # nowa mapa musi znać kartkę i paski, ZANIM dostanie miasta i dzień —
        # inaczej jej pierwszy kadr policzy się na całej szerokości widżetu
        self._przelicz_kotwice()
        self._podaj_zaslony()
        self._podaj_miasta_mapie()
        self._odswiez_odkryte()
        stara.ustaw_animacje(False)
        stara.setParent(None)
        stara.deleteLater()
        nowa.lower()
        nowa.show()
        for widget in (self.kartka, self.pigulka, self.zakres, self.taca):
            widget.raise_()
        self._przelicz_kotwice()

    # ── taca z prawdziwymi plikami; pamięta poprzednie miesiące ─────
    #  Na tacy leży JEDEN miesiąc: wynik tej sesji (kartki z silnika) albo
    #  miesiąc z dysku (kartki z tabel przejazdów gotowych PDF-ów, bez
    #  generowania). Pasek nad kartkami przełącza miesiące, a przyciski
    #  (folder, mapa, podpis, wysyłka) działają na tym, który leży.
    def _folder_tacy(self):
        return self._taca_folder or self.folder_wyniku

    def _miesiac_tacy(self):
        return self._taca_miesiac or (self.rok, self.miesiac)

    def _taca_z_dysku(self):
        return bool(self._taca_folder)

    def _dni_tacy(self):
        """Dni z kartkami na tacy — z dysku albo z silnika."""
        if self._taca_z_dysku():
            return [d for d in self._taca_dni if not d.wolny and not d.wylaczony]
        return self._dni_w_trasie()

    def _zdejmij_miesiac_z_tacy(self):
        self._taca_miesiac = None
        self._taca_folder = ""
        self._taca_dni = []
        self._taca_liczby = {}
        self._pliki_tacy = []

    def _miesiace_tacy(self):
        """[(rok, miesiąc)] — pigułki paska tacy: miesiące z gotowymi
        dokumentami na dysku, których liczby dały się odczytać (kwota we
        wpisie); folder z nieczytelnymi PDF-ami nie dostaje pigułki, bo
        taca pokazałaby zero kartek i zerową kwotę."""
        miesiace = set()
        for klucz, wpis in self._miesiace_historii().items():
            if wpis.get("istnieje") and wpis.get("folder") and wpis.get("kwota") is not None \
                    and dokumenty_w_wyniku(wpis["folder"]):
                miesiace.add(klucz)
        if self.folder_wyniku and self._po_generacji and dokumenty_w_wyniku(self.folder_wyniku):
            miesiace.add((self.rok, self.miesiac))
        if self._taca_miesiac and self._folder_tacy():
            miesiace.add(self._taca_miesiac)
        return sorted(miesiace)

    def _skrot_folderu(self, folder=None):
        """Folder wyniku w zapisie z prototypu: „Pulpit / Rozliczenie_…"."""
        folder = self._folder_tacy() if folder is None else folder
        if not folder:
            return ""
        sciezka = folder.rstrip(os.sep)
        rodzic = os.path.basename(os.path.dirname(sciezka))
        nazwa = os.path.basename(sciezka)
        return "%s / %s" % (rodzic, nazwa) if rodzic else nazwa

    def _opisz_tace(self):
        """Podpisy i kafle tacy: prawdziwe pliki, folder, miesiące i stan odległości."""
        folder = self._folder_tacy()
        if not folder:
            return
        rok, miesiac = self._miesiac_tacy()
        self._pliki_tacy = dokumenty_w_wyniku(folder)
        if not self._taca_z_dysku():
            self.pliki_wyniku = list(self._pliki_tacy)
        self.taca.l_sciezka.setText(
            "%s %d · %s" % (PMT.MIESIACE_PL[miesiac - 1], rok,
                            PMT._odmiana_plikow(len(self._pliki_tacy))))
        self.taca.l_folder.setText(self._skrot_folderu(folder))
        self.taca.l_folder.setToolTip(folder)
        # Kafel kilometrów nosił na sztywno podpis „REALNE DROGI" — także
        # wtedy, gdy kilometry były szacunkiem z linii prostej. Miesiąc z dysku
        # mówi to, co stoi w jego dokumentach („Odległości: szacunek").
        if self._taca_z_dysku():
            etykieta = (self._taca_liczby or {}).get("odleglosci") or ""
            opis = etykieta.upper() if etykieta else "KILOMETRY"
        else:
            stan = PMT.stan_zrodla_odleglosci()
            opis = stan["etykieta"].upper() if stan["odcinki"] else "KILOMETRY"
        kafel = self.taca.k_km
        if getattr(kafel, "_opis", "") != opis:
            kafel._opis = opis
            kafel.updateGeometry()
            kafel.update()
        self.taca.ustaw_miesiace(self._miesiace_tacy(), (rok, miesiac))
        self._odswiez_stan_mapy()

    def _pokaz_tace(self, animacja=True):
        """Kompas „Otwórz dokumenty" i koniec generowania: na tacę wraca
        wynik TEJ sesji, także gdy wcześniej leżał na niej miesiąc z dysku."""
        self._zdejmij_miesiac_z_tacy()
        if self._po_generacji:
            self._taca_miesiac = (self.rok, self.miesiac)
        super()._pokaz_tace(animacja)
        self._opisz_tace()

    def pokaz_tace_miesiaca(self, rok, miesiac, animacja=None):
        """Taca z kartkami TAMTEGO miesiąca — z folderu na dysku, bez
        generowania czegokolwiek. Miesiąc tej sesji z wynikiem silnika idzie
        zwykłą drogą. Zwraca folder miesiąca albo pusty napis."""
        rok, miesiac = int(rok), int(miesiac)
        animacja = self._animacje if animacja is None else animacja
        if (rok, miesiac) == (self.rok, self.miesiac) and self._po_generacji \
                and self.folder_wyniku:
            self._pokaz_tace(animacja)
            return self.folder_wyniku
        folder = self._folder_miesiaca(rok, miesiac)
        if not folder:
            return ""
        dni = dni_z_folderu(folder, rok, miesiac)
        if not any(not d.wolny for d in dni):
            return ""                     # PDF-y bez czytelnych tabel — taca bez kartek kłamałaby zerem
        self._taca_miesiac = (rok, miesiac)
        self._taca_folder = folder
        self._taca_dni = dni
        self._taca_liczby = DOK.liczby_kompletu(folder)
        self._oznacz_podpisane(self._taca_dni, folder)
        self.taca.ustaw_dni(self._taca_dni)
        if self._taca_liczby.get("km") is not None:
            self.taca.k_km.od_zera(float(self._taca_liczby["km"]))   # kilometry wprost z dokumentów
        self._odswiez_stan_tacy()
        self._wysun_tace(animacja)
        self._opisz_tace()
        return folder

    def _wybrano_miesiac_tacy(self, rok, miesiac):
        """Pigułka na pasku tacy — kartki tamtego miesiąca, taca zostaje."""
        if (int(rok), int(miesiac)) == self._miesiac_tacy() and self._folder_tacy():
            return
        self.pokaz_tace_miesiaca(rok, miesiac, animacja=False)

    def _otworz_folder(self):
        folder = self._folder_tacy()
        if folder:
            PMT.otworz_w_systemie(folder)

    def _otworz_wszystkie(self):
        """Prawdziwe pliki PDF otwierane w systemie."""
        folder = self._folder_tacy()
        if not folder:
            return
        pliki = dokumenty_w_wyniku(folder)
        self._pliki_tacy = pliki
        if not self._taca_z_dysku():
            self.pliki_wyniku = list(pliki)
        for sciezka in pliki:
            PMT.otworz_w_systemie(sciezka)
        self.taca.l_stan.setText(
            "otwarto %s" % PMT._odmiana_plikow(len(pliki)))
        self._zegar_stanu.start()

    def _otworz_dokument_dnia(self, dzien):
        """Kliknięcie kartki na tacy otwiera PDF z jej dniem."""
        folder = self._folder_tacy()
        if not folder:
            return
        sciezka = plik_dokumentu(folder, getattr(dzien, "dokument", 0))
        if sciezka:
            PMT.otworz_w_systemie(sciezka)
            self.taca.l_stan.setText(os.path.basename(sciezka))
            self._zegar_stanu.start()

    def _odswiez_stan_tacy(self):
        folder = self._folder_tacy()
        if not folder:
            super()._odswiez_stan_tacy()
            return
        w_trasie = self._dni_tacy()
        podpisane = [d for d in w_trasie if d.podpisany]
        if podpisane:
            self.taca.l_stan.setText("%d z %d podpisanych"
                                     % (len(podpisane), len(w_trasie)))
        else:
            self.taca.l_stan.setText(DOK.opis_kompletu(folder))

    # ── podpis i wysyłka: okna programu, nie makiety ─────────────────
    def _podpisane_numery(self, folder):
        """Numery dokumentów podpisanych w TYM folderze — z manifestu paczki
        podpisowej (pmt_podpis prowadzi go dla każdej kopii PDF: nazwa
        źródła i status). Numer delegacji z nazwy pliku wskazuje dokument."""
        modul = PMT.modul_pomocniczy("pmt_wysylka")
        dane = None
        if modul is not None:
            try:
                dane, _katalog = modul.wczytaj_manifest(folder)
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
            if not self._to_ten_sam_plik(modul_podpisu, nazwa, wpis.get("skrot"), folder):
                continue
            numer = DOK.numer_delegacji(nazwa)
            if numer:
                podpisane.add(numer)
        return podpisane

    def _oznacz_podpisane(self, dni, folder):
        podpisane = self._podpisane_numery(folder)
        for dzien in dni:
            dzien.podpisany = getattr(dzien, "dokument", 0) in podpisane
        return len(podpisane)

    def _wczytaj_podpisy(self, odswiez=True):
        """Które dni WYNIKU TEJ SESJI są już podpisane — pieczęć na kartce
        i na kartce delegacji nad mapą. Miesiąc z dysku ma własną drogę
        (_odswiez_podpisy_tacy)."""
        if not self.folder_wyniku:
            return 0
        ile = self._oznacz_podpisane(self.dni, self.folder_wyniku)
        if odswiez:
            if not self._taca_z_dysku():
                self.taca.ustaw_dni(self.dni_widoczne)
                self._opisz_tace()
            self.tasma.ustaw_dni(self.dni_widoczne)
            self.tasma.ustaw_dzis(OK.DZIS)
            self.tasma.ustaw_wybrany(self._wybrany)
            self._odswiez_dzien()
        return ile

    def _odswiez_podpisy_tacy(self):
        """Po podpisie albo wysyłce: pieczęcie na kartkach miesiąca, który
        leży na tacy — z dysku albo z silnika."""
        if self._taca_z_dysku():
            self._oznacz_podpisane(self._taca_dni, self._taca_folder)
            self.taca.ustaw_dni(self._taca_dni)
            self._opisz_tace()
        else:
            self._wczytaj_podpisy()
        self._odswiez_stan_tacy()

    def _to_ten_sam_plik(self, modul_podpisu, nazwa, skrot, folder=None):
        """Czy pieczęć z manifestu dotyczy PLIKU, KTÓRY TERAZ LEŻY W FOLDERZE.

        Po ponownym generowaniu w tym samym folderze nazwy się powtarzają,
        a treść nie — bez porównania sumy kontrolnej świeży, niepodpisany
        dokument dostawałby pieczęć po poprzedniku."""
        folder = self.folder_wyniku if folder is None else folder
        if not nazwa or not skrot or modul_podpisu is None:
            return True          # stary manifest bez sumy — wierzymy statusowi
        zrodlo = os.path.join(folder, nazwa)
        if not os.path.isfile(zrodlo):
            return True          # plik źródłowy zniknął — nie ma z czym równać
        try:
            return modul_podpisu.suma_sha256(zrodlo) == skrot
        except Exception:
            return True

    def _panel_podpisu(self):
        """Prawdziwy podpis elektroniczny — DialogPodpis nad pmt_podpis,
        na folderze miesiąca, który leży na tacy."""
        folder = self._folder_tacy()
        if not folder or not os.path.isdir(folder):
            return
        okno = PMT.DialogPodpis(self, folder=folder, is_dark=True)
        self._dialog_podpisu = okno
        try:
            okno.exec()
        finally:
            try:
                okno.zatrzymaj_zegar()
            except Exception:
                pass
            self._dialog_podpisu = None
        self._odswiez_podpisy_tacy()

    def _panel_wysylki(self):
        """Prawdziwa wysyłka pocztą — DialogWysylka nad pmt_wysylka,
        na folderze i miesiącu, który leży na tacy."""
        folder = self._folder_tacy()
        if not folder or not os.path.isdir(folder):
            return
        rok, miesiac = self._miesiac_tacy()
        okno = PMT.DialogWysylka(self, folder=folder,
                                 imie=self.profil.imie, miesiac=miesiac,
                                 rok=rok, is_dark=True)
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
        self._odswiez_podpisy_tacy()

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
        """„Zgłoś błąd": nowa wiadomość do adresu z pmt_kontakt.txt.

        Odnośnik składa PMT.mailto_zgloszenia — oczyszczony adresat i jawny
        temat (program, wersja, kod użytkownika), nic więcej: żadnego cc ani
        bcc/UDW, które potrafiły wjechać z pliku razem z adresem. Otwiera go
        Qt (QDesktopServices), nie moduł webbrowser — ten na Windows potrafił
        oddać mailto przeglądarce zamiast programowi pocztowemu.
        Zwraca otwarty odnośnik."""
        kod = self._kod_uzytkownika or PMT.online_kod_uzytkownika() or ""
        odnosnik = PMT.mailto_zgloszenia(kod)
        otworz_adres(odnosnik)
        return odnosnik

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
        akcje = {akcja_haslo: self.zmien_haslo,
                 akcja_tester: lambda: PMT.uruchom_karte_testera(self)}
        menu.addSeparator()
        akcja_wyloguj = menu.addAction("Wyloguj")
        akcje[akcja_wyloguj] = self.wyloguj
        return menu, akcje

    def zmien_haslo(self):
        PMT.zmien_haslo_w_programie(
            self, self._kod_uzytkownika or PMT.online_kod_uzytkownika(), True)

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
        self._schowaj_tace()
        self._zdejmij_miesiac_z_tacy()
        self._przebuduj_mape()
        self._wolne = self._wolne_z_ustawien()
        self._przelicz_teraz()
        self._odswiez_pasek_konta()
        self._dociagnij_historie()
        self._dymek_rozpoznania()

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
        """Jedno konto, jedna historia powiadomień, dane pracownika i miesiąc
        planu z tego ekranu, okna dialogowe paneli nad tym ekranem."""
        try:
            stare._kod_uzytkownika = self._kod_uzytkownika or PMT.online_kod_uzytkownika()
            stare._imie_zalogowany = self._imie_zal
            stare._demo_pozostalo = self._pozostalo_dni
        except Exception:
            pass
        # Tamto okno jest ukryte: okna dialogowe paneli (doprecyzowanie
        # adresu, różnice importu, aktualizacja) stają nad TYM ekranem.
        stare._okno_dialogow = self
        # Panele czytają pracownika z karty PRACOWNIK, a miesiąc planu
        # z paska miesięcy — formularza tamtego okna już nie ma.
        stare._dane_pracownika = self._profil_do_paneli
        stare._miesiac_planu = lambda: (self.rok, self.miesiac)
        for nazwa in ("overlay_staty", "overlay_plan"):
            try:
                getattr(stare, nazwa)._on_dane_uzytkownika = self._dane_uzytkownika
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

    def _profil_do_paneli(self):
        """Komplet danych pracownika dla paneli starego okna (delegacja
        z planu, adres bazy planera): karta PRACOWNIK, w zapasie profil."""
        imie, pesel = self._dane_uzytkownika()
        try:
            adres = " ".join(self.k_pracownik.adres.text().split())
        except Exception:
            adres = ""
        try:
            stanowisko = self.k_pracownik.stanowisko.currentText()
        except Exception:
            stanowisko = ""
        try:
            silnik = int(self.k_parametry.pojemnosc.currentIndex())
        except Exception:
            silnik = self.profil.silnik_idx
        return {"imie": imie, "pesel": pesel,
                "adres": adres or self.profil.adres,
                "stanowisko": stanowisko or self.profil.stanowisko,
                "silnik_idx": silnik if silnik in (0, 1) else self.profil.silnik_idx}

    # ── rama paneli nad nowym oknem ──────────────────────────────────
    def nakladka(self):
        """Rama, w której panele programu stają NAD nowym ekranem."""
        if self._nakladka is None:
            self._nakladka = NakladkaDzialu(self)
            self._nakladka.przed_zamknieciem = self._panel_wsiaka
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
        if self._nakladka is self._rama_w_ruchu:
            return                      # rama czeka za krawędzią — patrz _wyrosnij_panel
        self._nakladka.setGeometry(OK.SZYNA_W, OK.PASEK_H,
                                   max(320, self.width() - OK.SZYNA_W),
                                   max(240, self.height() - OK.PASEK_H))

    def resizeEvent(self, zdarzenie):
        super().resizeEvent(zdarzenie)
        self._ustaw_geometrie_nakladki()
        if self._wyrastanie is not None and self._wyrastanie.gra():
            self._wyrastanie.przerwij()     # obraz panelu jest już nieaktualny
            self._po_wyrastaniu()

    def pokaz_panel(self, widget, tytul, podtytul="", numer=None):
        """Gotowy panel programu w materiale nowego systemu, nad nowym oknem."""
        rama = self.nakladka()
        if self._wyrastanie is not None and self._wyrastanie.gra():
            self._wyrastanie.przerwij()      # poprzedni ruch kończy się od razu
            self._po_wyrastaniu()
        stal = rama.isVisible()
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
        if not stal:                     # panel wychodzi z ikony, a nie znikąd
            self._wyrosnij_panel(rama, numer)
        if self._zegar_stylu is not None and not self._zegar_stylu.isActive():
            self._zegar_stylu.start()
        return widget

    # ── panel wyrasta z ikony na szynie i tam wraca ──────────────────
    def wyrastanie(self):
        if self._wyrastanie is None:
            self._wyrastanie = WyrastaniePanelu(self)
            self._wyrastanie.skonczone.connect(self._po_wyrastaniu)
        return self._wyrastanie

    def _po_wyrastaniu(self):
        """Koniec ruchu: panel wjeżdża z poczekalni na swoje miejsce."""
        rama = self._rama_w_ruchu
        if rama is None:
            return
        self._rama_w_ruchu = None
        self._ustaw_geometrie_nakladki()
        if rama.isVisible():
            rama.raise_()

    def _pole_ikony(self, numer):
        """Pole ikony działu na szynie, przeliczone na współrzędne okna."""
        try:
            pola = self.szyna._pola()
            if numer is None:
                numer = getattr(self.szyna, "_aktywna", 0)
            pole = pola[int(numer)]
        except (AttributeError, IndexError, TypeError, ValueError):
            return None
        lewy_gorny = self.szyna.mapTo(self, pole.topLeft().toPoint())
        return QRectF(lewy_gorny.x(), lewy_gorny.y(), pole.width(), pole.height())

    def _wyrosnij_panel(self, rama, numer, wstecz=False):
        """Jedno przejście: panel rośnie z ikony albo w nią wsiąka."""
        if not self._animacje:
            return False
        skad = self._pole_ikony(numer)
        if skad is None or rama.width() < 40 or rama.height() < 40:
            return False
        obraz = rama.grab()
        if obraz.isNull():
            return False
        dokad = QRectF(rama.geometry())
        ruch = self.wyrastanie()
        # Panel JEST otwarty przez cały ruch — czeka tylko tuż za krawędzią
        # okna, żeby nie przeświecał przez własny rosnący obraz. Wjeżdża na
        # miejsce, gdy obraz dojdzie do końca; każde przerwanie (zmiana
        # rozmiaru, zgaszenie animacji, kolejny panel) też go tam stawia.
        if not wstecz:
            self._rama_w_ruchu = rama
            rama.move(self.width() + 8, rama.y())
        else:
            self._rama_w_ruchu = None
        ruch.zacznij(obraz, skad, dokad, wstecz)
        return True

    def _panel_wsiaka(self):
        """Zamykany panel wraca do swojej ikony — wywoływane tuż przed hide()."""
        rama = self._nakladka
        if rama is None or not rama.isVisible():
            return
        self._wyrosnij_panel(rama, None, wstecz=True)

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
        elif rodzaj == QEvent.Type.FocusOut and obiekt is self._pole_pesel \
                and self.pesel_odsloniety():
            self._ukryj_pesel()               # PESEL wraca pod znaki, gdy pole traci fokus
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
        self._dociagnij_historie()
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
        """Plik mapy tras: miesiąca z tacy, folderu tej sesji albo
        ostatniego rozliczenia na dysku."""
        return plik_mapy_tras(self._taca_folder) or \
            plik_mapy_tras(self.folder_wyniku) or \
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
    #  PO STARCIE — bez animacji startowej
    # ═══════════════════════════════════════════════════════════════

    def po_starcie(self, imie=""):
        """Wołane z sekwencji startowej zaraz po show(). Do 3.22.0 tu
        ruszała animacja startowa, a na jej koniec czekało zaproszenie
        testera i okno aktualizacji. Animacji nie ma — zaproszenie idzie
        po tej samej chwili co dawniej (900 ms), a okno aktualizacji
        buduje się w starym oknie od razu, gdy wątek zna werdykt."""
        if imie:
            self._imie_zalogowany = imie      # właściwość: karta i pasek konta
        QTimer.singleShot(900, lambda: PMT.zaproszenie_testera(
            self, self._imie_zal or "", True))

    def _dymek_rozpoznania(self):
        """„Rozpoznano pracownika": profil ZALOGOWANEJ osoby leżał na dysku,
        więc karta PRACOWNIK jest już wypełniona. Do 3.22.0 dymek pokazywał
        formularz starego okna po intrze; teraz ten ekran, zaraz po starcie
        i po zmianie konta. Nigdy dla cudzego profilu: tylko pełna zgodność
        imienia i nazwiska z kontem."""
        try:
            konto = " ".join((PMT.online_imie_uzytkownika() or "").split()).lower()
        except Exception:
            konto = ""
        profil = self.profil
        imie = " ".join(str(profil.imie or "").split())
        if not (konto and imie and profil.prawdziwy and imie.lower() == konto):
            return False
        self.toast.show_toast("Rozpoznano pracownika", imie, success=True)
        return True

    # ── okno jako główne okno programu ───────────────────────────────
    def show(self):
        """Program wstaje na PEŁNYM EKRANIE, bez ramy systemowej.

        dopasuj_do_ekranu() zostaje: to rozmiar, do którego okno wraca po
        wyjściu z pełnego ekranu (przycisk w pasku, F11 albo Esc)."""
        if not self._dopasowane and self.parent() is None:
            self._dopasowane = True
            self.dopasuj_do_ekranu()
            # showFullScreen() woła show() — tu weszlibyśmy w pętlę; stan
            # okna ustawiamy więc wprost, dokładnie tak jak robi to Qt.
            self.setWindowState((self.windowState()
                                 & ~(Qt.WindowState.WindowMinimized
                                     | Qt.WindowState.WindowMaximized))
                                | Qt.WindowState.WindowFullScreen)
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
        self._zakoncz_intro_generowania(natychmiast=True)   # przelot ginie razem z nim
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

    okno.showNormal()          # zrzuty robimy w rozmiarze docelowym, nie na pełnym ekranie
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
#     trasy powstają dopiero po naciśnięciu kompasu. Podgląd NIE woła
#     generuj_trasy: jedno wywołanie to 36–145 zapytań o drogi, zerowanie
#     stanu źródła odległości, zapis pamięci dróg i wpis do dziennika
#     diagnostycznego — a zegar kwoty odpala przeliczenie po każdym
#     klawiszu. Zamiast tego podgląd powtarza reguły silnika na sucho
#     (2–7 ms na przeliczenie) i tylko dlatego różni się od wyniku:
#     przy tych samych danych wychodzi mu ±4 dni i ±1 dokument.
#  4. Motyw jasny nie dotyczy nowego ekranu — panele w nim otwierane są
#     zawsze ciemne (materiał nowego systemu).
#  5. W oknie o minimalnym rozmiarze (1040×660) karta planera ma własne
#     minimum szersze niż rama i przycina się o kilkanaście pikseli.
#  6. Miesiąc z dysku (kratka roku → taca) ma na tacy PRAWDZIWE kartki
#     z jego PDF-ów, ale taśma, mapa i kartka nad mapą pokazują dla niego
#     wciąż podgląd (szacunek) — wynik silnika nie jest odtwarzany z plików.
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
