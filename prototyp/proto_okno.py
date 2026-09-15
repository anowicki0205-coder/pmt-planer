# -*- coding: utf-8 -*-
"""Okno główne prototypu nowego wyglądu PMT Planera (wariant A).

Składa gotowe części w jeden klikalny ekran: szynę z ikonami, pasek górny,
taśmę miesiąca, kolumnę kart (pracownik, parametry, kompas), mapę dnia
z kartką delegacji oraz tacę dokumentów wysuwaną od dołu.

Nic tu nie jest tłumaczone słowami — są nazwy, liczby i stany.
"""
import calendar
import datetime
import math
import sys

from PyQt6.QtCore import (Qt, QRect, QRectF, QPointF, QTimer, QEasingCurve,
                          QPropertyAnimation, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QFontMetricsF, QKeySequence, QLinearGradient,
                         QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient,
                         QShortcut)
from PyQt6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QLayout,
                             QLineEdit, QVBoxLayout, QWidget)

import proto_styl as S
import proto_dane as D
from proto_mapa import MapaDnia, KartkaDelegacji
from proto_tasma import TasmaMiesiaca
from proto_kompas import KartaKompasu
from proto_taca import (TacaDokumentow, Panel, PanelPodpisu, PanelWysylki,
                        Przycisk)

# ── miary układu (wprost z zatwierdzonego projektu) ───────────────────
SZYNA_W    = 72
PASEK_H    = 56
TASMA_H    = 118       # taśma w oknie szerokim
TASMA_H_MIN = 92       # taśma w oknie ciasnym
MARG       = 24        # margines boczny obszaru treści
MARG_MIN   = 14
KOL_W      = 380       # kolumna kart
KOL_W_MIN  = 300       # kolumna zwęża się pierwsza, aż do tej granicy
ODSTEP     = 16        # przerwa kolumna–mapa
ODSTEP_MIN = 12
ODSTEP_K   = 14        # przerwa między kartami
ODSTEP_K_MIN = 9
PRZERWA_GORA = 30      # taśma–karty
PRZERWA_GORA_MIN = 12
DOL_PRACY  = 16
DOL_PRACY_MIN = 10
KARTKA_W   = 342
H_STRON    = 34
H_STRON_MIN = 28
MAPA_W_MIN = 360

ROZMIAR_DOCELOWY = (1440, 900)   # rozmiar startowy, gdy ekran na to pozwala
ROZMIAR_MIN      = (1040, 660)
UDZIAL_EKRANU    = 0.90
PROG_WASKI       = 1240          # poniżej tej szerokości zwęża się kolumna
PROG_NISKI       = 820           # poniżej tej wysokości kurczą się odstępy

ROK, MIESIAC = 2026, 9
DZIS = 11
CZAS_GENERACJI_MS = 5000
CZAS_TACY_MS = 350

LIMITY_DNIA = (D.MAX_KWOTA_DNIA, 999.00)

# sterowanie oknem w pasku górnym (okno nie ma ramy systemowej)
PRZYCISK_OKNA_W = 30
PRZYCISK_OKNA_H = 28

DNI_PELNE = ["poniedziałek", "wtorek", "środa", "czwartek",
             "piątek", "sobota", "niedziela"]

ETAPY = ("dane", "trasy", "PDF", "mapa")
PROGI = (0.22, 0.62, 0.86, 1.01)     # koniec kolejnych etapów


def _postoje(n):
    if n == 1:
        return "1 postój"
    r, s = n % 10, n % 100
    if 2 <= r <= 4 and not (12 <= s <= 14):
        return "%d postoje" % n
    return "%d postojów" % n


def _dni_txt(n):
    if n == 1:
        return "1 dzień"
    return "%d dni" % n


def _czas_dnia(dzien):
    try:
        a = dzien.start.split(":")
        b = dzien.koniec.split(":")
        m = (int(b[0]) * 60 + int(b[1])) - (int(a[0]) * 60 + int(a[1]))
    except Exception:
        return ""
    m = max(0, m)
    return "%d h %02d" % (m // 60, m % 60)


def _azymut(skad, dokad):
    ax, ay = D.MIASTA.get(skad, (0.5, 0.5))
    bx, by = D.MIASTA.get(dokad, (0.5, 0.5))
    return math.degrees(math.atan2(bx - ax, ay - by)) % 360.0


def _napis_prawy(p, prawy, y, napis, kolor, rozmiar, waga=400,
                 mono=False, naglowek=False, odstep=0.0):
    f = S.czcionka(rozmiar, waga, mono, naglowek, odstep)
    szer = QFontMetricsF(f).horizontalAdvance(napis)
    S.tekst(p, prawy - szer, y, napis, kolor, rozmiar, waga, mono, naglowek, odstep)
    return szer


def _szerokosc(napis, rozmiar, waga=400, mono=False, naglowek=False, odstep=0.0):
    f = S.czcionka(rozmiar, waga, mono, naglowek, odstep)
    return QFontMetricsF(f).horizontalAdvance(napis)


def arkusz():
    """qss() bez narzuconego rozmiaru czcionki — inaczej arkusz zjada setFont()
    w gotowych częściach (tytuł tacy, liczby, plakietki)."""
    tresc = S.qss()
    poczatek = tresc.find("QWidget {")
    if poczatek >= 0:
        koniec = tresc.find("}", poczatek)
        if koniec > poczatek:
            tresc = (tresc[:poczatek] + "QWidget { color: %s; }" % S.TEKST.name()
                     + tresc[koniec + 1:])
    return tresc


def _wciecie_pola(w, wysokosc):
    """Wcięcie pola dobrane do jego wysokości.

    Arkusz stylów daje 9 px z każdej strony — w niskim oknie pole ma 27 px
    i tekst zostałby przycięty przy dolnej krawędzi."""
    pad = max(2, min(9, int((wysokosc - 20) / 2)))
    if getattr(w, "_wciecie", None) == pad:
        return
    w._wciecie = pad
    rodzaj = "QComboBox" if isinstance(w, QComboBox) else "QLineEdit"
    w.setStyleSheet("%s { padding: %dpx 12px; }" % (rodzaj, pad))


def _pigulka(p, r, promien, wypelnienie, obrys=None, szer_obrysu=1.0):
    s = QPainterPath()
    s.addRoundedRect(r, promien, promien)
    p.fillPath(s, QBrush(wypelnienie))
    if obrys is not None:
        p.setPen(QPen(obrys, szer_obrysu))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)
    return s


# ── szyna z ikonami ──────────────────────────────────────────────────
class Szyna(QWidget):
    """Pionowy pasek po lewej: logo, sześć ikon działów, dwie pomocnicze."""

    IKONY = ("wykres", "kalendarz", "pinezka", "trend", "tarcza", "warstwy")
    DOLNE = ("ksiezyc", "slonce")

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setFixedWidth(SZYNA_W)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._aktywna = 0
        self._pod = -1

    # — układ —
    def _pola(self):
        return [QRectF(14, 75 + i * 50, 44, 44) for i in range(len(self.IKONY))]

    def _pola_dolne(self):
        return [QRectF(14, self.height() - 110 + i * 49, 44, 44)
                for i in range(len(self.DOLNE))]

    def _trafienie(self, punkt):
        for i, r in enumerate(self._pola()):
            if r.contains(punkt):
                return i
        for i, r in enumerate(self._pola_dolne()):
            if r.contains(punkt):
                return 100 + i
        return -1

    # — zdarzenia —
    def mousePressEvent(self, e):
        i = self._trafienie(e.position())
        if 0 <= i < len(self.IKONY):
            self._aktywna = i
            self.update()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        i = self._trafienie(e.position())
        if i != self._pod:
            self._pod = i
            self.setCursor(Qt.CursorShape.PointingHandCursor if i >= 0
                           else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._pod = -1
        self.update()
        super().leaveEvent(e)

    # — rysowanie —
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect())
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.0, QColor("#0A1018"))
        g.setColorAt(1.0, QColor("#080D16"))
        p.fillRect(r, QBrush(g))
        p.fillRect(QRectF(r.right() - 1, 0, 1, r.height()), S.z_alfa(QColor(255, 255, 255), 16))

        self._logo(p, QRectF(16, 14, 40, 40))

        for i, pole in enumerate(self._pola()):
            czynna = (i == self._aktywna)
            kolor = S.CYJAN if czynna else (S.TEKST_2 if i == self._pod else S.TEKST_3)
            if czynna:
                _pigulka(p, pole.adjusted(1, 1, -1, -1), 13, S.z_alfa(S.CYJAN, 26),
                         S.z_alfa(S.CYJAN, 60))
                belka = QRectF(0, pole.y() + 9, 3, pole.height() - 18)
                _pigulka(p, belka, 1.5, S.CYJAN)
                S.punkt_swiatla(p, QPointF(2, pole.center().y()), 22, S.CYJAN, 70)
            elif i == self._pod:
                _pigulka(p, pole.adjusted(1, 1, -1, -1), 13,
                         S.z_alfa(QColor(255, 255, 255), 14))
            self._ikona(p, self.IKONY[i], pole, kolor)

        for i, pole in enumerate(self._pola_dolne()):
            kolor = S.TEKST_2 if (100 + i) == self._pod else S.z_alfa(S.TEKST_3, 190)
            self._ikona(p, self.DOLNE[i], pole, kolor)
        p.end()

    def _logo(self, p, r):
        s = QPainterPath()
        s.addRoundedRect(r, 13, 13)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, QColor("#4C1D95"))
        g.setColorAt(0.55, QColor("#C026D3"))
        g.setColorAt(1.0, QColor("#F97316"))
        p.fillPath(s, QBrush(g))
        p.save()
        p.setClipPath(s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(S.z_alfa(QColor("#FDE68A"), 235)))
        p.drawEllipse(QPointF(r.center().x(), r.y() + r.height() * 0.42), 5.2, 5.2)
        gora = QPolygonF([QPointF(r.x() + 4, r.bottom() - 4),
                          QPointF(r.x() + r.width() * 0.40, r.y() + r.height() * 0.50),
                          QPointF(r.x() + r.width() * 0.62, r.bottom() - 4)])
        p.setBrush(QBrush(QColor(8, 14, 24, 220)))
        p.drawPolygon(gora)
        dol = QPolygonF([QPointF(r.x() + r.width() * 0.44, r.bottom() - 4),
                         QPointF(r.x() + r.width() * 0.72, r.y() + r.height() * 0.60),
                         QPointF(r.right() - 3, r.bottom() - 4)])
        p.setBrush(QBrush(QColor(8, 14, 24, 180)))
        p.drawPolygon(dol)
        p.restore()
        p.setPen(QPen(S.z_alfa(QColor(255, 255, 255), 46), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)

    def _ikona(self, p, rodzaj, pole, kolor):
        c = pole.center()
        pen = QPen(kolor, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        if rodzaj == "wykres":
            for i, h in enumerate((6.0, 11.0, 8.0)):
                x = c.x() - 7 + i * 7
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(kolor))
                p.drawRoundedRect(QRectF(x - 1.8, c.y() + 6 - h, 3.6, h), 1.6, 1.6)
        elif rodzaj == "kalendarz":
            r = QRectF(c.x() - 8, c.y() - 7, 16, 15)
            p.drawRoundedRect(r, 3, 3)
            p.drawLine(QPointF(r.x(), r.y() + 5), QPointF(r.right(), r.y() + 5))
            p.drawLine(QPointF(r.x() + 4.5, r.y() - 2.5), QPointF(r.x() + 4.5, r.y() + 1))
            p.drawLine(QPointF(r.right() - 4.5, r.y() - 2.5), QPointF(r.right() - 4.5, r.y() + 1))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(kolor))
            p.drawEllipse(QPointF(r.x() + 5, r.y() + 10), 1.5, 1.5)
            p.drawEllipse(QPointF(r.x() + 11, r.y() + 10), 1.5, 1.5)
        elif rodzaj == "pinezka":
            s = QPainterPath()
            s.moveTo(c.x(), c.y() + 9)
            s.cubicTo(c.x() - 9, c.y() - 1, c.x() - 7, c.y() - 9, c.x(), c.y() - 9)
            s.cubicTo(c.x() + 7, c.y() - 9, c.x() + 9, c.y() - 1, c.x(), c.y() + 9)
            p.drawPath(s)
            p.setBrush(QBrush(kolor))
            p.drawEllipse(QPointF(c.x(), c.y() - 3), 2.4, 2.4)
        elif rodzaj == "trend":
            s = QPainterPath()
            s.moveTo(c.x() - 9, c.y() + 5)
            s.lineTo(c.x() - 3, c.y() - 2)
            s.lineTo(c.x() + 1, c.y() + 2)
            s.lineTo(c.x() + 8, c.y() - 6)
            p.drawPath(s)
            p.drawLine(QPointF(c.x() + 3.5, c.y() - 6), QPointF(c.x() + 8.5, c.y() - 6))
            p.drawLine(QPointF(c.x() + 8.5, c.y() - 6), QPointF(c.x() + 8.5, c.y() - 1))
        elif rodzaj == "tarcza":
            s = QPainterPath()
            s.moveTo(c.x(), c.y() - 9)
            s.lineTo(c.x() + 8, c.y() - 5)
            s.lineTo(c.x() + 8, c.y() + 1)
            s.cubicTo(c.x() + 8, c.y() + 6, c.x() + 4, c.y() + 8, c.x(), c.y() + 9.5)
            s.cubicTo(c.x() - 4, c.y() + 8, c.x() - 8, c.y() + 6, c.x() - 8, c.y() + 1)
            s.lineTo(c.x() - 8, c.y() - 5)
            s.closeSubpath()
            p.drawPath(s)
        elif rodzaj == "warstwy":
            for dy in (-4.0, 1.0, 6.0):
                romb = QPolygonF([QPointF(c.x(), c.y() + dy - 4),
                                  QPointF(c.x() + 8.5, c.y() + dy),
                                  QPointF(c.x(), c.y() + dy + 4),
                                  QPointF(c.x() - 8.5, c.y() + dy)])
                p.drawPolygon(romb)
        elif rodzaj == "ksiezyc":
            s = QPainterPath()
            s.addEllipse(QPointF(c.x(), c.y()), 8.0, 8.0)
            w = QPainterPath()
            w.addEllipse(QPointF(c.x() + 4.5, c.y() - 3.5), 8.0, 8.0)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(kolor))
            p.drawPath(s.subtracted(w))
        elif rodzaj == "slonce":
            p.setBrush(QBrush(kolor))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(c.x(), c.y()), 4.2, 4.2)
            p.setPen(pen)
            for k in range(8):
                a = math.radians(k * 45)
                p.drawLine(QPointF(c.x() + math.cos(a) * 6.8, c.y() + math.sin(a) * 6.8),
                           QPointF(c.x() + math.cos(a) * 9.4, c.y() + math.sin(a) * 9.4))


