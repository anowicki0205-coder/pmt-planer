# -*- coding: utf-8 -*-
"""Prawa strona ekranu prototypu: trójwymiarowa mapa dnia i kartka delegacji.

Mapa nie jest już planszą oglądaną z góry. Scena ma trzy wymiary — punkt to
trójka (x na wschód, y na północ, z nad terenem) — a kamera patrzy na nią
pod kątem ``KAT_KAMERY`` stopni od pionu. Cały rzut liczy klasa :class:`Rzut`
zwykłą matematyką kamery dziurkowej; żadnej biblioteki 3D tu nie ma, bo być
jej nie może — do dyspozycji jest PyQt6 i biblioteka standardowa.

Co z tego wynika na obrazie:

* drogi i rzeka to pasy o stałej szerokości w świecie, więc na ekranie zbiegają
  się w głębi — to najtańszy i najczytelniejszy dowód perspektywy,
* teren to stos wypełnionych warstw wysokościowych z pionowymi ścianami,
  a nie zbiór krzywych: wzgórze zasłania to, co za nim,
* przy miastach stoją bryły zabudowy z widoczną ścianą przednią, ciemniejszą
  boczną i jaśniejszym dachem; każda kładzie długi cień na grunt,
* trasa dnia leży kilka jednostek nad gruntem i rzuca na niego własny cień,
* przystanki to pionowe słupy światła, tym wyższe, im więcej wizyt,
* podpisy miast są tabliczkami zwróconymi do widza — jako jedyne nie pochylają
  się razem z terenem, bo muszą pozostać czytelne.

Wszystko rysowane jest od najdalszego do najbliższego, bo tylko w tej
kolejności bliższe obiekty zasłaniają dalsze.

Rzut, teren, sieć dróg i zabudowa liczone są raz i siedzą w dwóch pixmapach
zależnych wyłącznie od rozmiaru widżetu: osobno grunt z terenem, osobno bryły
zabudowy — bo cień trasy leży między nimi. Klatka animacji dokłada do tego
płynący blask, kreski powrotu i oddech bazy; sama nic nie przelicza.

Zegary: MapaDnia i KartkaDelegacji mają ``ustaw_animacje(wlaczone)``.
Wyłączenie zatrzymuje zegar i ustawia stałą fazę — zrzuty są powtarzalne.
Zegary gasną też przy schowaniu i zamknięciu widżetu.
"""
import math

from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import (QPainter, QPainterPath, QPen, QBrush, QColor, QPixmap,
                         QFontMetricsF, QLinearGradient, QRadialGradient,
                         QPolygonF)
from PyQt6.QtWidgets import QWidget

import proto_styl as st
import proto_dane as dn


# ── świat i kamera ───────────────────────────────────────────────────
KAT_KAMERY = 55.0          # stopnie od pionu; 0 to widok z góry, 90 to widok z poziomu
ODLEGLOSC_KAMERY = 330.0   # w jednostkach świata — im bliżej, tym mocniejsza zbieżność

# Układ miast w jednostkach świata. Jest głębszy niż szerszy, bo perspektywa
# i tak skraca głębię o ponad połowę; inaczej mapa wyszłaby spłaszczona.
POLE_SWIATA_X = 200.0
POLE_SWIATA_Y = 336.0
KM_NA_JEDNOSTKE = 235.0 / POLE_SWIATA_X    # ten sam przelicznik, co w proto_dane

# Światło: wektor wskazujący źródło, w świecie. Niskie z daje długie cienie.
SWIATLO_3D = (-0.56, 0.42, 0.60)

BARWA_TERENU = QColor(126, 178, 206)      # chłodny kamień, prawie bez nasycenia
BARWA_MGLY = QColor(150, 196, 226)        # mgła odległości w głębi sceny
BARWA_DACHU = QColor(54, 77, 99)
BARWA_SCIANY = QColor(21, 33, 49)
BARWA_BOKU = QColor(7, 12, 21)

KOMORKA_TERENU = 172.0     # bok siatki, w której może stanąć jedno wzgórze
WZNIOS_TRASY = 11.0        # o tyle trasa unosi się nad gruntem


def _hasz(*klucze):
    """Powtarzalna liczba 0..1 z dowolnych kluczy.

    Teren i zabudowa mają wyglądać tak samo przy każdym uruchomieniu, a przy
    tym zależeć od położenia w świecie — stąd hasz zamiast generatora ciągu.
    """
    n = 2166136261
    for k in klucze:
        if isinstance(k, str):
            for z in k.encode("utf-8"):
                n = ((n ^ z) * 16777619) & 0xFFFFFFFF
        else:
            v = int(k) & 0xFFFFFFFF
            for _ in range(4):
                n = ((n ^ (v & 0xFF)) * 16777619) & 0xFFFFFFFF
                v >>= 8
        n = ((n ^ 0x9E3779B9) * 16777619) & 0xFFFFFFFF
    n ^= n >> 15
    n = (n * 2246822519) & 0xFFFFFFFF
    n ^= n >> 13
    return n / float(0xFFFFFFFF)


def _swiat_miasta(fx, fy):
    """Ułamkowe współrzędne miasta z proto_dane → punkt świata (x, y)."""
    return ((fx - 0.5) * POLE_SWIATA_X, (0.5 - fy) * POLE_SWIATA_Y)


def _tlumik_doliny(x, y):
    """Prawie 0 w dolinie, w której stoją miasta, 1 poza nią.

    Dzięki temu wzgórza rosną dookoła układu miast, a nie pod nim — drogi,
    rzeka i zabudowa leżą na spokojnym dnie doliny. Dolna granica nie jest
    zerem, więc dno i tak lekko faluje: płaska plansza wyglądałaby martwo.
    """
    d = math.hypot(x / (POLE_SWIATA_X * 0.72), y / (POLE_SWIATA_Y * 0.62))
    return max(0.07, min(1.0, (d - 0.84) / 0.78))


class Rzut:
    """Kamera dziurkowa: punkt sceny (x, y, z) → punkt ekranu i skala.

    Kamera stoi na południe od celu i nad nim, patrzy w dół pod kątem ``kat``
    od pionu. Nie jest obrócona wokół osi patrzenia, więc oś wschód-zachód
    świata pokrywa się z poziomą osią ekranu — dzięki temu ``x`` liczy się
    w rzucie jednym mnożeniem.

    Ogniskową i przesunięcie dobiera konstruktor tak, żeby zadany obszar
    świata trafił dokładnie w zadany prostokąt ekranu. Nic tu nie jest
    wpisane na sztywno w pikselach, więc mapa znosi każdy rozmiar okna.
    """

    def __init__(self, pole, obszar, kat=KAT_KAMERY, odleglosc=ODLEGLOSC_KAMERY):
        a = math.radians(kat)
        self.kat = a
        self.sin_a, self.cos_a = math.sin(a), math.cos(a)
        # trójnóg kamery: oś patrzenia, góra i prawo
        self.f = (0.0, self.sin_a, -self.cos_a)
        self.u = (0.0, self.cos_a, self.sin_a)
        self.r = (1.0, 0.0, 0.0)
        self.d = float(odleglosc)

        x0, y0, sx, sy = obszar
        cel = (x0 + sx * 0.5, y0 + sy * 0.5, 0.0)
        self.cel = cel
        self.oko = (cel[0] - self.f[0] * self.d,
                    cel[1] - self.f[1] * self.d,
                    cel[2] - self.f[2] * self.d)

        # wpasowanie: cztery narożniki obszaru miast mają zmieścić się w polu
        rogi = ((x0, y0), (x0 + sx, y0), (x0, y0 + sy), (x0 + sx, y0 + sy))
        sur = [self._surowy(x, y, 0.0) for (x, y) in rogi]
        us = [s[0] for s in sur]
        vs = [s[1] for s in sur]
        szer_u = max(1e-6, max(us) - min(us))
        szer_v = max(1e-6, max(vs) - min(vs))
        self.k = min(pole.width() / szer_u, pole.height() / szer_v)
        self.px = pole.center().x() - self.k * (min(us) + max(us)) * 0.5
        self.py = pole.center().y() - self.k * (min(vs) + max(vs)) * 0.5

        # kierunek światła przeniesiony na ekran — ten sam dla cieni i rozbłysków
        lx, ly, lz = SWIATLO_3D
        ex = lx
        ey = -(ly * self.u[1] + lz * self.u[2])
        dl = math.hypot(ex, ey) or 1.0
        self.swiatlo_ekran = (ex / dl, ey / dl)
        # o ile przesuwa się cień punktu na wysokości 1 nad gruntem
        self.cien_x = -lx / lz
        self.cien_y = -ly / lz

    # — rzut —
    def _surowy(self, x, y, z):
        vx = x - self.oko[0]
        vy = y - self.oko[1]
        vz = z - self.oko[2]
        gleb = vx * self.f[0] + vy * self.f[1] + vz * self.f[2]
        if gleb < 1.0:                      # punkt za kamerą — przyklejamy do horyzontu
            gleb = 1.0
        b = vx * self.u[0] + vy * self.u[1] + vz * self.u[2]
        return vx / gleb, -b / gleb, gleb

    def rzutuj(self, x, y, z=0.0):
        """Punkt sceny → (punkt ekranu, skala malejąca z odległością).

        Skala to liczba pikseli przypadająca na jednostkę świata w tym miejscu
        sceny: przy dalekiej krawędzi terenu jest kilka razy mniejsza niż przy
        bliskiej, więc obiekty same maleją w głębi.
        """
        u, v, gleb = self._surowy(x, y, z)
        return QPointF(self.px + self.k * u, self.py + self.k * v), self.k / gleb

    def ekran(self, x, y, z=0.0):
        """Sam punkt ekranu — wersja do gorących pętli, bez pakowania krotek."""
        vx = x - self.oko[0]
        vy = y - self.oko[1]
        vz = z - self.oko[2]
        gleb = vx * self.f[0] + vy * self.f[1] + vz * self.f[2]
        if gleb < 1.0:
            gleb = 1.0
        b = vx * self.u[0] + vy * self.u[1] + vz * self.u[2]
        return QPointF(self.px + self.k * vx / gleb, self.py - self.k * b / gleb)

    def glebokosc(self, x, y, z=0.0):
        """Odległość punktu wzdłuż osi patrzenia — po niej sortujemy rysowanie."""
        return (x - self.oko[0]) * self.f[0] + (y - self.oko[1]) * self.f[1] \
            + (z - self.oko[2]) * self.f[2]

    def skala(self, x, y, z=0.0):
        return self.k / max(1.0, self.glebokosc(x, y, z))

    def na_grunt(self, sx, sy, dal_max=2600.0):
        """Punkt ekranu → punkt na płaszczyźnie z=0 (promień z oka przez piksel)."""
        u = (sx - self.px) / self.k
        v = (sy - self.py) / self.k
        dx = self.f[0] + self.r[0] * u - self.u[0] * v
        dy = self.f[1] + self.r[1] * u - self.u[1] * v
        dz = self.f[2] + self.r[2] * u - self.u[2] * v
        if dz > -1e-4:                       # promień nad horyzontem — bierzemy daleko
            t = dal_max
        else:
            t = min(dal_max, -self.oko[2] / dz)
        return (self.oko[0] + dx * t, self.oko[1] + dy * t)

    # — mgła odległości —
    def mgla(self, gleb):
        """0 przy widzu, 1 w głębi sceny — ile mgły kłaść na barwę."""
        t = (gleb - self.d * 0.42) / (self.d * 2.35)
        return 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)

    def zamgl(self, kolor, t, sila=0.78):
        """Barwa przesunięta ku mgle: mniejszy kontrast i jaśniejsze tło w głębi."""
        u = t * sila
        return QColor(int(kolor.red() + (BARWA_MGLY.red() - kolor.red()) * u),
                      int(kolor.green() + (BARWA_MGLY.green() - kolor.green()) * u),
                      int(kolor.blue() + (BARWA_MGLY.blue() - kolor.blue()) * u),
                      kolor.alpha())


# ── drobne narzędzia ─────────────────────────────────────────────────
class _Losowy:
    """Własny generator liniowy: ten sam wynik przy każdym odświeżeniu.

    Nie używamy random z modułu, żeby obraz nie zależał od tego, co inni
    wylosowali wcześniej w tym samym procesie.
    """

    def __init__(self, ziarno=20260902):
        self.stan = int(ziarno) & 0x7FFFFFFF

    def nast(self):
        self.stan = (1103515245 * self.stan + 12345) & 0x7FFFFFFF
        return self.stan / float(0x7FFFFFFF)

    def zakres(self, a, b):
        return a + (b - a) * self.nast()


def _gladko_2d(punkty, na_odcinek=8, zamknieta=False):
    """Catmull–Rom w świecie: punkty sterujące → gęsta łamana (lista par)."""
    n = len(punkty)
    if n < 2:
        return list(punkty)

    def we(i):
        if zamknieta:
            return punkty[i % n]
        return punkty[max(0, min(n - 1, i))]

    wynik = []
    ostatni = n if zamknieta else n - 1
    for i in range(ostatni):
        (x0, y0), (x1, y1) = we(i - 1), we(i)
        (x2, y2), (x3, y3) = we(i + 1), we(i + 2)
        for s in range(na_odcinek):
            t = s / float(na_odcinek)
            t2, t3 = t * t, t * t * t
            wynik.append((
                0.5 * ((2 * x1) + (-x0 + x2) * t + (2 * x0 - 5 * x1 + 4 * x2 - x3) * t2
                       + (-x0 + 3 * x1 - 3 * x2 + x3) * t3),
                0.5 * ((2 * y1) + (-y0 + y2) * t + (2 * y0 - 5 * y1 + 4 * y2 - y3) * t2
                       + (-y0 + 3 * y1 - 3 * y2 + y3) * t3)))
    if not zamknieta:
        wynik.append(punkty[-1])
    return wynik


