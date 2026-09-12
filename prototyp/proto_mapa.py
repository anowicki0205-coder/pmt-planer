# -*- coding: utf-8 -*-
"""Prawa strona ekranu prototypu: mapa dnia i leżąca na niej kartka delegacji.

Wszystko jest rysowane ręcznie w paintEvent — żadnych obrazków z dysku,
żadnych bibliotek poza PyQt6. Geometria liczona jest ze współczynników,
więc oba widżety znoszą dowolną zmianę rozmiaru okna.

Teren nie jest rysunkiem technicznym: buduje go kilkanaście wypełnionych
warstw wysokościowych o bardzo niskim kontraście, przesuwanych ku światłu,
plus mgła odległości u góry. Statyczny podkład (tło, teren, rzeka, drogi)
liczony jest raz na rozmiar i trzymany w pixmapie, więc animacja blasku
trasy kosztuje tylko odrysowanie warstw ruchomych.

Zegary: MapaDnia i KartkaDelegacji mają ``ustaw_animacje(wlaczone)``.
Wyłączenie zatrzymuje zegar i ustawia stałą fazę — zrzuty są powtarzalne.
"""
import math

from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import (QPainter, QPainterPath, QPen, QBrush, QColor, QPixmap,
                         QFontMetricsF, QLinearGradient, QRadialGradient)
from PyQt6.QtWidgets import QWidget

import proto_styl as st
import proto_dane as dn


# Kierunek, z którego pada światło na cały ekran: lewy górny róg.
# Wektor jednostkowy wskazuje źródło, więc cienie idą dokładnie w przeciwną stronę.
SWIATLO = (-0.58, -0.81)
BARWA_TERENU = QColor(126, 178, 206)      # chłodny kamień, prawie bez nasycenia
BARWA_MGLY = QColor(150, 196, 226)        # mgła odległości u góry mapy


