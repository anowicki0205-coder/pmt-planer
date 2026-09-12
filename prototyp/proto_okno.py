# -*- coding: utf-8 -*-
"""Okno główne prototypu nowego wyglądu PMT Planera (wariant A).

Składa gotowe części w jeden klikalny ekran: szynę z ikonami, pasek górny,
taśmę miesiąca, kolumnę kart (pracownik, parametry, kompas), mapę dnia
z kartką delegacji oraz tacę dokumentów wysuwaną od dołu.

Nic tu nie jest tłumaczone słowami — są nazwy, liczby i stany.
"""
import math
import sys

from PyQt6.QtCore import (Qt, QRect, QRectF, QPointF, QTimer, QEasingCurve,
                          QPropertyAnimation, QRegularExpression, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QFontMetricsF, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPolygonF, QRadialGradient,
                         QRegularExpressionValidator)
from PyQt6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel, QLineEdit,
                             QVBoxLayout, QWidget)

import proto_styl as S
import proto_dane as D
from proto_mapa import MapaDnia, KartkaDelegacji
from proto_tasma import TasmaMiesiaca
from proto_kompas import KartaKompasu
from proto_taca import TacaDokumentow, PanelPodpisu, PanelWysylki

# ── miary układu (wprost z zatwierdzonego projektu) ───────────────────
SZYNA_W    = 72
PASEK_H    = 56
TASMA_H    = 118
MARG       = 24        # margines boczny obszaru treści
KOL_W      = 380       # kolumna kart
ODSTEP     = 16        # przerwa kolumna–mapa
ODSTEP_K   = 14        # przerwa między kartami
GORA_PRACY = PASEK_H + TASMA_H + 30
DOL_PRACY  = 16
KARTKA_W   = 342
H_STRON    = 34

ROK, MIESIAC = 2026, 9
DZIS = 11
CZAS_GENERACJI_MS = 5000
CZAS_TACY_MS = 350

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

    def _pola_zakladek(self):
        x = MARG + _szerokosc("Bilans miesiąca", 19, 700, naglowek=True) + 22
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
        sr = PASEK_H / 2.0

        S.tekst(p, MARG, sr + 7, "Bilans miesiąca", S.TEKST, 19, 700, naglowek=True)

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

        # — prawa strona —
        x = self.width() - MARG
        x -= self._awatar(p, x, sr)
        x -= 12
        x -= self._przycisk(p, x, sr, "Zgłoś błąd")
        x -= 12
        x -= self._dzwonek(p, x, sr)
        x -= 16
        napis = "Konto ważne do 31.12.2026"
        szer = _napis_prawy(p, x, sr + 5, napis, S.TEKST_2, 12, 500)
        x -= szer + 10
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(S.ZIELEN))
        p.drawEllipse(QPointF(x, sr), 3.4, 3.4)
        S.punkt_swiatla(p, QPointF(x, sr), 9, S.ZIELEN, 120)
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
        inicjaly = "".join(cz[0] for cz in D.PRACOWNIK.split()[:2]).upper()
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
    """Karta kompasu z ciaśniejszym marginesem — pełny tytuł mieści się w kolumnie 380."""

    def resizeEvent(self, zdarzenie):
        super().resizeEvent(zdarzenie)
        bok = max(90, int(min(self.height() - 26, 122)))
        self.kompas.setGeometry(10, int((self.height() - bok) / 2.0), bok, bok)


class KartaPracownika(Karta):
    def __init__(self, rodzic=None):
        super().__init__("PRACOWNIK", "z konta", rodzic)
        z = QVBoxLayout(self)
        z.setContentsMargins(18, 40, 18, 14)
        z.setSpacing(9)

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
        for nazwa in self.pozycje:
            szer = _szerokosc(nazwa, self._rozmiar, 600) + 24
            pola.append(QRectF(x, r.y(), szer, r.height()))
            x += szer + 8
        return pola

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
            szer = _szerokosc(napis, self._rozmiar, 600 if czynna else 500)
            S.tekst(p, pole.center().x() - szer / 2.0, pole.center().y() + 5,
                    napis, kolor, self._rozmiar, 600 if czynna else 500)
        p.end()


