# -*- coding: utf-8 -*-
"""SPEKTAKL PRZY GENEROWANIU — historia miesiąca w jednym ujęciu.

Nakładka na mapę na czas pracy silnika, ciąg dalszy przelotu nad rejonem
(proto_mapa.PrzelotRejonu). Ten sam film, ta sama paralaksa i ten sam
zaczep INTRO_GENEROWANIA — inna choreografia:

    (1) noc         kamera wysoko nad rejonem; z wieczornego światła
                    mapy zostaje granatowa noc, świecą tylko osady
    (2) nitki       każdy dzień ułożony przez silnik to nitka światła,
                    która biegnie PO DROGACH rejonu od bazy przez
                    przystanki i z powrotem; gdy dobiega do miejscowości,
                    ta rozbłyskuje; kamera schodzi coraz niżej
    (3) kartki      każdy napisany dokument to kartka, która wylatuje
                    z trasy swoich dni i osiada na stosie u dołu mapy —
                    tam, gdzie zaraz wysunie się taca — z uderzeniem
                    pieczęci; kompas dostaje wtedy rozpęd
    (4) lądowanie   silnik skończył: nitki i kartki dochodzą do końca,
                    stos zjeżdża ku tacy, kamera osiada na widoku dnia,
                    kartka dnia wsuwa się jak zawsze

Pokaz CZYTA postęp silnika, nigdy odwrotnie: nitki i kartki ruszają, gdy
przyjdzie meldunek, a lądowanie — gdy silnik skończy; zanim skończy, pokaz
czeka (kamera waha się, osady świecą), nie zapętla efektów. Gdy silnik
skończy wcześniej, wszystko domyka się w czasie lądowania (< 1 s).
Esc przerywa (okno → przerwij), kliknięcie pomija (nakładka schodzi,
silnik pracuje dalej — zostaje postęp na kompasie).

Budżet klatki jak w przelocie: scena i osady upieczone RAZ na filmie,
gotowe trasy w drugiej pixmapie; co klatkę dochodzą tylko nitki w biegu
(prefiks łamanej), rozbłyski (dwa gradienty), kartki w locie i stos
(jedna mała pixmapa). Zamrożony zegar (``ustaw_chwile``) daje tę samą
klatkę za każdym razem — nitki i kartki są wtedy od razu na miejscu.
"""
import bisect
import math
import time

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (QPainter, QPainterPath, QPen, QBrush, QColor, QPixmap,
                         QLinearGradient, QRadialGradient)

import proto_styl as st
import proto_mapa as pm
from proto_mapa import (PrzelotRejonu, MapaDnia, RANGA_BAZA, RANGA_MIASTO, RANGA_WIES,
                        _gladko_2d, _poswiata_zmienna)

# ── choreografia ─────────────────────────────────────────────────────
NOC = QColor(92, 106, 152)       # mnożnik nocy dla całego filmu (composition Multiply)
NOC_NIEBO = QColor(8, 12, 30)    # niebo po zmroku — ponad horyzontem
BARWA_OSADY = QColor(255, 202, 132)      # ciepłe światło osad
PROMIEN_OSADY = {RANGA_BAZA: 8.0, RANGA_MIASTO: 4.2, RANGA_WIES: 2.4}     # jedn. świata
GWIAZD = 90                      # rzadkie, drobne — tylko nad horyzontem

CZAS_NITKI_MS = 1050             # nitka światła od bazy do bazy
NITEK_NARAZ = 2                  # więcej nitek w biegu to migotanie, nie choreografia
ODSTEP_NITEK_MS = 240            # najkrótsza przerwa między startami nitek
WARSTWY_NITKI = ((2.4, 40, 2), (1.0, 110, 1))      # ogon nitki tuż za głową
RDZEN_NITKI = ((0.22, 200, 1),)
# gotowa trasa na filmie: cieńsza i cichsza niż w przelocie — po ośmiu dniach
# rejon ma być siatką świateł, nie neonem; stempel dokumentu to sam jasny
# miętowy rdzeń NA cyjanowej poświacie, nie druga poświata
WARSTWY_TRASY = ((1.7, 14, 4), (0.8, 38, 2), (0.36, 110, 1))
RDZEN_TRASY = ((0.11, 170, 1),)
WARSTWY_STEMPLA = ((0.30, 90, 1),)
RDZEN_STEMPLA = ((0.13, 215, 1),)
PROMIEN_GLOWY = 4.2              # świecąca głowa nitki, jedn. świata
DLUGOSC_OGONA = 0.14             # jasny ogon za głową, ułamek długości trasy

CZAS_ROZBLYSKU_MS = 760          # miejscowość rozbłyskuje, gdy dobiegnie do niej światło
PROMIEN_ROZBLYSKU = 9.0          # jedn. świata, rośnie ×2,4
ROZBLYSKOW_NARAZ = 8             # więcej naraz to fajerwerki, nie rozbłyski

CZAS_KARTKI_MS = 640             # lot kartki z trasy na stos
CZAS_PIECZECI_MS = 420           # uderzenie pieczęci na stosie
KARTKA_SZER, KARTKA_WYS = 46.0, 62.0
STOS_ODSTEP = (5.0, -3.4)        # kolejna kartka na stosie: w prawo i w górę
STOS_MAX = 9                     # więcej kartek stos nie pokazuje osobno
ZBLIZENIE_POKAZU = 0.07          # kamera schodzi: powiększenie rośnie z postępem
CZAS_ZBLIZENIA_MS = 1400         # ...łagodnie, nie skokiem meldunków
ZJAZD_STOSU = 90.0               # px: stos zjeżdża ku tacy przy lądowaniu
CZAS_DOMYKANIA_MS = 380          # przy lądowaniu nitki i kartki kończą w tyle