def _rowno(punkty, ile):
    """Przepróbkowanie łamanej na ``ile`` punktów równo rozłożonych po długości."""
    if len(punkty) < 2:
        return list(punkty) * ile
    dlug = [0.0]
    for i in range(1, len(punkty)):
        dlug.append(dlug[-1] + math.hypot(punkty[i][0] - punkty[i - 1][0],
                                          punkty[i][1] - punkty[i - 1][1]))
    caly = dlug[-1] or 1.0
    wynik, j = [], 0
    for i in range(ile):
        cel = caly * i / float(ile - 1)
        while j < len(dlug) - 2 and dlug[j + 1] < cel:
            j += 1
        odc = max(1e-9, dlug[j + 1] - dlug[j])
        t = max(0.0, min(1.0, (cel - dlug[j]) / odc))
        wynik.append((punkty[j][0] + (punkty[j + 1][0] - punkty[j][0]) * t,
                      punkty[j][1] + (punkty[j + 1][1] - punkty[j][1]) * t))
    return wynik


def _wstega(rzut, punkty, szerokosc, wysokosc=None, wznios=0.0):
    """Pas o stałej szerokości w świecie — na ekranie zwęża się w głębi.

    To najprostszy dowód perspektywy na mapie: droga biegnąca w głąb sceny
    sama zbiega do punktu zbiegu, bez żadnego rysowania „na oko”.
    """
    n = len(punkty)
    if n < 2:
        return QPainterPath()
    lewa, prawa = [], []
    for i in range(n):
        x, y = punkty[i]
        if i == 0:
            dx, dy = punkty[1][0] - x, punkty[1][1] - y
        elif i == n - 1:
            dx, dy = x - punkty[n - 2][0], y - punkty[n - 2][1]
        else:
            dx = punkty[i + 1][0] - punkty[i - 1][0]
            dy = punkty[i + 1][1] - punkty[i - 1][1]
        dl = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / dl * szerokosc * 0.5, dx / dl * szerokosc * 0.5
        z = (wysokosc(x, y) if wysokosc is not None else 0.0) + wznios
        lewa.append(rzut.ekran(x + nx, y + ny, z))
        prawa.append(rzut.ekran(x - nx, y - ny, z))
    s = QPainterPath()
    s.moveTo(lewa[0])
    for pt in lewa[1:]:
        s.lineTo(pt)
    for pt in reversed(prawa):
        s.lineTo(pt)
    s.closeSubpath()
    return s


def _lamana(punkty):
    """Lista punktów ekranu → otwarta ścieżka."""
    s = QPainterPath()
    if not punkty:
        return s
    s.moveTo(punkty[0])
    for pt in punkty[1:]:
        s.lineTo(pt)
    return s


def _kreskowana(p, sciezka, kolor, warstwy=((15, 22), (7, 60), (2.4, 205)),
                kreska=10.0, przerwa=8.0, przesuniecie=0.0):
    """Świecąca linia kreskowana — poswiata_linii nie umie wzorów kreski."""
    p.setBrush(Qt.BrushStyle.NoBrush)
    for szer, alfa in warstwy:
        pen = QPen(st.z_alfa(kolor, alfa), szer)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        # wzór kreski podaje się w wielokrotnościach grubości pióra
        pen.setDashPattern([max(0.5, kreska / szer), max(0.4, przerwa / szer)])
        if przesuniecie:
            pen.setDashOffset(przesuniecie / szer)
        p.setPen(pen)
        p.drawPath(sciezka)


