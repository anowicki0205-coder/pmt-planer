# -*- coding: utf-8 -*-
"""Oprawa okna powitalnego — pierwszy ekran programu w języku nowego systemu.

Tu mieszka WYŁĄCZNIE wygląd: ciemna scena, żywa mapa pod spodem, szklana
karta, logo retro i zejście karty po udanym logowaniu. Cała kontrola dostępu
— hasła, historia urządzenia, tryb bez sieci, ważność konta, komunikaty —
zostaje tam, gdzie była, czyli w ``PMT_Delegacje.dialog_logowania``. Ten plik
nie wie nic o hasłach i nigdy ich nie dotyka.

Gdy czegoś tu zabraknie (brak katalogu ``prototyp`` w paczce, stare Qt),
import się nie uda i okno logowania wraca do poprzedniej oprawy — logowanie
działa dalej, tylko skromniej wygląda.

Żywe tło wyłącza ten sam przełącznik, co resztę głębi: pusty plik
``BEZ_3D.txt`` obok programu albo w katalogu użytkownika, ustawienie
``wyglad_3d`` w menu Wygląd, a osobno ustawienie ``zywe_tlo_logowania``.
Tło samo ustępuje także wtedy, gdy rysowanie okaże się za wolne — najpierw
gaśnie animacja, a przy naprawdę ciężkim sprzęcie znika cała mapa.
"""

import os
import sys
import time

from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import (QBrush, QColor, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap)
from PyQt6.QtWidgets import (QApplication, QFrame, QGraphicsOpacityEffect,
                             QPushButton, QWidget)


# ═══════════════════════════════════════════════════════════════════════
#  WPIĘCIE PROTOTYPU
#  Widżety nowego wyglądu leżą w podkatalogu „prototyp", a po spakowaniu
#  PyInstallerem — płasko obok programu. Sprawdzamy oba układy, dokładnie
#  tak jak robi to nowy_wyglad.katalog_prototypu().
# ═══════════════════════════════════════════════════════════════════════
def katalog_prototypu() -> str:
    miejsca = []
    paczka = getattr(sys, "_MEIPASS", "")
    if paczka:
        miejsca += [os.path.join(paczka, "prototyp"), paczka]
    tutaj = os.path.dirname(os.path.abspath(__file__))
    miejsca += [os.path.join(tutaj, "prototyp"), tutaj]
    for katalog in miejsca:
        if os.path.isfile(os.path.join(katalog, "proto_styl.py")):
            return katalog
    return os.path.join(tutaj, "prototyp")


def _wepnij_prototyp() -> str:
    katalog = katalog_prototypu()
    if katalog not in sys.path:
        sys.path.insert(0, katalog)
    return katalog


KATALOG_PROTOTYPU = _wepnij_prototyp()

import proto_styl as S                                            # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  MIARY
# ═══════════════════════════════════════════════════════════════════════
SZEROKOSC_KARTY = 496          # szkło z polami; reszta ekranu należy do mapy
ROZMIAR_ZNAKU = 92             # logo retro nad kartą
MIN_WYSOKOSC_ZE_ZNAKIEM = 600  # niżej logo ustępuje, żeby karta się mieściła
CZAS_ZEJSCIA = 200             # ms: karta ustępuje przed oknem programu
CZAS_KURTYNY = 260             # ms: scena gaśnie, gdy program już stoi
ZYCIE_KURTYNY = 8000           # ms: bezpiecznik — scena nie zostaje na wieki

# Budżety rysowania. Pierwsza klatka mapy liczona jest przy dołączaniu tła;
# przekroczona oznacza sprzęt, na którym żywe tło tylko przeszkadza.
# Pierwsza klatka zawiera jednorazowy wypiek krajobrazu 3D (relief, lasy,
# bryły osad — ok. 250 ms na zwykłym laptopie, do 450 ms w rozgrzanym
# procesie), więc próg jest luźny; o płynności decyduje dalej straż
# klatka po klatce (BUDZET_KLATKI / BUDZET_KRYTYCZNY).
BUDZET_PIERWSZEJ_KLATKI = 800.0   # ms
BUDZET_KLATKI = 42.0              # ms — powyżej gaśnie animacja blasku
BUDZET_KRYTYCZNY = 180.0          # ms — powyżej znika cała mapa
KLATEK_DO_OCENY = 5               # tyle klatek mierzymy, zanim wydamy wyrok