class PoleKwoty(QWidget):
    """Duże pole kwoty: cyfry, grosze i krótka nota po prawej."""

    zmieniono = pyqtSignal()
    zatwierdzono = pyqtSignal()

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setMinimumHeight(48)
        self._font_kwoty = S.czcionka(31, 700, naglowek=True)
        self.pole = QLineEdit(self)
        self.pole.setFrame(False)
        self.pole.setFont(self._font_kwoty)
        self.pole.setStyleSheet(
            "QLineEdit { background: transparent; border: none; padding: 0px;"
            " font-family: '%s'; font-size: 31px; font-weight: 700;"
            " color: %s; selection-background-color: rgba(0,240,255,0.30); }"
            % (S.rodzina_naglowek(), S.CYJAN.name()))
        self.pole.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"[0-9 ]{0,9}(,[0-9]{0,2})?")))
        self.pole.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.pole.textChanged.connect(self._na_zmiane)
        self.pole.returnPressed.connect(self.zatwierdzono.emit)

        self.l_grosze = QLabel(",00 zł", self)
        self.l_grosze.setFont(S.czcionka(15, 600))
        self.l_grosze.setStyleSheet("color: %s; background: transparent;"
                                    " font-size: 15px; font-weight: 600;" % S.TEKST_2.name())
        self.l_nota = QLabel("", self)
        self.l_nota.setFont(S.czcionka(11, 500))
        self.l_nota.setStyleSheet("color: %s; background: transparent; font-size: 11px;"
                                  % S.TEKST_3.name())
        self.l_nota.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def tekst(self):
        return self.pole.text()

    def ustaw_tekst(self, napis):
        self.pole.setText(napis)

    def ustaw_note(self, napis):
        self.l_nota.setText(napis)
        self._uklad()

    def _na_zmiane(self, _t=None):
        self._uklad()
        self.zmieniono.emit()

    def resizeEvent(self, e):
        self._uklad()
        super().resizeEvent(e)

    def _uklad(self):
        h = self.height()
        fm = QFontMetricsF(self.pole.font())
        tresc = self.pole.text() or "0"
        szer_nota = QFontMetricsF(self.l_nota.font()).horizontalAdvance(
            self.l_nota.text()) + 6
        szer_gr = QFontMetricsF(self.l_grosze.font()).horizontalAdvance(
            self.l_grosze.text()) + 4
        wolne = max(70.0, self.width() - 36 - szer_nota - szer_gr)
        szer = max(64.0, min(fm.horizontalAdvance(tresc) + 16.0, wolne))
        wys_pola = min(h - 12, 44)
        self.pole.setGeometry(int(18), int((h - wys_pola) / 2.0), int(szer), int(wys_pola))
        self.l_grosze.setGeometry(int(18 + szer), int(h / 2.0 - 2), int(szer_gr), 20)
        self.l_nota.setGeometry(int(self.width() - 18 - szer_nota), int(h / 2.0 - 9),
                                int(szer_nota), 18)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        czynne = bool(self.pole.text().strip())
        obrys = S.z_alfa(S.CYJAN, 150 if czynne else 60)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.0, QColor(10, 24, 34, 230))
        g.setColorAt(1.0, QColor(8, 17, 27, 235))
        s = _pigulka(p, r, 12, g, obrys, 1.4)
        if czynne:
            p.save()
            p.setClipPath(s)
            rg = QRadialGradient(QPointF(r.x() + 60, r.center().y()), 130)
            rg.setColorAt(0.0, S.z_alfa(S.CYJAN, 34))
            rg.setColorAt(1.0, S.z_alfa(S.CYJAN, 0))
            p.fillRect(r, QBrush(rg))
            p.restore()
        p.end()


