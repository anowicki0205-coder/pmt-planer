# -*- coding: utf-8 -*-
"""Wspólny język wizualny prototypu nowego wyglądu PMT Planera (wariant A).

Tu mieszkają kolory, czcionki i pomocniki do rysowania. Reszta prototypu
nie definiuje własnych barw ani nie dobiera czcionek — wszystko idzie stąd,
żeby ekran trzymał się kupy.

To jest warstwa materiału: z tych kilkunastu funkcji zbudowane są wszystkie
elementy interfejsu. Każda powierzchnia ma krawędź światła, głębię i ziarno,
żaden obrys nie jest płaski, a liczby dochodzą do wartości płynnie.

Uruchomiony wprost (``python proto_styl.py``) plik rysuje arkusz próbek
wszystkich pomocników i zapisuje go do ``zrzut_styl.png``.
"""
import array
import math
import random
import time
import weakref

from PyQt6.QtCore import Qt, QRectF, QPointF, QObject, QTimer, pyqtSignal
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QLinearGradient, QRadialGradient,
                         QPainter, QPainterPath, QPen, QBrush, QImage, QPixmap)

# ── barwy ────────────────────────────────────────────────────────────
TLO_GORA      = QColor("#050A14")
TLO_DOL       = QColor("#0B1320")
SZYNA         = QColor("#0A101B")
POWIERZCHNIA  = QColor(17, 28, 46, 184)     # szkło kart
POWIERZCHNIA_P = QColor(17, 28, 46, 235)    # szkło nieprzezroczyste (panele)
POWIERZCHNIA_CIEMNA = QColor(9, 15, 26, 210)    # wgłębienia, rowki, tło pól
POWIERZCHNIA_JASNA  = QColor(31, 47, 72, 168)   # wypukłości, kafel uniesiony
POWIERZCHNIA_C = POWIERZCHNIA_CIEMNA        # krótkie nazwy do rysowania
POWIERZCHNIA_J = POWIERZCHNIA_JASNA
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

# ── mapa 3D: krajobraz w kolorze ─────────────────────────────────────
# Wszystkie barwy krajobrazu mieszkają TU, a proto_mapa tylko je składa
# ze światłem dnia. Jedna zasada doboru: trasa dnia (cyjan i zieleń) ma
# zostać jedyną rzeczą na mapie z wyraźną przewagą zieleni I błękitu nad
# czerwienią przy dużej jasności — stąd niebo i woda są przygaszone ku
# szarości, a nie lazurowe. Pola i łąki: zieleń z żółcią (b < r), więc
# nigdy nie udają trasy.
#
# Pola: sześć odcieni na porę roku — sąsiednie działki mają się różnić.
POLA_WIOSNA = (QColor(118, 164, 70), QColor(134, 176, 82), QColor(104, 152, 62),
               QColor(146, 172, 92), QColor(128, 158, 74), QColor(156, 182, 98))
POLA_LATO   = (QColor(200, 176, 92), QColor(214, 190, 104), QColor(182, 166, 84),
               QColor(160, 168, 84), QColor(222, 200, 120), QColor(190, 154, 80))
POLA_JESIEN = (QColor(176, 128, 72), QColor(190, 142, 86), QColor(156, 116, 68),
               QColor(166, 152, 96), QColor(200, 152, 90), QColor(146, 124, 82))
POLA_ZIMA   = (QColor(204, 208, 208), QColor(196, 202, 204), QColor(212, 214, 214),
               QColor(186, 194, 192), QColor(200, 206, 206), QColor(192, 198, 196))
LAKA_WIOSNA, LAKA_LATO = QColor(140, 190, 90), QColor(150, 186, 88)
LAKA_JESIEN, LAKA_ZIMA = QColor(162, 164, 92), QColor(208, 212, 208)
# Las: (cień pod koronami, korony w świetle). Jesienią rdza, zimą szarość.
LAS_WIOSNA = (QColor(50, 100, 56), QColor(82, 136, 72))
LAS_LATO   = (QColor(40, 90, 50), QColor(66, 120, 62))
LAS_JESIEN = (QColor(72, 84, 44), QColor(134, 104, 50))
LAS_ZIMA   = (QColor(56, 70, 70), QColor(84, 96, 92))
GLEBA      = QColor(112, 98, 78)         # ziemia pod polami (miedze, obrzeża)
GLEBA_ZIMA = QColor(150, 152, 150)
# Woda: koryto, głębia i jasny blask słońca na tafli.
WODA        = QColor(70, 98, 138)
WODA_GLEBOKA = QColor(48, 72, 112)
WODA_BLASK  = QColor(196, 212, 226)
WODA_BRZEG  = QColor(154, 150, 124)
# Drogi: lokalna wąska i jasna, szybka szeroka i ciemna z jasnym pasem.
DROGA_LOKALNA = QColor(172, 170, 162)
DROGA_SZYBKA  = QColor(96, 98, 102)
DROGA_PAS     = QColor(228, 224, 206)
DROGA_OBRZEZE = QColor(118, 116, 108)
MOST          = QColor(214, 208, 196)
# Zabudowa: plama zabudowy, dachy (dachówka i szary), ściany, wieża, komin.
PLAMA_OSADY   = QColor(178, 168, 152)
DACH_DACHOWKA = QColor(172, 96, 70)
DACH_SZARY    = QColor(146, 146, 144)
DACH_BAZY     = QColor(158, 152, 150)
SCIANA_OSADY  = QColor(214, 204, 186)
WIEZA         = QColor(196, 188, 176)
KOMIN         = QColor(124, 112, 106)
OKNO_WIECZOR  = QColor(255, 206, 120)
# Niebo i światło w trzech porach dnia: (góra nieba, horyzont, słońce, ambient).
NIEBO_RANO     = (QColor(54, 74, 108), QColor(200, 204, 208),
                  QColor(236, 240, 255), QColor(150, 168, 196))
