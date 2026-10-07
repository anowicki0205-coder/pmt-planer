# -*- coding: utf-8 -*-
"""Kompas — przycisk „Generuj dokumenty” w prototypie nowego wyglądu PMT Planera.

Przycisk jest rysowany jak fizyczny przyrząd, a nie jak płaskie kółko:
chromowany pierścień zewnętrzny (gradient stożkowy), ciemna oprawa z cieniem
wewnętrznym, szklana soczewka z refleksem, dwanaście kresek podziałki, igła
z dwóch trójkątów i łuk postępu biegnący wokół soczewki od północy zgodnie
z ruchem wskazówek zegara.

Wszystkie ruchy chodzą na jednym zegarze Qt (bez dodatkowych bibliotek) i dają
się zatrzymać metodą ``zatrzymaj_animacje()`` — dzięki temu zrzuty ekranu są
powtarzalne, a okno zamyka się bez wiszących zegarów.

Tor postępu mówi jednym językiem w każdym stanie: część przebyta to pełny łuk
w barwie stanu z rampą jasności, część pozostała to widoczny rowek z drobną
podziałką, a między nimi stoi CZOŁO — poprzeczka w poprzek rowka z punktem
światła, dokładnie w miejscu, w którym praca stanęła. Odznaka stanu (ptaszek,
krzyżyk, wykrzyknik, strzałka nawrotu) siada OBOK czoła, żeby go nie zasłonić.
"""
import math
import time

from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QFontMetricsF, QLinearGradient,
                         QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient)
from PyQt6.QtWidgets import QAbstractButton, QApplication, QWidget

from proto_styl import (BLAD, BURSZTYN, CYJAN, MIETA, TEKST, TEKST_2, TEKST_3, ZIELEN,
                        cien, czcionka, punkt_swiatla, szklo, tlo_sceny, z_alfa)

# ── stałe elementu ───────────────────────────────────────────────────
STANY = ("nieaktywny", "gotowy", "praca", "sukces", "blad", "ostrzezenie", "zmieniono")

_POSTEP_STANU = {"nieaktywny": 0.0, "gotowy": 0.0, "praca": 0.35, "sukces": 1.0,
                 "blad": 0.68, "ostrzezenie": 0.66, "zmieniono": 0.0}

_IGLA_POLNOC = {"nieaktywny": QColor("#8D9DB4"), "gotowy": CYJAN, "praca": CYJAN,
                "sukces": ZIELEN, "blad": BLAD, "ostrzezenie": ZIELEN, "zmieniono": CYJAN}

_IGLA_POLUDNIE = QColor("#63748F")
_CIEMNY = QColor("#0A1220")          # dno soczewki i tło znaczników

_OKRES_MS = 33                        # jeden zegar dla całego elementu (~30 kl./s)

# proporcje tarczy względem promienia zewnętrznego
_CHROM_WEW = 0.845                    # wewnętrzna krawędź chromu
_TOR_R = 0.752                        # środek toru postępu
_TOR_GRUBOSC = 0.104                  # grubość toru
_SOCZEWKA = 0.663                     # promień szkła
_KRESKI_ZEW = 0.600                   # zewnętrzny koniec kresek podziałki
_RADELKO = 104                        # liczba prążków radełka na pierścieniu
# rozpęd igły w stanie „praca": tempo meldunków silnika na stopnie/sekundę
OBROT_START = 90.0                    # od tyla rusza, zanim przyjdzie drugi meldunek
OBROT_MIN = 18.0                      # przy zupełnym zastoju igła ledwo pełznie
OBROT_MAX = 400.0                     # szybciej już nie — dalej to migotanie
OBROT_NA_TEMPO = 1400.0               # ułamek postępu na sekundę → stopnie/sekundę
OBROT_OPADANIE = 0.972                # bez nowego meldunku rozpęd sam opada
_BLYSK_MS = 560.0                     # jak długo gaśnie błysk pierścienia po sukcesie