class WierszWolnych(QWidget):
    """Wiersz „Dni bez pracy” z listą dni wyłączonych przez użytkownika."""

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._dni = []
        self.setMinimumHeight(28)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def ustaw_dni(self, dni):
        self._dni = sorted(dni)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        _pigulka(p, r, 10, QColor(9, 16, 28, 190), S.OBRYS)
        S.tekst(p, r.x() + 14, r.center().y() + 5, "Dni bez pracy", S.TEKST_2, 12, 500)
        if self._dni:
            napis = ", ".join("%02d.%02d" % (d, MIESIAC) for d in self._dni)
            kolor = S.BURSZTYN
        else:
            napis = "brak"
            kolor = S.TEKST_3
        _napis_prawy(p, r.right() - 14, r.center().y() + 5, napis, kolor, 12, 700, mono=True)
        p.end()


class KartaParametrow(Karta):
    def __init__(self, rodzic=None):
        super().__init__("PARAMETRY", "", rodzic)
        z = QVBoxLayout(self)
        z.setContentsMargins(18, 36, 18, 14)
        z.setSpacing(12)

        self.kwota = PoleKwoty()
        self.kwota.setMinimumHeight(48)
        self.kwota.setMaximumHeight(58)
        z.addWidget(self.kwota)

        wiersz = QHBoxLayout()
        wiersz.setSpacing(10)
        self.pojemnosc = Lista()
        self.pojemnosc.addItems(["powyżej 900 cm³", "do 900 cm³", "motocykl"])
        self.pojemnosc.setMinimumHeight(30)
        self.pojemnosc.setMaximumHeight(36)
        self.pojemnosc.setFixedWidth(168)
        self.tryb = Segmentowany(["Tydzień", "Wieczory"], 0, "zlaczony")
        self.tryb.setMinimumHeight(30)
        self.tryb.setMaximumHeight(36)
        wiersz.addWidget(self.pojemnosc)
        wiersz.addWidget(self.tryb, 1)
        z.addLayout(wiersz)

        self.wolne = WierszWolnych()
        self.wolne.setMinimumHeight(28)
        self.wolne.setMaximumHeight(32)
        z.addWidget(self.wolne)
        z.addStretch(1)