# ── pasek górny ──────────────────────────────────────────────────────
class PasekGorny(QWidget):
    """Tytuł, zakładki miesięcy i prawa strona z kontem."""

    MIESIACE = ("sierpień", "wrzesień 2026", "październik")

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setFixedHeight(PASEK_H)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._aktywny = 1
        self._pod = -1
        self.marg = MARG
        # Napisy i stany prawej strony — ustawia je program. Wartości poniżej
        # są wyłącznie po to, żeby sam prototyp dało się uruchomić bez niego.
        self.tytul = "Bilans miesiąca"
        self.konto_napis = "Konto ważne do 31.12.2026"
        self.konto_ok = True
        self.inicjaly = ""
        self.powiadomienia = 0
        self._pola_prawe = {}      # nazwa → QRectF (wypełniane przy rysowaniu)
        self._pod_prawe = ""

    # — prawa strona: konto, dzwonek, zgłoszenie błędu, awatar —
    def pole_prawe(self, punkt):
        """Nazwa elementu prawej strony pod kursorem albo pusty napis."""
        for nazwa, pole in self._pola_prawe.items():
            if pole.contains(punkt):
                return nazwa
        return ""

    def ustaw_margines(self, marg):
        if int(marg) != self.marg:
            self.marg = int(marg)
            self.update()

    def _pola_zakladek(self):
        x = self.marg + _szerokosc(self.tytul, 19, 700, naglowek=True) + 22
        pola = []
        for nazwa in self.MIESIACE:
            szer = _szerokosc(nazwa, 13, 600) + 26
            pola.append(QRectF(x, (PASEK_H - 30) / 2.0, szer, 30))
            x += szer + 4
        return pola

    def mousePressEvent(self, e):
        for i, r in enumerate(self._pola_zakladek()):
            if r.contains(e.position()):
                self._aktywny = i
                self.update()
                break
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        i = -1
        for k, r in enumerate(self._pola_zakladek()):
            if r.contains(e.position()):
                i = k
        prawe = self.pole_prawe(e.position())
        if i != self._pod or prawe != self._pod_prawe:
            self._pod = i
            self._pod_prawe = prawe
            self.setCursor(Qt.CursorShape.PointingHandCursor if (i >= 0 or prawe)
                           else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._pod = -1
        self._pod_prawe = ""
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        sr = PASEK_H / 2.0

        self._pola_prawe = {}
        S.tekst(p, self.marg, sr + 7, self.tytul, S.TEKST, 19, 700, naglowek=True)

        pola = self._pola_zakladek()
        obwoluta = QRectF(pola[0].x() - 5, pola[0].y() - 4,
                          pola[-1].right() - pola[0].x() + 10, pola[0].height() + 8)
        _pigulka(p, obwoluta, 11, QColor(10, 17, 28, 170), S.OBRYS)
        for i, r in enumerate(pola):
            czynny = (i == self._aktywny)
            if czynny:
                _pigulka(p, r, 9, QColor(24, 40, 62, 245), S.z_alfa(S.CYJAN, 70))
            elif i == self._pod:
                _pigulka(p, r, 9, S.z_alfa(QColor(255, 255, 255), 14))
            kolor = S.TEKST if czynny else S.TEKST_3
            szer = _szerokosc(self.MIESIACE[i], 13, 600 if czynny else 500)
            S.tekst(p, r.center().x() - szer / 2.0, r.center().y() + 5,
                    self.MIESIACE[i], kolor, 13, 600 if czynny else 500)

        # — prawa strona: w ciasnym oknie znikają kolejne części, nic nie nachodzi —
        granica = pola[-1].right() + 24
        x = self.width() - self.marg
        # Okno programu nie ma ramy systemowej, więc sterowanie oknem stoi
        # tutaj — skrajnie z prawej i zawsze, także w najciaśniejszym układzie.
        for nazwa in ("zamknij", "pelny_ekran", "minimalizuj"):
            szer = self._przycisk_okna(p, x, sr, nazwa)
            self._pola_prawe[nazwa] = QRectF(x - szer, sr - PRZYCISK_OKNA_H / 2.0,
                                             szer, PRZYCISK_OKNA_H)
            x -= szer + 6
        x -= 10
        d = self._awatar(p, x, sr)
        self._pola_prawe["awatar"] = QRectF(x - d, sr - d / 2.0, d, d)
        x -= d
        x -= 12
        szer = _szerokosc("Zgłoś błąd", 13, 500) + 30
        if x - szer > granica:
            szer = self._przycisk(p, x, sr, "Zgłoś błąd")
            self._pola_prawe["blad"] = QRectF(x - szer, sr - 17, szer, 34)
            x -= szer
            x -= 12
        if x - 34 > granica:
            szer = self._dzwonek(p, x, sr)
            self._pola_prawe["dzwonek"] = QRectF(x - szer, sr - 17, szer, 34)
            x -= szer
            x -= 16
        napis = self.konto_napis
        szer = _szerokosc(napis, 12, 500) + 16
        if napis and x - szer > granica:
            kolor_k = S.ZIELEN if self.konto_ok else S.BURSZTYN
            szer = _napis_prawy(p, x, sr + 5, napis, S.TEKST_2, 12, 500)
            prawy_k = x
            x -= szer + 10
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(kolor_k))
            p.drawEllipse(QPointF(x, sr), 3.4, 3.4)
            S.punkt_swiatla(p, QPointF(x, sr), 9, kolor_k, 120)
            self._pola_prawe["konto"] = QRectF(x - 6, sr - 12,
                                               prawy_k - x + 6, 24)
        p.end()

    def _awatar(self, p, prawy, sr):
        d = 36.0
        r = QRectF(prawy - d, sr - d / 2.0, d, d)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, S.CYJAN)
        g.setColorAt(1.0, S.ZIELEN)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(r)
        zrodlo = self.inicjaly if self.inicjaly else \
            "".join(cz[0] for cz in D.PRACOWNIK.split()[:2])
        inicjaly = str(zrodlo).upper()[:2] or "?"
        szer = _szerokosc(inicjaly, 13, 700)
        S.tekst(p, r.center().x() - szer / 2.0, r.center().y() + 5, inicjaly,
                QColor("#04121A"), 13, 700)
        return d

    def _przycisk(self, p, prawy, sr, napis):
        szer = _szerokosc(napis, 13, 500) + 30
        r = QRectF(prawy - szer, sr - 17, szer, 34)
        _pigulka(p, r, 10, QColor(17, 28, 46, 200), S.OBRYS_MOCNY)
        S.tekst(p, r.center().x() - _szerokosc(napis, 13, 500) / 2.0,
                r.center().y() + 5, napis, S.TEKST, 13, 500)
        return szer

    def _przycisk_okna(self, p, prawy, sr, nazwa):
        """Sterowanie oknem bez ramy systemu: minimalizuj, pełny ekran, zamknij."""
        szer = PRZYCISK_OKNA_W
        r = QRectF(prawy - szer, sr - PRZYCISK_OKNA_H / 2.0, szer, PRZYCISK_OKNA_H)
        pod = (self._pod_prawe == nazwa)
        if nazwa == "zamknij" and pod:
            tlo, obrys, kolor = S.z_alfa(S.BLAD, 190), S.z_alfa(S.BLAD, 220), S.TEKST
        elif pod:
            tlo, obrys, kolor = QColor(30, 48, 74, 235), S.OBRYS_MOCNY, S.TEKST
        else:
            tlo, obrys, kolor = QColor(17, 28, 46, 160), S.OBRYS, S.TEKST_2
        _pigulka(p, r, 9, tlo, obrys)
        c = r.center()
        pen = QPen(kolor, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if nazwa == "minimalizuj":
            p.drawLine(QPointF(c.x() - 5.5, c.y() + 3.5), QPointF(c.x() + 5.5, c.y() + 3.5))
        elif nazwa == "zamknij":
            p.drawLine(QPointF(c.x() - 4.6, c.y() - 4.6), QPointF(c.x() + 4.6, c.y() + 4.6))
            p.drawLine(QPointF(c.x() + 4.6, c.y() - 4.6), QPointF(c.x() - 4.6, c.y() + 4.6))
        else:
            okno = self.window()
            if okno is not None and okno.isFullScreen():
                # na pełnym ekranie przycisk wraca do okna: prostokąt okna
                okienko = QPainterPath()
                okienko.addRoundedRect(QRectF(c.x() - 5.5, c.y() - 4.5, 11, 9), 2.0, 2.0)
                p.drawPath(okienko)
            else:
                # w oknie przycisk idzie na pełny ekran: rozchodzące się narożniki
                a, b = 5.4, 1.8
                for zx, zy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                    p.drawLine(QPointF(c.x() + zx * a, c.y() + zy * a),
                               QPointF(c.x() + zx * b, c.y() + zy * a))
                    p.drawLine(QPointF(c.x() + zx * a, c.y() + zy * a),
                               QPointF(c.x() + zx * a, c.y() + zy * b))
        return szer

    def _dzwonek(self, p, prawy, sr):
        szer = 34.0
        r = QRectF(prawy - szer, sr - 17, szer, 34)
        _pigulka(p, r, 10, QColor(17, 28, 46, 160), S.OBRYS)
        c = r.center()
        pen = QPen(S.TEKST_2, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        s = QPainterPath()
        s.moveTo(c.x() - 6.5, c.y() + 3.5)
        s.lineTo(c.x() - 5.2, c.y() - 1.5)
        s.cubicTo(c.x() - 4.6, c.y() - 7.5, c.x() + 4.6, c.y() - 7.5, c.x() + 5.2, c.y() - 1.5)
        s.lineTo(c.x() + 6.5, c.y() + 3.5)
        s.closeSubpath()
        p.drawPath(s)
        p.drawLine(QPointF(c.x() - 1.8, c.y() + 6), QPointF(c.x() + 1.8, c.y() + 6))
        if self.powiadomienia > 0:
            bx, by = r.right() - 7.0, r.y() + 7.0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(S.BLAD))
            p.drawEllipse(QPointF(bx, by), 7.0, 7.0)
            liczba = str(self.powiadomienia) if self.powiadomienia < 10 else "9+"
            S.tekst(p, bx - _szerokosc(liczba, 10, 700) / 2.0, by + 3.6,
                    liczba, QColor("#FFFFFF"), 10, 700)
        return szer


# ── karty ze szkła ───────────────────────────────────────────────────
class Karta(QWidget):
    def __init__(self, tytul, nota="", rodzic=None):
        super().__init__(rodzic)
        self.tytul = tytul
        self.nota = nota
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        S.cien(p, r, 18, sila=80, rozmycie=12, przesun=6)
        S.szklo(p, r, 18)
        S.tekst(p, r.x() + 18, r.y() + 26, self.tytul, S.TEKST_2, 11, 700, odstep=1.2)
        if self.nota:
            _napis_prawy(p, r.right() - 18, r.y() + 26, self.nota, S.TEKST_3, 11, 400)
        p.end()


class Lista(QComboBox):
    """Lista rozwijana z dorysowanym daszkiem — arkusz stylów nie ma obrazków."""

    def paintEvent(self, zdarzenie):
        super().paintEvent(zdarzenie)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        x = self.width() - 17.0
        y = self.height() / 2.0 - 1.0
        pen = QPen(S.TEKST_3, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        s = QPainterPath()
        s.moveTo(x - 4.0, y - 1.6)
        s.lineTo(x, y + 2.4)
        s.lineTo(x + 4.0, y - 1.6)
        p.drawPath(s)
        p.end()


class KartaKompasuOkna(KartaKompasu):
    """Karta kompasu dopasowana do kolumny.

    W kolumnie szerokiej układ zatwierdzony: kompas z lewej, tytuł i rząd
    plakietek z prawej. W kolumnie zwężonej plakietki schodzą pod spód, na
    całą szerokość karty — inaczej nie zmieściłyby się obok kompasu."""

    PROG_KOLUMNY = 348          # poniżej tej szerokości karta układa się inaczej
    WYS_PLAKIETKI = 25.0
    ROZMIARY_TYTULU = (19, 17, 15, 13)

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setMinimumSize(268, 126)
        self.kompas.setMinimumSize(64, 64)     # róża zostaje kwadratem

    def waska(self):
        return self.width() < self.PROG_KOLUMNY

    # — układ —
    def resizeEvent(self, zdarzenie):
        super().resizeEvent(zdarzenie)
        h, w = self.height(), self.width()
        if self.waska():
            pas = self.WYS_PLAKIETKI + 14.0
            bok = int(max(64, min(h - pas - 16, 116, w * 0.40)))
            gora = int(max(8, (h - pas - bok) / 2.0 + 2))
            self.kompas.setGeometry(12, gora, bok, bok)
        else:
            bok = max(90, int(min(h - 26, 122)))
            self.kompas.setGeometry(10, int((h - bok) / 2.0), bok, bok)

    def _rozmiar_tytulu(self, szer):
        for rozmiar in self.ROZMIARY_TYTULU:
            if _szerokosc(self.TYTUL, rozmiar, 700, naglowek=True) <= szer:
                return rozmiar
        return self.ROZMIARY_TYTULU[-1]

    def _uklad_plakietek(self, szer_max):
        """Dwa dodatkowe, drobniejsze stopnie — plakietki nie wychodzą poza kartę."""
        font, szerokosci, odstep, rozmiar = super()._uklad_plakietek(szer_max)
        if not szerokosci:
            return font, szerokosci, odstep, rozmiar
        if sum(szerokosci) + odstep * (len(szerokosci) - 1) <= szer_max + 0.5:
            return font, szerokosci, odstep, rozmiar
        for rozmiar2, zapas_ze, zapas_bez, odstep2 in ((9.0, 20.0, 13.0, 3.0),
                                                       (8.0, 17.0, 11.0, 2.5)):
            f = S.czcionka(rozmiar2, 600)
            metryka = QFontMetricsF(f)
            szer2 = []
            for nazwa in self.ETAPY:
                znacznik = self._etapy.get(nazwa, "czeka") in ("gotowe", "w_toku")
                szer2.append(metryka.horizontalAdvance(nazwa)
                             + (zapas_ze if znacznik else zapas_bez))
            if (sum(szer2) + odstep2 * (len(szer2) - 1) <= szer_max + 0.5
                    or rozmiar2 == 8.0):
                return f, szer2, odstep2, rozmiar2
        return font, szerokosci, odstep, rozmiar

    # — rysowanie —
    def paintEvent(self, zdarzenie):
        if not self.waska():
            super().paintEvent(zdarzenie)
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        karta = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        S.cien(p, karta, 18.0, sila=90, rozmycie=14, przesun=6)
        S.szklo(p, karta, 18.0)

        g = self.kompas.geometry()
        x = g.right() + 12.0
        szer = max(50.0, karta.right() - 14.0 - x)
        rozmiar = self._rozmiar_tytulu(szer)
        S.tekst(p, x, g.center().y() + rozmiar * 0.36, self.TYTUL,
                S.TEKST, rozmiar, 700, naglowek=True)

        y = karta.bottom() - 14.0 - self.WYS_PLAKIETKI
        self._rysuj_plakietki(p, karta.x() + 14.0, y, karta.width() - 28.0)
        p.end()


class KartaPracownika(Karta):
    def __init__(self, rodzic=None):
        super().__init__("PRACOWNIK", "z konta", rodzic)
        z = QVBoxLayout(self)
        z.setContentsMargins(18, 40, 18, 14)
        z.setSpacing(9)
        z.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self.imie = QLineEdit(D.PRACOWNIK)
        self.haslo = QLineEdit("kadry2026")
        self.haslo.setEchoMode(QLineEdit.EchoMode.Password)
        self.haslo.setFixedWidth(152)
        self.stanowisko = Lista()
        self.stanowisko.addItems([D.STANOWISKO, "przedstawiciel", "kierowca", "serwisant"])
        self.adres = QLineEdit(D.ADRES)

        for w in (self.imie, self.haslo, self.stanowisko, self.adres):
            w.setMinimumHeight(30)
            w.setMaximumHeight(36)

        z.addWidget(self.imie)
        wiersz = QHBoxLayout()
        wiersz.setSpacing(10)
        wiersz.addWidget(self.haslo)
        wiersz.addWidget(self.stanowisko, 1)
        z.addLayout(wiersz)
        z.addWidget(self.adres)

    def resizeEvent(self, e):
        """Trzy wiersze zostają zawsze — w ciasnym oknie kurczą się odstępy."""
        ciasno = self.height() < 172
        wasko = self.width() < 344
        z = self.layout()
        z.setContentsMargins(14 if wasko else 18, 32 if ciasno else 40,
                             14 if wasko else 18, 10 if ciasno else 14)
        z.setSpacing(6 if ciasno else 9)
        self.haslo.setFixedWidth(112 if wasko else 152)
        pola = (self.imie, self.haslo, self.stanowisko, self.adres)
        for w in pola:
            w.setMinimumHeight(27 if ciasno else 30)
            w.setMaximumHeight(30 if ciasno else 36)
        z.activate()
        for w in pola:
            _wciecie_pola(w, w.height())
        for w in (self.imie, self.adres):
            if not w.hasFocus():
                w.setCursorPosition(0)         # widać początek, nie koniec adresu
        super().resizeEvent(e)


class Segmentowany(QWidget):
    """Przełącznik dwóch pozycji: złączony albo dwie osobne pigułki."""

    wybrano = pyqtSignal(str)

    def __init__(self, pozycje, aktywna=0, styl="zlaczony", rozmiar=13, rodzic=None):
        super().__init__(rodzic)
        self.pozycje = list(pozycje)
        self._aktywna = int(aktywna)
        self._styl = styl
        self._rozmiar = rozmiar
        self._pod = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMinimumHeight(28)

    def aktywna(self):
        return self.pozycje[self._aktywna]

    def ustaw_aktywna(self, nazwa):
        if nazwa in self.pozycje:
            self._aktywna = self.pozycje.index(nazwa)
            self.update()

    def szerokosc_tresci(self):
        odstep = 4.0 if self._styl == "zlaczony" else 8.0
        zapas = 26.0 if self._styl == "zlaczony" else 24.0
        return sum(_szerokosc(n, self._rozmiar, 600) + zapas
                   for n in self.pozycje) + odstep * (len(self.pozycje) - 1) + 8.0

    def _pola(self):
        r = QRectF(self.rect())
        if self._styl == "zlaczony":
            wew = r.adjusted(4, 4, -4, -4)
            szer = wew.width() / len(self.pozycje)
            return [QRectF(wew.x() + i * szer, wew.y(), szer, wew.height())
                    for i in range(len(self.pozycje))]
        pola = []
        x = r.x()
        rozmiar = self._rozmiar_napisu()
        for nazwa in self.pozycje:
            szer = _szerokosc(nazwa, rozmiar, 600) + 24
            pola.append(QRectF(x, r.y(), szer, r.height()))
            x += szer + 8
        return pola

    def _rozmiar_napisu(self):
        """Napis kurczy się razem z przełącznikiem — nic nie wychodzi poza pigułkę."""
        if self._styl == "zlaczony":
            wolne = (self.width() - 8) / max(1, len(self.pozycje)) - 12
        else:
            wolne = (self.width() - 8 * (len(self.pozycje) - 1)) \
                / max(1, len(self.pozycje)) - 20
        rozmiar = self._rozmiar
        while rozmiar > 9 and max(_szerokosc(n, rozmiar, 600)
                                  for n in self.pozycje) > wolne:
            rozmiar -= 1
        return rozmiar

    def mousePressEvent(self, e):
        for i, r in enumerate(self._pola()):
            if r.contains(e.position()):
                if i != self._aktywna:
                    self._aktywna = i
                    self.update()
                    self.wybrano.emit(self.pozycje[i])
                break
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        i = -1
        for k, r in enumerate(self._pola()):
            if r.contains(e.position()):
                i = k
        if i != self._pod:
            self._pod = i
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._pod = -1
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect())
        if self._styl == "zlaczony":
            _pigulka(p, r, 10, QColor(9, 16, 28, 200), S.OBRYS)
        for i, pole in enumerate(self._pola()):
            czynna = (i == self._aktywna)
            promien = min(9.0, pole.height() / 2.0)
            if czynna:
                g = QLinearGradient(pole.topLeft(), pole.topRight())
                g.setColorAt(0.0, S.CYJAN)
                g.setColorAt(1.0, S.ZIELEN)
                _pigulka(p, pole, promien, g)
                kolor = QColor("#04121A")
            else:
                if self._styl != "zlaczony":
                    _pigulka(p, pole, promien,
                             QColor(17, 28, 46, 210 if i == self._pod else 170), S.OBRYS)
                elif i == self._pod:
                    _pigulka(p, pole, promien, S.z_alfa(QColor(255, 255, 255), 12))
                kolor = S.TEKST_2
            napis = self.pozycje[i]
            rozmiar = self._rozmiar_napisu()
            szer = _szerokosc(napis, rozmiar, 600 if czynna else 500)
            S.tekst(p, pole.center().x() - szer / 2.0,
                    pole.center().y() + 4 + rozmiar / 13.0,
                    napis, kolor, rozmiar, 600 if czynna else 500)
        p.end()


class PoleKwoty(QWidget):
    """Duże pole kwoty: złote dużą czcionką, grosze i „zł” mniejszą obok.

    To jedna liczba rysowana dwoma krojami — pole samo prowadzi kursor,
    zaznaczenie i spacje w tysiącach, więc grosze pokazują dokładnie to,
    co wpisano: „1850” → „1 850” i „,00 zł”, „1850,5” → „,50 zł”.
    """

    zmieniono = pyqtSignal()
    zatwierdzono = pyqtSignal()

    ROZMIARY = (31, 27, 24, 21)
    ROZMIAR_GROSZY = 15
    MAKS_ZLOTYCH = 9          # 999 999 999 zł — wyżej nie ma o czym mówić
    MAKS_GROSZY = 2
    MRUGANIE_MS = 530

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setMinimumHeight(44)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self._rozmiar = self.ROZMIARY[0]
        self._ostrzezenie = False
        self._tresc = ""          # same cyfry i najwyżej jeden przecinek
        self._kursor = 0
        self._kotwica = 0         # drugi koniec zaznaczenia
        self._przesun = 0.0       # przewinięcie, gdy liczba nie mieści się w polu
        self._obszar = QRectF()   # miejsce na liczbę, bez noty
        self._widac_kursor = True
        self._zegar_kursora = QTimer(self)
        self._zegar_kursora.setInterval(self.MRUGANIE_MS)
        self._zegar_kursora.timeout.connect(self._mrugnij)

        self.l_nota = QLabel("", self)
        self.l_nota.setFont(S.czcionka(11, 500))
        self.l_nota.setStyleSheet("color: %s; background: transparent; font-size: 11px;"
                                  % S.TEKST_3.name())
        self.l_nota.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    # ── treść: cyfry, jeden przecinek, dwa grosze ────────────────────
    @classmethod
    def _oczysc(cls, napis):
        """Z dowolnego napisu robi samą kwotę: „1 850,50 zł”, „1850.5”, „12,50”.

        Przecinek jest ZAWSZE znakiem dziesiętnym — tak samo, jak przy pisaniu
        w polu: „1850,555” to 1850,55 (trzecia cyfra groszy odpada, jak
        odpada przy pisaniu — nic nie dopisujemy i nie zaokrąglamy w górę),
        a nie 1 850 555 zł. Kropka jest dziesiętna, gdy stoi za przecinkiem
        („1,850.55”) albo ma za sobą jedną lub dwie cyfry („1850.5”); kropka
        z trzema cyframi i bez przecinka rozdziela tysiące („1.850”).
        Spacje, „zł”, minus i inne znaki odpadają — kwota delegacji nie bywa
        ujemna."""
        napis = str(napis or "")
        przecinek, kropka = napis.rfind(","), napis.rfind(".")
        ostatni = max(przecinek, kropka)
        if ostatni < 0:
            calosc, ulamek, dziesietny = napis, "", False
        else:
            ogon = napis[ostatni + 1:]
            po_znaku = ""
            for znak in ogon:
                if znak.isdigit():
                    po_znaku += znak
                else:
                    break
            tysiace = (ostatni == kropka and przecinek < 0
                       and len(po_znaku) == 3
                       and any(z.isdigit() for z in napis[:ostatni]))
            dziesietny = not tysiace
            calosc, ulamek = (napis[:ostatni], ogon) if dziesietny else (napis, "")
        zlote = "".join(z for z in calosc if z.isdigit())[:cls.MAKS_ZLOTYCH]
        grosze = "".join(z for z in ulamek if z.isdigit())[:cls.MAKS_GROSZY]
        if dziesietny and not zlote:
            zlote = "0"
        zlote = cls._bez_zer_wiodacych(zlote, dziesietny)
        return zlote + ("," + grosze if dziesietny else "")

    @staticmethod
    def _bez_zer_wiodacych(zlote, z_przecinkiem):
        """„05” to „5”, ale samo „0” zostaje zerem."""
        obciete = zlote.lstrip("0")
        if obciete:
            return obciete
        return "0" if (zlote or z_przecinkiem) else ""

    @classmethod
    def _popraw(cls, surowa, kursor):
        """Przepuszcza tylko poprawną kwotę i przesuwa kursor razem z nią."""
        wynik = ""
        nowy = int(kursor)
        zlote, grosze, po_przecinku = 0, 0, False
        for poz, znak in enumerate(str(surowa)):
            zostaje = False
            if znak.isdigit():
                if po_przecinku:
                    zostaje = grosze < cls.MAKS_GROSZY
                    grosze += 1 if zostaje else 0
                else:
                    zostaje = zlote < cls.MAKS_ZLOTYCH
                    zlote += 1 if zostaje else 0
            elif znak in ",." and not po_przecinku:
                zostaje = True
                po_przecinku = True
                znak = ","
            if zostaje:
                wynik += znak
            elif poz < kursor:
                nowy -= 1
        czesc_zl, _, czesc_gr = wynik.partition(",")
        if po_przecinku and not czesc_zl:
            czesc_zl = "0"
            nowy += 1
        obciete = cls._bez_zer_wiodacych(czesc_zl, po_przecinku)
        nowy -= min(max(0, nowy), len(czesc_zl) - len(obciete))
        wynik = obciete + ("," + czesc_gr if po_przecinku else "")
        return wynik, max(0, min(nowy, len(wynik)))

    def _zlote(self):
        return self._tresc.partition(",")[0]

    def _grosze(self):
        return self._tresc.partition(",")[2]

    @staticmethod
    def _grupy(zlote):
        """Tysiące rozdzielone spacją: „1850” → „1 850”."""
        czesci, i = [], len(zlote)
        while i > 3:
            czesci.insert(0, zlote[i - 3:i])
            i -= 3
        czesci.insert(0, zlote[:i])
        return " ".join(c for c in czesci if c)

    def zlote_napis(self):
        """Duża część kwoty — same złote, z odstępem co trzy cyfry."""
        return self._grupy(self._zlote())

    def grosze_napis(self):
        """Mała część kwoty — to, co wpisano, dopełnione do dwóch cyfr."""
        if not self._tresc:
            return ""
        return ",%s zł" % (self._grosze() + "00")[:self.MAKS_GROSZY]

    def wartosc(self):
        """Kwota co do grosza — tyle idzie do silnika."""
        if not self._tresc:
            return 0.0
        grosze = int((self._grosze() + "00")[:self.MAKS_GROSZY])
        return round(int(self._zlote() or "0") + grosze / 100.0, 2)

    def tekst(self):
        """Kwota jako napis: „1 850,55”. Puste pole daje pusty napis."""
        if not self._tresc:
            return ""
        return "%s,%s" % (self.zlote_napis(),
                          (self._grosze() + "00")[:self.MAKS_GROSZY])

    def ustaw_tekst(self, napis):
        tresc = self._oczysc(napis)
        zmiana = tresc != self._tresc
        self._tresc = tresc
        self._kursor = self._kotwica = len(tresc)
        self._przesun = 0.0
        self._widac_kursor = True
        if zmiana:
            self._na_zmiane()
        else:
            self._uklad()
            self.update()

    def ustaw_note(self, napis, ostrzezenie=False):
        ostrzezenie = bool(ostrzezenie)
        if ostrzezenie != self._ostrzezenie:
            self._ostrzezenie = ostrzezenie
            kolor = S.BURSZTYN if ostrzezenie else S.TEKST_3
            self.l_nota.setStyleSheet(
                "color: %s; background: transparent; font-size: 11px;%s"
                % (kolor.name(), " font-weight: 600;" if ostrzezenie else ""))
        self.l_nota.setText(napis)
        self._uklad()
        self.update()

    def _na_zmiane(self):
        self._uklad()
        self.update()
        self.zmieniono.emit()

    # ── zmiany treści ────────────────────────────────────────────────
    def _zakres(self):
        return min(self._kursor, self._kotwica), max(self._kursor, self._kotwica)

    def _ustaw_tresc(self, tresc, kursor):
        zmiana = tresc != self._tresc
        self._tresc = tresc
        self._kursor = self._kotwica = max(0, min(int(kursor), len(tresc)))
        self._widac_kursor = True
        if zmiana:
            self._na_zmiane()
        else:
            self._uklad()
            self.update()

    def _zloz(self, a, b, znaki=""):
        """Treść po zastąpieniu zakresu [a, b) znakami.

        Gdy z zakresu znika przecinek, znikają z nim grosze: skasowany
        przecinek ZDEJMUJE grosze („1850,55” → „1850”), a nigdy nie dokleja
        ich do złotych („185055” — stukrotny błąd jednym klawiszem). Wpisany
        w to miejsce nowy przecinek zostawia grosze groszami."""
        przed, wyciete, po = self._tresc[:a], self._tresc[a:b], self._tresc[b:]
        if "," in wyciete and not any(z in ",." for z in znaki):
            po = ""
        return przed + znaki + po

    def _wstaw(self, znaki):
        a, b = self._zakres()
        znaki = str(znaki)
        tresc, kursor = self._popraw(self._zloz(a, b, znaki), a + len(znaki))
        self._ustaw_tresc(tresc, kursor)

    def _skasuj(self, wstecz):
        a, b = self._zakres()
        if a == b:
            if wstecz and a > 0:
                a -= 1
            elif not wstecz and b < len(self._tresc):
                b += 1
            else:
                return
        tresc, kursor = self._popraw(self._zloz(a, b), a)
        self._ustaw_tresc(tresc, kursor)

    def _zaznaczone(self):
        a, b = self._zakres()
        return self._tresc[a:b]

    def _do_schowka(self):
        wybor = self._zaznaczone()
        if not wybor:
            return
        schowek = QApplication.clipboard()
        if schowek is not None:
            schowek.setText(wybor)

    def _ze_schowka(self):
        """Wklejenie: same cyfry wchodzą tam, gdzie stoi kursor — jak pisane.
        Kwota z groszami zastępuje całe pole: wstawiona w środek liczby
        robiłaby z jej cyfr grosze („12,5” w „1850,55” dawało 12,51 zł)."""
        schowek = QApplication.clipboard()
        napis = schowek.text() if schowek is not None else ""
        czysty = self._oczysc(napis)
        if not czysty:
            return
        if "," in czysty:
            self._ustaw_tresc(*self._popraw(czysty, len(czysty)))
        else:
            # same cyfry, razem z zerami wiodącymi: „07” wklejone w grosze
            # to „,07”, a nie „,70”; zbędne zera zdejmuje _popraw
            self._wstaw("".join(z for z in str(napis) if z.isdigit()))

    def zaznacz_wszystko(self):
        self._kotwica, self._kursor = 0, len(self._tresc)
        self._widac_kursor = True
        self._dopilnuj_widoku()
        self.update()

    # ── kursor ───────────────────────────────────────────────────────
    def _ustaw_kursor(self, dokad, zaznacz=False):
        self._kursor = max(0, min(int(dokad), len(self._tresc)))
        if not zaznacz:
            self._kotwica = self._kursor
        self._widac_kursor = True
        self._dopilnuj_widoku()
        self.update()

    def _mrugnij(self):
        self._widac_kursor = not self._widac_kursor
        self.update()

    def focusInEvent(self, e):
        self._widac_kursor = True
        self._zegar_kursora.start()
        if e.reason() in (Qt.FocusReason.TabFocusReason,
                          Qt.FocusReason.BacktabFocusReason,
                          Qt.FocusReason.ShortcutFocusReason):
            self.zaznacz_wszystko()
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        self._zegar_kursora.stop()
        self._widac_kursor = False
        self.update()
        super().focusOutEvent(e)

    # ── klawiatura ───────────────────────────────────────────────────
    def keyPressEvent(self, e):
        klucz = e.key()
        mod = e.modifiers()
        sterowanie = bool(mod & Qt.KeyboardModifier.ControlModifier)
        zaznacz = bool(mod & Qt.KeyboardModifier.ShiftModifier)
        a, b = self._zakres()
        if sterowanie and klucz == Qt.Key.Key_A:
            self.zaznacz_wszystko()
        elif sterowanie and klucz == Qt.Key.Key_C:
            self._do_schowka()
        elif sterowanie and klucz == Qt.Key.Key_X:
            self._do_schowka()
            if a != b:
                self._skasuj(True)
        elif sterowanie and klucz == Qt.Key.Key_V:
            self._ze_schowka()
        elif klucz in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.zatwierdzono.emit()
        elif klucz == Qt.Key.Key_Left:
            self._ustaw_kursor(self._kursor - 1 if (zaznacz or a == b) else a, zaznacz)
        elif klucz == Qt.Key.Key_Right:
            self._ustaw_kursor(self._kursor + 1 if (zaznacz or a == b) else b, zaznacz)
        elif klucz == Qt.Key.Key_Home:
            self._ustaw_kursor(0, zaznacz)
        elif klucz == Qt.Key.Key_End:
            self._ustaw_kursor(len(self._tresc), zaznacz)
        elif klucz == Qt.Key.Key_Backspace:
            self._skasuj(True)
        elif klucz == Qt.Key.Key_Delete:
            self._skasuj(False)
        else:
            znaki = "" if sterowanie else "".join(
                z for z in e.text() if z.isdigit() or z in ",.")
            if not znaki:
                e.ignore()          # Esc, F11, PageUp… należą do okna
                return
            self._wstaw(znaki)
        e.accept()

    # ── mysz ─────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(e)
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self._ustaw_kursor(self._indeks_z_x(e.position().x()), False)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            self._ustaw_kursor(self._indeks_z_x(e.position().x()), True)

    def mouseDoubleClickEvent(self, e):
        self.zaznacz_wszystko()

    # ── miary i układ ────────────────────────────────────────────────
    def _czcionka_zlotych(self, rozmiar=None):
        return S.czcionka(rozmiar or self._rozmiar, 700, naglowek=True)

    def _czcionka_groszy(self):
        return S.czcionka(self.ROZMIAR_GROSZY, 600)

    def _szer_zlotych(self):
        return QFontMetricsF(self._czcionka_zlotych()).horizontalAdvance(
            self.zlote_napis())

    def _szer_groszy(self):
        return QFontMetricsF(self._czcionka_groszy()).horizontalAdvance(
            self.grosze_napis())

    def _prefiks_zlotych(self, ile_cyfr):
        """Kawałek dużej części do wskazanej cyfry — razem z odstępem tysięcy."""
        napis = self.zlote_napis()
        if ile_cyfr >= len(self._zlote()):
            return napis
        widziane = 0
        for poz, znak in enumerate(napis):
            if znak.isdigit():
                if widziane == ile_cyfr:
                    return napis[:poz]
                widziane += 1
        return napis

    def _x_indeksu(self, i):
        """Odległość kursora od początku liczby (bez przewinięcia)."""
        zlote = self._zlote()
        fz = QFontMetricsF(self._czcionka_zlotych())
        if i <= len(zlote):
            return fz.horizontalAdvance(self._prefiks_zlotych(i))
        fg = QFontMetricsF(self._czcionka_groszy())
        ile = i - len(zlote) - 1
        return self._szer_zlotych() + fg.horizontalAdvance("," + self._grosze()[:ile])

    def _indeks_z_x(self, x):
        odleglosc = float(x) - self._obszar.x() + self._przesun
        najblizszy, roznica = 0, None
        for i in range(len(self._tresc) + 1):
            d = abs(self._x_indeksu(i) - odleglosc)
            if roznica is None or d < roznica:
                najblizszy, roznica = i, d
        return najblizszy

    def _dopilnuj_widoku(self):
        """Kursor zawsze w polu — długa liczba przewija się pod nim."""
        caly = self._szer_zlotych() + self._szer_groszy()
        wolne = self._obszar.width()
        if wolne <= 0.0 or caly <= wolne:
            self._przesun = 0.0
            return
        x = self._x_indeksu(self._kursor)
        self._przesun = min(self._przesun, x)
        self._przesun = max(self._przesun, x - wolne + 8.0)
        self._przesun = max(0.0, min(self._przesun, caly - wolne))

    def _uklad(self):
        h = self.height()
        szer_nota = QFontMetricsF(self.l_nota.font()).horizontalAdvance(
            self.l_nota.text()) + 6
        bok = 18 if self.width() >= 300 else 13
        wolne = max(60.0, self.width() - 2 * bok - szer_nota)
        szer_gr = self._szer_groszy()
        napis = self.zlote_napis() or "0"

        # liczba kurczy się razem z kartą — nie wjeżdża pod notę
        rozmiar = self.ROZMIARY[0]
        for kandydat in self.ROZMIARY:
            rozmiar = kandydat
            f = self._czcionka_zlotych(kandydat)
            if QFontMetricsF(f).horizontalAdvance(napis) + szer_gr + 14.0 <= wolne:
                break
        self._rozmiar = rozmiar
        self._obszar = QRectF(float(bok), 0.0, wolne, float(h))
        self.l_nota.setGeometry(int(self.width() - bok - szer_nota), int(h / 2.0 - 9),
                                int(szer_nota), 18)
        self._dopilnuj_widoku()

    def resizeEvent(self, e):
        self._uklad()
        super().resizeEvent(e)

    # ── rysowanie ────────────────────────────────────────────────────
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        czynne = bool(self._tresc)
        akcent = S.BURSZTYN if self._ostrzezenie else S.CYJAN
        obrys = S.z_alfa(akcent, 170 if self._ostrzezenie else (150 if czynne else 60))
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.0, QColor(10, 24, 34, 230))
        g.setColorAt(1.0, QColor(8, 17, 27, 235))
        s = _pigulka(p, r, 12, g, obrys, 1.4)
        if czynne:
            p.save()
            p.setClipPath(s)
            rg = QRadialGradient(QPointF(r.x() + 60, r.center().y()), 130)
            rg.setColorAt(0.0, S.z_alfa(akcent, 40 if self._ostrzezenie else 34))
            rg.setColorAt(1.0, S.z_alfa(akcent, 0))
            p.fillRect(r, QBrush(rg))
            p.restore()
        self._rysuj_liczbe(p)
        p.end()

    def _rysuj_liczbe(self, p):
        fz = QFontMetricsF(self._czcionka_zlotych())
        fg = QFontMetricsF(self._czcionka_groszy())
        x0 = self._obszar.x() - self._przesun
        srodek = self.height() / 2.0
        baza = srodek + (fz.ascent() - fz.descent()) / 2.0
        p.save()
        p.setClipRect(QRectF(self._obszar.x() - 2.0, 0.0,
                             self._obszar.width() + 3.0, float(self.height())))
        a, b = self._zakres()
        if a != b:
            self._rysuj_zaznaczenie(p, x0, baza, a, b, fz)
        if self._tresc:
            S.tekst(p, x0, baza, self.zlote_napis(), S.CYJAN, self._rozmiar, 700,
                    naglowek=True)
            S.tekst(p, x0 + self._szer_zlotych(), baza, self.grosze_napis(),
                    S.TEKST_2, self.ROZMIAR_GROSZY, 600)
        if self.hasFocus() and self._widac_kursor and a == b:
            w_groszach = a > len(self._zlote())
            f = fg if w_groszach else fz
            x = x0 + self._x_indeksu(a)
            p.setPen(QPen(S.CYJAN, 2.0))
            p.drawLine(QPointF(x, baza - f.ascent() * 0.94),
                       QPointF(x, baza + f.descent() * 0.9))
        p.restore()

    def _rysuj_zaznaczenie(self, p, x0, baza, a, b, fz):
        """Podkład pod zaznaczeniem — jeden pas, bo to jedna liczba."""
        x_a = x0 + self._x_indeksu(a)
        x_b = x0 + self._x_indeksu(b)
        if x_b <= x_a:
            return
        gora = baza - fz.ascent() * 0.94
        p.fillRect(QRectF(x_a, gora, x_b - x_a, baza + fz.descent() - gora),
                   QBrush(S.z_alfa(S.CYJAN, 77)))

    def hideEvent(self, e):
        self._zegar_kursora.stop()      # schowane pole nie mruga w tle
        super().hideEvent(e)


