# -*- coding: utf-8 -*-
"""Prawa strona ekranu prototypu: trójwymiarowa mapa regionu i kartka delegacji.

Mapa pokazuje REGION, a nie miasto, a jedna jednostka świata to
``KM_NA_JEDNOSTKE`` kilometra. Kadr należy do TRASY pokazywanego dnia: obejmuje
bazę i przystanki z marginesem, a nie cały spis miast, który podaje program —
tych jest kilkaset wokół bazy i dzień zmieściłby się wtedy w ćwiartce obrazu.
Miejscowości spoza trasy dalej się rysują, jeśli wpadają w kadr: krajobraz ma
być zamieszkany, tylko kadr ma należeć do trasy. Gdy kartka delegacji leży na
mapie, kadr idzie w tę część widżetu, której kartka nie zasłania.

Raz kadr obejmuje czterdzieści kilometrów, a raz trzysta, więc ziarno pola,
wysokość garbu, szerokość drogi i słup światła nad przystankiem są ułamkami
ROZPIĘTOŚCI KADRU, a nie stałą liczbą kilometrów. Inaczej przy ciasnym kadrze
jedno pole zajęłoby pół ekranu. Podziałka mierzy teren i tych ułamków nie widzi.

Miejscowość jest zwartą plamą zabudowy — szeroką na kilometr albo dwa, przy
bazie na kilka — a nie skupiskiem wież. Prawdziwy obrys ma jednak w tej skali
kilka pikseli, więc znak osady dostaje próg czytelności, dokładnie tak, jak
robią to mapy od zawsze: rysowany znak jest większy od prawdziwego obrysu, ale
nigdy nie sięga sąsiada. Między plamami zostaje otwarty teren: pola o różnych
odcieniach, płaty lasu, rzeka i drogi. To krajobraz zajmuje większość kadru.

Scena ma trzy wymiary — punkt to trójka (x na wschód, y na północ, z nad
terenem) — a kamera patrzy na nią pod kątem ``KAT_KAMERY`` stopni od pionu.
Cały rzut liczy klasa :class:`Rzut` zwykłą matematyką kamery dziurkowej;
żadnej biblioteki 3D tu nie ma, bo być jej nie może — do dyspozycji jest
PyQt6 i biblioteka standardowa.

Co z tego wynika na obrazie:

* drogi i rzeka to pasy o stałej szerokości w świecie, więc na ekranie zbiegają
  się w głębi — to najtańszy i najczytelniejszy dowód perspektywy,
* teren to siatka działek zarzucona na miękkie wzniesienia; każda działka
  dostaje odcień od nachylenia względem światła, więc garb widać bez
  rysowania warstwic, a bliższa działka zasłania dalszą,
* lasy to ciemniejsze płaty o nieregularnej krawędzi, rozsiane między polami,
* przy każdej miejscowości leży plama zabudowy wielkości wynikającej z rangi,
  z kilkoma niskimi bryłami i rozsypanymi domami; plama ma próg czytelności
  w pikselach i górną granicę w odległości do najbliższej sąsiadki, więc dwie
  osady nigdy nie zlewają się w jedną dzielnicę,
* trasa dnia leży kilka jednostek nad gruntem i rzuca na niego własny cień,
* przystanki to pionowe słupy światła, tym wyższe, im więcej wizyt,
* podpisy miast są tabliczkami zwróconymi do widza — jako jedyne nie pochylają
  się razem z terenem, bo muszą pozostać czytelne; żadna nie nachodzi na drugą
  ani nie wychodzi poza widżet, a odsunięta dalej dostaje nitkę odniesienia,
* podziałka u dołu ma dwa ramiona — w poprzek kadru i w głąb — bo na
  pochylonym terenie ten sam kilometr zajmuje w głąb mniej pikseli; mierzy
  świat, a nie ekran, więc zgadza się z kilometrami, które liczy silnik.

Wszystko rysowane jest od najdalszego do najbliższego, bo tylko w tej
kolejności bliższe obiekty zasłaniają dalsze.

Obraz otwartego terenu zależy od DNIA: ziarno bierze się z daty i z nazw
odwiedzanych miejscowości. Ten sam dzień daje zawsze ten sam układ pól, lasów
i rzeki, inny dzień — inny. Rozmieszczenie tabliczek jest za to całkowicie
deterministyczne i od ziarna niezależne: nie ma w nim ani losowania, ani
zależności od kolejności iteracji po zbiorach, więc ta sama trasa zawsze daje
ten sam układ podpisów.

Rzut, teren, sieć dróg i zabudowa liczone są raz i siedzą w dwóch pixmapach
zależnych od rozmiaru widżetu i od ziarna dnia: osobno grunt z terenem,
osobno plamy zabudowy — bo cień trasy leży między nimi. Klatka animacji
dokłada do tego płynący blask, kreski powrotu i oddech bazy; sama nic nie
przelicza.

Zegary: MapaDnia i KartkaDelegacji mają ``ustaw_animacje(wlaczone)``.
Wyłączenie zatrzymuje zegar i ustawia stałą fazę — zrzuty są powtarzalne.
Zegary gasną też przy schowaniu i zamknięciu widżetu.

Prawdziwe współrzędne: :meth:`MapaDnia.ustaw_miasta` przyjmuje słownik
{nazwa: (szerokość, długość, ranga)} i rzutuje go na płaszczyznę mapy
z zachowaniem proporcji odległości. Tak podaje je nowy_wyglad — wprost
z geokodowania silnika. Bez tego wywołania mapa pracuje na ułamkowych
współrzędnych z proto_dane, dokładnie jak dotąd.
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
KAT_KAMERY = 52.0          # stopnie od pionu; 0 to widok z góry, 90 to widok z poziomu
# Odległość kamery rozstrzyga, jak bardzo bliższy kilometr jest na ekranie
# dłuższy od dalszego. Przy 330 jednostkach miejscowość przy dolnej krawędzi
# kadru wychodziła o trzy czwarte większa niż przy górnej i podziałka myliła
# się na takich parach nawet o 45%. Przy 700 ta różnica spada do 30%, a błąd
# odczytu do kilku procent — zbieżność dróg i pochylenie terenu zostają.
ODLEGLOSC_KAMERY = 700.0   # w jednostkach świata — im bliżej, tym mocniejsza zbieżność

# Układ miast w jednostkach świata. Kwadrat, a nie prostokąt: gdyby głębia
# była rozciągnięta, kilometr na północ znaczyłby na mapie co innego niż
# kilometr na wschód, a podziałka kłamałaby w połowie kierunków.
POLE_SWIATA_X = 200.0
POLE_SWIATA_Y = 200.0
# Ten sam przelicznik, co w proto_dane: 1,0 w układzie ułamkowym to 235 km.
# Cały kadr obejmuje więc rejon rzędu dwustu kilometrów.
KM_NA_JEDNOSTKE = 235.0 / POLE_SWIATA_X
JEDNOSTEK_NA_KM = 1.0 / KM_NA_JEDNOSTKE

# Światło: wektor wskazujący źródło, w świecie. Niskie z daje długie cienie.
SWIATLO_3D = (-0.56, 0.42, 0.60)
_DL_SWIATLA = math.sqrt(sum(k * k for k in SWIATLO_3D))
SWIATLO_JEDN = tuple(k / _DL_SWIATLA for k in SWIATLO_3D)

BARWA_MGLY = QColor(58, 88, 118)          # mgła odległości w głębi sceny
# Otwarty teren: kilka odcieni pola, żeby sąsiednie działki się różniły,
# i jeden wyraźnie ciemniejszy las.
BARWY_POL = (QColor(24, 40, 43), QColor(20, 34, 40), QColor(28, 44, 42),
             QColor(18, 30, 37), QColor(23, 37, 37), QColor(16, 27, 34),
             QColor(26, 40, 39))
BARWA_LASU = QColor(8, 20, 23)
# Plama zabudowy jest CIEMNIEJSZA od dachów, które na niej stoją — inaczej
# bryły robią się dziurami w jasnej płycie i nie widać na plamie ani jednego
# budynku. Ściana od cienia jest najciemniejsza, więc bryła ma trzy tony.
BARWA_PLAMY = QColor(58, 66, 78)          # zwarta zabudowa oglądana z regionu
BARWA_DACHU = QColor(122, 134, 148)
BARWA_SCIANY = QColor(52, 63, 79)
BARWA_BOKU = QColor(12, 18, 28)

# Miary krajobrazu podane w UŁAMKACH ROZPIĘTOŚCI KADRU, nie w kilometrach.
# Kadr idzie za trasą dnia, więc raz obejmuje czterdzieści kilometrów, a raz
# trzysta; gdyby działka pola miała zawsze dwadzieścia jeden kilometrów, przy
# ciasnym kadrze jedno pole zajęłoby pół ekranu, droga rozlałaby się na
# trzydzieści pikseli, a słup światła nad bazą wyszedłby poza obraz. Ułamki
# dobrane są tak, żeby przy kadrze dwustu kilometrów wyszły co do liczby te
# same miary, co dotąd: działka 21 km, kratka wzniesień 84 km, zasięg terenu
# 560 km, wznios trasy 7 km, słupy 42 / 15 / 8 km, droga 1,6 km, rzeka 1,3 km.
UDZIAL_KOMORKI_POLA = 0.0894      # bok jednej działki otwartego terenu
UDZIAL_KOMORKI_TERENU = 0.3574    # w tej kratce może stanąć jedno wzniesienie
UDZIAL_ZASIEGU_TERENU = 2.383     # dalej teren i tak ginie we mgle
UDZIAL_WZNIOSU_TRASY = 0.0298     # o tyle trasa unosi się nad gruntem
UDZIAL_SLUPA_BAZY = 0.1787        # wysokość słupa światła nad bazą
UDZIAL_SLUPA_PRZYSTANKU = 0.0638  # nad przystankiem z jedną wizytą
UDZIAL_SLUPA_WIZYTY = 0.0340      # każda kolejna wizyta podnosi słup o tyle
UDZIAL_DROGI = 0.0068             # szerokość pasa drogi w skali mapy
UDZIAL_RZEKI = 0.0055             # szerokość koryta
UDZIAL_GARBU = (0.0150, 0.0650)   # najniższe i najwyższe wzniesienie terenu
UDZIAL_LASU = 0.27                # jaka część działek jest lasem
BLISKO_KAMERY = 26.0              # bliżej niż tyle jednostek nic już nie rysujemy

# ── kadr dnia ────────────────────────────────────────────────────────
# Kadr obejmuje bazę i przystanki dnia z marginesem. Margines liczy się od
# rozpiętości samej trasy, a nie od ekranu: dzień rozrzucony i dzień ciasny
# mają wyglądać na tak samo „oprawione”. Próg pilnuje, żeby dzień z wizytami
# w promieniu pięciu kilometrów nie dał absurdalnego zbliżenia.
MARGINES_TRASY = 0.08         # luz z każdej strony, w ułamku rozpiętości trasy
NAJMNIEJSZY_KADR_KM = 30.0    # poniżej tej rozpiętości kadr już się nie zacieśnia
MARGINES_KADRU = 0.038        # oddech przy krawędziach widżetu
ODSTEP_OD_KARTKI = 0.022      # przerwa między kadrem a brzegiem kartki delegacji

# Ranga miejscowości → wielkość plamy zabudowy. Kolejno: promień plamy w km,
# ile niskich brył, najmniejszy i największy bok bryły w km, ile domów.
# Promienie są prawdziwe: baza osiem kilometrów w poprzek, miasto powiatowe
# trzy, wieś półtora. Brył i domów jest tyle, żeby plama wyglądała na
# zabudowaną, a nie na pustą płytę — przy znaku pięćdziesięciu pikseli widać
# wtedy i niskie bryły, i ciepłe światła w oknach.
RANGA_WIES, RANGA_MIASTO, RANGA_BAZA = 1, 2, 3
RANGI = {
    RANGA_BAZA:   (4.00, 20, 0.62, 1.30, 56),
    RANGA_MIASTO: (1.55, 9, 0.34, 0.70, 24),
    RANGA_WIES:   (0.74, 5, 0.18, 0.38, 9),
}
# Próg czytelności znaku miejscowości: ile pikseli ma mieć plama zabudowy
# w poprzek, mierzona w środku kadru. Prawdziwa baza ma osiem kilometrów,
# miasto powiatowe trzy, wieś półtora — przy dwóch pikselach na kilometr
# wychodzą z tego kropki po cztery piksele i nie widać ani zabudowy, ani
# świateł. Mapy od zawsze rysują osadę znakiem WIĘKSZYM niż prawdziwy obrys;
# tu dzieje się to świadomie i w jednym miejscu: :meth:`MapaDnia._znaki_miejscowosci`.
PROG_ZNAKU_PX = {RANGA_BAZA: 52.0, RANGA_MIASTO: 27.0, RANGA_WIES: 15.0}
# Znak nigdy nie dorasta do sąsiada: para sąsiadek dzieli między siebie
# dzielącą je odległość — w proporcji do tego, ile która chce zająć — i zostawia
# na przerwę resztę. Dwie osady mają zostać dwiema plamami z otwartym terenem
# między nimi, a nie wyglądać, jakby leżały w tej samej dzielnicy.
SZCZELINA_ZNAKU = 0.92     # tyle odległości wolno zająć obu znakom razem
ZAPAS_ZNAKU = 1.20         # najdalszy łuk obrysu plamy względem jej promienia
SASIADOW_ZNAKU = 6         # z tyloma najbliższymi miejscowościami znak się dzieli
NAZWY_RANG = {
    "baza": RANGA_BAZA, "duze": RANGA_BAZA, "duże": RANGA_BAZA,
    "miasto": RANGA_MIASTO, "powiat": RANGA_MIASTO, "srednie": RANGA_MIASTO,
    "miasto powiatowe": RANGA_MIASTO, "średnie": RANGA_MIASTO,
    "wies": RANGA_WIES, "wieś": RANGA_WIES, "wioska": RANGA_WIES,
    "male": RANGA_WIES, "małe": RANGA_WIES,
}


def _hasz_calk(*klucze):
    """Powtarzalna liczba 32-bitowa z dowolnych kluczy.

    Teren i zabudowa mają wyglądać tak samo przy każdym uruchomieniu tego
    samego dnia, a przy tym zależeć od położenia w świecie — stąd własny hasz
    zamiast generatora ciągu i zamiast wbudowanego ``hash``, który zmienia się
    między uruchomieniami Pythona.
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
    return n


