# -*- coding: utf-8 -*-
"""
LOGO RETRO-FUTURYSTYCZNE PMT — generator obrazu.

Rysuje logo w całości kodem (Qt), bez żadnych zewnętrznych plików i bez
dodatkowych bibliotek poza tymi, które program już ma. Dzięki temu nie
dokłada nic do paczki i nie daje antywirusowi nowych powodów do nerwów.

    python logo_retro.py                 → pmt_logo_retro.png (1024×1024)
    python logo_retro.py --rozmiar 512   → inny rozmiar
    python logo_retro.py --ikona         → dodatkowo pmt_logo_retro.ico
    python logo_retro.py --jasny         → wariant na jasne tło

Program używa tego pliku AUTOMATYCZNIE, jeśli leży obok niego
(pmt_logo_retro.png ma pierwszeństwo przed pmt_logo.png). Nie chcesz go —
po prostu skasuj plik .png, nic więcej nie trzeba zmieniać.

Motyw: zachód słońca nad neonową siatką — kanon estetyki retro-futurystycznej
(synthwave), przełożony na znak firmowy: słońce z poziomymi przecięciami,
horyzont, siatka uciekająca do punktu zbiegu i chromowany napis PMT.
"""

import math
import os
import sys

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QLinearGradient,
                         QPainter, QPainterPath, QPen, QPixmap, QRadialGradient)
from PyQt6.QtWidgets import QApplication

# ── PALETY ───────────────────────────────────────────────────────────────
CIEMNY = dict(
    tlo_gora="#14052E", tlo_dol="#3B0A55",
    slonce_gora="#FFE39A", slonce_srodek="#FF8A3D", slonce_dol="#FF2E7E",
    siatka="#00F0FF", horyzont="#FF3DA6",
    napis_gora="#FFFFFF", napis_srodek="#8FE9FF", napis_dol="#2E7BE0",
    poswiata="#00F0FF", gwiazdy="#FFFFFF",
)
JASNY = dict(
    tlo_gora="#FFE9D6", tlo_dol="#FFC9C0",
    slonce_gora="#FFFFFF", slonce_srodek="#FF9A4D", slonce_dol="#E0246B",
    siatka="#0D9488", horyzont="#E0246B",
    napis_gora="#0B2540", napis_srodek="#0D9488", napis_dol="#07304F",
    poswiata="#0D9488", gwiazdy="#FFFFFF",
)


def _k(hex_kolor, alfa=255):
    c = QColor(hex_kolor)
    c.setAlpha(alfa)
    return c


def _czcionka_gruba(rozmiar_px):
    """Najgrubsza dostępna czcionka bezszeryfowa. Kolejność zgodna z tym,
    czego program używa w interfejsie — na Windows wyjdzie Segoe UI."""
    for nazwa in ("Segoe UI Black", "Segoe UI", "Arial Black", "Arial",
                  "DejaVu Sans", "Liberation Sans"):
        f = QFont(nazwa)
        f.setPixelSize(rozmiar_px)
        f.setWeight(QFont.Weight.Black)
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 112)
        if QFontMetricsF(f).horizontalAdvance("PMT") > 0:
            return f
    f = QFont()
    f.setPixelSize(rozmiar_px)
    f.setWeight(QFont.Weight.Black)
    return f


def _gwiazdy(p, R, pal, horyzont_y):
    """Rozsiane punkty na niebie. Rozkład deterministyczny (bez random) —
    ten sam kod zawsze daje ten sam obrazek."""
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(90):
        # ciąg liczb „rozrzucony", ale w pełni powtarzalny
        x = (math.sin(i * 12.9898) * 43758.5453) % 1.0
        y = (math.sin(i * 78.233) * 12345.6789) % 1.0
        px, py = x * R, y * horyzont_y * 0.94
        r = 0.0016 * R * (1.0 + ((i * 7) % 5) / 3.0)
        jasnosc = 70 + (i * 37) % 150
        p.setBrush(_k(pal["gwiazdy"], jasnosc))
        p.drawEllipse(QPointF(px, py), r, r)


