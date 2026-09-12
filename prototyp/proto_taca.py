# -*- coding: utf-8 -*-
"""Taca gotowych dokumentów oraz panele podpisu i wysyłki.

Taca wysuwa się od dołu po wygenerowaniu i zostaje NAD programem, żeby nie
trzeba było szukać plików w folderze. Panele podpisu i wysyłki otwierają się
z tacy. Zgodnie z wolą właściciela nigdzie nie tłumaczymy działania programu —
są nazwy, liczby i stany.

Wszystko rysowane jest ręcznie (arkusz stylów rodzica potrafi zjeść setFont),
a każdy ruch da się zatrzymać: ``TacaDokumentow.zatrzymaj_animacje()`` gasi
kaskadę kartek, dochodzenie liczb i podświetlenia przycisków, panele robią to
samo przy zamknięciu.
"""
import random

from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QFontMetricsF, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap, QRadialGradient)
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QPushButton,
                             QSizePolicy, QVBoxLayout, QWidget)

import proto_styl as S
import proto_dane as D


# ── barwy papieru i druku ────────────────────────────────────────────
PAPIER_GORA   = QColor("#FFFEFA")      # cieplejsza biel
PAPIER_SRODEK = QColor("#FDFAF3")
PAPIER_DOL    = QColor("#F5F1E7")
PAPIER_BOK    = QColor("#E3DCCC")      # grubość kartki
PAPIER_SPOD   = QColor("#D2CAB8")      # kartki leżące pod spodem
ATRAMENT      = QColor("#101828")
ATRAMENT_2    = QColor("#59667E")
ATRAMENT_3    = QColor("#98A1B2")
LINIA_DRUKU   = QColor(24, 36, 60, 46)

KAFEL_W       = 168.0                  # szerokość wzorcowa kartki na tacy
KAFEL_H       = 152.0
ODSTEP_KAFLI  = 10
KASKADA_MS    = 38                     # opóźnienie kolejnej kartki
MARG_SWIATLA  = 7                      # zapas wokół przycisku na poświatę


# ── drobne pomocniki ─────────────────────────────────────────────────
def _szer(napis, rozmiar, waga=400, mono=False, naglowek=False, odstep=0.0):
    m = QFontMetricsF(S.czcionka(rozmiar, waga, mono, naglowek, odstep))
    return m.horizontalAdvance(napis)


def _miary(rozmiar, waga=400, mono=False, naglowek=False, odstep=0.0):
    return QFontMetricsF(S.czcionka(rozmiar, waga, mono, naglowek, odstep))


def _cien_miekki(p, pole, promien, przesun, rozmycie, sila, barwa=QColor(0, 0, 0), krok=2):
    """Jedna warstwa miękkiego cienia: zanik kwadratowy, krok w pikselach."""
    if rozmycie <= 0 or sila <= 0:
        return
    ile = max(1, int(rozmycie / max(1, krok)))
    for i in range(ile, 0, -1):
        odl = i * krok
        a = int(sila * (1.0 - (i - 1) / float(ile)) ** 2.2 / ile * 2.4)
        if a <= 0:
            continue
        r = pole.adjusted(-odl, -odl + przesun, odl, odl + przesun)
        s = QPainterPath()
        s.addRoundedRect(r, promien + odl, promien + odl)
        p.fillPath(s, S.z_alfa(barwa, a))


def _sciezka(r, promien):
    s = QPainterPath()
    s.addRoundedRect(r, promien, promien)
    return s


def _polecenia(n):
    """Odmiana rzeczownika przy liczbie — bez tego napis zgrzyta."""
    n = int(n)
    if n == 1:
        return "1 polecenie wyjazdu"
    r, st = n % 10, n % 100
    if 2 <= r <= 4 and not (12 <= st <= 14):
        return "%d polecenia wyjazdu" % n
    return "%d poleceń wyjazdu" % n


def _ogranicz(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def _linia_swiatla(p, x1, x2, y, kolor=S.CYJAN, sila=150, grubosc=1.2, poswiata=True):
    """Cienka krawędź światła: gradient gaśnie po bokach, pod spodem aureola."""
    if x2 - x1 < 4:
        return
    g = QLinearGradient(QPointF(x1, y), QPointF(x2, y))
    g.setColorAt(0.00, S.z_alfa(kolor, 0))
    g.setColorAt(0.18, S.z_alfa(kolor, sila * 0.55))
    g.setColorAt(0.50, S.z_alfa(kolor, sila))
    g.setColorAt(0.82, S.z_alfa(kolor, sila * 0.55))
    g.setColorAt(1.00, S.z_alfa(kolor, 0))
    if poswiata:
        for i, a in ((5.0, 0.10), (3.0, 0.18), (1.8, 0.30)):
            gg = QLinearGradient(QPointF(x1, y), QPointF(x2, y))
            gg.setColorAt(0.00, S.z_alfa(kolor, 0))
            gg.setColorAt(0.50, S.z_alfa(kolor, sila * a))
            gg.setColorAt(1.00, S.z_alfa(kolor, 0))
            p.fillRect(QRectF(x1, y - i * 0.5, x2 - x1, i), QBrush(gg))
    p.fillRect(QRectF(x1, y, x2 - x1, grubosc), QBrush(g))


# ── napis rysowany ręcznie ───────────────────────────────────────────
class Napis(QWidget):
    """Etykieta rysowana pędzlem — odporna na font-size z arkusza rodzica."""

    def __init__(self, tekst="", rozmiar=13, waga=400, kolor=None, mono=False,
                 naglowek=False, odstep=0.0, wyrownanie=Qt.AlignmentFlag.AlignLeft,
                 punkt=None, rodzic=None):
        super().__init__(rodzic)
        self._tekst = str(tekst)
        self._rozmiar = float(rozmiar)
        self._waga = int(waga)
        self._kolor = QColor(kolor) if kolor is not None else QColor(S.TEKST)
        self._mono = bool(mono)
        self._naglowek = bool(naglowek)
        self._odstep = float(odstep)
        self._wyrownanie = wyrownanie
        self._punkt = QColor(punkt) if punkt is not None else None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    # — zgodność z QLabel —
    def setText(self, tekst):
        tekst = str(tekst)
        if tekst == self._tekst:
            return
        self._tekst = tekst
        self.updateGeometry()
        self.update()

    def text(self):
        return self._tekst

    def ustaw_kolor(self, kolor):
        self._kolor = QColor(kolor)
        self.update()

    def _odstep_punktu(self):
        return 14.0 if self._punkt is not None and self._tekst else 0.0

    def sizeHint(self):
        m = _miary(self._rozmiar, self._waga, self._mono, self._naglowek, self._odstep)
        return QSize(int(m.horizontalAdvance(self._tekst) + self._odstep_punktu() + 2),
                     int(m.height() + 2))

    def minimumSizeHint(self):
        p = self.sizeHint()
        return QSize(min(p.width(), int(48 + self._odstep_punktu())), p.height())

    def paintEvent(self, _zdarzenie):
        if not self._tekst:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        m = _miary(self._rozmiar, self._waga, self._mono, self._naglowek, self._odstep)
        napis = self._tekst
        wolne = self.width() - self._odstep_punktu()
        if m.horizontalAdvance(napis) > wolne:
            napis = m.elidedText(napis, Qt.TextElideMode.ElideRight, max(8.0, wolne))
        szer = m.horizontalAdvance(napis)
        pelna = szer + self._odstep_punktu()
        if self._wyrownanie & Qt.AlignmentFlag.AlignRight:
            x = self.width() - pelna
        elif self._wyrownanie & Qt.AlignmentFlag.AlignHCenter:
            x = (self.width() - pelna) * 0.5
        else:
            x = 0.0
        y = (self.height() + m.ascent() - m.descent()) * 0.5
        if self._punkt is not None:
            sr = QPointF(x + 4.0, self.height() * 0.5)
            S.punkt_swiatla(p, sr, 7.0, self._punkt, 110)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(self._punkt))
            p.drawEllipse(sr, 3.0, 3.0)
            x += self._odstep_punktu()
        S.tekst(p, x, y, napis, self._kolor, self._rozmiar, self._waga,
                mono=self._mono, naglowek=self._naglowek, odstep=self._odstep)
        p.end()


