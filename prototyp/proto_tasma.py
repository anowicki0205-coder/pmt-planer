# -*- coding: utf-8 -*-
"""Taśma miesiąca — poziomy pasek wszystkich dni, tuż pod paskiem tytułowym.

Jeden kafel to jeden dzień: skrót dnia tygodnia z numerem, miniatura trasy
i kwota. Dzień bez trasy jest tylko wygaszony, a napis „wolne” dostaje wyłącznie
dzień wyłączony przez użytkownika. Dzień wybrany jest uniesiony i ma jasną obwódkę, dzisiejszy dostaje
cyjanową obwódkę i plakietkę DZIŚ z dziobkiem. Po wygenerowaniu dokumentów
dni w trasie dostają plakietkę PDF, a dzień podpisany zielony znacznik.

Barwy, czcionki i pomocniki rysowania pochodzą z proto_styl, dane z proto_dane.
"""
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QEvent, pyqtSignal
from PyQt6.QtGui import (QPainter, QPainterPath, QPen, QBrush, QColor,
                         QLinearGradient, QRadialGradient, QFontMetricsF)
from PyQt6.QtWidgets import QWidget, QToolTip

from proto_styl import (TLO_GORA, TEKST, TEKST_2, TEKST_3,
                        CYJAN, ZIELEN, MIETA, BURSZTYN,
                        z_alfa, czcionka, szklo, cien, poswiata_linii,
                        punkt_swiatla, tekst)
import proto_dane as dane

# ── miary taśmy (wprost z zatwierdzonego projektu) ───────────────────
PAD_BOK      = 24.0     # margines lewy i prawy
PAD_GORA     = 14.0
H_NAGLOWEK   = 17.0     # wiersz z napisem i liczbami zbiorczymi
ODSTEP_PION  = 13.0     # luz na plakietkę DZIŚ
H_KAFLA      = 58.0
H_TASMY      = 118      # docelowa wysokość całości
ODSTEP       = 4.0      # przerwa między kaflami
PROMIEN      = 9.0
BIEL         = QColor(255, 255, 255)


def _postoje_txt(n):
    """1 postój, 2 postoje, 5 postojów — polska odmiana."""
    if n == 1:
        return "1 postój"
    r, s = n % 10, n % 100
    if 2 <= r <= 4 and not (12 <= s <= 14):
        return "%d postoje" % n
    return "%d postojów" % n


def _dopasuj(napisy, maks, rozmiary, **kw):
    """Największy rozmiar i pierwszy wariant napisu, który mieści się w maks."""
    for napis in napisy:
        for r in rozmiary:
            if QFontMetricsF(czcionka(r, **kw)).horizontalAdvance(napis) <= maks:
                return napis, r
    return napisy[-1], rozmiary[-1]