def _slonce(p, R, pal, cx, cy, promien):
    """Słońce z poziomymi przecięciami — znak rozpoznawczy tej estetyki.
    Przecięcia gęstnieją ku dołowi, dokładnie jak na plakatach z lat 80."""
    g = QLinearGradient(cx, cy - promien, cx, cy + promien)
    g.setColorAt(0.00, _k(pal["slonce_gora"]))
    g.setColorAt(0.45, _k(pal["slonce_srodek"]))
    g.setColorAt(1.00, _k(pal["slonce_dol"]))

    sciezka = QPainterPath()
    sciezka.addEllipse(QPointF(cx, cy), promien, promien)
    p.save()
    p.setClipPath(sciezka)
    p.fillRect(QRectF(cx - promien, cy - promien, 2 * promien, 2 * promien), QBrush(g))

    # przecięcia: im niżej, tym grubsze i gęstsze
    p.setPen(Qt.PenStyle.NoPen)
    y = cy - promien * 0.12
    krok = promien * 0.135
    grubosc = promien * 0.022
    while y < cy + promien:
        p.setBrush(_k(pal["tlo_dol"], 235))
        p.drawRect(QRectF(cx - promien, y, 2 * promien, grubosc))
        y += krok
        krok *= 0.90
        grubosc *= 1.16
    p.restore()

    # poświata dookoła słońca
    pos = QRadialGradient(QPointF(cx, cy), promien * 1.9)
    pos.setColorAt(0.55, _k(pal["slonce_srodek"], 0))
    pos.setColorAt(0.78, _k(pal["slonce_dol"], 60))
    pos.setColorAt(1.00, _k(pal["slonce_dol"], 0))
    p.setBrush(QBrush(pos))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(cx, cy), promien * 1.9, promien * 1.9)


def _siatka(p, R, pal, horyzont_y):
    """Perspektywiczna siatka: linie pionowe zbiegają się w punkcie na
    horyzoncie, poziome zagęszczają się ku niemu."""
    cx = R / 2.0
    dol = R * 1.02

    # linie uciekające do punktu zbiegu
    for i in range(-14, 15):
        x_dol = cx + i * (R * 0.135)
        pen = QPen(_k(pal["siatka"], 150 if i % 2 == 0 else 90))
        pen.setWidthF(max(1.0, R * 0.0026))
        p.setPen(pen)
        p.drawLine(QPointF(cx, horyzont_y), QPointF(x_dol, dol))

    # linie poziome — odstęp rośnie geometrycznie w dół
    y = horyzont_y
    krok = R * 0.0075
    while y < dol:
        alfa = int(40 + 190 * min(1.0, (y - horyzont_y) / (dol - horyzont_y)))
        pen = QPen(_k(pal["siatka"], alfa))
        pen.setWidthF(max(1.0, R * 0.0022 * (1 + (y - horyzont_y) / R)))
        p.setPen(pen)
        p.drawLine(QPointF(0, y), QPointF(R, y))
        y += krok
        krok *= 1.26


def _napis(p, R, pal, cx, cy):
    """Chromowany napis PMT: gradient pionowy z ostrym przejściem w połowie
    (tak wygląda odbicie w chromie) plus neonowy kontur i cień."""
    f = _czcionka_gruba(int(R * 0.255))
    p.setFont(f)
    fm = QFontMetricsF(f)
    tekst = "PMT"
    szer = fm.horizontalAdvance(tekst)
    sciezka = QPainterPath()
    sciezka.addText(QPointF(cx - szer / 2.0, cy + fm.capHeight() / 2.0), f, tekst)

    # cień pod napisem
    p.save()
    p.translate(0, R * 0.012)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_k("#000000", 120))
    p.drawPath(sciezka)
    p.restore()

    # poświata neonowa (kilka warstw coraz węższych)
    for szerokosc, alfa in ((R * 0.045, 26), (R * 0.028, 40), (R * 0.014, 70)):
        pen = QPen(_k(pal["poswiata"], alfa))
        pen.setWidthF(szerokosc)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(sciezka)

    # wypełnienie „chrom"
    gr = QLinearGradient(0, cy - R * 0.16, 0, cy + R * 0.16)
    gr.setColorAt(0.00, _k(pal["napis_gora"]))
    gr.setColorAt(0.46, _k(pal["napis_srodek"]))
    gr.setColorAt(0.50, _k(pal["napis_gora"]))
    gr.setColorAt(0.54, _k(pal["napis_dol"]))
    gr.setColorAt(1.00, _k(pal["napis_dol"]))
    p.setBrush(QBrush(gr))
    pen = QPen(_k(pal["horyzont"], 220))
    pen.setWidthF(max(1.0, R * 0.006))
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawPath(sciezka)