# ── przycisk rysowany ręcznie ────────────────────────────────────────
class Przycisk(QPushButton):
    """Trzy role: zwykły (szkło), zielony (obrys gradientowy), główny (poświata)."""

    def __init__(self, tekst, rola="zwykly", rozmiar=13, rodzic=None):
        super().__init__(tekst, rodzic)
        self._rola = rola
        self._rozmiar = float(rozmiar)
        self._wysokosc = 40.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoDefault(False)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._pod = S.Plynnie(0.0, czas=170, krzywa="lagodna", rodzic=self,
                              przy_zmianie=self.update)

    def ustaw_wysokosc(self, h):
        self._wysokosc = float(h)
        self.updateGeometry()

    def zatrzymaj_animacje(self):
        self._pod.zatrzymaj()
        self._pod.ustaw(0.0)

    def sizeHint(self):
        szer = _szer(self.text(), self._rozmiar, self._waga()) + 2 * 19
        return QSize(int(szer + 2 * MARG_SWIATLA), int(self._wysokosc + 2 * MARG_SWIATLA))

    def minimumSizeHint(self):
        # przy ciasnym oknie przycisk woli przyciąć napis niż rozepchać pasek
        peln = self.sizeHint()
        return QSize(min(peln.width(), int(96 + 2 * MARG_SWIATLA)), peln.height())

    def _waga(self):
        return 700 if self._rola == "glowny" else 600

    def enterEvent(self, zdarzenie):
        if self.isEnabled():
            self._pod.do(1.0)
        super().enterEvent(zdarzenie)

    def leaveEvent(self, zdarzenie):
        self._pod.do(0.0)
        super().leaveEvent(zdarzenie)

    def hideEvent(self, zdarzenie):
        self._pod.zatrzymaj()
        super().hideEvent(zdarzenie)

    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(MARG_SWIATLA, MARG_SWIATLA,
                                         -MARG_SWIATLA, -MARG_SWIATLA)
        if r.width() < 4 or r.height() < 4:
            p.end()
            return
        promien = min(12.0, r.height() * 0.32)
        czynny = self.isEnabled()
        pod = self._pod.teraz() if czynny else 0.0
        wcisniety = self.isDown() and czynny
        if wcisniety:
            r = r.adjusted(0, 1.0, 0, 1.0)
        s = _sciezka(r, promien)
        waga = self._waga()
        m = _miary(self._rozmiar, waga)
        napis = self.text()
        if m.horizontalAdvance(napis) > r.width() - 20:
            napis = m.elidedText(napis, Qt.TextElideMode.ElideRight,
                                 max(10.0, r.width() - 20))
        tx = r.center().x() - m.horizontalAdvance(napis) * 0.5
        ty = r.center().y() + (m.ascent() - m.descent()) * 0.5

        if self._rola == "glowny":
            S.halo(p, r, S.ZIELEN, sila=int((46 + 42 * pod) * (1.0 if czynny else 0.25)),
                   promien=MARG_SWIATLA + 6.0, zaokraglenie=promien, przesun=2.0)
            S.halo(p, r, S.CYJAN, sila=int((30 + 30 * pod) * (1.0 if czynny else 0.25)),
                   promien=MARG_SWIATLA + 2.0, zaokraglenie=promien, przesun=0.0)
            g = QLinearGradient(r.topLeft(), r.topRight())
            a, b = QColor(S.CYJAN), QColor(S.ZIELEN)
            if not czynny:
                a, b = a.darker(210), b.darker(210)
            g.setColorAt(0.0, a.lighter(100 + int(8 * pod)))
            g.setColorAt(1.0, b.lighter(100 + int(8 * pod)))
            p.fillPath(s, QBrush(g))
            polysk = QLinearGradient(r.topLeft(), QPointF(r.left(), r.center().y()))
            polysk.setColorAt(0.0, QColor(255, 255, 255, 95))
            polysk.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillPath(s, QBrush(polysk))
            S.tekst(p, tx, ty, napis, QColor("#04121A") if czynny else QColor("#0A1C22"),
                    self._rozmiar, waga)
        elif self._rola == "zielony":
            if pod > 0.01:
                S.halo(p, r, S.ZIELEN, sila=int(30 * pod), promien=MARG_SWIATLA + 2.0,
                       zaokraglenie=promien, przesun=1.0)
            tlo = QLinearGradient(r.topLeft(), r.bottomLeft())
            tlo.setColorAt(0.0, S.z_alfa(S.ZIELEN, (34 + 26 * pod) * (1.0 if czynny else 0.4)))
            tlo.setColorAt(1.0, S.z_alfa(S.ZIELEN, (14 + 14 * pod) * (1.0 if czynny else 0.4)))
            p.fillPath(s, QBrush(tlo))
            moc = 1.0 if czynny else 0.34
            S.obrys_gradientowy(p, s, S.z_alfa(S.CYJAN, (150 + 70 * pod) * moc),
                                S.z_alfa(S.ZIELEN, (190 + 60 * pod) * moc), szerokosc=1.2)
            barwa = QColor(S.MIETA) if czynny else S.z_alfa(S.MIETA, 80)
            S.tekst(p, tx, ty, napis, barwa, self._rozmiar, waga)
        else:
            tlo = QLinearGradient(r.topLeft(), r.bottomLeft())
            tlo.setColorAt(0.0, QColor(36, 52, 76, int(180 + 40 * pod)))
            tlo.setColorAt(1.0, QColor(19, 30, 48, int(200 + 30 * pod)))
            p.fillPath(s, QBrush(tlo))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(S.z_alfa(S.CYJAN if pod > 0.5 else QColor(255, 255, 255),
                                   int(30 + 90 * pod)), 1.0))
            p.drawPath(s)
            gora = QRectF(r.x() + promien * 0.6, r.y() + 0.5, r.width() - promien * 1.2, 1.0)
            p.fillRect(gora, QColor(255, 255, 255, int(26 + 30 * pod)))
            barwa = QColor(S.TEKST) if czynny else S.z_alfa(S.TEKST, 110)
            S.tekst(p, tx, ty, napis, barwa, self._rozmiar, waga)
        p.end()


class PrzyciskZamkniecia(QPushButton):
    """Krzyżyk panelu — rysowany, bez żadnego napisu."""

    def __init__(self, rodzic=None):
        super().__init__("", rodzic)
        self.setFixedSize(34, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._pod = S.Plynnie(0.0, czas=150, rodzic=self, przy_zmianie=self.update)

    def zatrzymaj_animacje(self):
        self._pod.zatrzymaj()
        self._pod.ustaw(0.0)

    def enterEvent(self, z):
        self._pod.do(1.0)
        super().enterEvent(z)

    def leaveEvent(self, z):
        self._pod.do(0.0)
        super().leaveEvent(z)

    def paintEvent(self, _z):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pod = self._pod.teraz()
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        s = _sciezka(r, r.height() * 0.5)
        p.fillPath(s, QColor(255, 255, 255, int(12 + 26 * pod)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(S.z_alfa(S.BLAD if pod > 0.4 else QColor(255, 255, 255),
                               int(28 + 80 * pod)), 1.0))
        p.drawPath(s)
        sr = r.center()
        d = 5.0
        pen = QPen(S.z_alfa(S.TEKST_2 if pod < 0.5 else S.TEKST, 230), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(sr.x() - d, sr.y() - d), QPointF(sr.x() + d, sr.y() + d))
        p.drawLine(QPointF(sr.x() + d, sr.y() - d), QPointF(sr.x() - d, sr.y() + d))
        p.end()


# ── pasek postępu z zaokrąglonym czołem ──────────────────────────────
class PasekPostepu(QWidget):
    def __init__(self, kolor_a=S.CYJAN, kolor_b=S.ZIELEN, rodzic=None):
        super().__init__(rodzic)
        self.setFixedHeight(16)
        self._a, self._b = QColor(kolor_a), QColor(kolor_b)
        self._pl = S.Plynnie(0.0, czas=340, krzywa="wyjscie", rodzic=self,
                             przy_zmianie=self.update)

    def ustaw(self, ulamek, natychmiast=False):
        u = _ogranicz(float(ulamek))
        if natychmiast:
            self._pl.ustaw(u)
        else:
            self._pl.do(u)

    def ustaw_kolory(self, kolor_a, kolor_b):
        self._a, self._b = QColor(kolor_a), QColor(kolor_b)
        self.update()

    def wartosc(self):
        return self._pl.cel()

    def zatrzymaj_animacje(self):
        self._pl.dokoncz()

    def hideEvent(self, z):
        self._pl.zatrzymaj()
        super().hideEvent(z)

    def paintEvent(self, _z):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h = 8.0
        tor = QRectF(1.0, (self.height() - h) * 0.5, max(4.0, self.width() - 2.0), h)
        st = _sciezka(tor, h * 0.5)
        g = QLinearGradient(tor.topLeft(), tor.bottomLeft())
        g.setColorAt(0.0, QColor(4, 9, 17, 220))
        g.setColorAt(1.0, QColor(14, 24, 40, 190))
        p.fillPath(st, QBrush(g))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        p.drawPath(st)
        cieniowanie = QLinearGradient(tor.topLeft(), QPointF(tor.x(), tor.y() + h * 0.6))
        cieniowanie.setColorAt(0.0, QColor(0, 0, 0, 90))
        cieniowanie.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillPath(st, QBrush(cieniowanie))

        t = _ogranicz(self._pl.teraz())
        if t <= 0.0005:
            p.end()
            return
        szer = max(h, tor.width() * t)
        wyp = QRectF(tor.x(), tor.y(), szer, h)
        sw = _sciezka(wyp, h * 0.5)
        gw = QLinearGradient(tor.topLeft(), QPointF(tor.right(), tor.y()))
        gw.setColorAt(0.0, self._a)
        gw.setColorAt(1.0, self._b)
        # aureola pod wypełnieniem
        S.halo(p, wyp.adjusted(0, 1.0, 0, -1.0), self._b, sila=52, promien=6.0,
               zaokraglenie=h * 0.5)
        p.fillPath(sw, QBrush(gw))
        polysk = QLinearGradient(wyp.topLeft(), QPointF(wyp.x(), wyp.center().y()))
        polysk.setColorAt(0.0, QColor(255, 255, 255, 80))
        polysk.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(sw, QBrush(polysk))
        # czoło: kropla światła
        czolo = QPointF(wyp.right() - h * 0.5, wyp.center().y())
        S.punkt_swiatla(p, czolo, 10.0, self._b, 150)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 215)))
        p.drawEllipse(czolo, h * 0.34, h * 0.34)
        p.end()