class _NocDnia:
    """Atrapa dnia dla światła rejonu: późny wieczór (MapaDnia zna trzy pory
    dnia — „wieczor" zapala okna, resztę nocy dokłada _noc), pora roku z daty."""

    wolny = False
    start, koniec = "21:30", "22:30"

    def __init__(self, data=None):
        self.data = data


class SpektaklMiesiaca(PrzelotRejonu):
    """Przelot nad rejonem z choreografią spektaklu — patrz opis modułu.

    ``na_stempel`` to wywołanie zwrotne uderzenia pieczęci (okno rozpędza
    nim kompas); ``data`` daje porę roku nocy."""

    pominieto = pyqtSignal()        # kliknięcie: pokaz zszedł, silnik pracuje

    def __init__(self, rejon, mapa_pod=None, rodzic=None, na_stempel=None):
        super().__init__(rejon, mapa_pod=mapa_pod, rodzic=rodzic)
        self._na_stempel = na_stempel
        self._kolejka = []              # trasy czekające na swoją nitkę
        self._ostatni_start = -1e9      # chwila startu ostatniej nitki
        self._rozblyski = []            # [(punkt filmu, skala, chwila startu)]
        self._kartki = []               # kartki dokumentów: w locie i na stosie
        self._stos_pix = None           # gotowy stos (kartki, które już doleciały)
        self._stos_klucz = None
        self._stos_poz = QPointF(0.0, 0.0)
        self._dokumenty = 0             # ile dokumentów już zameldował silnik
        self._zoom_od = 0.0             # zbliżenie: od → do w CZAS_ZBLIZENIA_MS
        self._zoom_do = 0.0
        self._t_zoom = 0.0
        self._t_domykania = None        # chwila lądowania — od niej wszystko kończy w tyle
        self._pominiety = False
        self._pomiar_blokow = None      # słownik do pomiaru bloków klatki (paintEvent)

    @classmethod
    def nad_mapa(cls, mapa, miasta=None, baza=None, mapa_pod=None, rodzic=None,
                 data=None, na_stempel=None):
        """Jak PrzelotRejonu.nad_mapa, ale rejon stoi w wieczornym świetle."""
        rejon = MapaDnia()
        rejon.resize(mapa.size())
        rejon._ustaw_ziarno(mapa.ziarno())
        if miasta:
            rejon.ustaw_miasta(miasta, baza=baza)
        rejon._ustaw_swiatlo(_NocDnia(data))
        rejon.ustaw_animacje(False)
        pokaz = cls(rejon, mapa_pod=mapa_pod, rodzic=rodzic, na_stempel=na_stempel)
        pokaz.setGeometry(mapa.geometry())
        return pokaz

    # — odczyt —
    def kartki(self):
        """Ile kartek dokumentów wyleciało z mapy."""
        return len(self._kartki)

    def kartki_na_stosie(self):
        """Ile z nich już leży na stosie (doleciało)."""
        t = self._czas()
        return sum(1 for k in self._kartki if self._lot_kartki(k, t) >= 1.0)

    def nitki_w_biegu(self):
        return len(self._zapalane)

    def czeka_w_kolejce(self):
        return len(self._kolejka)

    def rozblyski(self):
        return len(self._rozblyski)

    def zblizenie(self):
        """Powiększenie kamery w tej chwili (bez lądowania)."""
        return self._zblizenie(self._czas())

    def pominiety(self):
        return self._pominiety

    # — sterowanie z okna —
    def ustaw_postep(self, t):
        byl = self._postep
        super().ustaw_postep(t)
        if abs(self._postep - byl) > 1e-6 and self._faza == "lot":
            teraz = self._czas()
            self._zoom_od = self._postep_gladki(teraz)
            self._zoom_do = self._postep
            self._t_zoom = teraz

    def dodaj_trase(self, punkty, data=None):
        """Jak w przelocie, ale trasa zapamiętuje też przebieg PO DROGACH
        rejonu (nazwy przystanków → sieć dróg mapy); dla nazw spoza rejonu
        odcinek idzie wprost, jak dotąd."""
        if self._faza == "koniec" or self._rejon is None:
            return False
        swiat = []
        for pkt in (punkty or ()):
            try:
                lat, lng = (pkt[-2], pkt[-1])
                xy = self._rejon.swiat_z_geo(lat, lng)
            except (TypeError, ValueError, IndexError):
                xy = None
            if xy is None:
                return False
            swiat.append(xy)
        if len(swiat) < 2:
            return False
        trasa = {"swiat": swiat, "data": data, "stempel": False, "pix": None,
                 "obrys": None, "punkty": None, "skale": None, "zapal": None,
                 "droga": self._po_drogach(punkty, swiat)}
        self._trasy.append(trasa)
        if self._scena is not None:
            self._zapal(trasa)
        return True

    def ustaw_dokumenty(self, ile, z_ilu):
        """Stemple jak w przelocie; każdy NOWY dokument to kartka z trasy."""
        try:
            nr = int(ile)
        except (TypeError, ValueError):
            return 0
        przed = [t["stempel"] for t in self._trasy]
        nowe = super().ustaw_dokumenty(ile, z_ilu)
        if nr <= self._dokumenty or self._faza == "koniec":
            return nowe
        swieze = [t for t, s in zip(self._trasy, przed) if t["stempel"] and not s]
        zrodlo = swieze[-1] if swieze else (self._trasy[-1] if self._trasy else None)
        for _ in range(nr - self._dokumenty):
            self._wypusc_kartke(zrodlo)
        self._dokumenty = nr
        self.update()
        return nowe

    def ustaw_chwile(self, sekundy):
        super().ustaw_chwile(sekundy)
        if self._chwila is not None:
            self._rusz_kolejke()
            self._rozblyski = []
            self._stos_pix = None
            self.update()

    def pomin(self):
        """Kliknięcie: pokaz schodzi od razu, silnik pracuje dalej."""
        if self._faza == "koniec":
            return
        self._pominiety = True
        self.pominieto.emit()
        self.przerwij()

    def mousePressEvent(self, zdarzenie):
        zdarzenie.accept()
        self.pomin()

    # — noc —
    def _upiecz(self):
        """Film przelotu, a na nim noc: mnożnik granatu na całą scenę, ciemne
        niebo z rzadkimi gwiazdami, ciepłe światło każdej osady — wszystko
        raz, do tej samej pixmapy. Trasy sprzed wypieku czekają w kolejce
        na swoje nitki zamiast wchodzić od razu."""
        czekajace = list(self._trasy)
        self._trasy = []
        try:
            super()._upiecz()
        finally:
            self._trasy = czekajace
        self._noc()
        for trasa in czekajace:
            trasa["punkty"] = None
            self._zapal(trasa)
        self._t_zoom = 0.0
        self._zoom_od = self._zoom_do = self._postep

    def _noc(self):
        scena, rzut, rejon = self._scena, self._rzut, self._rejon
        if scena is None or rejon is None:
            return
        W = self._film_w
        H = self._srodek_h
        q = QPainter(scena)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        q.fillRect(QRectF(0, 0, W, H), NOC)
        q.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        # niebo: nad horyzontem granat, przy horyzoncie zostaje łuna
        y_hor = self._horyzont_filmu()
        if y_hor > 2.0:
            g = QLinearGradient(0.0, 0.0, 0.0, y_hor)
            g.setColorAt(0.0, st.z_alfa(NOC_NIEBO, 235))
            g.setColorAt(0.72, st.z_alfa(NOC_NIEBO, 150))
            g.setColorAt(1.0, st.z_alfa(NOC_NIEBO, 0))
            q.fillRect(QRectF(0, 0, W, y_hor), QBrush(g))
            q.setPen(Qt.PenStyle.NoPen)
            for i in range(GWIAZD):
                hx = pm._hasz("gwiazda", i, 1)
                hy = pm._hasz("gwiazda", i, 2)
                hj = pm._hasz("gwiazda", i, 3)
                x = hx * W
                y = hy * hy * y_hor * 0.82
                r = 0.55 + 0.75 * hj
                q.setBrush(QBrush(QColor(226, 232, 255, int(70 + 150 * hj * (1.0 - y / max(1.0, y_hor))))))
                q.drawEllipse(QPointF(x, y), r, r)
        # osady: ciepłe światło — im większa miejscowość, tym szerzej
        odn = rejon._odniesienie()
        for nazwa in rejon._nazwy():
            x, y = rejon._miasta[nazwa]
            ranga = rejon._rangi.get(nazwa, RANGA_MIASTO)
            pt, s = rzut.rzutuj(x, y, rejon._wysokosc(x, y))
            if pt.x() < -60 or pt.x() > W + 60 or pt.y() < -60 or pt.y() > H + 60:
                continue
            prom = PROMIEN_OSADY.get(ranga, PROMIEN_OSADY[RANGA_WIES]) * s * odn
            st.punkt_swiatla(q, pt, prom * 2.6, BARWA_OSADY, 34)
            st.punkt_swiatla(q, pt, prom, BARWA_OSADY, 130)
            st.punkt_swiatla(q, pt, prom * 0.4, QColor(255, 244, 222), 210)
        q.end()

    def _horyzont_filmu(self):
        """Wiersz filmu, od którego w dół jest grunt (nad nim niebo)."""
        rzut = self._rzut
        for y in range(0, int(self._srodek_h), 3):
            gx, gy = rzut.na_grunt(self._film_w * 0.5, float(y), dal_max=2600.0)
            if rzut.glebokosc(gx, gy, 0.0) < 2400.0:
                return float(y)
        return 0.0

    # — nitki po drogach —
    def _po_drogach(self, punkty, swiat):
        """Łamana świata od bazy przez przystanki do bazy, po sieci dróg rejonu.

        Przystanek z nazwą znaną mapie jedzie drogami (Dijkstra mapy —
        MapaDnia._po_drogach), reszta wprost. Końce każdego odcinka to
        DOKŁADNIE punkty trasy z ``swiat`` — nitka zaczyna i kończy tam,
        gdzie trasa przelotu."""
        rejon = self._rejon
        nazwy = []
        for pkt in (punkty or ()):
            nazwa = pkt[0] if len(pkt) >= 3 else None
            nazwy.append(nazwa if nazwa in rejon._miasta else None)
        droga = [swiat[0]]
        for i in range(1, len(swiat)):
            a, b = nazwy[i - 1], nazwy[i]
            if a is not None and b is not None and a != b:
                po = rejon._po_drogach(a, b)
                for j in range(1, len(po)):
                    odcinek = rejon._droga_miedzy(po[j - 1], po[j])
                    if odcinek is None:
                        droga.append(rejon._miasta[po[j]])
                        continue
                    droga.extend(tuple(p) for p in odcinek[1:-1])
                    droga.append(rejon._miasta[po[j]])
                droga[-1] = swiat[i]
            else:
                droga.append(swiat[i])
        return droga

    def _upiecz_trase(self, trasa):
        """Jak w przelocie, ale linia biegnie po drogach (``droga``), a
        przystanki zostają przystankami trasy. Do tego miary nitki:
        skumulowana długość (0…1) każdego punktu i miejsca przystanków."""
        rejon, rzut = self._rejon, self._rzut
        wznios = rejon._wznios_trasy
        odn = rejon._odniesienie()
        droga = trasa.get("droga") or trasa["swiat"]
        gesto = 2 if trasa.get("droga") else 6
        punkty, skale = [], []
        for (x, y) in _gladko_2d(droga, na_odcinek=gesto):
            pt, s = rzut.rzutuj(x, y, rejon._wysokosc(x, y) + wznios)
            punkty.append(pt)
            skale.append(s * odn)
        film = QRectF(0, 0, self._film_w, self._srodek_h)
        xs = [p.x() for p in punkty]
        ys = [p.y() for p in punkty]
        z = pm.ZAPAS_OBRYSU_TRASY
        obrys = QRectF(min(xs) - z, min(ys) - z, max(xs) - min(xs) + 2 * z,
                       max(ys) - min(ys) + 2 * z).intersected(film)
        obrys = QRectF(math.floor(obrys.x()), math.floor(obrys.y()),
                       math.ceil(obrys.width()) + 1, math.ceil(obrys.height()) + 1)
        kolor = pm.BARWA_DOKUMENTU_PRZELOTU if trasa["stempel"] else pm.BARWA_TRASY_PRZELOTU
        pix = pm._pixmapa_urzadzenia(obrys.width(), obrys.height(), self._scena.devicePixelRatio())
        q = QPainter(pix)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.translate(-obrys.x(), -obrys.y())
        if trasa["stempel"]:
            _poswiata_zmienna(q, punkty, skale, kolor, WARSTWY_STEMPLA)
            _poswiata_zmienna(q, punkty, skale, QColor(240, 255, 250), RDZEN_STEMPLA)
        else:
            _poswiata_zmienna(q, punkty, skale, kolor, WARSTWY_TRASY)
            _poswiata_zmienna(q, punkty, skale, QColor(232, 255, 255), RDZEN_TRASY)
        przystanki = []
        for (x, y) in trasa["swiat"][1:-1]:
            pt, s = rzut.rzutuj(x, y, rejon._wysokosc(x, y) + wznios)
            st.punkt_swiatla(q, pt, pm.PROMIEN_PRZYSTANKU_PRZELOTU * s * odn, kolor,
                             90 if trasa["stempel"] else 120)
            przystanki.append((pt, s * odn))
        q.end()
        trasa["pix"], trasa["obrys"] = pix, obrys
        trasa["punkty"], trasa["skale"] = punkty, skale
        # miary nitki
        dlug = [0.0]
        for i in range(1, len(punkty)):
            dlug.append(dlug[-1] + math.hypot(punkty[i].x() - punkty[i - 1].x(),
                                              punkty[i].y() - punkty[i - 1].y()))
        calk = dlug[-1] or 1.0
        trasa["dlug"] = [d / calk for d in dlug]
        # przystanek → ułamek długości, w którym nitka do niego dobiega
        miejsca = []
        for pt, s in przystanki:
            i = min(range(len(punkty)), key=lambda k: (punkty[k].x() - pt.x()) ** 2
                    + (punkty[k].y() - pt.y()) ** 2)
            miejsca.append((trasa["dlug"][i], pt, s))
        miejsca.append((1.0, punkty[-1], skale[-1]))           # powrót do bazy
        trasa["przystanki"] = miejsca
        trasa["rozblysnieto"] = trasa.get("rozblysnieto", 0)

    def _zapal(self, trasa, od_razu=False):
        """Trasa czeka na swoją nitkę: naraz biegną najwyżej NITEK_NARAZ,
        w odstępach — inaczej z ośmiu dni zrobiłoby się osiem błysków naraz."""
        if od_razu or not self._anim or self._chwila is not None:
            super()._zapal(trasa, od_razu=True)
            return
        self._kolejka.append(trasa)
        self._rusz_kolejke()

    def _rusz_kolejke(self):
        if self._scena is None or self._faza == "koniec":
            return
        if self._chwila is not None:             # zamrożony zegar: od razu na miejscu
            while self._kolejka:
                PrzelotRejonu._zapal(self, self._kolejka.pop(0), od_razu=True)
            return
        teraz = self._czas()
        while self._kolejka and len(self._zapalane) < NITEK_NARAZ \
                and (teraz - self._ostatni_start) * 1000.0 >= ODSTEP_NITEK_MS:
            trasa = self._kolejka.pop(0)
            self._ostatni_start = teraz
            self._upiecz_trase(trasa)
            czas = CZAS_NITKI_MS
            if self._t_domykania is not None:
                czas = CZAS_DOMYKANIA_MS
            zapal = st.Plynnie(0.0, czas=czas, krzywa="liniowa",
                               rodzic=self, klatka=pm.KLATKA_PRZELOTU)
            trasa["zapal"] = zapal
            zapal.koniec.connect(lambda t=trasa: self._po_rozblysku(t))
            self._zapalane.append(trasa)
            zapal.do(1.0)
            self.update()

    def _po_rozblysku(self, trasa):
        self._odpal_rozblyski(trasa, 1.0)
        trasa["odslona"] = None
        super()._po_rozblysku(trasa)
        self._rusz_kolejke()

    def _odpal_rozblyski(self, trasa, z):
        """Miejscowości, do których nitka już dobiegła, rozbłyskują — raz."""
        miejsca = trasa.get("przystanki") or ()
        teraz = self._czas()
        ile = trasa.get("rozblysnieto", 0)
        while ile < len(miejsca) and miejsca[ile][0] <= z:
            _u, pt, s = miejsca[ile]
            ile += 1
            trasa["rozblysnieto"] = ile
            if self._chwila is None:
                self._rozblyski.append((pt, s, teraz))

    # — kartki dokumentów —
    def _srodek_trasy(self, trasa):
        """Środek ciężkości trasy na filmie — stąd wylatuje kartka."""
        if trasa is not None and trasa.get("punkty"):
            pkt = trasa["punkty"]
            return QPointF(sum(p.x() for p in pkt) / len(pkt), sum(p.y() for p in pkt) / len(pkt))
        if trasa is not None and self._rzut is not None and self._rejon is not None:
            pkt = [self._rzut.ekran(x, y, self._rejon._wysokosc(x, y)) for (x, y) in trasa["swiat"]]
            return QPointF(sum(p.x() for p in pkt) / len(pkt), sum(p.y() for p in pkt) / len(pkt))
        return QPointF(self._zapas_px + self._srodek_w * 0.5, self._srodek_h * 0.55)

    def _wypusc_kartke(self, trasa):
        nr = len(self._kartki)
        kartka = {"zrodlo": self._srodek_trasy(trasa), "nr": nr, "start": self._czas(),
                  "kat": (pm._hasz("kartka", nr, 1) - 0.5) * 34.0,
                  "wzlot": 0.55 + 0.35 * pm._hasz("kartka", nr, 2),
                  "czas": CZAS_KARTKI_MS if self._t_domykania is None else CZAS_DOMYKANIA_MS,
                  "pieczec": None}
        if self._chwila is not None or self._scena is None:
            kartka["start"] = -1e9           # zamrożony zegar: od razu na stosie
            kartka["pieczec"] = False
        self._kartki.append(kartka)

    def _lot_kartki(self, kartka, t):
        """0…1 lotu kartki w chwili t."""
        return max(0.0, min(1.0, (t - kartka["start"]) * 1000.0 / float(kartka["czas"])))

    def _miejsce_stosu(self, r, nr):
        i = min(nr, STOS_MAX)
        return QPointF(r.center().x() + i * STOS_ODSTEP[0],
                       r.bottom() - KARTKA_WYS * 0.5 - 22.0 + i * STOS_ODSTEP[1])

    def _uderzenie(self, kartka):
        """Kartka doleciała — pieczęć: raz, bez względu na liczbę klatek."""
        if kartka["pieczec"] is None:
            kartka["pieczec"] = True
            if self._na_stempel is not None:
                try:
                    self._na_stempel()
                except Exception:
                    pass

    # — lądowanie i koniec —
    def _laduj(self):
        """Silnik skończył: kolejka rusza cała naraz w tyle, kartki w locie
        dolatują w tyle — a lądowanie idzie jak w przelocie."""
        if self._faza in ("ladowanie", "koniec"):
            return
        teraz = self._czas()
        self._t_domykania = teraz
        self._ostatni_start = -1e9
        for trasa in self._zapalane:
            if trasa["zapal"] is not None and not trasa["zapal"].gotowe():
                zostalo = max(0.0, 1.0 - trasa["zapal"].teraz())
                trasa["zapal"].zatrzymaj()
                trasa["zapal"].do(1.0, czas=max(40, int(CZAS_DOMYKANIA_MS * zostalo)))
        while self._kolejka and self._chwila is None and self._scena is not None:
            trasa = self._kolejka.pop(0)
            self._upiecz_trase(trasa)
            zapal = st.Plynnie(0.0, czas=CZAS_DOMYKANIA_MS, krzywa="liniowa",
                               rodzic=self, klatka=pm.KLATKA_PRZELOTU)
            trasa["zapal"] = zapal
            zapal.koniec.connect(lambda t=trasa: self._po_rozblysku(t))
            self._zapalane.append(trasa)
            zapal.do(1.0)
        for kartka in self._kartki:
            u = self._lot_kartki(kartka, teraz)
            if u < 1.0:
                kartka["czas"] = max(40.0, CZAS_DOMYKANIA_MS * (1.0 - u))
                kartka["start"] = teraz - u * kartka["czas"] / 1000.0
        super()._laduj()

    def przerwij(self):
        self._kolejka = []
        self._rozblyski = []
        super().przerwij()

    def _sprzatnij(self):
        self._stos_pix = None
        self._kartki = []
        super()._sprzatnij()

    # — klatka —
    def _tik(self):
        if self._scena is None:
            self._upiecz()
        if self._faza == "lot":
            self._rusz_kolejke()
        self.update()

    def _postep_gladki(self, t):
        """Postęp silnika wygładzony w czasie — kamera nie skacze z meldunkami."""
        u = max(0.0, min(1.0, (t - self._t_zoom) * 1000.0 / CZAS_ZBLIZENIA_MS))
        return self._zoom_od + (self._zoom_do - self._zoom_od) * st.KRZYWE["lagodna"](u)

    def _zblizenie(self, t):
        postep = max(0.0, min(1.0, self._postep_gladki(t)))
        return 1.0 + ZBLIZENIE_POKAZU * st.KRZYWE["lagodna"](postep)

    def _na_ekran(self, pt, r, dx, powiekszenie):
        """Punkt filmu → punkt widżetu, tą samą kamerą co ``_kamera``."""
        sw = r.width() / float(max(1, self._srodek_w))
        sh = r.height() / float(max(1, self._srodek_h))
        x = pt.x() - self._zapas_px - dx * (self._a + self._b * pt.y())
        return QPointF(r.center().x() + (x - self._srodek_w * 0.5) * sw * powiekszenie,
                       r.center().y() + (pt.y() - self._srodek_h * 0.5) * sh * powiekszenie)

    def paintEvent(self, _zdarzenie):
        zegar = time.perf_counter()
        bloki = self._pomiar_blokow          # None, albo słownik nazwa → [ms, …]
        znak = [zegar]

        def odhacz(nazwa):
            if bloki is not None:
                teraz = time.perf_counter()
                bloki.setdefault(nazwa, []).append((teraz - znak[0]) * 1000.0)
                znak[0] = teraz
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        r = QRectF(self.rect())
        if self._scena is None:
            self._rysuj_start(p, r, 1.0, 1.0)
            p.end()
            return
        t = self._czas()
        dx = self._przesuniecie_w(t)
        u = self._zejscie.teraz() if self._faza == "ladowanie" else 0.0
        alfa = 1.0 - u
        zoom = self._zblizenie(t) * (1.0 + (pm.POWIEKSZENIE_LADOWANIA - 1.0) * u)
        if self._pod is not None and u > 0.0:
            p.drawPixmap(r, self._pod, QRectF(self._pod.rect()))
        p.save()
        self._kamera(p, r, dx, zoom)
        p.setOpacity(alfa)
        p.drawPixmap(0, 0, self._scena)
        odhacz("scena")
        # trasy i nitki to miękkie poświaty: pod ścinaniem wolno je próbkować
        # bez wygładzania (0,8 ms zamiast 4 ms na pełny film) — scena nie,
        # bo cienkie drogi zaczęłyby drgać. Wygładzanie krawędzi włączamy
        # dopiero do kształtów: z nim drawPixmap pod ścinaniem idzie przez
        # wypełnianie ścieżki teksturą i kosztuje kilka razy więcej.
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        if self._trasy_pix is not None:
            p.drawPixmap(0, 0, self._trasy_pix)
        odhacz("trasy")
        for trasa in self._zapalane:
            self._rysuj_nitke(p, trasa, alfa)
        odhacz("nitki")
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._rysuj_rozblyski(p, t, alfa)
        odhacz("rozblyski")
        p.restore()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.setOpacity(alfa)
        wyk = self._rejon._wykonczenie()
        p.drawPixmap(r, wyk, QRectF(wyk.rect()))
        odhacz("wykonczenie")
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._rysuj_kartki(p, r, t, dx, zoom, alfa, u)
        odhacz("kartki")
        p.setOpacity(1.0)
        e = self._wejscie.teraz()
        if e < 0.999:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            self._rysuj_start(p, r, 1.0 - e, 1.0 + (pm.POWIEKSZENIE_STARTU - 1.0) * e)
            odhacz("start")
        p.end()
        odhacz("koniec")
        self._odnotuj_klatke((time.perf_counter() - zegar) * 1000.0)

    def _rysuj_nitke(self, p, trasa, alfa):
        """Nitka w biegu: odsłonięty prefiks upieczonej trasy, jasny ogon i głowa.

        Odsłona to pixmapa w obrysie trasy, do której co klatkę KOPIUJEMY
        z gotowej trasy tylko prostokąty świeżo przebytych odcinków
        (composition Source — kopia, nie nakładanie, więc powtórki nic nie
        rozjaśniają). Klatka płaci za jedno małe drawPixmap, kilkanaście
        punktów ogona i dwa gradienty głowy — nie za całą łamaną."""
        z = max(0.0, min(1.0, trasa["zapal"].teraz()))
        punkty, skale, dlug = trasa["punkty"], trasa["skale"], trasa.get("dlug")
        if not punkty or not dlug or trasa["pix"] is None:
            return
        self._odpal_rozblyski(trasa, z)
        i = bisect.bisect_right(dlug, z) - 1
        i = max(0, min(len(punkty) - 2, i))
        w = (z - dlug[i]) / (dlug[i + 1] - dlug[i]) if dlug[i + 1] > dlug[i] else 0.0
        glowa = QPointF(punkty[i].x() + (punkty[i + 1].x() - punkty[i].x()) * w,
                        punkty[i].y() + (punkty[i + 1].y() - punkty[i].y()) * w)
        s_glowy = skale[i] + (skale[i + 1] - skale[i]) * w
        odslona = trasa.get("odslona")
        if odslona is None or odslona[2] is not trasa["pix"]:
            pix = QPixmap(trasa["pix"].size())
            pix.setDevicePixelRatio(trasa["pix"].devicePixelRatio())
            pix.fill(Qt.GlobalColor.transparent)
            odslona = [pix, 0, trasa["pix"]]
            trasa["odslona"] = odslona
        if i > odslona[1] or (i == 0 and odslona[1] == 0):
            obrys = trasa["obrys"]
            q = QPainter(odslona[0])
            q.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            for k in range(odslona[1], i):
                a_, b_ = punkty[k], punkty[k + 1]
                zapas = 3.2 * max(skale[k], skale[k + 1]) + 2.0
                pole = QRectF(min(a_.x(), b_.x()) - zapas - obrys.x(), min(a_.y(), b_.y()) - zapas - obrys.y(),
                              abs(b_.x() - a_.x()) + 2 * zapas, abs(b_.y() - a_.y()) + 2 * zapas)
                q.drawPixmap(pole, trasa["pix"], pm._zrodlo_blitu(trasa["pix"], pole))
            q.end()
            odslona[1] = i
        kolor = pm.BARWA_DOKUMENTU_PRZELOTU if trasa["stempel"] else pm.BARWA_TRASY_PRZELOTU
        p.setOpacity(alfa)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.drawPixmap(trasa["obrys"].topLeft(), odslona[0])
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # ogon: jaśniejszy, krótki odcinek tuż za głową — JEDNA ścieżka na
        # warstwę (grubość ze skali głowy; na kilkunastu punktach różnica
        # głębi jest niewidoczna, a sto osobnych linii kosztowało 3 ms)
        j = bisect.bisect_left(dlug, z - DLUGOSC_OGONA)
        j = max(0, min(i, j))
        sciezka = QPainterPath(punkty[j])
        for pt in punkty[j + 1:i + 1]:
            sciezka.lineTo(pt)
        sciezka.lineTo(glowa)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for szer, alfa, _krok in WARSTWY_NITKI:
            pen = QPen(st.z_alfa(kolor, alfa), max(0.7, szer * s_glowy))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawPath(sciezka)
        pen = QPen(st.z_alfa(QColor(236, 255, 255), RDZEN_NITKI[0][1]), max(0.7, RDZEN_NITKI[0][0] * s_glowy))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(sciezka)
        st.punkt_swiatla(p, glowa, PROMIEN_GLOWY * s_glowy, kolor, 120)
        st.punkt_swiatla(p, glowa, 1.5 * s_glowy, QColor(240, 255, 255), 200)

    def _rysuj_rozblyski(self, p, t, alfa):
        """Rozbłysk miejscowości: jeden gradient (biały rdzeń → ciepło → nic)."""
        zywe = []
        p.setPen(Qt.PenStyle.NoPen)
        for (pt, s, t0) in self._rozblyski:
            u = (t - t0) * 1000.0 / CZAS_ROZBLYSKU_MS
            if u >= 1.0:
                continue
            zywe.append((pt, s, t0))
            u = max(0.0, u)
            prom = PROMIEN_ROZBLYSKU * s * (0.6 + 1.8 * st.KRZYWE["wyjscie"](u))
            gasn = (1.0 - u) ** 1.6
            rg = QRadialGradient(pt, prom)
            rg.setColorAt(0.0, st.z_alfa(QColor(255, 246, 226), int(210 * gasn)))
            rg.setColorAt(0.28, st.z_alfa(BARWA_OSADY, int(150 * gasn)))
            rg.setColorAt(1.0, st.z_alfa(BARWA_OSADY, 0))
            p.setBrush(QBrush(rg))
            p.drawEllipse(pt, prom, prom)
        self._rozblyski = zywe[-ROZBLYSKOW_NARAZ:]
        p.setOpacity(alfa)

    def _rysuj_kartki(self, p, r, t, dx, zoom, alfa, u_lad):
        """Kartki w locie i stos; przy lądowaniu stos zjeżdża ku tacy."""
        if not self._kartki:
            return
        zjazd = ZJAZD_STOSU * st.KRZYWE["wejscie"](u_lad)
        na_stosie = []
        w_locie = []
        for kartka in self._kartki:
            u = self._lot_kartki(kartka, t)
            if u >= 1.0:
                if kartka["pieczec"] is None:
                    self._uderzenie(kartka)
                na_stosie.append(kartka)
            else:
                w_locie.append((kartka, u))
        # stos: gotowa pixmapa (bez pieczęci w ruchu)
        klucz = (len(na_stosie), self.width(), self.height(), round(self.devicePixelRatioF(), 3))
        if self._stos_pix is None or self._stos_klucz != klucz:
            self._stos_pix, self._stos_poz = self._upiecz_stos(r, len(na_stosie))
            self._stos_klucz = klucz
        if self._stos_pix is not None:
            p.setOpacity(alfa)
            p.drawPixmap(QPointF(self._stos_poz.x(), self._stos_poz.y() + zjazd), self._stos_pix)
        # uderzenia pieczęci na wierzchu stosu
        for kartka in na_stosie:
            if not kartka["pieczec"]:
                continue
            wiek = (t - kartka["start"]) * 1000.0 - kartka["czas"]
            if 0.0 <= wiek < CZAS_PIECZECI_MS:
                v = wiek / CZAS_PIECZECI_MS
                srodek = self._miejsce_stosu(r, kartka["nr"])
                srodek = QPointF(srodek.x(), srodek.y() + zjazd)
                p.setOpacity(alfa * (1.0 - v) ** 1.4)
                st.punkt_swiatla(p, srodek, 26.0 + 58.0 * st.KRZYWE["wyjscie"](v), st.MIETA, 130)
                p.setOpacity(alfa * (1.0 - v))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(st.z_alfa(st.MIETA, 220), 2.2 - 1.6 * v))
                prom = KARTKA_SZER * 0.55 + 42.0 * st.KRZYWE["wyjscie"](v)
                p.drawEllipse(srodek, prom, prom * 0.72)
        # kartki w locie: z trasy, łukiem w górę, na stos
        for kartka, u in w_locie:
            a = self._na_ekran(kartka["zrodlo"], r, dx, zoom)
            b = self._miejsce_stosu(r, kartka["nr"])
            b = QPointF(b.x(), b.y() + zjazd)
            wzlot = QPointF((a.x() + b.x()) * 0.5, min(a.y(), b.y()) - r.height() * 0.22 * kartka["wzlot"])
            e = st.KRZYWE["lagodna"](u)
            m = 1.0 - e
            x = m * m * a.x() + 2 * m * e * wzlot.x() + e * e * b.x()
            y = m * m * a.y() + 2 * m * e * wzlot.y() + e * e * b.y()
            skala = 0.30 + 0.70 * st.KRZYWE["wyjscie"](u)
            kat = kartka["kat"] * (1.0 - e)
            p.setOpacity(alfa * min(1.0, 0.25 + 3.0 * u))
            p.save()
            p.translate(x, y)
            p.rotate(kat)
            p.scale(skala, skala)
            pix = self._pixmapa_kartki(ze_stemplem=False)
            p.drawPixmap(QPointF(-pix.width() * 0.5 / pix.devicePixelRatio(),
                                 -pix.height() * 0.5 / pix.devicePixelRatio()), pix)
            p.restore()
            if u > 0.2:
                # światło z trasy ciągnie się za kartką
                p.setOpacity(alfa * (1.0 - u) * 0.8)
                st.punkt_swiatla(p, QPointF(x, y), 22.0 * (1.0 - u) + 8.0, pm.BARWA_DOKUMENTU_PRZELOTU, 110)
        p.setOpacity(alfa)

    def _upiecz_stos(self, r, ile):
        """Stos w JEDNEJ małej pixmapie (obrys kartek z zapasem na cień)."""
        if ile <= 0:
            return None, QPointF(0.0, 0.0)
        a = self._miejsce_stosu(r, 0)
        b = self._miejsce_stosu(r, min(ile - 1, STOS_MAX))
        pole = QRectF(min(a.x(), b.x()) - KARTKA_SZER * 0.5 - 24.0,
                      min(a.y(), b.y()) - KARTKA_WYS * 0.5 - 12.0,
                      abs(b.x() - a.x()) + KARTKA_SZER + 48.0,
                      abs(b.y() - a.y()) + KARTKA_WYS + 44.0)
        pix = pm._pixmapa_urzadzenia(pole.width(), pole.height(), self.devicePixelRatioF())
        q = QPainter(pix)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.translate(-pole.x(), -pole.y())
        for nr in range(min(ile, STOS_MAX + 1)):
            self._rysuj_kartke(q, self._miejsce_stosu(r, nr), ze_stemplem=True, cien=1.0)
        q.end()
        return pix, pole.topLeft()

    _KARTKI_PIX = {}

    @classmethod
    def _pixmapa_kartki(cls, ze_stemplem):
        """Kartka w locie: raz upieczona (w podwójnej rozdzielczości, bo leci
        obrócona i pomniejszona), potem jedno drawPixmap na klatkę."""
        pix = cls._KARTKI_PIX.get(bool(ze_stemplem))
        if pix is None:
            zapas = 18.0
            szer, wys = KARTKA_SZER + 2 * zapas, KARTKA_WYS + 2 * zapas
            pix = QPixmap(int(szer * 2), int(wys * 2))
            pix.setDevicePixelRatio(2.0)
            pix.fill(Qt.GlobalColor.transparent)
            q = QPainter(pix)
            q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            cls._rysuj_kartke(q, QPointF(szer * 0.5, wys * 0.5), ze_stemplem=ze_stemplem, cien=1.6)
            q.end()
            cls._KARTKI_PIX[bool(ze_stemplem)] = pix
        return pix

    @staticmethod
    def _rysuj_kartke(p, srodek, ze_stemplem, cien=1.0):
        """Kartka dokumentu: papier z paru wierszami druku i pieczęcią."""
        kar = QRectF(srodek.x() - KARTKA_SZER * 0.5, srodek.y() - KARTKA_WYS * 0.5,
                     KARTKA_SZER, KARTKA_WYS)
        sciezka = QPainterPath()
        sciezka.addRoundedRect(kar, 3.0, 3.0)
        p.setPen(Qt.PenStyle.NoPen)
        for i, (przes, alfa) in enumerate(((2.0, 70), (6.0, 40), (12.0, 22))):
            c = QPainterPath()
            c.addRoundedRect(kar.translated(0.0, przes * cien).adjusted(-i * 1.5, -i * 1.0, i * 1.5, i * 2.0), 4.0, 4.0)
            p.fillPath(c, QBrush(QColor(0, 0, 0, alfa)))
        g = QLinearGradient(kar.topLeft(), kar.bottomRight())
        g.setColorAt(0.0, QColor(255, 253, 246))
        g.setColorAt(1.0, QColor(232, 228, 216))
        p.fillPath(sciezka, QBrush(g))
        p.setPen(QPen(QColor(120, 128, 140, 110), 1.0))
        x0, x1 = kar.left() + 7.0, kar.right() - 7.0
        y = kar.top() + 11.0
        for i, dl in enumerate((0.55, 0.9, 0.75, 0.85, 0.6)):
            p.drawLine(QPointF(x0, y), QPointF(x0 + (x1 - x0) * dl, y))
            y += 6.5
        p.setPen(QPen(QColor(40, 48, 62, 160), 1.6))
        p.drawLine(QPointF(x0, kar.top() + 5.0), QPointF(x0 + 16.0, kar.top() + 5.0))
        if ze_stemplem:
            p.save()
            p.translate(kar.center().x(), kar.bottom() - 12.0)
            p.rotate(-7.0)
            pole = QRectF(-15.0, -5.5, 30.0, 11.0)
            s = QPainterPath()
            s.addRoundedRect(pole, 2.5, 2.5)
            p.fillPath(s, QBrush(st.z_alfa(st.ZIELEN, 44)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(st.z_alfa(st.ZIELEN.darker(120), 220), 1.3))
            p.drawPath(s)
            p.setPen(QPen(st.z_alfa(st.ZIELEN.darker(120), 150), 0.8))
            p.drawLine(QPointF(-9.0, 0.0), QPointF(9.0, 0.0))
            p.restore()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(20, 26, 38, 70), 1.0))
        p.drawPath(sciezka)