def _mieszaj(a, b, t):
    """Liniowe przejście między dwiema barwami."""
    t = max(0.0, min(1.0, float(t)))
    return QColor(int(a.red() + (b.red() - a.red()) * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


_OPISY = {}


def _opis(klucz):
    """Podpisy liczone raz, z danych przykładowych, żeby nie kłamały."""
    if not _OPISY:
        dni, kwota = 6, "1 850"
        try:
            import proto_dane as dane
            p = dane.podsumowanie(dane.oblicz_miesiac(1850))
            dni = p["dni"]
            kwota = dane.zl(p["kwota"], grosze=False)
        except Exception:
            pass
        _OPISY["gotowy"] = "%d dni · %s zł · realne drogi" % (dni, kwota)
        _OPISY["sukces"] = "%d dni · 2 dokumenty · %s zł" % (dni, kwota)
        _OPISY["ostrzezenie"] = "1 236 zł z %s zł" % kwota
        _OPISY["ostrzezenie_glowny"] = "4 z %d dni" % dni
    return _OPISY.get(klucz, "")


def _podpisy_stanu(stan, etap, postep):
    """Domyślna para podpisów dla stanu — zgodna z arkuszem stanów."""
    if stan == "nieaktywny":
        return "Uzupełnij kwotę", "brak kwoty"
    if stan == "gotowy":
        return "Generuj", _opis("gotowy")
    if stan == "praca":
        nazwa = etap or "Pracuję"
        return nazwa, "postęp %d %%" % round(postep * 100)
    if stan == "sukces":
        return "Otwórz dokumenty", _opis("sukces")
    if stan == "blad":
        # jedna linia: to podpis przycisku, nie zdanie — powód idzie do drugiej
        return "Przerwane", "brak adresu · %d %%" % round(postep * 100)
    if stan == "ostrzezenie":
        return _opis("ostrzezenie_glowny"), _opis("ostrzezenie")
    if stan == "zmieniono":
        return "Dane się zmieniły", "poprzednie: 14:02"
    return "", ""


_PODPOWIEDZI = {
    "nieaktywny": "Uzupełnij: kwota, dni",
    "gotowy": "Generuj dokumenty",
    "praca": "Trwa generowanie…",
    "sukces": "Otwórz folder z dokumentami",
    "blad": "Generowanie przerwane — spróbuj ponownie",
    "ostrzezenie": "Kwota starczyła na część dni",
    "zmieniono": "Dane się zmieniły — generuj ponownie",
}

# Druga linia zawsze w barwie stanu, tylko ciszej. Szary TEKST_3 pod czerwonym
# albo bursztynowym kompasem gubił się w tle — podpis musi być czytelny w KAŻDYM
# stanie, bo to jedyne miejsce, gdzie stoi liczba.
_BARWY_PODPISU = {
    "nieaktywny": (TEKST_2, z_alfa(TEKST_3, 225)),
    "gotowy": (TEKST, MIETA),
    "praca": (TEKST, z_alfa(CYJAN, 200)),
    "sukces": (MIETA, z_alfa(MIETA, 190)),
    "blad": (BLAD, z_alfa(BLAD, 195)),
    "ostrzezenie": (BURSZTYN, z_alfa(BURSZTYN, 205)),
    "zmieniono": (TEKST, z_alfa(CYJAN, 185)),
}


class Kompas(QAbstractButton):
    """Okrągły przycisk generowania dokumentów w postaci kompasu."""

    uruchom = pyqtSignal()      # klik w stanie 'gotowy' albo 'zmieniono'
    otworz = pyqtSignal()       # klik w stanie 'sukces'

    def __init__(self, rodzic=None, srednica=120):
        super().__init__(rodzic)
        self._srednica = int(srednica)
        self._stan = "gotowy"
        self._postep = _POSTEP_STANU["gotowy"]
        self._etap = ""
        self._podpis = None
        self._podpis_dodatkowy = None
        self._azymut_cel = 0.0
        self._azymut_biez = 0.0
        self._azymut_v = 0.0
        self._blysk = 0.0
        self._faza = 0
        self._anim = True
        self._odcisk_klatki = None      # co widać z ruchomych części — patrz _tik
        self._obrot = 0.0               # ile stopni na sekundę kręci się igła
        self._obrot_cel = 0.0
        self._postep_czas = None        # kiedy przyszedł ostatni meldunek postępu
        self._pod_mysza = False
        self._obwodka = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(120, 58)
        self.clicked.connect(self._na_klik)

        self.setToolTip(_PODPOWIEDZI.get(self._stan, ""))

        self._zegar = QTimer(self)
        self._zegar.setInterval(_OKRES_MS)
        self._zegar.timeout.connect(self._tik)
        self._zegar.start()

    # ── wielkość ─────────────────────────────────────────────────────
    def sizeHint(self):
        wys = int(self._srednica * 1.14) + 4
        if self._tresc_podpisu():
            wys += 24
        if self._tresc_podpisu_dodatkowego():
            wys += 18
        return QSize(int(self._srednica * 1.5), wys)

    def minimumSizeHint(self):
        return QSize(90, 70)

    # ── publiczne ustawienia ─────────────────────────────────────────
    def stan(self):
        return self._stan

    def ustaw_stan(self, nazwa):
        """Przełącza stan przycisku; nieznana nazwa jest ignorowana."""
        if nazwa not in STANY or nazwa == self._stan:
            return
        self._stan = nazwa
        self._postep = _POSTEP_STANU[nazwa]
        if nazwa == "praca":
            self._postep_czas = None
            self._obrot_cel = OBROT_START if self._anim else 0.0
        else:
            self._obrot_cel = 0.0
            if not self._anim:
                self._obrot = 0.0
        # błysk pierścienia leci raz, zaraz po przejściu w sukces
        self._blysk = 1.0 if (nazwa == "sukces" and self._anim) else 0.0
        if nazwa in ("gotowy", "sukces", "ostrzezenie", "zmieniono"):
            self._azymut_cel = 0.0
            if not self._anim:
                self._azymut_biez = 0.0
        self.setCursor(Qt.CursorShape.BusyCursor if nazwa == "praca"
                       else Qt.CursorShape.PointingHandCursor)
        self.setToolTip(_PODPOWIEDZI.get(nazwa, ""))
        self.updateGeometry()
        self.update()

    def postep(self):
        return self._postep

    def ustaw_postep(self, wartosc):
        """Wypełnienie łuku w zakresie 0…1."""
        try:
            w = float(wartosc)
        except (TypeError, ValueError):
            w = 0.0
        w = max(0.0, min(1.0, w))
        if abs(w - self._postep) > 1e-4:
            self._rozpedz(w - self._postep)
            self._postep = w
            self.update()

    # ── rozpęd igły: ile pracy silnik zrobił w ostatniej chwili ──────
    def _rozpedz(self, przyrost):
        """Igła kręci się tym szybciej, im szybciej silnik melduje postęp.

        To nie jest ozdoba: gdy silnik czeka na sieć, meldunki przestają
        przychodzić i igła zwalnia niemal do zera. Widać więc, czy praca
        idzie, czy stoi — bez ani jednego zdania na ekranie.
        """
        if self._stan != "praca" or przyrost <= 0.0:
            return
        teraz = time.monotonic()
        poprz, self._postep_czas = self._postep_czas, teraz
        if poprz is None:
            self._obrot_cel = OBROT_START
            return
        odstep = max(0.02, teraz - poprz)
        tempo = przyrost / odstep                  # ułamek postępu na sekundę
        self._obrot_cel = max(OBROT_MIN, min(OBROT_MAX, tempo * OBROT_NA_TEMPO))

    def impuls(self, sila=OBROT_MAX):
        """Rozpęd z zewnątrz: uderzenie pieczęci na pokazie generowania.

        Tylko w pracy — igła skacze do ``sila`` stopni na sekundę i opada
        jak po meldunku (OBROT_OPADANIE), więc bez pokazu nic się nie zmienia."""
        if self._stan != "praca":
            return False
        self._obrot_cel = max(self._obrot_cel, max(OBROT_MIN, min(OBROT_MAX, float(sila))))
        return True

    def etap(self):
        return self._etap

    def ustaw_etap(self, napis):
        """Nazwa bieżącego etapu — trafia do podpisu w stanie 'praca'."""
        napis = "" if napis is None else str(napis)
        if napis != self._etap:
            self._etap = napis
            self.update()

    def azymut(self):
        return self._azymut_cel

    def ustaw_azymut(self, stopnie=None):
        """Obraca igłę na zadany azymut; bez wartości igła wraca na północ."""
        self._azymut_cel = 0.0 if stopnie is None else float(stopnie) % 360.0
        if not self._anim:
            self._azymut_biez = self._azymut_cel
            self._azymut_v = 0.0
        self.update()

    def ustaw_podpis(self, napis=None):
        """Podpis pod kompasem; None przywraca podpis domyślny dla stanu."""
        self._podpis = napis
        self.updateGeometry()
        self.update()

    def ustaw_podpis_dodatkowy(self, napis=None):
        """Drugi, mniejszy wiersz podpisu; None przywraca domyślny."""
        self._podpis_dodatkowy = napis
        self.updateGeometry()
        self.update()

    # ── animacje ─────────────────────────────────────────────────────
    def zatrzymaj_animacje(self):
        """Zatrzymuje zegar i ustawia ruchome części w powtarzalnym położeniu."""
        self._anim = False
        self._zegar.stop()
        self._faza = 0
        self._blysk = 0.0
        self._azymut_v = 0.0
        self._obrot = 0.0
        self._obrot_cel = 0.0
        self._odcisk_klatki = None
        self._azymut_biez = self._azymut_cel
        self.update()

    def wznow_animacje(self):
        self._anim = True
        if not self._zegar.isActive():
            self._zegar.start()
        self.update()

    def animacje_chodza(self):
        return bool(self._anim and self._zegar.isActive())

    # ── obsługa zdarzeń ──────────────────────────────────────────────
    def _tik(self):
        self._faza = (self._faza + _OKRES_MS) % 240000
        if self._blysk > 0.0:
            self._blysk = max(0.0, self._blysk - _OKRES_MS / _BLYSK_MS)
        if self._stan == "praca":
            # bez nowego meldunku rozpęd opada, ale igła nigdy nie staje
            self._obrot_cel = max(OBROT_MIN, self._obrot_cel * OBROT_OPADANIE)
        else:
            self._obrot_cel = 0.0
        if self._obrot > 0.02 or self._obrot_cel > 0.0:
            self._obrot += (self._obrot_cel - self._obrot) * 0.18
            if self._obrot <= 0.02:
                self._obrot = 0.0
            self._azymut_biez = (self._azymut_biez
                                 + self._obrot * _OKRES_MS / 1000.0) % 360.0
            self._azymut_v = 0.0
        else:
            # igła dochodzi do azymutu jak w prawdziwym przyrządzie: lekko
            # przestrzela i się uspokaja, zamiast przeskakiwać
            roznica = ((self._azymut_cel - self._azymut_biez + 180.0) % 360.0) - 180.0
            if abs(roznica) > 0.04 or abs(self._azymut_v) > 0.04:
                self._azymut_v = (self._azymut_v + roznica * 0.075) * 0.80
                self._azymut_biez = (self._azymut_biez + self._azymut_v) % 360.0
            else:
                self._azymut_v = 0.0
                self._azymut_biez = self._azymut_cel
        odcisk = self._odcisk()
        if odcisk != self._odcisk_klatki:
            self._odcisk_klatki = odcisk
            self.update()

    # próg widoczności: o tyle musi się ruszyć część kompasu, żeby warto
    # było przerysować całe 6 ms klatki. Poniżej tego nie zmienia się ani
    # jeden piksel, który oko byłoby w stanie zauważyć.
    KROK_ODDECHU = 1.0 / 26.0
    KROK_IGLY = 0.4                 # stopnie

    def _odcisk(self):
        """Ruchome części TEGO stanu, zaokrąglone do progu widoczności.

        Kompas rysuje się ponad 6 ms, a w spoczynku oddycha po jednym
        poziomie jasności na kilka klatek. Klatka bez różnicy w tej krotce
        nie zmieniłaby na ekranie niczego, więc jej nie rysujemy.
        """
        stan = self._stan
        czesci = [round(self._blysk * 64.0),
                  round(self._kat_igly() / self.KROK_IGLY),
                  bool(self._pod_mysza), bool(self._obwodka)]
        if stan == "gotowy":
            czesci.append(round(self._oddech(4000) / self.KROK_ODDECHU))
        elif stan == "zmieniono":
            czesci.append(round(self._oddech(2200) / self.KROK_ODDECHU))
            czesci.append(round(self._oddech(1600) / self.KROK_ODDECHU))
        elif stan == "praca":
            czesci.append(round(self._oddech(900) / self.KROK_ODDECHU))
        return tuple(czesci)

    def obrot_igly(self):
        """Ile stopni na sekundę kręci się igła — 0 poza pracą i na zrzutach."""
        return self._obrot

    def _na_klik(self):
        if self._stan in ("gotowy", "zmieniono"):
            self.uruchom.emit()
        elif self._stan == "sukces":
            self.otworz.emit()

    def enterEvent(self, zdarzenie):
        self._pod_mysza = True
        self.update()
        super().enterEvent(zdarzenie)

    def leaveEvent(self, zdarzenie):
        self._pod_mysza = False
        self.update()
        super().leaveEvent(zdarzenie)

    def focusInEvent(self, zdarzenie):
        self._obwodka = zdarzenie.reason() in (Qt.FocusReason.TabFocusReason,
                                               Qt.FocusReason.BacktabFocusReason,
                                               Qt.FocusReason.ShortcutFocusReason)
        super().focusInEvent(zdarzenie)

    def focusOutEvent(self, zdarzenie):
        self._obwodka = False
        super().focusOutEvent(zdarzenie)

    def hideEvent(self, zdarzenie):
        self._zegar.stop()
        super().hideEvent(zdarzenie)

    def showEvent(self, zdarzenie):
        if self._anim and not self._zegar.isActive():
            self._zegar.start()
        super().showEvent(zdarzenie)

    # ── pomocnicze ───────────────────────────────────────────────────
    def _tresc_podpisu(self):
        if self._podpis is not None:
            return self._podpis
        return _podpisy_stanu(self._stan, self._etap, self._postep)[0]

    def _tresc_podpisu_dodatkowego(self):
        if self._podpis_dodatkowy is not None:
            return self._podpis_dodatkowy
        return _podpisy_stanu(self._stan, self._etap, self._postep)[1]

    def _oddech(self, okres_ms):
        if not self._anim:
            return 0.5
        return 0.5 + 0.5 * math.sin(self._faza / float(okres_ms) * 2.0 * math.pi)

    def _kat_igly(self):
        if self._stan == "nieaktywny":
            return 158.0 + (3.0 * math.sin(self._faza / 6000.0 * 2.0 * math.pi)
                            if self._anim else 0.0)
        kat = self._azymut_biez
        if self._stan == "blad" and self._anim:
            kat += 7.0 * math.sin(self._faza / 55.0)
        return kat

    @staticmethod
    def _luk(srodek, promien, kat_start, rozpietosc):
        prost = QRectF(srodek.x() - promien, srodek.y() - promien, promien * 2.0, promien * 2.0)
        s = QPainterPath()
        s.arcMoveTo(prost, kat_start)
        s.arcTo(prost, kat_start, rozpietosc)
        return s

    @staticmethod
    def _na_obwodzie(srodek, promien, kat_zegarowy):
        rad = math.radians(kat_zegarowy - 90.0)
        return QPointF(srodek.x() + promien * math.cos(rad),
                       srodek.y() + promien * math.sin(rad))

    # ── rysowanie ────────────────────────────────────────────────────
    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        r = QRectF(self.rect())
        podpis = self._tresc_podpisu()
        podpis2 = self._tresc_podpisu_dodatkowego()
        szer_tekstu = max(40.0, r.width() - 10.0)
        # jeden wiersz mniejszą czcionką czyta się lepiej niż dwa wiersze większą
        czcionka_podpisu = czcionka(14, 650, naglowek=True)
        wiersze = 0
        wys_wiersza = 18.0
        if podpis:
            for rozmiar in (14, 13, 12):
                f = czcionka(rozmiar, 650, naglowek=True)
                if QFontMetricsF(f).horizontalAdvance(podpis) <= szer_tekstu:
                    czcionka_podpisu, wiersze = f, 1
                    wys_wiersza = rozmiar + 4.0
                    break
            else:
                czcionka_podpisu = czcionka(13, 650, naglowek=True)
                wiersze, wys_wiersza = 2, 17.0
        self._wys_wiersza = wys_wiersza
        wys_podpisu = (5.0 + wiersze * wys_wiersza) if podpis else 0.0
        wys_podpisu2 = 17.0 if podpis2 else 0.0
        miejsce = wys_podpisu + wys_podpisu2

        # tarcza z zapasem na poświatę, żeby nie obcinała się o brzeg kontrolki
        d = min(r.width() / 1.16, (r.height() - miejsce) / 1.10)
        d = max(46.0, min(d, float(self._srednica) * 1.30))
        gora = r.y() + max(0.0, (r.height() - miejsce - d * 1.05) / 2.0) + d * 0.05
        srodek = QPointF(r.center().x(), gora + d / 2.0)

        p.save()
        if self.isDown():
            p.translate(srodek)
            p.scale(0.972, 0.972)
            p.translate(-srodek.x(), -srodek.y())
        self._rysuj_kompas(p, srodek, d / 2.0)
        p.restore()

        if podpis or podpis2:
            self._rysuj_podpisy(p, r, gora + d, podpis, podpis2, wiersze,
                                czcionka_podpisu, szer_tekstu)

    def _rysuj_kompas(self, p, srodek, R):
        barwa = self._barwa_stanu()
        self._rysuj_cien_pod(p, srodek, R)
        self._rysuj_poswiate_zewnetrzna(p, srodek, R, barwa)
        self._rysuj_chrom(p, srodek, R)
        self._rysuj_oprawe(p, srodek, R)
        self._rysuj_soczewke(p, srodek, R, barwa)
        self._rysuj_podzialke(p, srodek, R)
        self._rysuj_tor(p, srodek, R)
        self._rysuj_igle(p, srodek, R)
        self._rysuj_szklo(p, srodek, R)
        self._rysuj_znaczniki(p, srodek, R)
        self._rysuj_blysk(p, srodek, R, barwa)
        if self._obwodka:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(z_alfa(CYJAN, 150), 1.4, Qt.PenStyle.DashLine))
            p.drawEllipse(srodek, R + 3.5, R + 3.5)

    def _rysuj_blysk(self, p, srodek, R, barwa):
        """Jeden błysk pierścienia zaraz po wejściu w sukces — potem gaśnie."""
        b = self._blysk
        if b <= 0.0:
            return
        t = 1.0 - b                       # 0 → 1 w miarę gaśnięcia
        p.setBrush(Qt.BrushStyle.NoBrush)
        # fala rozchodząca się na zewnątrz oprawy
        zasieg = R * (1.0 + 0.20 * t)
        p.setPen(QPen(z_alfa(barwa, int(170 * b * b)), R * 0.055 * (1.0 - 0.55 * t)))
        p.drawEllipse(srodek, zasieg, zasieg)
        # chrom łapie światło na całym obwodzie
        p.setPen(QPen(z_alfa(QColor("#FFFFFF"), int(150 * b)), R * 0.022))
        p.drawEllipse(srodek, R - R * 0.030, R - R * 0.030)
        # i odbija się na szkle
        r = R * _SOCZEWKA
        p.setPen(QPen(z_alfa(_mieszaj(barwa, QColor("#FFFFFF"), 0.6), int(110 * b)),
                      R * 0.016))
        p.drawEllipse(srodek, r - 1.0, r - 1.0)

    def _barwa_stanu(self):
        return {"nieaktywny": QColor("#6A7A92"), "gotowy": CYJAN, "praca": CYJAN,
                "sukces": ZIELEN, "blad": BLAD, "ostrzezenie": BURSZTYN,
                "zmieniono": CYJAN}[self._stan]

    def _rysuj_cien_pod(self, p, srodek, R):
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(6, 0, -1):
            p.setBrush(z_alfa(QColor(0, 0, 0), int(18 * (i / 6.0) ** 0.6)))
            p.drawEllipse(QPointF(srodek.x(), srodek.y() + R * 0.075),
                          R + i * R * 0.022, R + i * R * 0.020)

    def _rysuj_poswiate_zewnetrzna(self, p, srodek, R, barwa):
        if self._stan == "nieaktywny" and not self._pod_mysza:
            return
        sila = 46.0
        if self._stan == "gotowy":
            sila = 36.0 + 44.0 * self._oddech(4000)
        elif self._stan == "sukces":
            sila = 72.0
        elif self._stan == "zmieniono":
            sila = 32.0 + 26.0 * self._oddech(2200)
        elif self._stan == "nieaktywny":
            sila = 20.0
        if self._pod_mysza:
            sila += 26.0
        zasieg = R * 1.16
        rg = QRadialGradient(srodek, zasieg)
        rg.setColorAt(0.80, z_alfa(barwa, 0))
        rg.setColorAt(0.885, z_alfa(barwa, int(sila)))
        rg.setColorAt(0.94, z_alfa(barwa, int(sila * 0.45)))
        rg.setColorAt(1.0, z_alfa(barwa, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(rg))
        p.drawEllipse(srodek, zasieg, zasieg)

    def _rysuj_chrom(self, p, srodek, R):
        """Chromowany pierścień: gradient stożkowy plus ostre krawędzie."""
        r_wew = R * _CHROM_WEW
        pierscien = QPainterPath()
        pierscien.addEllipse(srodek, R, R)
        dziura = QPainterPath()
        dziura.addEllipse(srodek, r_wew, r_wew)
        pierscien = pierscien.subtracted(dziura)

        g = QConicalGradient(srodek, 0.0)
        # stal, nie szare tworzywo: ciemne pasy są głębsze, jasne cieplejsze,
        # a przejścia między nimi krótkie — od tego metal robi się twardy
        przystanki = [(0.000, "#8A9AAC"), (0.045, "#2E3845"), (0.120, "#151C25"),
                      (0.215, "#78889B"), (0.310, "#EDF4FC"), (0.372, "#FFFFFF"),
                      (0.428, "#D6E1EE"), (0.515, "#66758A"), (0.620, "#151D27"),
                      (0.695, "#414D5B"), (0.795, "#C8D5E4"), (0.870, "#FDFEFF"),
                      (0.938, "#A2B0C2"), (1.000, "#8A9AAC")]
        for poz, barwa in przystanki:
            k = QColor(barwa)
            if self._pod_mysza:
                k = k.lighter(110)
            g.setColorAt(poz, k)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(pierscien, QBrush(g))

        self._radelko(p, srodek, R, r_wew, pierscien)

        # pionowe przyciemnienie — metal ma górę i dół
        cieniowanie = QLinearGradient(QPointF(srodek.x(), srodek.y() - R),
                                      QPointF(srodek.x(), srodek.y() + R))
        cieniowanie.setColorAt(0.0, QColor(255, 255, 255, 22))
        cieniowanie.setColorAt(0.45, QColor(0, 0, 0, 0))
        cieniowanie.setColorAt(1.0, QColor(0, 0, 0, 82))
        p.fillPath(pierscien, QBrush(cieniowanie))

        # ostre krawędzie: jasna u góry z zewnątrz, ciemna u dołu
        p.setBrush(Qt.BrushStyle.NoBrush)
        krawedz = QLinearGradient(QPointF(srodek.x(), srodek.y() - R),
                                  QPointF(srodek.x(), srodek.y() + R))
        krawedz.setColorAt(0.0, QColor(255, 255, 255, 215))
        krawedz.setColorAt(0.5, QColor(255, 255, 255, 45))
        krawedz.setColorAt(1.0, QColor(0, 0, 0, 170))
        p.setPen(QPen(QBrush(krawedz), 1.1))
        p.drawEllipse(srodek, R - 0.55, R - 0.55)

        # druga, cieńsza krawędź światła — fazka tuż pod obrzeżem
        fazka = QLinearGradient(QPointF(srodek.x(), srodek.y() - R),
                                QPointF(srodek.x(), srodek.y() + R))
        fazka.setColorAt(0.00, QColor(255, 255, 255, 150))
        fazka.setColorAt(0.30, QColor(255, 255, 255, 46))
        fazka.setColorAt(0.62, QColor(0, 0, 0, 40))
        fazka.setColorAt(1.00, QColor(255, 255, 255, 96))   # odbite światło od dołu
        p.setPen(QPen(QBrush(fazka), 0.9))
        p.drawEllipse(srodek, R - R * 0.052, R - R * 0.052)

        wewn = QLinearGradient(QPointF(srodek.x(), srodek.y() - r_wew),
                               QPointF(srodek.x(), srodek.y() + r_wew))
        wewn.setColorAt(0.0, QColor(0, 0, 0, 180))
        wewn.setColorAt(1.0, QColor(255, 255, 255, 130))
        p.setPen(QPen(QBrush(wewn), 1.0))
        p.drawEllipse(srodek, r_wew + 0.5, r_wew + 0.5)
        # wewnętrzna fazka: cienka nitka światła po stronie soczewki
        p.setPen(QPen(QColor(255, 255, 255, 34), 0.8))
        p.drawEllipse(srodek, r_wew + R * 0.036, r_wew + R * 0.036)

        # styk z tłem: metal nie kończy się w powietrzu, rzuca cienką kreskę cienia
        p.setPen(QPen(QColor(0, 0, 0, 96), max(0.9, R * 0.014)))
        p.drawEllipse(srodek, R + R * 0.010, R + R * 0.010)

    def _radelko(self, p, srodek, R, r_wew, pierscien):
        """Prążkowanie radełka: dwie ścieżki kresek — jasne i ciemne — na raz."""
        if R < 26.0:
            return
        jasne, ciemne = QPainterPath(), QPainterPath()
        r1, r2 = R * 0.995, r_wew + (R - r_wew) * 0.06
        for i in range(_RADELKO):
            kat = math.radians(i * 360.0 / _RADELKO)
            dx, dy = math.cos(kat), math.sin(kat)
            sciezka = jasne if (i % 2 == 0) else ciemne
            sciezka.moveTo(srodek.x() + dx * r2, srodek.y() + dy * r2)
            sciezka.lineTo(srodek.x() + dx * r1, srodek.y() + dy * r1)
        p.save()
        p.setClipPath(pierscien)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # kreska szeroka na pół podziałki — prążki stykają się bokami i dają
        # frez radełka, a nie szprychy
        szer = max(0.8, 2.0 * math.pi * R / _RADELKO * 0.52)
        p.setPen(QPen(QColor(255, 255, 255, 26), szer))
        p.drawPath(jasne)
        p.setPen(QPen(QColor(0, 0, 0, 42), szer))
        p.drawPath(ciemne)
        p.restore()

    def _rysuj_oprawe(self, p, srodek, R):
        """Ciemna oprawa pod chromem, z cieniem wewnętrznym."""
        r_zew = R * _CHROM_WEW
        p.setPen(Qt.PenStyle.NoPen)
        g = QLinearGradient(QPointF(srodek.x(), srodek.y() - r_zew),
                            QPointF(srodek.x(), srodek.y() + r_zew))
        g.setColorAt(0.0, QColor("#0C1421"))
        g.setColorAt(1.0, QColor("#141F32"))
        p.setBrush(QBrush(g))
        p.drawEllipse(srodek, r_zew, r_zew)

        rg = QRadialGradient(srodek, r_zew)
        rg.setColorAt(0.55, QColor(0, 0, 0, 0))
        rg.setColorAt(0.86, QColor(0, 0, 0, 120))
        rg.setColorAt(1.0, QColor(0, 0, 0, 200))
        p.setBrush(QBrush(rg))
        p.drawEllipse(srodek, r_zew, r_zew)

    def _rysuj_soczewke(self, p, srodek, R, barwa):
        r = R * _SOCZEWKA
        p.setPen(Qt.PenStyle.NoPen)
        g = QRadialGradient(QPointF(srodek.x() - r * 0.25, srodek.y() - r * 0.32), r * 1.7)
        g.setColorAt(0.0, QColor("#1E2E4A"))
        g.setColorAt(0.55, QColor("#131D30"))
        g.setColorAt(1.0, _CIEMNY)
        p.setBrush(QBrush(g))
        p.drawEllipse(srodek, r, r)

        if self._stan != "nieaktywny":
            sila = 34
            if self._stan == "gotowy":
                sila = 22 + int(20 * self._oddech(4000))
            elif self._stan == "sukces":
                sila = 50
            poswiata = QRadialGradient(srodek, r)
            poswiata.setColorAt(0.0, z_alfa(barwa, 0))
            poswiata.setColorAt(0.70, z_alfa(barwa, int(sila * 0.30)))
            poswiata.setColorAt(1.0, z_alfa(barwa, sila))
            p.setBrush(QBrush(poswiata))
            p.drawEllipse(srodek, r, r)

        # cień wewnętrzny od oprawy — światło pada z góry
        p.save()
        sc = QPainterPath()
        sc.addEllipse(srodek, r, r)
        p.setClipPath(sc)
        cien_g = QLinearGradient(QPointF(srodek.x(), srodek.y() - r),
                                 QPointF(srodek.x(), srodek.y() + r * 0.10))
        cien_g.setColorAt(0.0, QColor(0, 0, 0, 96))
        cien_g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillPath(sc, QBrush(cien_g))
        # szkło gęstnieje przy krawędzi — tarcza wchodzi w cień pierścienia
        gestosc = QRadialGradient(srodek, r)
        gestosc.setColorAt(0.00, QColor(0, 0, 0, 0))
        gestosc.setColorAt(0.62, QColor(0, 0, 0, 18))
        gestosc.setColorAt(0.88, QColor(0, 0, 0, 74))
        gestosc.setColorAt(1.00, QColor(0, 0, 0, 130))
        p.fillPath(sc, QBrush(gestosc))
        p.restore()

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(z_alfa(QColor(255, 255, 255), 30), 1.0))
        p.drawEllipse(srodek, r - 0.5, r - 0.5)

    def _rysuj_podzialke(self, p, srodek, R):
        """Dwanaście kresek co 30°, strony świata dłuższe i jaśniejsze."""
        wygaszone = self._stan == "nieaktywny"
        # cienkie obręcze, między którymi siedzą kreski — tarcza jest toczona
        p.setBrush(Qt.BrushStyle.NoBrush)
        for prom, alfa in ((_KRESKI_ZEW + 0.012, 22 if not wygaszone else 14),
                           (_KRESKI_ZEW - 0.118, 13 if not wygaszone else 9)):
            p.setPen(QPen(z_alfa(QColor("#CCD8E8"), alfa), max(0.6, R * 0.008)))
            p.drawEllipse(srodek, R * prom, R * prom)
        p.save()
        p.translate(srodek)
        for i in range(12):
            glowna = (i % 3) == 0
            dl = R * (0.105 if glowna else 0.068)
            zew = R * _KRESKI_ZEW
            szer = R * (0.044 if glowna else 0.028)
            alfa = (180 if glowna else 112) if not wygaszone else (125 if glowna else 78)
            p.save()
            p.rotate(i * 30.0)
            pen = QPen(z_alfa(QColor("#CCD8E8"), alfa), szer)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawLine(QPointF(0, -zew), QPointF(0, -zew + dl))
            p.restore()
        p.restore()

    @staticmethod
    def _pioro_poswiaty(barwa, szerokosc):
        """Pióro poświaty z płaskim zakończeniem — łuk nie dostaje wypustki na starcie."""
        pen = QPen(barwa, szerokosc)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        return pen

    def _rampa_luku(self, p, srodek, r_tor, grubosc, sciezka, postep, moc=96):
        """Jasność wzdłuż łuku: ogon przygaszony, czoło rozświetlone."""
        rampa = QConicalGradient(srodek, 90.0)
        poz = max(0.001, min(0.999, 1.0 - postep))
        rampa.setColorAt(0.0, z_alfa(QColor("#FFFFFF"), 0))
        if poz > 0.02:
            rampa.setColorAt(max(0.0, poz - 0.02), z_alfa(QColor("#FFFFFF"), int(moc * 0.78)))
        rampa.setColorAt(poz, z_alfa(QColor("#FFFFFF"), moc))
        rampa.setColorAt(min(1.0, poz + 0.001), z_alfa(QColor("#FFFFFF"), 0))
        rampa.setColorAt(1.0, z_alfa(QColor("#FFFFFF"), 0))
        pen = QPen(QBrush(rampa), grubosc * 0.48)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.drawPath(sciezka)

    def _czolo_luku(self, p, srodek, r_tor, grubosc, kat, barwa, zywe=True, puls=1.0):
        """Czoło łuku: poprzeczka w rowku, jasny rdzeń i punkt światła.

        Wszystkie stany z niepełnym łukiem kończą się tak samo — po tym widać,
        gdzie dokładnie zatrzymała się praca, a nie tylko ile jej zostało.
        """
        punkt = self._na_obwodzie(srodek, r_tor, kat)
        jasna = _mieszaj(barwa, QColor("#FFFFFF"), 0.55)
        if zywe:
            ogon = self._luk(srodek, r_tor, 90.0 - kat + 13.0, -13.0)
            pen = QPen(jasna, grubosc)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawPath(ogon)
        # poprzeczka: cienka kreska w poprzek rowka, dokładnie na czole
        rad = math.radians(kat - 90.0)
        dx, dy = math.cos(rad), math.sin(rad)
        r1, r2 = r_tor - grubosc * 0.72, r_tor + grubosc * 0.72
        pen = QPen(z_alfa(jasna, 235), max(1.0, grubosc * 0.20))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(srodek.x() + dx * r1, srodek.y() + dy * r1),
                   QPointF(srodek.x() + dx * r2, srodek.y() + dy * r2))
        punkt_swiatla(p, punkt, grubosc * 3.2 * puls, barwa, int(190 * puls))
        punkt_swiatla(p, punkt, grubosc * 1.4 * puls, QColor("#FFFFFF"), int(140 * puls))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(punkt, grubosc * 0.32, grubosc * 0.32)
        p.setBrush(Qt.BrushStyle.NoBrush)

    def _kreski_rowka(self, p, srodek, r_tor, grubosc, kat_od, kat_do, barwa,
                      alfa=110, krok=6.0):
        """Drobna podziałka w pustej części rowka — skala, nie zębatka.

        Amber rysowany kreskowanym piórem na całą grubość rowka wyglądał jak
        gąsienica; te kreski są cienkie, krótkie i leżą w rowku.
        """
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(z_alfa(barwa, alfa), max(0.8, grubosc * 0.16))
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        r1, r2 = r_tor - grubosc * 0.30, r_tor + grubosc * 0.30
        kat = kat_od
        while kat < kat_do - 0.5:
            rad = math.radians(kat - 90.0)
            dx, dy = math.cos(rad), math.sin(rad)
            p.drawLine(QPointF(srodek.x() + dx * r1, srodek.y() + dy * r1),
                       QPointF(srodek.x() + dx * r2, srodek.y() + dy * r2))
            kat += krok

    def _rysuj_tor(self, p, srodek, R):
        """Tor postępu na oprawie: podkład, łuk stanu i czoło."""
        r_tor = R * _TOR_R
        grubosc = R * _TOR_GRUBOSC
        stan = self._stan
        p.setBrush(Qt.BrushStyle.NoBrush)

        # podkład toru — rowek w oprawie
        p.setPen(QPen(z_alfa(QColor(0, 0, 0), 90), grubosc * 1.15))
        p.drawEllipse(srodek, r_tor, r_tor)
        kolor_tla = z_alfa(QColor("#94A6BF"), 130) if stan == "nieaktywny" \
            else z_alfa(QColor("#94A6BF"), 62)
        pen = QPen(kolor_tla, grubosc * (0.70 if stan != "nieaktywny" else 0.78))
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.drawEllipse(srodek, r_tor, r_tor)
        if stan == "nieaktywny":
            return

        if stan in ("gotowy", "zmieniono"):
            stary = (stan == "zmieniono")
            # „Zmieniono" to ten sam pierścień, ale POMIAR JEST NIEAKTUALNY:
            # świeci ciszej i widać przez niego podziałkę rowka. Wcześniej oba
            # stany miały identyczną tarczę i w karcie (gdzie podpisy są puste)
            # dało się je odróżnić wyłącznie po odznace.
            p.setPen(QPen(z_alfa(CYJAN, 26 if stary else 62), grubosc * 1.2))
            p.drawEllipse(srodek, r_tor, r_tor)
            # jasność biegnie wzdłuż obwodu: najmocniej na północy, najciszej na dole
            moc = 0.42 if stary else 1.0
            g = QConicalGradient(srodek, 90.0)
            g.setColorAt(0.00, z_alfa(CYJAN, 255 * moc))
            g.setColorAt(0.28, z_alfa(CYJAN, 186 * moc))
            g.setColorAt(0.52, z_alfa(CYJAN, 150 * moc))
            g.setColorAt(0.76, z_alfa(CYJAN, 192 * moc))
            g.setColorAt(1.00, z_alfa(CYJAN, 255 * moc))
            p.setPen(QPen(QBrush(g), grubosc * 0.44))
            p.drawEllipse(srodek, r_tor, r_tor)
            # wąska nitka światła po zewnętrznej stronie rowka
            p.setPen(QPen(z_alfa(_mieszaj(CYJAN, QColor("#FFFFFF"), 0.55),
                                 30 if stary else 70), grubosc * 0.14))
            p.drawEllipse(srodek, r_tor + grubosc * 0.20, r_tor + grubosc * 0.20)
            if stary:
                self._kreski_rowka(p, srodek, r_tor, grubosc, 0.0, 360.0,
                                   QColor("#C3D2E6"), 74, krok=10.0)
                puls = 0.55 + 0.45 * self._oddech(1600)
                czolo = self._na_obwodzie(srodek, r_tor, 0.0)
                punkt_swiatla(p, czolo, grubosc * 2.6 * puls, CYJAN, int(160 * puls))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(_mieszaj(CYJAN, QColor("#FFFFFF"), 0.55))
                p.drawEllipse(czolo, grubosc * 0.42, grubosc * 0.42)
                p.setBrush(Qt.BrushStyle.NoBrush)
            return

        if stan == "sukces":
            g = QConicalGradient(srodek, 90.0)
            g.setColorAt(0.0, ZIELEN)
            g.setColorAt(0.45, _mieszaj(ZIELEN, MIETA, 0.40))
            g.setColorAt(1.0, ZIELEN)
            p.setPen(QPen(z_alfa(ZIELEN, 62), grubosc * 1.55))
            p.drawEllipse(srodek, r_tor, r_tor)
            p.setPen(QPen(QBrush(g), grubosc))
            p.drawEllipse(srodek, r_tor, r_tor)
            rampa = QConicalGradient(srodek, 90.0)
            rampa.setColorAt(0.00, z_alfa(QColor("#FFFFFF"), 62))
            rampa.setColorAt(0.35, z_alfa(QColor("#FFFFFF"), 10))
            rampa.setColorAt(0.72, z_alfa(QColor("#FFFFFF"), 34))
            rampa.setColorAt(1.00, z_alfa(QColor("#FFFFFF"), 62))
            p.setPen(QPen(QBrush(rampa), grubosc * 0.42))
            p.drawEllipse(srodek, r_tor - grubosc * 0.22, r_tor - grubosc * 0.22)
            return

        if stan == "ostrzezenie":
            postep = max(0.02, min(0.98, self._postep))
            kat = postep * 360.0
            # część pokryta kwotą — pełny, spokojny łuk
            zielony = self._luk(srodek, r_tor, 90.0, -kat)
            p.setPen(self._pioro_poswiaty(z_alfa(ZIELEN, 70), grubosc * 1.8))
            p.drawPath(zielony)
            pen = QPen(ZIELEN, grubosc)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawPath(zielony)
            self._rampa_luku(p, srodek, r_tor, grubosc, zielony, postep, 84)
            # reszta: płaski bursztyn w rowku i drobna podziałka — skala, nie zębatka
            reszta = self._luk(srodek, r_tor, 90.0 - kat, -(1.0 - postep) * 360.0)
            plaski = QPen(z_alfa(BURSZTYN, 58), grubosc)
            plaski.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(plaski)
            p.drawPath(reszta)
            self._kreski_rowka(p, srodek, r_tor, grubosc, kat + 3.0, 360.0,
                               BURSZTYN, 150)
            # czoło dokładnie tam, gdzie skończyła się kwota
            self._czolo_luku(p, srodek, r_tor, grubosc, kat, BURSZTYN, zywe=False)
            return

        if stan == "blad":
            postep = max(0.04, min(1.0, self._postep))
            kat = postep * 360.0
            sciezka = self._luk(srodek, r_tor, 90.0, -kat)
            p.setPen(self._pioro_poswiaty(z_alfa(BLAD, 60), grubosc * 1.9))
            p.drawPath(sciezka)
            # łuk jest ciągły aż do miejsca, w którym praca stanęła; przerwy
            # w kresce czytały się jak taśma ostrzegawcza, a nie jak pomiar
            pen = QPen(BLAD, grubosc)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawPath(sciezka)
            self._rampa_luku(p, srodek, r_tor, grubosc, sciezka, postep, 70)
            # to, czego już nie będzie: rowek gaśnie w stronę północy
            reszta = self._luk(srodek, r_tor, 90.0 - kat, -(1.0 - postep) * 360.0)
            p.setPen(self._pioro_poswiaty(z_alfa(QColor("#93A8C4"), 118), grubosc * 0.70))
            p.drawPath(reszta)
            self._kreski_rowka(p, srodek, r_tor, grubosc, kat + 4.0, 360.0,
                               QColor("#C3D2E6"), 58)
            # dwie poprzeczki na czole — tu praca się zatrzymała
            self._czolo_luku(p, srodek, r_tor, grubosc, kat, BLAD, zywe=False)
            rad = math.radians(kat - 90.0 + 5.0)
            dx, dy = math.cos(rad), math.sin(rad)
            r1, r2 = r_tor - grubosc * 0.62, r_tor + grubosc * 0.62
            pen = QPen(z_alfa(BLAD, 200), max(1.0, grubosc * 0.18))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(srodek.x() + dx * r1, srodek.y() + dy * r1),
                       QPointF(srodek.x() + dx * r2, srodek.y() + dy * r2))
            return

        # 'praca' — łuk od północy, cyjan → zieleń, z jaśniejszym czołem
        postep = max(0.0, min(1.0, self._postep))
        if postep <= 0.001:
            return
        # szew gradientu (poz. 0/1) odsunięty o 1,5° poza początek łuku,
        # żeby na północy nie błyskał zielony piksel
        g = QConicalGradient(srodek, 91.5)
        g.setColorAt(0.0, ZIELEN)
        g.setColorAt(0.30, _mieszaj(CYJAN, ZIELEN, 0.78))
        g.setColorAt(0.70, _mieszaj(CYJAN, ZIELEN, 0.28))
        g.setColorAt(1.0, CYJAN)
        sciezka = self._luk(srodek, r_tor, 90.0, -postep * 360.0)
        barwa_czola = _mieszaj(CYJAN, ZIELEN, postep)
        p.setPen(self._pioro_poswiaty(z_alfa(barwa_czola, 65), grubosc * 2.0))
        p.drawPath(sciezka)
        pen = QPen(QBrush(g), grubosc)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.drawPath(sciezka)

        # rampa jasności wzdłuż długości: ogon przygaszony, czoło rozświetlone
        self._rampa_luku(p, srodek, r_tor, grubosc, sciezka, postep, 96)
        # to, co zostało: rowek widać, więc widać też, ile drogi przed nami
        reszta = self._luk(srodek, r_tor, 90.0 - postep * 360.0,
                           -(1.0 - postep) * 360.0)
        p.setPen(self._pioro_poswiaty(z_alfa(QColor("#93A8C4"), 132), grubosc * 0.70))
        p.drawPath(reszta)
        self._kreski_rowka(p, srodek, r_tor, grubosc, postep * 360.0 + 4.0, 360.0,
                           QColor("#C3D2E6"), 64)
        self._czolo_luku(p, srodek, r_tor, grubosc, postep * 360.0, barwa_czola,
                         zywe=True, puls=0.7 + 0.3 * self._oddech(900))

    def _rysuj_igle(self, p, srodek, R):
        kat = self._kat_igly()
        polnoc = _IGLA_POLNOC[self._stan]
        # ślad drgania tylko wtedy, gdy igła naprawdę drga — na zatrzymanym
        # zrzucie dwie blade kopie wyglądały jak błąd rysowania
        if self._stan == "blad" and self._anim:
            for przesun in (-7.5, 7.5):
                self._jedna_igla(p, srodek, R, kat + przesun, polnoc, 55)
        self._jedna_igla(p, srodek, R, kat, polnoc, 255)

        # oś igły
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#08101C"))
        p.drawEllipse(srodek, R * 0.075, R * 0.075)
        p.setBrush(QColor("#EDF4FC") if self._stan != "nieaktywny" else QColor("#98A8BE"))
        p.drawEllipse(srodek, R * 0.048, R * 0.048)
        p.setBrush(z_alfa(QColor(0, 0, 0), 165))
        p.drawEllipse(srodek, R * 0.018, R * 0.018)
        p.setBrush(Qt.BrushStyle.NoBrush)

    def _jedna_igla(self, p, srodek, R, kat, barwa_polnoc, alfa):
        p.save()
        p.translate(srodek)
        p.rotate(kat)
        p.setPen(Qt.PenStyle.NoPen)

        dl_n, dl_s, szer = R * 0.525, R * 0.470, R * 0.080
        polnoc = QPolygonF([QPointF(0, -dl_n), QPointF(-szer, R * 0.045), QPointF(szer, R * 0.045)])
        poludnie = QPolygonF([QPointF(0, dl_s), QPointF(-szer, -R * 0.045), QPointF(szer, -R * 0.045)])

        if alfa >= 200:
            # Cień rzucany na tarczę. Światło pada z góry z lewej, więc cień
            # idzie w dół i w prawo — ale igła się obraca, a cień nie może
            # obracać się razem z nią. Kierunek liczymy w układzie tarczy
            # i obracamy go z powrotem o kąt igły.
            rad = math.radians(-kat)
            kx = math.cos(rad) * 0.34 - math.sin(rad) * 1.0
            ky = math.sin(rad) * 0.34 + math.cos(rad) * 1.0
            for odsun, ciemnosc in ((0.062, 18), (0.044, 30), (0.028, 46),
                                    (0.014, 72)):
                p.setBrush(z_alfa(QColor(0, 0, 0), ciemnosc))
                p.save()
                p.translate(R * odsun * kx, R * odsun * ky)
                p.drawPolygon(polnoc)
                p.drawPolygon(poludnie)
                p.restore()

        gs = QLinearGradient(QPointF(-szer, 0), QPointF(szer, 0))
        gs.setColorAt(0.0, z_alfa(_IGLA_POLUDNIE.lighter(118), alfa))
        gs.setColorAt(0.5, z_alfa(_IGLA_POLUDNIE, alfa))
        gs.setColorAt(1.0, z_alfa(_IGLA_POLUDNIE.darker(165), alfa))
        p.setBrush(QBrush(gs))
        p.drawPolygon(poludnie)

        gn = QLinearGradient(QPointF(-szer, 0), QPointF(szer, 0))
        gn.setColorAt(0.0, z_alfa(_mieszaj(barwa_polnoc, QColor("#FFFFFF"), 0.45), alfa))
        gn.setColorAt(0.40, z_alfa(barwa_polnoc, alfa))
        gn.setColorAt(1.0, z_alfa(barwa_polnoc.darker(160), alfa))
        p.setBrush(QBrush(gn))
        p.drawPolygon(polnoc)
        if alfa >= 200:
            pen = QPen(z_alfa(QColor("#FFFFFF"), 90), max(0.8, R * 0.012))
            p.setPen(pen)
            p.drawLine(QPointF(0, -dl_n), QPointF(-szer * 0.92, R * 0.035))
            p.setPen(Qt.PenStyle.NoPen)
        p.restore()

    def _rysuj_szklo(self, p, srodek, R):
        """Szkło nad tarczą: refleks, ciasna smuga i gęstnienie ku krawędzi."""
        r = R * _SOCZEWKA
        p.save()
        obszar = QPainterPath()
        obszar.addEllipse(srodek, r, r)
        p.setClipPath(obszar)
        p.setPen(Qt.PenStyle.NoPen)

        os_blysku = QPointF(srodek.x() - r * 0.10, srodek.y() - r * 1.05)
        blysk = QRadialGradient(os_blysku, r * 1.62)
        blysk.setColorAt(0.0, QColor(255, 255, 255, 44))
        blysk.setColorAt(0.55, QColor(255, 255, 255, 17))
        blysk.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(blysk))
        p.drawEllipse(os_blysku, r * 1.62, r * 1.62)

        # chłodny film powłoki — szkło nie jest bezbarwne, ma własny odcień
        film = QLinearGradient(QPointF(srodek.x(), srodek.y() - r),
                               QPointF(srodek.x(), srodek.y() + r))
        film.setColorAt(0.0, z_alfa(QColor("#7FD8FF"), 16))
        film.setColorAt(0.55, z_alfa(QColor("#7FD8FF"), 0))
        film.setColorAt(1.0, z_alfa(QColor("#3A6B96"), 20))
        p.setBrush(QBrush(film))
        p.drawEllipse(srodek, r, r)

        # ciasny refleks — wydłużona smuga światła odbita od wypukłego szkła
        p.save()
        p.translate(srodek.x() - r * 0.33, srodek.y() - r * 0.46)
        p.rotate(-32.0)
        p.scale(1.0, 0.42)
        smuga = QRadialGradient(QPointF(0, 0), r * 0.62)
        smuga.setColorAt(0.00, QColor(255, 255, 255, 86))
        smuga.setColorAt(0.45, QColor(255, 255, 255, 34))
        smuga.setColorAt(1.00, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(smuga))
        p.drawEllipse(QPointF(0, 0), r * 0.62, r * 0.62)
        p.restore()

        # odbicie od dołu — słabe, chłodne, żeby szkło miało dwie strony
        os_dolu = QPointF(srodek.x() + r * 0.34, srodek.y() + r * 0.56)
        dolne = QRadialGradient(os_dolu, r * 0.62)
        dolne.setColorAt(0.0, z_alfa(QColor("#BFE6FF"), 26))
        dolne.setColorAt(1.0, z_alfa(QColor("#BFE6FF"), 0))
        p.setBrush(QBrush(dolne))
        p.drawEllipse(os_dolu, r * 0.62, r * 0.62)

        # grubość szkła przy krawędzi — dysk nie ma takiego cienia, szkło ma
        kraw = QRadialGradient(srodek, r)
        kraw.setColorAt(0.00, QColor(0, 0, 0, 0))
        kraw.setColorAt(0.74, QColor(0, 0, 0, 10))
        kraw.setColorAt(0.93, QColor(0, 0, 0, 52))
        kraw.setColorAt(1.00, QColor(0, 0, 0, 104))
        p.setBrush(QBrush(kraw))
        p.drawEllipse(srodek, r, r)
        p.restore()

        p.setBrush(Qt.BrushStyle.NoBrush)
        # górny łuk refleksu — jaśniejszy w środku łuku, gasnący na końcach
        luk = self._luk(srodek, r - R * 0.030, 112.0, 66.0)
        g = QConicalGradient(srodek, 112.0)
        g.setColorAt(0.000, QColor(255, 255, 255, 0))
        g.setColorAt(0.050, QColor(255, 255, 255, 120))
        g.setColorAt(0.130, QColor(255, 255, 255, 150))
        g.setColorAt(0.185, QColor(255, 255, 255, 0))
        pen = QPen(QBrush(g), R * 0.042)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(luk)
        # krótki refleks od dołu z prawej
        luk2 = self._luk(srodek, r - R * 0.036, 300.0, 34.0)
        pen2 = QPen(z_alfa(QColor("#DCEEFF"), 40), R * 0.018)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        p.drawPath(luk2)

        # krawędź Fresnela: sama obręcz szkła łapie światło mocniej od tafli,
        # najmocniej od dołu — tam, gdzie główny refleks jej nie dotyka
        kraw_g = QLinearGradient(QPointF(srodek.x(), srodek.y() - r),
                                 QPointF(srodek.x(), srodek.y() + r))
        kraw_g.setColorAt(0.00, z_alfa(QColor("#FFFFFF"), 26))
        kraw_g.setColorAt(0.42, z_alfa(QColor("#FFFFFF"), 10))
        kraw_g.setColorAt(0.78, z_alfa(QColor("#CFEBFF"), 74))
        kraw_g.setColorAt(1.00, z_alfa(QColor("#CFEBFF"), 120))
        p.setPen(QPen(QBrush(kraw_g), max(0.9, R * 0.013)))
        p.drawEllipse(srodek, r - R * 0.008, r - R * 0.008)

    def _rysuj_znaczniki(self, p, srodek, R):
        r_tor = R * _TOR_R
        if self._stan == "sukces":
            self._odznaka(p, self._na_obwodzie(srodek, r_tor, 135.0), R * 0.175, ZIELEN, "ptaszek")
        elif self._stan == "blad":
            # odznaka OBOK czoła, nie na nim — inaczej zasłania właśnie to miejsce,
            # o którym mówi
            czolo = max(0.04, min(1.0, self._postep)) * 360.0
            self._odznaka(p, self._na_obwodzie(srodek, r_tor, czolo + 11.0),
                          R * 0.155, BLAD, "krzyzyk")
        elif self._stan == "ostrzezenie":
            postep = max(0.02, min(0.98, self._postep))
            # jedna odznaka, tuż za granicą — druga (zielona) tylko dublowała
            # to, co i tak mówi łuk, a przy okazji zabijała czytelność
            self._odznaka(p, self._na_obwodzie(srodek, r_tor, postep * 360.0 + 11.0),
                          R * 0.155, BURSZTYN, "wykrzyknik")
        elif self._stan == "zmieniono":
            self._odznaka(p, self._na_obwodzie(srodek, r_tor, 137.0), R * 0.155,
                          CYJAN, "teczka")

    def _odznaka(self, p, srodek, r, barwa, znak):
        p.setPen(QPen(_CIEMNY, max(1.4, r * 0.28)))
        p.setBrush(barwa)
        p.drawEllipse(srodek, r, r)
        ciemny = QColor("#052018")
        pen = QPen(ciemny, max(1.5, r * 0.30))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if znak == "ptaszek":
            s = QPainterPath()
            s.moveTo(srodek.x() - r * 0.46, srodek.y() + r * 0.02)
            s.lineTo(srodek.x() - r * 0.12, srodek.y() + r * 0.38)
            s.lineTo(srodek.x() + r * 0.50, srodek.y() - r * 0.36)
            p.drawPath(s)
        elif znak == "krzyzyk":
            p.drawLine(QPointF(srodek.x() - r * 0.36, srodek.y() - r * 0.36),
                       QPointF(srodek.x() + r * 0.36, srodek.y() + r * 0.36))
            p.drawLine(QPointF(srodek.x() + r * 0.36, srodek.y() - r * 0.36),
                       QPointF(srodek.x() - r * 0.36, srodek.y() + r * 0.36))
        elif znak == "wykrzyknik":
            p.drawLine(QPointF(srodek.x(), srodek.y() - r * 0.44),
                       QPointF(srodek.x(), srodek.y() + r * 0.08))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ciemny)
            p.drawEllipse(QPointF(srodek.x(), srodek.y() + r * 0.40), r * 0.15, r * 0.15)
        elif znak == "teczka":
            # strzałka nawrotu: dane się zmieniły, trzeba przeliczyć od nowa
            prom = r * 0.50
            kat_od, rozpietosc = 60.0, -272.0
            pen = QPen(ciemny, max(1.3, r * 0.24))
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawPath(self._luk(srodek, prom, kat_od, rozpietosc))
            # grot na końcu łuku, styczny do niego — liczony, nie wstawiony na oko
            kat = math.radians(kat_od + rozpietosc)
            koniec = QPointF(srodek.x() + prom * math.cos(kat),
                             srodek.y() - prom * math.sin(kat))
            sx, sy = math.sin(kat), math.cos(kat)          # styczna zgodna z ruchem
            px, py = -sy, sx                               # normalna do niej
            dl, bok = r * 0.46, r * 0.30
            grot = QPolygonF([
                QPointF(koniec.x() + sx * dl, koniec.y() + sy * dl),
                QPointF(koniec.x() + px * bok, koniec.y() + py * bok),
                QPointF(koniec.x() - px * bok, koniec.y() - py * bok)])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ciemny)
            p.drawPolygon(grot)
            p.setBrush(Qt.BrushStyle.NoBrush)

    def _rysuj_podpisy(self, p, r, dol_tarczy, podpis, podpis2, wiersze, font, szer):
        barwy = _BARWY_PODPISU.get(self._stan, (TEKST, TEKST_3))
        wys = getattr(self, "_wys_wiersza", 18.0)
        x = r.center().x() - szer / 2.0
        y = dol_tarczy + 4.0
        if podpis:
            p.setPen(QPen(barwy[0]))
            p.setFont(font)
            flagi = (int(Qt.AlignmentFlag.AlignHCenter) | int(Qt.AlignmentFlag.AlignTop)
                     | int(Qt.TextFlag.TextWordWrap))
            p.drawText(QRectF(x, y, szer, wiersze * wys + 2.0), flagi, podpis)
            y += wiersze * wys + 3.0
        if podpis2:
            p.setPen(QPen(barwy[1]))
            font2 = czcionka(11, 400)
            p.setFont(font2)
            fm = QFontMetricsF(font2)
            tekst2 = fm.elidedText(podpis2, Qt.TextElideMode.ElideRight, szer)
            p.drawText(QRectF(x, y, szer, 16.0),
                       int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                       tekst2)