# ── kafel liczby zbiorczej ───────────────────────────────────────────
class KafelLiczby(QWidget):
    """Liczba dochodząca do wartości, czcionka o stałej szerokości."""

    def __init__(self, opis, format_=None, wyrozniony=False, duzy=False, rodzic=None):
        super().__init__(rodzic)
        self._opis = str(opis)
        self._format = format_ or (lambda v: f"{v:,.0f}".replace(",", " "))
        self._wyrozniony = bool(wyrozniony)
        self._duzy = bool(duzy)
        self._cel = 0.0
        self._pl = S.Plynnie(0.0, czas=760, krzywa="wyjscie", rodzic=self,
                             przy_zmianie=self.update)
        self.setFixedHeight(62)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    # — dane —
    def ustaw_format(self, format_):
        self._format = format_
        self.updateGeometry()
        self.update()

    def ustaw_wartosc(self, wartosc, animuj=True):
        self._cel = float(wartosc)
        if animuj:
            self._pl.do(self._cel)
        else:
            self._pl.ustaw(self._cel)
        self.updateGeometry()
        self.update()

    def od_zera(self, wartosc):
        self._cel = float(wartosc)
        self._pl.ustaw(0.0)
        self._pl.do(self._cel)
        self.updateGeometry()
        self.update()

    def zatrzymaj_animacje(self):
        self._pl.dokoncz()

    def hideEvent(self, z):
        self._pl.zatrzymaj()
        super().hideEvent(z)

    # — miary —
    def _rozmiar_liczby(self):
        return 23.0 if self._duzy else 18.0

    def _napis(self):
        return self._format(self._pl.teraz())

    def sizeHint(self):
        wzor = self._format(self._cel if self._cel else 8888.88)
        a = _szer(wzor, self._rozmiar_liczby(), 700, mono=True)
        b = _szer(self._opis, 9, 700, odstep=0.9)
        return QSize(int(max(a, b) + 32), 62)

    def minimumSizeHint(self):
        peln = self.sizeHint()
        return QSize(min(peln.width(), 104), peln.height())

    def paintEvent(self, _z):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        s = _sciezka(r, 13.0)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        if self._wyrozniony:
            g.setColorAt(0.0, QColor(12, 40, 44, 232))
            g.setColorAt(1.0, QColor(7, 22, 30, 240))
        else:
            g.setColorAt(0.0, QColor(20, 32, 50, 214))
            g.setColorAt(1.0, QColor(10, 18, 30, 228))
        p.fillPath(s, QBrush(g))
        if self._wyrozniony:
            S.obrys_gradientowy(p, s, S.z_alfa(S.CYJAN, 170), S.z_alfa(S.ZIELEN, 215),
                                szerokosc=1.2)
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 26), 1.0))
            p.drawPath(s)
        gora = QRectF(r.x() + 9, r.y() + 0.6, r.width() - 18, 1.0)
        p.fillRect(gora, QColor(255, 255, 255, 34))

        rozm = self._rozmiar_liczby()
        napis = self._napis()
        wolne = r.width() - 30
        while rozm > 12 and _szer(napis, rozm, 700, mono=True) > wolne:
            rozm -= 0.5
        kolor = S.MIETA if self._wyrozniony else S.TEKST
        S.tekst(p, r.x() + 15, r.y() + 15 + rozm * 0.78, napis, kolor, rozm, 700,
                mono=True, poswiata=0.7 if self._wyrozniony else 0.0)
        S.tekst(p, r.x() + 15, r.bottom() - 12, self._opis,
                S.z_alfa(S.MIETA, 170) if self._wyrozniony else S.TEKST_3,
                9, 700, odstep=0.9)
        p.end()