class WierszWolnych(QWidget):
    """Wiersz „Dni bez pracy”: lista dni wyłączonych i wejście do ich wyboru."""

    kliknieto = pyqtSignal()

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._dni = []
        self._miesiac = MIESIAC
        self._pod = False
        self.setMouseTracking(True)
        self.setMinimumHeight(28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def ustaw_dni(self, dni, miesiac=None):
        if miesiac:
            self._miesiac = int(miesiac)
        self._dni = sorted(int(d) for d in dni)
        self.update()

    def dni(self):
        return list(self._dni)

    # — zdarzenia —
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.kliknieto.emit()
        super().mousePressEvent(e)

    def enterEvent(self, e):
        self._pod = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._pod = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().leaveEvent(e)

    # — napis po prawej: pełna lista, a gdy nie mieści się — reszta liczbą —
    def _napis(self, zapas):
        if not self._dni:
            return "brak"
        pelny = [("%02d.%02d" % (d, self._miesiac)) for d in self._dni]
        napis = ", ".join(pelny)
        if _szerokosc(napis, 12, 700, mono=True) <= zapas:
            return napis
        for ile in range(len(pelny) - 1, 0, -1):
            proba = ", ".join(pelny[:ile]) + "  +%d" % (len(pelny) - ile)
            if _szerokosc(proba, 12, 700, mono=True) <= zapas:
                return proba
        return "%d dni" % len(pelny)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        _pigulka(p, r, 10, QColor(16, 27, 44, 225) if self._pod
                 else QColor(9, 16, 28, 190),
                 S.OBRYS_MOCNY if self._pod else S.OBRYS)
        S.tekst(p, r.x() + 14, r.center().y() + 5, "Dni bez pracy", S.TEKST_2, 12, 500)
        podpis = _szerokosc("Dni bez pracy", 12, 500)
        napis = self._napis(max(40.0, r.width() - podpis - 52))
        kolor = S.BURSZTYN if self._dni else S.TEKST_3
        prawy = r.right() - 22
        _napis_prawy(p, prawy, r.center().y() + 5, napis, kolor, 12, 700, mono=True)
        # strzałka: wiersz otwiera wybór dni
        pen = QPen(S.TEKST_3 if not self._pod else S.TEKST_2, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        sx, sy = r.right() - 13.0, r.center().y()
        p.drawLine(QPointF(sx - 2.6, sy - 3.6), QPointF(sx + 1.0, sy))
        p.drawLine(QPointF(sx + 1.0, sy), QPointF(sx - 2.6, sy + 3.6))
        p.end()


def dni_poza_tygodniem(rok, miesiac, tryb="Tydzień"):
    """Dni miesiąca bez pracy z samego kalendarza: w trybie tygodniowym
    soboty i niedziele, w wieczornym tylko niedziele. Prototyp nie zna
    świąt ani niedziel handlowych — program podstawia pełną listę
    z silnika (PMT.dni_zablokowane_miesiaca)."""
    ile = calendar.monthrange(int(rok), int(miesiac))[1]
    prog = 6 if str(tryb).lower().startswith("wiecz") else 5
    return {d for d in range(1, ile + 1)
            if datetime.date(int(rok), int(miesiac), d).weekday() >= prog}


class SiatkaDni(QWidget):
    """Kalendarz miesiąca do zaznaczania dni bez pracy — klik przełącza dzień.

    Kolumna 0 to poniedziałek: dzień wpada w kolumnę swojego ``weekday()``
    (calendar.monthrange daje dzień tygodnia pierwszego), nagłówek pn…nd
    stoi nad tymi samymi kolumnami. Dni ZABLOKOWANE (święta i dni poza
    tygodniem roboczym w danym trybie) nie są do wyboru: wygaszone, bez
    pigułki, z cienką kreską zamiast dna — klik w nie nic nie robi."""

    SKROTY = ("pn", "wt", "śr", "cz", "pt", "sb", "nd")
    KOMORKA = 38.0
    ODSTEP = 6.0
    NAGLOWEK = 22.0

    zmieniono = pyqtSignal()

    def __init__(self, rok=ROK, miesiac=MIESIAC, wybrane=(), rodzic=None,
                 zablokowane=()):
        super().__init__(rodzic)
        self._pod = 0
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ustaw(rok, miesiac, wybrane, zablokowane)

    # — stan —
    def ustaw(self, rok, miesiac, wybrane=(), zablokowane=()):
        self.rok = int(rok)
        self.miesiac = int(miesiac)
        self.ile_dni = calendar.monthrange(self.rok, self.miesiac)[1]
        self.pierwszy = calendar.monthrange(self.rok, self.miesiac)[0]
        self.zablokowane = {int(d) for d in zablokowane if 1 <= int(d) <= self.ile_dni}
        self.wybrane = {int(d) for d in wybrane
                        if 1 <= int(d) <= self.ile_dni and int(d) not in self.zablokowane}
        self._wiersze = int(math.ceil((self.pierwszy + self.ile_dni) / 7.0))
        self.setMinimumHeight(int(self.NAGLOWEK + self._wiersze * self.KOMORKA
                                  + (self._wiersze - 1) * self.ODSTEP + 6))
        self.setMinimumWidth(int(7 * self.KOMORKA + 6 * self.ODSTEP))
        self.update()

    def wyczysc(self):
        if self.wybrane:
            self.wybrane = set()
            self.update()
            self.zmieniono.emit()

    # — układ —
    def _siatka(self):
        """Pole rysowania jednej komórki: {numer dnia: QRectF}."""
        szer = 7 * self.KOMORKA + 6 * self.ODSTEP
        x0 = (self.width() - szer) / 2.0
        y0 = self.NAGLOWEK
        pola = {}
        for dzien in range(1, self.ile_dni + 1):
            miejsce = self.pierwszy + dzien - 1
            kol, wiersz = miejsce % 7, miejsce // 7
            pola[dzien] = QRectF(x0 + kol * (self.KOMORKA + self.ODSTEP),
                                 y0 + wiersz * (self.KOMORKA + self.ODSTEP),
                                 self.KOMORKA, self.KOMORKA)
        return pola

    def _dzien_pod(self, punkt):
        """Dzień pod punktem — zablokowany liczy się jak puste tło."""
        for dzien, pole in self._siatka().items():
            if pole.contains(punkt):
                return 0 if dzien in self.zablokowane else dzien
        return 0

    def kolumna(self, dzien):
        """Kolumna siatki (0 = pn … 6 = nd) dnia miesiąca."""
        return (self.pierwszy + int(dzien) - 1) % 7

    def zablokowany(self, dzien):
        return int(dzien) in self.zablokowane

    # — zdarzenia —
    def mousePressEvent(self, e):
        dzien = self._dzien_pod(e.position())
        if dzien:
            if dzien in self.wybrane:
                self.wybrane.discard(dzien)
            else:
                self.wybrane.add(dzien)
            self.update()
            self.zmieniono.emit()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        dzien = self._dzien_pod(e.position())
        if dzien != self._pod:
            self._pod = dzien
            self.setCursor(Qt.CursorShape.PointingHandCursor if dzien
                           else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._pod = 0
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().leaveEvent(e)

    # — rysowanie —
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        pola = self._siatka()
        szer = 7 * self.KOMORKA + 6 * self.ODSTEP
        x0 = (self.width() - szer) / 2.0
        for kol, skrot in enumerate(self.SKROTY):
            sx = x0 + kol * (self.KOMORKA + self.ODSTEP) + self.KOMORKA / 2.0
            S.tekst(p, sx - _szerokosc(skrot, 10, 700) / 2.0, self.NAGLOWEK - 8,
                    skrot, S.TEKST_3 if kol < 5 else S.z_alfa(S.TEKST_3, 150),
                    10, 700)
        for dzien, pole in pola.items():
            wybrany = dzien in self.wybrane
            weekend = (self.pierwszy + dzien - 1) % 7 >= 5
            if dzien in self.zablokowane:
                # dzień bez pracy z góry (weekend, święto): wgłębiony kafel
                # z kropkowanym obrysem — czytelnie „zablokowany", nie
                # „brakujący" — wygaszony numer, cienka kreska w miejscu dna
                # pigułki; nic do kliknięcia
                kafel = pole.adjusted(1.0, 1.0, -1.0, -1.0)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(9, 16, 28, 110)))
                p.drawRoundedRect(kafel, 11, 11)
                obrys = QPen(S.z_alfa(S.TEKST_3, 84), 1.0)
                obrys.setStyle(Qt.PenStyle.DotLine)
                p.setPen(obrys)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(kafel, 11, 11)
                napis = str(dzien)
                S.tekst(p, pole.center().x() - _szerokosc(napis, 13, 500, mono=True) / 2.0,
                        pole.center().y() + 5, napis, S.z_alfa(S.TEKST_3, 120), 13, 500, mono=True)
                p.setPen(QPen(S.z_alfa(S.TEKST_3, 70), 1.0))
                p.drawLine(QPointF(pole.center().x() - 7.0, pole.bottom() - 6.5),
                           QPointF(pole.center().x() + 7.0, pole.bottom() - 6.5))
                continue
            if wybrany:
                g = QLinearGradient(pole.topLeft(), pole.bottomRight())
                g.setColorAt(0.0, S.z_alfa(S.BURSZTYN, 70))
                g.setColorAt(1.0, S.z_alfa(S.BURSZTYN, 40))
                _pigulka(p, pole, 11, g, S.z_alfa(S.BURSZTYN, 190))
                kolor, waga = S.TEKST, 700
            else:
                _pigulka(p, pole, 11,
                         QColor(22, 36, 56, 235) if dzien == self._pod
                         else QColor(12, 21, 35, 200),
                         S.OBRYS_MOCNY if dzien == self._pod else S.OBRYS)
                kolor = S.TEKST_2 if not weekend else S.TEKST_3
                waga = 600
            napis = str(dzien)
            S.tekst(p, pole.center().x() - _szerokosc(napis, 13, waga, mono=True) / 2.0,
                    pole.center().y() + 5, napis, kolor, 13, waga, mono=True)
        p.end()


class PanelDniBezPracy(Panel):
    """Wybór dni bez pracy — kalendarz miesiąca w materiale nowego systemu.
    ``zablokowane`` to dni, których nie ma co wybierać (święta, dni poza
    tygodniem roboczym) — siatka pokazuje je wygaszone i nie przyjmuje kliknięć."""

    def __init__(self, rok=ROK, miesiac=MIESIAC, wybrane=(), rodzic=None,
                 zablokowane=()):
        super().__init__("Dni bez pracy",
                         "%s %d" % (D.nazwa_miesiaca(miesiac), int(rok)), rodzic)
        self.setMinimumWidth(430)
        self.siatka = SiatkaDni(rok, miesiac, wybrane, self, zablokowane)
        self.siatka.zmieniono.connect(self._odswiez)
        self.z.addWidget(self.siatka)
        self.z.addSpacing(4)
        self.l_stan, self.l_licznik = self.wiersz_stanu("wybrane", "0")

        self.b_wyczysc = Przycisk("Wyczyść", "zwykly", 13, self)
        self.b_wyczysc.clicked.connect(self.siatka.wyczysc)
        self.b_gotowe = Przycisk("Gotowe", "glowny", 13, self)
        self.b_gotowe.setAutoDefault(True)
        self.b_gotowe.setDefault(True)
        self.b_gotowe.clicked.connect(self.accept)
        self.stopka(self.b_wyczysc, self.b_gotowe)
        self._odswiez()

    def _odswiez(self):
        self.l_licznik.setText(str(len(self.siatka.wybrane)))

    def dni(self):
        return set(self.siatka.wybrane)


class KartaParametrow(Karta):

    POJEMNOSCI = ("powyżej 900 cm³", "do 900 cm³", "motocykl")
    POJEMNOSCI_KROTKIE = ("> 900 cm³", "do 900 cm³", "motocykl")

    def __init__(self, rodzic=None):
        super().__init__("PARAMETRY", "", rodzic)
        z = QVBoxLayout(self)
        z.setContentsMargins(18, 36, 18, 14)
        z.setSpacing(12)
        z.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self.kwota = PoleKwoty()
        self.kwota.setMinimumHeight(44)
        self.kwota.setMaximumHeight(58)
        z.addWidget(self.kwota)

        wiersz = QHBoxLayout()
        wiersz.setSpacing(10)
        self.pojemnosc = Lista()
        self._krotkie = False
        self.pojemnosc.addItems(self.POJEMNOSCI)
        self.pojemnosc.setMinimumHeight(28)
        self.pojemnosc.setMaximumHeight(36)
        self.pojemnosc.setFixedWidth(168)
        self.tryb = Segmentowany(["Tydzień", "Wieczory"], 0, "zlaczony")
        self.tryb.setMinimumHeight(28)
        self.tryb.setMaximumHeight(36)
        wiersz.addWidget(self.pojemnosc)
        wiersz.addWidget(self.tryb, 1)
        z.addLayout(wiersz)

        # Limit dnia jest regułą silnika, nie ustawieniem użytkownika —
        # w karcie parametrów go nie ma.
        self.wolne = WierszWolnych()
        self.wolne.setMinimumHeight(28)
        self.wolne.setMaximumHeight(34)
        z.addWidget(self.wolne)
        z.addStretch(1)

    def _ustaw_pojemnosci(self, krotkie):
        """W wąskiej kolumnie pozycje mają krótsze nazwy — nic nie jest ucinane."""
        if krotkie == self._krotkie:
            return
        self._krotkie = krotkie
        i = max(0, self.pojemnosc.currentIndex())
        self.pojemnosc.blockSignals(True)
        self.pojemnosc.clear()
        self.pojemnosc.addItems(self.POJEMNOSCI_KROTKIE if krotkie else self.POJEMNOSCI)
        self.pojemnosc.setCurrentIndex(i)
        self.pojemnosc.blockSignals(False)

    def resizeEvent(self, e):
        """Karta sama się kurczy — w niskim oknie schodzą odstępy, nie treść."""
        ciasno = self.height() < 186
        wasko = self.width() < 344
        z = self.layout()
        z.setContentsMargins(14 if wasko else 18, 30 if ciasno else 36,
                             14 if wasko else 18, 10 if ciasno else 14)
        z.setSpacing(8 if ciasno else 12)
        self.kwota.setMaximumHeight(46 if ciasno else 58)
        self._ustaw_pojemnosci(wasko)
        self.pojemnosc.setFixedWidth(132 if wasko else 168)
        for w in (self.pojemnosc, self.tryb):
            w.setMaximumHeight(28 if ciasno else 36)
        self.wolne.setMaximumHeight(28 if ciasno else 34)
        z.activate()
        _wciecie_pola(self.pojemnosc, self.pojemnosc.height())
        super().resizeEvent(e)


# ── nakładki mapy ────────────────────────────────────────────────────
class PigulkaDnia(QWidget):
    """Nagłówek dnia leżący na mapie.

    Treść jest podzielona na człony; w wąskim oknie odpadają kolejne od końca,
    zamiast wyjeżdżać poza pigułkę."""

    LACZNIK = "  ·  "

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._glowny = ""
        self._czesci = []
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def ustaw_tekst(self, glowny, czesci=()):
        if isinstance(czesci, str):
            czesci = [c for c in czesci.split(self.LACZNIK) if c]
        self._glowny = glowny
        self._czesci = list(czesci)
        self.update()

    def _reszta(self, ile=None):
        czesci = self._czesci if ile is None else self._czesci[:ile]
        return "".join(self.LACZNIK + c for c in czesci)

    def szerokosc_tresci(self, ile=None):
        return (_szerokosc(self._glowny, 13, 700, odstep=0.5)
                + _szerokosc(self._reszta(ile), 13, 500) + 36)

    def _ile_miesci(self):
        for ile in range(len(self._czesci), -1, -1):
            if self.szerokosc_tresci(ile) <= self.width() + 0.5 or ile == 0:
                return ile
        return 0

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        _pigulka(p, r, r.height() / 2.0, QColor(11, 21, 34, 226), S.z_alfa(S.CYJAN, 70))
        x = r.x() + 18
        y = r.center().y() + 5
        S.tekst(p, x, y, self._glowny, S.CYJAN, 13, 700, odstep=0.5)
        x += _szerokosc(self._glowny, 13, 700, odstep=0.5)
        S.tekst(p, x, y, self._reszta(self._ile_miesci()), S.TEKST_2, 13, 500)
        p.end()


class PasekStron(QWidget):
    """Stronicowanie kartki: poprzednia, licznik, następna."""

    poprzedni = pyqtSignal()
    nastepny = pyqtSignal()

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._indeks = 0
        self._ile = 0
        self._lewy = ""
        self._prawy = ""
        self._pod = -1
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def ustaw(self, indeks, ile, lewy, prawy):
        self._indeks, self._ile = indeks, ile
        self._lewy, self._prawy = lewy, prawy
        self.update()

    def _pola(self):
        r = QRectF(self.rect())
        h = min(26.0, r.height())
        y = r.center().y() - h / 2.0
        szer_l = _szerokosc("‹ " + (self._lewy or "—"), 11, 600, mono=True) + 20
        szer_s = _szerokosc(self._licznik(), 11, 600, mono=True) + 22
        szer_p = _szerokosc((self._prawy or "—") + " ›", 11, 600, mono=True) + 20
        x = r.right() - szer_p
        prawy = QRectF(x, y, szer_p, h)
        x -= szer_s + 8
        srodek = QRectF(x, y, szer_s, h)
        x -= szer_l + 8
        lewy = QRectF(x, y, szer_l, h)
        return [lewy, srodek, prawy]

    def _licznik(self):
        return "%d z %d" % (self._indeks + 1, self._ile) if self._ile else "0 z 0"

    def mousePressEvent(self, e):
        pola = self._pola()
        if pola[0].contains(e.position()):
            self.poprzedni.emit()
        elif pola[2].contains(e.position()):
            self.nastepny.emit()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        i = -1
        for k, r in enumerate(self._pola()):
            if r.contains(e.position()) and k != 1:
                i = k
        if i != self._pod:
            self._pod = i
            self.setCursor(Qt.CursorShape.PointingHandCursor if i >= 0
                           else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._pod = -1
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        pola = self._pola()
        napisy = ["‹ " + (self._lewy or "—"), self._licznik(), (self._prawy or "—") + " ›"]
        for i, r in enumerate(pola):
            tlo = QColor(17, 28, 46, 225 if i == self._pod else 185)
            _pigulka(p, r, 9, tlo, S.OBRYS if i != 1 else S.z_alfa(S.CYJAN, 60))
            kolor = S.TEKST if i == 1 else S.TEKST_2
            szer = _szerokosc(napisy[i], 11, 600, mono=True)
            S.tekst(p, r.center().x() - szer / 2.0, r.center().y() + 4,
                    napisy[i], kolor, 11, 600, mono=True)
        p.end()


# ── okno główne ──────────────────────────────────────────────────────
class OknoPrototypu(QWidget):
    """Ekran główny prototypu — wszystko w jednym oknie, bez zakładek."""

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setWindowTitle("PMT Planer — prototyp wyglądu")
        self.setMinimumSize(*ROZMIAR_MIN)
        self.setStyleSheet(arkusz())
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.dni = []
        self.dni_widoczne = []
        self._wolne = {14, 15}
        self._wybrany = 0
        self._po_generacji = False
        self._taca_widoczna = False
        self._t_gen = 0
        self._limit_dnia = LIMITY_DNIA[0]
        self._maks_kwota = 0.0
        self._za_duzo = False
        self._animacje = True

        self._buduj()
        self._polacz()
        self._przelicz_teraz(pierwszy=True)

    # ── rozmiar okna ─────────────────────────────────────────────────
    def dopasuj_do_ekranu(self, docelowy=ROZMIAR_DOCELOWY):
        """Okno mieści się na ekranie: rozmiar docelowy albo 90% obszaru."""
        ekran = self.screen() or QApplication.primaryScreen()
        obszar = ekran.availableGeometry() if ekran is not None \
            else QRect(0, 0, docelowy[0], docelowy[1])

        # na małym ekranie minimum ustępuje — okno ma się zmieścić w całości
        self.setMinimumSize(min(ROZMIAR_MIN[0], obszar.width()),
                            min(ROZMIAR_MIN[1], obszar.height()))

        w = max(self.minimumWidth(),
                min(docelowy[0], int(obszar.width() * UDZIAL_EKRANU)))
        h = max(self.minimumHeight(),
                min(docelowy[1], int(obszar.height() * UDZIAL_EKRANU)))
        self.resize(w, h)
        self.move(obszar.x() + max(0, (obszar.width() - w) // 2),
                  obszar.y() + max(0, (obszar.height() - h) // 2))
        return w, h

    def przelacz_pelny_ekran(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ── budowa ───────────────────────────────────────────────────────
    def _buduj(self):
        self.szyna = Szyna(self)
        self.pasek = PasekGorny(self)
        self.tasma = TasmaMiesiaca(self)
        self.tasma.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.k_pracownik = KartaPracownika(self)
        self.k_parametry = KartaParametrow(self)
        self.k_kompas = KartaKompasuOkna(self)

        self.mapa = MapaDnia(self)
        self.mapa.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.kartka = KartkaDelegacji(self)
        self.kartka.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pigulka = PigulkaDnia(self)
        self.zakres = Segmentowany(["wszystkie dni", "ten dzień"], 1, "osobno", 12, self)
        self.strony = PasekStron(self)

        self.taca = TacaDokumentow(self)
        self.taca.hide()

        self.kartka.raise_()
        self.pigulka.raise_()
        self.zakres.raise_()
        self.taca.raise_()

        # zegary
        self._zegar_kwoty = QTimer(self)
        self._zegar_kwoty.setSingleShot(True)
        self._zegar_kwoty.setInterval(250)
        self._zegar_gen = QTimer(self)
        self._zegar_gen.setInterval(33)
        self._zegar_stanu = QTimer(self)
        self._zegar_stanu.setSingleShot(True)
        self._zegar_stanu.setInterval(2600)

        self._anim_tacy = QPropertyAnimation(self.taca, b"geometry", self)
        self._anim_tacy.setDuration(CZAS_TACY_MS)
        self._anim_tacy.setEasingCurve(QEasingCurve.Type.OutCubic)

        # pełny ekran działa także wtedy, gdy pisze się w polu kwoty
        self._skrot_pelny = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        self._skrot_pelny.setContext(Qt.ShortcutContext.WindowShortcut)
        self._skrot_pelny.activated.connect(self.przelacz_pelny_ekran)

    def _polacz(self):
        self.k_parametry.kwota.zmieniono.connect(self._kwota_zmieniona)
        self.k_parametry.kwota.zatwierdzono.connect(self._enter_w_kwocie)
        self.k_parametry.tryb.wybrano.connect(lambda _n: self._przelicz_teraz())
        self.k_parametry.wolne.kliknieto.connect(self._wybierz_dni_bez_pracy)
        self.tasma.wybrano.connect(self._wybierz_dzien)
        self.tasma.przelaczono_wolny.connect(self._przelacz_wolny)
        self.mapa.klikniete_miasto.connect(self._klik_miasto)
        self.mapa.trasa_rysuje_sie.connect(self.kartka.ustap)
        self.mapa.trasa_gotowa.connect(self._kartka_na_miejsce)
        self.kartka.przelaczono_zwiniecie.connect(self._przelacz_zwiniecie_kartki)
        self.kartka.obecnosc_zmieniona.connect(self._obecnosc_kartki)
        self.zakres.wybrano.connect(lambda _n: self._odswiez_dzien())
        self.strony.poprzedni.connect(lambda: self._przesun_kartke(-1))
        self.strony.nastepny.connect(lambda: self._przesun_kartke(1))
        self.k_kompas.kompas.uruchom.connect(self.uruchom_pokaz)
        self.k_kompas.kompas.otworz.connect(self._pokaz_tace)
        self.taca.zwin.connect(self._schowaj_tace)
        self.taca.otworz_podpis.connect(self._panel_podpisu)
        self.taca.otworz_wysylke.connect(self._panel_wysylki)
        self.taca.otworz_wszystkie.connect(self._otworz_wszystkie)
        self._zegar_kwoty.timeout.connect(self._przelicz_teraz)
        self._zegar_gen.timeout.connect(self._tik_generacji)
        self._zegar_stanu.timeout.connect(self._odswiez_stan_tacy)

    # ── układ ────────────────────────────────────────────────────────
    def _miary(self):
        """Wszystkie miary układu liczone z rozmiaru okna — jedno miejsce.

        Ciasne okno oddaje najpierw odstępy, potem szerokość kolumny kart
        (aż do KOL_W_MIN), a mapę zwęża dopiero na końcu."""
        W, H = self.width(), self.height()
        wask = max(0.0, min(1.0, (PROG_WASKI - W) / float(PROG_WASKI - ROZMIAR_MIN[0])))
        nisk = max(0.0, min(1.0, (PROG_NISKI - H) / float(PROG_NISKI - ROZMIAR_MIN[1])))
        cias = max(wask, nisk)

        def miedzy(duza, mala, t):
            return int(round(duza - (duza - mala) * t))

        m = {"marg": miedzy(MARG, MARG_MIN, cias),
             "odstep": miedzy(ODSTEP, ODSTEP_MIN, cias),
             "odstep_k": miedzy(ODSTEP_K, ODSTEP_K_MIN, nisk),
             "tasma_h": miedzy(TASMA_H, TASMA_H_MIN, nisk),
             "przerwa": miedzy(PRZERWA_GORA, PRZERWA_GORA_MIN, nisk),
             "dol": miedzy(DOL_PRACY, DOL_PRACY_MIN, nisk),
             "h_stron": miedzy(H_STRON, H_STRON_MIN, nisk)}

        kol = max(KOL_W_MIN, min(KOL_W, KOL_W - max(0, PROG_WASKI - W)))
        dostepna = W - SZYNA_W - 2 * m["marg"] - m["odstep"]
        if dostepna - kol < MAPA_W_MIN:      # ekran mniejszy niż minimum okna
            kol = max(232, dostepna - MAPA_W_MIN)
        m["kol"] = int(kol)
        m["x0"] = SZYNA_W + m["marg"]
        m["y0"] = PASEK_H + m["tasma_h"] + m["przerwa"]
        m["wys"] = max(220, H - m["dol"] - m["y0"])
        m["xm"] = m["x0"] + m["kol"] + m["odstep"]
        m["szer_m"] = max(MAPA_W_MIN, W - m["marg"] - m["xm"])
        return m

    def _wysokosci_kart(self, wys, odstep_k):
        """Trzy karty w kolumnie: najpierw minima, nadmiar idzie do kompasu."""
        # karta parametrów jest o wiersz niższa, odkąd limit dnia zniknął
        minima = (136, 156, 142)
        cele = (182, 202, 212)
        wolne = wys - 2 * odstep_k
        if wolne < sum(minima):
            skala = wolne / float(sum(minima))
            return [max(84, int(m * skala)) for m in minima]
        udzial = min(1.0, (wolne - sum(minima)) / float(sum(cele) - sum(minima)))
        h = [int(round(mi + (ce - mi) * udzial)) for mi, ce in zip(minima, cele)]
        nadmiar = wolne - sum(h)
        if nadmiar > 0:                      # w wysokim oknie karty rosną razem
            h[0] += min(int(nadmiar * 0.12), 24)
            h[1] += min(int(nadmiar * 0.14), 26)
        # karta kompasu bierze resztę, ale nie rozciąga się bez końca —
        # w bardzo wysokim oknie zostaje margines pod kolumną
        h[2] = max(minima[2], min(wolne - h[0] - h[1], 272))
        return h

    def resizeEvent(self, e):
        W, H = self.width(), self.height()
        m = self._miary()
        self.szyna.setGeometry(0, 0, SZYNA_W, H)
        self.pasek.setGeometry(SZYNA_W, 0, W - SZYNA_W, PASEK_H)
        self.pasek.ustaw_margines(m["marg"])
        self.tasma.setGeometry(SZYNA_W, PASEK_H, W - SZYNA_W, m["tasma_h"])

        x0, y0, wys = m["x0"], m["y0"], m["wys"]
        kol, odstep_k = m["kol"], m["odstep_k"]
        h_prac, h_par, h_komp = self._wysokosci_kart(wys, odstep_k)

        self.k_pracownik.setGeometry(x0, y0, kol, h_prac)
        self.k_parametry.setGeometry(x0, y0 + h_prac + odstep_k, kol, h_par)
        self.k_kompas.setGeometry(x0, y0 + h_prac + h_par + 2 * odstep_k, kol, h_komp)

        self._uklad_mapy(m, y0, wys)
        self.taca.setGeometry(self._geometria_tacy(self._taca_widoczna))
        super().resizeEvent(e)

    def _uklad_mapy(self, m=None, y0=None, wys=None):
        """Mapa, kartka i to, co na mapie leży — w jednym miejscu.

        Osobno od ``resizeEvent``, bo zwinięcie kartki też przestawia ten układ,
        a okno wtedy nie zmienia rozmiaru.
        """
        m = m or self._miary()
        y0 = m["y0"] if y0 is None else y0
        wys = m["wys"] if wys is None else wys
        xm, szer_m = m["xm"], m["szer_m"]
        h_mapy = max(220, wys - m["h_stron"])
        self.mapa.setGeometry(xm, y0, szer_m, h_mapy)
        self.strony.setGeometry(xm, y0 + h_mapy + 2, szer_m - 18, m["h_stron"] - 4)

        gora_k = 42 if h_mapy >= 392 else 30
        # Kartka nigdy nie bierze więcej niż dwie piąte mapy: w wąskim oknie
        # zwęża się razem z nią, zamiast spychać trasę do paska przy krawędzi.
        szer_k = int(max(176, min(KARTKA_W, szer_m * 0.42)))
        wys_k = int(min(500, max(292, min(h_mapy - 108, h_mapy - gora_k - 14))))
        # ...i nigdy nie wystaje poza mapę: mapa rezerwuje jej miejsce co do
        # piksela, więc kartka wisząca poniżej dolnej krawędzi kazałaby
        # rezerwować pas, którego nie ma
        wys_k = max(120, min(wys_k, h_mapy - gora_k - 8))
        if self.kartka.zwinieta():
            szer_k = self.kartka.SZEROKOSC_ZWINIETA
        self.kartka.setGeometry(xm + szer_m - 18 - szer_k, y0 + gora_k, szer_k, wys_k)

        szer_z = int(math.ceil(min(self.zakres.szerokosc_tresci(), szer_m * 0.46)))
        self.zakres.setGeometry(xm + szer_m - 18 - szer_z, y0 + 16, szer_z, 28)
        self._uklad_pigulki()
        self._przelicz_kotwice()

    def _przelacz_zwiniecie_kartki(self, _zwinieta=False):
        """Zwinięta kartka oddaje mapie swoje miejsce — kadr liczy się od nowa."""
        self._uklad_mapy()
        self.update()

    def showEvent(self, e):
        super().showEvent(e)
        self.setFocus()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        S.tlo_sceny(p, QRectF(self.rect()))
        p.end()

    # ── dane i przeliczenia ──────────────────────────────────────────
    def _kwota(self):
        """Kwota z pola — co do grosza, prosto z wpisanych cyfr."""
        return self.k_parametry.kwota.wartosc()

    def _kwota_zmieniona(self):
        self._zegar_kwoty.start()

    def _enter_w_kwocie(self):
        self._zegar_kwoty.stop()
        self._przelicz_teraz()
        self.uruchom_pokaz()

    def _maks_miesiaca(self, tryb):
        """Górna granica kwoty: dni robocze × sufit dnia — wprost z silnika."""
        wolne = tuple(sorted(self._wolne))
        try:
            return float(D.maks_kwota_miesiaca(ROK, MIESIAC, tryb, wolne,
                                               self._limit_dnia))
        except (AttributeError, TypeError):
            return 0.0

    def _przelicz_teraz(self, pierwszy=False):
        self._zegar_kwoty.stop()
        if pierwszy:
            self.k_parametry.kwota.ustaw_tekst("1 850")
        tryb = self.k_parametry.tryb.aktywna()
        self._maks_kwota = self._maks_miesiaca(tryb)
        self._za_duzo = bool(self._maks_kwota
                             and self._kwota() > self._maks_kwota + 0.005)
        try:
            self.dni = D.oblicz_miesiac(self._kwota(), ROK, MIESIAC, tryb,
                                        wolne=tuple(sorted(self._wolne)),
                                        limit_dnia=self._limit_dnia)
        except TypeError:      # silnik bez limitu dnia — prototyp dalej działa
            self.dni = D.oblicz_miesiac(self._kwota(), ROK, MIESIAC, tryb,
                                        wolne=tuple(sorted(self._wolne)))
        if tryb == "Tydzień":
            self.dni_widoczne = [d for d in self.dni if d.data.weekday() < 5]
        else:
            self.dni_widoczne = list(self.dni)
        self.tasma.ustaw_dni(self.dni_widoczne)
        self.tasma.ustaw_dzis(DZIS)

        w_trasie = self._dni_w_trasie()
        widoczne = [d.data.day for d in self.dni_widoczne]
        if w_trasie and self._wybrany not in [d.data.day for d in w_trasie]:
            self._wybrany = w_trasie[0].data.day
        elif not w_trasie and self._wybrany not in widoczne:
            self._wybrany = widoczne[0] if widoczne else 1
        self.tasma.ustaw_wybrany(self._wybrany)

        self.k_parametry.wolne.ustaw_dni(self._wolne, self._rok_miesiac()[1])
        if self._po_generacji and not pierwszy:
            self._po_zmianie_danych()
        self._odswiez_liczby()
        self._odswiez_dzien()
        self._odswiez_stan_kompasu()
        self._zegar_kwoty.stop()      # ustawienie tekstu w polu mogło go wzbudzić

    def _dni_w_trasie(self):
        return [d for d in self.dni_widoczne if not d.wolny and not d.wylaczony]

    def _dzien(self, numer):
        for d in self.dni:
            if d.data.day == numer:
                return d
        return None

    def _dzien_wybrany(self):
        return self._dzien(self._wybrany)

    def _odswiez_liczby(self):
        z = D.podsumowanie(self._dni_w_trasie())
        if self._za_duzo:
            self.k_parametry.kwota.ustaw_note(
                "maks. %s zł" % D.zl(self._maks_kwota, grosze=False), True)
        else:
            self.k_parametry.kwota.ustaw_note("%s · realne drogi" % _dni_txt(z["dni"]))

    def _odswiez_dzien(self):
        d = self._dzien_wybrany()
        zbiorczo = (self.zakres.aktywna() == "wszystkie dni")
        # KOLEJNOŚĆ MA ZNACZENIE: mapa musi znać kartkę, ZANIM dostanie dzień.
        # Inaczej pierwszy kadr liczy się bez zarezerwowanego miejsca i trasa
        # rysuje się przez chwilę na całej mapie, żeby zaraz przeskoczyć w bok.
        self._przelicz_kotwice()
        # Widok „wszystkie dni” to kontekst miesiąca z podświetlonym dniem:
        # trasy pozostałych dni leżą pod spodem jako tło, a na wierzchu jest
        # WYBRANY dzień — mapa idzie za taśmą dokładnie tak samo jak kartka.
        # Tło idzie PRZED dniem: ziarno terenu i światło biorą się wtedy
        # z miesiąca i teren nie przelicza się dwa razy.
        self.mapa.ustaw_dni_tla(self._dni_w_trasie() if zbiorczo else None)
        self.mapa.ustaw_dzien(d)

        w_trasie = self._dni_w_trasie()
        numery = [x.data.day for x in w_trasie]
        indeks = numery.index(self._wybrany) if self._wybrany in numery else -1

        self.kartka.ustaw_dzien(d)
        self.kartka.ustaw_numer("%d/%02d/%02d" % (ROK, MIESIAC, max(1, indeks + 1)))
        if d is None or d.wolny or d.wylaczony:
            self.kartka.ustaw_stan("pusta")
        elif self._po_generacji and d.podpisany:
            self.kartka.ustaw_stan("podpisana")
        else:
            self.kartka.ustaw_stan("zwykla")

        self._odswiez_pigulke(d, zbiorczo)
        if numery:
            i = indeks if indeks >= 0 else 0
            self.strony.ustaw(i, len(numery),
                              "%02d" % numery[(i - 1) % len(numery)],
                              "%02d" % numery[(i + 1) % len(numery)])
        else:
            self.strony.ustaw(0, 0, "", "")
        self._uklad_pigulki()
        self._przelicz_kotwice()
        # choreografia dnia: kartka ustępuje, trasa rysuje się od nowa, kartka
        # wraca dopiero na sygnał mapy (patrz _kartka_na_miejsce)
        if self.mapa.rysuje_trase():
            self.kartka.ustap()
        else:
            self.kartka.wroc()

    def _kartka_na_miejsce(self):
        """Trasa dobiegła do bazy — kartka wsuwa się i łączy z nią nitką."""
        self.kartka.wroc()

    def _obecnosc_kartki(self, ile):
        """Cień kartki na mapie i nitka do trasy idą za tym, ile kartki widać."""
        self.mapa.ustaw_obecnosc_kartki(ile)

    def _odswiez_pigulke(self, d, zbiorczo):
        if zbiorczo:
            z = D.podsumowanie(self._dni_w_trasie())
            self.pigulka.ustaw_tekst(
                "%s %d" % (D.nazwa_miesiaca(MIESIAC).upper(), ROK),
                [_dni_txt(z["dni"]), _postoje(z["postoje"]),
                 "%s km" % D.zl(z["km"], grosze=False)])
            return
        if d is None:
            self.pigulka.ustaw_tekst("", [])
            return
        glowny = "%s %02d.%02d" % (DNI_PELNE[d.data.weekday()].upper(),
                                   d.data.day, d.data.month)
        if d.wylaczony:
            czesci = ["wolne"]
        elif d.wolny:
            czesci = ["bez trasy"]
        else:
            czesci = [_postoje(d.postoje), "%s km" % D.zl(d.km, grosze=False),
                      _czas_dnia(d)]
        self.pigulka.ustaw_tekst(glowny, czesci)

    def _uklad_pigulki(self):
        g = self.mapa.geometry()
        wolne = g.width() - 16 - 18 - self.zakres.width() - 14
        szer = int(math.ceil(min(self.pigulka.szerokosc_tresci(), max(90, wolne))))
        self.pigulka.setGeometry(g.x() + 16, g.y() + 16, max(90, szer), 28)
        self._podaj_zaslony()

    def _podaj_zaslony(self):
        """Mapa dostaje prostokąty widżetów, które na niej leżą.

        Pigułka dnia i przełącznik zakresu są osobnymi widżetami położonymi na
        mapie — mapa nie ma jak ich zobaczyć. Bez tej listy kadr wpuszczał pod
        nie trasę, a tabliczki miast szukały miejsca dokładnie tam, gdzie
        siedzi pigułka.
        """
        g = self.mapa.geometry()
        luz = 6
        pola = []
        for widzet in (self.pigulka, self.zakres):
            r = widzet.geometry()
            pola.append(QRectF(r.x() - g.x() - luz, r.y() - g.y() - luz,
                               r.width() + 2 * luz, r.height() + 2 * luz))
        self.mapa.ustaw_zaslony(pola)

    def _przelicz_kotwice(self):
        """Mapa dostaje prawdziwy prostokąt kartki i punkt, do którego biegnie nitka."""
        g = self.kartka.geometry()
        m = self.mapa.geometry()
        pole = QRectF(g.x() - m.x(), g.y() - m.y(), g.width(), g.height())
        self.mapa.ustaw_kotwice_kartki(
            QPointF(pole.x() + min(8.0, pole.width() * 0.3), pole.y() + 26), pole)

    # ── wybór dnia ───────────────────────────────────────────────────
    def _wybierz_dzien(self, numer):
        if not self.dni_widoczne:
            return
        self._wybrany = int(numer)
        self.tasma.ustaw_wybrany(self._wybrany)
        self._odswiez_dzien()

    def _przesun_wybor(self, krok):
        """Sąsiedni dzień z taśmy — po dniach widocznych, bez wychodzenia poza miesiąc."""
        numery = [d.data.day for d in self.dni_widoczne]
        if not numery:
            return
        if self._wybrany in numery:
            i = numery.index(self._wybrany) + krok
        else:
            i = 0 if krok > 0 else len(numery) - 1
        self._wybierz_dzien(numery[max(0, min(len(numery) - 1, i))])

    def _przesun_kartke(self, krok):
        numery = [d.data.day for d in self._dni_w_trasie()]
        if not numery:
            return
        i = numery.index(self._wybrany) if self._wybrany in numery else 0
        self._wybierz_dzien(numery[(i + krok) % len(numery)])

    def _przelacz_wolny(self, numer):
        d = self._dzien(numer)
        if d is None:
            return
        if getattr(d, "wylaczony", False):
            self._wolne.add(numer)
        else:
            self._wolne.discard(numer)
        self._przelicz_teraz()

    # ── dni bez pracy ────────────────────────────────────────────────
    def _rok_miesiac(self):
        """Miesiąc pokazywany na taśmie — program podstawia swój."""
        return ROK, MIESIAC

    def _dni_zablokowane(self, rok, miesiac):
        """Dni miesiąca, których kalendarz nie daje wybrać — z kalendarza
        i trybu pracy; program podstawia listę z silnika (ze świętami)."""
        return dni_poza_tygodniem(rok, miesiac, self.k_parametry.tryb.aktywna())

    def _wybierz_dni_bez_pracy(self):
        """Wiersz „Dni bez pracy” otwiera kalendarz miesiąca."""
        rok, miesiac = self._rok_miesiac()
        panel = PanelDniBezPracy(rok, miesiac, self._wolne, self,
                                 self._dni_zablokowane(rok, miesiac))
        panel.setStyleSheet(arkusz())
        if panel.exec() == int(1):
            self._ustaw_dni_bez_pracy(panel.dni())

    def _ustaw_dni_bez_pracy(self, dni):
        """Jedno źródło prawdy dla taśmy, wiersza i silnika."""
        rok, miesiac = self._rok_miesiac()
        ile = calendar.monthrange(int(rok), int(miesiac))[1]
        nowe = {int(d) for d in dni if 1 <= int(d) <= ile}
        if nowe == set(self._wolne):
            return
        self._wolne = nowe
        self._przelicz_teraz()

    def _klik_miasto(self, nazwa):
        for d in self._dni_w_trasie():
            if nazwa in d.przystanki or nazwa == D.BAZA:
                self._wybierz_dzien(d.data.day)
                return

    # ── kompas i pokaz generowania ───────────────────────────────────
    def _odswiez_stan_kompasu(self):
        k = self.k_kompas.kompas
        if k.stan() == "praca":
            return
        if self._kwota() < D.KWOTA_MIN or not self._dni_w_trasie():
            k.ustaw_stan("nieaktywny")
            self.k_kompas.TYTUL = "Generuj dokumenty"
            self.k_kompas.ustaw_etapy({n: "czeka" for n in ETAPY})
        elif self._za_duzo:
            k.ustaw_stan("ostrzezenie")
            # łuk pokazuje, jaka część wpisanej kwoty mieści się w miesiącu
            k.ustaw_postep(max(0.04, min(0.96, self._maks_kwota / max(1.0, self._kwota()))))
            k.setToolTip("maks. %s zł" % D.zl(self._maks_kwota, grosze=False))
            self.k_kompas.TYTUL = "Generuj dokumenty"
            self.k_kompas.ustaw_etapy({n: "czeka" for n in ETAPY})
        elif self._po_generacji:
            k.ustaw_stan("sukces")
            self.k_kompas.TYTUL = "Otwórz dokumenty"
        elif k.stan() == "zmieniono":
            self.k_kompas.TYTUL = "Generuj dokumenty"
        else:
            k.ustaw_stan("gotowy")
            self.k_kompas.TYTUL = "Generuj dokumenty"
        self.k_kompas.update()

    def _po_zmianie_danych(self):
        """Dokumenty przestały pasować do danych — cofamy ekran do stanu zwykłego."""
        self._po_generacji = False
        self.k_kompas.kompas.ustaw_stan("zmieniono")
        self.k_kompas.TYTUL = "Generuj dokumenty"
        self.k_kompas.ustaw_etapy({n: "czeka" for n in ETAPY})
        self.tasma.ustaw_stan("zwykly")
        self.mapa.ustaw_stan("zwykly")
        self._schowaj_tace()

    def uruchom_pokaz(self):
        if not self._dni_w_trasie():
            return
        if self.k_kompas.kompas.stan() == "praca":
            return
        self._po_generacji = False
        self._t_gen = 0
        self.k_kompas.TYTUL = "Generuj dokumenty"
        self.k_kompas.kompas.ustaw_stan("praca")
        self.ustaw_postep_pokazu(0.0)
        self._zegar_gen.start()

    def _tik_generacji(self):
        self._t_gen += self._zegar_gen.interval()
        t = min(1.0, self._t_gen / float(CZAS_GENERACJI_MS))
        self.ustaw_postep_pokazu(t)
        if t >= 1.0:
            self._zegar_gen.stop()
            self.zakoncz_pokaz()

    def ustaw_postep_pokazu(self, t):
        """Ustawia kompas na zadany postęp 0…1 — także poza zegarem (zrzuty)."""
        t = max(0.0, min(1.0, float(t)))
        self._tasma_w_rytm(t)
        k = self.k_kompas.kompas
        k.ustaw_postep(t)
        biezacy = 0
        for i, prog in enumerate(PROGI):
            if t < prog:
                biezacy = i
                break
        else:
            biezacy = len(ETAPY) - 1
        stany = {}
        for i, nazwa in enumerate(ETAPY):
            stany[nazwa] = "gotowe" if i < biezacy else ("w_toku" if i == biezacy else "czeka")
        self.k_kompas.ustaw_etapy(stany)
        k.ustaw_etap(ETAPY[biezacy])

        d = self._dzien_wybrany()
        trasa = d.trasa if (d is not None and not d.wolny) else []
        if ETAPY[biezacy] == "trasy" and len(trasa) >= 2:
            u = (t - 0.0) / max(0.001, PROGI[1])
            u = max(0.0, min(0.999, (u - PROGI[0] / PROGI[1]) / (1.0 - PROGI[0] / PROGI[1])))
            i = min(len(trasa) - 2, int(u * (len(trasa) - 1)))
            k.ustaw_azymut(_azymut(trasa[i], trasa[i + 1]))
            k.ustaw_etap(trasa[i + 1])
        else:
            k.ustaw_azymut(None)

    def _tasma_w_rytm(self, t):
        """Dni na taśmie zapalają się w rytm postępu — etap po etapie.

        W prototypie postęp idzie z zegara pokazu; nowy wygląd podmienia tę
        metodę na meldunki prawdziwego silnika. Rytm jest ten sam: dni
        zapalają się na etapie układania tras, klamry poleceń wyjazdu —
        dopiero wtedy, gdy powstają pliki.
        """
        if t <= 0.0:
            dni, dokumenty = 0.0, None
        elif t < PROGI[0]:
            dni, dokumenty = 0.0, None
        elif t < PROGI[1]:
            dni = (t - PROGI[0]) / max(1e-6, PROGI[1] - PROGI[0])
            dokumenty = None
        elif t < PROGI[2]:
            dni = 1.0
            dokumenty = (t - PROGI[1]) / max(1e-6, PROGI[2] - PROGI[1])
        else:
            dni, dokumenty = 1.0, 1.0
        self.tasma.ustaw_prace(dni, dokumenty)

    def zakoncz_pokaz(self, animacja=True):
        self._zegar_gen.stop()
        self._po_generacji = True
        self.tasma.ustaw_prace(None)
        k = self.k_kompas.kompas
        k.ustaw_postep(1.0)
        k.ustaw_azymut(None)
        k.ustaw_stan("sukces")
        self.k_kompas.TYTUL = "Otwórz dokumenty"
        self.k_kompas.ustaw_etapy({n: "gotowe" for n in ETAPY})
        self.k_kompas.update()
        self.tasma.ustaw_stan("po_generacji")
        self.mapa.ustaw_stan("sukces")
        self._pokaz_tace(animacja)

    # ── taca ─────────────────────────────────────────────────────────
    def _wysokosc_tacy(self):
        podpowiedz = max(self.taca.sizeHint().height(),
                         self.taca.minimumSizeHint().height())
        gorna = max(318, int(self.height() * 0.52))
        return int(max(318, min(podpowiedz + 40, gorna)))

    def _geometria_tacy(self, widoczna):
        h = self._wysokosc_tacy()
        marg = self._miary()["marg"]
        x = SZYNA_W + marg
        w = max(360, self.width() - x - marg)
        y = self.height() - h if widoczna else self.height() + 4
        return QRect(x, y, w, h)

    def _pokaz_tace(self, animacja=True):
        if not self._po_generacji:
            return
        self.taca.ustaw_dni(self.dni_widoczne)
        self._odswiez_stan_tacy()
        self._wysun_tace(animacja)

    def _wysun_tace(self, animacja=True):
        """Sam ruch tacy — bez zmiany kartek. Osobno, bo program kładzie na
        tacę także miesiące z dysku, których ten ekran nie generował."""
        self._taca_widoczna = True
        self.taca.show()
        self.taca.raise_()
        self._anim_tacy.stop()
        if animacja is True:
            self.taca.setGeometry(self._geometria_tacy(False))
            self._anim_tacy.setStartValue(self._geometria_tacy(False))
            self._anim_tacy.setEndValue(self._geometria_tacy(True))
            self._anim_tacy.start()
        else:
            self.taca.setGeometry(self._geometria_tacy(True))

    def _schowaj_tace(self):
        if not self._taca_widoczna:
            self.taca.hide()
            return
        self._taca_widoczna = False
        self._anim_tacy.stop()
        self._anim_tacy.setStartValue(self.taca.geometry())
        self._anim_tacy.setEndValue(self._geometria_tacy(False))
        try:
            self._anim_tacy.finished.disconnect()
        except TypeError:
            pass
        self._anim_tacy.finished.connect(self._po_schowaniu)
        self._anim_tacy.start()

    def _po_schowaniu(self):
        try:
            self._anim_tacy.finished.disconnect()
        except TypeError:
            pass
        if not self._taca_widoczna:
            self.taca.hide()

    def _odswiez_stan_tacy(self):
        dni = [d for d in self._dni_w_trasie() if d.podpisany]
        wszystkie = self._dni_w_trasie()
        if not wszystkie:
            self.taca.l_stan.setText("")
        elif len(dni) == len(wszystkie):
            self.taca.l_stan.setText("%d z %d podpisanych" % (len(dni), len(wszystkie)))
        elif dni:
            self.taca.l_stan.setText("%02d.%02d podpisana · pozostałe czekają"
                                     % (dni[0].data.day, MIESIAC))
        else:
            self.taca.l_stan.setText("")

    def _otworz_wszystkie(self):
        ile = len(self._dni_w_trasie()) + 1
        self.taca.l_stan.setText("otwarto %d plików PDF" % ile)
        self._zegar_stanu.start()

    def _panel_podpisu(self):
        dni = self._dni_w_trasie()
        if not dni:
            return
        panel = PanelPodpisu(dni, self)
        panel.setStyleSheet(arkusz())
        if panel.exec() == int(1):
            for d in dni:
                d.podpisany = True
            self.taca.ustaw_dni(self.dni_widoczne)
            self.tasma.ustaw_dni(self.dni_widoczne)
            self.tasma.ustaw_dzis(DZIS)
            self.tasma.ustaw_wybrany(self._wybrany)
            self._odswiez_dzien()
        self._odswiez_stan_tacy()

    def _panel_wysylki(self):
        dni = self._dni_w_trasie()
        if not dni:
            return
        panel = PanelWysylki(dni, self)
        panel.setStyleSheet(arkusz())
        panel.exec()

    # ── klawiatura ───────────────────────────────────────────────────
    def keyPressEvent(self, e):
        klucz = e.key()
        if klucz == Qt.Key.Key_Left:
            self._przesun_wybor(-1)
        elif klucz == Qt.Key.Key_Right:
            self._przesun_wybor(1)
        elif klucz in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.uruchom_pokaz()
        elif klucz == Qt.Key.Key_F11:
            self.przelacz_pelny_ekran()
        elif klucz == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self._schowaj_tace()
        else:
            super().keyPressEvent(e)

    # ── animacje i zamknięcie ────────────────────────────────────────
    def ustaw_animacje(self, wlaczone):
        """Jeden przełącznik na cały ekran — zrzuty i zamknięcie gaszą wszystko."""
        self._animacje = bool(wlaczone)
        if self._animacje:
            self.k_kompas.wznow_animacje()
            self.tasma.wznow_animacje()
            self.mapa.ustaw_animacje(True)
            self.kartka.ustaw_animacje(True)
            return
        self._zegar_kwoty.stop()
        self._zegar_gen.stop()
        self._zegar_stanu.stop()
        self._anim_tacy.stop()
        self._dokoncz_tace()
        self.k_kompas.zatrzymaj_animacje()
        self.tasma.zatrzymaj_animacje()
        self.mapa.ustaw_animacje(False)
        self.kartka.ustaw_animacje(False)
        self.taca.zatrzymaj_animacje()
        S.Plynnie.zatrzymaj_wszystkie()

    def zamroz(self):
        """Zatrzymuje animacje — powtarzalne zrzuty i czyste wyjście."""
        self.ustaw_animacje(False)

    def _dokoncz_tace(self):
        """Stawia tacę w położeniu docelowym — po przerwanej animacji."""
        self.taca.setGeometry(self._geometria_tacy(self._taca_widoczna))
        if self._taca_widoczna:
            self.taca.show()
            self.taca.raise_()
        else:
            self.taca.hide()

    def closeEvent(self, e):
        self.zamroz()
        super().closeEvent(e)


# ── uruchomienie i zrzuty ────────────────────────────────────────────
def _zrzuty(app, okno):
    def odswiez(ile=4):
        for _ in range(ile):
            app.processEvents()

    zapisane = []

    def zapisz(nazwa):
        okno.zamroz()
        odswiez()
        okno.zamroz()
        odswiez()
        okno.grab().save(nazwa)
        zapisane.append(nazwa)

    def ustaw_rozmiar(szer, wys):
        okno.setMinimumSize(min(ROZMIAR_MIN[0], szer), min(ROZMIAR_MIN[1], wys))
        okno.resize(szer, wys)
        odswiez(6)

    ustaw_rozmiar(*ROZMIAR_DOCELOWY)
    zapisz("zrzut_okno_1_start.png")

    okno.uruchom_pokaz()
    okno._zegar_gen.stop()
    okno.ustaw_postep_pokazu(0.6)
    zapisz("zrzut_okno_2_praca.png")

    okno.zakoncz_pokaz(animacja=False)
    zapisz("zrzut_okno_3_taca.png")

    okno.k_parametry.kwota.ustaw_tekst("")
    okno._przelicz_teraz()
    zapisz("zrzut_okno_4_pusto.png")

    # najciaśniejszy dopuszczalny układ — wszystko ma się mieścić
    okno.k_parametry.kwota.ustaw_tekst("1 850")
    okno._przelicz_teraz()
    ustaw_rozmiar(*ROZMIAR_MIN)
    zapisz("zrzut_okno_5_male.png")

    for nazwa in zapisane:
        print("zapisano", nazwa)
    return 0


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(argv)
    app.setFont(S.czcionka(13))
    app.setStyleSheet(arkusz())
    okno = OknoPrototypu()
    okno.dopasuj_do_ekranu()
    okno.show()
    if "--zrzut" in argv:
        kod = _zrzuty(app, okno)
        okno.close()
        return kod
    if "--pelny" in argv:
        okno.showFullScreen()
    kod = app.exec()
    okno.zamroz()          # nic nie tyka po wyjściu z pętli zdarzeń
    return kod


if __name__ == "__main__":
    sys.exit(main())