USTAWIENIE_TLA = "zywe_tlo_logowania"


# ═══════════════════════════════════════════════════════════════════════
#  WYŁĄCZNIKI
# ═══════════════════════════════════════════════════════════════════════
def _program():
    """Moduł PMT_Delegacje, jeśli już stoi — bez wczytywania go drugi raz."""
    modul = sys.modules.get("PMT_Delegacje")
    if modul is not None:
        return modul
    glowny = sys.modules.get("__main__")
    if glowny is not None and hasattr(glowny, "WERSJA_PROGRAMU") \
            and hasattr(glowny, "dialog_logowania"):
        return glowny
    return None


def _katalogi_wylacznika():
    kat = []
    P = _program()
    try:
        if P is not None:
            kat.append(P._katalog_programu())
    except Exception:
        pass
    kat.append(os.path.dirname(os.path.abspath(__file__)))
    kat.append(os.path.expanduser("~"))
    return kat


def zywe_tlo_wlaczone() -> bool:
    """Czy pod kartą ma żyć mapa. Trzy drogi wyłączenia, wszystkie znane
    z reszty programu: BEZ_3D.txt, ustawienie „wyglad_3d" i osobne
    ustawienie „zywe_tlo_logowania"."""
    P = _program()
    try:
        if P is not None and not bool(P.ustawienie(USTAWIENIE_TLA, True)):
            return False
    except Exception:
        pass
    try:
        if P is not None and not bool(P.glebia_wlaczona()):
            return False
    except Exception:
        pass
    for kat in _katalogi_wylacznika():
        try:
            if os.path.exists(os.path.join(kat, "BEZ_3D.txt")):
                return False
        except Exception:
            continue
    return True


def powitanie(teraz=None) -> str:
    """Powitanie zamiast nagłówka „Zaloguj się" — okno i tak o nic innego
    nie prosi, więc nie musi tego mówić."""
    import datetime
    godzina = (teraz or datetime.datetime.now()).hour
    if godzina < 5:
        return "Dobrej nocy"
    if godzina < 18:
        return "Dzień dobry"
    return "Dobry wieczór"