# ── kafel jednego dokumentu ──────────────────────────────────────────
class KafelDokumentu(QWidget):
    """Kartka polecenia wyjazdu: ciepły papier, faktura, grubość i cień."""

    otwarty = pyqtSignal(object)

    def __init__(self, dzien, numer, rodzic=None):
        super().__init__(rodzic)
        self.dzien = dzien
        self.numer = int(numer)
        los = random.Random("%s-%02d" % (dzien.data.isoformat(), self.numer))
        self._kat = los.uniform(-1.25, 1.25)          # ułamek stopnia przechylenia
        self._przesuw = los.uniform(-1.6, 1.6)
        self.setMinimumSize(int(KAFEL_W * 0.84), 140)
        self.setMaximumHeight(int(KAFEL_H))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pix = None
        self._klucz_pix = None
        self._wejscie = S.Plynnie(0.0, czas=380, krzywa="wyjscie", rodzic=self,
                                  przy_zmianie=self.update)
        self._pod = S.Plynnie(0.0, czas=170, rodzic=self, przy_zmianie=self.update)

    # — animacja wejścia —
    def przygotuj(self):
        self._wejscie.ustaw(0.0)

    def pokaz(self):
        self._wejscie.do(1.0)

    def dokoncz(self):
        self._wejscie.zatrzymaj()
        self._wejscie.ustaw(1.0)

    def zatrzymaj_animacje(self):
        self.dokoncz()
        self._pod.zatrzymaj()
        self._pod.ustaw(0.0)

    def widoczny_w_calosci(self):
        return self._wejscie.teraz() > 0.999

    # — zdarzenia —
    def enterEvent(self, z):
        self._pod.do(1.0)
        super().enterEvent(z)

    def leaveEvent(self, z):
        self._pod.do(0.0)
        super().leaveEvent(z)

    def mouseReleaseEvent(self, z):
        if z.button() == Qt.MouseButton.LeftButton and self.rect().contains(z.pos()):
            self.otwarty.emit(self.dzien)
        super().mouseReleaseEvent(z)

    def hideEvent(self, z):
        self._wejscie.zatrzymaj()
        self._pod.zatrzymaj()
        super().hideEvent(z)

    def resizeEvent(self, z):
        self._pix = None
        super().resizeEvent(z)

    # — rysowanie —
    def _pole(self):
        r = QRectF(self.rect())
        return r.adjusted(10.0, 7.0, -10.0, -18.0)

    def _klucz(self):
        d = self.dzien
        return (self.width(), self.height(), round(self.devicePixelRatioF(), 2),
                d.data, round(d.kwota, 2), round(d.km, 1), d.podpisany, self.numer)

    def _pixmapa(self):
        klucz = self._klucz()
        if self._pix is not None and self._klucz_pix == klucz:
            return self._pix
        dpr = self.devicePixelRatioF()
        pix = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = self._pole()
        p.translate(r.center())
        p.rotate(self._kat)
        p.translate(-r.center().x() + self._przesuw, -r.center().y())
        self._rysuj_kartke(p, r)
        p.end()
        self._pix, self._klucz_pix = pix, klucz
        return pix

    def _rysuj_kartke(self, p, r):
        promien = 7.0
        # cień wielowarstwowy: styk, korpus, daleka poświata
        _cien_miekki(p, r, promien, przesun=1, rozmycie=4, sila=120, krok=1)
        _cien_miekki(p, r, promien, przesun=6, rozmycie=13, sila=104, krok=2)
        _cien_miekki(p, r, promien, przesun=15, rozmycie=26, sila=62, krok=4)

        # kartki leżące pod spodem — plik dokumentów, nie pojedyncza kartka
        for wsun, zejscie, barwa in ((5.5, 6.5, PAPIER_SPOD), (2.6, 3.2, PAPIER_BOK)):
            rr = QRectF(r.x() + wsun, r.y() + zejscie, r.width() - 2 * wsun, r.height())
            p.fillPath(_sciezka(rr, promien), QBrush(barwa))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(150, 142, 126, 90), 1.0))
            p.drawLine(QPointF(rr.x() + promien, rr.bottom() - 0.5),
                       QPointF(rr.right() - promien, rr.bottom() - 0.5))

        s = _sciezka(r, promien)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, PAPIER_GORA)
        g.setColorAt(0.55, PAPIER_SRODEK)
        g.setColorAt(1.0, PAPIER_DOL)
        p.fillPath(s, QBrush(g))

        p.save()
        p.setClipPath(s)
        zasieg = max(r.width(), r.height()) * 1.3
        rg = QRadialGradient(QPointF(r.x() + r.width() * 0.2, r.y() + r.height() * 0.08), zasieg)
        rg.setColorAt(0.0, QColor(255, 251, 240, 130))
        rg.setColorAt(1.0, QColor(255, 251, 240, 0))
        p.fillRect(r, QBrush(rg))
        rg2 = QRadialGradient(QPointF(r.right(), r.bottom()), zasieg * 0.85)
        rg2.setColorAt(0.0, QColor(122, 116, 100, 34))
        rg2.setColorAt(1.0, QColor(122, 116, 100, 0))
        p.fillRect(r, QBrush(rg2))
        S.ziarno(p, r, sila=6, skala=1.6, ciemne=1.35)         # faktura papieru
        # grubość kartki po dolnej krawędzi
        pas = QRectF(r.x(), r.bottom() - 4.5, r.width(), 4.5)
        gp = QLinearGradient(pas.topLeft(), pas.bottomLeft())
        gp.setColorAt(0.0, QColor(206, 198, 182, 0))
        gp.setColorAt(1.0, QColor(200, 191, 174, 140))
        p.fillRect(pas, QBrush(gp))
        p.restore()

        self._rysuj_tresc(p, r)

        # krawędzie: góra zbiera światło, dół siada w cieniu
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.setClipRect(QRectF(r.x(), r.y(), r.width(), r.height() * 0.5))
        p.setPen(QPen(QColor(255, 255, 255, 205), 1.0))
        p.drawPath(_sciezka(r.adjusted(0.6, 0.6, -0.6, -0.6), promien))
        p.restore()
        p.setPen(QPen(QColor(150, 142, 126, 120), 1.0))
        p.drawLine(QPointF(r.x() + promien * 0.6, r.bottom() - 0.5),
                   QPointF(r.right() - promien * 0.6, r.bottom() - 0.5))
        p.setPen(QPen(QColor(26, 32, 46, 52), 1.0))
        p.drawPath(s)

        if self.dzien.podpisany:
            p.setPen(QPen(S.z_alfa(S.ZIELEN.darker(125), 150), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(s)

    def _rysuj_tresc(self, p, r):
        d = self.dzien
        lewy = r.x() + 12
        prawy = r.right() - 12
        data = "%02d.%02d" % (d.data.day, d.data.month)
        S.tekst(p, lewy, r.y() + 23, data, ATRAMENT, 16, 700)
        S.tekst(p, lewy, r.y() + 36, D.DNI_PL[d.data.weekday()], ATRAMENT_3, 9.5, 600,
                odstep=0.4)

        # plakietka PDF
        pr = QRectF(prawy - 34, r.y() + 10, 34, 16)
        pp = _sciezka(pr, 5.0)
        gp = QLinearGradient(pr.topLeft(), pr.bottomRight())
        gp.setColorAt(0.0, QColor("#0FD6A4"))
        gp.setColorAt(1.0, QColor("#0AA9C9"))
        p.fillPath(pp, QBrush(gp))
        szer_pdf = _szer("PDF", 9, 800, odstep=0.4)
        S.tekst(p, pr.center().x() - szer_pdf * 0.5, pr.y() + 11.5, "PDF",
                QColor("#04121A"), 9, 800, odstep=0.4)

        p.setPen(QPen(LINIA_DRUKU, 1.0))
        p.drawLine(QPointF(lewy, r.y() + 44.5), QPointF(prawy, r.y() + 44.5))

        ciasno = r.height() < 124
        nr = "NR %d/%02d/%02d" % (d.data.year, d.data.month, d.data.day)
        if ciasno:
            S.tekst(p, lewy, r.y() + 58, nr, ATRAMENT_2, 8.5, 600, mono=True)
        else:
            S.tekst(p, lewy, r.y() + 58, "POLECENIE WYJAZDU", ATRAMENT_2, 8, 800, odstep=0.7)
            S.tekst(p, lewy, r.y() + 69.5, nr, ATRAMENT_3, 8.5, 500, mono=True)

        # stopka: kilometry i kwota
        yb = r.bottom() - 12
        S.tekst(p, lewy, yb, "%.0f km" % d.km, ATRAMENT_3, 10, 600, mono=True)
        kwota = "%s zł" % D.zl(d.kwota)
        S.tekst(p, prawy - _szer(kwota, 11.5, 700, mono=True), yb, kwota,
                ATRAMENT, 11.5, 700, mono=True)

        # pole między numerem a stopką: wiersze druku albo pieczęć
        gora = r.y() + (66.0 if ciasno else 78.0)
        dol = yb - 15.0
        if d.podpisany:
            pasmo = max(8.0, dol - gora + 8.0)
            self._rysuj_pieczec(p, r, (gora + dol) * 0.5,
                                min(1.0, pasmo / 30.0))
            return
        y = gora
        i = 0
        while y <= dol and i < 3:
            p.fillRect(QRectF(lewy, y, (r.width() - 34) * (0.92 - i * 0.16), 2.2),
                       QColor(150, 160, 180, 120))
            y += 7.5
            i += 1

    def _rysuj_pieczec(self, p, r, srodek_y, skala=1.0):
        p.save()
        p.translate(r.center().x(), srodek_y)
        p.rotate(-5)
        p.scale(skala, skala)
        pole = QRectF(-47, -10.5, 94, 21)
        s = _sciezka(pole, 5.5)
        p.fillPath(s, QBrush(S.z_alfa(S.ZIELEN, 42)))
        p.setPen(QPen(S.z_alfa(S.ZIELEN.darker(115), 200), 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)
        S.tekst(p, -39, -1.5, "PODPISANO", QColor("#0B7A5A"), 9.5, 800, odstep=0.7)
        S.tekst(p, -39, 7.5, "profil zaufany · 14:20", QColor("#2E8B72"), 6.5, 500)
        p.restore()

    def paintEvent(self, _z):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = _ogranicz(self._wejscie.teraz())
        pod = self._pod.teraz() if t > 0.999 else 0.0
        pole = self._pole()
        if pod > 0.01:
            S.halo(p, pole.adjusted(0, -3 - 2 * pod, 0, -3 - 2 * pod), S.CYJAN,
                   sila=int(52 * pod), promien=16.0, zaokraglenie=8.0, przesun=3.0)
        p.save()
        if t < 0.999:
            p.setOpacity(_ogranicz(t * 1.25))
            sr = pole.center()
            k = 0.93 + 0.07 * t
            p.translate(sr)
            p.scale(k, k)
            p.translate(-sr)
            p.translate(0.0, (1.0 - t) * 18.0)
        elif pod > 0.01:
            p.translate(0.0, -3.0 * pod)
        p.drawPixmap(0, 0, self._pixmapa())
        if t < 0.999:
            p.fillPath(_sciezka(pole, 7.0), QColor(255, 255, 255, int(70 * (1.0 - t))))
        p.restore()
        p.end()


# ── pasek kartek z układem liczonym ręcznie ──────────────────────────
class PasPapierow(QWidget):
    """Kartki leżą obok siebie; mieści się tyle, ile wchodzi na szerokość."""

    otwarty = pyqtSignal(object)

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self._kafle = []
        self._ukryte = 0
        self._odsloniete = 0
        self._x_reszty = 0.0
        self._wys_reszty = (0.0, float(KAFEL_H))
        self._kaskada = QTimer(self)
        self._kaskada.setInterval(KASKADA_MS)
        self._kaskada.timeout.connect(self._nastepna)
        self.setMinimumHeight(148)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # — zawartość —
    def ustaw_dni(self, dni):
        for k in self._kafle:
            k.setParent(None)
            k.deleteLater()
        self._kafle = []
        for i, d in enumerate(dni, start=1):
            k = KafelDokumentu(d, i, self)
            k.otwarty.connect(self.otwarty.emit)
            k.przygotuj()
            k.show()
            self._kafle.append(k)
        self._ulozenie()

    def sizeHint(self):
        return QSize(int(KAFEL_W * 4 + ODSTEP_KAFLI * 3), int(KAFEL_H))

    def resizeEvent(self, z):
        self._ulozenie()
        super().resizeEvent(z)

    def _ulozenie(self):
        n = len(self._kafle)
        if not n:
            self._ukryte = 0
            self.update()
            return
        szerokosc = float(self.width())
        wysokosc = min(KAFEL_H, max(140.0, float(self.height())))
        gora = (self.height() - wysokosc) * 0.5
        def zmiesci(szer, wolne):
            return int((wolne + ODSTEP_KAFLI) // (szer + ODSTEP_KAFLI))

        szer, ile = KAFEL_W, 0
        for kandydat in (KAFEL_W, 160.0, 152.0, 144.0):
            # najpierw próbujemy pokazać wszystkie kartki, od najszerszej wersji
            if zmiesci(kandydat, szerokosc) >= n:
                szer, ile = kandydat, n
                break
        if ile != n:                     # nie wchodzą — zostaw miejsce na „resztę”
            szer = KAFEL_W
            ile = max(1, min(n - 1, zmiesci(szer, szerokosc - 74.0)))
        self._ukryte = n - ile
        x = 0.0
        for i, k in enumerate(self._kafle):
            if i < ile:
                k.setFixedWidth(int(szer))
                k.setGeometry(int(x), int(gora), int(szer), int(wysokosc))
                k.show()
                x += szer + ODSTEP_KAFLI
            else:
                k.hide()
        self._x_reszty = x
        self._wys_reszty = (gora, wysokosc)
        self.update()

    # — pusty pas —
    def _rysuj_pusto(self):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        wysokosc = min(KAFEL_H, max(140.0, float(self.height()))) - 26.0
        gora = (self.height() - wysokosc) * 0.5
        x = 10.0
        while x + KAFEL_W - 20 < self.width():
            r = QRectF(x, gora, KAFEL_W - 20, wysokosc)
            s = _sciezka(r, 7.0)
            p.fillPath(s, QColor(255, 255, 255, 7))
            pen = QPen(QColor(255, 255, 255, 20), 1.0)
            pen.setDashPattern([3.0, 4.0])
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(s)
            x += KAFEL_W + ODSTEP_KAFLI
        p.end()

    # — kaskada —
    def uruchom_kaskade(self):
        self._kaskada.stop()
        self._odsloniete = 0
        for k in self._kafle:
            k.przygotuj()
        if not self._kafle:
            return
        self._nastepna()
        self._kaskada.start()

    def _nastepna(self):
        widoczne = [k for k in self._kafle if not k.isHidden()]
        if self._odsloniete >= len(widoczne):
            self._kaskada.stop()
            return
        widoczne[self._odsloniete].pokaz()
        self._odsloniete += 1

    def zatrzymaj_animacje(self):
        self._kaskada.stop()
        for k in self._kafle:
            k.zatrzymaj_animacje()
        self._odsloniete = len(self._kafle)
        self.update()

    def hideEvent(self, z):
        self._kaskada.stop()
        super().hideEvent(z)

    def paintEvent(self, _z):
        if not self._kafle:
            self._rysuj_pusto()
            return
        if not self._ukryte:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        gora, wysokosc = self._wys_reszty
        r = QRectF(self._x_reszty + 2, gora + 10, 62.0, wysokosc - 34.0)
        # brzegi kartek leżących dalej w pliku
        for i, (dx, alfa) in enumerate(((10.0, 34), (6.0, 52), (2.0, 74))):
            rr = QRectF(r.x() + dx, r.y() + i * 2.0, 5.0, r.height() - i * 4.0)
            p.fillPath(_sciezka(rr, 2.0), QColor(240, 238, 230, alfa))
        s = _sciezka(r, 8.0)
        p.fillPath(s, QColor(255, 255, 255, 10))
        pen = QPen(QColor(255, 255, 255, 46), 1.0)
        pen.setDashPattern([3.0, 3.5])
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)
        napis = "+%d" % self._ukryte
        S.tekst(p, r.center().x() - _szer(napis, 17, 700, mono=True) * 0.5 + 5,
                r.center().y() + 2, napis, S.TEKST, 17, 700, mono=True)
        S.tekst(p, r.center().x() - _szer("PDF", 8, 700, odstep=0.8) * 0.5 + 5,
                r.center().y() + 18, "PDF", S.TEKST_3, 8, 700, odstep=0.8)
        p.end()


# ── taca ─────────────────────────────────────────────────────────────
class TacaDokumentow(QWidget):
    zwin = pyqtSignal()
    otworz_podpis = pyqtSignal()
    otworz_wysylke = pyqtSignal()
    otworz_wszystkie = pyqtSignal()

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.dni = []
        self._czeka_kaskada = False
        self._buduj()

    # — budowa —
    def _buduj(self):
        z = QVBoxLayout(self)
        z.setContentsMargins(26, 18, 26, 16)
        z.setSpacing(10)

        gora = QHBoxLayout()
        gora.setSpacing(14)
        lewo = QVBoxLayout()
        lewo.setSpacing(1)
        self.l_tytul = Napis("Otwórz dokumenty", 23, 700, S.TEKST, naglowek=True)
        self.l_sciezka = Napis("", 11.5, 600, S.TEKST_2)
        self.l_folder = Napis("", 11, 400, S.TEKST_3, mono=True)
        pod = QHBoxLayout()
        pod.setSpacing(10)
        pod.addWidget(self.l_sciezka, 0, Qt.AlignmentFlag.AlignVCenter)
        pod.addWidget(self.l_folder, 0, Qt.AlignmentFlag.AlignVCenter)
        pod.addStretch(1)
        lewo.addWidget(self.l_tytul)
        lewo.addLayout(pod)
        gora.addLayout(lewo)
        gora.addStretch(1)

        self.k_kwota = KafelLiczby("CO DO GROSZA", lambda v: "%s zł" % D.zl(v),
                                   wyrozniony=True, duzy=True, rodzic=self)
        self.k_km = KafelLiczby("REALNE DROGI",
                                lambda v: "%s km" % f"{v:,.0f}".replace(",", " "),
                                rodzic=self)
        self.k_dni = KafelLiczby("DELEGACJE", lambda v: "%.0f" % v, rodzic=self)
        for k in (self.k_kwota, self.k_km, self.k_dni):
            gora.addWidget(k, 0, Qt.AlignmentFlag.AlignVCenter)
        gora.addSpacing(4)
        self.b_zwin = Przycisk("Zwiń tacę", "zwykly", 12.5, self)
        self.b_zwin.ustaw_wysokosc(38)
        self.b_zwin.clicked.connect(self.zwin.emit)
        gora.addWidget(self.b_zwin, 0, Qt.AlignmentFlag.AlignVCenter)
        z.addLayout(gora)

        self.pas = PasPapierow(self)
        self.pas.otwarty.connect(self._kartka_klikieta)
        z.addWidget(self.pas, 1)

        dol = QHBoxLayout()
        dol.setSpacing(8)
        self.l_stan = Napis("", 12, 600, S.MIETA, punkt=S.ZIELEN)
        dol.addWidget(self.l_stan, 0, Qt.AlignmentFlag.AlignVCenter)
        dol.addStretch(1)
        self.b_folder = Przycisk("Otwórz folder", "zwykly", 13, self)
        self.b_podpis = Przycisk("Podpisz elektronicznie", "zielony", 13, self)
        self.b_mail = Przycisk("Wyślij e-mailem", "zielony", 13, self)
        self.b_wszystkie = Przycisk("Otwórz wszystkie dokumenty", "glowny", 13, self)
        for b in (self.b_folder, self.b_podpis, self.b_mail, self.b_wszystkie):
            dol.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        self.b_podpis.clicked.connect(self.otworz_podpis.emit)
        self.b_mail.clicked.connect(self.otworz_wysylke.emit)
        self.b_wszystkie.clicked.connect(self.otworz_wszystkie.emit)
        z.addLayout(dol)

    # — dane —
    def ustaw_dni(self, dni, folder="Pulpit / Rozliczenie_Anna_Nowak_wrzesień_2026r"):
        self.dni = [d for d in dni if not d.wolny and not d.wylaczony]
        p = D.podsumowanie(self.dni)          # liczby zgadzają się z kartkami na tacy
        wszystkie = len(dni)
        ile_plikow = len(self.dni) + 1 if self.dni else 0
        self.l_sciezka.setText("wrzesień 2026 · %d plików PDF" % ile_plikow)
        self.l_folder.setText(folder)
        self.k_kwota.od_zera(p["kwota"])
        self.k_km.od_zera(p["km"])
        self.k_dni.ustaw_format(lambda v, c=wszystkie: "%.0f z %d" % (v, c))
        self.k_dni.od_zera(p["dni"])
        self.pas.ustaw_dni(self.dni)
        ile = sum(1 for d in self.dni if d.podpisany)
        self.l_stan.setText("%d z %d podpisanych" % (ile, len(self.dni)) if ile else "")
        for b in (self.b_podpis, self.b_mail, self.b_wszystkie):
            b.setEnabled(bool(self.dni))
        if self.isVisible():
            self.pas.uruchom_kaskade()
            self._czeka_kaskada = False
        else:
            self._czeka_kaskada = True

    def resizeEvent(self, z):
        # przy wąskim oknie znikają rzeczy najmniej ważne — pasek ma się zmieścić
        w = self.width()
        self.l_folder.setVisible(w >= 1000)
        self.b_folder.setVisible(w >= 920)
        self.k_dni.setVisible(w >= 800)
        self.k_km.setVisible(w >= 700)
        super().resizeEvent(z)

    def _kartka_klikieta(self, dzien):
        self.l_stan.setText("%02d.%02d · otwarto" % (dzien.data.day, dzien.data.month))

    # — animacje —
    def zatrzymaj_animacje(self):
        """Stawia wszystko w położeniu docelowym — powtarzalne zrzuty i czyste wyjście."""
        self._czeka_kaskada = False
        self.pas.zatrzymaj_animacje()
        for k in (self.k_kwota, self.k_km, self.k_dni):
            k.zatrzymaj_animacje()
        for b in (self.b_zwin, self.b_folder, self.b_podpis, self.b_mail, self.b_wszystkie):
            b.zatrzymaj_animacje()

    def showEvent(self, z):
        super().showEvent(z)
        if self._czeka_kaskada:
            self._czeka_kaskada = False
            self.pas.uruchom_kaskade()

    def hideEvent(self, z):
        self.zatrzymaj_animacje()
        super().hideEvent(z)

    def closeEvent(self, z):
        self.zatrzymaj_animacje()
        super().closeEvent(z)

    def sizeHint(self):
        return QSize(1100, 324)

    # — rysowanie —
    def paintEvent(self, _z):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect())
        s = _sciezka(r.adjusted(0, 0, 0, 26), 26.0)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.0, QColor(24, 40, 60, 248))
        g.setColorAt(0.45, QColor(16, 27, 44, 250))
        g.setColorAt(1.0, QColor(10, 17, 29, 252))
        p.fillPath(s, QBrush(g))
        p.save()
        p.setClipPath(s)
        zasieg = max(r.width(), r.height())
        rg = QRadialGradient(QPointF(r.center().x(), r.y()), zasieg * 0.75)
        rg.setColorAt(0.0, S.z_alfa(S.CYJAN, 20))
        rg.setColorAt(1.0, S.z_alfa(S.CYJAN, 0))
        p.fillRect(r, QBrush(rg))
        S.ziarno(p, r, sila=9, skala=1.0, ciemne=0.5)
        p.restore()

        # rowek, w którym leżą kartki — taca ma dno
        g_pas = QRectF(self.pas.geometry()).adjusted(-12, -10, 12, 12)
        if g_pas.width() > 20 and g_pas.height() > 20:
            sp = _sciezka(g_pas, 16.0)
            gr = QLinearGradient(g_pas.topLeft(), g_pas.bottomLeft())
            gr.setColorAt(0.0, QColor(0, 0, 0, 58))
            gr.setColorAt(0.35, QColor(0, 0, 0, 26))
            gr.setColorAt(1.0, QColor(0, 0, 0, 10))
            p.fillPath(sp, QBrush(gr))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(0, 0, 0, 70), 1.0))
            p.drawPath(sp)
            p.setPen(QPen(QColor(255, 255, 255, 16), 1.0))
            p.drawPath(_sciezka(g_pas.adjusted(0, 1.0, 0, 1.0), 16.0))

        _linia_swiatla(p, r.x() + 24, r.right() - 24, r.y() + 0.4, S.CYJAN, 165, 1.2)
        p.setPen(QPen(S.OBRYS_MOCNY, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)

        ucho = QRectF(r.center().x() - 26, r.y() + 8, 52, 3)
        p.fillPath(_sciezka(ucho, 1.5), QBrush(QColor(255, 255, 255, 62)))
        p.end()


# ── wspólna podstawa paneli ──────────────────────────────────────────
class Panel(QDialog):
    """Okno bez ramy systemowej: ten sam materiał co taca, miękki cień pod spodem."""

    MARGINES = 26          # zapas na cień dookoła okna

    def __init__(self, tytul, podtytul="", rodzic=None):
        super().__init__(rodzic)
        self.setWindowTitle(tytul)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(S.qss())
        self.setMinimumWidth(620)
        self._ciagniecie = None

        m = self.MARGINES
        self.z = QVBoxLayout(self)
        self.z.setContentsMargins(m + 26, m + 20, m + 26, m + 20)
        self.z.setSpacing(13)

        naglowek = QHBoxLayout()
        naglowek.setSpacing(12)
        kolumna = QVBoxLayout()
        kolumna.setSpacing(2)
        self.l_tytul = Napis(tytul, 21, 700, S.TEKST, naglowek=True)
        self.l_podtytul = Napis(podtytul, 11, 500, S.TEKST_3, odstep=0.4)
        kolumna.addWidget(self.l_tytul)
        kolumna.addWidget(self.l_podtytul)
        naglowek.addLayout(kolumna)
        naglowek.addStretch(1)
        self.b_zamknij = PrzyciskZamkniecia(self)
        self.b_zamknij.clicked.connect(self.reject)
        naglowek.addWidget(self.b_zamknij, 0, Qt.AlignmentFlag.AlignTop)
        self.z.addLayout(naglowek)
        self.z.addSpacing(8)

    # — pomocniki układu —
    def wiersz(self, etykieta, widget):
        w = QHBoxLayout()
        w.setSpacing(12)
        l = Napis(etykieta, 9.5, 800, S.TEKST_3, odstep=0.9)
        l.setFixedWidth(104)
        w.addWidget(l, 0, Qt.AlignmentFlag.AlignVCenter)
        w.addWidget(widget, 1)
        self.z.addLayout(w)
        return widget

    def wiersz_stanu(self, tekst="", licznik=""):
        """Stan po lewej, liczba po prawej — jedna para o wyraźnej hierarchii."""
        w = QHBoxLayout()
        w.setSpacing(12)
        l_stan = Napis(tekst, 12, 600, S.TEKST_2)
        l_licznik = Napis(licznik, 13, 700, S.TEKST, mono=True,
                          wyrownanie=Qt.AlignmentFlag.AlignRight)
        w.addWidget(l_stan, 0, Qt.AlignmentFlag.AlignVCenter)
        w.addStretch(1)
        w.addWidget(l_licznik, 0, Qt.AlignmentFlag.AlignVCenter)
        self.z.addLayout(w)
        return l_stan, l_licznik

    def stopka(self, *przyciski):
        d = QHBoxLayout()
        d.setSpacing(8)
        d.addStretch(1)
        for b in przyciski:
            d.addWidget(b)
        self.z.addLayout(d)
        return d

    def pole(self):
        m = self.MARGINES
        return QRectF(self.rect()).adjusted(m, m - 4, -m, -m - 4)

    # — przesuwanie okna bez ramy —
    def mousePressEvent(self, z):
        if z.button() == Qt.MouseButton.LeftButton and z.position().y() < self.MARGINES + 74:
            self._ciagniecie = z.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(z)

    def mouseMoveEvent(self, z):
        if self._ciagniecie is not None and z.buttons() & Qt.MouseButton.LeftButton:
            self.move(z.globalPosition().toPoint() - self._ciagniecie)
        super().mouseMoveEvent(z)

    def mouseReleaseEvent(self, z):
        self._ciagniecie = None
        super().mouseReleaseEvent(z)

    # — rysowanie —
    def paintEvent(self, _z):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = self.pole()
        promien = 20.0
        _cien_miekki(p, r, promien, przesun=4, rozmycie=10, sila=150, krok=2)
        _cien_miekki(p, r, promien, przesun=12, rozmycie=26, sila=130, krok=3)
        _cien_miekki(p, r, promien, przesun=26, rozmycie=52, sila=90, krok=6)

        s = _sciezka(r, promien)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.0, QColor(26, 43, 64, 252))
        g.setColorAt(0.45, QColor(17, 28, 46, 253))
        g.setColorAt(1.0, QColor(10, 17, 29, 254))
        p.fillPath(s, QBrush(g))
        p.save()
        p.setClipPath(s)
        rg = QRadialGradient(QPointF(r.center().x(), r.y()), max(r.width(), r.height()) * 0.8)
        rg.setColorAt(0.0, S.z_alfa(S.CYJAN, 22))
        rg.setColorAt(1.0, S.z_alfa(S.CYJAN, 0))
        p.fillRect(r, QBrush(rg))
        S.ziarno(p, r, sila=9, skala=1.0, ciemne=0.5)
        p.restore()

        _linia_swiatla(p, r.x() + 22, r.right() - 22, r.y() + 0.6, S.CYJAN, 165, 1.2)
        p.setPen(QPen(S.OBRYS_MOCNY, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)

        # kreska pod nagłówkiem
        y = self.l_podtytul.geometry().bottom() + 12.0
        gk = QLinearGradient(QPointF(r.x(), y), QPointF(r.right(), y))
        gk.setColorAt(0.00, QColor(255, 255, 255, 0))
        gk.setColorAt(0.22, QColor(255, 255, 255, 46))
        gk.setColorAt(0.90, QColor(255, 255, 255, 28))
        gk.setColorAt(1.00, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(r.x() + 18, y, r.width() - 36, 1.0), QBrush(gk))
        _linia_swiatla(p, r.x() + 20, r.x() + 168, y, S.CYJAN, 220, 1.3)
        p.end()


# ── kafel ścieżki podpisu ────────────────────────────────────────────
class KafelSciezki(QWidget):
    """Klikalna ścieżka podpisu — kafel, nie przełącznik."""

    wybrano = pyqtSignal(int)

    def __init__(self, numer, nazwa, opis, znak="tarcza", rodzic=None):
        super().__init__(rodzic)
        self.numer = int(numer)
        self.nazwa = str(nazwa)
        self.opis = str(opis)
        self.znak = znak
        self._wybrany = False
        self._ramka = False              # obwódka tylko przy wędrówce klawiszem
        self._pod = S.Plynnie(0.0, czas=160, rodzic=self, przy_zmianie=self.update)
        self._wybor = S.Plynnie(0.0, czas=240, krzywa="wyjscie", rodzic=self,
                                przy_zmianie=self.update)
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def ustaw_wybrany(self, wybrany, animuj=True):
        self._wybrany = bool(wybrany)
        if animuj:
            self._wybor.do(1.0 if self._wybrany else 0.0)
        else:
            self._wybor.ustaw(1.0 if self._wybrany else 0.0)
        self.update()

    def wybrany(self):
        return self._wybrany

    def zatrzymaj_animacje(self):
        self._pod.zatrzymaj()
        self._pod.ustaw(0.0)
        self._wybor.dokoncz()

    def enterEvent(self, z):
        if self.isEnabled():
            self._pod.do(1.0)
        super().enterEvent(z)

    def leaveEvent(self, z):
        self._pod.do(0.0)
        super().leaveEvent(z)

    def mouseReleaseEvent(self, z):
        if (self.isEnabled() and z.button() == Qt.MouseButton.LeftButton
                and self.rect().contains(z.pos())):
            self.wybrano.emit(self.numer)
        super().mouseReleaseEvent(z)

    def keyPressEvent(self, z):
        if (self.isEnabled() and z.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return,
                                             Qt.Key.Key_Enter)):
            self.wybrano.emit(self.numer)
            return
        super().keyPressEvent(z)

    def focusInEvent(self, z):
        self._ramka = z.reason() in (Qt.FocusReason.TabFocusReason,
                                     Qt.FocusReason.BacktabFocusReason,
                                     Qt.FocusReason.ShortcutFocusReason)
        self.update()
        super().focusInEvent(z)

    def focusOutEvent(self, z):
        self._ramka = False
        self.update()
        super().focusOutEvent(z)

    def _rysuj_znak(self, p, sr, kolor):
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(kolor, 1.5)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        x, y = sr.x(), sr.y()
        if self.znak == "tarcza":
            s = QPainterPath()
            s.moveTo(x, y - 9)
            s.lineTo(x + 8, y - 5)
            s.lineTo(x + 8, y + 2)
            s.cubicTo(x + 8, y + 7, x + 4, y + 9, x, y + 10)
            s.cubicTo(x - 4, y + 9, x - 8, y + 7, x - 8, y + 2)
            s.lineTo(x - 8, y - 5)
            s.closeSubpath()
            p.drawPath(s)
            p.drawLine(QPointF(x - 3.4, y), QPointF(x - 0.8, y + 3.0))
            p.drawLine(QPointF(x - 0.8, y + 3.0), QPointF(x + 4.0, y - 3.0))
        elif self.znak == "karta":
            r = QRectF(x - 9, y - 6.5, 18, 13)
            p.drawPath(_sciezka(r, 2.5))
            p.drawLine(QPointF(x - 9, y - 2.0), QPointF(x + 9, y - 2.0))
            p.setBrush(QBrush(kolor))
            p.drawEllipse(QPointF(x - 4.0, y + 2.5), 1.8, 1.8)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(x + 0.5, y + 2.5), QPointF(x + 6.5, y + 2.5))
        else:
            s = QPainterPath()
            s.moveTo(x - 7, y - 9)
            s.lineTo(x + 3, y - 9)
            s.lineTo(x + 7, y - 5)
            s.lineTo(x + 7, y + 9)
            s.lineTo(x - 7, y + 9)
            s.closeSubpath()
            p.drawPath(s)
            p.drawLine(QPointF(x + 3, y - 9), QPointF(x + 3, y - 5))
            p.drawLine(QPointF(x + 3, y - 5), QPointF(x + 7, y - 5))
            p.drawLine(QPointF(x - 3.5, y + 1), QPointF(x + 3.5, y + 1))
            p.drawLine(QPointF(x - 3.5, y + 5), QPointF(x + 1.5, y + 5))

    def paintEvent(self, _z):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = _ogranicz(self._wybor.teraz())
        pod = self._pod.teraz() * (1.0 - w * 0.6)
        czynny = self.isEnabled()
        if not czynny:
            pod = 0.0
        r = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        s = _sciezka(r, 13.0)
        if w > 0.01:
            S.halo(p, r, S.ZIELEN, sila=int(26 * w), promien=10.0, zaokraglenie=13.0,
                   przesun=2.0)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.0, QColor(int(20 + 6 * w), int(32 + 22 * w), int(50 + 14 * w),
                                 int(200 + 30 * pod)))
        g.setColorAt(1.0, QColor(int(11 + 2 * w), int(19 + 10 * w), int(31 + 8 * w), 225))
        p.fillPath(s, QBrush(g))
        if w > 0.02:
            S.obrys_gradientowy(p, s, S.z_alfa(S.CYJAN, int(210 * w)),
                                S.z_alfa(S.ZIELEN, int(230 * w)), szerokosc=1.4)
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, int(26 + 44 * pod)), 1.0))
            p.drawPath(s)
        gora = QRectF(r.x() + 10, r.y() + 0.6, r.width() - 20, 1.0)
        p.fillRect(gora, QColor(255, 255, 255, int(28 + 26 * (pod + w))))
        if self._ramka and self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(S.z_alfa(S.CYJAN, 150), 1.0))
            p.drawPath(_sciezka(r.adjusted(2.5, 2.5, -2.5, -2.5), 10.5))

        alfa = 255 if czynny else 120
        kolor_znaku = S.z_alfa(S.MIETA if w > 0.4 else S.TEKST_2, alfa)
        self._rysuj_znak(p, QPointF(r.x() + 30, r.center().y()), kolor_znaku)

        x = r.x() + 54
        nazwa_kolor = S.z_alfa(S.TEKST if w < 0.4 else S.MIETA, alfa)
        S.tekst(p, x, r.center().y() - 3, self.nazwa, nazwa_kolor, 14, 700 if w > 0.4 else 600,
                poswiata=0.6 * w)
        S.tekst(p, x, r.center().y() + 14, self.opis, S.z_alfa(S.TEKST_3, alfa), 11, 500)

        # znacznik wyboru po prawej
        sr = QPointF(r.right() - 26, r.center().y())
        if w > 0.02:
            S.punkt_swiatla(p, sr, 14.0, S.ZIELEN, int(120 * w))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(S.z_alfa(S.ZIELEN if w > 0.4 else QColor(255, 255, 255),
                               int(60 + 170 * w)), 1.4))
        p.drawEllipse(sr, 9.0, 9.0)
        if w > 0.02:
            pen = QPen(S.z_alfa(S.MIETA, int(255 * w)), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawLine(QPointF(sr.x() - 4.0, sr.y() + 0.2), QPointF(sr.x() - 1.2, sr.y() + 3.2))
            p.drawLine(QPointF(sr.x() - 1.2, sr.y() + 3.2), QPointF(sr.x() + 4.4, sr.y() - 3.4))
        p.end()


# ── panel podpisu ────────────────────────────────────────────────────
class PanelPodpisu(Panel):
    """Wybór bezpłatnej ścieżki podpisu i jego przebieg."""

    SCIEZKI = (("Profil zaufany", "gov.pl · bezpłatny", "tarcza"),
               ("e-dowód · podpis osobisty", "certyfikat w dowodzie · NFC albo czytnik", "karta"),
               ("Mam już podpisany plik", "plik z dysku", "plik"))

    def __init__(self, dni, rodzic=None):
        self.dni = list(dni)
        super().__init__("Podpisz elektronicznie",
                         "%d dokumentów · %s zł" % (len(self.dni),
                                                    D.zl(sum(d.kwota for d in self.dni))),
                         rodzic)
        self._wybor = 0
        self.kafle = []
        for i, (nazwa, opis, znak) in enumerate(self.SCIEZKI):
            k = KafelSciezki(i, nazwa, opis, znak, self)
            k.wybrano.connect(self._wybierz)
            k.ustaw_wybrany(i == 0, animuj=False)
            self.kafle.append(k)
            self.z.addWidget(k)
        self.z.addSpacing(4)

        self.l_stan, self.l_licznik = self.wiersz_stanu(
            "gotowe do podpisu", "0 / %d" % len(self.dni))
        self.postep = PasekPostepu(S.CYJAN, S.ZIELEN, self)
        self.z.addWidget(self.postep)

        self.b_anuluj = Przycisk("Anuluj", "zwykly", 13, self)
        self.b_anuluj.clicked.connect(self.reject)
        self.b_dalej = Przycisk("Dalej", "glowny", 13, self)
        self.b_dalej.setAutoDefault(True)
        self.b_dalej.setDefault(True)
        self.b_dalej.clicked.connect(self._dalej)
        self.stopka(self.b_anuluj, self.b_dalej)

        self._licznik = 0
        self._zegar = QTimer(self)
        self._zegar.setInterval(max(90, int(1900 / max(1, len(self.dni)))))
        self._zegar.timeout.connect(self._tyk)

    # — wybór ścieżki —
    def _wybierz(self, numer):
        if numer == self._wybor:
            return
        self._wybor = int(numer)
        for k in self.kafle:
            k.ustaw_wybrany(k.numer == self._wybor)
        self.l_stan.setText("gotowe do podpisu · %s" % self.SCIEZKI[self._wybor][0].lower())

    def nazwa_sciezki(self):
        return self.SCIEZKI[self._wybor][0]

    # — przebieg —
    def _dalej(self):
        self.b_dalej.setEnabled(False)
        for k in self.kafle:
            k.setEnabled(False)
        self.l_stan.setText(self.nazwa_sciezki().lower())
        self._zegar.start()

    def _tyk(self):
        self._licznik += 1
        ile = len(self.dni)
        self.postep.ustaw(self._licznik / float(max(1, ile)))
        self.l_licznik.setText("%d / %d" % (self._licznik, ile))
        if self._licznik >= ile:
            self._zegar.stop()
            self.postep.ustaw_kolory(S.ZIELEN, S.MIETA)
            self.l_stan.setText("podpisano · %s" % self.nazwa_sciezki().lower())
            self.l_stan.ustaw_kolor(S.MIETA)
            self.l_licznik.ustaw_kolor(S.MIETA)
            self.b_dalej.setText("Zamknij")
            self.b_dalej.setEnabled(True)
            try:
                self.b_dalej.clicked.disconnect()
            except Exception:
                pass
            self.b_dalej.clicked.connect(self.accept)

    # — zatrzymanie —
    def zatrzymaj_animacje(self):
        self._zegar.stop()
        self.postep.zatrzymaj_animacje()
        for k in self.kafle:
            k.zatrzymaj_animacje()
        for b in (self.b_anuluj, self.b_dalej):
            b.zatrzymaj_animacje()
        self.b_zamknij.zatrzymaj_animacje()

    def reject(self):
        self.zatrzymaj_animacje()
        super().reject()

    def accept(self):
        self.zatrzymaj_animacje()
        super().accept()


# ── lista załączników ────────────────────────────────────────────────
class ListaPlikow(QWidget):
    """Wiersze załączników: z plakietką PDF albo bez (wiersz „reszta”)."""

    def __init__(self, wiersze, rodzic=None):
        super().__init__(rodzic)
        self._wiersze = list(wiersze)          # (napis, czy_plakietka)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(int(len(self._wiersze) * 20 + 4))

    def paintEvent(self, _z):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        y = 14.0
        for napis, plakietka in self._wiersze:
            if plakietka:
                r = QRectF(0, y - 9, 24, 13)
                sc = _sciezka(r, 3.5)
                p.fillPath(sc, QBrush(S.z_alfa(S.ZIELEN, 46)))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(S.z_alfa(S.ZIELEN, 110), 1.0))
                p.drawPath(sc)
                S.tekst(p, r.x() + 4.5, y + 1.5, "PDF", S.z_alfa(S.MIETA, 220), 7.5, 800,
                        odstep=0.4)
                S.tekst(p, 32, y + 1.0, napis, S.TEKST_2, 11, 500, mono=True)
            else:
                S.tekst(p, 32, y + 1.0, napis, S.TEKST_3, 11, 500, mono=True)
            y += 20.0
        p.end()