# ── karta ze szkła z kompasem ────────────────────────────────────────
class KartaKompasu(QWidget):
    """Karta „Generuj dokumenty”: kompas, tytuł i cztery plakietki etapów."""

    ETAPY = ("dane", "trasy", "PDF", "mapa")
    TYTUL = "Generuj dokumenty"

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.kompas = Kompas(self, srednica=124)
        self.kompas.ustaw_podpis("")
        self.kompas.ustaw_podpis_dodatkowy("")
        self._etapy = {nazwa: "czeka" for nazwa in self.ETAPY}
        self.setMinimumSize(360, 180)

    def sizeHint(self):
        return QSize(400, 210)

    def ustaw_etapy(self, slownik):
        """Stany plakietek: 'czeka', 'w_toku' albo 'gotowe'."""
        for nazwa, stan in (slownik or {}).items():
            if nazwa in self._etapy and stan in ("czeka", "w_toku", "gotowe"):
                self._etapy[nazwa] = stan
        self.update()

    def etapy(self):
        return dict(self._etapy)

    def zatrzymaj_animacje(self):
        self.kompas.zatrzymaj_animacje()

    def wznow_animacje(self):
        self.kompas.wznow_animacje()

    def resizeEvent(self, zdarzenie):
        margines = 16
        bok = min(self.height() - 2 * margines, 142)
        self.kompas.setGeometry(margines, int((self.height() - bok) / 2), bok, bok)
        super().resizeEvent(zdarzenie)

    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        karta = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        cien(p, karta, promien=18.0, sila=90, rozmycie=14, przesun=6)
        szklo(p, karta, promien=18.0)

        x = self.kompas.geometry().right() + 14.0
        szer = max(60.0, karta.right() - 18.0 - x)
        srodek_y = karta.center().y()

        p.setPen(QPen(TEKST))
        p.setFont(czcionka(19, 700, naglowek=True))
        p.drawText(QRectF(x, srodek_y - 36.0, szer, 26.0),
                   int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                   self.TYTUL)
        self._rysuj_plakietki(p, x, srodek_y + 2.0, szer)

    def _uklad_plakietek(self, szer_max):
        """Dobiera rozmiar plakietek tak, żeby wszystkie cztery zmieściły się w rzędzie."""
        for rozmiar, zapas_ze, zapas_bez, odstep in ((12.0, 32.0, 20.0, 6.0),
                                                     (11.0, 28.0, 18.0, 5.0),
                                                     (10.0, 24.0, 15.0, 4.0)):
            font = czcionka(rozmiar, 600)
            metryka = QFontMetricsF(font)
            szerokosci = []
            for nazwa in self.ETAPY:
                znacznik = self._etapy.get(nazwa, "czeka") in ("gotowe", "w_toku")
                szerokosci.append(metryka.horizontalAdvance(nazwa)
                                  + (zapas_ze if znacznik else zapas_bez))
            razem = sum(szerokosci) + odstep * (len(szerokosci) - 1)
            if razem <= szer_max + 0.5 or rozmiar == 10.0:
                return font, szerokosci, odstep, rozmiar
        return czcionka(12.0, 600), [], 6.0, 12.0

    def _rysuj_plakietki(self, p, x, y, szer_max):
        font, szerokosci, odstep, rozmiar = self._uklad_plakietek(szer_max)
        p.setFont(font)
        wys = 25.0 if rozmiar >= 11.0 else 22.0
        skala = rozmiar / 12.0
        kursor = x
        for nazwa, szer in zip(self.ETAPY, szerokosci):
            stan = self._etapy.get(nazwa, "czeka")
            znacznik = stan in ("gotowe", "w_toku")
            pole = QRectF(kursor, y, szer, wys)
            if stan == "gotowe":
                obrys, baza, napis = ZIELEN, ZIELEN, MIETA
            elif stan == "w_toku":
                obrys, baza, napis = CYJAN, CYJAN, CYJAN
            else:
                obrys = z_alfa(QColor("#8FA1BA"), 90)
                baza = QColor("#8FA1BA")
                napis = TEKST_3

            # plakietka ma wypukłość: jaśniej u góry, ciemniej przy dnie
            mocna = stan in ("gotowe", "w_toku")
            wypelnienie = QLinearGradient(pole.topLeft(), pole.bottomLeft())
            wypelnienie.setColorAt(0.0, z_alfa(baza, 52 if mocna else 30))
            wypelnienie.setColorAt(1.0, z_alfa(baza, 20 if mocna else 10))
            p.setPen(QPen(obrys, 1.1))
            p.setBrush(QBrush(wypelnienie))
            p.drawRoundedRect(pole, wys / 2.0, wys / 2.0)
            # wewnętrzna krawędź światła u góry
            p.setBrush(Qt.BrushStyle.NoBrush)
            swiatlo = QLinearGradient(pole.topLeft(), pole.bottomLeft())
            swiatlo.setColorAt(0.00, z_alfa(QColor("#FFFFFF"), 92 if mocna else 52))
            swiatlo.setColorAt(0.45, z_alfa(QColor("#FFFFFF"), 0))
            swiatlo.setColorAt(1.00, z_alfa(QColor("#FFFFFF"), 22))
            p.setPen(QPen(QBrush(swiatlo), 1.0))
            wnetrze = pole.adjusted(0.7, 0.7, -0.7, -0.7)
            p.drawRoundedRect(wnetrze, wnetrze.height() / 2.0, wnetrze.height() / 2.0)

            if stan == "gotowe":
                sr = QPointF(pole.x() + 13.0 * skala, pole.center().y())
                pen = QPen(MIETA, 1.8 * skala)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                s = QPainterPath()
                s.moveTo(sr.x() - 4.0 * skala, sr.y() + 0.2)
                s.lineTo(sr.x() - 1.2 * skala, sr.y() + 3.2 * skala)
                s.lineTo(sr.x() + 4.2 * skala, sr.y() - 3.4 * skala)
                p.drawPath(s)
            elif stan == "w_toku":
                oko = QPointF(pole.x() + 12.5 * skala, pole.center().y())
                punkt_swiatla(p, oko, 7.0 * skala, CYJAN, 150)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(CYJAN)
                p.drawEllipse(oko, 3.2 * skala, 3.2 * skala)
                p.setBrush(_mieszaj(CYJAN, QColor("#FFFFFF"), 0.7))
                p.drawEllipse(QPointF(oko.x() - 0.8 * skala, oko.y() - 0.9 * skala),
                              1.1 * skala, 1.1 * skala)

            p.setPen(QPen(napis))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawText(pole.adjusted((22.0 if znacznik else 10.0) * skala, 0, -7.0 * skala, 0),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                       nazwa)
            kursor += szer + odstep