def _hasz(*klucze):
    """To samo co :func:`_hasz_calk`, sprowadzone do przedziału 0..1."""
    return _hasz_calk(*klucze) / float(0xFFFFFFFF)


def _ziarno_dnia(dzien):
    """Ziarno obrazu terenu: data dnia i nazwy odwiedzanych miejscowości.

    Ten sam dzień daje zawsze ten sam krajobraz — inaczej zrzuty nie byłyby
    powtarzalne, a oko nie miałoby na czym spocząć. Inny dzień daje inny układ
    pól, lasów i rzeki.
    """
    if dzien is None:
        return _hasz_calk("mapa", "pusto")
    klucze = ["mapa", str(getattr(dzien, "data", ""))]
    if not getattr(dzien, "wolny", False):
        klucze.extend(getattr(dzien, "trasa", ()) or ())
    return _hasz_calk(*klucze)


def _ranga_domyslna(nazwa, baza=False):
    """Ranga miejscowości, gdy nikt jej nie podał — z nazwy, więc stała."""
    if baza:
        return RANGA_BAZA
    return RANGA_MIASTO if _hasz(nazwa, "ranga") > 0.28 else RANGA_WIES


def _czytaj_ranga(wartosc, domyslna=RANGA_MIASTO):
    """Ranga z liczby albo z nazwy; nieznana wartość zostawia domyślną."""
    if isinstance(wartosc, bool) or wartosc is None:
        return domyslna
    if isinstance(wartosc, (int, float)):
        return max(RANGA_WIES, min(RANGA_BAZA, int(round(wartosc))))
    if isinstance(wartosc, str):
        return NAZWY_RANG.get(wartosc.strip().lower(), domyslna)
    return domyslna


def _swiat_miasta(fx, fy):
    """Ułamkowe współrzędne miasta z proto_dane → punkt świata (x, y)."""
    return ((fx - 0.5) * POLE_SWIATA_X, (0.5 - fy) * POLE_SWIATA_Y)


def _tlumik_srodka(x, y, sx, sy):
    """Blisko środka kadru teren jest spokojny, ku krawędziom faluje mocniej.

    Pasmo miejscowości leży wtedy na łagodnym terenie, a dalsze plany dostają
    wzniesienia. Dolna granica nie jest zerem, więc i środek lekko faluje:
    płaska plansza wyglądałaby martwo.
    """
    d = math.hypot(x / max(1.0, sx), y / max(1.0, sy))
    return max(0.26, min(1.0, (d - 0.44) / 0.86))