# ── drobne narzędzia ─────────────────────────────────────────────────
class _Losowy:
    """Własny generator liniowy: ten sam teren przy każdym odświeżeniu.

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


def _sciezka_gladka(punkty, zamknieta=False, napiecie=1.0):
    """Krzywa Catmull–Rom przepuszczona przez punkty, zamieniona na sześcienne Béziery."""
    sciezka = QPainterPath()
    if len(punkty) < 2:
        return sciezka
    pkt = [QPointF(x, y) for (x, y) in punkty]
    n = len(pkt)

    def we(i):
        if zamknieta:
            return pkt[i % n]
        return pkt[max(0, min(n - 1, i))]

    sciezka.moveTo(we(0))
    ostatni = n if zamknieta else n - 1
    for i in range(ostatni):
        p0, p1, p2, p3 = we(i - 1), we(i), we(i + 1), we(i + 2)
        c1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6.0 * napiecie,
                     p1.y() + (p2.y() - p0.y()) / 6.0 * napiecie)
        c2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6.0 * napiecie,
                     p2.y() - (p3.y() - p1.y()) / 6.0 * napiecie)
        sciezka.cubicTo(c1, c2, p2)
    if zamknieta:
        sciezka.closeSubpath()
    return sciezka


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


def _cien_miekki(p, pole, promien, przesun, rozmycie, sila, barwa=QColor(0, 0, 0)):
    """Jedna warstwa miękkiego cienia: zanik kwadratowy, krok co 2 piksele."""
    if rozmycie <= 0 or sila <= 0:
        return
    krok = 2
    ile = max(1, int(rozmycie / krok))
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
    """Mapa okolicy z trasą dnia. Cała rysowana ręcznie, warstwa po warstwie."""

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
        self._teren = self._zbuduj_teren()
        self._drogi = self._zbuduj_drogi()
        self._podklad = None            # pixmapa terenu (zależy tylko od rozmiaru)
        self._podklad_klucz = None
        self._dol = None                # teren + cień i światło trasy
        self._gora = None               # miasta i podpisy, na przezroczystym
        self._warstwy_klucz = None
        self._geo = None                # policzona geometria trasy i podpisów
        self._geo_klucz = None
        self._faza = self.FAZA_ZRZUTU
        self._anim = True
        self._zegar = QTimer(self)
        self._zegar.setInterval(self.KLATKA)
        self._zegar.timeout.connect(self._tik)
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
        czynny = (self._dzien is not None and not self._dzien.wolny
                  and len(self._dzien.trasa) >= 2)
        if self._anim and czynny and self.isVisible():
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
        super().closeEvent(zdarzenie)

    def resizeEvent(self, zdarzenie):
        self._podklad = None
        self._warstwy_klucz = None
        self._geo_klucz = None
        super().resizeEvent(zdarzenie)

    # — geometria terenu (liczona raz, w układzie 0..1) —
    def _zbuduj_teren(self):
        """Wzgórza jako stosy zamkniętych warstw wysokościowych.

        Każda kolejna warstwa jest mniejsza i przesunięta w stronę światła,
        więc od lewej góry wychodzą jaśniejsze tarasy, a prawy dół zostaje
        w cieniu. To daje relief zamiast zbioru cienkich krzywych.
        """
        los = _Losowy(20260902)

        def wzgorze(prom_min, prom_max, wys_min, wys_max, ile_warstw):
            sx = los.zakres(-0.06, 1.06)
            sy = los.zakres(-0.04, 1.04)
            prom = los.zakres(prom_min, prom_max)
            splaszcz = los.zakres(0.52, 0.96)
            obrot = los.zakres(0.0, math.pi)
            wys = los.zakres(wys_min, wys_max)
            ile = 13
            zaburzenia = [los.zakres(0.74, 1.26) for _ in range(ile)]
            warstwy = []
            for k in range(ile_warstw):
                t = k / (ile_warstw - 1.0)
                kurcz = 1.0 - 0.74 * t
                dryf = prom * 0.44 * t
                punkty = []
                for j in range(ile):
                    kat = 2 * math.pi * j / ile + obrot
                    # im wyżej, tym gładszy obrys — szczyt jest spokojniejszy
                    faluje = 1.0 + (zaburzenia[j] - 1.0) * (1.0 - 0.55 * t)
                    rr = prom * kurcz * faluje
                    x = sx + math.cos(kat) * rr + SWIATLO[0] * dryf
                    y = sy + math.sin(kat) * rr * splaszcz + SWIATLO[1] * dryf
                    punkty.append((x, y))
                warstwy.append(punkty)
            return {"warstwy": warstwy, "wys": wys}

        # dwie rodziny: szerokie masywy i drobniejsze garby, które je urozmaicają
        wzgorza = [wzgorze(0.13, 0.30, 0.62, 1.00, 9) for _ in range(9)]
        wzgorza += [wzgorze(0.045, 0.115, 0.40, 0.72, 6) for _ in range(12)]

        # rzeka: kilka punktów sterujących z góry na dół, lekko wijąca się
        rzeka = []
        x = los.zakres(0.05, 0.2)
        for i in range(8):
            y = -0.06 + i * (1.16 / 7.0)
            x = min(0.98, max(0.02, x + los.zakres(0.02, 0.2)))
            rzeka.append((x, y))
        return {"wzgorza": wzgorza, "rzeka": rzeka}

    def _zbuduj_drogi(self):
        """Sieć dróg: każde miasto łączy się z dwoma najbliższymi sąsiadami."""
        nazwy = list(dn.MIASTA.keys())
        pary = set()
        for a in nazwy:
            ax, ay = dn.MIASTA[a]
            sasiedzi = sorted(
                (n for n in nazwy if n != a),
                key=lambda n: (dn.MIASTA[n][0] - ax) ** 2 + (dn.MIASTA[n][1] - ay) ** 2)
            for b in sasiedzi[:2]:
                pary.add(tuple(sorted((a, b))))
        return sorted(pary)

    # — przeliczanie współrzędnych —
    def _pole(self):
        """Obszar, w którym mieszczą się miasta.

        Jest węższy od widżetu i przesunięty w lewo — prawą stronę zasłania
        kartka delegacji, dokładnie jak na projekcie.
        """
        r = QRectF(self.rect())
        return QRectF(r.x() + r.width() * 0.045, r.y() + r.height() * 0.07,
                      r.width() * 0.63, r.height() * 0.86)

    def _punkt(self, nazwa):
        fx, fy = dn.MIASTA.get(nazwa, (0.5, 0.5))
        pole = self._pole()
        return QPointF(pole.x() + fx * pole.width(), pole.y() + fy * pole.height())

    def _kolor_trasy(self):
        return st.ZIELEN if self._stan == "sukces" else st.CYJAN

    def _czynny(self):
        d = self._dzien
        return d is not None and not d.wolny and len(d.trasa) >= 2

    # — rysowanie —
    def paintEvent(self, _zdarzenie):
        """Klatka składa się z dwóch gotowych warstw i tego, co się rusza."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect())
        geo = self._geometria() if self._czynny() else None
        dol, gora = self._warstwy(geo)

        p.drawPixmap(0, 0, dol)                        # a) teren i trasa
        if geo is not None:
            self._rysuj_powrot(p, geo)                 # b) kreskowany powrót
            self._rysuj_blask(p, geo)                  # c) płynący blask
        p.drawPixmap(0, 0, gora)                       # d) miasta i podpisy
        if geo is not None:
            self._rysuj_puls_bazy(p)                   # e) oddech bazy
            self._rysuj_nitke(p, geo)                  # f) nitka do kartki

        st.winieta(p, r, 78)                           # g) wykończenie
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
        r = QRectF(self.rect())

        dol = self._nowa_pixmapa()
        q = QPainter(dol)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.drawPixmap(0, 0, self._pixmapa_podkladu())
        if geo is not None:
            self._rysuj_cien_trasy(q, geo)
            self._rysuj_trase(q, geo)
        q.end()

        gora = self._nowa_pixmapa()
        q = QPainter(gora)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self._rysuj_miasta(q, geo)
        if geo is not None:
            self._rysuj_podpisy(q, geo)
        q.end()

        self._dol, self._gora, self._warstwy_klucz = dol, gora, klucz
        return dol, gora

    # — statyczny podkład —
    def _pixmapa_podkladu(self):
        """Tło, teren, mgła, rzeka i drogi — liczone raz na rozmiar widżetu."""
        dpr = self.devicePixelRatioF()
        klucz = (self.width(), self.height(), round(dpr, 3))
        if self._podklad is not None and self._podklad_klucz == klucz:
            return self._podklad
        pix = self._nowa_pixmapa()
        q = QPainter(pix)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        r = QRectF(self.rect())
        # teren jest z natury miękki, więc liczy się go w połowie skali
        # i rozciąga — cztery razy taniej przy zmianie rozmiaru okna
        teren = self._pixmapa_terenu(dpr)
        q.drawPixmap(QRectF(r), teren, QRectF(teren.rect()))
        self._rysuj_siatke(q, r)
        self._rysuj_rzeke(q, r)
        self._rysuj_drogi(q, r)
        self._rysuj_mgle(q, r)
        q.end()
        self._podklad = pix
        self._podklad_klucz = klucz
        return pix

    def _pixmapa_terenu(self, dpr):
        """Tło sceny i wzgórza w połowie rozdzielczości."""
        skala = 0.5
        w = max(2, int(self.width() * dpr * skala))
        h = max(2, int(self.height() * dpr * skala))
        pix = QPixmap(w, h)
        pix.fill(Qt.GlobalColor.transparent)
        q = QPainter(pix)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.scale(w / max(1.0, float(self.width())), h / max(1.0, float(self.height())))
        r = QRectF(self.rect())
        st.tlo_sceny(q, r)
        self._rysuj_teren(q, r)
        q.end()
        return pix

    def _rysuj_siatke(self, p, r):
        p.setBrush(Qt.BrushStyle.NoBrush)
        krok = max(28.0, r.width() / 22.0)
        # siatka gaśnie ku górze — tam, gdzie zaczyna się mgła
        def alfa_dla(y):
            t = max(0.0, min(1.0, (y - r.y()) / max(1.0, r.height())))
            return 4.0 + 8.0 * t

        x = r.x() + krok * 0.5
        while x < r.right():
            p.setPen(_pioro_gradientowe(QPointF(x, r.y()), QPointF(x, r.bottom()),
                                        st.z_alfa(st.CYJAN, alfa_dla(r.y())),
                                        st.z_alfa(st.CYJAN, alfa_dla(r.bottom())), 1.0))
            p.drawLine(QPointF(x, r.y()), QPointF(x, r.bottom()))
            x += krok
        y = r.y() + krok * 0.5
        while y < r.bottom():
            p.setPen(QPen(st.z_alfa(st.CYJAN, int(alfa_dla(y))), 1.0))
            p.drawLine(QPointF(r.x(), y), QPointF(r.right(), y))
            y += krok

    def _rysuj_teren(self, p, r):
        """Wypełnione warstwy wysokościowe: relief, nie mapa poziomicowa."""
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for wzg in self._teren["wzgorza"]:
            warstwy = wzg["warstwy"]
            wys = wzg["wys"]
            sciezki = []
            for punkty in warstwy:
                pkt = [(r.x() + x * r.width(), r.y() + y * r.height()) for (x, y) in punkty]
                sciezki.append(_sciezka_gladka(pkt, zamknieta=True))

            # cień rzucany przez całe wzgórze w stronę przeciwną do światła
            podstawa = sciezki[0]
            rozmiar = max(r.width(), r.height())
            for i, (odl, a) in enumerate(((0.016, 9), (0.010, 8), (0.005, 7))):
                przes = rozmiar * odl
                p.save()
                p.translate(-SWIATLO[0] * przes, -SWIATLO[1] * przes)
                p.fillPath(podstawa, QColor(0, 0, 0, int(a * wys)))
                p.restore()

            for k, sciezka in enumerate(sciezki):
                t = k / float(len(sciezki) - 1)
                pole = sciezka.boundingRect()
                srodek = pole.center()
                zasieg = max(pole.width(), pole.height()) * 0.62 + 1.0
                jasny = QPointF(srodek.x() + SWIATLO[0] * zasieg,
                                srodek.y() + SWIATLO[1] * zasieg)
                ciemny = QPointF(srodek.x() - SWIATLO[0] * zasieg,
                                 srodek.y() - SWIATLO[1] * zasieg)
                # szerokość miękkiego pasa krawędzi — skaluje się z wielkością garbu
                pas = max(2.2, min(pole.width(), pole.height()) * 0.085)

                # a) pas cienia tuż pod krawędzią od strony przeciwnej do światła
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.save()
                p.translate(-SWIATLO[0] * pas * 0.42, -SWIATLO[1] * pas * 0.42)
                p.setPen(_pioro_gradientowe(
                    jasny, ciemny, QColor(0, 0, 0, 0),
                    QColor(0, 0, 0, int((10.0 + 7.0 * t) * wys)), pas))
                p.drawPath(sciezka)
                p.restore()

                # b) wypełnienie warstwy: bardzo niski kontrast, lekko cieplejsze
                #    od strony światła — relief bierze się z nakładania warstw
                sila = (2.1 + 1.9 * t) * wys
                g = QLinearGradient(jasny, ciemny)
                g.setColorAt(0.0, st.z_alfa(BARWA_TERENU, sila * 1.25))
                g.setColorAt(0.62, st.z_alfa(BARWA_TERENU, sila * 0.95))
                g.setColorAt(1.0, st.z_alfa(BARWA_TERENU, sila * 0.62))
                p.fillPath(sciezka, QBrush(g))

                # c) pas światła po wewnętrznej stronie krawędzi — taras
                p.save()
                p.translate(SWIATLO[0] * pas * 0.34, SWIATLO[1] * pas * 0.34)
                p.setPen(_pioro_gradientowe(
                    jasny, srodek,
                    st.z_alfa(st.MIETA, (7.0 + 9.0 * t) * wys),
                    st.z_alfa(st.MIETA, 0), pas * 0.85))
                p.drawPath(sciezka)
                p.restore()

    def _rysuj_mgle(self, p, r):
        """Mgła odległości: góra mapy jaśniejsza i o mniejszym kontraście."""
        g = QLinearGradient(r.topLeft(), QPointF(r.x(), r.y() + r.height() * 0.66))
        g.setColorAt(0.0, st.z_alfa(BARWA_MGLY, 30))
        g.setColorAt(0.34, st.z_alfa(BARWA_MGLY, 14))
        g.setColorAt(1.0, st.z_alfa(BARWA_MGLY, 0))
        p.fillRect(r, QBrush(g))
        # druga, cieplejsza warstwa tuż przy górnej krawędzi
        g2 = QLinearGradient(r.topLeft(), QPointF(r.x(), r.y() + r.height() * 0.22))
        g2.setColorAt(0.0, QColor(205, 226, 240, 22))
        g2.setColorAt(1.0, QColor(205, 226, 240, 0))
        p.fillRect(r, QBrush(g2))

    def _rysuj_rzeke(self, p, r):
        punkty = [(r.x() + x * r.width(), r.y() + y * r.height())
                  for (x, y) in self._teren["rzeka"]]
        sciezka = _sciezka_gladka(punkty)
        p.setBrush(Qt.BrushStyle.NoBrush)
        szer = max(6.0, r.width() * 0.013)
        # koryto ciemniejsze od tła, na nim jaśniejszy brzeg od strony światła
        pen = QPen(QColor(2, 8, 16, 58), szer)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(sciezka)
        p.save()
        p.translate(SWIATLO[0] * szer * 0.30, SWIATLO[1] * szer * 0.30)
        pen = QPen(st.z_alfa(st.CYJAN, 20), max(1.0, szer * 0.16))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(sciezka)
        p.restore()

    def _rysuj_drogi(self, p, r):
        p.setBrush(Qt.BrushStyle.NoBrush)
        for a, b in self._drogi:
            pa, pb = self._punkt(a), self._punkt(b)
            p.setPen(QPen(QColor(0, 0, 0, 40), 2.2))
            p.drawLine(QPointF(pa.x() + 1.0, pa.y() + 1.4), QPointF(pb.x() + 1.0, pb.y() + 1.4))
            p.setPen(QPen(st.z_alfa(st.TEKST_3, 26), 1.0))
            p.drawLine(pa, pb)

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

        punkty = [(self._punkt(n).x(), self._punkt(n).y()) for n in trasa]
        glowna = _sciezka_gladka(punkty[:-1], napiecie=1.0)       # bez powrotu do bazy
        powrot = self._luk_powrotu(punkty)                        # odcinek powrotny
        ile_probek = 220
        probki = [glowna.pointAtPercent(i / float(ile_probek)) for i in range(ile_probek + 1)]
        nitka = self._sciezka_nitki()
        etykiety = self._ulozenie_podpisow(glowna, powrot, nitka)
        self._geo = {"glowna": glowna, "powrot": powrot, "probki": probki,
                     "nitka": nitka, "etykiety": etykiety, "trasa": trasa}
        self._geo_klucz = klucz
        return self._geo

    def _luk_powrotu(self, punkty):
        """Powrót do bazy wygięty na zewnątrz pętli, żeby nie był suchą prostą."""
        (ax, ay), (bx, by) = punkty[-2], punkty[-1]
        sx = sum(x for x, _ in punkty) / len(punkty)
        sy = sum(y for _, y in punkty) / len(punkty)
        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
        dx, dy = bx - ax, by - ay
        dlug = max(1.0, math.hypot(dx, dy))
        nx, ny = -dy / dlug, dx / dlug
        # normalna skierowana od środka trasy — łuk wychodzi na zewnątrz
        if (mx + nx - sx) ** 2 + (my + ny - sy) ** 2 < (mx - nx - sx) ** 2 + (my - ny - sy) ** 2:
            nx, ny = -nx, -ny
        sciezka = QPainterPath(QPointF(ax, ay))
        sciezka.quadTo(QPointF(mx + nx * dlug * 0.12, my + ny * dlug * 0.12), QPointF(bx, by))
        return sciezka

    def _grubosc(self):
        return min(self.width(), self.height()) / 620.0

    def _rysuj_cien_trasy(self, p, geo):
        """Trasa rzuca cień na teren — linia unosi się nad mapą."""
        k = self._grubosc()
        przes = max(4.0, 11.0 * k)
        p.save()
        p.translate(-SWIATLO[0] * przes, -SWIATLO[1] * przes)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for szer, alfa in ((26 * k, 30), (15 * k, 40), (7.0 * k, 52)):
            pen = QPen(QColor(0, 0, 0, alfa), max(1.0, szer))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawPath(geo["glowna"])
        pen = QPen(QColor(0, 0, 0, 34), max(1.0, 5.0 * k))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(geo["powrot"])
        p.restore()

    def _rysuj_trase(self, p, geo):
        kolor = self._kolor_trasy()
        k = self._grubosc()
        # linia spokojna sama z siebie — jasność dokłada dopiero płynący blask
        st.poswiata_linii(p, geo["glowna"], kolor,
                          warstwy=((30 * k, 10), (17 * k, 22), (8.0 * k, 74),
                                   (3.4 * k, 170)))
        # jasny rdzeń, jak na projekcie
        pen = QPen(st.z_alfa(QColor(228, 255, 255), 120), 1.3 * k)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen)
        p.drawPath(geo["glowna"])

    def _rysuj_powrot(self, p, geo):
        """Powrót do bazy: kreski wolno płyną w stronę domu."""
        k = self._grubosc()
        przesun = -self._faza * 34.0 * k if self._anim else 0.0
        _kreskowana(p, geo["powrot"], st.ZIELEN,
                    warstwy=((18 * k, 22), (8 * k, 58), (3.0 * k, 210)),
                    kreska=11.0 * k, przerwa=8.0 * k, przesuniecie=przesun)

    def _rysuj_blask(self, p, geo):
        """Powoli płynący jaśniejszy odcinek wzdłuż trasy."""
        probki = geo["probki"]
        if len(probki) < 3:
            return
        k = self._grubosc()
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
            a = probki[max(0, min(n, int(round(max(0.0, t0) * n))))]
            b = probki[max(0, min(n, int(round(min(1.0, t1) * n))))]
            jas = (1.0 - i / float(ile)) ** 2.0
            for szer, sila, barwa in ((24.0 * k, 26, kolor),
                                      (11.0 * k, 60, kolor),
                                      (5.0 * k, 96, kolor),
                                      (2.2 * k, 235, QColor(238, 255, 255))):
                pen = QPen(st.z_alfa(barwa, sila * jas), max(0.8, szer))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.drawLine(a, b)
        # czubek blasku
        if 0.0 <= czolo <= 1.0:
            glowa = probki[max(0, min(n, int(round(czolo * n))))]
            st.punkt_swiatla(p, glowa, 46.0 * k, kolor, 62)
            st.punkt_swiatla(p, glowa, 18.0 * k, QColor(235, 255, 255), 96)

    # — miasta —
    def _znak_miasta(self, p, srodek, r_pkt, kolor, waga=1.0, powtorka=False):
        """Pierścień z cienkim obrysem, punkt w środku i miękkie halo."""
        if powtorka:
            # miasto odwiedzone wcześniej tego dnia: spokojniejsze, bez halo
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(5, 13, 23, 210)))
            p.drawEllipse(srodek, r_pkt * 0.92, r_pkt * 0.92)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(st.z_alfa(st.MIETA, 86), max(1.0, r_pkt * 0.20)))
            p.drawEllipse(srodek, r_pkt * 0.92, r_pkt * 0.92)
            p.setPen(QPen(st.z_alfa(st.MIETA, 40), 1.0))
            p.drawEllipse(srodek, r_pkt * 1.62, r_pkt * 1.62)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(st.z_alfa(st.MIETA, 150)))
            p.drawEllipse(srodek, r_pkt * 0.26, r_pkt * 0.26)
            return

        st.punkt_swiatla(p, srodek, r_pkt * 5.2 * waga, kolor, int(52 * waga))
        st.punkt_swiatla(p, srodek, r_pkt * 2.6 * waga, kolor, int(92 * waga))
        # ciemne wnętrze pierścienia, żeby punkt nie zlewał się z trasą
        rg = QRadialGradient(srodek, r_pkt * 1.05)
        rg.setColorAt(0.0, QColor(6, 16, 26, 245))
        rg.setColorAt(1.0, QColor(4, 11, 20, 215))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(rg))
        p.drawEllipse(srodek, r_pkt, r_pkt)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(kolor, int(235 * min(1.0, waga))), max(1.0, r_pkt * 0.24)))
        p.drawEllipse(srodek, r_pkt, r_pkt)
        p.setPen(QPen(st.z_alfa(kolor, 52), 1.0))
        p.drawEllipse(srodek, r_pkt * 1.85, r_pkt * 1.85)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(st.z_alfa(QColor(240, 255, 255), 240)))
        p.drawEllipse(srodek, r_pkt * 0.30, r_pkt * 0.30)

    def _rysuj_miasta(self, p, geo):
        trasa = list(geo["trasa"]) if geo is not None else []
        kolor = self._kolor_trasy()
        skala = min(self.width(), self.height())
        r_pkt = max(3.4, skala * 0.0095)

        # miasta poza trasą — ledwo widoczne punkciki, żeby mapa miała treść
        for nazwa in dn.MIASTA:
            if nazwa in trasa:
                continue
            s = self._punkt(nazwa)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(st.z_alfa(st.TEKST_3, 80)))
            p.drawEllipse(s, r_pkt * 0.34, r_pkt * 0.34)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(st.z_alfa(st.TEKST_3, 34), 1.0))
            p.drawEllipse(s, r_pkt * 0.92, r_pkt * 0.92)

        if geo is None:
            # sam teren: baza zaznaczona dyskretnie
            s = self._punkt(dn.BAZA)
            self._znak_miasta(p, s, r_pkt * 1.25, st.ZIELEN, waga=0.55)
            return

        widziane = set()
        for nazwa in trasa[1:-1]:
            s = self._punkt(nazwa)
            self._znak_miasta(p, s, r_pkt, kolor, powtorka=(nazwa in widziane))
            widziane.add(nazwa)

        # baza: większa i jaśniejsza od reszty
        self._znak_miasta(p, self._punkt(dn.BAZA), r_pkt * 1.5, st.ZIELEN, waga=1.0)

    def _rysuj_puls_bazy(self, p):
        """Wolny oddech halo bazy — jedyny ruch poza blaskiem trasy."""
        puls = 0.5 + 0.5 * math.sin(self._faza * 2.0 * math.pi)
        r_pkt = max(3.4, min(self.width(), self.height()) * 0.0095)
        s = self._punkt(dn.BAZA)
        st.punkt_swiatla(p, s, r_pkt * (7.2 + 1.6 * puls), st.ZIELEN, int(26 + 26 * puls))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(st.ZIELEN, int(58 - 34 * puls)), 1.2))
        p.drawEllipse(s, r_pkt * (2.6 + 1.5 * puls), r_pkt * (2.6 + 1.5 * puls))

    # — podpisy z unikaniem kolizji —
    def _ulozenie_podpisow(self, glowna, powrot, nitka):
        """Szuka miejsca na każdy podpis: raz na układ, nie co klatkę."""
        dzien = self._dzien
        skala = min(self.width(), self.height())
        r_pkt = max(3.4, skala * 0.0095)
        pozycje = {n: self._punkt(n) for n in dn.MIASTA}

        f_zwykly = st.czcionka(12, 500)
        f_baza = st.czcionka(14, 600)
        m_zwykly = QFontMetricsF(f_zwykly)
        m_baza = QFontMetricsF(f_baza)

        # próbki trasy — podpis nie powinien leżeć na linii
        probki = []
        for sciezka in (glowna, powrot):
            if sciezka is not None and sciezka.length() > 0:
                probki.extend(sciezka.pointAtPercent(i / 90.0) for i in range(91))
        probki.extend(pozycje[n] for n in dzien.trasa if n in pozycje)
        # nitka jest cienka, więc kolizja z nią kosztuje mniej niż z trasą
        probki_nitki = ([nitka.pointAtPercent(i / 60.0) for i in range(61)]
                        if nitka is not None and nitka.length() > 0 else [])

        zajete = []
        etykiety = []
        widziane = set()
        kolejnosc = [dn.BAZA]
        for n in dzien.trasa[1:-1]:
            if n not in kolejnosc:
                kolejnosc.append(n)

        for nazwa in kolejnosc:
            baza = (nazwa == dn.BAZA)
            napis = f"{nazwa} · start i powrót" if baza else nazwa
            m = m_baza if baza else m_zwykly
            szer = m.horizontalAdvance(napis)
            wys = m.height()
            srodek = pozycje[nazwa]
            odsun = r_pkt * (2.8 if baza else 2.1)

            # kandydaci: prawo, lewo, góra, dół i skosy — w trzech odległościach,
            # dalsze pozycje są droższe, więc używa ich dopiero przy ciasnocie
            kandydaci = []
            for mnoznik in (1.0, 2.0, 3.2):
                d = odsun * mnoznik
                kandydaci.extend([
                    (d, wys * 0.33),
                    (-szer - d, wys * 0.33),
                    (-szer * 0.5, -d - wys * 0.15),
                    (-szer * 0.5, d + wys * 0.85),
                    (d * 0.7, -d - wys * 0.15),
                    (-szer - d * 0.7, -d - wys * 0.15),
                    (d * 0.7, d + wys * 0.85),
                    (-szer - d * 0.7, d + wys * 0.85),
                ])
            najlepszy, najkoszt = None, None
            brzeg = QRectF(self.rect()).adjusted(12, 10, -12, -10)
            for nr, (dx, dy) in enumerate(kandydaci):
                x = srodek.x() + dx
                y = srodek.y() + dy                     # linia bazowa tekstu
                pole = QRectF(x - 5, y - m.ascent() - 4, szer + 10, wys + 8)
                koszt = (nr % 8) * 5.0 + (nr // 8) * 26.0
                if not brzeg.contains(pole):            # wyjście poza widżet
                    koszt += 900
                for inne in zajete:
                    wspolne = pole.intersected(inne)
                    if not wspolne.isEmpty():
                        koszt += 4.0 * wspolne.width() * wspolne.height()
                for pt in probki:
                    if pole.contains(pt):
                        koszt += 130
                for pt in probki_nitki:
                    if pole.contains(pt):
                        koszt += 45
                for inna, pkt in pozycje.items():
                    if inna != nazwa and pole.contains(pkt):
                        koszt += 60
                if najkoszt is None or koszt < najkoszt:
                    najkoszt, najlepszy = koszt, (x, y, pole)

            x, y, pole = najlepszy
            zajete.append(pole)
            powtorka = nazwa in widziane
            widziane.add(nazwa)
            etykiety.append((x, y, napis, baza, pole, powtorka))
        return etykiety

    def _rysuj_podpisy(self, p, geo):
        for (x, y, napis, baza, pole, _powt) in geo["etykiety"]:
            _poduszka(p, pole.adjusted(2, 1, -2, -1), sila=170)
        for (x, y, napis, baza, pole, _powt) in geo["etykiety"]:
            rozmiar, waga = (14, 600) if baza else (12, 500)
            kolor = st.TEKST if baza else st.z_alfa(st.TEKST, 238)
            _napis(p, x, y, napis, kolor, rozmiar, waga)

    # — nitka do kartki —
    def _sciezka_nitki(self):
        """Łuk od trasy do kartki; None, gdy kartka nie podała kotwicy."""
        dzien = self._dzien
        if self._kotwica is None or dzien is None or dzien.wolny:
            return None
        dokad = QPointF(self._kotwica)
        # nitka wychodzi z ostatniego przystanku, chyba że inny punkt trasy leży
        # wyraźnie bliżej kartki — wtedy linia nie przecina całej mapy
        ostatni = dzien.przystanki[-1] if dzien.przystanki else dn.BAZA

        def dystans(nazwa):
            s = self._punkt(nazwa)
            return math.hypot(s.x() - dokad.x(), s.y() - dokad.y())

        najblizszy = min(dzien.przystanki or [dn.BAZA], key=dystans)
        if dystans(najblizszy) < dystans(ostatni) * 0.75:
            ostatni = najblizszy
        skad = self._punkt(ostatni)
        # lekki łuk: punkt sterujący odsunięty w bok od cięciwy
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

    # — obsługa myszy —
    def mousePressEvent(self, zdarzenie):
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
        _cien_miekki(p, kar, promien, przesun=2, rozmycie=6, sila=110)
        _cien_miekki(p, kar, promien, przesun=9, rozmycie=20, sila=96)
        _cien_miekki(p, kar, promien, przesun=24, rozmycie=46, sila=64)

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
        st.ziarno(p, kar, sila=9, skala=1.5, ciemne=1.6)
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