# ═══════════════════════════════════════════════════════════════════════
#  ARKUSZ STYLU
#  Te same nazwy obiektów, co dotąd (kod, haslo, etyk, blad, ok, anuluj,
#  pomoc, chip, chipmin) — dzięki temu sama treść okna logowania nie
#  musi wiedzieć, w jakiej stoi oprawie.
# ═══════════════════════════════════════════════════════════════════════
def styl() -> str:
    tekst = S.rodzina_tekst()
    naglowek = S.rodzina_naglowek()
    return """
    #PmtLogowanie { background: #050A14; }
    #PmtKarta { background: transparent; border: none; }
    QLabel { background: transparent; }
    QLabel#tytul { color:%(tekst)s; font-family:'%(fn)s'; font-size:26px;
                   font-weight:700; }
    QLabel#pod   { color:%(tekst3)s; font-family:'%(ft)s'; font-size:12px; }
    QLabel#etyk  { color:%(tekst3)s; font-family:'%(ft)s'; font-size:10px;
                   font-weight:700; letter-spacing:1.6px; }
    QLabel#blad  { color:%(blad)s; font-family:'%(ft)s'; font-size:11.5px;
                   font-weight:600; }
    QLineEdit { background: rgba(9,16,28,215); color:%(tekst)s;
                border:1px solid rgba(255,255,255,0.10); border-radius:12px;
                padding:11px 12px; font-family:'%(ft)s';
                selection-background-color:%(cyjan)s; selection-color:#04121A; }
    QLineEdit#kod { color:%(cyjan)s; font-family:'%(fn)s'; font-size:23px;
                    font-weight:700; letter-spacing:10px; }
    QLineEdit#haslo { font-size:15px; letter-spacing:3px; }
    QLineEdit:focus { border:1px solid rgba(0,240,255,0.55);
                      background: rgba(11,22,38,230); }
    QLineEdit:disabled { color:%(tekst3)s; border-color: rgba(255,255,255,0.06); }
    QPushButton#ok { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                       stop:0 %(cyjan)s, stop:1 %(zielen)s);
                     color:#04121A; font-family:'%(ft)s'; font-size:14px;
                     font-weight:700; border:none; border-radius:12px;
                     padding:12px 30px; }
    QPushButton#ok:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                             stop:0 #66F6FF, stop:1 #5CEEC4); }
    QPushButton#ok:disabled { background: rgba(17,28,46,0.72); color:%(tekst3)s;
                              border:1px solid rgba(255,255,255,0.10);
                              padding:11px 29px; }
    QPushButton#anuluj { background: rgba(17,28,46,0.72); color:%(tekst2)s;
                         font-family:'%(ft)s'; font-size:12.5px; font-weight:600;
                         border:1px solid rgba(255,255,255,0.12);
                         border-radius:12px; padding:11px 18px; }
    QPushButton#anuluj:hover { color:%(mieta)s; border-color: rgba(0,228,161,0.55);
                               background: rgba(0,228,161,0.10); }
    QPushButton#anuluj:pressed { background: rgba(0,228,161,0.18); }
    QPushButton#anuluj:disabled { color:#4B5A72; border-color: rgba(255,255,255,0.06); }
    QPushButton#pomoc { background: transparent; color:%(tekst3)s;
                        font-family:'%(ft)s'; font-size:11.5px; font-weight:600;
                        border:none; border-radius:9px; padding:6px 8px; }
    QPushButton#pomoc:hover { color:%(mieta)s; background: rgba(0,228,161,0.10); }
    QPushButton#pomoc:pressed { background: rgba(0,228,161,0.18); }
    QPushButton#pomoc:disabled { color:#3E4B60; }
    QPushButton#chip { color:%(tekst2)s; background: rgba(17,28,46,0.72);
                       border:1px solid rgba(255,255,255,0.12); border-radius:13px;
                       font-family:'%(ft)s'; font-size:11.5px; font-weight:700;
                       padding:6px 12px; }
    QPushButton#chip:hover { color:%(mieta)s; border-color: rgba(0,228,161,0.55);
                             background: rgba(0,228,161,0.12); }
    QPushButton#chipmin { color:%(tekst3)s; background: rgba(11,19,32,0.66);
                          border:1px solid rgba(255,255,255,0.10); border-radius:8px;
                          font-family:'%(ft)s'; font-size:12px; font-weight:700; }
    QPushButton#chipmin:hover { color:%(cyjan)s; border-color: rgba(0,240,255,0.55);
                                background: rgba(0,240,255,0.12); }
    QToolTip { background:#0E1726; color:%(tekst)s;
               border:1px solid rgba(255,255,255,0.14); padding:6px; }
    """ % {"fn": naglowek, "ft": tekst,
           "tekst": S.TEKST.name(), "tekst2": S.TEKST_2.name(),
           "tekst3": S.TEKST_3.name(), "cyjan": S.CYJAN.name(),
           "zielen": S.ZIELEN.name(), "mieta": S.MIETA.name(),
           "blad": S.BLAD.name()}


def pasek_swiatla(polozenie: float) -> str:
    """Przycisk „Sprawdzam…" z przesuwającym się światłem — ten sam ruch,
    co dotąd, tylko w barwach nowego systemu."""
    a1 = max(0.001, polozenie - 0.20)
    a2 = min(0.999, polozenie + 0.20)
    return ("QPushButton#ok { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            " stop:0 %s, stop:%.3f %s, stop:%.3f %s, stop:%.3f %s, stop:1 %s);"
            " color:#04121A; font-family:'%s'; font-size:14px; font-weight:700;"
            " border:none; border-radius:12px; padding:12px 30px; }"
            % (S.CYJAN.name(), a1, S.ZIELEN.name(), polozenie, S.MIETA.name(),
               a2, S.ZIELEN.name(), S.CYJAN.name(), S.rodzina_tekst()))