def narysuj_logo(rozmiar=1024, ciemny=True) -> QPixmap:
    """Zwraca gotowe logo jako QPixmap (kwadrat, przezroczyste narożniki)."""
    pal = CIEMNY if ciemny else JASNY
    R = float(rozmiar)
    pix = QPixmap(rozmiar, rozmiar)
    pix.fill(QColor(0, 0, 0, 0))

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    # okrągła „moneta" — logo wpisuje się w koło, jak dotychczasowe
    koło = QPainterPath()
    koło.addEllipse(QRectF(R * 0.012, R * 0.012, R * 0.976, R * 0.976))
    p.setClipPath(koło)

    horyzont_y = R * 0.615

    # niebo
    niebo = QLinearGradient(0, 0, 0, horyzont_y)
    niebo.setColorAt(0.0, _k(pal["tlo_gora"]))
    niebo.setColorAt(1.0, _k(pal["tlo_dol"]))
    p.fillRect(QRectF(0, 0, R, horyzont_y), QBrush(niebo))
    _gwiazdy(p, R, pal, horyzont_y)

    # ziemia
    ziemia = QLinearGradient(0, horyzont_y, 0, R)
    ziemia.setColorAt(0.0, _k(pal["tlo_dol"]))
    ziemia.setColorAt(1.0, _k(pal["tlo_gora"]))
    p.fillRect(QRectF(0, horyzont_y, R, R - horyzont_y), QBrush(ziemia))

    _slonce(p, R, pal, R * 0.5, horyzont_y - R * 0.115, R * 0.245)
    _siatka(p, R, pal, horyzont_y)

    # świecąca linia horyzontu
    for szer, alfa in ((R * 0.030, 45), (R * 0.012, 110), (R * 0.004, 255)):
        pen = QPen(_k(pal["horyzont"], alfa))
        pen.setWidthF(szer)
        p.setPen(pen)
        p.drawLine(QPointF(0, horyzont_y), QPointF(R, horyzont_y))

    _napis(p, R, pal, R * 0.5, R * 0.495)

    # obwódka monety
    p.setClipping(False)
    pen = QPen(_k(pal["siatka"], 210))
    pen.setWidthF(R * 0.016)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(R * 0.012, R * 0.012, R * 0.976, R * 0.976))
    p.end()
    return pix


def main():
    rozmiar = 1024
    if "--rozmiar" in sys.argv:
        try:
            rozmiar = int(sys.argv[sys.argv.index("--rozmiar") + 1])
        except Exception:
            pass
    ciemny = "--jasny" not in sys.argv
    katalog = os.path.dirname(os.path.abspath(__file__))

    app = QApplication.instance() or QApplication(sys.argv)   # noqa: F841
    pix = narysuj_logo(rozmiar, ciemny)
    cel = os.path.join(katalog, "pmt_logo_retro.png")
    pix.save(cel, "PNG")
    print("zapisano: %s (%d×%d)" % (cel, rozmiar, rozmiar))

    if "--ikona" in sys.argv:
        cel_ico = os.path.join(katalog, "pmt_logo_retro.ico")
        # Windows chce kilku rozmiarów w jednym pliku — Qt zapisuje jeden,
        # więc bierzemy 256 px (tego używa pasek zadań i Eksplorator).
        pix.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio,
                   Qt.TransformationMode.SmoothTransformation).save(cel_ico, "ICO")
        print("zapisano: %s" % cel_ico)
    return 0


if __name__ == "__main__":
    sys.exit(main())
