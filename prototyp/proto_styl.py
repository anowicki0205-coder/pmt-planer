# -*- coding: utf-8 -*-
"""Wspólny język wizualny prototypu nowego wyglądu PMT Planera (wariant A).

Tu mieszkają kolory, czcionki i pomocniki do rysowania. Reszta prototypu
nie definiuje własnych barw ani nie dobiera czcionek — wszystko idzie stąd,
żeby ekran trzymał się kupy.
"""
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QLinearGradient, QRadialGradient,
                         QPainter, QPainterPath, QPen, QBrush, QImage)

# ── barwy ────────────────────────────────────────────────────────────
TLO_GORA      = QColor("#050A14")
TLO_DOL       = QColor("#0B1320")
SZYNA         = QColor("#0A101B")
POWIERZCHNIA  = QColor(17, 28, 46, 184)     # szkło kart
POWIERZCHNIA_P = QColor(17, 28, 46, 235)    # szkło nieprzezroczyste (panele)
OBRYS         = QColor(255, 255, 255, 26)
OBRYS_MOCNY   = QColor(255, 255, 255, 46)
TEKST         = QColor("#F1F5F9")
TEKST_2       = QColor("#A7B4C8")
TEKST_3       = QColor("#7C8BA3")
CYJAN         = QColor("#00F0FF")
ZIELEN        = QColor("#00E4A1")
MIETA         = QColor("#9FF5D7")
BURSZTYN      = QColor("#F5B841")
BLAD          = QColor("#FF5C7A")
PAPIER        = QColor("#FFFFFF")
PAPIER_TEKST  = QColor("#101828")

def z_alfa(kolor, a):
    k = QColor(kolor)
    k.setAlpha(int(a))
    return k

# ── czcionki ─────────────────────────────────────────────────────────
_RODZINY = {}

def _pierwsza_dostepna(kandydaci, zapas):
    klucz = tuple(kandydaci)
    if klucz in _RODZINY:
        return _RODZINY[klucz]
    try:
        rodziny = set(QFontDatabase.families())
    except Exception:
        rodziny = set()
    wybrana = zapas
    for k in kandydaci:
        if k in rodziny:
            wybrana = k
            break
    _RODZINY[klucz] = wybrana
    return wybrana

def rodzina_naglowek():
    return _pierwsza_dostepna(["Space Grotesk", "Segoe UI Variable Display", "Segoe UI",
                               "Inter", "DejaVu Sans"], "Segoe UI")

def rodzina_tekst():
    return _pierwsza_dostepna(["IBM Plex Sans", "Segoe UI", "Inter", "DejaVu Sans"], "Segoe UI")

def rodzina_mono():
    return _pierwsza_dostepna(["IBM Plex Mono", "Cascadia Mono", "Consolas",
                               "DejaVu Sans Mono"], "Consolas")

def czcionka(rozmiar=13, waga=400, mono=False, naglowek=False, odstep=0.0):
    if mono:
        f = QFont(rodzina_mono())
    elif naglowek:
        f = QFont(rodzina_naglowek())
    else:
        f = QFont(rodzina_tekst())
    f.setPixelSize(int(rozmiar))
    f.setWeight(QFont.Weight(int(waga)))
    if odstep:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, float(odstep))
    return f

# ── pomocniki rysowania ──────────────────────────────────────────────
def tlo_sceny(p: QPainter, rect: QRectF, plamy=True):
    """Głęboki gradient tła z miękkimi plamami światła."""
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0.0, TLO_GORA)
    g.setColorAt(1.0, TLO_DOL)
    p.fillRect(rect, QBrush(g))
    if not plamy:
        return
    for (fx, fy, prom, kolor, sila) in (
        (0.62, 0.46, 0.55, CYJAN, 26),
        (0.88, 0.92, 0.42, ZIELEN, 18),
        (0.10, 0.02, 0.45, QColor("#3B82F6"), 12),
    ):
        srodek = QPointF(rect.x() + rect.width() * fx, rect.y() + rect.height() * fy)
        r = max(rect.width(), rect.height()) * prom
        rg = QRadialGradient(srodek, r)
        rg.setColorAt(0.0, z_alfa(kolor, sila))
        rg.setColorAt(1.0, z_alfa(kolor, 0))
        p.fillRect(rect, QBrush(rg))

