# -*- coding: utf-8 -*-
"""Taśma miesiąca — poziomy pasek wszystkich dni, tuż pod paskiem tytułowym.

Jeden kafel to jeden dzień, czytany z góry na dół w trzech stopniach:
NUMER DNIA (mono, najjaśniejszy, skrót dnia tygodnia obok niego w drugim
planie), MINIATURA trasy i KWOTA (o stopień mniejsza od numeru, „zł” ciszej).
Kafel nie jest płaskim prostokątem — ma wypukłą płaszczyznę, wewnętrzną
krawędź światła u góry i własny cień pod spodem, więc taśma czyta się jak rząd
fizycznych klawiszy. Dzień bez trasy jest tylko wygaszony, a napis „wolne”
dostaje wyłącznie dzień wyłączony przez użytkownika.

Dzień WYBRANY i dzień DZISIEJSZY różnią się materiałem, nie samą barwą:
wybrany unosi się, jaśnieje, dostaje białą obręcz światła i klin wskazujący go
na szynie pod taśmą; dzisiejszy ma cyjanową aureolę z wolnym pulsowaniem
i plakietkę DZIŚ z dziobkiem. Gdy to ten sam dzień, oba znaki są widoczne naraz.
Po wygenerowaniu dokumentów dni w trasie dostają plakietkę PDF, a dzień
podpisany zielony znacznik — jedno i drugie wchodzi płynnie.

Przy wąskim oknie kafel schodzi stopniami: najpierw znika „zł”, potem kwota
(zastępuje ją słupek wartości), potem miniatura, a na końcu skrót dnia
tygodnia — zostaje sam numer. Plakietka DZIŚ zmienia się wtedy w dziobek,
a przerwy między kaflami maleją, żeby nic się nie zlewało.

Liczby zbiorcze w nagłówku dochodzą do nowych wartości płynnie (proto_styl.Plynnie).
Wszystkie ruchy da się zatrzymać metodą ``zatrzymaj_animacje()``; zegar pulsu
chodzi tylko wtedy, gdy jest co pulsować, i gaśnie przy chowaniu widżetu.

Barwy, czcionki i pomocniki rysowania pochodzą z proto_styl, dane z proto_dane.
"""
import math

from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QEvent, QTimer, pyqtSignal
from PyQt6.QtGui import (QPainter, QPainterPath, QPen, QBrush, QColor,
                         QLinearGradient, QRadialGradient, QFontMetricsF)
from PyQt6.QtWidgets import QWidget, QToolTip

from proto_styl import (TLO_GORA, TEKST, TEKST_2, TEKST_3,
                        CYJAN, ZIELEN, MIETA, BURSZTYN,
                        z_alfa, czcionka, poswiata_linii,
                        punkt_swiatla, tekst, Plynnie)
import proto_dane as dane

# ── miary taśmy (wprost z zatwierdzonego projektu) ───────────────────
PAD_BOK      = 24.0     # margines lewy i prawy
PAD_GORA     = 14.0
H_NAGLOWEK   = 17.0     # wiersz z napisem i liczbami zbiorczymi
ODSTEP_PION  = 13.0     # luz na plakietkę DZIŚ
H_KAFLA      = 58.0
H_TASMY      = 118      # docelowa wysokość całości
ODSTEP       = 4.0      # przerwa między kaflami przy szerokim oknie
ODSTEP_MIN   = 1.5      # …i przy wąskim: kafel ma być szerszy od przerwy
PROMIEN      = 9.0
BIEL         = QColor(255, 255, 255)
CZERN        = QColor(0, 0, 0)

# ── progi zwężania kafla ─────────────────────────────────────────────
PROG_MINIATURY = 19.0   # poniżej tej szerokości kafla nie ma miejsca na trasę
PROG_PLAKIETEK = 26.0   # …ani na plakietki PDF, znacznik podpisu i pełne DZIŚ

# ── ruch ─────────────────────────────────────────────────────────────
KLATKA_MS    = 40       # zegar pulsu — 25 kl./s wystarczy na wolne tętno
OKRES_PULSU  = 2600.0   # pełny oddech obwódki dnia dzisiejszego
CZAS_WYBORU  = 210      # przejście uniesienia kafla
CZAS_LICZB   = 300      # dochodzenie liczb zbiorczych w nagłówku
CZAS_KURSORA = 130      # rozjaśnienie kafla pod kursorem
CZAS_STANU   = 260      # wejście plakietek PDF po wygenerowaniu
CZAS_WOLNEGO = 240      # błysk kafla przełączonego na wolny

# ── materiał kafla ───────────────────────────────────────────────────
KORPUS_GORA  = QColor(40, 59, 89, 196)
KORPUS_SROD  = QColor(22, 35, 56, 180)
KORPUS_DOL   = QColor(11, 18, 31, 196)
# ten sam materiał uniesiony do światła — kafel wybrany ma być JAŚNIEJSZY,
# a nie tylko bardziej kryjący (podbijanie samej alfy robiło z niego dziurę)
KORPUS_GORA_J = QColor(70, 98, 140, 225)
KORPUS_SROD_J = QColor(44, 66, 100, 215)
KORPUS_DOL_J  = QColor(20, 32, 52, 225)


def _mieszaj(a, b, t):
    """Liniowe przejście między dwiema barwami (razem z kanałem alfa)."""
    t = max(0.0, min(1.0, float(t)))
    return QColor(int(a.red() + (b.red() - a.red()) * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t),
                  int(a.alpha() + (b.alpha() - a.alpha()) * t))


def _postoje_txt(n):
    """1 postój, 2 postoje, 5 postojów — polska odmiana."""
    if n == 1:
        return "1 postój"
    r, s = n % 10, n % 100
    if 2 <= r <= 4 and not (12 <= s <= 14):
        return "%d postoje" % n
    return "%d postojów" % n


ODSTEP_ETYKIETY = 3.0   # odstęp numeru dnia od skrótu dnia tygodnia


def _rozmiar_skrotu(rozmiar_numeru):
    """Skrót dnia tygodnia jest wyraźnie mniejszy od numeru — stąd hierarchia."""
    return max(7, int(rozmiar_numeru) - 3)