# ── panel wysyłki ────────────────────────────────────────────────────
class PanelWysylki(Panel):
    """Adresat, gotowy temat i załączniki."""

    def __init__(self, dni, rodzic=None):
        self.dni = list(dni)
        ile = len(self.dni) + 1 if self.dni else 1
        super().__init__("Wyślij e-mailem",
                         "%s · %s 2026 · %d załączników"
                         % (D.PRACOWNIK, D.nazwa_miesiaca(9), ile), rodzic)
        self._ile_plikow = ile
        self.e_do = self.wiersz("DO", QLineEdit("kadry@pmt.pl"))
        self.e_dw = self.wiersz("DW", QLineEdit(""))
        temat = "Delegacje — %s — %s 2026" % (D.PRACOWNIK, D.nazwa_miesiaca(9))
        self.e_temat = self.wiersz("TEMAT", QLineEdit(temat))
        for pole in (self.e_do, self.e_dw, self.e_temat):
            pole.setMinimumHeight(38)
        pracownik = D.PRACOWNIK.replace(" ", "_")
        widoczne = min(ile - 1, 4)
        wiersze = [("delegacja_%02d_%s_wrzesień_2026r.pdf" % (i, pracownik), True)
                   for i in range(1, widoczne + 1)]
        if ile - 1 > widoczne:
            wiersze.append(("+ %s" % _polecenia(ile - 1 - widoczne), False))
        wiersze.append(("ewidencja_przebiegu_%s_wrzesień_2026r.pdf" % pracownik, True))
        self.wiersz("ZAŁĄCZNIKI", ListaPlikow(wiersze, self))
        self.z.addSpacing(4)

        self.l_stan, self.l_licznik = self.wiersz_stanu(
            "gotowe do wysyłki", "0 / %d" % ile)
        self.postep = PasekPostepu(S.CYJAN, S.ZIELEN, self)
        self.z.addWidget(self.postep)

        self.b_anuluj = Przycisk("Anuluj", "zwykly", 13, self)
        self.b_anuluj.clicked.connect(self.reject)
        self.b_wyslij = Przycisk("Wyślij", "glowny", 13, self)
        self.b_wyslij.setAutoDefault(True)
        self.b_wyslij.setDefault(True)
        self.b_wyslij.clicked.connect(self._wyslij)
        self.stopka(self.b_anuluj, self.b_wyslij)

        self._i = 0
        self._zegar = QTimer(self)
        self._zegar.setInterval(max(110, int(1600 / max(1, ile))))
        self._zegar.timeout.connect(self._tyk)

    def _wyslij(self):
        self.b_wyslij.setEnabled(False)
        self.l_stan.setText("załączniki")
        self._zegar.start()

    def _tyk(self):
        self._i += 1
        self.postep.ustaw(self._i / float(max(1, self._ile_plikow)))
        self.l_licznik.setText("%d / %d" % (self._i, self._ile_plikow))
        if self._i >= self._ile_plikow:
            self._zegar.stop()
            self.postep.ustaw_kolory(S.ZIELEN, S.MIETA)
            self.l_stan.setText("wysłano 14:26 · %s" % self.e_do.text())
            self.l_stan.ustaw_kolor(S.MIETA)
            self.l_licznik.ustaw_kolor(S.MIETA)
            self.b_wyslij.setText("Zamknij")
            self.b_wyslij.setEnabled(True)
            try:
                self.b_wyslij.clicked.disconnect()
            except Exception:
                pass
            self.b_wyslij.clicked.connect(self.accept)

    def zatrzymaj_animacje(self):
        self._zegar.stop()
        self.postep.zatrzymaj_animacje()
        for b in (self.b_anuluj, self.b_wyslij):
            b.zatrzymaj_animacje()
        self.b_zamknij.zatrzymaj_animacje()

    def reject(self):
        self.zatrzymaj_animacje()
        super().reject()

    def accept(self):
        self.zatrzymaj_animacje()
        super().accept()