# ── sprawdzenie: siatka stanów i karta ───────────────────────────────
if __name__ == "__main__":
    import sys

    NAGLOWKI = [("01", "NIEAKTYWNY", "nieaktywny"), ("02", "GOTOWY", "gotowy"),
                ("03", "PRACA", "praca"), ("04", "SUKCES", "sukces"),
                ("05", "BŁĄD", "blad"), ("06", "OSTRZEŻENIE", "ostrzezenie"),
                ("07", "ZMIENIONO", "zmieniono")]

    BARWY_NAGLOWKA = {"nieaktywny": TEKST_3, "gotowy": CYJAN, "praca": CYJAN,
                      "sukces": ZIELEN, "blad": BLAD, "ostrzezenie": BURSZTYN,
                      "zmieniono": CYJAN}

    class Scena(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Kompas — stany")
            self.resize(1440, 540)
            self.kompasy = []
            for numer, tytul, stan in NAGLOWKI:
                k = Kompas(self)
                k.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                k.ustaw_stan(stan)
                if stan == "praca":
                    k.ustaw_etap("Składam PDF")
                    k.ustaw_postep(0.62)
                    k.ustaw_azymut(174)
                self.kompasy.append((k, numer, tytul, stan))
            self.karta = KartaKompasu(self)
            self.karta.kompas.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.karta.kompas.ustaw_stan("praca")
            self.karta.kompas.ustaw_postep(0.62)
            self.karta.kompas.ustaw_azymut(174)
            self.karta.ustaw_etapy({"dane": "gotowe", "trasy": "gotowe",
                                    "PDF": "w_toku", "mapa": "czeka"})

        def resizeEvent(self, zdarzenie):
            szer = (self.width() - 36) / 7.0
            for i, (k, _n, _t, _s) in enumerate(self.kompasy):
                k.setGeometry(int(18 + i * szer), 66, int(szer - 8), 226)
            self.karta.setGeometry(24, 310, 452, 196)
            super().resizeEvent(zdarzenie)

        def paintEvent(self, _z):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            tlo_sceny(p, QRectF(self.rect()))
            for k, numer, tytul, stan in self.kompasy:
                g = k.geometry()
                p.setPen(QPen(TEKST_3))
                p.setFont(czcionka(11, 700, mono=True))
                p.drawText(QRectF(g.x(), 26, g.width(), 18),
                           int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter),
                           numer)
                p.setPen(QPen(BARWY_NAGLOWKA[stan]))
                p.setFont(czcionka(12, 700, naglowek=True, odstep=0.8))
                p.drawText(QRectF(g.x(), 42, g.width(), 18),
                           int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter),
                           tytul)

        def zatrzymaj(self):
            for k, _n, _t, _s in self.kompasy:
                k.zatrzymaj_animacje()
            self.karta.zatrzymaj_animacje()

    app = QApplication(sys.argv)
    scena = Scena()
    scena.show()
    scena.zatrzymaj()
    QApplication.processEvents()
    scena.zatrzymaj()
    QApplication.processEvents()
    scena.grab().save("zrzut_kompas.png")
    print("zapisano zrzut_kompas.png")
    if "--pokaz" in sys.argv:
        for kompas, _n, _t, _s in scena.kompasy:
            kompas.wznow_animacje()
        scena.karta.wznow_animacje()
        sys.exit(app.exec())
