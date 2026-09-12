# -*- coding: utf-8 -*-
"""Prawa strona ekranu prototypu: mapa dnia i leżąca na niej kartka delegacji.

Wszystko jest rysowane ręcznie w paintEvent — żadnych obrazków z dysku,
żadnych bibliotek poza PyQt6. Geometria liczona jest ze współczynników,
więc oba widżety znoszą dowolną zmianę rozmiaru okna.
"""
import math

from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt6.QtGui import (QPainter, QPainterPath, QPen, QBrush, QColor,
                         QFontMetricsF, QLinearGradient)
from PyQt6.QtWidgets import QWidget

import proto_styl as st
import proto_dane as dn


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
                kreska=10.0, przerwa=8.0):
    """Świecąca linia kreskowana — poswiata_linii nie umie wzorów kreski."""
    p.setBrush(Qt.BrushStyle.NoBrush)
    for szer, alfa in warstwy:
        pen = QPen(st.z_alfa(kolor, alfa), szer)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        # wzór kreski podaje się w wielokrotnościach grubości pióra
        pen.setDashPattern([max(0.5, kreska / szer), max(0.4, przerwa / szer)])
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

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setMinimumSize(420, 300)
        self._dzien = None
        self._kotwica = None
        self._stan = "zwykly"
        self._teren = self._zbuduj_teren()
        self._drogi = self._zbuduj_drogi()

    # — interfejs publiczny —
    def ustaw_dzien(self, dzien):
        self._dzien = dzien
        self.update()

    def ustaw_kotwice_kartki(self, punkt):
        """Punkt (we współrzędnych mapy), do którego biegnie nitka; None = brak."""
        self._kotwica = QPointF(punkt) if punkt is not None else None
        self.update()

    def ustaw_stan(self, nazwa):
        self._stan = nazwa if nazwa in ("zwykly", "sukces") else "zwykly"
        self.update()

    def sizeHint(self):
        return QSize(900, 600)

    # — geometria terenu (liczona raz, w układzie 0..1) —
    def _zbuduj_teren(self):
        los = _Losowy(20260902)
        poziomice = []
        # siedem miękkich wzgórz; każde dostaje dwa obrysy, jak na mapie poziomicowej
        for _ in range(7):
            sx = los.zakres(0.02, 0.98)
            sy = los.zakres(0.04, 0.96)
            prom = los.zakres(0.10, 0.26)
            splaszcz = los.zakres(0.62, 1.35)
            obrot = los.zakres(0.0, math.pi)
            zabyrzenia = [los.zakres(0.72, 1.3) for _ in range(11)]
            poziomice.append((sx, sy, prom, splaszcz, obrot, zabyrzenia))

        # rzeka: kilka punktów sterujących z góry na dół, lekko wijąca się
        rzeka = []
        x = los.zakres(0.05, 0.2)
        for i in range(8):
            y = -0.06 + i * (1.16 / 7.0)
            x = min(0.98, max(0.02, x + los.zakres(0.02, 0.2)))
            rzeka.append((x, y))
        return {"poziomice": poziomice, "rzeka": rzeka}

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

    # — rysowanie —
    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect())

        st.tlo_sceny(p, r)                    # a) tło sceny
        self._rysuj_siatke(p, r)              # b) siatka i poziomice
        self._rysuj_poziomice(p, r)
        self._rysuj_rzeke(p, r)               # c) rzeka
        self._rysuj_drogi(p, r)               # d) drogi

        dzien = self._dzien
        czynny = dzien is not None and not dzien.wolny and len(dzien.trasa) >= 2

        sciezki_trasy = []
        if czynny:
            sciezki_trasy = self._rysuj_trase(p)   # e) trasa dnia

        self._rysuj_miasta(p, czynny)              # f) punkty miast
        self._rysuj_podpisy(p, czynny, sciezki_trasy)   # g) podpisy
        if czynny:
            self._rysuj_nitke(p)                   # h) nitka do kartki

        st.winieta(p, r, 96)                       # i) wykończenie
        st.ziarno(p, r, 10)
        p.end()

    def _rysuj_siatke(self, p, r):
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(st.CYJAN, 12), 1.0))
        krok = max(28.0, r.width() / 22.0)
        x = r.x() + krok * 0.5
        while x < r.right():
            p.drawLine(QPointF(x, r.y()), QPointF(x, r.bottom()))
            x += krok
        y = r.y() + krok * 0.5
        while y < r.bottom():
            p.drawLine(QPointF(r.x(), y), QPointF(r.right(), y))
            y += krok

    def _rysuj_poziomice(self, p, r):
        p.setBrush(Qt.BrushStyle.NoBrush)
        for (sx, sy, prom, splaszcz, obrot, zaburzenia) in self._teren["poziomice"]:
            srodek = QPointF(r.x() + sx * r.width(), r.y() + sy * r.height())
            skala = max(r.width(), r.height())
            for warstwa, (mnoznik, alfa) in enumerate(((1.0, 22), (0.68, 16), (0.4, 11))):
                punkty = []
                ile = len(zaburzenia)
                for i in range(ile):
                    kat = 2 * math.pi * i / ile
                    rr = prom * skala * mnoznik * zaburzenia[i]
                    x = srodek.x() + math.cos(kat + obrot) * rr
                    y = srodek.y() + math.sin(kat + obrot) * rr * splaszcz
                    punkty.append((x, y))
                p.setPen(QPen(st.z_alfa(st.MIETA, alfa), 1.0))
                p.drawPath(_sciezka_gladka(punkty, zamknieta=True))

    def _rysuj_rzeke(self, p, r):
        punkty = [(r.x() + x * r.width(), r.y() + y * r.height())
                  for (x, y) in self._teren["rzeka"]]
        sciezka = _sciezka_gladka(punkty)
        p.setBrush(Qt.BrushStyle.NoBrush)
        szer = max(6.0, r.width() * 0.013)
        # koryto ciemniejsze od tła, na nim jaśniejszy brzeg
        pen = QPen(QColor(2, 8, 16, 70), szer)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(sciezka)
        pen = QPen(st.z_alfa(st.CYJAN, 14), max(1.0, szer * 0.18))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(sciezka)

    def _rysuj_drogi(self, p, r):
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(st.TEKST_3, 24), 1.0))
        for a, b in self._drogi:
            p.drawLine(self._punkt(a), self._punkt(b))

    def _sciezka_trasy(self):
        trasa = self._dzien.trasa
        punkty = [(self._punkt(n).x(), self._punkt(n).y()) for n in trasa]
        return punkty

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

    def _rysuj_trase(self, p):
        punkty = self._sciezka_trasy()
        kolor = self._kolor_trasy()
        k = min(self.width(), self.height()) / 620.0     # grubości skalują się z oknem
        glowna = _sciezka_gladka(punkty[:-1], napiecie=1.0)      # bez powrotu do bazy
        powrot = self._luk_powrotu(punkty)                       # odcinek powrotny

        st.poswiata_linii(p, glowna, kolor,
                          warstwy=((34 * k, 12), (20 * k, 30), (9.5 * k, 105),
                                   (4.2 * k, 235)))
        # jasny rdzeń, jak na projekcie
        pen = QPen(st.z_alfa(QColor(228, 255, 255), 190), 1.7 * k)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen)
        p.drawPath(glowna)

        _kreskowana(p, powrot, st.ZIELEN,
                    warstwy=((18 * k, 22), (8 * k, 60), (3.0 * k, 215)),
                    kreska=11.0 * k, przerwa=8.0 * k)
        return [glowna, powrot]

    def _rysuj_miasta(self, p, czynny):
        dzien = self._dzien
        trasa = list(dzien.trasa) if czynny else []
        kolor = self._kolor_trasy()
        skala = min(self.width(), self.height())
        r_pkt = max(3.4, skala * 0.0085)

        # miasta poza trasą — ledwo widoczne punkciki, żeby mapa miała treść
        for nazwa in dn.MIASTA:
            if nazwa in trasa:
                continue
            s = self._punkt(nazwa)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(st.z_alfa(st.TEKST_3, 90)))
            p.drawEllipse(s, r_pkt * 0.42, r_pkt * 0.42)

        if not czynny:
            # sam teren: baza zaznaczona dyskretnie
            s = self._punkt(dn.BAZA)
            st.punkt_swiatla(p, s, r_pkt * 3.0, st.ZIELEN, 60)
            p.setPen(QPen(st.z_alfa(st.ZIELEN, 120), 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(s, r_pkt * 1.5, r_pkt * 1.5)
            return

        for nazwa in trasa[1:-1]:
            s = self._punkt(nazwa)
            st.punkt_swiatla(p, s, r_pkt * 3.4, kolor, 120)
            p.setPen(QPen(st.z_alfa(kolor, 255), 2.0))
            p.setBrush(QBrush(QColor(4, 12, 22, 235)))
            p.drawEllipse(s, r_pkt, r_pkt)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(st.z_alfa(QColor(240, 255, 255), 235)))
            p.drawEllipse(s, r_pkt * 0.30, r_pkt * 0.30)

        # baza: większa i jaśniejsza od reszty
        s = self._punkt(dn.BAZA)
        st.punkt_swiatla(p, s, r_pkt * 6.0, st.ZIELEN, 150)
        p.setPen(QPen(st.z_alfa(st.ZIELEN, 200), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(s, r_pkt * 2.1, r_pkt * 2.1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(st.z_alfa(st.ZIELEN, 235)))
        p.drawEllipse(s, r_pkt * 1.05, r_pkt * 1.05)
        p.setBrush(QBrush(QColor(4, 14, 22, 220)))
        p.drawEllipse(s, r_pkt * 0.34, r_pkt * 0.34)

    # — podpisy z unikaniem kolizji —
    def _rysuj_podpisy(self, p, czynny, sciezki_trasy):
        if not czynny:
            return
        dzien = self._dzien
        skala = min(self.width(), self.height())
        r_pkt = max(3.4, skala * 0.0085)

        # pozycje wszystkich miast liczymy raz — sprawdzanie kolizji jest gęste
        pozycje = {n: self._punkt(n) for n in dn.MIASTA}

        f_zwykly = st.czcionka(12, 500)
        f_baza = st.czcionka(14, 600)
        m_zwykly = QFontMetricsF(f_zwykly)
        m_baza = QFontMetricsF(f_baza)

        # próbki trasy — podpis nie powinien leżeć na linii
        probki = []
        for sciezka in sciezki_trasy:
            if sciezka is not None and sciezka.length() > 0:
                probki.extend(sciezka.pointAtPercent(i / 90.0) for i in range(91))
        probki.extend(pozycje[n] for n in dzien.trasa if n in pozycje)
        # nitka jest cienka, więc kolizja z nią kosztuje mniej niż z trasą
        nitka = self._sciezka_nitki()
        probki_nitki = ([nitka.pointAtPercent(i / 60.0) for i in range(61)]
                        if nitka is not None and nitka.length() > 0 else [])

        zajete = []
        etykiety = []

        kolejnosc = [dn.BAZA] + [n for n in dzien.trasa[1:-1]]
        for nazwa in kolejnosc:
            baza = (nazwa == dn.BAZA)
            napis = f"{nazwa} · start i powrót" if baza else nazwa
            m = m_baza if baza else m_zwykly
            szer = m.horizontalAdvance(napis)
            wys = m.height()
            srodek = pozycje[nazwa]
            odsun = r_pkt * (2.8 if baza else 2.0)

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
            for nr, (dx, dy) in enumerate(kandydaci):
                x = srodek.x() + dx
                y = srodek.y() + dy                     # linia bazowa tekstu
                pole = QRectF(x - 5, y - m.ascent() - 4, szer + 10, wys + 8)
                koszt = (nr % 8) * 5.0 + (nr // 8) * 26.0
                # wyjście poza widżet
                brzeg = QRectF(self.rect()).adjusted(12, 10, -12, -10)
                if not brzeg.contains(pole):
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
            etykiety.append((x, y, napis, baza))

        for (x, y, napis, baza) in etykiety:
            rozmiar, waga = (14, 600) if baza else (12, 500)
            _napis(p, x + 1, y + 1, napis, QColor(0, 0, 0, 170), rozmiar, waga)
            _napis(p, x, y, napis, st.TEKST, rozmiar, waga)

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

    def _rysuj_nitke(self, p):
        sciezka = self._sciezka_nitki()
        if sciezka is None:
            return
        dokad = sciezka.pointAtPercent(1.0)
        k = min(self.width(), self.height()) / 620.0
        _kreskowana(p, sciezka, self._kolor_trasy(),
                    warstwy=((14 * k, 18), (6 * k, 48), (2.0 * k, 185)),
                    kreska=10.0 * k, przerwa=7.5 * k)

        kolor = self._kolor_trasy()
        st.punkt_swiatla(p, dokad, 16, kolor, 130)
        p.setPen(QPen(st.z_alfa(kolor, 230), 2.0))
        p.setBrush(QBrush(QColor(4, 12, 22, 200)))
        p.drawEllipse(dokad, 5.0, 5.0)

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

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMinimumSize(260, 320)
        self._dzien = None
        self._numer = ""
        self._stan = "pusta"

    # — interfejs publiczny —
    def ustaw_dzien(self, dzien):
        self._dzien = dzien
        if dzien is not None and not self._numer:
            self._numer = f"{dzien.data.year}/{dzien.data.month:02d}/{dzien.data.day:02d}"
        self.update()

    def ustaw_numer(self, tekst):
        self._numer = str(tekst or "")
        self.update()

    def ustaw_stan(self, nazwa):
        self._stan = nazwa if nazwa in ("pusta", "zwykla", "podpisana") else "zwykla"
        self.update()

    def sizeHint(self):
        return QSize(360, 470)

    # — rysowanie —
    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect())

        margines = min(r.width(), r.height()) * 0.035
        kar = r.adjusted(margines, margines, -margines, -margines * 1.5)
        promien = max(6.0, kar.width() * 0.028)
        pusta = (self._stan == "pusta") or self._dzien is None or self._dzien.wolny

        st.cien(p, kar, promien, sila=190, rozmycie=26, przesun=10)

        sciezka = QPainterPath()
        sciezka.addRoundedRect(kar, promien, promien)
        g = QLinearGradient(kar.topLeft(), kar.bottomLeft())
        if pusta:
            g.setColorAt(0.0, QColor("#E8EAEE"))
            g.setColorAt(1.0, QColor("#DCDFE5"))
        else:
            g.setColorAt(0.0, QColor("#FFFFFF"))
            g.setColorAt(1.0, QColor("#F4F6F9"))
        p.fillPath(sciezka, QBrush(g))
        p.setPen(QPen(QColor(16, 24, 40, 30), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(sciezka)

        self._rysuj_tresc(p, kar, pusta)

        if self._stan == "podpisana" and not pusta:
            p.setPen(QPen(st.z_alfa(st.ZIELEN.darker(130), 210), 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(sciezka)
            self._rysuj_pieczatke(p, kar)
        p.end()

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

        y += 12 * s
        p.setPen(QPen(kreska_mocna, 1.2))
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
            f = st.czcionka(13 * s, 600)
            napis = "dzień wolny"
            szer = QFontMetricsF(f).horizontalAdvance(napis)
            _napis(p, kar.center().x() - szer / 2.0, srodek, napis, QColor("#98A2B3"), 13 * s, 600)
        else:
            self._rysuj_tabele(p, lewy, prawy, y, y_rubryki - 24 * s - zapas_pieczatki, s,
                               szary, ciemny, sredni, kreska_mocna, kreska_slaba)
            self._rysuj_rubryki_dolne(p, lewy, prawy, y_rubryki, s, szary, ciemny, sredni)

        # — linie podpisu —
        p.setPen(QPen(kreska_mocna, 1.0))
        szer_podpisu = (prawy - lewy) * 0.44
        p.drawLine(QPointF(lewy, y_linia_podpisu), QPointF(lewy + szer_podpisu, y_linia_podpisu))
        p.drawLine(QPointF(prawy - szer_podpisu, y_linia_podpisu), QPointF(prawy, y_linia_podpisu))
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
        _napis(p, prawy, y + 15 * s, dn.zl(kwota) + " zł", ciemny, 12 * s, 700, mono=True, prawy=True)

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
    okno = QWidget()
    okno.resize(980, 620)
    okno.setStyleSheet(f"background: {st.TLO_GORA.name()};")

    mapa = MapaDnia(okno)
    mapa.setGeometry(0, 0, 980, 620)

    kartka = KartkaDelegacji(okno)
    kartka.setGeometry(980 - 372 - 18, 16, 372, 528)

    dni = dn.oblicz_miesiac(1850)
    dzien = next((d for d in dni if not d.wolny), None)
    mapa.ustaw_dzien(dzien)
    mapa.ustaw_kotwice_kartki(QPointF(kartka.x() + 8, kartka.y() + 26))
    kartka.ustaw_dzien(dzien)
    kartka.ustaw_stan("zwykla")

    okno.show()
    app.processEvents()
    okno.grab().save("zrzut_mapa.png")
    print("zapisano zrzut_mapa.png")