def _poswiata_zmienna(p, punkty, skale, kolor, warstwy):
    """Świecąca linia o grubości malejącej w głębi sceny.

    Pióro Qt ma jedną szerokość na całą ścieżkę, więc trasę rysujemy odcinek
    po odcinku, każdy grubością wziętą z lokalnej skali rzutu. Warstwy podaje
    się jako (szerokość w jednostkach świata, alfa, co ile punktów) — szeroka
    i miękka poświata nie potrzebuje gęstej łamanej, więc przeskakuje punkty.
    """
    p.setBrush(Qt.BrushStyle.NoBrush)
    n = len(punkty)
    if n < 2:
        return
    for szer, alfa, krok in warstwy:
        pen = QPen(st.z_alfa(kolor, alfa), 1.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        i = 0
        while i < n - 1:
            j = min(n - 1, i + krok)
            pen.setWidthF(max(0.7, szer * (skale[i] + skale[j]) * 0.5))
            p.setPen(pen)
            p.drawLine(punkty[i], punkty[j])
            i = j


def _wypukla_otoczka(punkty):
    """Otoczka wypukła (obchód Andrew) — obrys cienia bryły na gruncie."""
    pkt = sorted(set(punkty))
    if len(pkt) < 3:
        return pkt

    def kierunek(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    dol = []
    for p in pkt:
        while len(dol) >= 2 and kierunek(dol[-2], dol[-1], p) <= 0:
            dol.pop()
        dol.append(p)
    gora = []
    for p in reversed(pkt):
        while len(gora) >= 2 and kierunek(gora[-2], gora[-1], p) <= 0:
            gora.pop()
        gora.append(p)
    return dol[:-1] + gora[:-1]


def _napis(p, x, y, napis, kolor, rozmiar, waga=400, mono=False,
           naglowek=False, odstep=0.0, prawy=False):
    """Rysuje tekst od linii bazowej; przy prawy=True x jest prawą krawędzią."""
    f = st.czcionka(rozmiar, waga, mono, naglowek, odstep)
    p.setFont(f)
    p.setPen(QPen(kolor))
    if prawy:
        x -= QFontMetricsF(f).horizontalAdvance(napis)
    p.drawText(QPointF(x, y), napis)
    return x


def _przytnij(napis, f, szerokosc):
    """Skraca napis wielokropkiem, żeby nie wyszedł poza rubrykę."""
    m = QFontMetricsF(f)
    if m.horizontalAdvance(napis) <= szerokosc:
        return napis
    return m.elidedText(napis, Qt.TextElideMode.ElideRight, int(szerokosc))


def _zawin(napis, f, szerokosc, ile_linii=2):
    """Prymitywne łamanie po wyrazach — tekst celu wyjazdu ma dwie linie."""
    m = QFontMetricsF(f)
    slowa = napis.split(" ")
    linie, biezaca = [], ""
    for s in slowa:
        proba = (biezaca + " " + s).strip()
        if m.horizontalAdvance(proba) <= szerokosc or not biezaca:
            biezaca = proba
        else:
            linie.append(biezaca)
            biezaca = s
            if len(linie) == ile_linii:
                break
    if len(linie) < ile_linii and biezaca:
        linie.append(biezaca)
    if len(linie) == ile_linii:
        linie[-1] = _przytnij(linie[-1], f, szerokosc)
    return linie[:ile_linii]


def _poduszka(p, pole, promien=None, sila=150, warstw=5):
    """Miękka ciemna poduszka pod tekstem — bez ramki, sam zanik ku brzegom."""
    if pole.isEmpty():
        return
    promien = pole.height() * 0.48 if promien is None else promien
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(warstw, 0, -1):
        rozlew = (i - 1) * max(1.6, pole.height() * 0.16)
        a = int(sila * (1.0 - (i - 1) / float(warstw)) ** 1.8 / warstw * 1.9)
        if a <= 0:
            continue
        r = pole.adjusted(-rozlew, -rozlew * 0.72, rozlew, rozlew * 0.72)
        s = QPainterPath()
        s.addRoundedRect(r, promien + rozlew, promien + rozlew)
        p.fillPath(s, QColor(3, 8, 15, a))


def _cien_miekki(p, pole, promien, przesun, rozmycie, sila, barwa=QColor(0, 0, 0), krok=2):
    """Jedna warstwa miękkiego cienia: zanik kwadratowy, krok w pikselach.

    Im dalszy cień, tym rzadszy krok — rozmycie i tak zjada różnicę, a rysuje
    się dwa razy mniej ścieżek.
    """
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
        p.fillPath(s, st.z_alfa(barwa, a))


def _pioro_gradientowe(a, b, kolor_a, kolor_b, szerokosc=1.0):
    """Pióro malowane gradientem — do cienkich linii, które gasną na końcu."""
    g = QLinearGradient(a, b)
    g.setColorAt(0.0, kolor_a)
    g.setColorAt(1.0, kolor_b)
    pen = QPen(QBrush(g), szerokosc)
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    return pen


def _na_minuty(godzina):
    try:
        g, m = godzina.split(":")
        return int(g) * 60 + int(m)
    except Exception:
        return 0


def _na_godzine(minuty):
    minuty = int(round(minuty)) % (24 * 60)
    return f"{minuty // 60:02d}:{minuty % 60:02d}"


def odcinki_dnia(dzien):
    """Rozkłada dzień na odcinki trasy: godziny, kilometry i złotówki.

    Prototyp nie liczy tras naprawdę — dzieli dzienne km i kwotę po długości
    odcinków na mapie, tak żeby sumy zgadzały się co do grosza.
    """
    if dzien is None or dzien.wolny or len(dzien.trasa) < 2:
        return []
    punkty = dzien.trasa
    pary = [(punkty[i], punkty[i + 1]) for i in range(len(punkty) - 1)]

    dlugosci = []
    for a, b in pary:
        ax, ay = dn.MIASTA.get(a, (0.5, 0.5))
        bx, by = dn.MIASTA.get(b, (0.5, 0.5))
        dlugosci.append(max(0.02, math.hypot(ax - bx, ay - by)))
    suma_dl = sum(dlugosci)

    start = _na_minuty(dzien.start)
    koniec = _na_minuty(dzien.koniec)
    caly_czas = max(60, koniec - start)
    postojow = max(1, len(pary) - 1)
    czas_postoju = caly_czas * 0.34 / postojow          # wizyty w sklepach
    czas_jazdy = caly_czas - czas_postoju * postojow

    odcinki = []
    zegar = start
    suma_km, suma_zl = 0.0, 0.0
    for i, (a, b) in enumerate(pary):
        udzial = dlugosci[i] / suma_dl
        km = round(dzien.km * udzial, 1)
        zlot = round(km * dn.STAWKA, 2)
        if i == len(pary) - 1:                          # domknięcie sum
            km = round(dzien.km - suma_km, 1)
            zlot = round(dzien.kwota - suma_zl, 2)
        suma_km += km
        suma_zl += zlot
        wyjazd = zegar
        przyjazd = wyjazd + czas_jazdy * udzial
        zegar = przyjazd + czas_postoju
        odcinki.append({
            "wyj": _na_godzine(wyjazd),
            "z": a, "do": b,
            "przyj": _na_godzine(przyjazd),
            "km": km, "zl": zlot,
        })
    return odcinki


# ── mapa dnia ────────────────────────────────────────────────────────
class MapaDnia(QWidget):
    """Trójwymiarowa mapa okolicy z trasą dnia. Cała rysowana ręcznie."""

    klikniete_miasto = pyqtSignal(str)

    KLATKA = 40                # ms między klatkami blasku
    OKRES_BLASKU = 7600.0      # ms na jeden przebieg blasku wzdłuż trasy
    FAZA_ZRZUTU = 0.46         # gdzie stoi blask przy wyłączonej animacji

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setMinimumSize(360, 250)
        self._dzien = None
        self._kotwica = None
        self._stan = "zwykly"

        # geometria świata liczona raz, niezależna od rozmiaru okna
        self._miasta = {n: _swiat_miasta(*fr) for n, fr in dn.MIASTA.items()}
        self._siec = self._zbuduj_siec()
        self._drogi = self._ksztalty_drog()
        self._sasiedzi = self._zbuduj_graf()
        self._zabudowa = self._zbuduj_zabudowe()
        self._rzeka = self._zbuduj_rzeke()

        self._kopuly = []               # wzgórza w postaci do liczenia wysokości
        self._rzut = None               # kamera; zależy tylko od rozmiaru widżetu
        self._rzut_klucz = None
        self._wzgorza = None            # teren widoczny przy tym rozmiarze
        self._statyk = None             # grunt, teren, rzeka, drogi i zabudowa
        self._statyk_klucz = None
        self._dol = None                # statyka + cień i światło trasy
        self._gora = None               # słupy przystanków i tabliczki
        self._warstwy_klucz = None
        self._geo = None                # policzona geometria trasy i podpisów
        self._geo_klucz = None
        self._faza = self.FAZA_ZRZUTU
        self._anim = True
        self._zegar = QTimer(self)
        self._zegar.setInterval(self.KLATKA)
        self._zegar.timeout.connect(self._tik)
        # teren przelicza się dopiero, gdy rozmiar okna przestanie się zmieniać
        self._zegar_terenu = QTimer(self)
        self._zegar_terenu.setSingleShot(True)
        self._zegar_terenu.setInterval(180)
        self._zegar_terenu.timeout.connect(self._przelicz_teren)
        self._rozsadz_zegar()

    # — interfejs publiczny —
    def ustaw_dzien(self, dzien):
        self._dzien = dzien
        self._geo_klucz = None
        self._rozsadz_zegar()
        self.update()

    def ustaw_kotwice_kartki(self, punkt):
        """Punkt (we współrzędnych mapy), do którego biegnie nitka; None = brak."""
        self._kotwica = QPointF(punkt) if punkt is not None else None
        self._geo_klucz = None
        self.update()

    def ustaw_stan(self, nazwa):
        self._stan = nazwa if nazwa in ("zwykly", "sukces") else "zwykly"
        self._geo_klucz = None
        self.update()

    def ustaw_animacje(self, wlaczone):
        """Włącza albo gasi blask trasy. Wyłączony ustawia stałą fazę."""
        self._anim = bool(wlaczone)
        if not self._anim:
            self._faza = self.FAZA_ZRZUTU
            if self._zegar_terenu.isActive():     # zrzut ma mieć ostry teren
                self._zegar_terenu.stop()
                self._przelicz_teren()
        self._rozsadz_zegar()
        self.update()

    def zatrzymaj_animacje(self):
        """Skrót używany przy zamykaniu okna i przed zrzutami."""
        self.ustaw_animacje(False)

    def animacje_wlaczone(self):
        return self._anim

    def sizeHint(self):
        return QSize(900, 600)

    # — zegar —
    def _rozsadz_zegar(self):
        if self._anim and self._czynny() and self.isVisible():
            if not self._zegar.isActive():
                self._zegar.start()
        elif self._zegar.isActive():
            self._zegar.stop()

    def _tik(self):
        self._faza = (self._faza + self.KLATKA / self.OKRES_BLASKU) % 1.0
        self.update()

    def showEvent(self, zdarzenie):
        super().showEvent(zdarzenie)
        self._rozsadz_zegar()

    def hideEvent(self, zdarzenie):
        self._zegar.stop()
        super().hideEvent(zdarzenie)

    def closeEvent(self, zdarzenie):
        self._zegar.stop()
        self._zegar_terenu.stop()
        super().closeEvent(zdarzenie)

    def resizeEvent(self, zdarzenie):
        self._rzut_klucz = None
        self._warstwy_klucz = None
        self._geo_klucz = None
        # w trakcie ciągnięcia okna statyka jest rozciągana, nie przeliczana
        self._zegar_terenu.start()
        super().resizeEvent(zdarzenie)

    def _przelicz_teren(self):
        self._statyk_klucz = None
        self._warstwy_klucz = None
        self.update()

    # — kamera —
    def _pole(self):
        """Prostokąt ekranu, w który ma trafić układ miast.

        Jest węższy od widżetu i przesunięty w lewo — prawą stronę zasłania
        kartka delegacji, dokładnie jak na projekcie.
        """
        r = QRectF(self.rect())
        return QRectF(r.x() + r.width() * 0.040, r.y() + r.height() * 0.055,
                      r.width() * 0.645, r.height() * 0.885)

    def rzut(self):
        """Kamera dla obecnego rozmiaru widżetu — liczona raz i pamiętana."""
        klucz = (self.width(), self.height())
        if self._rzut is not None and self._rzut_klucz == klucz:
            return self._rzut
        obszar = (-POLE_SWIATA_X * 0.5, -POLE_SWIATA_Y * 0.5,
                  POLE_SWIATA_X, POLE_SWIATA_Y)
        self._rzut = Rzut(self._pole(), obszar)
        self._rzut_klucz = klucz
        self._wzgorza = None
        return self._rzut

    def rzutuj(self, x, y, z=0.0):
        """Punkt sceny → (punkt ekranu, skala). Skrót do kamery widżetu."""
        return self.rzut().rzutuj(x, y, z)

    # — teren —
    def _zbuduj_wzgorza(self, rzut):
        """Wzgórza na siatce komórek pokrywającej to, co widać.

        Każde wzgórze to bryła: pięć do siedmiu warstw wysokości o nieregularnym
        obrysie, jedna nad drugą. Kształt bierze się z hasza położenia komórki,
        więc przy zmianie rozmiaru okna teren dobudowuje się po bokach, zamiast
        losować się od nowa.
        """
        r = QRectF(self.rect())
        rogi = [rzut.na_grunt(r.x(), r.y()), rzut.na_grunt(r.right(), r.y()),
                rzut.na_grunt(r.x(), r.bottom()), rzut.na_grunt(r.right(), r.bottom())]
        xs = [p[0] for p in rogi]
        ys = [p[1] for p in rogi]
        x0 = max(-1250.0, min(xs) - KOMORKA_TERENU)
        x1 = min(1600.0, max(xs) + KOMORKA_TERENU)
        y0 = max(-520.0, min(ys) - KOMORKA_TERENU)
        y1 = min(1050.0, max(ys) + KOMORKA_TERENU)

        boki = 13
        wzgorza = []
        for i in range(int(math.floor(x0 / KOMORKA_TERENU)),
                       int(math.ceil(x1 / KOMORKA_TERENU)) + 1):
            for j in range(int(math.floor(y0 / KOMORKA_TERENU)),
                           int(math.ceil(y1 / KOMORKA_TERENU)) + 1):
                if _hasz(i, j, 1) > 0.76:            # nie w każdej komórce stoi garb
                    continue
                cx = (i + 0.16 + 0.68 * _hasz(i, j, 2)) * KOMORKA_TERENU
                cy = (j + 0.16 + 0.68 * _hasz(i, j, 3)) * KOMORKA_TERENU
                tlum = _tlumik_doliny(cx, cy)
                if tlum <= 0.02:                      # dolina miast zostaje płaska
                    continue
                prom = KOMORKA_TERENU * (0.34 + 0.30 * _hasz(i, j, 4))
                wys = (34.0 + 92.0 * _hasz(i, j, 5) ** 1.35) * tlum
                ile = 5 + int(_hasz(i, j, 6) * 2.99)
                splasz = 0.66 + 0.52 * _hasz(i, j, 7)
                obrot = 2.0 * math.pi * _hasz(i, j, 8)
                srodek, ska = rzut.rzutuj(cx, cy, 0.0)
                zasieg = prom * ska * 1.7 + wys * ska
                if (srodek.x() + zasieg < r.x() - 4 or srodek.x() - zasieg > r.right() + 4
                        or srodek.y() + zasieg < r.y() - 4
                        or srodek.y() - zasieg > r.bottom() + 4):
                    continue                          # całe wzgórze poza widżetem
                fala = [0.74 + 0.52 * _hasz(i, j, 20 + t) for t in range(boki)]
                wzgorza.append({
                    "cx": cx, "cy": cy, "prom": prom, "wys": wys, "ile": ile,
                    "splasz": splasz, "obrot": obrot, "fala": fala,
                    "gleb": rzut.glebokosc(cx, cy, 0.0),
                })
        wzgorza.sort(key=lambda w: -w["gleb"])        # od najdalszego do najbliższego
        # skrócony opis kopuł do liczenia wysokości terenu
        self._kopuly = [(w["cx"], w["cy"], w["prom"], w["prom"] * w["splasz"], w["wys"])
                        for w in wzgorza]
        return wzgorza

    def _wysokosc(self, x, y):
        """Wysokość terenu w punkcie — suma miękkich kopuł wszystkich wzgórz.

        Wywoływana tysiące razy przy liczeniu trasy i dróg, więc najpierw
        odrzuca wzgórza po prostokącie otaczającym, a dopiero potem liczy.
        """
        h = 0.0
        for (cx, cy, rx, ry, wys) in self._kopuly:
            dx = x - cx
            if dx < -rx or dx > rx:
                continue
            dy = y - cy
            if dy < -ry or dy > ry:
                continue
            dx /= rx
            dy /= ry
            r2 = dx * dx + dy * dy
            if r2 < 1.0:
                h += wys * (1.0 - r2) ** 1.3
        return h

    def _obrys_wzgorza(self, w, s, k=0):
        """Obrys warstwy wzgórza skurczonej do ułamka ``s`` promienia.

        Zaburzenie przesuwa się z wysokością, więc kolejne warstwy nie są
        swoimi kopiami — wzgórze wygląda jak bryła, a nie jak stos talerzy.
        """
        boki = len(w["fala"])
        m = 0.45 * (1.0 - s)
        punkty = []
        for j in range(boki):
            kat = 2.0 * math.pi * j / boki + w["obrot"] + 0.10 * k
            fala = w["fala"][j] * (1.0 - m) + w["fala"][(j + 5 * k) % boki] * m
            rr = w["prom"] * s * fala
            punkty.append((w["cx"] + math.cos(kat) * rr,
                           w["cy"] + math.sin(kat) * rr * w["splasz"]))
        return _gladko_2d(punkty, na_odcinek=2, zamknieta=True)

    def _rysuj_teren(self, p, rzut):
        """Bryły wzgórz: warstwa po warstwie, od dołu do góry, od dali do widza."""
        p.setPen(Qt.PenStyle.NoPen)
        lx, ly = rzut.swiatlo_ekran
        for w in self._wzgorza:
            skala = rzut.k / max(1.0, w["gleb"])
            r_pix = w["prom"] * skala
            if r_pix < 3.5 or w["wys"] * skala < 1.6:
                continue                               # za mały garb, żeby go było widać
            mgla = rzut.mgla(w["gleb"])
            moc = min(1.0, w["wys"] / 44.0) ** 0.8      # ile kontrastu dostaje bryła
            drobny = r_pix < 22.0 or w["wys"] * skala < 7.0
            ile = 3 if drobny else w["ile"]

            # cień całego wzgórza kładziony na grunt w stronę przeciwną do światła
            if not drobny:
                pod = self._obrys_wzgorza(w, 1.0)
                cx = w["wys"] * 0.42 * rzut.cien_x
                cy = w["wys"] * 0.42 * rzut.cien_y
                wiel = QPolygonF([rzut.ekran(x + cx, y + cy, 0.0) for (x, y) in pod])
                s = QPainterPath()
                s.addPolygon(wiel)
                p.fillPath(s, QColor(0, 0, 0, int(52 * min(1.0, w["wys"] / 46.0)
                                                    * (1.0 - mgla * 0.8))))

            poprz_obrys, poprz_z = None, 0.0
            for k in range(ile):
                s_dol = 1.0 - k / float(ile)
                z = w["wys"] * (1.0 - s_dol * s_dol) ** 1.3
                obrys = self._obrys_wzgorza(w, s_dol, k)
                t = k / float(max(1, ile - 1))

                # a) pionowa ściana od poprzedniej warstwy do tej — stąd bryła
                gorne = [rzut.ekran(x, y, z) for (x, y) in obrys]
                if poprz_obrys is not None and not drobny:
                    sciana = QPainterPath()
                    sciana.setFillRule(Qt.FillRule.WindingFill)
                    dolne = [rzut.ekran(x, y, poprz_z) for (x, y) in obrys[::2]]
                    rzadkie = gorne[::2]
                    n = len(dolne)
                    for q in range(n):
                        q2 = (q + 1) % n
                        sciana.addPolygon(QPolygonF([dolne[q], dolne[q2],
                                                     rzadkie[q2], rzadkie[q]]))
                    pole = sciana.boundingRect()
                    g = QLinearGradient(
                        QPointF(pole.center().x() + lx * pole.width() * 0.6,
                                pole.center().y() + ly * pole.height() * 0.6),
                        QPointF(pole.center().x() - lx * pole.width() * 0.6,
                                pole.center().y() - ly * pole.height() * 0.6))
                    jasna = rzut.zamgl(QColor(92, 130, 160), mgla)
                    ciemna = rzut.zamgl(QColor(3, 7, 15), mgla)
                    g.setColorAt(0.0, st.z_alfa(jasna, int((196 - 72 * mgla) * moc)))
                    g.setColorAt(0.38, st.z_alfa(ciemna, int((214 - 84 * mgla) * moc)))
                    g.setColorAt(1.0, st.z_alfa(ciemna, int((240 - 96 * mgla) * moc)))
                    p.fillPath(sciana, QBrush(g))

                # b) taras: wypełniony kształt o nieregularnej krawędzi,
                #    jaśniejszy od strony światła, ciemniejszy po przeciwnej
                gora = QPainterPath()
                gora.addPolygon(QPolygonF(gorne))
                pole = gora.boundingRect()
                sr = pole.center()
                zas = max(pole.width(), pole.height()) * 0.62 + 1.0
                jasny = QPointF(sr.x() + lx * zas, sr.y() + ly * zas)
                ciemny = QPointF(sr.x() - lx * zas, sr.y() - ly * zas)
                barwa = rzut.zamgl(BARWA_TERENU, mgla)
                sila = (8.0 + 18.0 * t) * (1.0 - 0.42 * mgla) * (0.42 + 0.58 * moc)
                g = QLinearGradient(jasny, ciemny)
                g.setColorAt(0.0, st.z_alfa(barwa, int(sila * 1.35)))
                g.setColorAt(0.58, st.z_alfa(barwa, int(sila * 0.86)))
                g.setColorAt(1.0, st.z_alfa(barwa, int(sila * 0.42)))
                p.fillPath(gora, QBrush(g))

                # c) grzbiet zbierający światło po stronie źródła
                if not drobny:
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(_pioro_gradientowe(
                        jasny, ciemny,
                        st.z_alfa(rzut.zamgl(st.MIETA, mgla),
                                  int((58 + 46 * t) * (1.0 - mgla * 0.85) * (0.35 + 0.65 * moc))),
                        QColor(0, 0, 0, 0), max(1.0, min(2.0, r_pix * 0.03))))
                    p.drawPath(gora)
                    p.setPen(Qt.PenStyle.NoPen)

                # cienka poziomica w połowie stopnia — faktura zbocza
                if not drobny and k in (1, 3) and k + 1 < ile and r_pix > 34.0:
                    s_sr = 1.0 - (k + 0.5) / float(ile)
                    z_sr = w["wys"] * (1.0 - s_sr * s_sr) ** 1.3
                    posr = QPainterPath()
                    posr.addPolygon(QPolygonF([rzut.ekran(qx, qy, z_sr)
                                               for (qx, qy) in
                                               self._obrys_wzgorza(w, s_sr, k)]))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.setPen(QPen(st.z_alfa(rzut.zamgl(BARWA_TERENU, mgla),
                                            int(30 * (1.0 - mgla * 0.7) * moc)), 1.0))
                    p.drawPath(posr)
                    p.setPen(Qt.PenStyle.NoPen)
                poprz_obrys, poprz_z = obrys, z

    # — grunt, siatka, mgła —
    def _rysuj_grunt(self, p, rzut, r):
        """Dno doliny: ciemniejsze przy widzu, coraz jaśniejsze w głębi."""
        g = QLinearGradient(QPointF(r.x(), r.y()), QPointF(r.x(), r.bottom()))
        g.setColorAt(0.0, QColor(20, 38, 56, 150))
        g.setColorAt(0.44, QColor(11, 22, 36, 140))
        g.setColorAt(1.0, QColor(4, 9, 17, 120))
        p.fillRect(r, QBrush(g))

    def _rysuj_siatke(self, p, rzut, r):
        """Siatka pomiarowa na dnie doliny — linie zbiegają się w głębi sceny."""
        krok = 42.0
        zas_x, zas_y = 760.0, 900.0
        p.setBrush(Qt.BrushStyle.NoBrush)
        i = -int(zas_x / krok)
        while i * krok <= zas_x:
            x = i * krok
            a = rzut.ekran(x, -zas_y * 0.45, 0.0)
            b = rzut.ekran(x, zas_y, 0.0)
            p.setPen(_pioro_gradientowe(a, b, st.z_alfa(st.CYJAN, 30),
                                        st.z_alfa(st.CYJAN, 4), 1.0))
            p.drawLine(a, b)
            i += 1
        j = -int(zas_y * 0.45 / krok)
        while j * krok <= zas_y:
            y = j * krok
            gleb = rzut.glebokosc(0.0, y, 0.0)
            a = rzut.ekran(-zas_x, y, 0.0)
            b = rzut.ekran(zas_x, y, 0.0)
            p.setPen(QPen(st.z_alfa(st.CYJAN, int(26 * (1.0 - rzut.mgla(gleb)) + 4)), 1.0))
            p.drawLine(a, b)
            j += 1

    def _rysuj_mgle(self, p, rzut, r):
        """Mgła odległości: w głębi sceny mniejszy kontrast i jaśniejsze tło."""
        # gdzie na ekranie leży horyzont — od niego idzie cała skala mgły
        y_gora = rzut.ekran(0.0, 900.0, 0.0).y()
        y_dol = rzut.ekran(0.0, -POLE_SWIATA_Y * 0.62, 0.0).y()
        g = QLinearGradient(QPointF(r.x(), y_gora), QPointF(r.x(), y_dol))
        g.setColorAt(0.0, st.z_alfa(BARWA_MGLY, 34))
        g.setColorAt(0.30, st.z_alfa(BARWA_MGLY, 14))
        g.setColorAt(0.72, st.z_alfa(BARWA_MGLY, 3))
        g.setColorAt(1.0, st.z_alfa(BARWA_MGLY, 0))
        p.fillRect(r, QBrush(g))
        # światło wpadające z tej strony, z której pada na teren
        lx, ly = rzut.swiatlo_ekran
        rg = QRadialGradient(QPointF(r.center().x() + lx * r.width() * 0.55,
                                     r.center().y() + ly * r.height() * 0.75),
                             max(r.width(), r.height()) * 0.95)
        rg.setColorAt(0.0, st.z_alfa(BARWA_MGLY, 13))
        rg.setColorAt(1.0, st.z_alfa(BARWA_MGLY, 0))
        p.fillRect(r, QBrush(rg))

    # — rzeka —
    def _zbuduj_rzeke(self):
        """Rzeka wijąca się doliną z północy na południowy wschód."""
        los = _Losowy(20260902)
        sterowe = []
        x = -POLE_SWIATA_X * 1.24
        for i in range(9):
            y = POLE_SWIATA_Y * 0.90 - i * (POLE_SWIATA_Y * 1.70 / 8.0)
            x += los.zakres(POLE_SWIATA_X * 0.015, POLE_SWIATA_X * 0.20)
            sterowe.append((x + los.zakres(-14.0, 14.0), y))
        return _gladko_2d(sterowe, na_odcinek=7)

    def _rysuj_rzeke(self, p, rzut):
        """Koryto ciemniejsze od gruntu, jaśniejszy brzeg i pasek połysku."""
        szer = 15.0
        p.setPen(Qt.PenStyle.NoPen)
        # brzeg: szersza, jaśniejsza wstęga pod korytem
        brzeg = _wstega(rzut, self._rzeka, szer * 1.66, self._wysokosc)
        p.fillPath(brzeg, QColor(104, 146, 172, 62))
        koryto = _wstega(rzut, self._rzeka, szer, self._wysokosc)
        p.fillPath(koryto, QColor(2, 8, 17, 235))
        p.fillPath(koryto, QColor(9, 42, 66, 150))
        # połysk: wąski pas przesunięty ku światłu
        bok = [(x + SWIATLO_3D[0] * 3.2, y + SWIATLO_3D[1] * 3.2) for (x, y) in self._rzeka]
        polysk = _wstega(rzut, bok, szer * 0.20, self._wysokosc, wznios=0.4)
        p.fillPath(polysk, st.z_alfa(st.MIETA, 90))

    # — drogi —
    def _zbuduj_siec(self):
        """Sieć dróg: graf Gabriela plus dwaj najbliżsi sąsiedzi każdego miasta.

        Graf Gabriela daje układ podobny do prawdziwej sieci — bez krzyżujących
        się skrótów — a najbliżsi sąsiedzi pilnują, żeby nic nie zostało bez
        dojazdu. Trasa dnia biegnie potem wyłącznie po tych drogach.
        """
        nazwy = list(dn.MIASTA.keys())
        poz = {n: _swiat_miasta(*dn.MIASTA[n]) for n in nazwy}
        pary = set()
        for i, a in enumerate(nazwy):
            ax, ay = poz[a]
            sasiedzi = sorted((n for n in nazwy if n != a),
                              key=lambda n: (poz[n][0] - ax) ** 2 + (poz[n][1] - ay) ** 2)
            for b in sasiedzi[:2]:
                pary.add(tuple(sorted((a, b))))
            for b in nazwy[i + 1:]:
                bx, by = poz[b]
                sx, sy = (ax + bx) * 0.5, (ay + by) * 0.5
                r2 = ((ax - bx) ** 2 + (ay - by) ** 2) * 0.25
                if all((poz[c][0] - sx) ** 2 + (poz[c][1] - sy) ** 2 >= r2 - 1e-6
                       for c in nazwy if c != a and c != b):
                    pary.add(tuple(sorted((a, b))))
        return sorted(pary)

    def _ksztalty_drog(self):
        """Każda droga jako łagodnie wygięta łamana w świecie — nie sucha prosta."""
        ksztalty = {}
        for a, b in self._siec:
            ax, ay = self._miasta[a]
            bx, by = self._miasta[b]
            dx, dy = bx - ax, by - ay
            dl = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / dl, dx / dl
            w1 = (_hasz(a, b, 11) - 0.5) * 0.17 * dl
            w2 = (_hasz(a, b, 12) - 0.5) * 0.17 * dl
            sterowe = [(ax, ay),
                       (ax + dx * 0.34 + nx * w1, ay + dy * 0.34 + ny * w1),
                       (ax + dx * 0.67 + nx * w2, ay + dy * 0.67 + ny * w2),
                       (bx, by)]
            ksztalty[(a, b)] = _gladko_2d(sterowe, na_odcinek=4)
        return ksztalty

    def _zbuduj_graf(self):
        """Listy sąsiedztwa z długościami — do szukania trasy po drogach."""
        graf = {n: [] for n in dn.MIASTA}
        for (a, b), punkty in self._drogi.items():
            dl = sum(math.hypot(punkty[i][0] - punkty[i - 1][0],
                                punkty[i][1] - punkty[i - 1][1])
                     for i in range(1, len(punkty)))
            graf[a].append((b, dl))
            graf[b].append((a, dl))
        return graf

    def _droga_miedzy(self, a, b):
        """Łamana drogi a→b we właściwym kierunku; None, gdy takiej drogi nie ma."""
        punkty = self._drogi.get((a, b))
        if punkty is not None:
            return punkty
        punkty = self._drogi.get((b, a))
        if punkty is not None:
            return list(reversed(punkty))
        return None

    def _po_drogach(self, a, b):
        """Najkrótsza droga z a do b po sieci — algorytm Dijkstry na 18 węzłach."""
        if a == b:
            return [a]
        odl = {a: 0.0}
        skad = {}
        do_zrobienia = {a}
        gotowe = set()
        while do_zrobienia:
            biezacy = min(do_zrobienia, key=lambda n: odl[n])
            do_zrobienia.discard(biezacy)
            gotowe.add(biezacy)
            if biezacy == b:
                break
            for (sasiad, dl) in self._sasiedzi.get(biezacy, ()):
                if sasiad in gotowe:
                    continue
                nowa = odl[biezacy] + dl
                if sasiad not in odl or nowa < odl[sasiad]:
                    odl[sasiad] = nowa
                    skad[sasiad] = biezacy
                    do_zrobienia.add(sasiad)
        if b not in odl:
            return [a, b]
        sciezka = [b]
        while sciezka[-1] != a:
            sciezka.append(skad[sciezka[-1]])
        sciezka.reverse()
        # zbyt wielkie objazdy wyglądają na pomyłkę — wtedy jedziemy wprost
        prosto = math.hypot(self._miasta[b][0] - self._miasta[a][0],
                            self._miasta[b][1] - self._miasta[a][1])
        if odl[b] > prosto * 1.9:
            return [a, b]
        return sciezka

    def _rysuj_drogi(self, p, rzut, odcinki):
        """Drogi jako jaśniejsze pasma leżące na terenie."""
        odcinki = list(odcinki)
        if not odcinki:
            return
        p.setPen(Qt.PenStyle.NoPen)
        # od najdalszej do najbliższej, żeby bliższe kładły się na dalszych
        odcinki.sort(key=lambda pk: -rzut.glebokosc(
            sum(x for x, _ in pk) / len(pk), sum(y for _, y in pk) / len(pk), 0.0))
        for punkty in odcinki:
            sr_y = sum(y for _, y in punkty) / len(punkty)
            mgla = rzut.mgla(rzut.glebokosc(0.0, sr_y, 0.0))
            pas = _wstega(rzut, punkty, 9.0, self._wysokosc, wznios=0.25)
            p.fillPath(pas, st.z_alfa(rzut.zamgl(QColor(132, 160, 184), mgla),
                                      int(38 - 18 * mgla)))
            rdzen = _wstega(rzut, punkty, 3.2, self._wysokosc, wznios=0.5)
            p.fillPath(rdzen, st.z_alfa(rzut.zamgl(QColor(186, 212, 230), mgla),
                                        int(44 - 21 * mgla)))

    # — zabudowa —
    def _zbuduj_zabudowe(self):
        """Ciasne skupiska brył przy miastach: bok, głębokość, wysokość, położenie.

        Wszystko z hasza nazwy miasta, więc każde miasto ma swoją, stałą
        sylwetkę. Skupisko to jedna do trzech niskich brył tuż przy punkcie
        miasta (przy bazie pięć) —
        region ma wyglądać na rozrzucone miasteczka, a nie na jedną
        metropolię, więc między nimi zostaje otwarty teren: pola, rzeka
        i drogi. Baza jest większa od pozostałych, ale i tak niższa od słupa
        światła, żeby nie zasłaniała trasy.
        """
        bryly = []
        for nazwa in dn.MIASTA:
            cx, cy = self._miasta[nazwa]
            baza = (nazwa == dn.BAZA)
            ile = 5 if baza else 1 + int(_hasz(nazwa, 0) * 2.50)
            promien = 13.0 if baza else 7.5
            for i in range(ile):
                kat = 2.0 * math.pi * (i / float(ile) + 0.16 * _hasz(nazwa, i, 1))
                odl = promien * (0.22 + 0.78 * _hasz(nazwa, i, 2))
                bx = cx + math.cos(kat) * odl
                by = cy + math.sin(kat) * odl * 0.82
                niski = _hasz(nazwa, i, 8) > 0.45         # hala zamiast kamienicy
                bok = (4.0 + 3.0 * _hasz(nazwa, i, 3)) if niski else 2.6 + 2.1 * _hasz(nazwa, i, 3)
                glab = (3.5 + 2.6 * _hasz(nazwa, i, 4)) if niski else 2.6 + 2.1 * _hasz(nazwa, i, 4)
                # najwyższa bryła miasteczka ma być wyraźnie niższa od słupa
                # przystanku (24 jednostki), żeby trasa nie ginęła za dachami
                wys = (4.0 + 5.0 * _hasz(nazwa, i, 5)) if niski else \
                    7.0 + 10.0 * _hasz(nazwa, i, 5) ** 1.15
                if baza:
                    bok *= 1.45
                    glab *= 1.45
                    wys = 9.0 + 15.0 * _hasz(nazwa, i, 6) ** 1.15
                bryly.append({"x": bx, "y": by, "bok": bok, "glab": glab,
                              "wys": wys, "miasto": nazwa,
                              "okna": _hasz(nazwa, i, 7)})
        return bryly

    def _cien_bryly(self, rzut, b):
        """Długi cień bryły położony na teren, wzdłuż kierunku światła."""
        x, y, bok, glab, wys = b["x"], b["y"], b["bok"], b["glab"], b["wys"]
        px = wys * rzut.cien_x
        py = wys * rzut.cien_y
        rogi = [(x - bok, y - glab), (x + bok, y - glab),
                (x + bok, y + glab), (x - bok, y + glab)]
        pkt = rogi + [(rx + px, ry + py) for (rx, ry) in rogi]
        return _wypukla_otoczka(pkt)

    def _rysuj_cienie_bryl(self, p, rzut):
        """Wszystkie cienie zabudowy naraz — leżą na gruncie, pod bryłami."""
        p.setPen(Qt.PenStyle.NoPen)
        for b in self._zabudowa:
            gleb = rzut.glebokosc(b["x"], b["y"], 0.0)
            if gleb < 12.0 or b["wys"] * rzut.k / gleb < 2.2:
                continue
            otoczka = self._cien_bryly(rzut, b)
            wiel = QPolygonF([rzut.ekran(x, y, self._wysokosc(x, y)) for (x, y) in otoczka])
            s = QPainterPath()
            s.addPolygon(wiel)
            p.fillPath(s, QColor(0, 0, 0, int(58 * (1.0 - rzut.mgla(gleb) * 0.75))))

    def _rysuj_zabudowe(self, p, rzut):
        """Bryły od najdalszej do najbliższej: ściana przednia, bok i dach."""
        widoczne = []
        for b in self._zabudowa:
            gleb = rzut.glebokosc(b["x"], b["y"] - b["glab"], 0.0)
            if gleb < 12.0:
                continue
            widoczne.append((gleb, b))
        widoczne.sort(key=lambda z: -z[0])
        # bliższa bryła zasłania dalszą, bo idziemy od tyłu sceny
        for gleb, b in widoczne:
            self._rysuj_bryle(p, rzut, b, gleb)

    def _rysuj_bryle(self, p, rzut, b, gleb):
        x, y, bok, glab, wys = b["x"], b["y"], b["bok"], b["glab"], b["wys"]
        h = self._wysokosc(x, y)
        z0, z1 = h, h + wys
        skala = rzut.k / max(1.0, gleb)
        if wys * skala < 2.2:
            return
        mgla = rzut.mgla(gleb)

        # kamera stoi na południe i patrzy w dół: zawsze widać dach i ścianę
        # południową, a z boków ten, który jest odwrócony od osi kamery
        zach = x > rzut.oko[0]
        xb = x - bok if zach else x + bok
        e = rzut.ekran
        pd_l = e(x - bok, y - glab, z0)
        pd_p = e(x + bok, y - glab, z0)
        pg_l = e(x - bok, y - glab, z1)
        pg_p = e(x + bok, y - glab, z1)
        bd_t = e(xb, y + glab, z0)
        bg_t = e(xb, y + glab, z1)
        bd_p = e(xb, y - glab, z0)
        bg_p = e(xb, y - glab, z1)

        p.setPen(Qt.PenStyle.NoPen)
        # ściana boczna — ciemniejsza, odwrócona od światła
        bok_path = QPainterPath()
        bok_path.addPolygon(QPolygonF([bd_t, bd_p, bg_p, bg_t]))
        p.fillPath(bok_path, st.z_alfa(rzut.zamgl(BARWA_BOKU, mgla), 255))

        # ściana przednia — główna, z pasami okien
        przod = QPainterPath()
        przod.addPolygon(QPolygonF([pd_l, pd_p, pg_p, pg_l]))
        g = QLinearGradient(pg_l, pd_p)
        odcien = 100 + int(26 * (b["okna"] - 0.5))     # drobna różnica barwy
        sciana = BARWA_SCIANY.lighter(odcien)
        jasna = rzut.zamgl(sciana.lighter(126), mgla)
        ciemna = rzut.zamgl(sciana.darker(122), mgla)
        g.setColorAt(0.0, jasna)
        g.setColorAt(1.0, ciemna)
        p.fillPath(przod, QBrush(g))

        # dach — najjaśniejszy, bo zbiera światło z góry
        dach = QPainterPath()
        dach.addPolygon(QPolygonF([e(x - bok, y - glab, z1), e(x + bok, y - glab, z1),
                                   e(x + bok, y + glab, z1), e(x - bok, y + glab, z1)]))
        p.fillPath(dach, st.z_alfa(rzut.zamgl(BARWA_DACHU.lighter(odcien), mgla), 255))

        # okna: poziome pasy na ścianie przedniej, kilka rozświetlonych
        wys_pix = abs(pd_l.y() - pg_l.y())
        if wys_pix > 16.0:
            pieter = max(2, min(7, int(wys_pix / 7.0)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for q in range(pieter):
                t = (q + 0.55) / float(pieter)
                a = QPointF(pd_l.x() + (pg_l.x() - pd_l.x()) * t,
                            pd_l.y() + (pg_l.y() - pd_l.y()) * t)
                c = QPointF(pd_p.x() + (pg_p.x() - pd_p.x()) * t,
                            pd_p.y() + (pg_p.y() - pd_p.y()) * t)
                wsp = 0.14
                a2 = QPointF(a.x() + (c.x() - a.x()) * wsp, a.y() + (c.y() - a.y()) * wsp)
                c2 = QPointF(c.x() - (c.x() - a.x()) * wsp, c.y() - (c.y() - a.y()) * wsp)
                swieci = _hasz(b["miasto"], int(b["okna"] * 1000), q) > 0.83
                barwa = (st.z_alfa(st.BURSZTYN, int(150 * (1.0 - mgla)))
                         if swieci else QColor(120, 156, 184, int(52 * (1.0 - mgla))))
                p.setPen(QPen(barwa, max(0.8, wys_pix / (pieter * 5.0))))
                p.drawLine(a2, c2)
            p.setPen(Qt.PenStyle.NoPen)

        # krawędź dachu od strony światła — cienki rozbłysk, który domyka bryłę
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(rzut.zamgl(st.MIETA, mgla), int(78 * (1.0 - mgla))), 1.0))
        p.drawLine(pg_l, pg_p)
        p.setPen(Qt.PenStyle.NoPen)

    # — podziałka —
    def _rysuj_podzialke(self, p, rzut, r):
        """Podziałka odległości położona na gruncie — mierzy świat, nie ekran."""
        km = 50.0
        dlug = km / KM_NA_JEDNOSTKE
        # punkt gruntu pod lewym dolnym rogiem — podziałka mierzy świat, nie ekran
        x0, y = rzut.na_grunt(r.x() + r.width() * 0.05, r.bottom() - r.height() * 0.055)
        a, _ = rzut.rzutuj(x0, y, 0.0)
        b, _ = rzut.rzutuj(x0 + dlug, y, 0.0)
        if b.x() - a.x() < 40.0 or not r.contains(a) or not r.contains(b):
            return
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(st.TEKST_3, 80), 1.0))
        p.drawLine(a, b)
        for u in (0.0, 0.5, 1.0):
            pt = rzut.ekran(x0 + dlug * u, y, 0.0)
            gora = rzut.ekran(x0 + dlug * u, y, 3.4)
            p.drawLine(pt, gora)
        _napis(p, a.x(), a.y() - 8.0, "0", st.z_alfa(st.TEKST_3, 115), 9.0, 500, mono=True)
        _napis(p, b.x(), b.y() - 8.0, "50 km", st.z_alfa(st.TEKST_3, 115), 9.0, 500,
               mono=True, prawy=True)

    # — pomocnicze —
    def _punkt(self, nazwa):
        """Miasto na gruncie, już po rzucie — po tych punktach liczymy trafienia."""
        x, y = self._miasta.get(nazwa, (0.0, 0.0))
        return self.rzut().ekran(x, y, self._wysokosc(x, y))

    def _kolor_trasy(self):
        return st.ZIELEN if self._stan == "sukces" else st.CYJAN

    def _czynny(self):
        """Dzień z prawdziwą trasą: baza, co najmniej jeden przystanek i powrót."""
        d = self._dzien
        return d is not None and not d.wolny and len(d.trasa) >= 3

    def _grubosc(self):
        return min(self.width(), self.height()) / 620.0

    # — rysowanie —
    def paintEvent(self, _zdarzenie):
        """Klatka składa się z dwóch gotowych warstw i tego, co się rusza."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect())
        geo = self._geometria() if self._czynny() else None
        dol, gora = self._warstwy(geo)

        p.drawPixmap(0, 0, dol)                        # a) scena 3D i trasa
        if geo is not None:
            self._rysuj_powrot(p, geo)                 # b) kreskowany powrót
            self._rysuj_blask(p, geo)                  # c) płynący blask
        p.drawPixmap(0, 0, gora)                       # d) słupy i tabliczki
        if geo is not None:
            self._rysuj_puls_bazy(p)                   # e) oddech bazy
            self._rysuj_nitke(p, geo)                  # f) nitka do kartki
        self._rysuj_cien_kartki(p)                     # g) kartka kładzie cień

        st.winieta(p, r, 62)                           # h) wykończenie
        st.ziarno(p, r, 10)
        p.end()

    # — warstwy trzymane w pixmapach —
    def _nowa_pixmapa(self):
        dpr = self.devicePixelRatioF()
        pix = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        return pix

    def _warstwy(self, geo):
        """Dwie pixmapy: pod blaskiem i nad nim. Liczone raz na układ."""
        klucz = (self.width(), self.height(), round(self.devicePixelRatioF(), 3),
                 self._geo_klucz, self._stan)
        if self._warstwy_klucz == klucz and self._dol is not None:
            return self._dol, self._gora

        rzut = self.rzut()
        cel = QRectF(self.rect())
        dol = self._nowa_pixmapa()
        q = QPainter(dol)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        grunt = self._pixmapa_gruntu()
        q.drawPixmap(cel, grunt, QRectF(grunt.rect()))
        if geo is not None:
            self._rysuj_drogi(q, rzut, geo["dodatkowe"])   # dojazdy spoza sieci
            self._rysuj_cien_trasy(q, geo)                 # cień trasy leży na gruncie
        bryly = self._pixmapa_bryl()                       # ...więc bryły idą po nim
        q.drawPixmap(cel, bryly, QRectF(bryly.rect()))
        if geo is not None:
            self._rysuj_trase(q, geo)
        q.end()

        gora = self._nowa_pixmapa()
        q = QPainter(gora)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self._rysuj_slupy(q, rzut, geo)
        if geo is not None:
            self._rysuj_podpisy(q, geo)
        q.end()

        self._dol, self._gora, self._warstwy_klucz = dol, gora, klucz
        return dol, gora

    def _statyka(self):
        """Dwie pixmapy sceny bez trasy: grunt z terenem i osobno bryły zabudowy.

        Rozdział jest potrzebny, bo cień trasy leży na gruncie i musi trafić
        pod bryły, a sama trasa świeci nad nimi. Obie zależą wyłącznie od
        rozmiaru widżetu, więc przy zmianie dnia nic się tu nie przelicza.
        W trakcie ciągnięcia okna zwracamy stare pixmapy i pozwalamy je
        rozciągnąć — przeliczenie czeka na koniec ruchu.
        """
        dpr = self.devicePixelRatioF()
        klucz = (self.width(), self.height(), round(dpr, 3))
        if self._statyk is not None and (self._statyk_klucz == klucz
                                         or self._zegar_terenu.isActive()):
            return self._statyk
        r = QRectF(self.rect())
        rzut = self.rzut()
        if self._wzgorza is None:
            self._wzgorza = self._zbuduj_wzgorza(rzut)

        grunt = self._nowa_pixmapa()
        q = QPainter(grunt)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        st.tlo_sceny(q, r)                    # niebo i głębia
        self._rysuj_grunt(q, rzut, r)         # dno doliny
        self._rysuj_siatke(q, rzut, r)        # linie zbiegające się w głębi
        self._rysuj_teren(q, rzut)            # bryły wzgórz, od dali do widza
        self._rysuj_rzeke(q, rzut)
        self._rysuj_drogi(q, rzut, self._drogi.values())
        self._rysuj_cienie_bryl(q, rzut)      # cienie leżą na gruncie
        q.end()

        bryly = self._nowa_pixmapa()
        q = QPainter(bryly)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self._rysuj_zabudowe(q, rzut)
        self._rysuj_mgle(q, rzut, r)          # mgła przykrywa też dalekie bryły
        self._rysuj_podzialke(q, rzut, r)
        q.end()

        self._statyk = (grunt, bryly)
        self._statyk_klucz = klucz
        return self._statyk

    def _pixmapa_gruntu(self):
        return self._statyka()[0]

    def _pixmapa_bryl(self):
        return self._statyka()[1]

    # — geometria trasy i podpisów (liczona raz na układ) —
    def _geometria(self):
        dzien = self._dzien
        trasa = tuple(dzien.trasa)
        kot = None
        if self._kotwica is not None:
            kot = (round(self._kotwica.x(), 1), round(self._kotwica.y(), 1))
        klucz = (self.width(), self.height(), trasa, self._stan, kot)
        if self._geo_klucz == klucz and self._geo is not None:
            return self._geo

        rzut = self.rzut()
        if self._wzgorza is None:
            self._wzgorza = self._zbuduj_wzgorza(rzut)

        # a) trasa dnia poprowadzona po drogach
        odcinki = []
        dodatkowe = []
        for i in range(len(trasa) - 1):
            weze = self._po_drogach(trasa[i], trasa[i + 1])
            punkty = []
            for j in range(len(weze) - 1):
                kawalek = self._droga_miedzy(weze[j], weze[j + 1])
                if kawalek is None:                   # brak drogi: kładziemy nową
                    kawalek = _gladko_2d([self._miasta[weze[j]],
                                          self._miasta[weze[j + 1]]], na_odcinek=4)
                    dodatkowe.append(kawalek)
                punkty.extend(kawalek if not punkty else kawalek[1:])
            odcinki.append(punkty or [self._miasta[trasa[i]], self._miasta[trasa[i + 1]]])

        swiat_glowna = []
        for punkty in odcinki[:-1]:
            swiat_glowna.extend(punkty if not swiat_glowna else punkty[1:])
        swiat_powrot = odcinki[-1]

        # b) rzut: trasa unosi się nad gruntem, jej cień leży na gruncie.
        #    skala to liczba pikseli na jednostkę świata — po niej dobieramy
        #    grubości, więc linia zwęża się w głębi sceny
        def na_ekran(punkty, wznios):
            pkt, ska = [], []
            for (x, y) in punkty:
                z = self._wysokosc(x, y) + wznios
                p, s = rzut.rzutuj(x, y, z)
                pkt.append(p)
                ska.append(s)
            return pkt, ska

        pkt_gl, ska_gl = na_ekran(swiat_glowna, WZNIOS_TRASY)
        pkt_pw, ska_pw = na_ekran(swiat_powrot, WZNIOS_TRASY)
        cien_gl, ska_cgl = na_ekran(swiat_glowna, 0.0)
        cien_pw, ska_cpw = na_ekran(swiat_powrot, 0.0)

        glowna = _lamana(pkt_gl)
        powrot = _lamana(pkt_pw)
        probki_swiat = _rowno(swiat_glowna, 150)
        probki, skale_probek = na_ekran(probki_swiat, WZNIOS_TRASY)

        # c) słupy przystanków: im więcej wizyt, tym wyższy słup światła
        ile_wizyt = {}
        for n in trasa[1:-1]:
            ile_wizyt[n] = ile_wizyt.get(n, 0) + 1
        slupy = []
        for nazwa in [dn.BAZA] + [n for n in trasa[1:-1]]:
            if any(s["nazwa"] == nazwa for s in slupy):
                continue
            x, y = self._miasta[nazwa]
            h = self._wysokosc(x, y)
            baza = (nazwa == dn.BAZA)
            wysokosc = (62.0 if baza else
                        24.0 + 16.0 * (ile_wizyt.get(nazwa, 1) - 1)
                        + 9.0 * _hasz(nazwa, 31))
            dol, skala = rzut.rzutuj(x, y, h)
            gora, skala_g = rzut.rzutuj(x, y, h + wysokosc)
            slupy.append({"nazwa": nazwa, "dol": dol, "gora": gora,
                          "skala": skala, "skala_g": skala_g, "baza": baza,
                          "wizyty": ile_wizyt.get(nazwa, 1)})

        nitka = self._sciezka_nitki()
        etykiety = self._ulozenie_podpisow(slupy, probki, pkt_pw, nitka)
        self._geo = {"glowna": glowna, "powrot": powrot, "probki": probki,
                     "skale": skale_probek, "cien_glowna": cien_gl,
                     "cien_powrot": cien_pw, "ska_cglowna": ska_cgl,
                     "ska_cpowrot": ska_cpw, "pkt_glowna": pkt_gl,
                     "ska_glowna": ska_gl, "pkt_powrot": pkt_pw, "ska_powrot": ska_pw,
                     "slupy": slupy, "nitka": nitka, "etykiety": etykiety,
                     "trasa": trasa, "dodatkowe": dodatkowe}
        self._geo_klucz = klucz
        return self._geo

    def _rysuj_cien_trasy(self, p, geo):
        """Trasa unosi się nad terenem, więc rzuca na niego cień prosto w dół."""
        czern = QColor(0, 0, 0)
        warstwy = ((5.4, 52, 4), (3.0, 66, 2), (1.5, 78, 1))
        _poswiata_zmienna(p, geo["cien_glowna"], geo["ska_cglowna"], czern, warstwy)
        _poswiata_zmienna(p, geo["cien_powrot"], geo["ska_cpowrot"], czern, warstwy)

    def _rysuj_trase(self, p, geo):
        """Świecąca linia leżąca nad terenem, węższa w głębi sceny."""
        kolor = self._kolor_trasy()
        _poswiata_zmienna(p, geo["pkt_glowna"], geo["ska_glowna"], kolor,
                          ((13.0, 20, 5), (7.2, 42, 3), (3.6, 118, 2), (1.7, 226, 1)))
        _poswiata_zmienna(p, geo["pkt_glowna"], geo["ska_glowna"],
                          QColor(232, 255, 255), ((0.60, 185, 1),))

    def _rysuj_powrot(self, p, geo):
        """Powrót do bazy: kreski wolno płyną w stronę domu."""
        k = self._grubosc()
        ska = geo["ska_powrot"]
        sr = sum(ska) / max(1, len(ska))
        przesun = -self._faza * 34.0 * k if self._anim else 0.0
        _kreskowana(p, geo["powrot"], st.ZIELEN,
                    warstwy=((7.2 * sr, 30), (3.4 * sr, 76), (1.35 * sr, 235)),
                    kreska=11.0 * k, przerwa=8.0 * k, przesuniecie=przesun)

    def _rysuj_blask(self, p, geo):
        """Powoli płynący jaśniejszy odcinek wzdłuż trasy."""
        probki = geo["probki"]
        skale = geo["skale"]
        if len(probki) < 3:
            return
        kolor = self._kolor_trasy()
        n = len(probki) - 1
        dlugosc = 0.19                       # jaka część trasy świeci
        ile = 24
        # czoło wchodzi na trasę i schodzi z niej — bez skoku na zapętleniu
        czolo = -dlugosc + self._faza * (1.0 + dlugosc)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(ile):
            t1 = czolo - dlugosc * (i / float(ile))
            t0 = czolo - dlugosc * ((i + 1) / float(ile))
            if t1 <= 0.0 or t0 >= 1.0:
                continue
            i0 = max(0, min(n, int(round(max(0.0, t0) * n))))
            i1 = max(0, min(n, int(round(min(1.0, t1) * n))))
            a, b = probki[i0], probki[i1]
            s = (skale[i0] + skale[i1]) * 0.5
            jas = (1.0 - i / float(ile)) ** 2.0
            for szer, sila, barwa in ((10.5 * s, 34, kolor),
                                      (4.8 * s, 74, kolor),
                                      (2.3 * s, 112, kolor),
                                      (1.0 * s, 245, QColor(240, 255, 255))):
                pen = QPen(st.z_alfa(barwa, sila * jas), max(0.8, szer))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.drawLine(a, b)
        # czubek blasku
        if 0.0 <= czolo <= 1.0:
            ic = max(0, min(n, int(round(czolo * n))))
            glowa = probki[ic]
            st.punkt_swiatla(p, glowa, 22.0 * skale[ic], kolor, 62)
            st.punkt_swiatla(p, glowa, 8.6 * skale[ic], QColor(235, 255, 255), 96)

    # — słupy przystanków —
    def _rysuj_slupy(self, p, rzut, geo):
        """Pionowe słupy światła nad miastami — wyższe tam, gdzie więcej wizyt."""
        kolor = self._kolor_trasy()
        if geo is None:
            # sam teren: baza zaznaczona dyskretnym słupem
            x, y = self._miasta[dn.BAZA]
            h = self._wysokosc(x, y)
            dol, ska = rzut.rzutuj(x, y, h)
            gora, ska_g = rzut.rzutuj(x, y, h + 40.0)
            self._pierscien(p, dol, ska * 3.4, st.ZIELEN, 0.55)
            self._slup(p, dol, gora, ska_g, st.ZIELEN, 0.55)
            return
        # od najdalszego do najbliższego
        for s in sorted(geo["slupy"], key=lambda z: z["dol"].y()):
            barwa = st.ZIELEN if s["baza"] else kolor
            waga = 1.0 if s["baza"] else 0.82
            self._pierscien(p, s["dol"], s["skala"] * (4.4 if s["baza"] else 3.2),
                            barwa, waga)
            self._slup(p, s["dol"], s["gora"], s["skala_g"], barwa, waga)

    def _slup(self, p, dol, gora, skala, kolor, waga):
        """Snop światła od gruntu w górę, zakończony jarzącym się punktem."""
        p.setBrush(Qt.BrushStyle.NoBrush)
        for szer, alfa in ((8.4, 26), (3.6, 66), (1.25, 190)):
            g = QLinearGradient(dol, gora)
            g.setColorAt(0.0, st.z_alfa(kolor, int(alfa * 0.35 * waga)))
            g.setColorAt(0.45, st.z_alfa(kolor, int(alfa * waga)))
            g.setColorAt(1.0, st.z_alfa(kolor, int(alfa * 0.9 * waga)))
            pen = QPen(QBrush(g), max(0.8, szer * skala))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(dol, gora)
        st.punkt_swiatla(p, gora, max(5.0, 16.0 * skala), kolor, int(96 * waga))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(st.z_alfa(QColor(238, 255, 255), int(245 * waga))))
        r = max(1.6, 2.1 * skala)
        p.drawEllipse(gora, r, r)

    def _pierscien(self, p, dol, r, kolor, waga):
        """Ślad przystanku na gruncie — spłaszczona elipsa, bo teren jest pochylony."""
        r = max(3.0, r)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(4, 12, 21, 200)))
        p.drawEllipse(dol, r, r * 0.56)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(kolor, int(215 * waga)), max(1.0, r * 0.26)))
        p.drawEllipse(dol, r, r * 0.56)
        p.setPen(QPen(st.z_alfa(kolor, int(60 * waga)), 1.0))
        p.drawEllipse(dol, r * 1.85, r * 1.85 * 0.56)

    def _rysuj_puls_bazy(self, p):
        """Wolny oddech halo bazy — jedyny ruch poza blaskiem trasy."""
        puls = 0.5 + 0.5 * math.sin(self._faza * 2.0 * math.pi)
        x, y = self._miasta[dn.BAZA]
        rzut = self.rzut()
        dol, ska = rzut.rzutuj(x, y, self._wysokosc(x, y))
        r = max(3.4, ska * 4.4)
        st.punkt_swiatla(p, dol, r * (6.0 + 1.6 * puls), st.ZIELEN, int(26 + 26 * puls))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(st.ZIELEN, int(58 - 34 * puls)), 1.2))
        rr = r * (2.6 + 1.6 * puls)
        p.drawEllipse(dol, rr, rr * 0.56)

    # — tabliczki z nazwami —
    def _rozmiary_podpisow(self):
        """Wielkość podpisów rośnie z oknem, ale wolniej niż ono samo."""
        k = max(0.55, min(2.0, self._grubosc())) ** 0.45
        return max(10.5, min(15.0, 11.5 * k)), max(12.0, min(18.0, 13.5 * k))

    # osiem stron świata wokół szczytu słupa; góra i skosy przed bokami,
    # bo tam tabliczka najrzadziej wchodzi na trasę
    KIERUNKI_PODPISU = ((0.0, -1.0), (0.8, -0.8), (-0.8, -0.8), (1.0, -0.15),
                        (-1.0, -0.15), (0.7, 0.7), (-0.7, 0.7), (0.0, 1.0))
    LUZY_PODPISU = (9.0, 20.0, 34.0, 52.0)

    def _ulozenie_podpisow(self, slupy, probki, pkt_powrot, nitka):
        """Tabliczki rozsuwane wokół swoich punktów — raz na układ, nie co klatkę.

        Każda szuka miejsca w ośmiu kierunkach od szczytu swojego słupa, zaczynając
        od najkrótszego odsunięcia. Im dalej od miasta i im bardziej w bok, tym
        droższe miejsce, więc tabliczka odchodzi od punktu dopiero wtedy, gdy
        inaczej weszłaby na sąsiadkę albo na trasę.
        """
        rozm_z, rozm_b = self._rozmiary_podpisow()
        f_zwykly = st.czcionka(rozm_z, 600)
        f_baza = st.czcionka(rozm_b, 700)
        m_zwykly = QFontMetricsF(f_zwykly)
        m_baza = QFontMetricsF(f_baza)

        przeszkody = list(probki[::4]) + list(pkt_powrot[::3])
        przeszkody += [s["gora"] for s in slupy]
        if nitka is not None and nitka.length() > 0:
            przeszkody += [nitka.pointAtPercent(i / 24.0) for i in range(25)]

        brzeg = QRectF(self.rect()).adjusted(10, 8, -10, -8)
        zajete, etykiety = [], []
        # baza pierwsza, potem przystanki od najdalszego — najdalsze mają
        # najmniej miejsca, więc wybierają wcześniej
        kolejnosc = sorted(slupy, key=lambda s: (not s["baza"], s["gora"].y()))
        for s in kolejnosc:
            baza = s["baza"]
            napis = f"{s['nazwa']} · start i powrót" if baza else s["nazwa"]
            m = m_baza if baza else m_zwykly
            szer = m.horizontalAdvance(napis) + (baza and 20 or 16)
            wys = m.height() + 8
            kotwica = s["gora"]

            najlepszy, najkoszt = None, None
            for luz in self.LUZY_PODPISU:
                for nr, (kx, ky) in enumerate(self.KIERUNKI_PODPISU):
                    # środek tabliczki odsunięty od kotwicy o pół jej rozmiaru
                    # plus luz — dzięki temu kreska zostaje krótka w każdą stronę
                    sx = kotwica.x() + kx * (szer * 0.5 + luz)
                    sy = kotwica.y() + ky * (wys * 0.5 + luz)
                    pole = QRectF(sx - szer * 0.5, sy - wys * 0.5, szer, wys)
                    koszt = luz * 1.4 + nr * 5.0
                    if not brzeg.contains(pole):
                        koszt += 900
                    for inne in zajete:
                        wspolne = pole.intersected(inne.adjusted(-7, -6, 7, 6))
                        if not wspolne.isEmpty():
                            koszt += 12.0 * wspolne.width() * wspolne.height()
                    for pt in przeszkody:
                        if pole.contains(pt):
                            koszt += 60
                    for s2 in slupy:                 # nie zasłaniamy cudzych słupów
                        if s2 is not s and pole.contains(s2["gora"]):
                            koszt += 120
                    if najkoszt is None or koszt < najkoszt:
                        najkoszt, najlepszy = koszt, pole
            zajete.append(najlepszy)
            rozmiar, waga = (rozm_b, 700) if baza else (rozm_z, 600)
            etykiety.append({"pole": najlepszy, "napis": napis, "rozmiar": rozmiar,
                             "waga": waga, "baza": baza, "kotwica": kotwica,
                             "powtorka": s["wizyty"] > 1})
        return etykiety

    def _rysuj_podpisy(self, p, geo):
        """Tabliczki zwrócone do widza: nie pochylają się razem z terenem."""
        kolor = self._kolor_trasy()
        for e in geo["etykiety"]:
            pole = e["pole"]
            barwa = st.ZIELEN if e["baza"] else kolor
            kotwica = e["kotwica"]
            # cienka kreska od tabliczki do jej punktu — celujemy w najbliższą
            # krawędź, więc przy tabliczce z boku kreska też zostaje krótka
            styk = QPointF(min(max(kotwica.x(), pole.left() + 6), pole.right() - 6),
                           min(max(kotwica.y(), pole.top() + 4), pole.bottom() - 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(_pioro_gradientowe(styk, kotwica, st.z_alfa(barwa, 150),
                                        st.z_alfa(barwa, 40), 1.1))
            p.drawLine(styk, kotwica)

            promien = pole.height() * 0.42
            s = QPainterPath()
            s.addRoundedRect(pole, promien, promien)
            _poduszka(p, pole.adjusted(4, 3, -4, -3), sila=120, warstw=4)
            p.fillPath(s, QColor(6, 17, 27, 232))
            p.setPen(QPen(st.z_alfa(barwa, 120 if not e["powtorka"] else 70), 1.1))
            p.drawPath(s)
            f = st.czcionka(e["rozmiar"], e["waga"])
            m = QFontMetricsF(f)
            x = pole.center().x() - m.horizontalAdvance(e["napis"]) * 0.5
            y = pole.center().y() + m.ascent() * 0.5 - m.descent() * 0.28
            _napis(p, x, y, e["napis"],
                   st.TEKST if not e["powtorka"] else st.z_alfa(st.TEKST_2, 225),
                   e["rozmiar"], e["waga"])

    # — nitka do kartki —
    def _sciezka_nitki(self):
        """Łuk od trasy do kartki; None, gdy kartka nie podała kotwicy."""
        dzien = self._dzien
        if self._kotwica is None or dzien is None or dzien.wolny:
            return None
        dokad = QPointF(self._kotwica)
        ostatni = dzien.przystanki[-1] if dzien.przystanki else dn.BAZA

        def dystans(nazwa):
            s = self._punkt(nazwa)
            return math.hypot(s.x() - dokad.x(), s.y() - dokad.y())

        najblizszy = min(dzien.przystanki or [dn.BAZA], key=dystans)
        if dystans(najblizszy) < dystans(ostatni) * 0.75:
            ostatni = najblizszy
        x, y = self._miasta[ostatni]
        skad = self.rzut().ekran(x, y, self._wysokosc(x, y) + 24.0)
        srodek = QPointF((skad.x() + dokad.x()) / 2.0, (skad.y() + dokad.y()) / 2.0)
        dx, dy = dokad.x() - skad.x(), dokad.y() - skad.y()
        dlug = max(1.0, math.hypot(dx, dy))
        ster = QPointF(srodek.x() - dy / dlug * dlug * 0.14,
                       srodek.y() + dx / dlug * dlug * 0.14)
        sciezka = QPainterPath(skad)
        sciezka.quadTo(ster, dokad)
        return sciezka

    def _rysuj_nitke(self, p, geo):
        sciezka = geo["nitka"]
        if sciezka is None:
            return
        dokad = sciezka.pointAtPercent(1.0)
        k = self._grubosc()
        kolor = self._kolor_trasy()
        przesun = -self._faza * 36.0 * k if self._anim else 0.0
        _kreskowana(p, sciezka, kolor,
                    warstwy=((14 * k, 16), (6 * k, 44), (2.0 * k, 175)),
                    kreska=10.0 * k, przerwa=7.5 * k, przesuniecie=przesun)
        st.punkt_swiatla(p, dokad, 18, kolor, 120)
        p.setPen(QPen(st.z_alfa(kolor, 230), 1.6))
        p.setBrush(QBrush(QColor(4, 12, 22, 200)))
        p.drawEllipse(dokad, 4.6, 4.6)

    # — cień kartki —
    def _pole_kartki(self):
        """Prostokąt kartki odtworzony z kotwicy, którą podaje okno główne."""
        if self._kotwica is None:
            return None
        lewy = self._kotwica.x() - 8.0
        gora = self._kotwica.y() - 26.0
        prawy = self.width() - 18.0
        if prawy - lewy < 60.0:
            return None
        return QRectF(lewy, gora, prawy - lewy, self.height() * 0.85)

    def _rysuj_cien_kartki(self, p):
        """Kartka unosi się nad terenem, więc kładzie na niego długi cień."""
        kar = self._pole_kartki()
        if kar is None:
            return
        lx, ly = self.rzut().swiatlo_ekran
        promien = max(6.0, kar.width() * 0.028)
        odl = max(14.0, min(self.width(), self.height()) * 0.055)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(6, 0, -1):
            rozlew = i * odl * 0.26
            a = int(62 * (1.0 - (i - 1) / 6.0) ** 2.0 / 6.0 * 2.2)
            if a <= 0:
                continue
            r = kar.adjusted(-rozlew, -rozlew, rozlew, rozlew)
            r.translate(-lx * odl, -ly * odl)
            s = QPainterPath()
            s.addRoundedRect(r, promien + rozlew, promien + rozlew)
            p.fillPath(s, QColor(0, 0, 0, a))

    # — obsługa myszy —
    def mousePressEvent(self, zdarzenie):
        """Trafienia liczone na współrzędnych PO rzucie — mapa jest pochylona."""
        poz = zdarzenie.position()
        prog = max(14.0, min(self.width(), self.height()) * 0.03)
        najblizsze, dyst = None, None
        for nazwa in dn.MIASTA:
            s = self._punkt(nazwa)
            d = math.hypot(s.x() - poz.x(), s.y() - poz.y())
            if d <= prog and (dyst is None or d < dyst):
                najblizsze, dyst = nazwa, d
        if najblizsze:
            self.klikniete_miasto.emit(najblizsze)
        super().mousePressEvent(zdarzenie)


# ── kartka delegacji ─────────────────────────────────────────────────
class KartkaDelegacji(QWidget):
    """Biała kartka polecenia wyjazdu, kładziona przez okno główne na mapie."""

    SZEROKOSC_WZORCOWA = 342.0     # szerokość kartki z projektu; od niej idzie skala
    WSUNIECIE = 14.0               # o tyle kartka wjeżdża przy zmianie dnia

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMinimumSize(230, 290)
        self._dzien = None
        self._numer = ""
        self._stan = "pusta"
        self._klucz = None
        self._pix = None                # gotowa kartka; wsuwanie tylko ją przesuwa
        self._pix_klucz = None
        self._anim = True
        self._wejscie = st.Plynnie(1.0, czas=380, krzywa="wyjscie", rodzic=self,
                                   przy_zmianie=self.update)

    # — interfejs publiczny —
    def ustaw_dzien(self, dzien):
        zmiana = self._klucz_dnia(dzien) != self._klucz
        self._klucz = self._klucz_dnia(dzien)
        self._dzien = dzien
        if dzien is not None and not self._numer:
            self._numer = f"{dzien.data.year}/{dzien.data.month:02d}/{dzien.data.day:02d}"
        if zmiana and self._anim and self.isVisible():
            self._wejscie.ustaw(0.0)
            self._wejscie.do(1.0)
        elif zmiana:
            self._wejscie.ustaw(1.0)
        self.update()

    def ustaw_numer(self, tekst):
        self._numer = str(tekst or "")
        self.update()

    def resizeEvent(self, zdarzenie):
        self._pix = None
        super().resizeEvent(zdarzenie)

    def ustaw_stan(self, nazwa):
        self._stan = nazwa if nazwa in ("pusta", "zwykla", "podpisana") else "zwykla"
        self.update()

    def ustaw_animacje(self, wlaczone):
        """Włącza albo gasi wsuwanie kartki. Wyłączona siada od razu na miejscu."""
        self._anim = bool(wlaczone)
        if not self._anim:
            self._wejscie.zatrzymaj()
            self._wejscie.ustaw(1.0)
        self.update()

    def zatrzymaj_animacje(self):
        self.ustaw_animacje(False)

    def animacje_wlaczone(self):
        return self._anim

    def sizeHint(self):
        return QSize(360, 470)

    def hideEvent(self, zdarzenie):
        self._wejscie.zatrzymaj()
        super().hideEvent(zdarzenie)

    def closeEvent(self, zdarzenie):
        self._wejscie.zatrzymaj()
        super().closeEvent(zdarzenie)

    def _klucz_dnia(self, dzien):
        if dzien is None:
            return None
        return (dzien.data, dzien.wolny, round(dzien.kwota, 2), tuple(dzien.przystanki))

    # — rysowanie —
    def _pole_kartki(self):
        r = QRectF(self.rect())
        margines = min(r.width(), r.height()) * 0.035
        kar = r.adjusted(margines, margines, -margines, -margines * 1.5)
        return kar, max(6.0, kar.width() * 0.028)

    def _pixmapa(self):
        """Gotowa kartka w pixmapie — wsuwanie jest wtedy samym przesunięciem."""
        dpr = self.devicePixelRatioF()
        klucz = (self.width(), self.height(), round(dpr, 3), self._klucz,
                 self._stan, self._numer)
        if self._pix is not None and self._pix_klucz == klucz:
            return self._pix
        pix = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        kar, promien = self._pole_kartki()
        pusta = (self._stan == "pusta") or self._dzien is None or self._dzien.wolny

        # cień wielowarstwowy: styk, korpus, daleka poświata
        _cien_miekki(p, kar, promien, przesun=2, rozmycie=6, sila=110, krok=2)
        _cien_miekki(p, kar, promien, przesun=9, rozmycie=21, sila=96, krok=3)
        _cien_miekki(p, kar, promien, przesun=24, rozmycie=48, sila=64, krok=6)

        sciezka = QPainterPath()
        sciezka.addRoundedRect(kar, promien, promien)
        self._rysuj_papier(p, kar, sciezka, promien, pusta)
        self._rysuj_tresc(p, kar, pusta)

        if self._stan == "podpisana" and not pusta:
            p.setPen(QPen(st.z_alfa(st.ZIELEN.darker(130), 190), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(sciezka)
            self._rysuj_pieczatke(p, kar)
        p.end()
        self._pix, self._pix_klucz = pix, klucz
        return pix

    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = max(0.0, min(1.0, self._wejscie.teraz()))
        if t < 0.999:
            p.setOpacity(max(0.0, min(1.0, t * 1.15)))
            p.translate((1.0 - t) * self.WSUNIECIE, (1.0 - t) * self.WSUNIECIE * 0.22)
        p.drawPixmap(0, 0, self._pixmapa())
        # rozjaśnienie przy wjeździe — kartka „zapala się” i gaśnie do normy
        if t < 0.999:
            kar, promien = self._pole_kartki()
            sciezka = QPainterPath()
            sciezka.addRoundedRect(kar, promien, promien)
            p.fillPath(sciezka, QColor(255, 255, 255, int(80 * (1.0 - t))))
        p.end()

    def _rysuj_papier(self, p, kar, sciezka, promien, pusta):
        """Cieplejsza biel, fakturа i światło padające z lewej góry."""
        g = QLinearGradient(kar.topLeft(), kar.bottomRight())
        if pusta:
            g.setColorAt(0.0, QColor("#EDEDEA"))
            g.setColorAt(0.55, QColor("#E5E6E4"))
            g.setColorAt(1.0, QColor("#D9DBDC"))
        else:
            g.setColorAt(0.0, QColor("#FFFDF9"))
            g.setColorAt(0.52, QColor("#FBFAF6"))
            g.setColorAt(1.0, QColor("#F1F0EB"))
        p.fillPath(sciezka, QBrush(g))

        p.save()
        p.setClipPath(sciezka)
        # światło z lewego górnego rogu i cień w przeciwległym
        zasieg = max(kar.width(), kar.height()) * 1.25
        rg = QRadialGradient(QPointF(kar.x() + kar.width() * 0.18,
                                     kar.y() + kar.height() * 0.10), zasieg)
        rg.setColorAt(0.0, QColor(255, 252, 244, 120))
        rg.setColorAt(1.0, QColor(255, 252, 244, 0))
        p.fillRect(kar, QBrush(rg))
        rg2 = QRadialGradient(QPointF(kar.right(), kar.bottom()), zasieg * 0.9)
        rg2.setColorAt(0.0, QColor(120, 116, 104, 30))
        rg2.setColorAt(1.0, QColor(120, 116, 104, 0))
        p.fillRect(kar, QBrush(rg2))
        # faktura papieru — drobne ziarno, ledwie widoczne
        st.ziarno(p, kar, sila=7, skala=1.4, ciemne=1.8)
        p.restore()

        # krawędź: górna zbiera światło, dolna siada w cieniu
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 190), 1.0))
        gora = QPainterPath()
        gora.addRoundedRect(kar.adjusted(0.6, 0.6, -0.6, -0.6), promien, promien)
        p.setClipRect(QRectF(kar.x(), kar.y(), kar.width(), kar.height() * 0.45))
        p.drawPath(gora)
        p.setClipping(False)
        p.setPen(QPen(QColor(28, 34, 48, 46), 1.0))
        p.drawPath(sciezka)

    def _rysuj_tresc(self, p, kar, pusta):
        s = kar.width() / self.SZEROKOSC_WZORCOWA          # skala względem projektu
        pad = kar.width() * 0.055
        lewy = kar.x() + pad
        prawy = kar.right() - pad
        cw = prawy - lewy

        szary = QColor("#8A94A6")
        ciemny = st.PAPIER_TEKST
        sredni = QColor("#2A3853")
        zielony = QColor("#0E9B74")
        kreska_mocna = QColor(16, 24, 40, 120)
        kreska_slaba = QColor(16, 24, 40, 28)

        y = kar.y() + 30 * s
        _napis(p, lewy, y, "Polecenie wyjazdu", ciemny, 17 * s, 700, naglowek=True)
        _napis(p, prawy, kar.y() + 22 * s, "PMT", sredni, 11 * s, 600, prawy=True)
        _napis(p, prawy, kar.y() + 36 * s, dn.BAZA, sredni, 11 * s, 400, prawy=True)
        data = self._dzien.data.strftime("%d.%m.%Y") if self._dzien else ""
        podtytul = f"nr {self._numer} · {data}" if self._numer else data
        y += 15 * s
        _napis(p, lewy, y, podtytul, szary, 10.5 * s, 400)

        # cienka linia z gradientem — nagłówek dokumentu odcięty od treści
        y += 12 * s
        p.setBrush(Qt.BrushStyle.NoBrush)
        g = QLinearGradient(QPointF(lewy, y), QPointF(prawy, y))
        g.setColorAt(0.0, st.z_alfa(zielony, 185))
        g.setColorAt(0.16, QColor(16, 24, 40, 140))
        g.setColorAt(0.62, QColor(16, 24, 40, 52))
        g.setColorAt(1.0, QColor(16, 24, 40, 12))
        p.setPen(QPen(QBrush(g), 1.2))
        p.drawLine(QPointF(lewy, y), QPointF(prawy, y))

        # — rubryki nagłówkowe —
        def rubryka(x, yy, etykieta, wartosc, szer, kolor=ciemny, waga=700):
            _napis(p, x, yy, etykieta, szary, 8.6 * s, 500, odstep=0.8 * s)
            f = st.czcionka(11.5 * s, waga)
            _napis(p, x, yy + 14 * s, _przytnij(wartosc, f, szer), kolor, 11.5 * s, waga)

        y += 18 * s
        menedzer = "uzupełniony" if dn.MENEDZER.startswith("(") else dn.MENEDZER
        rubryka(lewy, y, "PRACOWNIK", dn.PRACOWNIK, cw * 0.33)
        rubryka(lewy + cw * 0.355, y, "STANOWISKO", dn.STANOWISKO, cw * 0.34)
        rubryka(lewy + cw * 0.715, y, "MENEDŻER", menedzer, cw * 0.285, zielony)

        y += 32 * s
        rubryka(lewy, y, "ADRES", dn.ADRES, cw)

        y += 32 * s
        _napis(p, lewy, y, "CEL WYJAZDU", szary, 8.6 * s, 500, odstep=0.8 * s)
        sieci = ", ".join(dn.SIECI[:-1]) + " i " + dn.SIECI[-1]
        cel = f"Wizyty w sklepach sieci {sieci} · samochód prywatny pow. 900 cm³"
        f_cel = st.czcionka(11 * s, 400)
        for i, linia in enumerate(_zawin(cel, f_cel, cw, 2)):
            _napis(p, lewy, y + (14 + i * 14) * s, linia, sredni, 11 * s, 400)

        y += 54 * s

        # — dół kartki liczony od spodu, żeby podpisy zawsze siedziały na miejscu —
        dol = kar.bottom() - 18 * s
        y_podpis = dol - 6 * s
        y_linia_podpisu = y_podpis - 12 * s
        y_rubryki = y_linia_podpisu - 34 * s
        # podpisana kartka oddaje tabeli mniej miejsca, żeby pieczątka miała gdzie usiąść
        zapas_pieczatki = 34 * s if self._stan == "podpisana" else 0.0
        self._miejsce_pieczatki = QPointF(prawy - cw * 0.30, y_rubryki - 34 * s)

        if pusta:
            srodek = (y + y_rubryki) / 2.0
            f = st.czcionka(13 * s, 600, odstep=1.2 * s)
            napis = "dzień wolny"
            szer = QFontMetricsF(f).horizontalAdvance(napis)
            x0 = kar.center().x() - szer / 2.0
            _napis(p, x0, srodek, napis, QColor("#98A2B3"), 13 * s, 600, odstep=1.2 * s)
            kreska = szer * 0.62
            for kier in (-1, 1):
                a = QPointF(kar.center().x() - kreska / 2.0, srodek + 16 * s * kier
                            - (24 * s if kier < 0 else 0))
                b = QPointF(a.x() + kreska, a.y())
                g = QLinearGradient(a, b)
                g.setColorAt(0.0, QColor(16, 24, 40, 0))
                g.setColorAt(0.5, QColor(16, 24, 40, 56))
                g.setColorAt(1.0, QColor(16, 24, 40, 0))
                p.setPen(QPen(QBrush(g), 1.0))
                p.drawLine(a, b)
        else:
            self._rysuj_tabele(p, lewy, prawy, y, y_rubryki - 24 * s - zapas_pieczatki, s,
                               szary, ciemny, sredni, kreska_mocna, kreska_slaba)
            self._rysuj_rubryki_dolne(p, lewy, prawy, y_rubryki, s, szary, ciemny, sredni)

        # — linie podpisu, gasnące ku końcowi —
        szer_podpisu = (prawy - lewy) * 0.44
        for x0 in (lewy, prawy - szer_podpisu):
            a = QPointF(x0, y_linia_podpisu)
            b = QPointF(x0 + szer_podpisu, y_linia_podpisu)
            g = QLinearGradient(a, b)
            g.setColorAt(0.0, QColor(16, 24, 40, 120))
            g.setColorAt(1.0, QColor(16, 24, 40, 26))
            p.setPen(QPen(QBrush(g), 1.0))
            p.drawLine(a, b)
        _napis(p, lewy, y_podpis, "podpis pracownika", szary, 9.5 * s, 400)
        _napis(p, prawy - szer_podpisu, y_podpis, "podpis przełożonego", szary, 9.5 * s, 400)

    def _rysuj_tabele(self, p, lewy, prawy, y_gora, y_dol, s,
                      szary, ciemny, sredni, kreska_mocna, kreska_slaba):
        cw = prawy - lewy
        x_wyj = lewy
        x_trasa = lewy + cw * 0.131
        x_przyj = lewy + cw * 0.599
        x_km = lewy + cw * 0.854
        x_zl = prawy

        odcinki = odcinki_dnia(self._dzien)
        y = y_gora
        _napis(p, x_wyj, y, "WYJ.", szary, 8.6 * s, 500, odstep=0.8 * s)
        _napis(p, x_trasa, y, "TRASA", szary, 8.6 * s, 500, odstep=0.8 * s)
        _napis(p, x_przyj, y, "PRZYJ.", szary, 8.6 * s, 500, odstep=0.8 * s)
        _napis(p, x_km, y, "KM", szary, 8.6 * s, 500, odstep=0.8 * s, prawy=True)
        _napis(p, x_zl, y, "ZŁ", szary, 8.6 * s, 500, odstep=0.8 * s, prawy=True)
        y += 7 * s
        p.setPen(QPen(kreska_mocna, 1.0))
        p.drawLine(QPointF(lewy, y), QPointF(prawy, y))

        # wiersz „Razem” trzymamy na dole, wiersze trasy dzielą to, co zostało
        wys_razem = 24 * s
        dostepne = max(10.0, (y_dol - wys_razem) - y)
        ile = max(1, len(odcinki))
        wys_wiersza = max(13.0 * s, min(30.0 * s, dostepne / ile))

        f_trasa = st.czcionka(11 * s, 400)
        for i, o in enumerate(odcinki):
            if i % 2 == 1:                      # cichy pasek co drugi wiersz
                p.fillRect(QRectF(lewy - 3 * s, y + wys_wiersza * i,
                                  (prawy - lewy) + 6 * s, wys_wiersza),
                           QColor(16, 24, 40, 9))
            yy = y + wys_wiersza * (i + 0.72)
            _napis(p, x_wyj, yy, o["wyj"], sredni, 10.5 * s, 400, mono=True)
            napis = f'{o["z"]} → {o["do"]}'
            _napis(p, x_trasa, yy, _przytnij(napis, f_trasa, x_przyj - x_trasa - 8 * s),
                   ciemny, 11 * s, 400)
            _napis(p, x_przyj, yy, o["przyj"], sredni, 10.5 * s, 400, mono=True)
            _napis(p, x_km, yy, f'{o["km"]:.1f}'.replace(".", ","),
                   ciemny, 10.5 * s, 400, mono=True, prawy=True)
            _napis(p, x_zl, yy, dn.zl(o["zl"]), ciemny, 10.5 * s, 400, mono=True, prawy=True)
            if i < len(odcinki) - 1:
                p.setPen(QPen(kreska_slaba, 1.0))
                p.drawLine(QPointF(lewy, y + wys_wiersza * (i + 1)),
                           QPointF(prawy, y + wys_wiersza * (i + 1)))

        y_razem = y + wys_wiersza * len(odcinki)
        p.setPen(QPen(kreska_mocna, 1.0))
        p.drawLine(QPointF(lewy, y_razem), QPointF(prawy, y_razem))
        yy = y_razem + 15 * s
        _napis(p, x_trasa, yy, "Razem", ciemny, 11.5 * s, 700)
        _napis(p, x_km, yy, f'{self._dzien.km:.1f}'.replace(".", ","),
               ciemny, 10.5 * s, 700, mono=True, prawy=True)
        _napis(p, x_zl, yy, dn.zl(self._dzien.kwota), ciemny, 10.5 * s, 700, mono=True, prawy=True)

    def _rysuj_rubryki_dolne(self, p, lewy, prawy, y, s, szary, ciemny, sredni):
        cw = prawy - lewy
        kwota = self._dzien.kwota if self._dzien else 0.0
        _napis(p, lewy, y, "STAWKA", szary, 8.6 * s, 500, odstep=0.8 * s)
        _napis(p, lewy, y + 15 * s, f"{dn.STAWKA:.4f}".replace(".", ",") + "  zł/km",
               sredni, 11 * s, 400, mono=True)
        _napis(p, lewy + cw * 0.36, y, "DIETA", szary, 8.6 * s, 500, odstep=0.8 * s)
        _napis(p, lewy + cw * 0.36, y + 15 * s, "0,00 zł", sredni, 11 * s, 400, mono=True)
        _napis(p, prawy, y, "DO WYPŁATY", szary, 8.6 * s, 500, odstep=0.8 * s, prawy=True)
        napis = dn.zl(kwota) + " zł"
        f = st.czcionka(12 * s, 700, mono=True)
        szer = QFontMetricsF(f).horizontalAdvance(napis)
        pole = QRectF(prawy - szer - 7 * s, y + 3 * s, szer + 14 * s, 17 * s)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(14, 155, 116, 20)))
        p.drawRoundedRect(pole, 4 * s, 4 * s)
        _napis(p, prawy, y + 15 * s, napis, ciemny, 12 * s, 700, mono=True, prawy=True)

    def _rysuj_pieczatke(self, p, kar):
        s = kar.width() / self.SZEROKOSC_WZORCOWA
        zielony = QColor("#0E9B74")
        srodek = getattr(self, "_miejsce_pieczatki", None) or QPointF(
            kar.right() - kar.width() * 0.28, kar.bottom() - kar.height() * 0.22)
        godzina = self._dzien.koniec if self._dzien else ""
        p.save()
        p.translate(srodek)
        p.rotate(-11)
        pole = QRectF(-56 * s, -19 * s, 112 * s, 38 * s)
        p.setPen(QPen(st.z_alfa(zielony, 190), 2.0))
        p.setBrush(QBrush(st.z_alfa(zielony, 18)))
        p.drawRoundedRect(pole, 6 * s, 6 * s)
        p.setPen(QPen(st.z_alfa(zielony, 110), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(pole.adjusted(3 * s, 3 * s, -3 * s, -3 * s), 4 * s, 4 * s)
        f = st.czcionka(12.5 * s, 700, odstep=1.4 * s)
        szer = QFontMetricsF(f).horizontalAdvance("PODPISANO")
        _napis(p, -szer / 2.0, -2 * s, "PODPISANO", st.z_alfa(zielony, 235), 12.5 * s, 700,
               odstep=1.4 * s)
        f2 = st.czcionka(9.5 * s, 500, mono=True)
        szer2 = QFontMetricsF(f2).horizontalAdvance(godzina)
        _napis(p, -szer2 / 2.0, 12 * s, godzina, st.z_alfa(zielony, 200), 9.5 * s, 500, mono=True)
        p.restore()


# ── podgląd bez okna głównego ────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    def scena(nazwa, dzien, stan_mapy="zwykly", stan_kartki="zwykla", szer=980, wys=620):
        okno = QWidget()
        okno.resize(szer, wys)
        okno.setStyleSheet(f"background: {st.TLO_GORA.name()};")

        mapa = MapaDnia(okno)
        mapa.setGeometry(0, 0, szer, wys)
        kartka = KartkaDelegacji(okno)
        szer_k = int(szer * 0.38)
        kartka.setGeometry(szer - szer_k - 18, 16, szer_k, int(wys * 0.85))

        mapa.ustaw_animacje(False)
        kartka.ustaw_animacje(False)
        mapa.ustaw_dzien(dzien)
        mapa.ustaw_stan(stan_mapy)
        mapa.ustaw_kotwice_kartki(QPointF(kartka.x() + 8, kartka.y() + 26))
        kartka.ustaw_dzien(dzien)
        kartka.ustaw_stan(stan_kartki)

        okno.show()
        for _ in range(4):
            app.processEvents()
        mapa.ustaw_animacje(False)
        kartka.ustaw_animacje(False)
        app.processEvents()
        okno.grab().save(nazwa)
        okno.hide()
        print("zapisano", nazwa)

    dni = dn.oblicz_miesiac(1850)
    dzien = next((d for d in dni if not d.wolny), None)
    wolny = next((d for d in dni if d.wolny), None)

    scena("zrzut_mapa.png", dzien)
    scena("zrzut_mapa_pusto.png", wolny, stan_kartki="pusta")
    scena("zrzut_mapa_sukces.png", dzien, stan_mapy="sukces", stan_kartki="podpisana")