def szklo(p: QPainter, rect: QRectF, promien=18.0, mocne=False, obrys=True, rozblysk=True):
    """Karta ze szkła: półprzezroczyste tło, jasna krawędź u góry, obrys."""
    sciezka = QPainterPath()
    sciezka.addRoundedRect(rect, promien, promien)
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    baza = POWIERZCHNIA_P if mocne else POWIERZCHNIA
    g.setColorAt(0.0, z_alfa(baza.lighter(118), baza.alpha()))
    g.setColorAt(0.35, baza)
    g.setColorAt(1.0, z_alfa(baza.darker(112), baza.alpha()))
    p.fillPath(sciezka, QBrush(g))
    if rozblysk:
        gora = QRectF(rect.x() + promien * 0.5, rect.y(), rect.width() - promien, 1.0)
        p.fillRect(gora, z_alfa(QColor(255, 255, 255), 30))
    if obrys:
        p.setPen(QPen(OBRYS, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(sciezka)

def cien(p: QPainter, rect: QRectF, promien=18.0, sila=120, rozmycie=18, przesun=8):
    """Tani, warstwowy cień pod kartą — bez efektów graficznych Qt."""
    for i in range(rozmycie, 0, -2):
        a = int(sila * (i / float(rozmycie)) ** 2 / rozmycie * 2)
        if a <= 0:
            continue
        r = rect.adjusted(-i, -i + przesun, i, i + przesun)
        s = QPainterPath()
        s.addRoundedRect(r, promien + i, promien + i)
        p.fillPath(s, z_alfa(QColor(0, 0, 0), a))

def poswiata_linii(p: QPainter, sciezka: QPainterPath, kolor=CYJAN,
                   warstwy=((14, 34), (6, 90), (2.2, 255))):
    """Świecąca linia: kilka nakładających się grubości od najszerszej."""
    p.setBrush(Qt.BrushStyle.NoBrush)
    for szer, alfa in warstwy:
        pen = QPen(z_alfa(kolor, alfa), szer)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(sciezka)

def punkt_swiatla(p: QPainter, srodek: QPointF, promien=14.0, kolor=CYJAN, sila=150):
    rg = QRadialGradient(srodek, promien)
    rg.setColorAt(0.0, z_alfa(kolor, sila))
    rg.setColorAt(1.0, z_alfa(kolor, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(rg))
    p.drawEllipse(srodek, promien, promien)

_ZIARNO = {}

def ziarno(p: QPainter, rect: QRectF, sila=12):
    """Delikatny szum na wierzchu — łamie plastik płaskiego tła."""
    bok = 128
    klucz = (bok, sila)
    obraz = _ZIARNO.get(klucz)
    if obraz is None:
        import random
        rnd = random.Random(7)
        obraz = QImage(bok, bok, QImage.Format.Format_ARGB32_Premultiplied)
        obraz.fill(0)
        for y in range(bok):
            for x in range(bok):
                v = rnd.randint(0, 255)
                if v > 200:
                    a = int((v - 200) / 55.0 * sila)
                    obraz.setPixelColor(x, y, QColor(255, 255, 255, a))
        _ZIARNO[klucz] = obraz
    p.save()
    p.setClipRect(rect)
    p.drawTiledPixmap(rect, __import__("PyQt6.QtGui", fromlist=["QPixmap"]).QPixmap.fromImage(obraz))
    p.restore()

def winieta(p: QPainter, rect: QRectF, sila=90):
    rg = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.72)
    rg.setColorAt(0.55, QColor(0, 0, 0, 0))
    rg.setColorAt(1.0, QColor(0, 0, 0, sila))
    p.fillRect(rect, QBrush(rg))

def tekst(p: QPainter, x, y, napis, kolor=TEKST, rozmiar=13, waga=400,
          mono=False, naglowek=False, odstep=0.0, wyrownanie=None, szerokosc=None):
    p.setPen(QPen(kolor))
    p.setFont(czcionka(rozmiar, waga, mono, naglowek, odstep))
    if wyrownanie is None or szerokosc is None:
        p.drawText(QPointF(x, y), napis)
    else:
        p.drawText(QRectF(x, y - rozmiar, szerokosc, rozmiar * 1.6), wyrownanie, napis)

# ── arkusz stylów dla zwykłych kontrolek ─────────────────────────────
def qss():
    return f"""
    QWidget {{ color: {TEKST.name()}; font-family: '{rodzina_tekst()}'; font-size: 13px; }}
    QLineEdit, QComboBox {{
        background: rgba(9, 16, 28, 200); border: 1px solid rgba(255,255,255,0.10);
        border-radius: 10px; padding: 9px 12px; color: {TEKST.name()}; selection-background-color: {CYJAN.name()};
    }}
    QLineEdit:focus, QComboBox:focus {{ border: 1px solid rgba(0,240,255,0.55); }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: #0E1726; border: 1px solid rgba(255,255,255,0.12);
        selection-background-color: rgba(0,240,255,0.18); outline: none;
    }}
    QPushButton {{
        background: rgba(17,28,46,0.86); border: 1px solid rgba(255,255,255,0.12);
        border-radius: 10px; padding: 9px 14px; color: {TEKST.name()};
    }}
    QPushButton:hover {{ border-color: rgba(0,240,255,0.45); }}
    QPushButton:pressed {{ background: rgba(0,240,255,0.14); }}
    QPushButton[rola="glowny"] {{
        background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {CYJAN.name()}, stop:1 {ZIELEN.name()});
        color: #04121A; border: none; font-weight: 600;
    }}
    QPushButton[rola="zielony"] {{
        background: rgba(0,228,161,0.16); border: 1px solid rgba(0,228,161,0.55); color: {MIETA.name()};
    }}
    QToolTip {{ background: #0E1726; color: {TEKST.name()}; border: 1px solid rgba(255,255,255,0.14); padding: 6px; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; }}
    QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.16); border-radius: 5px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    """