# ── nakładki mapy ────────────────────────────────────────────────────
class PigulkaDnia(QWidget):
    """Nagłówek dnia leżący na mapie."""

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._glowny = ""
        self._reszta = ""
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def ustaw_tekst(self, glowny, reszta=""):
        self._glowny, self._reszta = glowny, reszta
        self.update()

    def szerokosc_tresci(self):
        return (_szerokosc(self._glowny, 13, 700, odstep=0.5)
                + _szerokosc(self._reszta, 13, 500) + 36)

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
        S.tekst(p, x, y, self._reszta, S.TEKST_2, 13, 500)
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
        self.setMinimumSize(1200, 780)
        self.setStyleSheet(arkusz())
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.dni = []
        self.dni_widoczne = []
        self._wolne = {14, 15}
        self._wybrany = 0
        self._po_generacji = False
        self._taca_widoczna = False
        self._t_gen = 0

        self._buduj()
        self._polacz()
        self._przelicz_teraz(pierwszy=True)

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

    def _polacz(self):
        self.k_parametry.kwota.zmieniono.connect(self._kwota_zmieniona)
        self.k_parametry.kwota.zatwierdzono.connect(self._enter_w_kwocie)
        self.k_parametry.tryb.wybrano.connect(lambda _n: self._przelicz_teraz())
        self.tasma.wybrano.connect(self._wybierz_dzien)
        self.tasma.przelaczono_wolny.connect(self._przelacz_wolny)
        self.mapa.klikniete_miasto.connect(self._klik_miasto)
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
    def resizeEvent(self, e):
        W, H = self.width(), self.height()
        self.szyna.setGeometry(0, 0, SZYNA_W, H)
        self.pasek.setGeometry(SZYNA_W, 0, W - SZYNA_W, PASEK_H)
        self.tasma.setGeometry(SZYNA_W, PASEK_H, W - SZYNA_W, TASMA_H)

        x0 = SZYNA_W + MARG
        y0 = GORA_PRACY
        dol = H - DOL_PRACY
        wys = dol - y0

        h_prac, h_par = 182, 211
        nadmiar = max(0, wys - 700)          # w wysokich oknach karty rosną razem
        h_prac += min(int(nadmiar * 0.20), 40)
        h_par += min(int(nadmiar * 0.25), 50)
        zapas = wys - h_prac - h_par - 2 * ODSTEP_K - 190
        if zapas < 0:
            ubytek = min(-zapas, 24)
            h_prac -= ubytek
            zapas += ubytek
        if zapas < 0:
            h_par -= min(-zapas, 27)
        h_komp = max(190, wys - h_prac - h_par - 2 * ODSTEP_K)

        self.k_pracownik.setGeometry(x0, y0, KOL_W, h_prac)
        self.k_parametry.setGeometry(x0, y0 + h_prac + ODSTEP_K, KOL_W, h_par)
        self.k_kompas.setGeometry(x0, y0 + h_prac + h_par + 2 * ODSTEP_K, KOL_W, h_komp)

        xm = x0 + KOL_W + ODSTEP
        szer_m = max(420, W - MARG - xm)
        h_mapy = max(300, wys - H_STRON)
        self.mapa.setGeometry(xm, y0, szer_m, h_mapy)
        self.strony.setGeometry(xm, y0 + h_mapy + 2, szer_m - 18, H_STRON - 4)

        szer_k = int(min(KARTKA_W, max(272, szer_m * 0.40)))
        wys_k = int(min(500, max(330, h_mapy - 108)))
        self.kartka.setGeometry(xm + szer_m - 18 - szer_k, y0 + 42, szer_k, wys_k)

        self.pigulka.setGeometry(xm + 16, y0 + 16,
                                 int(min(self.pigulka.szerokosc_tresci(), szer_m - 240)), 28)
        szer_z = int(self.zakres.szerokosc_tresci())
        self.zakres.setGeometry(xm + szer_m - 18 - szer_z, y0 + 16, szer_z, 28)

        self.taca.setGeometry(self._geometria_tacy(self._taca_widoczna))
        self._przelicz_kotwice()
        super().resizeEvent(e)

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
        t = self.k_parametry.kwota.tekst().replace(" ", "").replace(",", ".")
        try:
            return float(t) if t else 0.0
        except ValueError:
            return 0.0

    def _kwota_zmieniona(self):
        self._zegar_kwoty.start()

    def _enter_w_kwocie(self):
        self._zegar_kwoty.stop()
        self._przelicz_teraz()
        self.uruchom_pokaz()

    def _przelicz_teraz(self, pierwszy=False):
        self._zegar_kwoty.stop()
        if pierwszy:
            self.k_parametry.kwota.ustaw_tekst("1 850")
        tryb = self.k_parametry.tryb.aktywna()
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

        self.k_parametry.wolne.ustaw_dni(self._wolne)
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

    def _dzien_zbiorczy(self):
        """Sztuczny dzień z miastami całego miesiąca — widok „wszystkie dni”."""
        w_trasie = self._dni_w_trasie()
        if not w_trasie:
            return None
        kolejne = []
        for d in w_trasie:
            for m in d.przystanki:
                if m not in kolejne:
                    kolejne.append(m)
        z = D.podsumowanie(self.dni_widoczne)
        zbiorczy = D.Dzien(w_trasie[0].data, przystanki=kolejne[:9],
                           km=z["km"], kwota=z["kwota"],
                           start="06:00", koniec="20:00")
        return zbiorczy

    def _odswiez_liczby(self):
        z = D.podsumowanie(self._dni_w_trasie())
        self.k_parametry.kwota.ustaw_note("%s · realne drogi" % _dni_txt(z["dni"]))

    def _odswiez_dzien(self):
        d = self._dzien_wybrany()
        zbiorczo = (self.zakres.aktywna() == "wszystkie dni")
        self.mapa.ustaw_dzien(self._dzien_zbiorczy() if zbiorczo else d)

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

    def _odswiez_pigulke(self, d, zbiorczo):
        if zbiorczo:
            z = D.podsumowanie(self._dni_w_trasie())
            self.pigulka.ustaw_tekst(
                "%s %d" % (D.nazwa_miesiaca(MIESIAC).upper(), ROK),
                "  ·  %s  ·  %s  ·  %s km" % (_dni_txt(z["dni"]), _postoje(z["postoje"]),
                                              D.zl(z["km"], grosze=False)))
            return
        if d is None:
            self.pigulka.ustaw_tekst("", "")
            return
        glowny = "%s %02d.%02d" % (DNI_PELNE[d.data.weekday()].upper(),
                                   d.data.day, d.data.month)
        if d.wylaczony:
            reszta = "  ·  wolne"
        elif d.wolny:
            reszta = "  ·  bez trasy"
        else:
            reszta = "  ·  %s  ·  %s km  ·  %s" % (_postoje(d.postoje),
                                                   D.zl(d.km, grosze=False), _czas_dnia(d))
        self.pigulka.ustaw_tekst(glowny, reszta)

    def _uklad_pigulki(self):
        g = self.mapa.geometry()
        szer = int(min(self.pigulka.szerokosc_tresci(), g.width() - 240))
        self.pigulka.setGeometry(g.x() + 16, g.y() + 16, max(60, szer), 28)

    def _przelicz_kotwice(self):
        punkt = QPointF(self.kartka.x() - self.mapa.x() + 8,
                        self.kartka.y() - self.mapa.y() + 26)
        self.mapa.ustaw_kotwice_kartki(punkt)

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

    def zakoncz_pokaz(self, animacja=True):
        self._zegar_gen.stop()
        self._po_generacji = True
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
        podpowiedz = self.taca.sizeHint().height()
        return int(max(352, min(podpowiedz + 40, self.height() * 0.46)))

    def _geometria_tacy(self, widoczna):
        h = self._wysokosc_tacy()
        x = SZYNA_W + 16
        w = max(400, self.width() - x - 16)
        y = self.height() - h if widoczna else self.height() + 4
        return QRect(x, y, w, h)

    def _pokaz_tace(self, animacja=True):
        if not self._po_generacji:
            return
        self.taca.ustaw_dni(self.dni_widoczne)
        self._odswiez_stan_tacy()
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
        elif klucz == Qt.Key.Key_Escape:
            self._schowaj_tace()
        else:
            super().keyPressEvent(e)

    # ── zamknięcie ───────────────────────────────────────────────────
    def zamroz(self):
        """Zatrzymuje animacje — powtarzalne zrzuty i czyste wyjście."""
        self._zegar_kwoty.stop()
        self._zegar_gen.stop()
        self._zegar_stanu.stop()
        self._anim_tacy.stop()
        self._dokoncz_tace()
        self.k_kompas.zatrzymaj_animacje()

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

    for nazwa in zapisane:
        print("zapisano", nazwa)
    return 0


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(argv)
    app.setFont(S.czcionka(13))
    app.setStyleSheet(arkusz())
    okno = OknoPrototypu()
    okno.resize(1440, 900)
    okno.show()
    if "--zrzut" in argv:
        kod = _zrzuty(app, okno)
        okno.close()
        return kod
    kod = app.exec()
    okno.zamroz()          # nic nie tyka po wyjściu z pętli zdarzeń
    return kod


if __name__ == "__main__":
    sys.exit(main())