def _plama(cx, cy, promien, ziarno, lobow=9, splasz=0.84, sila=0.46, gestosc=3):
    """Nieregularny, zamknięty obrys wokół punktu — plama zabudowy albo lasu.

    Zaburzenie promienia bierze się z bajtów trzech haszy, a nie z osobnego
    hasza na każdy wierzchołek: takich obrysów powstaje przy jednym terenie
    kilkaset, a hasz jest pętlą po bajtach.
    """
    lobow = max(3, min(12, lobow))
    bity = (_hasz_calk(ziarno, 5), _hasz_calk(ziarno, 6), _hasz_calk(ziarno, 7))
    punkty = []
    for i in range(lobow):
        kat = 2.0 * math.pi * i / lobow
        szum = ((bity[i // 4] >> (8 * (i % 4))) & 0xFF) / 255.0
        r = promien * (1.0 - sila * 0.5 + sila * szum)
        punkty.append((cx + math.cos(kat) * r, cy + math.sin(kat) * r * splasz))
    return _gladko_2d(punkty, na_odcinek=gestosc, zamknieta=True)


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

        # Mgła rozciągnięta na głębi RYSOWANEGO TERENU, a nie na odległości
        # kamery: dal ma gasnąć tak samo przy każdym ustawieniu obiektywu.
        # Zasięg terenu idzie za rozpiętością kadru, tak samo jak reszta miar.
        zasieg = max(sx, sy) * UDZIAL_ZASIEGU_TERENU * self.f[1]
        self.mgla_od = self.d - zasieg * 0.34
        self.mgla_zakres = max(1.0, zasieg * 1.42)

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

    def blisko_y(self, glebia):
        """Najmniejsze y gruntu o zadanej głębi — bliżej jest już za kamerą.

        Głębia punktu gruntu nie zależy od x (kamera nie jest obrócona wokół
        osi patrzenia), więc wystarczy jedna liczba, żeby odciąć teren, który
        wpadłby za obiektyw i rozjechał się na ekranie.
        """
        return self.oko[1] + (glebia + self.oko[2] * self.f[2]) / max(1e-6, self.f[1])

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
        t = (gleb - self.mgla_od) / self.mgla_zakres
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
        self._baza = dn.BAZA
        self._jedn_na_km = JEDNOSTEK_NA_KM    # ile jednostek świata ma kilometr
        self._miasta = {n: _swiat_miasta(*fr) for n, fr in dn.MIASTA.items()}
        self._rangi = {n: _ranga_domyslna(n, n == self._baza) for n in self._miasta}
        self._ziarno = _ziarno_dnia(None)
        self._ziarno_terenu = self._ziarno    # ziarno, z którego stoi obecny teren
        self._kopuly = []               # wzniesienia w postaci do liczenia wysokości
        self._siatka_kopul = {}         # te same wzniesienia w kratce, do szybkiego szukania
        self._sasiedztwo = {}           # najbliżsi sąsiedzi każdej miejscowości
        self._znaki = None              # powiększenie znaku każdej miejscowości
        self._znaki_klucz = None
        self._miara = POLE_SWIATA_X     # rozpiętość kadru — od niej idą miary terenu
        self._przebuduj_swiat()

        self._rzut = None               # kamera; zależy od widżetu, trasy i kartki
        self._rzut_klucz = None
        self._pola = None               # działki terenu widoczne przy tym rozmiarze
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
        self._ustaw_ziarno(_ziarno_dnia(dzien))
        self._rozsadz_zegar()
        self.update()

    def ustaw_miasta(self, slownik, baza=None):
        """Prawdziwe miejscowości: {nazwa: (szerokość, długość[, ranga])}.

        Zamiast krotki wolno podać słownik z kluczami ``lat``/``szerokosc``,
        ``lng``/``dlugosc`` i ``ranga``. Ranga to 1..3 albo nazwa („wieś”,
        „miasto”, „baza”) i decyduje o wielkości plamy zabudowy.

        Współrzędne idą na płaszczyznę mapy z zachowaniem proporcji odległości:
        jeden wspólny przelicznik dla obu osi, zmniejszany tylko wtedy, gdy
        rejon nie mieści się w kadrze. Podziałka bierze ten sam przelicznik,
        więc dalej mierzy prawdę. Bez tego wywołania mapa pracuje na danych
        z proto_dane.
        """
        punkty = {}
        rangi = {}
        for nazwa, wartosc in (slownik or {}).items():
            odczyt = self._czytaj_miasto(wartosc)
            if odczyt is None:
                continue
            punkty[nazwa] = (odczyt[0], odczyt[1])
            rangi[nazwa] = odczyt[2]
        if not punkty:
            return
        kolejne = list(punkty)
        if baza in punkty:
            self._baza = baza
        elif dn.BAZA in punkty:
            self._baza = dn.BAZA
        else:
            self._baza = max(kolejne, key=lambda n: (rangi.get(n) or 0, n))
        for nazwa in kolejne:
            if rangi.get(nazwa) is None:
                rangi[nazwa] = _ranga_domyslna(nazwa, nazwa == self._baza)
        rangi[self._baza] = RANGA_BAZA
        self._miasta = self._rzutuj_geo(punkty)
        self._rangi = rangi
        self._przebuduj_swiat()
        self._rzut = None
        self._rzut_klucz = None
        self._pola = None
        self._statyk_klucz = None
        self._warstwy_klucz = None
        self._geo_klucz = None
        self.update()

    # — świat —
    @staticmethod
    def _czytaj_miasto(wartosc):
        """(szerokość, długość, ranga) z krotki albo ze słownika; None = pomijamy."""
        if isinstance(wartosc, dict):
            lat = wartosc.get("lat", wartosc.get("szerokosc", wartosc.get("szer")))
            lng = wartosc.get("lng", wartosc.get("lon", wartosc.get("dlugosc",
                                                                   wartosc.get("dl"))))
            ranga = wartosc.get("ranga", wartosc.get("rank"))
        elif isinstance(wartosc, (str, bytes)):
            return None                       # napis rozpadłby się na znaki
        else:
            try:
                lista = list(wartosc)
            except TypeError:
                return None
            if len(lista) < 2:
                return None
            lat, lng = lista[0], lista[1]
            ranga = lista[2] if len(lista) > 2 else None
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            return None
        return lat, lng, (None if ranga is None else _czytaj_ranga(ranga))

    def _rzutuj_geo(self, punkty):
        """Szerokość i długość → jednostki świata, wspólną skalą dla obu osi."""
        srodek = self._baza if self._baza in punkty else sorted(punkty)[0]
        lat0, lng0 = punkty[srodek]
        km = {}
        for nazwa, (lat, lng) in punkty.items():
            # Południk zwęża się ku biegunowi, więc cosinus bierzemy ze ŚRODKA
            # odcinka do bazy, a nie z samej bazy. Przy rejonie rozciągniętym
            # z południa na północ jeden wspólny cosinus mylił się o kilometr
            # na stu trzydziestu; tak mylą się dwie trzecie tego.
            km[nazwa] = ((lng - lng0) * 111.32
                         * math.cos(math.radians((lat + lat0) * 0.5)),
                         (lat - lat0) * 110.57)
        sx = [x for (x, _) in km.values()]
        sy = [y for (_, y) in km.values()]
        cx = (max(sx) + min(sx)) * 0.5
        cy = (max(sy) + min(sy)) * 0.5
        zasieg = max([max(abs(x - cx), abs(y - cy)) for (x, y) in km.values()] or [1.0])
        skala = JEDNOSTEK_NA_KM
        granica = POLE_SWIATA_X * 0.46
        if zasieg * skala > granica:
            skala = granica / max(1.0, zasieg)
        self._jedn_na_km = skala
        return {n: ((x - cx) * skala, (y - cy) * skala) for n, (x, y) in km.items()}

    def _przebuduj_swiat(self):
        """Wszystko, co zależy od układu miast i od ziarna dnia."""
        self._przelicz_miary()
        self._kopuly, self._siatka_kopul = self._zbuduj_wzniesienia()
        self._rzeka = self._zbuduj_rzeke()
        self._ziarno_terenu = self._ziarno
        self._siec = self._zbuduj_siec()
        self._drogi = self._ksztalty_drog()
        self._sasiedzi = self._zbuduj_graf()
        self._miejscowosci = self._zbuduj_miejscowosci()
        self._sasiedztwo = self._dystanse_sasiadow()
        self._znaki = None

    def _przelicz_miary(self):
        """Miary krajobrazu w jednostkach świata — rozciągają się razem z kadrem.

        Ziarno pola, kratka wzniesień, zasięg terenu i wznios trasy są
        ułamkami rozpiętości kadru. Dzięki temu dzień w promieniu czterdziestu
        kilometrów ma tak samo gęsty krajobraz jak dzień rozrzucony na trzysta,
        a nie jedno pole na pół ekranu. Wzniesienia i wysokość terenu muszą się
        przeliczać razem, bo kratka wzniesień jest kluczem do ich szukania.
        """
        _ox, _oy, sx, sy = self._obszar_swiata()
        self._miara = max(1.0, max(sx, sy))
        self._komorka_pola = self._miara * UDZIAL_KOMORKI_POLA
        self._komorka_terenu = self._miara * UDZIAL_KOMORKI_TERENU
        self._zasieg_terenu = self._miara * UDZIAL_ZASIEGU_TERENU
        self._wznios_trasy = self._miara * UDZIAL_WZNIOSU_TRASY

    def _ustaw_ziarno(self, ziarno):
        """Nowe ziarno przestawia krajobraz; to samo ziarno nie zmienia nic.

        Przeliczenie terenu jest odłożone o ułamek sekundy — tak samo jak przy
        ciągnięciu okna. Dzięki temu przeskakiwanie po dniach nie zacina się na
        budowaniu pól, a zrzuty i tak wychodzą ostre, bo ``ustaw_animacje(False)``
        domyka ten zegar od razu.
        """
        if ziarno == self._ziarno:
            return
        self._ziarno = ziarno
        self._geo_klucz = None
        self._zegar_terenu.start()

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
            self._dopilnuj_terenu()              # ...i teren z tego samego ziarna
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
        """Koniec ruchu: teren dla obecnego ziarna i rozmiaru liczy się od nowa."""
        self._pola = None
        self._statyk_klucz = None
        self._warstwy_klucz = None
        self.update()

    def _dopilnuj_terenu(self):
        """Wzniesienia i rzeka z tego samego ziarna, z którego jest obraz.

        Wysokość terenu podnosi trasę, drogi i zabudowę, więc nie może zmienić
        się wcześniej niż same pola — inaczej przez chwilę trasa wisiałaby obok
        swojego cienia. Dlatego ziarno przestawia się dopiero tutaj, jednym
        ruchem dla całej sceny.
        """
        if self._ziarno_terenu == self._ziarno:
            return
        self._przelicz_miary()
        self._kopuly, self._siatka_kopul = self._zbuduj_wzniesienia()
        self._rzeka = self._zbuduj_rzeke()
        self._ziarno_terenu = self._ziarno
        self._pola = None
        self._statyk_klucz = None
        self._warstwy_klucz = None
        self._geo_klucz = None
        self._znaki = None

    # — kamera —
    def _pole(self):
        """Prostokąt ekranu, w który ma trafić kadr — część widżetu bez kartki.

        Kartka delegacji leży NA mapie i zasłania jej prawą stronę, więc trasa
        wyśrodkowana w całym widżecie chowałaby się pod papierem, a tabliczki
        uciekałyby za lewą krawędź. Kadr idzie w to, co po kartce zostaje.
        Bez kotwicy kartki (sama mapa, podgląd, zrzuty) wolny jest cały widżet.
        """
        r = QRectF(self.rect())
        lewy = r.x() + r.width() * MARGINES_KADRU
        gora = r.y() + r.height() * MARGINES_KADRU
        prawy = r.right() - r.width() * MARGINES_KADRU
        dol = r.bottom() - r.height() * MARGINES_KADRU
        if self._kotwica is not None:
            # kartka zaczyna się osiem pikseli przed kotwicą — tak ją stawia okno
            brzeg_kartki = self._kotwica.x() - 8.0 - r.width() * ODSTEP_OD_KARTKI
            prawy = min(prawy, max(lewy + r.width() * 0.34, brzeg_kartki))
        return QRectF(lewy, gora, max(40.0, prawy - lewy), max(40.0, dol - gora))

    def _punkty_kadru(self):
        """Punkty świata, które kadr ma objąć: baza i przystanki tego dnia.

        Dzień bez trasy — i mapa, której dnia jeszcze nie podano — oddaje kadr
        całemu układowi miast, dokładnie jak dotąd.
        """
        d = self._dzien
        trasa = () if d is None or getattr(d, "wolny", False) else tuple(d.trasa)
        punkty = [self._miasta[n] for n in trasa if n in self._miasta]
        if not punkty:
            return list(self._miasta.values())
        if self._baza in self._miasta:
            punkty.append(self._miasta[self._baza])      # baza zawsze w kadrze
        return punkty

    def _obszar_swiata(self):
        """Prostokąt świata, który ma trafić w kadr: TRASA DNIA plus margines.

        Kadr należy do trasy, a nie do spisu miast. Program podaje mapie
        kilkaset miejscowości wokół bazy i gdyby kadr obejmował je wszystkie,
        cały dzień siedziałby w ćwiartce obrazu, a reszta byłaby pustym
        krajobrazem. Miejscowości spoza trasy dalej się rysują — po prostu
        wpadają w kadr albo nie. Próg rozpiętości pilnuje, żeby dzień z
        przystankami w promieniu pięciu kilometrów nie dał absurdalnego
        zbliżenia, na którym widać już tylko dwie ulice.
        """
        punkty = self._punkty_kadru()
        xs = [x for (x, _) in punkty] or [0.0]
        ys = [y for (_, y) in punkty] or [0.0]
        prog = NAJMNIEJSZY_KADR_KM * self._jedn_na_km
        luz = 1.0 + 2.0 * MARGINES_TRASY
        sx = max(prog, max(xs) - min(xs)) * luz
        sy = max(prog, max(ys) - min(ys)) * luz
        cx = (max(xs) + min(xs)) * 0.5
        cy = (max(ys) + min(ys)) * 0.5
        return (cx - sx * 0.5, cy - sy * 0.5, sx, sy)

    def _klucz_kadru(self):
        """Wszystko, co przestawia kamerę: widżet, trasa dnia i brzeg kartki."""
        ox, oy, sx, sy = self._obszar_swiata()
        kot = None if self._kotwica is None else round(self._kotwica.x(), 1)
        return (self.width(), self.height(), round(ox, 3), round(oy, 3),
                round(sx, 3), round(sy, 3), kot)

    def rzut(self):
        """Kamera dla obecnego kadru — liczona raz i pamiętana."""
        klucz = self._klucz_kadru()
        if self._rzut is not None and self._rzut_klucz == klucz:
            return self._rzut
        self._rzut = Rzut(self._pole(), self._obszar_swiata())
        self._rzut_klucz = klucz
        self._pola = None
        self._znaki = None
        return self._rzut

    def rzutuj(self, x, y, z=0.0):
        """Punkt sceny → (punkt ekranu, skala). Skrót do kamery widżetu."""
        return self.rzut().rzutuj(x, y, z)

    def _odniesienie(self):
        """Ile razy kadr jest rozleglejszy od wzorcowego.

        Grubość trasy, słupa i pierścienia podana jest w jednostkach świata,
        żeby zwężały się w głębi sceny. Same jednostki rozciągają się jednak
        razem z kadrem, więc przy dniu ciasnym ta sama trasa wyszłaby na sto
        pikseli szeroka. Skale rzutu mnożymy więc przez rozpiętość kadru —
        linia zostaje tej samej grubości co przy kadrze wzorcowym i dalej
        zwęża się w głębi.
        """
        return self._miara / POLE_SWIATA_X

    # — teren —
    def _zbuduj_wzniesienia(self):
        """Miękkie wzniesienia i kratka do szybkiego szukania wysokości.

        Samych wzniesień nie rysujemy — one tylko podnoszą grunt, a widać je
        po odcieniach działek zarzuconych na garb. Kształt bierze się z ziarna
        dnia i z położenia kratki, więc ten sam dzień daje ten sam teren.
        """
        z = self._ziarno
        ox, oy, sx, sy = self._obszar_swiata()
        px, py = ox + sx * 0.5, oy + sy * 0.5
        kom = self._komorka_terenu
        zas = int(math.ceil(self._zasieg_terenu / kom))
        srx, sry = sx * 0.60, sy * 0.60
        kopuly = []
        for i in range(-zas, zas + 1):
            for j in range(-zas, zas + 1):
                if _hasz(z, i, j, 1) > 0.80:          # nie w każdej kratce stoi garb
                    continue
                cx = px + (i + 0.14 + 0.72 * _hasz(z, i, j, 2)) * kom
                cy = py + (j + 0.14 + 0.72 * _hasz(z, i, j, 3)) * kom
                tlum = _tlumik_srodka(cx - px, cy - py, srx, sry)
                prom = kom * (0.40 + 0.36 * _hasz(z, i, j, 4))
                niski, wysoki = UDZIAL_GARBU
                wys = self._miara * (niski + wysoki
                                     * _hasz(z, i, j, 5) ** 1.35) * tlum
                kopuly.append((cx, cy, prom,
                               prom * (0.68 + 0.54 * _hasz(z, i, j, 7)), wys))
        siatka = {}
        for k in kopuly:
            cx, cy, rx, ry = k[0], k[1], k[2], k[3]
            for i in range(int(math.floor((cx - rx) / kom)),
                           int(math.floor((cx + rx) / kom)) + 1):
                for j in range(int(math.floor((cy - ry) / kom)),
                               int(math.floor((cy + ry) / kom)) + 1):
                    siatka.setdefault((i, j), []).append(k)
        return kopuly, siatka

    def _wysokosc(self, x, y):
        """Wysokość terenu w punkcie — suma miękkich kopuł, szukanych po kratce.

        Wywoływana dziesiątki tysięcy razy przy liczeniu pól, dróg i trasy,
        więc kratka zastępuje przeglądanie wszystkich wzniesień naraz.
        """
        kom = self._komorka_terenu
        lista = self._siatka_kopul.get((int(math.floor(x / kom)),
                                        int(math.floor(y / kom))))
        if not lista:
            return 0.0
        h = 0.0
        for (cx, cy, rx, ry, wys) in lista:
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

    # — otwarty teren: pola i lasy —
    @staticmethod
    def _odcien(rzut, barwa, jas, mgla):
        """Barwa działki po oświetleniu jej nachylenia i po mgle odległości."""
        k = max(0.40, min(1.50, 0.46 + 0.78 * jas))
        return rzut.zamgl(QColor(min(255, int(barwa.red() * k)),
                                 min(255, int(barwa.green() * k)),
                                 min(255, int(barwa.blue() * k))), mgla, 0.62)

    def _plat_lasu(self, rzut, sx, sy, kom, jas, mgla, klucz):
        """Płat lasu: ciemna plama o nieregularnej krawędzi, lekko wyniesiona.

        Wielkość i kształt płatu biorą się z klucza działki, więc sąsiednie
        lasy nie są swoimi kopiami i razem dają nierówną, postrzępioną ścianę.
        """
        prom = kom * (0.38 + 0.34 * _hasz(klucz, 3))
        obrys = _plama(sx, sy, prom, klucz, lobow=7 + int(_hasz(klucz, 4) * 3.99),
                       splasz=0.66 + 0.46 * _hasz(klucz, 6),
                       sila=0.42 + 0.34 * _hasz(klucz, 7), gestosc=2)
        wys = self._wysokosc
        korona = kom * 0.075
        wysokosci = [wys(x, y) for (x, y) in obrys]
        gora = QPolygonF([rzut.ekran(x, y, h + korona)
                          for ((x, y), h) in zip(obrys, wysokosci)])
        barwa = self._odcien(rzut, BARWA_LASU, jas * 1.2 + 0.16, mgla)
        wierzch = (gora, barwa, barwa)
        if prom * rzut.k / max(1.0, rzut.glebokosc(sx, sy, 0.0)) < 9.0:
            return [wierzch]                  # daleki płat i tak jest jedną plamą
        ciemny = self._odcien(rzut, BARWA_LASU.darker(135), jas, mgla)
        dol = (QPolygonF([rzut.ekran(x, y, h) for ((x, y), h) in zip(obrys, wysokosci)]),
               ciemny)
        return [(dol[0], dol[1], dol[1]), wierzch]

    def _zbuduj_pola(self, rzut):
        """Działki otwartego terenu gotowe do namalowania, od dali do widza.

        Siatka działek jest nieregularna — wierzchołki przesuwa hasz wspólny
        dla czterech sąsiadów, więc między polami nie ma szczelin. Odcień
        bierze się z nachylenia działki względem światła i z mgły odległości,
        dzięki czemu garb terenu widać bez rysowania warstwic.
        """
        z = self._ziarno
        kom = self._komorka_pola
        r = QRectF(self.rect())
        rogi = [rzut.na_grunt(r.x(), r.y()), rzut.na_grunt(r.right(), r.y()),
                rzut.na_grunt(r.x(), r.bottom()), rzut.na_grunt(r.right(), r.bottom())]
        xs = [p[0] for p in rogi]
        ys = [p[1] for p in rogi]
        ox, oy, osx, osy = self._obszar_swiata()
        px, py = ox + osx * 0.5, oy + osy * 0.5
        zasieg = self._zasieg_terenu
        x0 = max(px - zasieg, min(xs) - kom)
        x1 = min(px + zasieg, max(xs) + kom)
        # przy dolnej krawędzi ekranu grunt kończy się tuż przed obiektywem;
        # działka policzona dalej rozjechałaby się przez dzielenie przez głębię
        blisko = rzut.blisko_y(BLISKO_KAMERY) + kom
        y0 = max(py - zasieg, min(ys) - kom, blisko)
        y1 = min(py + zasieg, max(ys) + kom)
        if y1 <= y0 or x1 <= x0:
            return []

        # hasz jest pętlą po bajtach, więc w gorącej pętli liczymy go raz na
        # węzeł i raz na działkę, a potrzebne liczby bierzemy z osobnych bitów
        pamiec, kepy_lasu, kepy_tonu = {}, {}, {}

        def wezel(i, j):
            """Wierzchołek siatki wraz z wysokością — wspólny dla czterech działek."""
            w = pamiec.get((i, j))
            if w is None:
                h = _hasz_calk(z, i, j, 71)
                wx = (i + 0.56 * ((h & 0xFFFF) / 65535.0 - 0.5)) * kom
                wy = (j + 0.56 * (((h >> 16) & 0xFFFF) / 65535.0 - 0.5)) * kom
                w = (wx, wy, self._wysokosc(wx, wy))
                pamiec[(i, j)] = w
            return w

        def kepa(pamiatka, i, j, klucz):
            """Wolno zmienna liczba dla większej kratki — stąd kępy lasu i tonu."""
            w = pamiatka.get((i, j))
            if w is None:
                w = _hasz(z, i, j, klucz)
                pamiatka[(i, j)] = w
            return w

        lx, ly, lz = SWIATLO_JEDN
        ile_barw = len(BARWY_POL)
        dzialki = []
        for i in range(int(math.floor(x0 / kom)), int(math.ceil(x1 / kom))):
            for j in range(int(math.floor(y0 / kom)), int(math.ceil(y1 / kom))):
                a = wezel(i, j)
                b = wezel(i + 1, j)
                c = wezel(i + 1, j + 1)
                d = wezel(i, j + 1)
                sx = (a[0] + b[0] + c[0] + d[0]) * 0.25
                sy = (a[1] + b[1] + c[1] + d[1]) * 0.25
                if min(a[1], b[1], c[1], d[1]) < blisko - kom * 0.5:
                    continue                          # narożnik wypadłby za kamerę
                gleb = rzut.glebokosc(sx, sy, 0.0)
                if gleb < BLISKO_KAMERY:
                    continue
                ska = rzut.k / gleb
                if kom * ska < 1.6:                  # działka cieńsza niż dwa piksele
                    continue
                srodek = rzut.ekran(sx, sy, 0.0)
                zas = kom * ska * 1.5
                if (srodek.x() + zas < r.x() - 2 or srodek.x() - zas > r.right() + 2
                        or srodek.y() + zas < r.y() - 2
                        or srodek.y() - zas > r.bottom() + 2):
                    continue                          # działka poza widżetem
                ha, hb, hc, hd = a[2], b[2], c[2], d[2]
                # nachylenie działki — z niego wychodzi cała rzeźba terenu
                szer = max(1e-6, (b[0] + c[0] - a[0] - d[0]) * 0.5)
                glab = max(1e-6, (d[1] + c[1] - a[1] - b[1]) * 0.5)
                nx = -(hb + hc - ha - hd) * 0.5 / szer
                ny = -(hd + hc - ha - hb) * 0.5 / glab
                jas = (nx * lx + ny * ly + lz) / math.sqrt(nx * nx + ny * ny + 1.0)
                mgla = rzut.mgla(gleb)
                # lasy rosną kępami: o tym, czy w tej okolicy w ogóle jest las,
                # decyduje hasz większej kratki, a dopiero potem sama działka
                hasz = _hasz_calk(z, i, j, 73)
                prog = UDZIAL_LASU * (0.15 + 1.90 * kepa(kepy_lasu, i // 2, j // 2, 81))
                if (hasz & 0xFFFF) / 65535.0 < prog:
                    warstwy = self._plat_lasu(rzut, sx, sy, kom, jas, mgla, hasz)
                else:
                    # odcień pola też idzie kępami — inaczej wychodzi kołdra
                    ton = (0.52 * ((hasz >> 16) & 0xFFFF) / 65535.0
                           + 0.48 * kepa(kepy_tonu, i // 3, j // 3, 82))
                    barwa = BARWY_POL[int(ton * ile_barw) % ile_barw]
                    pole = self._odcien(rzut, barwa, jas, mgla)
                    warstwy = [(QPolygonF([rzut.ekran(a[0], a[1], ha),
                                           rzut.ekran(b[0], b[1], hb),
                                           rzut.ekran(c[0], c[1], hc),
                                           rzut.ekran(d[0], d[1], hd)]),
                                pole, pole.darker(122))]
                dzialki.append((gleb, warstwy))
        dzialki.sort(key=lambda para: -para[0])
        return [w for (_, warstwy) in dzialki for w in warstwy]

    def _rysuj_pola(self, p):
        """Działki od najdalszej do najbliższej — bliższa zasłania dalszą.

        Każda dostaje cieńszą, ciemniejszą obwódkę: to i miedza między polami,
        i zasłonięcie szwu, który antyaliasing zostawiłby między działkami.
        """
        for wiel, barwa, miedza in self._pola:
            p.setPen(QPen(miedza, 1.0))
            p.setBrush(QBrush(barwa))
            p.drawPolygon(wiel)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(Qt.BrushStyle.NoBrush)

    # — grunt i mgła —
    def _rysuj_grunt(self, p, rzut, r):
        """Ziemia pod polami: ciemniejsza przy widzu, jaśniejsza w głębi."""
        g = QLinearGradient(QPointF(r.x(), r.y()), QPointF(r.x(), r.bottom()))
        g.setColorAt(0.0, QColor(20, 38, 56, 150))
        g.setColorAt(0.44, QColor(11, 22, 36, 140))
        g.setColorAt(1.0, QColor(4, 9, 17, 120))
        p.fillRect(r, QBrush(g))

    def _rysuj_mgle(self, p, rzut, r):
        """Mgła odległości: w głębi sceny mniejszy kontrast i jaśniejsze tło."""
        # gdzie na ekranie leży horyzont — od niego idzie cała skala mgły
        ox, oy, osx, osy = self._obszar_swiata()
        y_gora = rzut.ekran(0.0, oy + osy * 0.5 + self._zasieg_terenu, 0.0).y()
        y_dol = rzut.ekran(0.0, oy - osy * 0.30, 0.0).y()
        g = QLinearGradient(QPointF(r.x(), y_gora), QPointF(r.x(), y_dol))
        g.setColorAt(0.0, st.z_alfa(BARWA_MGLY, 46))
        g.setColorAt(0.30, st.z_alfa(BARWA_MGLY, 20))
        g.setColorAt(0.72, st.z_alfa(BARWA_MGLY, 5))
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
        """Rzeka wijąca się przez rejon — koryto wynika z ziarna dnia.

        Inny dzień to inny bieg rzeki; ten sam dzień to zawsze ten sam.
        """
        los = _Losowy(self._ziarno)
        ox, oy, sx, sy = self._obszar_swiata()
        px, py = ox + sx * 0.5, oy + sy * 0.5
        zas = max(sx, sy) * 1.7
        x = los.zakres(-0.62, -0.05) * sx
        sterowe = []
        for i in range(10):
            y = py + zas * 0.5 - i * (zas / 9.0)
            x += los.zakres(0.02, 0.13) * sx
            sterowe.append((x + los.zakres(-0.05, 0.05) * sx, y))
        if _hasz(self._ziarno, "rzeka") > 0.5:        # czasem z drugiej strony
            sterowe = [(-x, y) for (x, y) in sterowe]
        return _gladko_2d([(px + x, y) for (x, y) in sterowe], na_odcinek=7)

    def _rysuj_rzeke(self, p, rzut):
        """Koryto ciemniejsze od gruntu, jaśniejszy brzeg i pasek połysku."""
        szer = self._miara * UDZIAL_RZEKI
        p.setPen(Qt.PenStyle.NoPen)
        # brzeg: szersza, jaśniejsza wstęga pod korytem
        brzeg = _wstega(rzut, self._rzeka, szer * 2.10, self._wysokosc)
        p.fillPath(brzeg, QColor(104, 146, 172, 62))
        koryto = _wstega(rzut, self._rzeka, szer, self._wysokosc)
        p.fillPath(koryto, QColor(2, 8, 17, 235))
        p.fillPath(koryto, QColor(9, 42, 66, 150))
        # połysk: wąski pas przesunięty ku światłu
        bok = [(x + SWIATLO_3D[0] * szer * 0.3, y + SWIATLO_3D[1] * szer * 0.3)
               for (x, y) in self._rzeka]
        polysk = _wstega(rzut, bok, szer * 0.24, self._wysokosc, wznios=0.2)
        p.fillPath(polysk, st.z_alfa(st.MIETA, 90))

    # — drogi —
    def _zbuduj_siec(self):
        """Sieć dróg: graf Gabriela plus dwaj najbliżsi sąsiedzi każdego miasta.

        Graf Gabriela daje układ podobny do prawdziwej sieci — bez krzyżujących
        się skrótów — a najbliżsi sąsiedzi pilnują, żeby nic nie zostało bez
        dojazdu. Trasa dnia biegnie potem wyłącznie po tych drogach.
        """
        nazwy = self._nazwy()
        poz = self._miasta
        pary = set()
        for i, a in enumerate(nazwy):
            ax, ay = poz[a]
            # klucz z nazwą na końcu: przy równych odległościach wybór nie
            # zależy od tego, w jakiej kolejności wypadły miasta w zbiorze
            sasiedzi = sorted((n for n in nazwy if n != a),
                              key=lambda n: ((poz[n][0] - ax) ** 2
                                             + (poz[n][1] - ay) ** 2, n))
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

    def _nazwy(self):
        """Nazwy miejscowości w stałej kolejności — nigdy prosto ze zbioru."""
        return sorted(self._miasta)

    def _zbuduj_graf(self):
        """Listy sąsiedztwa z długościami — do szukania trasy po drogach."""
        graf = {n: [] for n in self._miasta}
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
        """Najkrótsza droga z a do b po sieci — algorytm Dijkstry na kilkunastu węzłach.

        Przy równych odległościach rozstrzyga nazwa, a nie kolejność wyjmowania
        ze zbioru: ta sama trasa musi dawać ten sam przebieg przy każdym
        uruchomieniu, bo od niego zależy rozmieszczenie tabliczek.
        """
        if a == b:
            return [a]
        if a not in self._sasiedzi or b not in self._sasiedzi:
            return [a, b]
        odl = {a: 0.0}
        skad = {}
        do_zrobienia = {a}
        gotowe = set()
        while do_zrobienia:
            biezacy = min(do_zrobienia, key=lambda n: (odl[n], n))
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
        pa = self._miasta.get(a, (0.0, 0.0))
        pb = self._miasta.get(b, (0.0, 0.0))
        prosto = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
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
            szer = self._miara * UDZIAL_DROGI
            pas = _wstega(rzut, punkty, szer, self._wysokosc, wznios=0.10)
            p.fillPath(pas, st.z_alfa(rzut.zamgl(QColor(120, 148, 172), mgla),
                                      int(42 - 20 * mgla)))
            rdzen = _wstega(rzut, punkty, szer * 0.36, self._wysokosc, wznios=0.20)
            p.fillPath(rdzen, st.z_alfa(rzut.zamgl(QColor(176, 200, 220), mgla),
                                        int(50 - 24 * mgla)))

    # — miejscowości —
    def _zbuduj_miejscowosci(self):
        """Plamy zabudowy: obrys, kilka niskich brył i rozsypane domy.

        W skali regionu pojedynczy budynek ma ułamek piksela, więc miejscowość
        jest zwartą plamą zabudowy — szeroką na kilometr albo dwa, przy bazie
        na kilka — a nie skupiskiem wież. Wielkość bierze się z rangi, kształt
        z hasza nazwy, więc ta sama miejscowość zawsze wygląda tak samo,
        a między sąsiadkami zostaje otwarty teren.
        """
        jedn = self._jedn_na_km
        lista = []
        for nazwa in self._nazwy():
            cx, cy = self._miasta[nazwa]
            ranga = self._rangi.get(nazwa, RANGA_MIASTO)
            prom_km, ile, bok_min, bok_max, domow = RANGI.get(ranga, RANGI[RANGA_MIASTO])
            prom = prom_km * jedn
            obrys = _plama(cx, cy, prom, _hasz_calk(nazwa, "plama"), lobow=10, sila=0.40)
            bryly = []
            for i in range(ile):
                kat = 2.0 * math.pi * (i / float(ile) + 0.34 * _hasz(nazwa, i, 1))
                odl = prom * (0.06 + 0.72 * _hasz(nazwa, i, 2) ** 0.7)
                bok = (bok_min + (bok_max - bok_min) * _hasz(nazwa, i, 3)) * jedn * 0.5
                bryly.append({
                    "x": cx + math.cos(kat) * odl,
                    "y": cy + math.sin(kat) * odl * 0.86,
                    "bok": bok,
                    "glab": bok * (0.66 + 0.52 * _hasz(nazwa, i, 4)),
                    # bryła ma być wyraźnie niższa, niż szeroka — inaczej
                    # miejscowość znowu zrobiłaby się skupiskiem wież
                    "wys": bok * (0.62 + 0.66 * _hasz(nazwa, i, 5)),
                    "odcien": _hasz(nazwa, i, 6),
                })
            domy = []
            for i in range(domow):
                kat = 2.0 * math.pi * _hasz(nazwa, i, 11)
                odl = prom * (0.10 + 0.84 * _hasz(nazwa, i, 12) ** 0.6)
                domy.append((cx + math.cos(kat) * odl,
                             cy + math.sin(kat) * odl * 0.86,
                             _hasz(nazwa, i, 13) > 0.74))
            lista.append({"nazwa": nazwa, "x": cx, "y": cy, "ranga": ranga,
                          "promien": prom, "wys": prom * 0.30, "obrys": obrys,
                          "bryly": bryly, "domy": domy})
        return lista

    def _dystanse_sasiadow(self):
        """Najbliżsi sąsiedzi każdej miejscowości — z nich wychodzi granica znaku.

        Liczone raz na układ miast, bo od kadru nie zależą. Sześciu wystarczy:
        znak nie bywa większy od odległości do najbliższej sąsiadki, więc dalsze
        i tak nic już nie przycinają.
        """
        nazwy = self._nazwy()
        poz = self._miasta
        wynik = {}
        for a in nazwy:
            ax, ay = poz[a]
            bliscy = sorted((math.hypot(poz[b][0] - ax, poz[b][1] - ay), b)
                            for b in nazwy if b != a)
            wynik[a] = bliscy[:SASIADOW_ZNAKU]
        return wynik

    def _znaki_miejscowosci(self, rzut):
        """Ile razy powiększyć znak każdej miejscowości — JEDNO miejsce w kodzie.

        Prawdziwe rozmiary bierze tabela RANGI: baza osiem kilometrów w poprzek,
        miasto powiatowe trzy, wieś półtora. Przy dwóch–trzech pikselach na
        kilometr wychodzą z tego kropki po kilka pikseli i nie widać ani
        zabudowy, ani ciepłych świateł. Mapy od zawsze rysują osadę znakiem
        większym od prawdziwego obrysu — tu dzieje się to świadomie: znak
        dostaje próg czytelności w pikselach, mierzony skalą w środku kadru
        (nie na własnej głębi, bo wtedy wszystkie osady byłyby równe i zniknęłaby
        perspektywa). Prawdziwy obrys wygrywa, kiedy jest większy od progu.

Górną granicą jest sąsiad: para sąsiadek dzieli dzielącą je odległość
        w proporcji do tego, ile która chce zająć, i zostawia na przerwę resztę.
        Dwie osady zostają więc dwiema plamami z otwartym terenem między nimi
        i nigdy nie wyglądają, jakby leżały w tej samej dzielnicy — a podziałka
        mierzy teren i o niczym z tego nie wie.
        """
        ox, oy, sx, sy = self._obszar_swiata()
        odn = rzut.k / max(1.0, rzut.glebokosc(ox + sx * 0.5, oy + sy * 0.5, 0.0))
        klucz = round(odn, 6)
        if self._znaki is not None and self._znaki_klucz == klucz:
            return self._znaki
        # a) ile znak chciałby zająć: prawdziwy obrys albo próg czytelności
        chciane = {}
        for m in self._miejscowosci:
            prog = PROG_ZNAKU_PX.get(m["ranga"],
                                     PROG_ZNAKU_PX[RANGA_MIASTO]) * 0.5 / max(1e-6, odn)
            chciane[m["nazwa"]] = max(m["promien"], prog)
        # b) ile zająć może: para sąsiadek dzieli dzielącą je odległość
        #    w proporcji do swoich chęci, więc mniejsza wieś nie zabiera bazie
        #    połowy drogi, a między znakami i tak zostaje przerwa
        znaki = {}
        for m in self._miejscowosci:
            nazwa = m["nazwa"]
            chce = chciane[nazwa]
            prom = chce
            for (dystans, sasiad) in self._sasiedztwo.get(nazwa, ()):
                razem = chce + chciane.get(sasiad, 0.0)
                if razem <= 0.0:
                    continue
                granica = dystans * SZCZELINA_ZNAKU / ZAPAS_ZNAKU * chce / razem
                if granica < prom:
                    prom = granica
            znaki[nazwa] = max(0.05, prom) / max(1e-6, m["promien"])
        self._znaki, self._znaki_klucz = znaki, klucz
        return znaki

    def _rysuj_cienie_miejscowosci(self, p, rzut):
        """Cienie plam zabudowy — leżą na gruncie, pod samą zabudową."""
        p.setPen(Qt.PenStyle.NoPen)
        wysokosc = self._wysokosc
        znaki = self._znaki_miejscowosci(rzut)
        for m in self._miejscowosci:
            wsp = znaki.get(m["nazwa"], 1.0)
            gleb = rzut.glebokosc(m["x"], m["y"], 0.0)
            if gleb < 12.0 or m["promien"] * wsp * rzut.k / gleb < 1.8:
                continue
            cx, cy = m["x"], m["y"]
            px = m["wys"] * wsp * rzut.cien_x
            py = m["wys"] * wsp * rzut.cien_y
            wiel = QPolygonF([rzut.ekran(cx + (x - cx) * wsp + px,
                                         cy + (y - cy) * wsp + py,
                                         wysokosc(cx + (x - cx) * wsp,
                                                  cy + (y - cy) * wsp))
                              for (x, y) in m["obrys"]])
            s = QPainterPath()
            s.addPolygon(wiel)
            p.fillPath(s, QColor(0, 0, 0, int(84 * (1.0 - rzut.mgla(gleb) * 0.75))))

    def _rysuj_miejscowosci(self, p, rzut):
        """Miejscowości od najdalszej do najbliższej — bliższa zasłania dalszą."""
        znaki = self._znaki_miejscowosci(rzut)
        widoczne = []
        for m in self._miejscowosci:
            gleb = rzut.glebokosc(m["x"], m["y"], 0.0)
            if gleb < 10.0:
                continue
            widoczne.append((gleb, m["nazwa"], m))
        widoczne.sort(key=lambda z: (-z[0], z[1]))
        for gleb, nazwa, m in widoczne:
            self._rysuj_miejscowosc(p, rzut, m, gleb, znaki.get(nazwa, 1.0))

    def _rysuj_miejscowosc(self, p, rzut, m, gleb, wsp=1.0):
        """Plama zabudowy, na niej kilka niskich brył, na wierzchu domy.

        ``wsp`` to powiększenie znaku z :meth:`_znaki_miejscowosci` — całą
        miejscowość rozciąga wokół jej środka, więc bryły i domy rosną razem
        z plamą i zostają widoczne.
        """
        skala = rzut.k / max(1.0, gleb)
        promien = m["promien"] * wsp
        szer_pix = promien * 2.0 * skala
        if szer_pix < 1.2:
            return
        mgla = rzut.mgla(gleb)
        wysokosc = self._wysokosc
        wys = m["wys"] * wsp
        cx, cy = m["x"], m["y"]

        def roz(x, y):
            """Punkt znaku: prawdziwe położenie rozciągnięte wokół środka osady."""
            return (cx + (x - cx) * wsp, cy + (y - cy) * wsp)

        p.setPen(Qt.PenStyle.NoPen)

        # a) łuna świateł rozlana wokół miejscowości — po niej widać osadę
        #    nawet wtedy, gdy sama plama ma kilka pikseli
        if szer_pix > 2.5:
            srodek = rzut.ekran(cx, cy, wysokosc(cx, cy))
            baza = m["ranga"] == RANGA_BAZA
            sila = (46 if baza else 34) * (1.0 - mgla * 0.5)
            # łuna jest poświatą nad osadą, nie osadą — przy ciasnym kadrze
            # rozlałaby się na pół ekranu, więc ma swój sufit
            luna = max(6.0, min(szer_pix * 1.45, 72.0 if baza else 46.0))
            st.punkt_swiatla(p, srodek, luna, QColor(255, 206, 140), int(sila))

        # b) plama: niski, zwarty kawałek terenu innego niż pole dookoła
        obrys = [roz(x, y) for (x, y) in m["obrys"]]
        dol = [rzut.ekran(x, y, wysokosc(x, y)) for (x, y) in obrys]
        gora = [rzut.ekran(x, y, wysokosc(x, y) + wys) for (x, y) in obrys]
        if szer_pix > 4.0:
            sciana = QPainterPath()
            sciana.setFillRule(Qt.FillRule.WindingFill)
            n = len(dol)
            for q in range(0, n, 2):
                q2 = (q + 2) % n
                sciana.addPolygon(QPolygonF([dol[q], dol[q2], gora[q2], gora[q]]))
            p.fillPath(sciana, rzut.zamgl(BARWA_BOKU, mgla, 0.55))
        wierzch = QPainterPath()
        wierzch.addPolygon(QPolygonF(gora))
        p.fillPath(wierzch, rzut.zamgl(BARWA_PLAMY, mgla, 0.62))

        # c) kilka niskich brył, od najdalszej do najbliższej
        if szer_pix > 3.0:
            bryly = []
            for b in m["bryly"]:
                bx, by = roz(b["x"], b["y"])
                bryly.append({"x": bx, "y": by, "bok": b["bok"] * wsp,
                              "glab": b["glab"] * wsp, "wys": b["wys"] * wsp,
                              "odcien": b["odcien"]})
            for b in sorted(bryly,
                            key=lambda z: -rzut.glebokosc(z["x"], z["y"], 0.0)):
                self._rysuj_bryle(p, rzut, b, mgla, skala)

        # d) domy: pojedyncze punkty na plamie, kilka z nich świeci ciepło
        if szer_pix > 5.0:
            r = max(0.75, min(2.6, promien * skala * 0.16))
            for (dx, dy, swieci) in m["domy"]:
                x, y = roz(dx, dy)
                pt = rzut.ekran(x, y, wysokosc(x, y) + wys * 0.92)
                p.setBrush(QBrush(st.z_alfa(st.BURSZTYN, int(225 * (1.0 - mgla)))
                                  if swieci
                                  else st.z_alfa(BARWA_DACHU, int(190 * (1.0 - mgla)))))
                p.drawEllipse(pt, r * (1.15 if swieci else 1.0), r * 0.8)
            p.setBrush(Qt.BrushStyle.NoBrush)

        # e) krawędź plamy od strony światła — domyka miejscowość
        if szer_pix > 6.0:
            lx, ly = rzut.swiatlo_ekran
            p.setBrush(Qt.BrushStyle.NoBrush)
            sr = wierzch.boundingRect().center()
            zas = max(wierzch.boundingRect().width(), 1.0) * 0.7
            p.setPen(_pioro_gradientowe(
                QPointF(sr.x() + lx * zas, sr.y() + ly * zas),
                QPointF(sr.x() - lx * zas, sr.y() - ly * zas),
                st.z_alfa(rzut.zamgl(st.MIETA, mgla), int(74 * (1.0 - mgla))),
                QColor(0, 0, 0, 0), 1.0))
            p.drawPath(wierzch)
            p.setPen(Qt.PenStyle.NoPen)

    def _rysuj_bryle(self, p, rzut, b, mgla, skala):
        """Niska bryła zabudowy: ściana boczna, przednia i dach."""
        x, y, bok, glab, wys = b["x"], b["y"], b["bok"], b["glab"], b["wys"]
        if bok * 2.0 * skala < 1.3:
            return
        h = self._wysokosc(x, y)
        z0, z1 = h, h + wys
        e = rzut.ekran
        # kamera stoi na południe i patrzy w dół: zawsze widać dach i ścianę
        # południową, a z boków ten, który jest odwrócony od osi kamery
        xb = x - bok if x > rzut.oko[0] else x + bok
        pd_l, pd_p = e(x - bok, y - glab, z0), e(x + bok, y - glab, z0)
        pg_l, pg_p = e(x - bok, y - glab, z1), e(x + bok, y - glab, z1)
        p.setPen(Qt.PenStyle.NoPen)
        sciana = QPainterPath()
        sciana.addPolygon(QPolygonF([e(xb, y + glab, z0), e(xb, y - glab, z0),
                                     e(xb, y - glab, z1), e(xb, y + glab, z1)]))
        p.fillPath(sciana, rzut.zamgl(BARWA_BOKU, mgla, 0.6))
        odcien = 104 + int(26 * (b["odcien"] - 0.5))
        przod = QPainterPath()
        przod.addPolygon(QPolygonF([pd_l, pd_p, pg_p, pg_l]))
        p.fillPath(przod, rzut.zamgl(BARWA_SCIANY.lighter(odcien), mgla, 0.6))
        dach = QPainterPath()
        dach.addPolygon(QPolygonF([pg_l, pg_p, e(x + bok, y + glab, z1),
                                   e(x - bok, y + glab, z1)]))
        p.fillPath(dach, rzut.zamgl(BARWA_DACHU.lighter(odcien), mgla, 0.6))

    # — podziałka —
    KROKI_PODZIALKI = (1, 2, 5, 10, 20, 25, 50, 100, 200)

    def _rysuj_podzialke(self, p, rzut, r):
        """Podziałka kilometrowa: dwa ramiona mierzone w środku układu miejscowości.

        Teren jest pochylony do widza, więc jeden odcinek nie może mierzyć
        naraz we wszystkich kierunkach: ten sam kilometr zajmuje w poprzek
        kadru więcej pikseli niż w głąb. Ramię poziome mierzy więc
        wschód-zachód, a pionowe północ-południe — oba w głębi środka rejonu,
        tam gdzie stoją miejscowości i gdzie porównuje się odległości.
        Ramię w głąb liczone jest rzutem prawdziwego odcinka gruntu, a nie
        mnożeniem przez cosinus, więc uwzględnia i pochylenie, i zbieżność.
        Podziałka leży przy dolnej krawędzi, żeby nie wchodzić na mapę.
        """
        ox, oy, sx, sy = self._obszar_swiata()
        cx, cy = ox + sx * 0.5, oy + sy * 0.5
        gleb = rzut.glebokosc(cx, cy, 0.0)
        na_km = rzut.k / max(1.0, gleb) * self._jedn_na_km     # pikseli na kilometr
        km = None
        for kandydat in self.KROKI_PODZIALKI:
            if kandydat * na_km >= r.width() * 0.115:
                km = kandydat
                break
        if km is None:
            return
        # ile pikseli ma ten sam odcinek położony z południa na północ
        pol = km * self._jedn_na_km * 0.5
        w_glab = abs(rzut.ekran(cx, cy + pol, 0.0).y()
                     - rzut.ekran(cx, cy - pol, 0.0).y())
        a = QPointF(r.x() + r.width() * 0.045, r.bottom() - r.height() * 0.060)
        b = QPointF(a.x() + km * na_km, a.y())
        c = QPointF(a.x(), a.y() - w_glab)
        if not r.contains(b) or not r.contains(c):
            return
        zab = max(2.5, (b.x() - a.x()) * 0.036)
        _poduszka(p, QRectF(a.x() - 5, c.y() - 12, b.x() - a.x() + 10,
                            a.y() - c.y() + zab + 16), sila=104, warstw=4)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(st.TEKST_2, 185), 1.2))
        p.drawLine(a, b)
        p.drawLine(a, c)
        for u in (0.0, 0.25, 0.5, 0.75, 1.0):
            dluga = u in (0.0, 0.5, 1.0)
            dlugosc = zab * (1.0 if dluga else 0.55)
            x = a.x() + (b.x() - a.x()) * u
            p.drawLine(QPointF(x, a.y()), QPointF(x, a.y() - dlugosc))
            y = a.y() + (c.y() - a.y()) * u
            p.drawLine(QPointF(a.x(), y), QPointF(a.x() + dlugosc, y))
        _napis(p, a.x(), a.y() - zab - 4.0, "0", st.z_alfa(st.TEKST_2, 185),
               9.0, 500, mono=True)
        _napis(p, b.x(), b.y() - zab - 4.0, "%d km" % km, st.z_alfa(st.TEKST, 215),
               9.0, 600, mono=True, prawy=True)
        _napis(p, c.x() + zab + 4.0, c.y() + 3.0, "%d km" % km,
               st.z_alfa(st.TEKST, 215), 9.0, 600, mono=True)

    # — pomocnicze —
    def _polozenie(self, nazwa):
        """Miejscowość w świecie. Nazwa spoza układu siada na bazie.

        Trasa dnia przychodzi z zewnątrz i może wymienić przystanek, którego
        w układzie miast nie ma. Do niedawna kończyło się to wyjątkiem w
        rysowaniu; teraz taki punkt po prostu leży na bazie."""
        return self._miasta.get(nazwa,
                                self._miasta.get(self._baza, (0.0, 0.0)))

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
        if not self._zegar_terenu.isActive():
            self._dopilnuj_terenu()                    # cała scena z jednego ziarna
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
        rzut = self.rzut()
        klucz = (self._klucz_kadru(), round(self.devicePixelRatioF(), 3),
                 self._geo_klucz, self._stan)
        if self._warstwy_klucz == klucz and self._dol is not None:
            return self._dol, self._gora

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
        """Dwie pixmapy sceny bez trasy: grunt z terenem i osobno miejscowości.

        Rozdział jest potrzebny, bo cień trasy leży na gruncie i musi trafić
        pod zabudowę, a sama trasa świeci nad nią. Obie zależą od rozmiaru
        widżetu i od ziarna dnia — przy powrocie do tego samego dnia obraz
        jest ten sam. W trakcie ciągnięcia okna zwracamy stare pixmapy
        i pozwalamy je rozciągnąć; przeliczenie czeka na koniec ruchu.
        """
        dpr = self.devicePixelRatioF()
        rzut = self.rzut()
        klucz = (self._klucz_kadru(), round(dpr, 3), self._ziarno)
        if self._statyk is not None and (self._statyk_klucz == klucz
                                         or self._zegar_terenu.isActive()):
            return self._statyk
        r = QRectF(self.rect())
        if self._pola is None:
            self._pola = self._zbuduj_pola(rzut)

        grunt = self._nowa_pixmapa()
        q = QPainter(grunt)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        st.tlo_sceny(q, r)                    # niebo i głębia
        self._rysuj_grunt(q, rzut, r)         # ziemia, na której leżą pola
        self._rysuj_pola(q)                   # pola i lasy, od dali do widza
        self._rysuj_rzeke(q, rzut)
        self._rysuj_drogi(q, rzut, self._drogi.values())
        self._rysuj_cienie_miejscowosci(q, rzut)   # cienie leżą na gruncie
        q.end()

        bryly = self._nowa_pixmapa()
        q = QPainter(bryly)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self._rysuj_miejscowosci(q, rzut)
        self._rysuj_mgle(q, rzut, r)          # mgła przykrywa też dalekie plamy
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
        klucz = (self._klucz_kadru(), trasa, self._stan, kot)
        if self._geo_klucz == klucz and self._geo is not None:
            return self._geo

        rzut = self.rzut()

        # a) trasa dnia poprowadzona po drogach
        odcinki = []
        dodatkowe = []
        for i in range(len(trasa) - 1):
            weze = self._po_drogach(trasa[i], trasa[i + 1])
            punkty = []
            for j in range(len(weze) - 1):
                kawalek = self._droga_miedzy(weze[j], weze[j + 1])
                if kawalek is None:                   # brak drogi: kładziemy nową
                    kawalek = _gladko_2d([self._polozenie(weze[j]),
                                          self._polozenie(weze[j + 1])], na_odcinek=4)
                    dodatkowe.append(kawalek)
                punkty.extend(kawalek if not punkty else kawalek[1:])
            odcinki.append(punkty or [self._polozenie(trasa[i]),
                                      self._polozenie(trasa[i + 1])])

        swiat_glowna = []
        for punkty in odcinki[:-1]:
            swiat_glowna.extend(punkty if not swiat_glowna else punkty[1:])
        swiat_powrot = odcinki[-1]

        # b) rzut: trasa unosi się nad gruntem, jej cień leży na gruncie.
        #    skala to liczba pikseli na jednostkę świata — po niej dobieramy
        #    grubości, więc linia zwęża się w głębi sceny
        odn = self._odniesienie()

        def na_ekran(punkty, wznios):
            pkt, ska = [], []
            for (x, y) in punkty:
                z = self._wysokosc(x, y) + wznios
                p, s = rzut.rzutuj(x, y, z)
                pkt.append(p)
                ska.append(s * odn)
            return pkt, ska

        wznios = self._wznios_trasy
        pkt_gl, ska_gl = na_ekran(swiat_glowna, wznios)
        pkt_pw, ska_pw = na_ekran(swiat_powrot, wznios)
        cien_gl, ska_cgl = na_ekran(swiat_glowna, 0.0)
        cien_pw, ska_cpw = na_ekran(swiat_powrot, 0.0)

        glowna = _lamana(pkt_gl)
        powrot = _lamana(pkt_pw)
        probki_swiat = _rowno(swiat_glowna, 150)
        probki, skale_probek = na_ekran(probki_swiat, wznios)

        # c) słupy przystanków: im więcej wizyt, tym wyższy słup światła
        ile_wizyt = {}
        for n in trasa[1:-1]:
            ile_wizyt[n] = ile_wizyt.get(n, 0) + 1
        slupy = []
        for nazwa in [self._baza] + [n for n in trasa[1:-1]]:
            if nazwa not in self._miasta or any(s["nazwa"] == nazwa for s in slupy):
                continue
            x, y = self._miasta[nazwa]
            h = self._wysokosc(x, y)
            baza = (nazwa == self._baza)
            miara = self._miara
            wysokosc = (UDZIAL_SLUPA_BAZY * miara if baza else
                        (UDZIAL_SLUPA_PRZYSTANKU
                         + UDZIAL_SLUPA_WIZYTY * (ile_wizyt.get(nazwa, 1) - 1)
                         + 0.017 * _hasz(nazwa, 31)) * miara)
            dol, skala = rzut.rzutuj(x, y, h)
            gora, skala_g = rzut.rzutuj(x, y, h + wysokosc)
            slupy.append({"nazwa": nazwa, "dol": dol, "gora": gora,
                          "skala": skala * odn, "skala_g": skala_g * odn,
                          "baza": baza, "wizyty": ile_wizyt.get(nazwa, 1)})

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
        warstwy = ((3.1, 52, 4), (1.7, 66, 2), (0.9, 78, 1))
        _poswiata_zmienna(p, geo["cien_glowna"], geo["ska_cglowna"], czern, warstwy)
        _poswiata_zmienna(p, geo["cien_powrot"], geo["ska_cpowrot"], czern, warstwy)

    def _rysuj_trase(self, p, geo):
        """Świecąca linia leżąca nad terenem, węższa w głębi sceny."""
        kolor = self._kolor_trasy()
        _poswiata_zmienna(p, geo["pkt_glowna"], geo["ska_glowna"], kolor,
                          ((7.4, 20, 5), (4.1, 42, 3), (2.1, 118, 2), (1.0, 226, 1)))
        _poswiata_zmienna(p, geo["pkt_glowna"], geo["ska_glowna"],
                          QColor(232, 255, 255), ((0.36, 185, 1),))

    def _rysuj_powrot(self, p, geo):
        """Powrót do bazy: kreski wolno płyną w stronę domu."""
        k = self._grubosc()
        ska = geo["ska_powrot"]
        sr = sum(ska) / max(1, len(ska))
        przesun = -self._faza * 34.0 * k if self._anim else 0.0
        _kreskowana(p, geo["powrot"], st.ZIELEN,
                    warstwy=((4.2 * sr, 30), (2.0 * sr, 76), (0.80 * sr, 235)),
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
            for szer, sila, barwa in ((6.0 * s, 34, kolor),
                                      (2.8 * s, 74, kolor),
                                      (1.3 * s, 112, kolor),
                                      (0.6 * s, 245, QColor(240, 255, 255))):
                pen = QPen(st.z_alfa(barwa, sila * jas), max(0.8, szer))
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.drawLine(a, b)
        # czubek blasku
        if 0.0 <= czolo <= 1.0:
            ic = max(0, min(n, int(round(czolo * n))))
            glowa = probki[ic]
            st.punkt_swiatla(p, glowa, 13.0 * skale[ic], kolor, 62)
            st.punkt_swiatla(p, glowa, 5.0 * skale[ic], QColor(235, 255, 255), 96)

    # — słupy przystanków —
    def _rysuj_slupy(self, p, rzut, geo):
        """Pionowe słupy światła nad miastami — wyższe tam, gdzie więcej wizyt."""
        kolor = self._kolor_trasy()
        if geo is None:
            # sam teren: baza zaznaczona dyskretnym słupem
            x, y = self._miasta.get(self._baza, (0.0, 0.0))
            h = self._wysokosc(x, y)
            odn = self._odniesienie()
            dol, ska = rzut.rzutuj(x, y, h)
            gora, ska_g = rzut.rzutuj(x, y, h + UDZIAL_SLUPA_BAZY * 0.7 * self._miara)
            self._pierscien(p, dol, ska * odn * 3.4, st.ZIELEN, 0.55)
            self._slup(p, dol, gora, ska_g * odn, st.ZIELEN, 0.55)
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
        for szer, alfa in ((4.8, 26), (2.1, 66), (0.72, 190)):
            g = QLinearGradient(dol, gora)
            g.setColorAt(0.0, st.z_alfa(kolor, int(alfa * 0.35 * waga)))
            g.setColorAt(0.45, st.z_alfa(kolor, int(alfa * waga)))
            g.setColorAt(1.0, st.z_alfa(kolor, int(alfa * 0.9 * waga)))
            pen = QPen(QBrush(g), max(0.8, szer * skala))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(dol, gora)
        st.punkt_swiatla(p, gora, max(5.0, 9.0 * skala), kolor, int(96 * waga))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(st.z_alfa(QColor(238, 255, 255), int(245 * waga))))
        r = max(1.6, 2.1 * skala)
        p.drawEllipse(gora, r, r)

    def _pierscien(self, p, dol, r, kolor, waga):
        """Ślad przystanku na gruncie — spłaszczona elipsa, bo teren jest pochylony."""
        r = max(3.0, r)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(4, 12, 21, 96)))    # przeziera przez niego plama
        p.drawEllipse(dol, r, r * 0.56)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(st.z_alfa(kolor, int(215 * waga)), max(1.0, r * 0.26)))
        p.drawEllipse(dol, r, r * 0.56)
        p.setPen(QPen(st.z_alfa(kolor, int(60 * waga)), 1.0))
        p.drawEllipse(dol, r * 1.85, r * 1.85 * 0.56)

    def _rysuj_puls_bazy(self, p):
        """Wolny oddech halo bazy — jedyny ruch poza blaskiem trasy."""
        puls = 0.5 + 0.5 * math.sin(self._faza * 2.0 * math.pi)
        x, y = self._miasta.get(self._baza, (0.0, 0.0))
        rzut = self.rzut()
        dol, ska = rzut.rzutuj(x, y, self._wysokosc(x, y))
        r = max(3.4, ska * self._odniesienie() * 4.4)
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
    LUZY_PODPISU = (9.0, 20.0, 34.0, 52.0, 76.0, 108.0, 148.0)
    ODSTEP_PODPISOW = 3.0        # tyle pikseli przerwy zostaje między tabliczkami
    NITKA_PODPISU = 44.0         # dalej odsunięta tabliczka dostaje nitkę odniesienia

    def _obszar_podpisow(self):
        """Prostokąt, poza który tabliczka wyjść nie może: widżet bez brzegu."""
        return QRectF(self.rect()).adjusted(6, 5, -6, -5)

    def _ulozenie_podpisow(self, slupy, probki, pkt_powrot, nitka):
        """Tabliczki rozsuwane wokół swoich punktów — raz na układ, nie co klatkę.

        Każda szuka miejsca w ośmiu kierunkach od szczytu swojego słupa,
        zaczynając od najkrótszego odsunięcia. Wyjście poza widżet, wejście na
        kartkę delegacji i wejście na już położoną tabliczkę są ZAKAZANE, a nie
        tylko drogie — inaczej osiem tabliczek dnia układało się w jeden stos
        w rogu. Kiedy przy mieście nie ma wolnego miejsca, tabliczka odchodzi
        dalej i łączy ją z punktem cienka nitka odniesienia.

        Wszystko idzie po listach w stałej kolejności — słupy w kolejności
        trasy, kierunki i odsunięcia z krotek — więc ta sama trasa daje zawsze
        ten sam układ co do piksela, także przy innym PYTHONHASHSEED.
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

        brzeg = self._obszar_podpisow()
        kartka = self._pole_kartki()
        zajete, etykiety = [], []
        # baza pierwsza, potem przystanki w kolejności trasy — dokładnie tak,
        # jak zbudowana jest lista słupów. Żadnego sortowania po położeniu na
        # ekranie ani po zbiorze: ta sama trasa ma zawsze dać ten sam układ
        for s in slupy:
            baza = s["baza"]
            napis = f"{s['nazwa']} · start i powrót" if baza else s["nazwa"]
            m = m_baza if baza else m_zwykly
            szer = m.horizontalAdvance(napis) + (baza and 20 or 16)
            wys = m.height() + 8
            kotwica = s["gora"]
            pole = self._miejsce_podpisu(kotwica, szer, wys, zajete, brzeg,
                                         kartka, przeszkody, slupy, s)
            zajete.append(pole)
            rozmiar, waga = (rozm_b, 700) if baza else (rozm_z, 600)
            odlegla = math.hypot(pole.center().x() - kotwica.x(),
                                 pole.center().y() - kotwica.y()) > self.NITKA_PODPISU
            etykiety.append({"pole": pole, "napis": napis, "rozmiar": rozmiar,
                             "waga": waga, "baza": baza, "kotwica": kotwica,
                             "powtorka": s["wizyty"] > 1, "nitka": odlegla})
        return etykiety

    def _miejsce_podpisu(self, kotwica, szer, wys, zajete, brzeg, kartka,
                         przeszkody, slupy, moj):
        """Wolne miejsce na jedną tabliczkę: najpierw przy mieście, potem dalej.

        Trzy podejścia, jedno po drugim: osiem stron świata przy coraz większym
        odsunięciu (tabliczka ma leżeć przy swoim mieście), kratka całego
        wolnego kadru (gdy przy mieście nie ma już miejsca), a na koniec — gdy
        kadr jest ciasny do granic — położenie o najmniejszym nachodzeniu,
        wciągnięte do widżetu. Żaden krok niczego nie losuje.
        """
        odstep = self.ODSTEP_PODPISOW

        def wolne(pole):
            if not brzeg.contains(pole):
                return False
            if kartka is not None and not pole.intersected(kartka).isEmpty():
                return False
            for inne in zajete:
                if not pole.intersected(
                        inne.adjusted(-odstep, -odstep, odstep, odstep)).isEmpty():
                    return False
            return True

        def koszt(pole, podstawa):
            """Im mniej tabliczka zasłania, tym lepsze miejsce."""
            k = podstawa
            for pt in przeszkody:
                if pole.contains(pt):
                    k += 60.0
            for s2 in slupy:                         # nie zasłaniamy cudzych słupów
                if s2 is not moj and pole.contains(s2["gora"]):
                    k += 120.0
            return k

        def probne(luz, kx, ky):
            # środek tabliczki odsunięty od kotwicy o pół jej rozmiaru plus luz
            # — dzięki temu kreska zostaje krótka w każdą stronę
            sx = kotwica.x() + kx * (szer * 0.5 + luz)
            sy = kotwica.y() + ky * (wys * 0.5 + luz)
            return QRectF(sx - szer * 0.5, sy - wys * 0.5, szer, wys)

        # a) wokół miasta, od najbliższego pierścienia
        for luz in self.LUZY_PODPISU:
            najlepszy, najkoszt = None, None
            for nr, (kx, ky) in enumerate(self.KIERUNKI_PODPISU):
                pole = probne(luz, kx, ky)
                if not wolne(pole):
                    continue
                k = koszt(pole, nr * 5.0)
                if najkoszt is None or k < najkoszt:
                    najkoszt, najlepszy = k, pole
            if najlepszy is not None:
                return najlepszy

        # b) kratka całego wolnego kadru — bierzemy miejsce najbliższe miastu
        krok = max(8.0, wys * 0.6)
        najlepszy, najkoszt = None, None
        y = brzeg.top()
        while y + wys <= brzeg.bottom() + 0.01:
            x = brzeg.left()
            while x + szer <= brzeg.right() + 0.01:
                pole = QRectF(x, y, szer, wys)
                if wolne(pole):
                    k = koszt(pole, math.hypot(pole.center().x() - kotwica.x(),
                                               pole.center().y() - kotwica.y()))
                    if najkoszt is None or k < najkoszt:
                        najkoszt, najlepszy = k, pole
                x += krok
            y += krok
        if najlepszy is not None:
            return najlepszy

        # c) nie ma wolnego miejsca: najmniej nachodzące, wciągnięte do widżetu
        najlepszy, najkoszt = None, None
        for luz in self.LUZY_PODPISU:
            for kx, ky in self.KIERUNKI_PODPISU:
                pole = probne(luz, kx, ky)
                x = min(max(pole.x(), brzeg.left()),
                        max(brzeg.left(), brzeg.right() - szer))
                y = min(max(pole.y(), brzeg.top()),
                        max(brzeg.top(), brzeg.bottom() - wys))
                pole = QRectF(x, y, szer, wys)
                k = luz * 0.2
                for inne in zajete:
                    w = pole.intersected(inne)
                    k += w.width() * w.height()
                if kartka is not None:
                    w = pole.intersected(kartka)
                    k += w.width() * w.height() * 0.5
                if najkoszt is None or k < najkoszt:
                    najkoszt, najlepszy = k, pole
        return najlepszy

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
            if e.get("nitka"):
                # tabliczka odsunięta dalej od swojego miasta: nitka odniesienia
                # kończy się kropką, żeby było widać, czyj to podpis
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(st.z_alfa(barwa, 190)))
                p.drawEllipse(kotwica, 2.2, 2.2)
                p.setBrush(Qt.BrushStyle.NoBrush)

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
        ostatni = dzien.przystanki[-1] if dzien.przystanki else self._baza

        def dystans(nazwa):
            s = self._punkt(nazwa)
            return math.hypot(s.x() - dokad.x(), s.y() - dokad.y())

        # przy równej odległości decyduje nazwa, nie kolejność listy
        najblizszy = min(dzien.przystanki or [self._baza],
                         key=lambda n: (dystans(n), n))
        if dystans(najblizszy) < dystans(ostatni) * 0.75:
            ostatni = najblizszy
        x, y = self._miasta.get(ostatni, self._miasta.get(self._baza, (0.0, 0.0)))
        skad = self.rzut().ekran(x, y, self._wysokosc(x, y)
                                 + UDZIAL_SLUPA_PRZYSTANKU * self._miara)
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
        for nazwa in self._nazwy():
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