NIEBO_POLUDNIE = (QColor(44, 74, 124), QColor(176, 192, 206),
                  QColor(255, 250, 238), QColor(158, 172, 196))
NIEBO_WIECZOR  = (QColor(50, 40, 76), QColor(226, 166, 116),
                  QColor(255, 196, 132), QColor(150, 134, 172))
WZGORZA_DALEKIE = QColor(108, 128, 158)  # pasma na horyzoncie, dalsze i bliższe
WZGORZA_BLISKIE = QColor(90, 108, 138)
CHMURA          = QColor(224, 228, 232)
CHMURA_CIEN     = QColor(168, 178, 194)
CIEN_CHMURY     = QColor(12, 14, 34)      # cień chmury na ziemi (z małą alfą)
POZIOMICA       = QColor(70, 58, 40)
# Góry: ponad granicą lasu skała, na szczytach śnieg (zimą śnieg schodzi niżej).
SKALA           = QColor(146, 134, 120)
SNIEG           = QColor(238, 241, 244)
# Iskra słońca na wodzie — jaśniejsza od blasku, w wąskim pasie.
WODA_ISKRA      = QColor(244, 249, 253)
DACH_CIEMNY     = QColor(110, 94, 86)     # trzeci odcień dachu: łupek

# ── miary ────────────────────────────────────────────────────────────
PROMIEN       = 18.0     # domyślne zaokrąglenie narożnika
PROMIEN_MALY  = 10.0
PROMIEN_DUZY  = 26.0


def z_alfa(kolor, a):
    k = QColor(kolor)
    k.setAlpha(max(0, min(255, int(a))))
    return k


def _ile(a):
    return max(0, min(255, int(a)))


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


def _sciezka(ksztalt, promien=PROMIEN):
    """Przyjmuje gotową ścieżkę albo prostokąt i zwraca ścieżkę."""
    if isinstance(ksztalt, QPainterPath):
        return ksztalt
    s = QPainterPath()
    s.addRoundedRect(QRectF(ksztalt), promien, promien)
    return s