class TasmaMiesiaca(QWidget):
    """Pasek dni miesiąca. Kliknięcie wybiera dzień, prawy przycisk przełącza wolne."""

    wybrano = pyqtSignal(int)
    przelaczono_wolny = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dni = []
        self._dzis = 0
        self._wybrany = 0
        self._stan = "zwykly"
        self._pod_kursorem = -1
        self._zbior = dane.podsumowanie([])
        self.setMouseTracking(True)
        self.setMinimumHeight(84)
        self.setMinimumWidth(420)
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # ── stan publiczny ───────────────────────────────────────────────
    def sizeHint(self):
        return QSize(int(2 * PAD_BOK + 31 * 39 + 30 * ODSTEP), H_TASMY)

    def _przelicz(self):
        # dni wyłączone przez użytkownika nie wchodzą do sum w nagłówku
        licz = [d for d in self._dni if not self._wylaczony(d)]
        z = dane.podsumowanie(licz)
        z["dni_wszystkie"] = len(self._dni)
        self._zbior = z

    @staticmethod
    def _wylaczony(d):
        return bool(getattr(d, "wylaczony", False))

    def ustaw_dni(self, lista_dni):
        self._dni = list(lista_dni or [])
        self._przelicz()
        if self._wybrany and not self._dzien(self._wybrany):
            self._wybrany = 0
        self.update()

    def ustaw_dzis(self, numer_dnia):
        self._dzis = int(numer_dnia or 0)
        self.update()

    def ustaw_wybrany(self, numer_dnia):
        self._wybrany = int(numer_dnia or 0)
        self.update()

    def ustaw_stan(self, nazwa):
        self._stan = "po_generacji" if nazwa == "po_generacji" else "zwykly"
        self.update()

    @property
    def wybrany(self):
        return self._wybrany

    @wybrany.setter
    def wybrany(self, numer_dnia):
        self.ustaw_wybrany(numer_dnia)

    @property
    def dzis(self):
        return self._dzis

    @property
    def stan(self):
        return self._stan

    @property
    def dni(self):
        return list(self._dni)

    def _dzien(self, numer):
        for d in self._dni:
            if d.data.day == numer:
                return d
        return None

    # ── układ ────────────────────────────────────────────────────────
    def _pas(self):
        gora = PAD_GORA + H_NAGLOWEK + ODSTEP_PION
        wys = max(34.0, min(H_KAFLA, self.height() - gora - 6.0))
        return QRectF(PAD_BOK, gora, max(1.0, self.width() - 2 * PAD_BOK), wys)

    def _kafle(self):
        n = len(self._dni)
        if n <= 0:
            return []
        pas = self._pas()
        odstep = ODSTEP if n > 1 else 0.0
        szer = (pas.width() - odstep * (n - 1)) / float(n)
        if szer < 8.0:
            szer, odstep = max(4.0, pas.width() / n), 0.0
        return [QRectF(pas.x() + i * (szer + odstep), pas.y(), szer, pas.height())
                for i in range(n)]

    def _indeks(self, punkt):
        for i, r in enumerate(self._kafle()):
            if r.adjusted(-ODSTEP / 2, -6, ODSTEP / 2, 2).contains(punkt):
                return i
        return -1

    # ── zdarzenia ────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        i = self._indeks(e.position())
        if i < 0:
            super().mousePressEvent(e)
            return
        d = self._dni[i]
        if e.button() == Qt.MouseButton.LeftButton:
            self.ustaw_wybrany(d.data.day)
            self.wybrano.emit(d.data.day)
        elif e.button() == Qt.MouseButton.RightButton:
            d.wylaczony = not self._wylaczony(d)
            self._przelicz()
            self.update()
            self.przelaczono_wolny.emit(d.data.day)

    def mouseMoveEvent(self, e):
        i = self._indeks(e.position())
        if i != self._pod_kursorem:
            self._pod_kursorem = i
            self.setCursor(Qt.CursorShape.PointingHandCursor if i >= 0
                           else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        if self._pod_kursorem != -1:
            self._pod_kursorem = -1
            self.update()
        super().leaveEvent(e)

    def event(self, e):
        if e.type() == QEvent.Type.ToolTip:
            i = self._indeks(QPointF(e.pos()))
            if i >= 0:
                QToolTip.showText(e.globalPos(), self._podpowiedz(self._dni[i]), self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    def _podpowiedz(self, d):
        nag = "%s %02d.%02d.%d" % (dane.DNI_PL[d.data.weekday()],
                                   d.data.day, d.data.month, d.data.year)
        if self._wylaczony(d):
            return "%s\nwolne" % nag
        if d.wolny or d.postoje == 0:
            return "%s\nbez trasy" % nag
        return "%s\n%s · %s km\n%s zł" % (nag, _postoje_txt(d.postoje),
                                          dane.zl(d.km, grosze=False), dane.zl(d.kwota))

    # ── rysowanie ────────────────────────────────────────────────────
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self._rysuj_naglowek(p)
        kafle = self._kafle()
        gorne = []
        for i, r in enumerate(kafle):
            d = self._dni[i]
            if d.data.day in (self._dzis, self._wybrany):
                gorne.append((i, r, d))
            else:
                self._rysuj_kafel(p, r, d, i)
        for i, r, d in gorne:
            self._rysuj_kafel(p, r, d, i)
        # plakietki idą na wierzch, żeby sąsiedni kafel ich nie przykrył
        if self._stan == "po_generacji":
            for i, r in enumerate(kafle):
                d = self._dni[i]
                if d.wolny or d.postoje == 0 or self._wylaczony(d):
                    continue
                ru = self._uniesienie(r, d)
                # pod plakietką DZIŚ nie ma miejsca — tam znacznik idzie na dół kafla
                self._plakietka_pdf(p, ru, na_dole=(d.data.day == self._dzis))
                if d.podpisany:
                    self._znacznik_podpisu(p, ru)
        for i, r, d in gorne:
            if d.data.day == self._dzis:
                self._plakietka_dzis(p, self._uniesienie(r, d))
        p.end()

    def _uniesienie(self, r, d):
        if d.data.day == self._wybrany:
            return r.adjusted(-1.2, -4.0, 1.2, 1.2)
        return r

    def _rysuj_naglowek(self, p):
        y = PAD_GORA + 12.5
        tekst(p, PAD_BOK, y, "TAŚMA MIESIĄCA", kolor=z_alfa(ZIELEN, 60),
              rozmiar=12, waga=600, naglowek=True, odstep=1.3)
        tekst(p, PAD_BOK, y, "TAŚMA MIESIĄCA", kolor=MIETA,
              rozmiar=12, waga=600, naglowek=True, odstep=1.3)

        z = self._zbior
        grupy = [(dane.zl(z["kwota"], grosze=False) + " zł", ""),
                 (dane.zl(z["km"], grosze=False) + " km", ""),
                 (str(z["dni"]), "z %d dni" % z["dni_wszystkie"])]
        f_w = czcionka(12, 700, mono=True)
        f_s = czcionka(12, 400)
        fm_w, fm_s = QFontMetricsF(f_w), QFontMetricsF(f_s)
        x = self.width() - PAD_BOK
        for wart, sufiks in reversed(grupy):
            if sufiks:
                x -= fm_s.horizontalAdvance(sufiks)
                tekst(p, x, y, sufiks, kolor=TEKST_2, rozmiar=12)
                x -= 4.0
            x -= fm_w.horizontalAdvance(wart)
            tekst(p, x, y, wart, kolor=TEKST, rozmiar=12, waga=700, mono=True)
            x -= 16.0

    def _aureola(self, p, sciezka, kolor, warstwy):
        p.setBrush(Qt.BrushStyle.NoBrush)
        for szer, alfa in warstwy:
            p.setPen(QPen(z_alfa(kolor, alfa), szer))
            p.drawPath(sciezka)

    def _rysuj_kafel(self, p, rbaza, d, i):
        dzis = (d.data.day == self._dzis)
        wyb = (d.data.day == self._wybrany)
        wyl = self._wylaczony(d)
        ma_trase = (not wyl) and (not d.wolny) and d.postoje > 0
        pod = (i == self._pod_kursorem)
        po_gen = (self._stan == "po_generacji")
        r = self._uniesienie(rbaza, d)

        prom = min(PROMIEN, r.width() * 0.26)
        sciezka = QPainterPath()
        sciezka.addRoundedRect(r, prom, prom)

        weekend = d.data.weekday() >= 5

        # tło kafla
        if wyl:
            p.fillPath(sciezka, z_alfa(BIEL, 7))
        else:
            cien(p, r, prom, sila=150 if (wyb or dzis) else 90,
                 rozmycie=10 if (wyb or dzis) else 6, przesun=5)
            szklo(p, r, prom, mocne=False, obrys=False, rozblysk=True)
            if weekend and not ma_trase:
                p.fillPath(sciezka, z_alfa(TLO_GORA, 120))   # weekend głębiej w tle
        if ma_trase:
            baza = CYJAN if dzis else ZIELEN
            g = QLinearGradient(r.topLeft(), r.bottomLeft())
            g.setColorAt(0.0, z_alfa(baza, 82 if (wyb or dzis) else 62))
            g.setColorAt(1.0, z_alfa(baza, 16))
            p.fillPath(sciezka, QBrush(g))

        # obwódka
        if dzis:
            self._aureola(p, sciezka, CYJAN, ((9.0, 12), (5.0, 24), (2.6, 48)))
            pen = QPen(CYJAN, 1.6)
        elif wyb:
            if ma_trase:
                self._aureola(p, sciezka, ZIELEN, ((7.0, 14), (3.5, 24)))
            pen = QPen(z_alfa(TEKST, 235), 1.4)
        elif ma_trase:
            self._aureola(p, sciezka, ZIELEN, ((6.0, 10), (3.0, 18)))
            pen = QPen(z_alfa(ZIELEN, 130), 1.2)
        elif wyl:
            pen = QPen(z_alfa(BURSZTYN, 130 if pod else 100), 1.0)
            pen.setStyle(Qt.PenStyle.CustomDashLine)
            pen.setDashPattern([3.0, 3.0])
        else:
            pen = QPen(z_alfa(BIEL, 60 if pod else (14 if weekend else 26)), 1.0)
        if pod and not (wyb or dzis) and ma_trase:
            pen.setColor(z_alfa(MIETA, 210))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen)
        p.drawPath(sciezka)
        if wyb:
            zew = QPainterPath()
            zew.addRoundedRect(r.adjusted(-2.0, -2.0, 2.0, 2.0), prom + 2, prom + 2)
            p.setPen(QPen(z_alfa(TEKST, 200), 1.8))
            p.drawPath(zew)

        # miejsce zajęte przez plakietki (rysowane osobno, na wierzchu)
        z_lewej = 0.0
        z_prawej = 0.0
        if po_gen and ma_trase:
            z_prawej = 3.5
            if d.podpisany:
                z_lewej = 3.5

        # etykieta dnia
        if wyb or dzis:
            kol_etyk, waga = TEKST, 700
        elif ma_trase:
            kol_etyk, waga = MIETA, 600
        elif wyl:
            kol_etyk, waga = TEKST_2, 500
        elif weekend:
            kol_etyk, waga = z_alfa(TEKST_3, 130), 500
        else:
            kol_etyk, waga = TEKST_3, 500
        maks = max(10.0, r.width() - 6.0 - z_lewej - z_prawej)
        napis, rozm = _dopasuj([d.etykieta, str(d.data.day)], maks, (10, 9, 8), waga=waga)
        srodek = r.center().x() + (z_lewej - z_prawej) * 0.5
        szer_n = QFontMetricsF(czcionka(rozm, waga)).horizontalAdvance(napis)
        tekst(p, srodek - szer_n / 2.0, r.top() + 15.0, napis, kolor=kol_etyk,
              rozmiar=rozm, waga=waga)

        # środek: miniatura trasy albo przekreślenie
        pole = QRectF(r.left() + 5.0, r.top() + r.height() * 0.33,
                      r.width() - 10.0, r.height() * 0.27)
        if ma_trase:
            self._rysuj_miniature(p, sciezka, pole, d, CYJAN if dzis else
                                  (MIETA if wyb else ZIELEN), wyb or dzis)
        elif wyl:
            p.setPen(QPen(z_alfa(BURSZTYN, 70), 1.0))
            p.drawLine(QPointF(pole.left() + 3.5, pole.bottom() + 1.0),
                       QPointF(pole.right() - 3.5, pole.top() - 1.0))

        # dół: kwota albo napis wolne
        if ma_trase:
            warianty = ["%s zł" % dane.zl(d.kwota, grosze=False),
                        dane.zl(d.kwota, grosze=False)]
            napis, rozm = _dopasuj(warianty, r.width() - 6.0, (10, 9, 8),
                                   waga=700, mono=True)
            szer_n = QFontMetricsF(czcionka(rozm, 700, mono=True)).horizontalAdvance(napis)
            tekst(p, r.center().x() - szer_n / 2.0, r.bottom() - 8.0, napis,
                  kolor=TEKST, rozmiar=rozm, waga=700, mono=True)
        elif wyl:
            napis, rozm = _dopasuj(["wolne", "—"], r.width() - 6.0, (9, 8), waga=500)
            szer_n = QFontMetricsF(czcionka(rozm, 500)).horizontalAdvance(napis)
            tekst(p, r.center().x() - szer_n / 2.0, r.bottom() - 8.0, napis,
                  kolor=BURSZTYN, rozmiar=rozm, waga=500)

    def _rysuj_miniature(self, p, obrys_kafla, pole, d, kolor, mocno):
        punkty = self._punkty_trasy(d, pole)
        if not punkty:
            return
        sc = QPainterPath(punkty[0])
        for i in range(1, len(punkty) - 1):
            sr = QPointF((punkty[i].x() + punkty[i + 1].x()) / 2.0,
                         (punkty[i].y() + punkty[i + 1].y()) / 2.0)
            sc.quadTo(punkty[i], sr)
        sc.lineTo(punkty[-1])
        p.save()
        p.setClipPath(obrys_kafla)
        poswiata_linii(p, sc, kolor, ((5.0, 18 if mocno else 12),
                                      (2.6, 56 if mocno else 42),
                                      (1.3, 245)))
        punkt_swiatla(p, punkty[0], 4.0, kolor, 140)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(TEKST if mocno else MIETA))
        p.drawEllipse(punkty[0], 1.8, 1.8)
        p.restore()

    def _punkty_trasy(self, d, pole):
        """Przystanki dnia przeniesione w prostokąt miniatury (bez powrotu do bazy)."""
        nazwy = [dane.BAZA] + [m for m in d.przystanki if m in dane.MIASTA]
        if len(nazwy) < 2:
            return []
        xy = [dane.MIASTA[m] for m in nazwy]
        xs = [a for a, _ in xy]
        ys = [b for _, b in xy]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        rozp = max(x1 - x0, y1 - y0, 1e-6)
        sx = max(x1 - x0, rozp * 0.42)
        sy = max(y1 - y0, rozp * 0.42)
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        pkt = [QPointF(pole.center().x() + (a - cx) / sx * pole.width(),
                       pole.center().y() + (b - cy) / sy * pole.height())
               for a, b in xy]
        if len(pkt) >= 3:   # jedno przejście wygładzające — bez kolców
            wyg = [pkt[0]]
            for i in range(1, len(pkt) - 1):
                a, b, c = pkt[i - 1], pkt[i], pkt[i + 1]
                wyg.append(QPointF(0.25 * a.x() + 0.5 * b.x() + 0.25 * c.x(),
                                   0.25 * a.y() + 0.5 * b.y() + 0.25 * c.y()))
            wyg.append(pkt[-1])
            pkt = wyg
        return pkt

    def _plakietka_dzis(self, p, r):
        f = czcionka(10, 700, naglowek=True, odstep=0.8)
        fm = QFontMetricsF(f)
        szer = fm.horizontalAdvance("DZIŚ") + 16.0
        wys = 16.0
        pr = QRectF(r.center().x() - szer / 2.0, r.top() - 19.0, szer, wys)
        # dziobek
        dzb = QPainterPath()
        dzb.moveTo(r.center().x() - 4.0, pr.bottom() - 1.0)
        dzb.lineTo(r.center().x() + 4.0, pr.bottom() - 1.0)
        dzb.lineTo(r.center().x(), r.top() + 1.5)
        dzb.closeSubpath()
        sc = QPainterPath()
        sc.addRoundedRect(pr, wys / 2.0, wys / 2.0)
        sc = sc.united(dzb)
        self._aureola(p, sc, CYJAN, ((10.0, 26), (5.0, 52)))
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(sc, QBrush(CYJAN))
        p.setPen(QPen(z_alfa(BIEL, 90), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(sc)
        p.setPen(QPen(TLO_GORA))
        p.setFont(f)
        p.drawText(pr, int(Qt.AlignmentFlag.AlignCenter), "DZIŚ")

    def _plakietka_pdf(self, p, r, na_dole=False):
        f = czcionka(6, 800)
        fm = QFontMetricsF(f)
        szer = fm.horizontalAdvance("PDF") + 4.0
        gora = (r.bottom() - 5.0) if na_dole else (r.top() - 4.0)
        pr = QRectF(r.right() - szer + szer * 0.30, gora, szer, 9.5)
        sc = QPainterPath()
        sc.addRoundedRect(pr, 2.5, 2.5)
        self._aureola(p, sc, ZIELEN, ((5.0, 40),))
        g = QLinearGradient(pr.topLeft(), pr.bottomLeft())
        g.setColorAt(0.0, MIETA)
        g.setColorAt(1.0, ZIELEN)
        p.fillPath(sc, QBrush(g))
        p.setPen(QPen(TLO_GORA))
        p.setFont(f)
        p.drawText(pr, int(Qt.AlignmentFlag.AlignCenter), "PDF")

    def _znacznik_podpisu(self, p, r):
        sr = QPointF(r.left() + 1.5, r.top() + 0.5)
        prom = 5.6
        rg = QRadialGradient(QPointF(sr.x() - prom * 0.3, sr.y() - prom * 0.4), prom * 1.6)
        rg.setColorAt(0.0, MIETA)
        rg.setColorAt(0.55, ZIELEN)
        rg.setColorAt(1.0, ZIELEN.darker(150))
        p.setPen(QPen(z_alfa(TLO_GORA, 220), 1.5))
        p.setBrush(QBrush(rg))
        p.drawEllipse(sr, prom, prom)
        pen = QPen(TLO_GORA, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        ptak = QPainterPath()
        ptak.moveTo(sr.x() - 2.6, sr.y() + 0.2)
        ptak.lineTo(sr.x() - 0.8, sr.y() + 2.0)
        ptak.lineTo(sr.x() + 2.8, sr.y() - 2.2)
        p.drawPath(ptak)


# ── sprawdzenie ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout
    from proto_styl import tlo_sceny, qss

    class _Okno(QWidget):
        def paintEvent(self, _e):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            tlo_sceny(p, QRectF(self.rect()))
            p.end()

    app = QApplication(sys.argv)
    app.setStyleSheet(qss())

    okno = _Okno()
    okno.resize(1380, 200)
    ukl = QVBoxLayout(okno)
    ukl.setContentsMargins(0, 0, 0, 0)
    ukl.setSpacing(0)
    tasma = TasmaMiesiaca(okno)
    tasma.setFixedHeight(H_TASMY)
    ukl.addWidget(tasma)
    ukl.addStretch(1)

    tasma.ustaw_dni(dane.oblicz_miesiac(1850, wolne=(14, 15)))
    tasma.ustaw_dzis(11)
    tasma.ustaw_wybrany(2)
    tasma.wybrano.connect(lambda n: print("wybrano", n))
    tasma.przelaczono_wolny.connect(lambda n: print("wolny", n))

    okno.show()
    app.processEvents()
    okno.grab().save("zrzut_tasma.png")

    tasma.ustaw_stan("po_generacji")
    app.processEvents()
    okno.grab().save("zrzut_tasma_po.png")
    print("zapisano zrzut_tasma.png i zrzut_tasma_po.png")

    if "--pokaz" in sys.argv:
        sys.exit(app.exec())