# ═══════════════════════════════════════════════════════════════════════
#  LOGO RETRO
# ═══════════════════════════════════════════════════════════════════════
_ZNAK_PAMIEC = {}


def _plik_znaku():
    """Logo programu z paczki albo podmienione przez administratora —
    to samo, które program pokazuje w oknie i na pasku zadań."""
    P = _program()
    try:
        if P is not None:
            return P.znajdz_logo()
    except Exception:
        pass
    return None


def znak_retro(bok: int) -> QPixmap:
    """Logo retro w podanym boku. Najpierw plik programu (pmt_logo_retro.png
    w paczce albo własny obok programu), a gdy go nie ma — rysowane kodem
    przez logo_retro. Liczone raz i trzymane w pamięci: drugie okno
    logowania, po wylogowaniu, dostaje je za darmo."""
    bok = max(24, int(bok))
    gotowe = _ZNAK_PAMIEC.get(bok)
    if gotowe is not None:
        return gotowe
    obraz = None
    sciezka = _plik_znaku()
    if sciezka:
        try:
            zrodlo = QPixmap(sciezka)
            if not zrodlo.isNull():
                obraz = zrodlo.scaled(
                    bok, bok, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
        except Exception:
            obraz = None
    if obraz is None:
        from logo_retro import narysuj_logo
        obraz = narysuj_logo(bok * 2, True).scaled(
            bok, bok, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
    _ZNAK_PAMIEC[bok] = obraz
    return obraz


class Znak(QWidget):
    """Logo nad kartą. Rysuje się dopiero po pokazaniu okna — start programu
    nie czeka na obrazek."""

    def __init__(self, bok=ROZMIAR_ZNAKU, rodzic=None):
        super().__init__(rodzic)
        self.setFixedSize(bok, bok)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._obraz = None

    def przygotuj(self):
        if self._obraz is not None:
            return
        try:
            self._obraz = znak_retro(self.width())
        except Exception:
            self._obraz = None
            self.hide()
            return
        self.update()

    def paintEvent(self, _zdarzenie):
        if self._obraz is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pole = QRectF(self.rect()).adjusted(10, 10, -10, -10)
        # halo domyślnie rysuje ZAOKRĄGLONY KWADRAT — logo jest monetą, więc
        # zaokrąglenie idzie do połowy boku, inaczej wokół znaku stoi jasna ramka
        S.halo(p, pole, S.CYJAN, 40, 26.0, zaokraglenie=pole.width() * 0.5)
        p.drawPixmap(0, 0, self._obraz)
        p.end()


# ═══════════════════════════════════════════════════════════════════════
#  PRZYCISKI OKNA: MINIMALIZUJ, ZAMKNIJ
# ═══════════════════════════════════════════════════════════════════════
PRZYCISK_OKNA_W = 30
PRZYCISK_OKNA_H = 28


class PrzyciskOkna(QPushButton):
    """Przycisk rogu okna malowany pędzlem — ta sama pigułka i ta sama
    kreska, co w pasku górnym okna programu (proto_okno.PasekGorny).
    ``rodzaj``: „minimalizuj" albo „zamknij"."""

    def __init__(self, rodzaj="zamknij", rodzic=None):
        super().__init__("", rodzic)
        self.rodzaj = rodzaj
        self.setObjectName("chipmin")
        self.setAutoDefault(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(PRZYCISK_OKNA_W, PRZYCISK_OKNA_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Minimalizuj" if rodzaj == "minimalizuj" else "Zamknij")
        self._pod = False

    def enterEvent(self, zdarzenie):
        self._pod = True
        self.update()
        super().enterEvent(zdarzenie)

    def leaveEvent(self, zdarzenie):
        self._pod = False
        self.update()
        super().leaveEvent(zdarzenie)

    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self.rodzaj == "zamknij" and self._pod:
            tlo, obrys, kolor = S.z_alfa(S.BLAD, 190), S.z_alfa(S.BLAD, 220), S.TEKST
        elif self._pod:
            tlo, obrys, kolor = QColor(30, 48, 74, 235), S.OBRYS_MOCNY, S.TEKST
        else:
            tlo, obrys, kolor = QColor(17, 28, 46, 160), S.OBRYS, S.TEKST_2
        sciezka = QPainterPath()
        sciezka.addRoundedRect(r, 9.0, 9.0)
        p.fillPath(sciezka, QBrush(tlo))
        p.setPen(QPen(obrys, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(sciezka)
        c = r.center()
        pen = QPen(kolor, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        if self.rodzaj == "minimalizuj":
            p.drawLine(QPointF(c.x() - 5.5, c.y() + 3.5), QPointF(c.x() + 5.5, c.y() + 3.5))
        else:
            p.drawLine(QPointF(c.x() - 4.6, c.y() - 4.6), QPointF(c.x() + 4.6, c.y() + 4.6))
            p.drawLine(QPointF(c.x() + 4.6, c.y() - 4.6), QPointF(c.x() - 4.6, c.y() + 4.6))
        p.end()


# ═══════════════════════════════════════════════════════════════════════
#  SZKLANA KARTA
# ═══════════════════════════════════════════════════════════════════════
class Karta(QFrame):
    """Karta logowania: szkło z gradientowym obrysem, halo i cieniem.

    LUZ to margines na cień i poświatę — układ w środku musi go doliczyć
    do swoich marginesów, inaczej pola wejdą na krawędź szkła."""

    LUZ = 18

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setObjectName("PmtKarta")
        self._pam = None            # gotowe szkło; przeliczane przy zmianie rozmiaru
        self._pam_rozmiar = None

    def pole(self) -> QRectF:
        return QRectF(self.rect()).adjusted(self.LUZ, self.LUZ,
                                            -self.LUZ, -self.LUZ)

    def _zbuduj_szklo(self):
        """Szkło kosztuje kilkanaście milisekund, a nie zmienia się ani przy
        pisaniu, ani przy błędzie — rysujemy je RAZ na rozmiar."""
        pam = QPixmap(self.size())
        pam.fill(QColor(0, 0, 0, 0))
        p = QPainter(pam)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = self.pole()
        # kolejność ma znaczenie: poświata i cień IDĄ POD szkło, inaczej
        # cyjan rozlewa się po całej karcie i szkło robi się mleczne
        S.halo(p, r, S.CYJAN, 46, 26.0, zaokraglenie=S.PROMIEN_DUZY)
        S.cien(p, r, S.PROMIEN_DUZY, sila=200, rozmycie=24, przesun=12)
        S.szklo(p, r, S.PROMIEN_DUZY, mocne=True)
        S.szron(p, r, S.PROMIEN_DUZY, sila=18)
        S.swiatlo_kierunkowe(p, r, 125.0, 16, promien=S.PROMIEN_DUZY)
        S.obrys_gradientowy(p, S._sciezka(r, S.PROMIEN_DUZY),
                            S.CYJAN, S.ZIELEN, 1.4)
        p.end()
        self._pam = pam
        self._pam_rozmiar = self.size()

    def paintEvent(self, _zdarzenie):
        r = self.pole()
        if r.width() < 8 or r.height() < 8:
            return
        if self._pam is None or self._pam_rozmiar != self.size():
            self._zbuduj_szklo()
        p = QPainter(self)
        p.drawPixmap(0, 0, self._pam)
        p.end()


# ═══════════════════════════════════════════════════════════════════════
#  ŻYWA MAPA POD KARTĄ
# ═══════════════════════════════════════════════════════════════════════
def _dzien_pokazowy():
    """Trasa do tła. To dane POKAZOWE prototypu, nie plan zalogowanej osoby
    — przed podaniem hasła nikt nie ma prawa zobaczyć cudzej trasy."""
    import datetime
    import proto_dane as D
    dzis = datetime.date.today()
    dni = D.oblicz_miesiac(2400, dzis.year, dzis.month, "Tydzień")
    z_wizytami = [d for d in dni if getattr(d, "wizyty", None)]
    if not z_wizytami:
        return None
    return z_wizytami[(dzis.day - 1) % len(z_wizytami)]


def _zbuduj_mape(rodzic):
    """Podklasa mapy dnia bez podziałki i z pomiarem czasu klatki."""
    from proto_mapa import MapaDnia

    class MapaTla(MapaDnia):
        def __init__(self, rodzic=None):
            super().__init__(rodzic)
            self.czasy = []

        def _rysuj_podzialke(self, p, rzut, r):
            return          # „20 km" pod oknem powitalnym to zbędny napis

        def paintEvent(self, zdarzenie):
            poczatek = time.perf_counter()
            super().paintEvent(zdarzenie)
            self.czasy.append((time.perf_counter() - poczatek) * 1000.0)
            if len(self.czasy) > 40:
                del self.czasy[:20]

    return MapaTla(rodzic)


class Zaslona(QWidget):
    """Cienka warstwa między mapą a kartą: przygasza tło, żeby szkło i napisy
    czytały się spokojnie, a mapa dalej była widoczna."""

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        pole = QRectF(self.rect())
        if pole.isEmpty():
            p.end()
            return
        g = QLinearGradient(pole.topLeft(), pole.bottomLeft())
        g.setColorAt(0.0, QColor(5, 10, 20, 140))
        g.setColorAt(0.45, QColor(5, 10, 20, 70))
        g.setColorAt(1.0, QColor(5, 10, 20, 165))
        p.fillRect(pole, QBrush(g))
        S.winieta(p, pole, 120)
        p.end()


class Tlo(QWidget):
    """Scena pod kartą: głęboki gradient, winieta, ziarno — a na to, już po
    pokazaniu okna, żywa mapa."""

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.mapa = None
        self.zaslona = None
        self._znak = None
        self._pam = None            # gotowa scena; przeliczana przy zmianie rozmiaru
        self._pam_rozmiar = None
        self._straz = None
        self._oceny = 0
        self._pierwsza_klatka = False
        self._po_pokazaniu = []

    # — rysowanie —
    def _zbuduj_scene(self):
        pam = QPixmap(self.size())
        p = QPainter(pam)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pole = QRectF(self.rect())
        S.tlo_sceny(p, pole)
        S.winieta(p, pole, 110)
        S.ziarno(p, pole, sila=10, skala=1.0)
        p.end()
        self._pam = pam
        self._pam_rozmiar = self.size()

    def paintEvent(self, _zdarzenie):
        if self.width() < 2 or self.height() < 2:
            return
        if self._pam is None or self._pam_rozmiar != self.size():
            self._zbuduj_scene()
        p = QPainter(self)
        p.drawPixmap(0, 0, self._pam)
        p.end()
        if not self._pierwsza_klatka:
            self._pierwsza_klatka = True
            QTimer.singleShot(0, self._po_pierwszej_klatce)

    def resizeEvent(self, zdarzenie):
        super().resizeEvent(zdarzenie)
        if self.mapa is not None:
            self.mapa.setGeometry(self.rect())
        if self.zaslona is not None:
            self.zaslona.setGeometry(self.rect())
        self._dopasuj_znak()

    def przypnij_znak(self, znak):
        """Logo nad kartą. Na niskim ekranie ustępuje — pierwsza jest karta."""
        self._znak = znak
        self._dopasuj_znak()

    def _dopasuj_znak(self):
        if self._znak is None:
            return
        try:
            self._znak.setVisible(self.height() >= MIN_WYSOKOSC_ZE_ZNAKIEM)
        except Exception:
            pass

    # — dokładanie życia PO pokazaniu karty —
    def zrob_po_pokazaniu(self, zadanie):
        """Kolejka rzeczy, które mogą poczekać na pierwszą klatkę okna."""
        self._po_pokazaniu.append(zadanie)

    def _po_pierwszej_klatce(self):
        zadania, self._po_pokazaniu = self._po_pokazaniu, []
        self.dolacz_zywe_tlo()          # mapa najpierw: idzie pod całą resztę
        for zadanie in zadania:
            try:
                zadanie()
            except Exception:
                pass
        # jedna pełna klatka całej sceny: bez tego widżety odrysowane osobno
        # mają pod sobą samo tło, a nie mapę
        self.update()

    def dolacz_zywe_tlo(self) -> bool:
        """Stawia mapę pod kartą. Zwraca False, gdy tło jest wyłączone albo
        gdy pierwsza klatka trwała dłużej, niż wolno."""
        if self.mapa is not None:
            return True
        if not zywe_tlo_wlaczone():
            return False
        poczatek = time.perf_counter()
        mapa = None
        try:
            mapa = _zbuduj_mape(self)
            mapa.setGeometry(self.rect())
            mapa.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            mapa.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            mapa.ustaw_dzien(_dzien_pokazowy())
            mapa.lower()
            mapa.show()
            mapa.repaint()                   # pierwsza klatka — ta jest droga
        except Exception:
            self._odstaw_mape(mapa)
            return False
        koszt = (time.perf_counter() - poczatek) * 1000.0
        if koszt > BUDZET_PIERWSZEJ_KLATKI:
            self._odstaw_mape(mapa)          # sprzęt nie udźwignie — bez mapy
            return False
        self.mapa = mapa
        # kolejność od spodu: scena, mapa, zasłona, karta i logo z układu
        zaslona = Zaslona(self)
        zaslona.setGeometry(self.rect())
        zaslona.show()
        zaslona.lower()
        mapa.lower()
        self.zaslona = zaslona
        self._straz = QTimer(self)
        self._straz.setInterval(1500)
        self._straz.timeout.connect(self._ocen_plynnosc)
        self._straz.start()
        return True

    def _odstaw_mape(self, mapa):
        if mapa is None:
            return
        try:
            mapa.zatrzymaj_animacje()
        except Exception:
            pass
        try:
            mapa.hide()
            mapa.setParent(None)
            mapa.deleteLater()
        except Exception:
            pass
        if mapa is self.mapa:
            self.mapa = None
        if self.zaslona is not None:
            try:
                self.zaslona.hide()
                self.zaslona.setParent(None)
                self.zaslona.deleteLater()
            except Exception:
                pass
            self.zaslona = None
        self.update()

    def _ocen_plynnosc(self):
        """Tło samo ustępuje, gdy rysowanie okazuje się za wolne: najpierw
        gaśnie blask trasy, a przy naprawdę ciężkim sprzęcie znika mapa."""
        mapa = self.mapa
        if mapa is None:
            self._zatrzymaj_straz()
            return
        czasy = list(getattr(mapa, "czasy", ()))[-KLATEK_DO_OCENY:]
        if len(czasy) < KLATEK_DO_OCENY:
            self._oceny += 1
            if self._oceny > 8:
                self._zatrzymaj_straz()
            return
        srednia = sum(czasy) / float(len(czasy))
        if srednia > BUDZET_KRYTYCZNY:
            self._odstaw_mape(mapa)
            self._zatrzymaj_straz()
            return
        if srednia > BUDZET_KLATKI:
            try:
                mapa.ustaw_animacje(False)
            except Exception:
                pass
            self._zatrzymaj_straz()
            return
        self._oceny += 1
        if self._oceny > 8:
            self._zatrzymaj_straz()

    def _zatrzymaj_straz(self):
        if self._straz is not None:
            try:
                self._straz.stop()
            except Exception:
                pass
            self._straz = None

    def zatrzymaj(self):
        """Gasi wszystko, co chodzi na zegarze — wołane przy zamykaniu okna."""
        self._zatrzymaj_straz()
        if self.mapa is not None:
            try:
                self.mapa.zatrzymaj_animacje()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════
#  ZEJŚCIE KARTY I KURTYNA
#  Po udanym logowaniu karta nie znika skokiem: rozpływa się, a scena
#  zostaje na ekranie jako nieruchoma kurtyna, dopóki okno programu nie
#  stanie na pełnym ekranie. Dzięki temu między jednym a drugim nie widać
#  pulpitu.
# ═══════════════════════════════════════════════════════════════════════
def zejdz(karta, gotowe, czas=CZAS_ZEJSCIA):
    """Karta ustępuje. ``gotowe`` wywoływane dokładnie raz — także wtedy,
    gdy animacja się nie uda albo utknie."""
    stan = {"wyslane": False}

    def _koniec():
        if stan["wyslane"]:
            return
        stan["wyslane"] = True
        try:
            gotowe()
        except Exception:
            pass

    if karta is None or not zywe_tlo_wlaczone():
        _koniec()
        return
    try:
        efekt = QGraphicsOpacityEffect(karta)
        efekt.setOpacity(1.0)
        karta.setGraphicsEffect(efekt)
        ruch = S.Plynnie(1.0, czas=czas, krzywa="wyjscie", rodzic=karta)
        ruch.zmiana.connect(lambda: efekt.setOpacity(max(0.0, min(1.0, ruch.teraz()))))
        ruch.koniec.connect(_koniec)
        karta._zejscie = ruch
        ruch.do(0.0)
        QTimer.singleShot(int(czas) + 300, _koniec)   # bezpiecznik
    except Exception:
        _koniec()


_KURTYNA = {"okno": None}


class Kurtyna(QWidget):
    """Nieruchoma klatka sceny powitalnej. Stoi między oknem logowania
    a oknem programu, żeby na ułamek sekundy nie błysnął pulpit."""

    def __init__(self, obraz, ksztalt):
        super().__init__(None)
        self._obraz = obraz
        self.setWindowFlags(Qt.WindowType.Window
                            | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setGeometry(ksztalt)
        self._ruch = None

    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        if self._obraz is not None and not self._obraz.isNull():
            p.drawPixmap(self.rect(), self._obraz)
        else:
            p.fillRect(self.rect(), QColor(5, 10, 20))
        p.end()

    def zgas(self, czas=CZAS_KURTYNY):
        if self._ruch is not None:
            return
        try:
            self._ruch = S.Plynnie(1.0, czas=czas, krzywa="wyjscie", rodzic=self)
            self._ruch.zmiana.connect(
                lambda: self.setWindowOpacity(max(0.0, min(1.0, self._ruch.teraz()))))
            self._ruch.koniec.connect(self._zamknij)
            self._ruch.do(0.0)
            QTimer.singleShot(int(czas) + 300, self._zamknij)
        except Exception:
            self._zamknij()

    def _zamknij(self):
        try:
            self.hide()
            self.deleteLater()
        except Exception:
            pass
        if _KURTYNA.get("okno") is self:
            _KURTYNA["okno"] = None


def postaw_kurtyne(okno) -> bool:
    """Zapamiętuje bieżącą klatkę okna logowania i zostawia ją na ekranie."""
    zdejmij_kurtyne(natychmiast=True)
    try:
        if okno is None or not okno.isVisible():
            return False
        obraz = okno.grab()
        kurtyna = Kurtyna(obraz, okno.geometry())
        kurtyna.show()
        # scena ma przykryć pulpit, a nie schować się za cudzymi oknami —
        # okno programu i tak wstanie nad nią, a potem kurtyna gaśnie
        kurtyna.raise_()
        _KURTYNA["okno"] = kurtyna
        # bezpiecznik: gdyby okno programu nigdy nie wstało, scena i tak schodzi
        QTimer.singleShot(ZYCIE_KURTYNY, lambda: zdejmij_kurtyne())
        return True
    except Exception:
        return False


def zdejmij_kurtyne(natychmiast=False):
    """Scena schodzi — wołane, gdy okno programu już stoi na ekranie."""
    kurtyna = _KURTYNA.get("okno")
    if kurtyna is None:
        return False
    if natychmiast:
        _KURTYNA["okno"] = None
        try:
            kurtyna.hide()
            kurtyna.deleteLater()
        except Exception:
            pass
        return True
    try:
        kurtyna.zgas()
    except Exception:
        _KURTYNA["okno"] = None
    return True


# ═══════════════════════════════════════════════════════════════════════
#  ROZMIAR OKNA
# ═══════════════════════════════════════════════════════════════════════
def na_caly_ekran(okno):
    """Okno powitalne zajmuje cały ekran — tak samo jak okno programu,
    które za chwilę wstanie w jego miejsce."""
    try:
        ekran = okno.screen() or QApplication.primaryScreen()
        if ekran is not None:
            okno.setGeometry(ekran.geometry())
    except Exception:
        pass
    try:
        okno.showFullScreen()
    except Exception:
        okno.show()