class TasmaMiesiaca(QWidget):
    """Pasek dni miesiąca. Kliknięcie wybiera dzień, prawy przycisk przełącza wolne."""

    wybrano = pyqtSignal(int)
    przelaczono_wolny = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dni = []
        self._dzis = 0
        self._wybrany = 0
        self._wybrany_stary = 0
        self._stan = "zwykly"
        self._pod_kursorem = -1
        self._zbior = dane.podsumowanie([])
        self._uklad = {"etykieta": ("pelny", 12), "kwota": (11, True),
                       "miniatura": True, "plakietki": True, "szerokosc": 39.0}
        self._pod_kursorem_stary = -1
        self._maks_kwota = 0.0
        self._wersja_danych = 0
        self._uklad_klucz = None
        self._zajete_naglowka = (PAD_BOK, 10000.0)
        self._ostatni_wolny = 0
        self._faza = 0.0
        self._anim = True
        self._pierwsze_dane = True

        # płynne dochodzenie liczb i uniesienia kafla
        self._pl_kwota = Plynnie(0.0, czas=CZAS_LICZB, krzywa="wyjscie", rodzic=self,
                                 przy_zmianie=self._odswiez_naglowek)
        self._pl_km = Plynnie(0.0, czas=CZAS_LICZB, krzywa="wyjscie", rodzic=self,
                              przy_zmianie=self._odswiez_naglowek)
        self._pl_dni = Plynnie(0.0, czas=CZAS_LICZB, krzywa="wyjscie", rodzic=self,
                               przy_zmianie=self._odswiez_naglowek)
        self._pl_wybor = Plynnie(1.0, czas=CZAS_WYBORU, krzywa="sprezyna", rodzic=self,
                                 przy_zmianie=self._odswiez_wybor)
        # kafel pod kursorem rozjaśnia się, a nie przeskakuje
        self._pl_kursor = Plynnie(1.0, czas=CZAS_KURSORA, krzywa="wyjscie", rodzic=self,
                                  przy_zmianie=self._odswiez_kursor)
        # plakietki PDF wchodzą po wygenerowaniu, zamiast pojawić się nagle
        self._pl_stan = Plynnie(0.0, czas=CZAS_STANU, krzywa="wyjscie", rodzic=self,
                                przy_zmianie=self.update)
        # przełączenie dnia na wolny i z powrotem ma być widać, a nie tylko zobaczyć
        self._pl_wolne = Plynnie(1.0, czas=CZAS_WOLNEGO, krzywa="wyjscie", rodzic=self,
                                 przy_zmianie=self._odswiez_wolny)

        self._zegar = QTimer(self)
        self._zegar.setInterval(KLATKA_MS)
        self._zegar.timeout.connect(self._tik)

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
        kwoty = [d.kwota for d in licz if not d.wolny and d.postoje > 0]
        self._maks_kwota = max(kwoty) if kwoty else 0.0
        self._wersja_danych += 1      # unieważnia policzony układ napisów
        # pierwsze dane, taśma schowana albo wyzerowana kwota — liczby siadają
        # od razu; doliczanie ma sens tylko między dwiema prawdziwymi kwotami
        skok = (self._pierwsze_dane or not self.isVisible()
                or z["kwota"] <= 0.0 or not self._anim)
        for plynne, wartosc in ((self._pl_kwota, z["kwota"]),
                                (self._pl_km, z["km"]),
                                (self._pl_dni, z["dni"])):
            if skok:
                plynne.ustaw(wartosc)
            else:
                plynne.do(wartosc)
        self._pierwsze_dane = False

    @staticmethod
    def _wylaczony(d):
        return bool(getattr(d, "wylaczony", False))

    def ustaw_dni(self, lista_dni):
        self._dni = list(lista_dni or [])
        self._przelicz()
        if self._wybrany and not self._dzien(self._wybrany):
            self._wybrany = 0
        self._dopilnuj_zegara()
        self.update()

    def ustaw_dzis(self, numer_dnia):
        self._dzis = int(numer_dnia or 0)
        self._dopilnuj_zegara()
        self.update()

    def ustaw_wybrany(self, numer_dnia):
        numer = int(numer_dnia or 0)
        if numer == self._wybrany:
            return
        self._wybrany_stary = self._wybrany
        self._wybrany = numer
        if self._anim and self.isVisible():
            self._pl_wybor.ustaw(0.0)
            self._pl_wybor.do(1.0)
        else:
            self._pl_wybor.ustaw(1.0)
        self.update()

    def ustaw_stan(self, nazwa):
        nowy = "po_generacji" if nazwa == "po_generacji" else "zwykly"
        if nowy == self._stan:
            return
        self._stan = nowy
        cel = 1.0 if nowy == "po_generacji" else 0.0
        if self._anim and self.isVisible():
            self._pl_stan.do(cel)
        else:
            self._pl_stan.ustaw(cel)
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

    # ── animacje ─────────────────────────────────────────────────────
    def zatrzymaj_animacje(self):
        """Gasi zegar i stawia wszystkie ruchy w położeniu docelowym."""
        self._anim = False
        self._zegar.stop()
        self._faza = 0.0
        self._stoj_plynne()
        self._wybrany_stary = self._wybrany
        self._pod_kursorem_stary = self._pod_kursorem
        self.update()

    def wznow_animacje(self):
        self._anim = True
        self._dopilnuj_zegara()
        self.update()

    def animacje_chodza(self):
        return bool(self._anim)

    def _dopilnuj_zegara(self):
        """Zegar pulsu chodzi tylko wtedy, gdy dzisiejszy dzień jest na taśmie."""
        trzeba = bool(self._anim and self.isVisible() and self._dzis
                      and self._dzien(self._dzis) is not None)
        if trzeba and not self._zegar.isActive():
            self._zegar.start()
        elif not trzeba and self._zegar.isActive():
            self._zegar.stop()

    def _tik(self):
        self._faza = (self._faza + KLATKA_MS) % (OKRES_PULSU * 4.0)
        r = self._rect_dnia(self._dzis)
        self.update(self._obszar(r, 9.0) if r is not None else self.rect())

    def _puls(self):
        """0…1 — wolny oddech obwódki dnia dzisiejszego."""
        if not self._anim:
            return 0.35
        return 0.5 + 0.5 * math.sin(self._faza / OKRES_PULSU * 2.0 * math.pi)

    @staticmethod
    def _obszar(rect, zapas):
        """Prostokąt kafla z zapasem na poświatę, plakietkę DZIŚ nad nim
        i klin wyboru pod nim."""
        return rect.adjusted(-zapas, -zapas - 22.0, zapas, zapas + 8.0).toAlignedRect()

    def _rect_dnia(self, numer):
        if not numer:
            return None
        kafle = self._kafle()
        for i, d in enumerate(self._dni):
            if d.data.day == numer and i < len(kafle):
                return kafle[i]
        return None

    def _odswiez_naglowek(self):
        self.update(0, 0, self.width(), int(PAD_GORA + H_NAGLOWEK + 4.0))

    def _odswiez_wybor(self):
        obszar = None
        for numer in (self._wybrany, self._wybrany_stary):
            r = self._rect_dnia(numer)
            if r is None:
                continue
            pole = self._obszar(r, 10.0)
            obszar = pole if obszar is None else obszar.united(pole)
        self.update(obszar if obszar is not None else self.rect())

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
        if n == 1:
            return [QRectF(pas.x(), pas.y(), pas.width(), pas.height())]
        # Przerwa kurczy się razem z kaflem. Stała przerwa 4 px przy wąskim
        # oknie zjadała jedną trzecią taśmy i kafle robiły się drzazgami —
        # światła potrzebuje wnętrze kafla, nie odstęp między nimi.
        luzno = pas.width() / float(n)
        odstep = max(ODSTEP_MIN, min(ODSTEP, luzno * 0.15))
        szer = (pas.width() - odstep * (n - 1)) / float(n)
        if szer < 5.0:
            szer, odstep = max(3.0, pas.width() / n), 0.0
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
            self._ostatni_wolny = d.data.day
            if self._anim and self.isVisible():
                self._pl_wolne.ustaw(0.0)
                self._pl_wolne.do(1.0)
            else:
                self._pl_wolne.ustaw(1.0)
            self.update()
            self.przelaczono_wolny.emit(d.data.day)

    def mouseMoveEvent(self, e):
        self._pod_kursor(self._indeks(e.position()))
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._pod_kursor(-1)
        super().leaveEvent(e)

    def _pod_kursor(self, i):
        """Przełącza kafel pod kursorem — z krótkim przejściem na obu kaflach."""
        if i == self._pod_kursorem:
            return
        self._pod_kursorem_stary = self._pod_kursorem
        self._pod_kursorem = i
        self.setCursor(Qt.CursorShape.PointingHandCursor if i >= 0
                       else Qt.CursorShape.ArrowCursor)
        if self._anim and self.isVisible():
            self._pl_kursor.ustaw(0.0)
            self._pl_kursor.do(1.0)
        else:
            self._pl_kursor.ustaw(1.0)
        self._odswiez_kafle((self._pod_kursorem_stary, i))

    def _odswiez_wolny(self):
        r = self._rect_dnia(self._ostatni_wolny)
        self.update(self._obszar(r, 11.0) if r is not None else self.rect())

    def _blysk_wolnego(self, d):
        """1 tuż po przełączeniu dnia, 0 po chwili — krótki rozbłysk kafla."""
        if d.data.day != self._ostatni_wolny:
            return 0.0
        return max(0.0, 1.0 - self._pl_wolne.teraz())

    def _odswiez_kursor(self):
        self._odswiez_kafle((self._pod_kursorem_stary, self._pod_kursorem))

    def _udzial_kursora(self, i):
        """Ile kafel jest „pod kursorem”: 1, 0, albo ułamek w trakcie przejścia."""
        if i < 0:
            return 0.0
        t = self._pl_kursor.teraz()
        if i == self._pod_kursorem:
            return t
        if i == self._pod_kursorem_stary:
            return 1.0 - t
        return 0.0

    def _odswiez_kafle(self, indeksy):
        """Odświeża tylko wskazane kafle — taśma ma trzydzieści, malujemy dwa."""
        kafle = self._kafle()
        obszar = None
        for i in indeksy:
            if i is None or i < 0 or i >= len(kafle):
                continue
            pole = self._obszar(kafle[i], 10.0)
            obszar = pole if obszar is None else obszar.united(pole)
        self.update(obszar if obszar is not None else self.rect())

    def showEvent(self, e):
        self._dopilnuj_zegara()
        super().showEvent(e)

    def hideEvent(self, e):
        self._zegar.stop()
        self._stoj_plynne()
        super().hideEvent(e)

    def closeEvent(self, e):
        self._zegar.stop()
        self._stoj_plynne()
        super().closeEvent(e)

    def _stoj_plynne(self):
        """Stawia dochodzenia liczb na wartościach docelowych i gasi ich zegary."""
        for plynne in (self._pl_kwota, self._pl_km, self._pl_dni, self._pl_wybor,
                       self._pl_kursor, self._pl_stan, self._pl_wolne):
            plynne.dokoncz()

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
        kafle = self._kafle()
        self._uklad = self._policz_uklad(kafle)
        self._rysuj_naglowek(p)
        self._rysuj_szyne(p, kafle)
        wyjatki = {self._dzis, self._wybrany, self._wybrany_stary} - {0}
        gorne = []
        for i, r in enumerate(kafle):
            d = self._dni[i]
            if d.data.day in wyjatki:
                gorne.append((i, r, d))
            else:
                self._rysuj_kafel(p, r, d, i)
        for i, r, d in gorne:
            self._rysuj_kafel(p, r, d, i)
        # plakietki idą na wierzch, żeby sąsiedni kafel ich nie przykrył
        wejscie = self._pl_stan.teraz()
        if wejscie > 0.01 and self._uklad["plakietki"]:
            for i, r in enumerate(kafle):
                d = self._dni[i]
                if d.wolny or d.postoje == 0 or self._wylaczony(d):
                    continue
                ru = self._uniesienie(r, d)
                # pod plakietką DZIŚ nie ma miejsca — tam znacznik idzie na dół kafla
                prom = min(PROMIEN, ru.width() * 0.26)
                obrys = QPainterPath()
                obrys.addRoundedRect(ru, prom, prom)
                self._plakietka_pdf(p, ru, obrys, wejscie)
                if d.podpisany:
                    self._znacznik_podpisu(p, ru, wejscie)
        for i, r, d in gorne:
            if d.data.day == self._dzis:
                self._plakietka_dzis(p, self._uniesienie(r, d))
        p.end()

    def _udzial_wyboru(self, numer):
        """Ile dany dzień jest „wybrany”: 1 dla wybranego, 0 dla reszty, po drodze ułamek."""
        if not numer:
            return 0.0
        t = self._pl_wybor.teraz()
        if numer == self._wybrany:
            return t
        if numer == self._wybrany_stary and numer != self._wybrany:
            return 1.0 - t
        return 0.0

    def _uniesienie(self, r, d):
        u = self._udzial_wyboru(d.data.day)
        if u <= 0.002:
            return r
        u = max(0.0, u)          # sprężyna potrafi zejść pod zero — kafel nie tonie
        # rozepchnięcie na boki skalujemy szerokością kafla: te same 1,2 px na
        # kaflu dziesięciopikselowym robiły z wybranego dnia inny rozmiar,
        # a nie ten sam kafel uniesiony
        bok = 1.2 * u * min(1.0, r.width() / 24.0)
        return r.adjusted(-bok, -4.0 * u, bok, 1.2 * u)

    def _rysuj_naglowek(self, p):
        y = PAD_GORA + 12.5

        wszystkie = self._zbior["dni_wszystkie"]
        # liczba osobno (stała szerokość, pełna jasność), jednostka osobno i ciszej
        grupy = [(dane.zl(self._pl_kwota.teraz(), grosze=False), "zł", ""),
                 (dane.zl(self._pl_km.teraz(), grosze=False), "km", ""),
                 (str(int(round(self._pl_dni.teraz()))), "", "z %d dni" % wszystkie)]
        fm_w = QFontMetricsF(czcionka(12, 700, mono=True))
        fm_j = QFontMetricsF(czcionka(11, 600))
        fm_s = QFontMetricsF(czcionka(12, 400))
        x = self.width() - PAD_BOK
        for wart, jedn, sufiks in reversed(grupy):
            if sufiks:
                x -= fm_s.horizontalAdvance(sufiks)
                tekst(p, x, y, sufiks, kolor=TEKST_2, rozmiar=12)
                x -= 5.0
            if jedn:
                x -= fm_j.horizontalAdvance(jedn)
                tekst(p, x, y, jedn, kolor=z_alfa(TEKST_2, 200), rozmiar=11, waga=600)
                x -= 3.0
            x -= fm_w.horizontalAdvance(wart)
            tekst(p, x, y, wart, kolor=TEKST, rozmiar=12, waga=700, mono=True)
            x -= 17.0
        liczby_od = x + 17.0

        # tytuł ustępuje liczbom: przy wąskim oknie skraca się, zamiast wchodzić pod nie
        napis = "TAŚMA MIESIĄCA"
        for kandydat in ("TAŚMA MIESIĄCA", "TAŚMA", ""):
            szer = QFontMetricsF(czcionka(12, 600, naglowek=True,
                                          odstep=1.3)).horizontalAdvance(kandydat)
            if PAD_BOK + szer + 14.0 <= liczby_od:
                napis = kandydat
                break
        else:
            napis = ""
        if napis:
            tekst(p, PAD_BOK, y, napis, kolor=z_alfa(ZIELEN, 60),
                  rozmiar=12, waga=600, naglowek=True, odstep=1.3)
            tekst(p, PAD_BOK, y, napis, kolor=MIETA,
                  rozmiar=12, waga=600, naglowek=True, odstep=1.3)
            tytul_do = PAD_BOK + QFontMetricsF(
                czcionka(12, 600, naglowek=True, odstep=1.3)).horizontalAdvance(napis)
        else:
            tytul_do = PAD_BOK
        # gdzie nagłówek jest zajęty — plakietka DZIŚ nie może tam wejść
        self._zajete_naglowka = (tytul_do + 14.0, liczby_od - 14.0)

    def _rysuj_szyne(self, p, kafle):
        """Cienka szyna pod kaflami: szwy tygodni i świecące odcinki dni w trasie."""
        if not kafle:
            return
        pas = self._pas()
        y = pas.bottom() + 6.5
        if self.height() - y < 5.0:
            return
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(z_alfa(BIEL, 22), 1.0))
        p.drawLine(QPointF(pas.left(), y), QPointF(pas.right(), y))
        for i, r in enumerate(kafle):
            d = self._dni[i]
            if d.data.weekday() == 0 and i > 0:      # szew tygodnia
                x = r.left() - ODSTEP / 2.0
                p.setPen(QPen(z_alfa(BIEL, 52), 1.0))
                p.drawLine(QPointF(x, y - 5.0), QPointF(x, y + 1.0))
            if self._wylaczony(d) or d.wolny or d.postoje == 0:
                continue
            dzis = (d.data.day == self._dzis)
            kolor = CYJAN if dzis else ZIELEN
            wciecie = min(2.0, r.width() * 0.10)
            odcinek = QPainterPath()
            odcinek.moveTo(r.left() + wciecie, y)
            odcinek.lineTo(r.right() - wciecie, y)
            poswiata_linii(p, odcinek, kolor, ((5.0, 18), (2.6, 40),
                                               (1.3, 235 if dzis else 190)))
        self._klin_wyboru(p, y)

    def _klin_wyboru(self, p, y):
        """Drugi znak dnia wybranego: biały klin na szynie pod kaflem.

        Sama obręcz kafla to za mało — przy dniu bez trasy wybór ginął wśród
        wygaszonych sąsiadów. Klin widać niezależnie od barwy kafla.
        """
        for numer in (self._wybrany_stary, self._wybrany):
            u = self._udzial_wyboru(numer)
            if u <= 0.02:
                continue
            r = self._rect_dnia(numer)
            if r is None:
                continue
            u = max(0.0, min(1.0, u))
            sr = r.center().x()
            bok = max(2.0, min(4.2, r.width() * 0.20))
            klin = QPainterPath()
            klin.moveTo(sr, y - 5.6 * u)
            klin.lineTo(sr - bok, y + 1.2)
            klin.lineTo(sr + bok, y + 1.2)
            klin.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.fillPath(klin, z_alfa(BIEL, int(252 * u)))
            odcinek = QPainterPath()
            odcinek.moveTo(r.left() + 1.0, y)
            odcinek.lineTo(r.right() - 1.0, y)
            poswiata_linii(p, odcinek, BIEL, ((3.0, int(12 * u)),
                                              (1.2, int(88 * u))))

    def _aureola(self, p, sciezka, kolor, warstwy):
        p.setBrush(Qt.BrushStyle.NoBrush)
        for szer, alfa in warstwy:
            p.setPen(QPen(z_alfa(kolor, alfa), szer))
            p.drawPath(sciezka)

    # ── materiał kafla ───────────────────────────────────────────────
    def _cien_pod_kaflem(self, p, r, prom, sila, przesun, warstwy=None):
        """Kilka warstw zamiast rozmycia — kafel ma się odklejać od tła."""
        p.setPen(Qt.PenStyle.NoPen)
        for rozrost, alfa in (warstwy or ((3.4, 0.30), (1.9, 0.52), (0.7, 1.0))):
            s = QPainterPath()
            s.addRoundedRect(r.adjusted(-rozrost, -rozrost + przesun,
                                        rozrost, rozrost + przesun),
                             prom + rozrost, prom + rozrost)
            p.fillPath(s, z_alfa(CZERN, sila * alfa))

    def _korpus(self, p, r, sciezka, prom, jasnosc=1.0, akcent=None, moc=0.0,
                uniesienie=0.0):
        """Wypukła płaszczyzna: gradient pionowy, barwa stanu, kopuła światła, cień przy dnie.

        ``jasnosc`` steruje kryciem (dzień bez trasy jest przezroczysty i cofa
        się w tło), ``uniesienie`` — barwą materiału (dzień wybrany i dzisiejszy
        wychodzą do światła). Barwa stanu idzie pod kopułę, więc zielony dzień
        dalej jest wybrzuszony, a nie zamalowany na płasko.
        """
        s = max(0.0, min(1.0, uniesienie))
        gora = _mieszaj(KORPUS_GORA, KORPUS_GORA_J, s)
        srod = _mieszaj(KORPUS_SROD, KORPUS_SROD_J, s)
        dol = _mieszaj(KORPUS_DOL, KORPUS_DOL_J, s)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.00, z_alfa(gora, gora.alpha() * jasnosc))
        g.setColorAt(0.46, z_alfa(srod, srod.alpha() * jasnosc))
        g.setColorAt(1.00, z_alfa(dol, dol.alpha()))
        p.fillPath(sciezka, QBrush(g))

        if akcent is not None and moc > 0.0:
            a = QLinearGradient(r.topLeft(), r.bottomLeft())
            a.setColorAt(0.00, z_alfa(akcent, 58 * moc))
            a.setColorAt(0.55, z_alfa(akcent, 30 * moc))
            a.setColorAt(1.00, z_alfa(akcent, 12 * moc))
            p.fillPath(sciezka, QBrush(a))

        # kopuła — źródło światła tuż nad kaflem, płaszczyzna wybrzusza się do widza
        h = r.height()
        kopula = QRadialGradient(QPointF(r.center().x(), r.top() - h * 0.52), h * 1.30)
        kopula.setColorAt(0.00, z_alfa(BIEL, 30 * jasnosc))
        kopula.setColorAt(0.55, z_alfa(BIEL, 12 * jasnosc))
        kopula.setColorAt(1.00, z_alfa(BIEL, 0))
        p.fillPath(sciezka, QBrush(kopula))
        # dno kafla ucieka w cień
        dno = QLinearGradient(QPointF(0, r.bottom() - h * 0.42), QPointF(0, r.bottom()))
        dno.setColorAt(0.0, z_alfa(CZERN, 0))
        dno.setColorAt(1.0, z_alfa(CZERN, 72))
        p.fillPath(sciezka, QBrush(dno))

    def _krawedz_swiatla(self, p, r, prom, sila=1.0):
        """Wewnętrzna krawędź: mocne światło u góry, cienkie odbicie u dołu."""
        if r.width() < 5.0 or r.height() < 5.0 or sila <= 0.0:
            return
        wew = QPainterPath()
        pw = max(0.0, prom - 0.6)
        wew.addRoundedRect(r.adjusted(0.6, 0.6, -0.6, -0.6), pw, pw)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.00, z_alfa(BIEL, 132 * sila))
        g.setColorAt(0.16, z_alfa(BIEL, 40 * sila))
        g.setColorAt(0.46, z_alfa(BIEL, 0))
        g.setColorAt(0.97, z_alfa(BIEL, 0))
        g.setColorAt(1.00, z_alfa(BIEL, 30 * sila))
        pen = QPen(QBrush(g), 1.0)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen)
        p.drawPath(wew)

    def _rysuj_kafel(self, p, rbaza, d, i):
        dzis = (d.data.day == self._dzis)
        wyb_u = self._udzial_wyboru(d.data.day)
        wyb = wyb_u > 0.02
        wyl = self._wylaczony(d)
        ma_trase = (not wyl) and (not d.wolny) and d.postoje > 0
        kur = self._udzial_kursora(i)       # 0…1, z krótkim przejściem
        r = self._uniesienie(rbaza, d)
        u = max(0.0, min(1.0, wyb_u))       # do jasności: bez przestrzelenia

        prom = min(PROMIEN, r.width() * 0.26)
        sciezka = QPainterPath()
        sciezka.addRoundedRect(r, prom, prom)

        weekend = d.data.weekday() >= 5

        # tło kafla
        wysoko = max(u, 1.0 if dzis else 0.0)
        if wyl:
            p.fillPath(sciezka, z_alfa(BIEL, 7))
        else:
            self._cien_pod_kaflem(p, r, prom,
                                  sila=48 + 64 * wysoko,
                                  przesun=2.0 + 3.0 * wysoko,
                                  warstwy=None if (wysoko > 0.02 or ma_trase)
                                  else ((2.2, 0.40), (0.8, 1.0)))
            # dzień bez trasy jest cofnięty w tło, dzień w trasie wychodzi do przodu
            if ma_trase:
                jasnosc = 0.92 + 0.22 * wysoko
            elif weekend:
                jasnosc = 0.34 + 0.62 * wysoko
            else:
                jasnosc = 0.52 + 0.46 * wysoko
            jasnosc += 0.10 * kur
            if ma_trase or dzis:
                akcent = CYJAN if dzis else ZIELEN
                moc = (0.85 + 0.35 * wysoko) if ma_trase else 0.45
            elif u > 0.02:
                # wybrany dzień bez trasy: chłodne światło, żeby nie był dziurą
                akcent, moc = MIETA, 0.55 * u
            else:
                akcent, moc = None, 0.0
            self._korpus(p, r, sciezka, prom, jasnosc, akcent, moc,
                         uniesienie=max(u, 0.55 if dzis else 0.0) + 0.22 * kur)

        # obwódka
        if dzis:
            puls = self._puls()
            self._aureola(p, sciezka, CYJAN,
                          ((10.0, 8 + int(10 * puls)), (5.0, 20 + int(14 * puls)),
                           (2.6, 44 + int(16 * puls))))
            pen = QPen(z_alfa(CYJAN, 205 + int(50 * puls)), 1.5 + 0.3 * puls)
        elif wyb:
            if ma_trase:
                self._aureola(p, sciezka, ZIELEN, ((7.0, int(14 * u)), (3.5, int(24 * u))))
            pen = QPen(z_alfa(TEKST, 120 - int(60 * u)), 1.0)
        elif ma_trase:
            self._aureola(p, sciezka, ZIELEN, ((6.0, 10), (3.0, 18)))
            pen = QPen(z_alfa(ZIELEN, 130), 1.2)
        elif wyl:
            pen = QPen(z_alfa(BURSZTYN, 100 + int(30 * kur)), 1.0)
            # kreskowana obwódka na kaflu szerokim na trzynaście pikseli robi
            # się kratką — tam wystarczy spokojna, ciągła linia
            if self._uklad["miniatura"]:
                pen.setStyle(Qt.PenStyle.CustomDashLine)
                pen.setDashPattern([3.0, 3.0])
        else:
            spok = 14 if weekend else 26
            pen = QPen(z_alfa(BIEL, spok + int((60 - spok) * kur)), 1.0)
        if kur > 0.02 and not (wyb or dzis) and ma_trase:
            pen.setColor(z_alfa(MIETA, 130 + int(80 * kur)))
        blysk = self._blysk_wolnego(d)
        if blysk > 0.01:
            self._aureola(p, sciezka, BURSZTYN if wyl else ZIELEN,
                          ((9.0, int(34 * blysk)), (4.5, int(58 * blysk))))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(pen)
        p.drawPath(sciezka)
        if not wyl:
            self._krawedz_swiatla(p, r, prom,
                                  sila=(0.85 if ma_trase else 0.60) + 0.50 * wysoko)
        if wyb:
            # obręcz wybranego dnia jest światłem, nie plastikiem: jaśnieje u góry.
            # Pod nią miękka biała aureola — dzień bez trasy też ma się wybijać.
            self._aureola(p, sciezka, BIEL, ((8.0, int(16 * u)), (4.0, int(26 * u))))
            zew = QPainterPath()
            odsun = 2.0
            zew.addRoundedRect(r.adjusted(-odsun, -odsun, odsun, odsun),
                               prom + odsun, prom + odsun)
            g = QLinearGradient(QPointF(0, r.top() - odsun), QPointF(0, r.bottom() + odsun))
            g.setColorAt(0.0, z_alfa(BIEL, 250 * u))
            g.setColorAt(0.5, z_alfa(TEKST, 200 * u))
            g.setColorAt(1.0, z_alfa(TEKST_2, 135 * u))
            p.setPen(QPen(QBrush(g), 1.8))
            p.drawPath(zew)
        if dzis:
            puls = self._puls()
            obw = QPainterPath()
            odsun = 2.2 + 1.6 * puls
            obw.addRoundedRect(r.adjusted(-odsun, -odsun, odsun, odsun),
                               prom + odsun, prom + odsun)
            p.setPen(QPen(z_alfa(CYJAN, 26 + int(58 * puls)), 1.1))
            p.drawPath(obw)

        # miejsce zajęte przez plakietki (rysowane osobno, na wierzchu)
        z_lewej = 0.0
        z_prawej = 0.0
        wejscie = self._pl_stan.teraz()
        if self._uklad["plakietki"] and wejscie > 0.01 and ma_trase:
            # miejsce oddajemy stopniowo, razem z wchodzącą plakietką —
            # inaczej numer dnia przeskakiwał w połowie przejścia
            z_prawej = 8.0 * wejscie
            if d.podpisany:
                z_lewej = 5.0 * wejscie

        # 1. stopień: numer dnia (skrót dnia tygodnia obok, ciszej)
        self._rysuj_numer(p, r, d, dzis, wyb, u, ma_trase, wyl, weekend,
                          z_lewej - z_prawej)

        # 2. stopień: miniatura trasy albo przekreślenie dnia wyłączonego
        if self._uklad["miniatura"]:
            pole = QRectF(r.left() + 4.0, r.top() + r.height() * 0.31,
                          r.width() - 8.0, r.height() * 0.29)
            if ma_trase:
                self._rysuj_miniature(p, sciezka, pole, d, CYJAN if dzis else
                                      (MIETA if wyb else ZIELEN), dzis or u > 0.5)
            elif wyl:
                p.setPen(QPen(z_alfa(BURSZTYN, 70), 1.0))
                p.drawLine(QPointF(pole.left() + 3.5, pole.bottom() + 1.0),
                           QPointF(pole.right() - 3.5, pole.top() - 1.0))
        elif wyl:
            sr_y = r.top() + r.height() * 0.52
            p.setPen(QPen(z_alfa(BURSZTYN, 80), 1.0))
            p.drawLine(QPointF(r.left() + 2.0, sr_y + 2.0),
                       QPointF(r.right() - 2.0, sr_y - 2.0))

        # 3. stopień: kwota — a gdy na nią nie ma miejsca, słupek jej wartości
        if ma_trase:
            if self._uklad["kwota"][0]:
                self._rysuj_kwote(p, r, d, dzis or wyb)
            else:
                self._slupek_wartosci(p, r, d, CYJAN if dzis else
                                      (BIEL if wyb else ZIELEN))
        elif wyl:
            self._napis_wolne(p, r)

    def _rysuj_numer(self, p, r, d, dzis, wyb, u, ma_trase, wyl, weekend, przesun):
        """Numer dnia prowadzi kafel; skrót dnia tygodnia stoi obok, w drugim planie."""
        tryb, rozm = self._uklad["etykieta"]
        numer = str(d.data.day)
        skrot = dane.DNI_PL[d.data.weekday()]
        r_skrot = _rozmiar_skrotu(rozm)

        if dzis:
            kol_numer, kol_skrot = BIEL, z_alfa(MIETA, 215)
        elif wyb:
            kol_numer = z_alfa(TEKST, 165 + int(90 * u))
            kol_skrot = z_alfa(TEKST_2, 110 + int(90 * u))
        elif wyl:
            kol_numer, kol_skrot = z_alfa(BURSZTYN, 220), z_alfa(BURSZTYN, 125)
        elif ma_trase:
            kol_numer, kol_skrot = z_alfa(TEKST, 244), z_alfa(MIETA, 155)
        elif weekend:
            kol_numer, kol_skrot = z_alfa(TEKST_3, 150), z_alfa(TEKST_3, 95)
        else:
            kol_numer, kol_skrot = z_alfa(TEKST_2, 205), z_alfa(TEKST_3, 130)

        szer_n = QFontMetricsF(czcionka(rozm, 700, mono=True)).horizontalAdvance(numer)
        szer_s = (QFontMetricsF(czcionka(r_skrot, 600)).horizontalAdvance(skrot)
                  if tryb == "pelny" else 0.0)
        calosc = szer_n + (ODSTEP_ETYKIETY + szer_s if tryb == "pelny" else 0.0)
        x = r.center().x() + przesun * 0.5 - calosc / 2.0
        y = self._y_numeru(r, rozm)
        tekst(p, x, y, numer, kolor=kol_numer, rozmiar=rozm, waga=700, mono=True)
        if tryb == "pelny":
            tekst(p, x + szer_n + ODSTEP_ETYKIETY, y, skrot, kolor=kol_skrot,
                  rozmiar=r_skrot, waga=600)

    def _y_numeru(self, r, rozm):
        """Bez miniatury numer i kwota stoją blisko siebie w środku kafla —
        inaczej wąski kafel robi się pustą rurą z napisem na każdym końcu."""
        if self._uklad["miniatura"]:
            return r.top() + rozm + 2.0
        return r.center().y() - 2.0

    def _y_dolu(self, r):
        return r.bottom() - 8.0 if self._uklad["miniatura"] else r.center().y() + 13.0

    def _napis_wolne(self, p, r):
        """„wolne” tylko wtedy, gdy naprawdę się mieści — inaczej sama kreska."""
        wolne = r.width() - 5.0
        for napis, rozm in (("wolne", 9), ("wolne", 8), ("—", 9), ("—", 8)):
            if QFontMetricsF(czcionka(rozm, 500)).horizontalAdvance(napis) <= wolne:
                szer_n = QFontMetricsF(czcionka(rozm, 500)).horizontalAdvance(napis)
                tekst(p, r.center().x() - szer_n / 2.0, self._y_dolu(r), napis,
                      kolor=BURSZTYN, rozmiar=rozm, waga=500)
                return

    def _rysuj_kwote(self, p, r, d, mocno):
        """Liczba czcionką o stałej szerokości, „zł” cicho obok — drugi plan kafla."""
        liczba = dane.zl(d.kwota, grosze=False)
        rozm, z_jednostka = self._uklad["kwota"]
        y = self._y_dolu(r)
        kol = z_alfa(TEKST, 252 if mocno else 224)
        szer_l = QFontMetricsF(czcionka(rozm, 700, mono=True)).horizontalAdvance(liczba)
        if not z_jednostka:
            tekst(p, r.center().x() - szer_l / 2.0, y, liczba, kolor=kol,
                  rozmiar=rozm, waga=700, mono=True)
            return
        r_j = max(7, rozm - 3)
        szer_j = QFontMetricsF(czcionka(r_j, 600)).horizontalAdvance("zł")
        x = r.center().x() - (szer_l + 2.0 + szer_j) / 2.0
        tekst(p, x, y, liczba, kolor=kol, rozmiar=rozm, waga=700, mono=True)
        tekst(p, x + szer_l + 2.0, y, "zł", kolor=z_alfa(TEKST_2, 175),
              rozmiar=r_j, waga=600)

    def _slupek_wartosci(self, p, r, d, kolor):
        """Kwota dnia jako słupek — wchodzi tam, gdzie na cyfry nie ma już miejsca."""
        if self._maks_kwota <= 0.0:
            return
        pelna = max(3.0, r.width() - 6.0)
        udzial = max(0.14, min(1.0, d.kwota / self._maks_kwota))
        y = (r.bottom() - 7.0) if self._uklad["miniatura"] else (r.center().y() + 8.0)
        x0 = r.center().x() - pelna / 2.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(z_alfa(BIEL, 28)))
        p.drawRoundedRect(QRectF(x0, y, pelna, 2.6), 1.3, 1.3)
        p.setBrush(QBrush(z_alfa(kolor, 225)))
        p.drawRoundedRect(QRectF(x0, y, pelna * udzial, 2.6), 1.3, 1.3)
        p.setBrush(Qt.BrushStyle.NoBrush)

    @staticmethod
    def _szer_etykiety(d, tryb, rozm):
        """Szerokość nagłówka kafla w danym trybie: „12 wt” albo samo „12”."""
        szer = QFontMetricsF(czcionka(rozm, 700, mono=True)).horizontalAdvance(
            str(d.data.day))
        if tryb == "pelny":
            szer += ODSTEP_ETYKIETY + QFontMetricsF(
                czcionka(_rozmiar_skrotu(rozm), 600)).horizontalAdvance(
                    dane.DNI_PL[d.data.weekday()])
        return szer

    def _policz_uklad(self, kafle):
        """Jeden wariant napisów dla całej taśmy — kafle nie mogą się różnić.

        Rozmiar dobiera najszerszy napis w miesiącu, nie pojedynczy dzień.
        Przy zwężaniu okna kolejne stopnie odpadają: „zł”, kwota, miniatura,
        skrót dnia tygodnia. Nic nigdy nie wychodzi poza kafel — jeżeli napis
        się nie mieści, po prostu go nie ma.
        """
        szer = kafle[0].width() if kafle else 0.0
        # Dobór napisów to kilkaset pomiarów czcionki; przy najeżdżaniu myszą
        # paintEvent leci kilkadziesiąt razy na sekundę, a wynik się nie zmienia.
        klucz = (round(szer, 2), self._stan, self._wersja_danych)
        if self._uklad_klucz == klucz:
            return self._uklad
        plakietki = szer >= PROG_PLAKIETEK
        zapas = 7.0 if (self._stan == "po_generacji" and plakietki) else 0.0
        maks = max(4.0, szer - 5.0 - zapas)

        # numer dnia prowadzi: mono, największy stopień, jaki się mieści
        etykieta = ("numer", 7)
        for tryb, rozmiary in (("pelny", (12, 11, 10)),
                               ("numer", (12, 11, 10, 9, 8, 7))):
            for rozm in rozmiary:
                if all(self._szer_etykiety(d, tryb, rozm) <= maks for d in self._dni):
                    etykieta = (tryb, rozm)
                    break
            else:
                continue
            break

        # kwota o stopień niżej od numeru — drugi plan, nie pierwszy
        kwoty = [dane.zl(d.kwota, grosze=False) for d in self._dni
                 if not self._wylaczony(d) and not d.wolny and d.postoje > 0]
        kwota = (0, False)                     # 0 = kwota się nie mieści
        if kwoty:
            wolne = max(4.0, szer - 6.0)
            gorny = max(8, min(11, etykieta[1] - 1))
            # ósemka to dno czytelności cyfr; niżej kwotę zastępuje słupek
            stopnie = [r for r in (11, 10, 9, 8) if r <= gorny]
            # Większa liczba bez „zł” bije mniejszą liczbę ze „zł”: liczy się
            # kwota, jednostka jest dopiskiem. Kolejność prób idzie więc
            # stopniami w dół, a w każdym stopniu najpierw z jednostką.
            szukaj = []
            for r in stopnie:
                szukaj.append((r, True))
                szukaj.append((r, False))
            for rozm, z_jedn in szukaj:
                fm = QFontMetricsF(czcionka(rozm, 700, mono=True))
                potrzeba = max(fm.horizontalAdvance(k) for k in kwoty)
                if z_jedn:
                    potrzeba += 2.0 + QFontMetricsF(
                        czcionka(max(7, rozm - 3), 600)).horizontalAdvance("zł")
                if potrzeba <= wolne:
                    kwota = (rozm, z_jedn)
                    break
        self._uklad_klucz = klucz
        return {"etykieta": etykieta, "kwota": kwota,
                "miniatura": szer >= PROG_MINIATURY, "plakietki": plakietki,
                "szerokosc": szer}

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
        # cienka nitka z poświatą zamiast grubej krechy
        poswiata_linii(p, sc, kolor, ((4.4, 14 if mocno else 9),
                                      (2.3, 34 if mocno else 24),
                                      (1.1, 240 if mocno else 205)))
        self._kropki_przystankow(p, punkty, kolor, mocno)
        p.restore()

    def _kropki_przystankow(self, p, punkty, kolor, mocno):
        """Przystanki jako drobne kropki — rzedniejemy je, gdy trasa jest gęsta."""
        r_kropki = 1.25 if mocno else 1.1
        krok = 1
        if len(punkty) > 2:
            dlugosci = [math.hypot(punkty[i + 1].x() - punkty[i].x(),
                                   punkty[i + 1].y() - punkty[i].y())
                        for i in range(len(punkty) - 1)]
            sredni = sum(dlugosci) / len(dlugosci)
            if sredni < 3.2:
                krok = max(2, int(math.ceil(3.2 / max(sredni, 0.6))))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(z_alfa(kolor, 190 if mocno else 150)))
        for i in range(krok, len(punkty), krok):
            p.drawEllipse(punkty[i], r_kropki, r_kropki)
        # baza — jaśniejszy punkt z poświatą
        punkt_swiatla(p, punkty[0], 3.6, kolor, 150 if mocno else 110)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(TEKST if mocno else MIETA))
        p.drawEllipse(punkty[0], 1.7, 1.7)

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
        # plakietka trzyma się w oknie i nie wchodzi pod nagłówek — przy wąskiej
        # taśmie zostaje z niej sam dziobek
        lewa = max(PAD_BOK, min(r.center().x() - szer / 2.0,
                                self.width() - PAD_BOK - szer))
        zaj_a, zaj_b = self._zajete_naglowka
        koliduje = (lewa < zaj_a) or (lewa + szer > zaj_b)
        if koliduje or r.width() < 12.0 or szer > self.width() - 2 * PAD_BOK:
            self._dziobek_dzis(p, r)
            return
        pr = QRectF(lewa, r.top() - 19.0, szer, wys)
        # dziobek
        czubek = max(pr.left() + 6.0, min(r.center().x(), pr.right() - 6.0))
        dzb = QPainterPath()
        dzb.moveTo(czubek - 4.0, pr.bottom() - 1.0)
        dzb.lineTo(czubek + 4.0, pr.bottom() - 1.0)
        dzb.lineTo(r.center().x(), r.top() + 1.5)
        dzb.closeSubpath()
        sc = QPainterPath()
        sc.addRoundedRect(pr, wys / 2.0, wys / 2.0)
        sc = sc.united(dzb)
        puls = self._puls()
        self._aureola(p, sc, CYJAN, ((10.0, 18 + int(16 * puls)), (5.0, 40 + int(24 * puls))))
        p.setPen(Qt.PenStyle.NoPen)
        g = QLinearGradient(pr.topLeft(), pr.bottomLeft())
        g.setColorAt(0.0, CYJAN.lighter(118))
        g.setColorAt(1.0, CYJAN.darker(108))
        p.fillPath(sc, QBrush(g))
        p.setPen(QPen(z_alfa(BIEL, 90), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(sc)
        p.setPen(QPen(TLO_GORA))
        p.setFont(f)
        p.drawText(pr, int(Qt.AlignmentFlag.AlignCenter), "DZIŚ")

    def _dziobek_dzis(self, p, r):
        """Wąska taśma: zamiast plakietki sam cyjanowy dziobek nad kaflem."""
        puls = self._puls()
        sr = r.center().x()
        bok = max(2.6, min(5.0, r.width() * 0.26))
        dzb = QPainterPath()
        dzb.moveTo(sr, r.top() + 1.0)
        dzb.lineTo(sr - bok, r.top() - 6.0)
        dzb.lineTo(sr + bok, r.top() - 6.0)
        dzb.closeSubpath()
        self._aureola(p, dzb, CYJAN, ((6.0, 30 + int(30 * puls)),
                                      (3.0, 60 + int(40 * puls))))
        p.setPen(Qt.PenStyle.NoPen)
        g = QLinearGradient(QPointF(0, r.top() - 6.0), QPointF(0, r.top() + 1.0))
        g.setColorAt(0.0, CYJAN.lighter(122))
        g.setColorAt(1.0, CYJAN.darker(106))
        p.fillPath(dzb, QBrush(g))

    def _plakietka_pdf(self, p, r, obrys=None, wejscie=1.0):
        """Gotowy dokument to zagięty róg kartki, nie naklejka z napisem.

        Naklejka „PDF” w rogu kafla właziła na numer dnia — przy trzydziestu
        kaflach nie ma miejsca na czwarty napis. Zagięcie rogu czyta się od razu
        i nie zabiera ani jednego piksela tekstowi.
        """
        w = max(0.0, min(1.0, wejscie))
        if w <= 0.01:
            return
        bok = max(6.0, min(12.0, r.width() * 0.30)) * (0.45 + 0.55 * w)
        rog = QPointF(r.right() - 1.0, r.top() + 1.0)
        zagiecie = QPainterPath()
        zagiecie.moveTo(rog.x() - bok, rog.y())
        zagiecie.lineTo(rog.x(), rog.y())
        zagiecie.lineTo(rog.x(), rog.y() + bok)
        zagiecie.closeSubpath()
        p.save()
        if obrys is not None:
            p.setClipPath(obrys)
        p.setPen(Qt.PenStyle.NoPen)
        g = QLinearGradient(QPointF(rog.x() - bok, rog.y()),
                            QPointF(rog.x(), rog.y() + bok))
        g.setColorAt(0.0, z_alfa(MIETA, 255 * w))
        g.setColorAt(1.0, z_alfa(ZIELEN, 235 * w))
        p.fillPath(zagiecie, QBrush(g))
        # linia zagięcia — róg ma grubość
        pen = QPen(z_alfa(TLO_GORA, 190 * w), 1.0)
        p.setPen(pen)
        p.drawLine(QPointF(rog.x() - bok, rog.y()), QPointF(rog.x(), rog.y() + bok))
        p.restore()
        self._aureola(p, zagiecie, ZIELEN, ((6.0, int(30 * w)), (3.0, int(52 * w))))

    def _znacznik_podpisu(self, p, r, wejscie=1.0):
        """Podpisany dzień dostaje grzbiet: zieloną krawędź przy lewym boku kafla.

        Kółko z ptaszkiem w rogu właziło na numer dnia — na kaflu szerokim
        na trzydzieści dziewięć pikseli nie ma miejsca na dwie plakietki obok
        siebie. Grzbiet widać z odległości i nie zabiera nic tekstowi.
        """
        w = max(0.0, min(1.0, wejscie))
        if w <= 0.01 or r.width() < 10.0:
            return
        szer = 2.4
        x = r.left() + 2.6
        wys = max(6.0, (r.height() - 12.0) * w)
        pasek = QRectF(x - szer / 2.0, r.center().y() - wys / 2.0, szer, wys)
        sc = QPainterPath()
        sc.addRoundedRect(pasek, szer / 2.0, szer / 2.0)
        self._aureola(p, sc, ZIELEN, ((6.0, int(28 * w)), (3.0, int(46 * w))))
        g = QLinearGradient(pasek.topLeft(), pasek.bottomLeft())
        g.setColorAt(0.0, z_alfa(MIETA, 255 * w))
        g.setColorAt(1.0, z_alfa(ZIELEN, 235 * w))
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(sc, QBrush(g))


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
    tasma.zatrzymaj_animacje()      # powtarzalny zrzut: żadnego ruchu w tle
    app.processEvents()
    okno.grab().save("zrzut_tasma.png")

    tasma.ustaw_stan("po_generacji")
    app.processEvents()
    okno.grab().save("zrzut_tasma_po.png")

    # wąskie okno — tu widać, jak kafel schodzi stopniami
    tasma.ustaw_stan("zwykly")
    okno.resize(640, 200)
    app.processEvents()
    tasma.zatrzymaj_animacje()
    app.processEvents()
    okno.grab().save("zrzut_tasma_wasko.png")
    print("zapisano zrzut_tasma.png, zrzut_tasma_po.png i zrzut_tasma_wasko.png")

    if "--pokaz" in sys.argv:
        tasma.wznow_animacje()
        sys.exit(app.exec())