def szklo(p: QPainter, rect: QRectF, promien=18.0, mocne=False, obrys=True, rozblysk=True,
          sila_krawedzi=1.0, refleks=True, baza=None):
    """Karta ze szkła: półprzezroczyste tło, krawędź światła, refleks, obrys.

    ``sila_krawedzi`` prowadzi cienki gradient tuż pod górną i lewą krawędzią
    wewnątrz kształtu (0.0 wyłącza), ``refleks`` dokłada delikatną smugę po
    przekątnej. ``baza`` pozwala podstawić inną barwę powierzchni.
    """
    sciezka = QPainterPath()
    sciezka.addRoundedRect(rect, promien, promien)
    zrodlo = QColor(baza) if baza is not None else (POWIERZCHNIA_P if mocne else POWIERZCHNIA)
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0.0, z_alfa(zrodlo.lighter(118), zrodlo.alpha()))
    g.setColorAt(0.35, zrodlo)
    g.setColorAt(1.0, z_alfa(zrodlo.darker(112), zrodlo.alpha()))
    p.fillPath(sciezka, QBrush(g))

    if (refleks or sila_krawedzi > 0) and rect.width() > 6 and rect.height() > 6:
        # Rysujemy po ścieżce wsuniętej o pół piksela i kreską grubości 1 —
        # światło zostaje w środku kształtu bez zakładania maski, która
        # przy kilkudziesięciu kaflach kosztuje więcej niż całe rysowanie.
        wew = QPainterPath()
        pw = max(0.0, promien - 0.5)
        wew.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), pw, pw)
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Szczegół idzie za wielkością: drobny kafel dostaje samo górne
        # światło, bo smugi po przekątnej i tak na nim nie widać, a przy
        # trzydziestu kaflach naraz liczy się każda kreska.
        drobny = rect.width() < 64.0 or rect.height() < 64.0
        if refleks and not drobny:
            a = _ile(13 * min(1.6, max(0.0, sila_krawedzi)))
            sm = QLinearGradient(rect.topLeft(), rect.bottomRight())
            sm.setColorAt(0.00, z_alfa(PAPIER, 0))
            sm.setColorAt(0.29, z_alfa(PAPIER, 0))
            sm.setColorAt(0.38, z_alfa(PAPIER, a))
            sm.setColorAt(0.47, z_alfa(PAPIER, 0))
            sm.setColorAt(1.00, z_alfa(PAPIER, 0))
            p.fillPath(wew, QBrush(sm))
        if sila_krawedzi > 0:
            s = float(sila_krawedzi)
            # górna krawędź: światło zbiera się tuż pod obrysem i gaśnie w dół,
            # na samym dole wraca cienkie odbicie
            h = max(4.0, min(rect.height() * 0.45, promien * 2.2 + 9.0))
            t = h / rect.height()
            pion = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            pion.setColorAt(0.00, z_alfa(PAPIER, 84 * s))
            pion.setColorAt(t * 0.45, z_alfa(PAPIER, 30 * s))
            pion.setColorAt(min(0.94, t), z_alfa(PAPIER, 0))
            pion.setColorAt(0.985, z_alfa(PAPIER, 0))
            pion.setColorAt(1.00, z_alfa(PAPIER, 22 * s))
            pen = QPen(QBrush(pion), 1.0)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawPath(wew)
            if not drobny:
                # lewa krawędź: to samo światło, tylko w poprzek
                w = max(4.0, min(rect.width() * 0.45, promien * 2.2 + 9.0))
                u = w / rect.width()
                poziom = QLinearGradient(rect.topLeft(), rect.topRight())
                poziom.setColorAt(0.00, z_alfa(PAPIER, 50 * s))
                poziom.setColorAt(min(0.86, u), z_alfa(PAPIER, 0))
                poziom.setColorAt(0.93, z_alfa(QColor(0, 0, 0), 0))
                poziom.setColorAt(1.00, z_alfa(QColor(0, 0, 0), 30 * s))  # prawa krawędź się cofa
                pen2 = QPen(QBrush(poziom), 1.0)
                pen2.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen2)
                p.drawPath(wew)
        p.restore()

    if rozblysk:
        gora = QRectF(rect.x() + promien * 0.5, rect.y(), rect.width() - promien, 1.0)
        p.fillRect(gora, z_alfa(QColor(255, 255, 255), 30))
    if obrys:
        p.setPen(QPen(OBRYS, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(sciezka)


def obrys_gradientowy(p: QPainter, sciezka, kolor_a=CYJAN, kolor_b=ZIELEN, szerokosc=1.4,
                      kat_stopnie=None, promien=PROMIEN):
    """Obramowanie przechodzące z barwy ``kolor_a`` w ``kolor_b``.

    ``sciezka`` to gotowa QPainterPath albo prostokąt (wtedy zaokrąglany
    o ``promien``). Bez ``kat_stopnie`` gradient biegnie po przekątnej,
    z góry z lewej na dół w prawo.
    """
    s = _sciezka(sciezka, promien)
    r = s.boundingRect()
    if r.isEmpty():
        return
    if kat_stopnie is None:
        g = QLinearGradient(r.topLeft(), r.bottomRight())
    else:
        a = math.radians(float(kat_stopnie))
        dx, dy = math.cos(a), -math.sin(a)
        dl = max(r.width(), r.height()) * 0.72
        sr = r.center()
        g = QLinearGradient(QPointF(sr.x() - dx * dl, sr.y() - dy * dl),
                            QPointF(sr.x() + dx * dl, sr.y() + dy * dl))
    ka, kb = QColor(kolor_a), QColor(kolor_b)
    srodkowy = QColor((ka.red() + kb.red()) // 2, (ka.green() + kb.green()) // 2,
                      (ka.blue() + kb.blue()) // 2, (ka.alpha() + kb.alpha()) // 2)
    g.setColorAt(0.0, ka)
    g.setColorAt(0.5, srodkowy)
    g.setColorAt(1.0, kb)
    pen = QPen(QBrush(g), float(szerokosc))
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(s)


def halo(p: QPainter, rect: QRectF, kolor=CYJAN, sila=90, promien=26.0,
         zaokraglenie=None, przesun=0.0):
    """Miękka poświata POD elementem — rysowana przed samym elementem.

    ``promien`` to zasięg rozmycia w pikselach, ``sila`` szczyt jasności.
    """
    promien = float(promien)
    if promien <= 0 or sila <= 0:
        return
    zaokr = PROMIEN if zaokraglenie is None else float(zaokraglenie)
    kroki = max(5, min(26, int(promien / 1.6)))
    for i in range(kroki, 0, -1):
        frac = i / float(kroki)                    # 1.0 skraj → 0.0 środek
        rozs = promien * frac
        a = _ile(sila * (1.0 - frac) ** 1.5 / kroki * 3.2)
        if a <= 0:
            continue
        r = rect.adjusted(-rozs, -rozs + przesun, rozs, rozs + przesun)
        s = QPainterPath()
        s.addRoundedRect(r, zaokr + rozs, zaokr + rozs)
        p.fillPath(s, z_alfa(kolor, a))


def swiatlo_kierunkowe(p: QPainter, rect: QRectF, kat_stopnie=135.0, sila=20,
                       sciezka=None, kolor=None, promien=PROMIEN):
    """Subtelny gradient udający światło padające z jednej strony.

    Kąt liczony jak w matematyce: 90 to światło z góry, 135 z góry z lewej,
    0 z prawej. Strona oświetlona rozjaśnia się, przeciwna przygasa.
    """
    if rect.isEmpty() or sila <= 0:
        return
    a = math.radians(float(kat_stopnie))
    dx, dy = math.cos(a), -math.sin(a)
    sr = rect.center()
    dl = (abs(dx) * rect.width() + abs(dy) * rect.height()) * 0.5
    if dl <= 0:
        return
    jasny = QColor(kolor) if kolor is not None else QColor(255, 255, 255)
    g = QLinearGradient(QPointF(sr.x() + dx * dl, sr.y() + dy * dl),
                        QPointF(sr.x() - dx * dl, sr.y() - dy * dl))
    g.setColorAt(0.00, z_alfa(jasny, sila))
    g.setColorAt(0.38, z_alfa(jasny, sila * 0.28))
    g.setColorAt(0.52, z_alfa(jasny, 0))
    g.setColorAt(1.00, z_alfa(QColor(0, 0, 0), sila * 0.85))
    p.save()
    if sciezka is not None:
        p.setClipPath(_sciezka(sciezka, promien), Qt.ClipOperation.IntersectClip)
    else:
        p.setClipRect(rect, Qt.ClipOperation.IntersectClip)
    p.fillRect(rect, QBrush(g))
    p.restore()


def _obwod(rect: QRectF, promien):
    """Opis obwodu zaokrąglonego prostokąta: odcinki i łuki wraz z długościami.

    Zwraca (dlugosc_calkowita, lista_odcinkow). Liczymy sami, bo chodzenie po
    QPainterPath metodą pointAtPercent jest kilkanaście razy wolniejsze.
    """
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    r = max(0.0, min(float(promien), w * 0.5, h * 0.5))
    lp, lb = max(0.0, w - 2 * r), max(0.0, h - 2 * r)
    luk = math.pi * r * 0.5
    odcinki = (
        ("p", lp, (x + r, y), (1.0, 0.0), (0.0, 1.0)),                   # góra
        ("l", luk, (x + w - r, y + r), (0.0, 0.0), r),                   # narożnik PG
        ("p", lb, (x + w, y + r), (0.0, 1.0), (-1.0, 0.0)),              # prawo
        ("l", luk, (x + w - r, y + h - r), (1.0, 0.0), r),               # narożnik PD
        ("p", lp, (x + w - r, y + h), (-1.0, 0.0), (0.0, -1.0)),         # dół
        ("l", luk, (x + r, y + h - r), (2.0, 0.0), r),                   # narożnik LD
        ("p", lb, (x, y + h - r), (0.0, -1.0), (1.0, 0.0)),              # lewo
        ("l", luk, (x + r, y + r), (3.0, 0.0), r),                       # narożnik LG
    )
    return sum(o[1] for o in odcinki), odcinki


def _punkt_obwodu(odcinki, s):
    """Punkt na obwodzie w odległości ``s`` od startu + normalna do środka."""
    for rodzaj, dl, baza, kier, extra in odcinki:
        if s > dl and dl > 0:
            s -= dl
            continue
        if dl <= 0:
            continue
        if rodzaj == "p":
            return (baza[0] + kier[0] * s, baza[1] + kier[1] * s, extra[0], extra[1])
        r = extra
        if r <= 0:
            return (baza[0], baza[1], 0.0, 0.0)
        t = (s / dl) * (math.pi * 0.5) + kier[0] * (math.pi * 0.5) - math.pi * 0.5
        nx, ny = math.cos(t), math.sin(t)
        return (baza[0] + nx * r, baza[1] + ny * r, -nx, -ny)
    return None


_SZRON = {}

def szron(p: QPainter, rect: QRectF, promien=PROMIEN, sila=30, gestosc=1.0, nasienie=11):
    """Bardzo delikatny, nieregularny szum na krawędzi szkła."""
    if rect.width() < 4 or rect.height() < 4 or sila <= 0:
        return
    dlugosc, odcinki = _obwod(rect, promien)
    if dlugosc <= 0:
        return
    ile = max(12, min(1200, int(dlugosc * 0.42 * float(gestosc))))
    klucz = (ile, int(nasienie))
    wzor = _SZRON.get(klucz)
    if wzor is None:
        rnd = random.Random(nasienie)
        wzor = []
        for i in range(ile):
            wzor.append((
                min(0.9995, max(0.0, (i + rnd.random() * 1.8 - 0.4) / float(ile))),
                rnd.uniform(-0.5, 2.4),                     # odchylenie: głównie do wnętrza
                rnd.random() ** 2.0,                        # jasność
                rnd.uniform(0.6, 1.5),                      # wielkość
            ))
        _SZRON[klucz] = wzor
    biel = QColor(PAPIER)
    for (pct, odch, jas, wlk) in wzor:
        a = _ile(sila * jas)
        if a <= 0:
            continue
        pkt = _punkt_obwodu(odcinki, pct * dlugosc)
        if pkt is None:
            continue
        x = pkt[0] + pkt[2] * odch
        y = pkt[1] + pkt[3] * odch
        biel.setAlpha(a)
        p.fillRect(QRectF(x - wlk * 0.5, y - wlk * 0.5, wlk, wlk), biel)


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


# ── ziarno ───────────────────────────────────────────────────────────
_ZIARNO = {}        # obrazy kafla (trzymamy też bufor, bo QImage go nie kopiuje)
_ZIARNO_PIX = {}    # gotowe pixmapy do kładzenia kafelkami

def _kafel_ziarna(bok, sila, ciemne):
    klucz = (bok, int(sila), round(float(ciemne), 2))
    gotowe = _ZIARNO.get(klucz)
    if gotowe is not None:
        return gotowe[0]
    typ = "I" if array.array("I").itemsize == 4 else "L"
    bufor = array.array(typ, bytes(bok * bok * 4))
    rnd = random.Random(7)
    losy = rnd.randbytes(bok * bok)
    for i, v in enumerate(losy):
        if v > 200:
            a = int((v - 200) / 55.0 * sila)
            if a:
                bufor[i] = (a << 24) | (a << 16) | (a << 8) | a      # biel, premnożona
        elif v < 40 and ciemne > 0:
            a = int((40 - v) / 40.0 * sila * ciemne)
            if a:
                bufor[i] = a << 24                                   # czerń, premnożona
    dane = bufor.tobytes()
    obraz = QImage(dane, bok, bok, bok * 4, QImage.Format.Format_ARGB32_Premultiplied)
    _ZIARNO[klucz] = (obraz, dane)
    return obraz


def ziarno(p: QPainter, rect: QRectF, sila=12, skala=1.0, ciemne=0.45):
    """Delikatny szum na wierzchu — łamie plastik płaskiego tła.

    ``skala`` powiększa kropkę ziarna (1.0 to jeden piksel), ``ciemne``
    dokłada ciemne drobiny obok jasnych. Kafel liczony jest raz i trzymany
    w pamięci jako pixmapa, więc rysowanie to jedno położenie kafelków.
    """
    if sila <= 0 or rect.isEmpty():
        return
    bok = 128
    skala = max(0.25, float(skala))
    klucz = (bok, int(sila), round(float(ciemne), 2), round(skala, 2))
    pix = _ZIARNO_PIX.get(klucz)
    if pix is None:
        obraz = _kafel_ziarna(bok, sila, ciemne)
        if abs(skala - 1.0) > 0.01:
            n = max(8, int(round(bok * skala)))
            tryb = (Qt.TransformationMode.SmoothTransformation if skala > 1.0
                    else Qt.TransformationMode.FastTransformation)
            obraz = obraz.scaled(n, n, Qt.AspectRatioMode.IgnoreAspectRatio, tryb)
        pix = QPixmap.fromImage(obraz)
        _ZIARNO_PIX[klucz] = pix
    p.save()
    p.setClipRect(rect, Qt.ClipOperation.IntersectClip)
    p.drawTiledPixmap(rect, pix)
    p.restore()


def winieta(p: QPainter, rect: QRectF, sila=90):
    rg = QRadialGradient(rect.center(), max(rect.width(), rect.height()) * 0.72)
    rg.setColorAt(0.55, QColor(0, 0, 0, 0))
    rg.setColorAt(1.0, QColor(0, 0, 0, sila))
    p.fillRect(rect, QBrush(rg))


def tekst(p: QPainter, x, y, napis, kolor=TEKST, rozmiar=13, waga=400,
          mono=False, naglowek=False, odstep=0.0, wyrownanie=None, szerokosc=None,
          poswiata=0.0):
    """Napis jedną z trzech rodzin. ``poswiata`` kładzie pod nim miękką aureolę."""
    f = czcionka(rozmiar, waga, mono, naglowek, odstep)
    p.setFont(f)

    def rysuj(dx, dy, kol):
        p.setPen(QPen(kol))
        if wyrownanie is None or szerokosc is None:
            p.drawText(QPointF(x + dx, y + dy), napis)
        else:
            p.drawText(QRectF(x + dx, y - rozmiar + dy, szerokosc, rozmiar * 1.6),
                       wyrownanie, napis)

    if poswiata > 0:
        r = 1.0 + float(poswiata)
        a = _ile(34 * min(2.0, float(poswiata)))
        kol = z_alfa(kolor, a)
        for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r),
                       (-r * 0.7, -r * 0.7), (r * 0.7, -r * 0.7),
                       (-r * 0.7, r * 0.7), (r * 0.7, r * 0.7)):
            rysuj(dx, dy, kol)
    rysuj(0.0, 0.0, kolor)


# ── płynne dochodzenie liczb ─────────────────────────────────────────
def _k_liniowa(t):
    return t

def _k_lagodna(t):
    return t * t * (3.0 - 2.0 * t)

def _k_wyjscie(t):
    return 1.0 - (1.0 - t) ** 3

def _k_wejscie(t):
    return t * t * t

def _k_sprezyna(t):
    c = 1.70158
    u = t - 1.0
    return 1.0 + (c + 1.0) * u * u * u + c * u * u

KRZYWE = {
    "liniowa": _k_liniowa,
    "lagodna": _k_lagodna,
    "wyjscie": _k_wyjscie,
    "wejscie": _k_wejscie,
    "sprezyna": _k_sprezyna,
}


class Plynnie(QObject):
    """Prosty tweening jednej liczby na zegarze Qt.

    ``do(wartosc)`` każe wartości dojść do celu, ``teraz()`` zwraca bieżącą,
    ``gotowe()`` mówi, czy ruch się skończył. Każdy ruch emituje ``zmiana``
    — wystarczy podpiąć ``update`` widżetu. Zegar zatrzymuje się sam po
    dojściu do celu i da się zatrzymać ręcznie metodą ``zatrzymaj()``;
    ``Plynnie.zatrzymaj_wszystkie()`` gasi wszystkie naraz przy zamykaniu okna.
    """

    zmiana = pyqtSignal()
    koniec = pyqtSignal()

    _WSZYSTKIE = weakref.WeakSet()

    def __init__(self, wartosc=0.0, czas=280, krzywa="lagodna", rodzic=None,
                 przy_zmianie=None, klatka=16):
        super().__init__(rodzic)
        self._od = float(wartosc)
        self._cel = float(wartosc)
        self._teraz = float(wartosc)
        self._czas = max(1, int(czas))
        self._krzywa = self._wybierz(krzywa)
        self._start = 0.0
        self._trwa = 0
        self._zegar = QTimer(self)
        self._zegar.setInterval(max(8, int(klatka)))
        self._zegar.timeout.connect(self._krok)
        if przy_zmianie is not None:
            self.zmiana.connect(przy_zmianie)
        Plynnie._WSZYSTKIE.add(self)

    # — ustawienia —
    @staticmethod
    def _wybierz(krzywa):
        if callable(krzywa):
            return krzywa
        return KRZYWE.get(str(krzywa), _k_lagodna)

    def ustaw_czas(self, czas):
        self._czas = max(1, int(czas))

    def ustaw_krzywa(self, krzywa):
        self._krzywa = self._wybierz(krzywa)

    # — sterowanie —
    def do(self, wartosc, czas=None, krzywa=None):
        """Rusz wartość do celu. Ten sam cel przy stojącym zegarze nic nie robi."""
        cel = float(wartosc)
        if czas is not None:
            self._czas = max(1, int(czas))
        if krzywa is not None:
            self._krzywa = self._wybierz(krzywa)
        if abs(cel - self._cel) < 1e-9 and self._trwa:
            return
        if abs(cel - self._teraz) < 1e-9:
            self._cel = cel
            self.dokoncz()
            return
        self._od = self._teraz
        self._cel = cel
        self._start = time.monotonic()
        self._trwa = 1
        if not self._zegar.isActive():
            self._zegar.start()

    def ustaw(self, wartosc):
        """Skok bez ruchu — do pierwszego ustawienia albo po przeładowaniu danych."""
        self._zegar.stop()
        self._trwa = 0
        self._od = self._cel = self._teraz = float(wartosc)
        self.zmiana.emit()

    def dokoncz(self):
        """Natychmiast na cel i stop."""
        self._zegar.stop()
        byl = self._trwa
        self._trwa = 0
        self._teraz = self._od = self._cel
        self.zmiana.emit()
        if byl:
            self.koniec.emit()

    def zatrzymaj(self):
        """Zatrzymuje zegar tam, gdzie wartość aktualnie stoi."""
        self._zegar.stop()
        self._trwa = 0

    # — odczyt —
    def teraz(self):
        return self._teraz

    def cel(self):
        return self._cel

    def gotowe(self):
        return not self._trwa

    def _krok(self):
        t = (time.monotonic() - self._start) * 1000.0 / self._czas
        if t >= 1.0:
            self.dokoncz()
            return
        self._teraz = self._od + (self._cel - self._od) * self._krzywa(t)
        self.zmiana.emit()

    @classmethod
    def zatrzymaj_wszystkie(cls):
        for pl in list(cls._WSZYSTKIE):
            try:
                pl.zatrzymaj()
            except RuntimeError:
                pass


# ── arkusz stylów dla zwykłych kontrolek ─────────────────────────────
def qss():
    return f"""
    /* Bez font-size i bez font-family na QWidget: taka regula nadpisuje
       setFont() w widzetach rysowanych recznie i zjada ich rozmiary. */
    QWidget {{ color: {TEKST.name()}; }}
    QLineEdit, QComboBox, QPushButton, QRadioButton, QLabel {{ font-family: '{rodzina_tekst()}'; font-size: 13px; }}
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


# ── arkusz próbek ────────────────────────────────────────────────────
def _szer(napis, rozmiar, waga=400, mono=False, naglowek=False, odstep=0.0):
    from PyQt6.QtGui import QFontMetricsF
    return QFontMetricsF(czcionka(rozmiar, waga, mono, naglowek, odstep)).horizontalAdvance(napis)


def _kafel(p, r, tytul):
    """Ramka jednej próbki; zwraca prostokąt na zawartość."""
    cien(p, r, PROMIEN, sila=70, rozmycie=12, przesun=6)
    szklo(p, r, PROMIEN, sila_krawedzi=1.0)
    tekst(p, r.x() + 16, r.y() + 26, tytul, TEKST_2, 11, 700, odstep=1.4)
    p.setPen(QPen(z_alfa(PAPIER, 16), 1.0))
    p.drawLine(QPointF(r.x() + 16, r.y() + 38), QPointF(r.right() - 16, r.y() + 38))
    return QRectF(r.x() + 16, r.y() + 50, r.width() - 32, r.height() - 66)


def _podpis(p, x, y, napis, kolor=None):
    tekst(p, x, y, napis, kolor or TEKST_3, 10, 500, mono=True)


def _probka_tlo(p, r):
    p.save()
    s = QPainterPath()
    s.addRoundedRect(r, 12, 12)
    p.setClipPath(s, Qt.ClipOperation.IntersectClip)
    tlo_sceny(p, r)
    winieta(p, r, 96)
    ziarno(p, r, 10)
    p.restore()
    p.setPen(QPen(OBRYS, 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(s)
    _podpis(p, r.x() + 4, r.bottom() + 12, "tlo_sceny + winieta + ziarno")


def _probka_szklo(p, r):
    w = (r.width() - 14) / 2.0
    a = QRectF(r.x(), r.y(), w, r.height() - 18)
    b = QRectF(r.x() + w + 14, r.y(), w, r.height() - 18)
    szklo(p, a, 14, sila_krawedzi=0.0, refleks=False)
    szklo(p, b, 14, sila_krawedzi=2.2, refleks=True)
    _podpis(p, a.x() + 4, r.bottom() + 12, "sila_krawedzi 0")
    _podpis(p, b.x() + 4, r.bottom() + 12, "2.2 + refleks", MIETA)


def _probka_obrys(p, r):
    w = (r.width() - 14) / 2.0
    a = QRectF(r.x(), r.y(), w, r.height() - 18)
    b = QRectF(r.x() + w + 14, r.y(), w, r.height() - 18)
    szklo(p, a, 14, obrys=False)
    p.setPen(QPen(OBRYS_MOCNY, 1.4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = QPainterPath()
    s.addRoundedRect(a, 14, 14)
    p.drawPath(s)
    szklo(p, b, 14, obrys=False)
    obrys_gradientowy(p, b, CYJAN, ZIELEN, 1.8, promien=14)
    _podpis(p, a.x() + 4, r.bottom() + 12, "obrys plaski")
    _podpis(p, b.x() + 4, r.bottom() + 12, "obrys_gradientowy", MIETA)


def _probka_halo(p, r):
    w = (r.width() - 20) / 3.0
    h = r.height() - 22
    for i, (kol, sila, prom) in enumerate(((CYJAN, 110, 26), (ZIELEN, 90, 20), (BURSZTYN, 120, 32))):
        k = QRectF(r.x() + i * (w + 10), r.y() + 10, w, h - 10)
        halo(p, k, kol, sila, prom, zaokraglenie=12)
        szklo(p, k, 12, mocne=True, sila_krawedzi=1.2)
        obrys_gradientowy(p, k, z_alfa(kol, 190), z_alfa(kol, 60), 1.2, promien=12)
    _podpis(p, r.x() + 4, r.bottom() + 12, "halo   sila 110 / 90 / 120")


def _probka_swiatlo(p, r):
    w = (r.width() - 20) / 3.0
    h = r.height() - 22
    for i, kat in enumerate((135, 90, 45)):
        k = QRectF(r.x() + i * (w + 10), r.y(), w, h)
        s = QPainterPath()
        s.addRoundedRect(k, 12, 12)
        p.fillPath(s, QColor(30, 46, 70, 255))
        swiatlo_kierunkowe(p, k, kat, 46, sciezka=s)
        p.setPen(QPen(OBRYS, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)
        n = f"{kat}"
        _podpis(p, k.center().x() - _szer(n, 10, 500, True) / 2.0, k.bottom() + 15, n)
    _podpis(p, r.x() + 4, r.bottom() + 12, "swiatlo_kierunkowe   kat")


def _probka_szron(p, r):
    w = (r.width() - 14) / 2.0
    a = QRectF(r.x(), r.y(), w, r.height() - 18)
    b = QRectF(r.x() + w + 14, r.y(), w, r.height() - 18)
    szklo(p, a, 14)
    szklo(p, b, 14)
    szron(p, b, 14, sila=64, gestosc=1.7)
    _podpis(p, a.x() + 4, r.bottom() + 12, "bez")
    _podpis(p, b.x() + 4, r.bottom() + 12, "szron", MIETA)


def _probka_ziarno(p, r):
    w = (r.width() - 20) / 3.0
    h = r.height() - 22
    for i, sk in enumerate((1.0, 2.0, 3.5)):
        k = QRectF(r.x() + i * (w + 10), r.y(), w, h)
        s = QPainterPath()
        s.addRoundedRect(k, 12, 12)
        p.fillPath(s, QColor(24, 38, 60, 255))
        p.save()
        p.setClipPath(s, Qt.ClipOperation.IntersectClip)
        ziarno(p, k, 34, skala=sk)
        p.restore()
        p.setPen(QPen(OBRYS, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)
        n = f"{sk:g}"
        _podpis(p, k.center().x() - _szer(n, 10, 500, True) / 2.0, k.bottom() + 15, n)
    _podpis(p, r.x() + 4, r.bottom() + 12, "ziarno   skala")


def _probka_cien(p, r):
    w = (r.width() - 24) / 2.0
    h = r.height() - 30
    a = QRectF(r.x() + 8, r.y() + 6, w - 8, h - 12)
    b = QRectF(r.x() + w + 24, r.y() + 6, w - 16, h - 12)
    cien(p, a, 14, sila=90, rozmycie=12, przesun=5)
    szklo(p, a, 14)
    cien(p, b, 14, sila=190, rozmycie=26, przesun=10)
    szklo(p, b, 14, mocne=True)
    _podpis(p, a.x(), r.bottom() + 12, "cien 90/12")
    _podpis(p, b.x(), r.bottom() + 12, "cien 190/26")


def _probka_linie(p, r):
    s = QPainterPath()
    s.moveTo(r.x() + 6, r.bottom() - 34)
    s.cubicTo(r.x() + r.width() * 0.32, r.y() + 4,
              r.x() + r.width() * 0.58, r.bottom() - 18,
              r.right() - 6, r.y() + 16)
    poswiata_linii(p, s, CYJAN)
    for pct in (0.0, 0.45, 1.0):
        punkt_swiatla(p, s.pointAtPercent(pct), 16, ZIELEN, 130)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(PAPIER))
    for pct in (0.0, 0.45, 1.0):
        p.drawEllipse(s.pointAtPercent(pct), 2.6, 2.6)
    _podpis(p, r.x() + 4, r.bottom() + 12, "poswiata_linii + punkt_swiatla")


def _probka_paleta(p, r):
    pary = (("POWIERZCHNIA", POWIERZCHNIA), ("POWIERZCHNIA_P", POWIERZCHNIA_P),
            ("POWIERZCHNIA_C", POWIERZCHNIA_CIEMNA), ("POWIERZCHNIA_J", POWIERZCHNIA_JASNA),
            ("CYJAN", CYJAN), ("ZIELEN", ZIELEN), ("MIETA", MIETA), ("BURSZTYN", BURSZTYN),
            ("BLAD", BLAD), ("TEKST", TEKST), ("TEKST_2", TEKST_2), ("TEKST_3", TEKST_3))
    h = (r.height() - 16) / 6.0
    w = (r.width() - 10) / 2.0
    for i, (n, kol) in enumerate(pary):
        kol_i, wier = divmod(i, 6)
        x = r.x() + kol_i * (w + 10)
        y = r.y() + wier * h
        pr = QRectF(x, y + 1, 26, h - 5)
        s = QPainterPath()
        s.addRoundedRect(pr, 5, 5)
        p.fillPath(s, QColor(126, 138, 156))               # podkład pod przezroczystość
        p.save()
        p.setClipPath(s, Qt.ClipOperation.IntersectClip)
        p.fillRect(QRectF(pr.x(), pr.y(), pr.width() * 0.5, pr.height()), QColor(14, 22, 36))
        p.restore()
        p.fillPath(s, QColor(kol))
        p.setPen(QPen(z_alfa(PAPIER, 22), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(s)
        tekst(p, x + 33, y + h * 0.5 + 3, n, TEKST_2, 10, 500, mono=True)
    _podpis(p, r.x() + 4, r.bottom() + 12, f"paleta   PROMIEN {PROMIEN:g}")


def _probka_plynnie(p, r):
    pole = QRectF(r.x(), r.y(), r.width(), r.height() - 30)
    s = QPainterPath()
    s.addRoundedRect(pole, 10, 10)
    p.fillPath(s, POWIERZCHNIA_CIEMNA)
    p.setPen(QPen(z_alfa(PAPIER, 12), 1.0))
    for i in range(1, 4):
        y = pole.y() + pole.height() * i / 4.0
        p.drawLine(QPointF(pole.x() + 4, y), QPointF(pole.right() - 4, y))
    barwy = {"liniowa": TEKST_3, "lagodna": CYJAN, "wyjscie": ZIELEN, "sprezyna": BURSZTYN}
    for nazwa, kol in barwy.items():
        f = KRZYWE[nazwa]
        kr = QPainterPath()
        n = 64
        for i in range(n + 1):
            t = i / float(n)
            v = max(-0.12, min(1.12, f(t)))
            x = pole.x() + 8 + (pole.width() - 16) * t
            y = pole.bottom() - 14 - (pole.height() - 38) * v
            if i == 0:
                kr.moveTo(x, y)
            else:
                kr.lineTo(x, y)
        poswiata_linii(p, kr, kol, warstwy=((5, 26), (1.8, 230)))
    x = r.x() + 2
    for nazwa, kol in barwy.items():
        tekst(p, x, r.bottom() + 12, nazwa, kol, 10, 600, mono=True)
        x += _szer(nazwa, 10, 600, True) + 12
    _podpis(p, r.x() + 2, r.bottom() + 26, "Plynnie.do / teraz / gotowe")


def _probka_tekst(p, r):
    y = r.y() + 22
    tekst(p, r.x(), y, "999,00 zl", TEKST, 26, 800, naglowek=True, poswiata=0.0)
    y += 34
    tekst(p, r.x(), y, "999,00 zl", CYJAN, 26, 800, naglowek=True, poswiata=1.4)
    y += 30
    tekst(p, r.x(), y, "nagl. 13/700 " + rodzina_naglowek(), TEKST_2, 12, 700, naglowek=True)
    y += 20
    tekst(p, r.x(), y, "tekst 12/400 " + rodzina_tekst(), TEKST_2, 12, 400)
    y += 20
    tekst(p, r.x(), y, "mono 12/500 " + rodzina_mono(), TEKST_3, 12, 500, mono=True)
    _podpis(p, r.x(), r.bottom() + 12, "tekst   poswiata 0 / 1.4")


def _arkusz(sciezka_pliku):
    MARG, ODST = 26, 20
    KOL, WIE = 4, 3
    CW, CH = 330, 300
    W = MARG * 2 + KOL * CW + (KOL - 1) * ODST
    H = MARG * 2 + 76 + WIE * CH + (WIE - 1) * ODST

    obraz = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    obraz.fill(0)
    p = QPainter(obraz)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    calosc = QRectF(0, 0, W, H)
    tlo_sceny(p, calosc)

    tekst(p, MARG, MARG + 34, "MATERIAL", MIETA, 30, 800, naglowek=True, odstep=6.0, poswiata=1.2)
    n2 = "proto_styl"
    tekst(p, W - MARG - _szer(n2, 13, 500, True), MARG + 34, n2, TEKST_3, 13, 500, mono=True)
    p.setPen(QPen(z_alfa(PAPIER, 22), 1.0))
    p.drawLine(QPointF(MARG, MARG + 52), QPointF(W - MARG, MARG + 52))

    probki = (
        ("TLO SCENY", _probka_tlo),
        ("SZKLO", _probka_szklo),
        ("OBRYS", _probka_obrys),
        ("HALO", _probka_halo),
        ("SWIATLO KIERUNKOWE", _probka_swiatlo),
        ("SZRON", _probka_szron),
        ("ZIARNO", _probka_ziarno),
        ("CIEN", _probka_cien),
        ("LINIE I PUNKTY", _probka_linie),
        ("PALETA", _probka_paleta),
        ("PLYNNIE", _probka_plynnie),
        ("TEKST", _probka_tekst),
    )
    for i, (tyt, rysuj) in enumerate(probki):
        wier, kol = divmod(i, KOL)
        r = QRectF(MARG + kol * (CW + ODST), MARG + 76 + wier * (CH + ODST), CW, CH)
        wnetrze = _kafel(p, r, tyt)
        p.save()
        rysuj(p, QRectF(wnetrze.x(), wnetrze.y(), wnetrze.width(), wnetrze.height() - 22))
        p.restore()

    winieta(p, calosc, 70)
    ziarno(p, calosc, 8)
    p.end()
    obraz.save(sciezka_pliku)
    return W, H


if __name__ == "__main__":
    import os
    import sys

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtGui import QGuiApplication

    app = QGuiApplication(sys.argv)
    cel = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zrzut_styl.png")
    w, h = _arkusz(cel)
    print(f"{cel}  {w}x{h}")