# ── zrzuty ───────────────────────────────────────────────────────────
def _tlo_pod_panel(rozmiar):
    pix = QPixmap(rozmiar)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    S.tlo_sceny(p, QRectF(0, 0, rozmiar.width(), rozmiar.height()))
    p.end()
    return pix


def _zrzut_panelu(app, panel, nazwa):
    panel.show()
    for _ in range(6):
        app.processEvents()
    panel.zatrzymaj_animacje()
    for _ in range(4):
        app.processEvents()
    tlo = _tlo_pod_panel(panel.size())
    p = QPainter(tlo)
    p.drawPixmap(0, 0, panel.grab())
    p.end()
    tlo.save(nazwa)
    panel.close()
    print("zapisano", nazwa)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setFont(S.czcionka(13))
    dni = D.oblicz_miesiac(4200, wolne=(14, 15))
    okno = QWidget()
    okno.resize(1440, 430)
    okno.setStyleSheet(S.qss())
    l = QVBoxLayout(okno)
    l.setContentsMargins(0, 0, 0, 0)
    taca = TacaDokumentow()
    l.addStretch(1)
    l.addWidget(taca)
    okno.show()
    taca.ustaw_dni(dni)

    if "--zrzut" in sys.argv:
        for _ in range(6):
            app.processEvents()
        taca.zatrzymaj_animacje()
        for _ in range(4):
            app.processEvents()
        okno.grab().save("zrzut_taca.png")
        print("zapisano zrzut_taca.png")
        w_trasie = [d for d in dni if not d.wolny]
        _zrzut_panelu(app, PanelPodpisu(w_trasie), "zrzut_taca_podpis.png")
        _zrzut_panelu(app, PanelWysylki(w_trasie), "zrzut_taca_wysylka.png")
        sys.exit(0)
    sys.exit(app.exec())
