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

Białe plamy rejonu: rejon leży pod delikatną mgłą (część gotowej warstwy pod
trasą, więc klatka nic za nią nie płaci). Miejscowości ze śladem obecności
programu — :meth:`MapaDnia.ustaw_odkryte` — są z niej wycięte i świecą,
trasa dnia i jej przystanki zawsze. W prawym dolnym rogu ramy stoją dwie
liczby: odkryte / w zasięgu (:meth:`MapaDnia.odkryte_w_zasiegu`). Bez śladu
wszystko leży pod mgłą, a licznik pokazuje 0 / N.

Kartka delegacji ma dwie strony: przód to polecenie wyjazdu, odwrót
(:func:`tresc_tylu`) to ten sam dzień taki, jaki był naprawdę. Klik obraca
kartkę — obrót jest przekształceniem gotowej pixmapy, nie rysowaniem.

Zegary: MapaDnia i KartkaDelegacji mają ``ustaw_animacje(wlaczone)``.
Wyłączenie zatrzymuje zegar i ustawia stałą fazę (także obrót kartki) —
zrzuty są powtarzalne. Zegary gasną też przy schowaniu i zamknięciu widżetu.

Prawdziwe współrzędne: :meth:`MapaDnia.ustaw_miasta` przyjmuje słownik
{nazwa: (szerokość, długość, ranga)} i rzutuje go na płaszczyznę mapy
z zachowaniem proporcji odległości. Tak podaje je nowy_wyglad — wprost
z geokodowania silnika. Bez tego wywołania mapa pracuje na ułamkowych
współrzędnych z proto_dane, dokładnie jak dotąd.
"""
import copy
import math
import time
import unicodedata

from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QTimer, QEvent, pyqtSignal
from PyQt6.QtGui import (QPainter, QPainterPath, QPen, QBrush, QColor, QPixmap,
                         QFontMetricsF, QLinearGradient, QRadialGradient,
                         QPolygonF, QRegion, QTransform)
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
# ── białe plamy rejonu ───────────────────────────────────────────────
# Rejon pracy leży pod delikatną mgłą. Miejscowości, w których program ma
# ślad obecności (wpis w historii — MapaDnia.ustaw_odkryte), są z niej
# wycięte i świecą; trasa dnia i jej przystanki są odsłonięte zawsze. Mgła
# jest częścią gotowej warstwy POD trasą (MapaDnia._warstwy), więc klatka
# animacji nie dokłada za nią ani jednego wywołania. Licznik w rogu ramy:
# odkryte / w zasięgu (bez bazy — w niej się mieszka, nie odkrywa).
BARWA_MGLY_REJONU = QColor(178, 194, 212)
ALFA_MGLY_REJONU = (36, 68)       # gęstość zasłony: w głębi sceny i przy widzu
PROMIEN_ODKRYCIA = 2.3            # wycięcie względem promienia znaku miejscowości
PROMIEN_ODKRYCIA_PX = (34.0, 130.0)   # najmniejsze i największe wycięcie
BARWA_ODKRYCIA = st.MIETA         # poświata odkrytej miejscowości
# Mgła jest miękka, więc rysuje się w POŁOWIE rozdzielczości i rozciąga —
# szerokie, wygładzane pociągnięcia korytarza trasy kosztują cztery razy
# mniej, a oko nie widzi różnicy (zasłona nie ma ostrych krawędzi).
SKALA_MGLY = 0.5
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
# Kadr ustępuje kartce i paskom, ale nie bez końca: gdyby po ustąpieniu został
# skrawek węższy niż ten ułamek widżetu, zasłonę pomijamy. Tak wygląda układ
# jeszcze nieustawiony — okno buduje się, kartka siedzi w lewym górnym rogu —
# i lepiej narysować trasę na całej mapie, niż wcisnąć ją w pasek przy brzegu.
UDZIAL_MIN_KADRU = 0.34
# Kamera wpasowuje w kadr ROZPIĘTOŚĆ TRASY, a rysuje się coś grubszego: linia
# ma szerokość, a jej świecąca głowa promień kilkudziesięciu pikseli. Obie
# miary podane są tak samo jak grubości trasy — w jednostkach odniesienia.
# ── życie na mapie ───────────────────────────────────────────────────
# Trzy ruchy, których nie da się nazwać miganiem: każdy trwa kilkanaście
# sekund. Wszystkie liczone są W ŚWIECIE i rzutowane tą samą kamerą, co
# teren, więc światło na dalekiej drodze jest mniejsze niż na bliskiej.
# Wszystkie gasną razem z ustaw_animacje(False) i wtedy mapa wygląda
# dokładnie tak, jak wyglądała przed nimi.
#
# Cień chmury wędrujący po terenie był próbowany i został WYRZUCONY:
# na tak ciemnym krajobrazie ciemna plama nie czyta się jako chmura,
# tylko jako nierówność rysunku (zrzuty w katalogu roboczym rundy).
# Klatka mapy ma się mieścić w tym budżecie. Kiedy komputer jej nie
# wyrabia (słaby laptop, antywirus, wielki ekran), ŻYCIE MAPY GAŚNIE SAMO
# i wraca dopiero wtedy, gdy klatka znowu schodzi poniżej progu powrotu.
# Przerwa między progami jest szersza niż koszt samych efektów, więc nic
# tu nie zacznie mrugać w kółko. Ściszanie zdejmuje SAMO ŻYCIE REJONU;
# blask trasy i płynące kreski powrotu zostają, bo były tu przed nim
# i kosztują ułamek tego, co ono.
SUFIT_KLATKI_MS = 16.0
PROG_POWROTU_MS = 12.0
KLATEK_DO_DECYZJI = 8         # tyle klatek z rzędu musi potwierdzić zmianę

OKRES_DROGI_MS = 23000.0      # ile jedzie jedno światełko od końca drogi do końca
SWIATEL_DROG = 5              # tyle świateł jedzie naraz po całym rejonie
BARWA_SWIATLA_DROGI = QColor(255, 208, 140)
OKRES_RZEKI_MS = 19000.0      # połysk przepływa wzdłuż rzeki

PROMIEN_LINII = 4.2           # połowa najszerszej warstwy samej linii
PROMIEN_BLASKU = 13.0         # promień świecącej głowy płynącej po trasie
CZAS_ODSLONY_MS = 1500        # ile trwa rysowanie trasy od bazy z powrotem do bazy

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

    def poszerzony(self, dodatkowo_px):
        """Ta sama kamera na filmie szerszym o ``dodatkowo_px`` z każdej strony.

        Ogniskowa, oko i kąt zostają; przesuwa się tylko środek filmu. Obraz
        na szerokim filmie jest więc pikselowo tym samym obrazem, co na
        wąskim, z dodanym po bokach dalszym ciągiem sceny — na tym stoi
        przelot nad rejonem (:class:`PrzelotRejonu`)."""
        nowy = copy.copy(self)
        nowy.px = self.px + float(dodatkowo_px)
        return nowy

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


def _narastajaco(punkty):
    """Długość łamanej narastająco — po niej mierzy się postęp rysowania."""
    dlug = [0.0]
    for i in range(1, len(punkty)):
        dlug.append(dlug[-1] + math.hypot(punkty[i].x() - punkty[i - 1].x(),
                                          punkty[i].y() - punkty[i - 1].y()))
    return dlug


def _udzial_punktu(swiat, dlug, pozycja):
    """W którym miejscu łamanej (0..1) leży dany punkt świata."""
    if pozycja is None or len(swiat) < 2 or dlug[-1] <= 0.0:
        return 0.0
    naj, gdzie = None, 0
    for i, (x, y) in enumerate(swiat):
        d = (x - pozycja[0]) ** 2 + (y - pozycja[1]) ** 2
        if naj is None or d < naj:
            naj, gdzie = d, i
    return max(0.0, min(1.0, dlug[min(gdzie, len(dlug) - 1)] / dlug[-1]))


def _uciecie(dlug, udzial):
    """Na którym odcinku łamanej i w jakim jego ułamku urywa się rysowanie.

    Zwraca (ile punktów w całości, ułamek ostatniego odcinka). Po tej parze
    docina się nie tylko samą linię, ale i wszystko, co idzie z nią równolegle
    — cień na gruncie i skale rzutu — więc każda z tych łamanych kończy się
    w tym samym miejscu trasy, a nie na najbliższym własnym punkcie.
    """
    n = len(dlug)
    if n < 2 or dlug[-1] <= 0.0:
        return n, 0.0
    cel = max(0.0, min(1.0, udzial)) * dlug[-1]
    i = 1
    while i < n - 1 and dlug[i] < cel:
        i += 1
    odc = max(1e-9, dlug[i] - dlug[i - 1])
    return i, max(0.0, min(1.0, (cel - dlug[i - 1]) / odc))


def _punkt_miedzy(lista, i, t):
    """Punkt między dwoma sąsiednimi punktami łamanej."""
    if not lista:
        return None
    i = max(1, min(i, len(lista) - 1))
    a, b = lista[i - 1], lista[i]
    return QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t)


def _miara_miedzy(lista, i, t):
    """Ta sama interpolacja dla listy liczb — na przykład skal rzutu."""
    if not lista:
        return 1.0
    i = max(1, min(i, len(lista) - 1))
    return lista[i - 1] + (lista[i] - lista[i - 1]) * t


def _domknij(lista, ostatni):
    """Lista z domalowanym ostatnim elementem; None nic nie dokłada."""
    wynik = list(lista)
    if ostatni is not None:
        wynik.append(ostatni)
    return wynik


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


# Kolor ostrzeżenia NA BIAŁEJ KARTCE — bursztyn z ciemnego tła (st.BURSZTYN)
# na papierze ginie, więc rubryka bez nazwiska dostaje jego ciemniejszy ton.
OSTRZEZENIE_NA_PAPIERZE = QColor("#B8730A")


def _tekst_menedzera(wartosc):
    """(tekst do rubryki MENEDŻER, czy to brak). Nazwisko przychodzi WYŁĄCZNIE
    z pliku menedzer.txt; wartość w nawiasie to zaślepka za brak pliku —
    rubryka pokazuje wtedy kreskę w kolorze ostrzeżenia, nie zielony sukces
    (dotąd świeciło tu „uzupełniony", a na PDF rubryka wychodziła pusta)."""
    tekst = str(wartosc or "").strip()
    if not tekst or tekst.startswith("("):
        return "—", True
    return tekst, False


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


# ── druga strona kartki: dzień taki, jaki był naprawdę ───────────────
# Skąd wzięły się kilometry odcinka — nazwy jak w PMT_Delegacje
# (stan_zrodla_odleglosci) i ich etykiety na papierze. Barwy: realne drogi
# zielenią sukcesu, pamięć dróg spokojnym granatem, szacunek ostrzeżeniem.
ZRODLO_DROGI, ZRODLO_PAMIEC, ZRODLO_SZACUNEK = "drogi", "pamiec", "szacunek"
ETYKIETY_ZRODEL = {ZRODLO_DROGI: "drogi", ZRODLO_PAMIEC: "pamięć",
                   ZRODLO_SZACUNEK: "szacunek"}
KOLEJNOSC_ZRODEL = (ZRODLO_DROGI, ZRODLO_PAMIEC, ZRODLO_SZACUNEK)


def etapy_dnia(dzien):
    """Odcinki dnia na drugą stronę kartki, w jednej postaci.

    Z pola ``dzien.etapy`` (program: godziny z dokumentu, kilometry silnika,
    linia prosta i źródło każdego odcinka), a gdy go nie ma — z
    :func:`odcinki_dnia`, czyli z rozkładu prototypu: bez linii prostej
    i bez źródła. Każdy wpis: {"z", "do", "wyj", "przyj", "km", "prosta",
    "zrodlo"}; ``prosta`` to None, gdy nieznana, ``zrodlo`` to „" gdy nieznane.
    """
    if dzien is None or getattr(dzien, "wolny", False):
        return []
    surowe = list(getattr(dzien, "etapy", None) or [])
    if not surowe:
        surowe = odcinki_dnia(dzien)
    wynik = []
    for o in surowe:
        if not isinstance(o, dict):
            continue
        try:
            km = max(0.0, float(o.get("km") or 0.0))
        except (TypeError, ValueError):
            km = 0.0
        prosta = o.get("prosta")
        try:
            prosta = float(prosta) if prosta not in (None, "") else None
        except (TypeError, ValueError):
            prosta = None
        if prosta is not None and prosta <= 0.0:
            prosta = None
        zrodlo = str(o.get("zrodlo") or "")
        wynik.append({"z": str(o.get("z") or ""), "do": str(o.get("do") or ""),
                      "wyj": str(o.get("wyj") or ""), "przyj": str(o.get("przyj") or ""),
                      "km": km, "prosta": prosta,
                      "zrodlo": zrodlo if zrodlo in ETYKIETY_ZRODEL else ""})
    return wynik


def _roznica_minut(od, do):
    """Minuty od godziny ``od`` do ``do`` (przez północ też); None bez godzin."""
    if not od or not do:
        return None
    return (_na_minuty(do) - _na_minuty(od)) % (24 * 60)


def _czas_hm(minuty):
    """Minuty → „4 h 50" albo „23 min"; None → „—"."""
    if minuty is None:
        return "—"
    minuty = int(round(minuty))
    if minuty < 60:
        return "%d min" % minuty
    return "%d h %02d" % (minuty // 60, minuty % 60)


def tresc_tylu(dzien):
    """Liczby na odwrót kartki — jedno miejsce, z którego czyta i rysunek,
    i sprawdzenia.

    Zwraca słownik: ``etapy`` (patrz :func:`etapy_dnia`), ``wyjazd`` i
    ``powrot`` (godziny), ``jazda_min`` / ``postoje_min`` / ``razem_min``
    (minuty w drodze: jazda to suma odcinków, postoje to reszta dnia),
    ``postoje`` (minuty postoju po każdym odcinku; ostatni — None),
    ``km`` (suma odcinków), ``prosta`` (suma linii prostych, gdy ma ją KAŻDY
    odcinek, inaczej None), ``wskaznik`` (km / prosta albo None) i ``zrodla``
    ({źródło: liczba odcinków}, tylko znane). Dzień wolny — pusty słownik.
    """
    etapy = etapy_dnia(dzien)
    if not etapy:
        return {}
    wyjazd = etapy[0]["wyj"]
    powrot = etapy[-1]["przyj"]
    razem = _roznica_minut(wyjazd, powrot)
    jazda = 0
    znane = True
    for e in etapy:
        d = _roznica_minut(e["wyj"], e["przyj"])
        if d is None:
            znane = False
            break
        jazda += d
    postoje = []
    for i, e in enumerate(etapy):
        if i == len(etapy) - 1:
            postoje.append(None)
        else:
            postoje.append(_roznica_minut(e["przyj"], etapy[i + 1]["wyj"]))
    km = round(sum(e["km"] for e in etapy), 1)
    prosta = None
    if all(e["prosta"] is not None for e in etapy):
        prosta = round(sum(e["prosta"] for e in etapy), 1)
    zrodla = {}
    for e in etapy:
        if e["zrodlo"]:
            zrodla[e["zrodlo"]] = zrodla.get(e["zrodlo"], 0) + 1
    return {
        "etapy": etapy, "wyjazd": wyjazd, "powrot": powrot,
        "razem_min": razem,
        "jazda_min": jazda if znane else None,
        "postoje_min": (max(0, razem - jazda) if (znane and razem is not None) else None),
        "postoje": postoje, "km": km, "prosta": prosta,
        "wskaznik": (km / prosta if prosta else None),
        "zrodla": zrodla,
    }


# ── mapa dnia ────────────────────────────────────────────────────────
class MapaDnia(QWidget):
    """Trójwymiarowa mapa okolicy z trasą dnia. Cała rysowana ręcznie."""

    klikniete_miasto = pyqtSignal(str)
    trasa_rysuje_sie = pyqtSignal()   # trasa zaczyna się rysować — kartka ustępuje
    trasa_gotowa = pyqtSignal()       # trasa dobiegła końca — kartka może wejść

    KLATKA = 40                # ms między klatkami blasku
    OKRES_BLASKU = 7600.0      # ms na jeden przebieg blasku wzdłuż trasy
    FAZA_ZRZUTU = 0.46         # gdzie stoi blask przy wyłączonej animacji

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setMinimumSize(360, 250)
        self._dzien = None
        self._kotwica = None
        self._pole_kar = None           # prawdziwy prostokąt kartki, podany przez okno
        self._zaslony = ()              # inne widżety leżące na mapie (pigułka, zakres)
        self._obecnosc_kar = 1.0        # ile kartki widać: cień i nitka idą za tym
        self._stan = "zwykly"
        # trasa dnia i kadr liczone raz na układ miast — nie co klatkę
        self._wersja_swiata = 0
        self._sciezka_pam = None
        self._sciezka_klucz = None
        self._obszar_pam = None
        self._obszar_klucz = None
        self._probki_pam = None
        self._probki_klucz = None

        # geometria świata liczona raz, niezależna od rozmiaru okna
        self._baza = dn.BAZA
        self._jedn_na_km = JEDNOSTEK_NA_KM    # ile jednostek świata ma kilometr
        self._miasta = {n: _swiat_miasta(*fr) for n, fr in dn.MIASTA.items()}
        self._rangi = {n: _ranga_domyslna(n, n == self._baza) for n in self._miasta}
        self._geo_odniesienie = None    # (lat0, lng0, cx, cy, skala) po ustaw_miasta
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
        self._dol = None                # statyka bez trasy: pod życiem mapy
        self._trasa_pix = None          # sama linia trasy: NAD życiem mapy
        self._gora = None               # słupy przystanków i tabliczki
        self._warstwy_klucz = None
        self._geo = None                # policzona geometria trasy i podpisów
        self._geo_klucz = None
        self._cien_pix = None           # cień kartki — nieruchomy, więc w pixmapie
        self._cien_klucz = None
        self._wykonczenie_pix = None    # winieta i ziarno — też się nie ruszają
        self._wykonczenie_klucz = None
        self._faza = self.FAZA_ZRZUTU
        self._czas_zycia = 0.0          # zegar życia na mapie, w milisekundach
        self._koszt_klatki = 0.0        # średni koszt klatki, w milisekundach
        self._ciche = False             # True, kiedy komputer nie wyrabia
        self._pod_rzad = 0              # ile klatek z rzędu mówi to samo
        self._swiatla_pam = None        # światła na drogach, liczone raz na świat
        self._swiatla_klucz = None
        self._odkryte_surowe = frozenset()   # ślad obecności: klucze nazw (NFC, casefold)
        self._odkryte_pam = None        # ...dopasowane do nazw tej mapy
        self._wersja_odkrytych = 0      # zmiana śladu unieważnia warstwę z mgłą
        self._anim = True
        # ile trasy jest już narysowane: 0 to sama baza, 1 to powrót do domu
        self._odslona = st.Plynnie(1.0, czas=CZAS_ODSLONY_MS, krzywa="lagodna",
                                   rodzic=self, przy_zmianie=self.update, klatka=25)
        self._odslona.koniec.connect(self._koniec_odslony)
        self._odslonieta = None         # trasa, którą już narysowano do końca
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
        poprzednia = self._klucz_trasy()
        self._dzien = dzien
        self._geo_klucz = None
        self._ustaw_ziarno(_ziarno_dnia(dzien))
        if self._klucz_trasy() != poprzednia:
            self._zacznij_odslone()
        self._rozsadz_zegar()
        self.update()

    def _klucz_trasy(self):
        """Trasa dnia jako niezmienna krotka; dzień wolny i brak dnia to ()."""
        d = self._dzien
        if d is None or getattr(d, "wolny", False):
            return ()
        return tuple(d.trasa)

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
        self._odkryte_pam = None
        self._wersja_odkrytych += 1
        self._przebuduj_swiat()
        self._rzut = None
        self._rzut_klucz = None
        self._pola = None
        self._statyk_klucz = None
        self._warstwy_klucz = None
        self._geo_klucz = None
        self.update()

    # — białe plamy rejonu —
    @staticmethod
    def _klucz_nazwy(nazwa):
        """Nazwa w postaci porównywalnej: NFC, jedna spacja, bez wielkości liter."""
        return unicodedata.normalize("NFC", " ".join(str(nazwa or "").split())).casefold()

    def ustaw_odkryte(self, nazwy):
        """Miejscowości ze śladem obecności programu — wycięte z mgły rejonu.

        ``nazwy`` to dowolny zbiór nazw (np. klucze miejsc_wizyty z historii);
        dopasowanie do nazw mapy jest niewrażliwe na wielkość liter i formę
        Unicode. Nazwy spoza mapy niczego nie psują — po prostu nie liczą się
        do odkrytych. Pusty zbiór: cały rejon pod mgłą, licznik 0 / N.
        """
        klucze = frozenset(self._klucz_nazwy(n) for n in (nazwy or ()) if n)
        if klucze == self._odkryte_surowe:
            return
        self._odkryte_surowe = klucze
        self._odkryte_pam = None
        self._wersja_odkrytych += 1
        self._warstwy_klucz = None
        self.update()

    def _odkryte_na_mapie(self):
        """Nazwy TEJ mapy ze śladem obecności — bez bazy."""
        if self._odkryte_pam is None:
            self._odkryte_pam = frozenset(
                n for n in self._nazwy()
                if n != self._baza and self._klucz_nazwy(n) in self._odkryte_surowe)
        return self._odkryte_pam

    def odkryte_w_zasiegu(self):
        """(odkryte, w zasięgu): miejscowości mapy ze śladem obecności i
        wszystkie miejscowości mapy — obie liczby bez bazy."""
        zasieg = [n for n in self._nazwy() if n != self._baza]
        return len(self._odkryte_na_mapie()), len(zasieg)

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
        self._geo_odniesienie = (lat0, lng0, cx, cy, skala)
        return {n: ((x - cx) * skala, (y - cy) * skala) for n, (x, y) in km.items()}

    def swiat_z_geo(self, lat, lng):
        """Szerokość i długość → punkt świata TEJ mapy, tym samym przelicznikiem,
        którym poszły miasta z ``ustaw_miasta``. Bez prawdziwych miast (układ
        z proto_dane) nie ma czego przeliczać — zwraca None."""
        if self._geo_odniesienie is None:
            return None
        lat0, lng0, cx, cy, skala = self._geo_odniesienie
        x_km = (float(lng) - lng0) * 111.32 * math.cos(math.radians((float(lat) + lat0) * 0.5))
        y_km = (float(lat) - lat0) * 110.57
        return ((x_km - cx) * skala, (y_km - cy) * skala)

    def ziarno(self):
        """Ziarno krajobrazu — z niego stoi teren, rzeka i zabudowa."""
        return self._ziarno

    def _przebuduj_swiat(self):
        """Wszystko, co zależy od układu miast i od ziarna dnia.

        Sieć dróg idzie PRZED miarami krajobrazu, bo od niej zależy kadr:
        rozpiętość kadru liczy się z przebiegu trasy po drogach, a miary
        terenu są ułamkami tej rozpiętości. Same drogi o miarach nic nie
        wiedzą, więc kolejność da się odwrócić bez straty.
        """
        self._wersja_swiata = getattr(self, "_wersja_swiata", 0) + 1
        self._sciezka_klucz = None
        self._obszar_klucz = None
        self._probki_klucz = None
        self._siec = self._zbuduj_siec()
        self._drogi = self._ksztalty_drog()
        self._sasiedzi = self._zbuduj_graf()
        self._przelicz_miary()
        self._kopuly, self._siatka_kopul = self._zbuduj_wzniesienia()
        self._rzeka = self._zbuduj_rzeke()
        self._ziarno_terenu = self._ziarno
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

    def ustaw_kotwice_kartki(self, punkt, pole=None):
        """Kartka delegacji widziana przez mapę: punkt nitki i jej prostokąt.

        ``punkt`` to miejsce we współrzędnych mapy, do którego biegnie nitka.
        ``pole`` to PRAWDZIWY prostokąt kartki — okno zna jej geometrię co do
        piksela i podaje ją wprost. Bez niego mapa musi zgadywać wysokość
        kartki z własnej wysokości, a wtedy rezerwuje pas, który naprawdę jest
        wolną mapą, i spycha tabliczki tam, gdzie leży pigułka dnia.
        """
        self._kotwica = QPointF(punkt) if punkt is not None else None
        self._pole_kar = QRectF(pole) if pole is not None else None
        self._geo_klucz = None
        self.update()

    def ustaw_zaslony(self, pola):
        """Inne widżety leżące NA mapie: pigułka dnia i przełącznik zakresu.

        Mapa sama ich nie rysuje i nic by o nich nie wiedziała, a jednak
        zasłaniają obraz. Kadr im ustępuje, a tabliczki miast omijają je tak
        samo jak kartkę.
        """
        nowe = tuple(QRectF(p) for p in (pola or ()) if p is not None
                     and p.width() > 1.0 and p.height() > 1.0)
        stare = tuple((round(p.x(), 1), round(p.y(), 1),
                       round(p.width(), 1), round(p.height(), 1))
                      for p in self._zaslony)
        if stare == tuple((round(p.x(), 1), round(p.y(), 1),
                           round(p.width(), 1), round(p.height(), 1)) for p in nowe):
            return
        self._zaslony = nowe
        self._geo_klucz = None
        self.update()

    def ustaw_obecnosc_kartki(self, ile):
        """Ile kartki widać (0..1) — za tym idzie jej cień i nitka do trasy.

        Kadr tego NIE słucha: prostokąt kartki jest zarezerwowany także wtedy,
        gdy kartka ustąpiła, bo inaczej trasa przeskakiwałaby w bok za każdym
        razem, gdy papier wychodzi i wraca.
        """
        ile = max(0.0, min(1.0, float(ile)))
        if abs(ile - self._obecnosc_kar) < 0.004:
            return
        self._obecnosc_kar = ile
        self.update()

    # — rysowanie trasy na oczach —
    def _zacznij_odslone(self):
        """Trasa ma narysować się od nowa: od bazy, przez przystanki, do domu."""
        klucz = self._klucz_trasy()
        self._warstwy_klucz = None
        self._odslona.zatrzymaj()
        if not self._czynny() or not self._anim:
            self._odslona.ustaw(1.0)
            self._odslonieta = klucz
            if self._czynny():
                self.trasa_gotowa.emit()
            return
        if not self.isVisible():
            # okno jeszcze się nie pokazało: trasa narysuje się przy pokazaniu,
            # a nie w niewidocznym widżecie, gdzie nikt by tego nie zobaczył
            self._odslona.ustaw(1.0)
            self._odslonieta = None
            return
        self._odslonieta = None
        self._odslona.ustaw(0.0)
        self._odslona.do(1.0, czas=CZAS_ODSLONY_MS)
        self.trasa_rysuje_sie.emit()

    def _koniec_odslony(self):
        """Trasa dobiegła do bazy — wchodzi do gotowej warstwy, kartka wraca."""
        self._odslonieta = self._klucz_trasy()
        self._warstwy_klucz = None
        self.update()
        self.trasa_gotowa.emit()

    def postep_rysowania(self):
        """Jaka część trasy jest narysowana: 1.0 to trasa gotowa."""
        return max(0.0, min(1.0, self._odslona.teraz()))

    def rysuje_trase(self):
        """Czy trasa właśnie się rysuje — okno czeka z kartką."""
        return self._czynny() and self.postep_rysowania() < 0.999

    def ustaw_postep_rysowania(self, ile):
        """Zatrzymuje rysowanie trasy na zadanym ułamku — do zrzutów i sprawdzeń."""
        ile = max(0.0, min(1.0, float(ile)))
        self._odslona.zatrzymaj()
        self._odslona.ustaw(ile)
        self._odslonieta = self._klucz_trasy() if ile >= 0.999 else None
        self._warstwy_klucz = None
        self.update()

    def rysuj_trase_od_nowa(self):
        """Trasa dnia rysuje się jeszcze raz od bazy — po lądowaniu przelotu."""
        self._zacznij_odslone()
        self.update()

    def wypiek_przelotu(self, zapas_px):
        """Scena bez trasy na filmie szerszym o ``zapas_px`` z każdej strony.

        Ta sama kamera co w ``rzut()``, więc środek filmu to dokładnie obraz
        widżetu; po bokach dalszy ciąg rejonu. Zwraca (pixmapa, rzut filmu).
        Liczone raz na przelot — to jedyna droga rzecz w całym przelocie."""
        zapas_px = max(0, int(zapas_px))
        rzut = self.rzut().poszerzony(zapas_px)
        szer = self.width() + 2 * zapas_px
        film = QRectF(0, 0, szer, self.height())
        srodek = QRectF(zapas_px, 0, self.width(), self.height())
        pola = self._zbuduj_pola(rzut, film)
        dpr = self.devicePixelRatioF()
        pix = QPixmap(max(1, int(szer * dpr)), max(1, int(self.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        q = QPainter(pix)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        st.tlo_sceny(q, film)
        self._rysuj_grunt(q, rzut, film)
        self._rysuj_pola(q, pola)
        self._rysuj_rzeke(q, rzut)
        self._rysuj_drogi(q, rzut, self._drogi.values())
        self._rysuj_cienie_miejscowosci(q, rzut)
        self._rysuj_miejscowosci(q, rzut)
        self._rysuj_mgle(q, rzut, srodek, pole=film)
        q.end()
        return pix, rzut

    def ustaw_stan(self, nazwa):
        self._stan = nazwa if nazwa in ("zwykly", "sukces") else "zwykly"
        self._geo_klucz = None
        self.update()

    def ustaw_animacje(self, wlaczone):
        """Włącza albo gasi blask trasy. Wyłączony ustawia stałą fazę."""
        self._anim = bool(wlaczone)
        if not self._anim:
            self._faza = self.FAZA_ZRZUTU
            self._czas_zycia = 0.0          # życie mapy gaśnie w całości
            self._koszt_klatki = 0.0
            self._ciche = False
            self._pod_rzad = 0
            if self._odslona.teraz() < 1.0:      # zrzut ma mieć trasę narysowaną
                self._warstwy_klucz = None
            self._odslona.zatrzymaj()
            self._odslona.ustaw(1.0)
            self._odslonieta = self._klucz_trasy()
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
        # jeden zegar na całe życie mapy; każdy ruch bierze z niego swój okres
        self._czas_zycia = (self._czas_zycia + self.KLATKA) % 9360000.0
        self.update()

    def showEvent(self, zdarzenie):
        super().showEvent(zdarzenie)
        # trasa dnia dostała dzień jeszcze przed pokazaniem okna — rysuje się
        # dopiero teraz, kiedy jest to komu pokazać
        if self._anim and self._odslonieta != self._klucz_trasy():
            self._zacznij_odslone()
        self._rozsadz_zegar()

    def hideEvent(self, zdarzenie):
        self._zegar.stop()
        self._odslona.zatrzymaj()
        super().hideEvent(zdarzenie)

    def closeEvent(self, zdarzenie):
        self._zegar.stop()
        self._odslona.zatrzymaj()
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
        self._probki_klucz = None      # trasa unosi się nad INNYM już terenem
        self._pola = None
        self._statyk_klucz = None
        self._warstwy_klucz = None
        self._geo_klucz = None
        self._znaki = None

    # — kamera —
    def _strefy_zajete(self):
        """Prostokąty, w których na mapie leży już coś innego niż mapa.

        Kartka delegacji, pigułka dnia i przełącznik zakresu są osobnymi
        widżetami położonymi NA mapie. Mapa nie ma jak ich zobaczyć, więc okno
        podaje je wprost — inaczej trasa rysuje się pod papierem, a tabliczki
        miast wchodzą pod pigułkę.
        """
        strefy = []
        kar = self._pole_kartki()
        if kar is not None:
            strefy.append(kar)
        strefy.extend(self._zaslony)
        return tuple(strefy)

    def _uklad_gotowy(self, strefa):
        """Czy ta zasłona wygląda na ustawioną, a nie na domyślną geometrię.

        Widżet, którego okno jeszcze nie rozstawiło, siedzi w lewym górnym
        rogu i bywa większy od mapy. Rezerwowanie miejsca dla takiego
        prostokąta wciskało trasę w pasek przy krawędzi na pierwszych
        klatkach po otwarciu programu.
        """
        luz = 4.0
        return (strefa.left() >= -luz and strefa.top() >= -luz
                and strefa.right() <= self.width() + luz
                and strefa.bottom() <= self.height() + luz)

    def _ciecia_kadru(self):
        """Z której strony i dokąd kadr ustępuje każdej zasłonie.

        Zasłonę odcinamy od tej strony, z której kosztuje najmniej miejsca:
        kartka stoi przy prawej krawędzi, więc oddaje się prawą kolumnę,
        a pigułka leży u góry, więc oddaje się pasek nad trasą. Cięcie, po
        którym zostałby skrawek węższy niż UDZIAL_MIN_KADRU widżetu, jest
        pomijane — tak wygląda układ jeszcze nieustawiony.
        """
        strefy = self._strefy_zajete()
        if not strefy:
            return ()
        r = QRectF(self.rect())
        lewy = r.x() + r.width() * MARGINES_KADRU
        gora = r.y() + r.height() * MARGINES_KADRU
        prawy = r.right() - r.width() * MARGINES_KADRU
        dol = r.bottom() - r.height() * MARGINES_KADRU
        odstep_x = r.width() * ODSTEP_OD_KARTKI
        odstep_y = r.height() * ODSTEP_OD_KARTKI
        min_x = r.width() * UDZIAL_MIN_KADRU
        min_y = r.height() * UDZIAL_MIN_KADRU
        ciecia = []
        # od największej zasłony do najmniejszej; przy równej — po położeniu,
        # żeby ten sam układ zawsze dawał to samo cięcie
        for strefa in sorted(strefy, key=lambda z: (-z.width() * z.height(),
                                                    round(z.x(), 2), round(z.y(), 2))):
            if not self._uklad_gotowy(strefa):
                continue                       # widżet jeszcze nierozstawiony
            if strefa.right() <= lewy or strefa.left() >= prawy \
                    or strefa.bottom() <= gora or strefa.top() >= dol:
                continue                       # zasłona i tak leży poza kadrem
            kandydaci = (
                ("prawo", strefa.left() - odstep_x, prawy - strefa.left()),
                ("gora", strefa.bottom() + odstep_y, strefa.bottom() - gora),
                ("lewo", strefa.right() + odstep_x, strefa.right() - lewy),
                ("dol", strefa.top() - odstep_y, dol - strefa.top()))
            for bok, wartosc, _koszt in sorted(kandydaci, key=lambda z: (z[2], z[0])):
                if bok == "prawo" and wartosc - lewy >= min_x:
                    prawy = wartosc
                elif bok == "lewo" and prawy - wartosc >= min_x:
                    lewy = wartosc
                elif bok == "gora" and dol - wartosc >= min_y:
                    gora = wartosc
                elif bok == "dol" and wartosc - gora >= min_y:
                    dol = wartosc
                else:
                    continue
                ciecia.append((bok, wartosc))
                break
        return tuple(ciecia)

    @staticmethod
    def _zastosuj_ciecia(r, ciecia, min_szer=120.0, min_wys=100.0):
        """Prostokąt po oddaniu zasłonom tego, co im się należy."""
        lewy, gora, prawy, dol = r.left(), r.top(), r.right(), r.bottom()
        for bok, wartosc in ciecia:
            if bok == "prawo":
                prawy = min(prawy, wartosc)
            elif bok == "lewo":
                lewy = max(lewy, wartosc)
            elif bok == "gora":
                gora = max(gora, wartosc)
            else:
                dol = min(dol, wartosc)
        return QRectF(lewy, gora, max(min_szer, prawy - lewy),
                      max(min_wys, dol - gora))

    def _pole(self):
        """Prostokąt ekranu, w który ma trafić kadr — widżet bez zasłon.

        Kartka delegacji leży NA mapie i zasłania jej prawą stronę, więc trasa
        wyśrodkowana w całym widżecie chowałaby się pod papierem, a tabliczki
        uciekałyby za lewą krawędź. Kadr idzie w to, co po zasłonach zostaje.
        Bez kartki i pasków (sama mapa, podgląd, zrzuty) wolny jest cały widżet.
        """
        r = QRectF(self.rect())
        kadr = QRectF(r.x() + r.width() * MARGINES_KADRU,
                      r.y() + r.height() * MARGINES_KADRU,
                      r.width() * (1.0 - 2.0 * MARGINES_KADRU),
                      r.height() * (1.0 - 2.0 * MARGINES_KADRU))
        return self._zastosuj_ciecia(kadr, self._ciecia_kadru())

    def _pole_blasku(self):
        """Dokąd wolno sięgnąć świecącej poświacie trasy.

        Przy krawędziach widżetu poświatę wolno przyciąć — tak było zawsze
        i tak wygląda naturalnie. Czego nie wolno, to wpuścić ją na kartkę
        albo na pasek leżący na mapie, bo wtedy świecąca linia wygląda,
        jakby ktoś przeciął ją krawędzią papieru.
        """
        d = max(2000.0, self.width() + self.height())
        r = QRectF(-d, -d, self.width() + 2.0 * d, self.height() + 2.0 * d)
        return self._zastosuj_ciecia(r, self._ciecia_kadru())

    def _sciezka_swiata(self):
        """Trasa dnia poprowadzona po drogach — w świecie, bez kamery.

        To jest TO, CO SIĘ NAPRAWDĘ RYSUJE: objazd przez miasta spoza trasy
        i wygięcie każdej drogi. Kadr liczy się z tego przebiegu, a nie z
        samych przystanków — inaczej narysowana linia wychodzi poza kadr,
        który kamera obiecała, i wsuwa się pod kartkę.
        """
        trasa = self._klucz_trasy()
        klucz = (trasa, self._wersja_swiata)
        if self._sciezka_klucz == klucz and self._sciezka_pam is not None:
            return self._sciezka_pam
        odcinki, dodatkowe = [], []
        if len(trasa) >= 2 and getattr(self, "_drogi", None) is not None:
            for i in range(len(trasa) - 1):
                weze = self._po_drogach(trasa[i], trasa[i + 1])
                punkty = []
                for j in range(len(weze) - 1):
                    kawalek = self._droga_miedzy(weze[j], weze[j + 1])
                    if kawalek is None:               # brak drogi: kładziemy nową
                        kawalek = _gladko_2d([self._polozenie(weze[j]),
                                              self._polozenie(weze[j + 1])],
                                             na_odcinek=4)
                        dodatkowe.append(kawalek)
                    punkty.extend(kawalek if not punkty else kawalek[1:])
                odcinki.append(punkty or [self._polozenie(trasa[i]),
                                          self._polozenie(trasa[i + 1])])
        glowna = []
        for punkty in odcinki[:-1]:
            glowna.extend(punkty if not glowna else punkty[1:])
        self._sciezka_pam = {"odcinki": odcinki, "dodatkowe": dodatkowe,
                             "glowna": glowna,
                             "powrot": odcinki[-1] if odcinki else []}
        self._sciezka_klucz = klucz
        return self._sciezka_pam

    def _punkty_kadru(self):
        """Punkty świata, które kadr ma objąć: cała RYSOWANA trasa dnia i baza.

        Dzień bez trasy — i mapa, której dnia jeszcze nie podano — oddaje kadr
        całemu układowi miast, dokładnie jak dotąd.
        """
        punkty = [p for odcinek in self._sciezka_swiata()["odcinki"] for p in odcinek]
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
        klucz = (self._klucz_trasy(), self._wersja_swiata)
        if self._obszar_klucz == klucz and self._obszar_pam is not None:
            return self._obszar_pam
        punkty = self._punkty_kadru()
        xs = [x for (x, _) in punkty] or [0.0]
        ys = [y for (_, y) in punkty] or [0.0]
        prog = NAJMNIEJSZY_KADR_KM * self._jedn_na_km
        luz = 1.0 + 2.0 * MARGINES_TRASY
        sx = max(prog, max(xs) - min(xs)) * luz
        sy = max(prog, max(ys) - min(ys)) * luz
        cx = (max(xs) + min(xs)) * 0.5
        cy = (max(ys) + min(ys)) * 0.5
        self._obszar_pam = (cx - sx * 0.5, cy - sy * 0.5, sx, sy)
        self._obszar_klucz = klucz
        return self._obszar_pam

    def _klucz_kadru(self):
        """Wszystko, co przestawia kamerę i układ tabliczek.

        Zasłony idą tu w całości, a nie tylko przez swoje cięcia: kadr zależy
        od samego cięcia, ale tabliczki omijają CAŁE prostokąty, więc szersza
        pigułka dnia musi unieważnić i gotowe warstwy, nie tylko kamerę.
        """
        ox, oy, sx, sy = self._obszar_swiata()
        return (self.width(), self.height(), round(ox, 3), round(oy, 3),
                round(sx, 3), round(sy, 3),
                tuple((round(z.x(), 1), round(z.y(), 1),
                       round(z.width(), 1), round(z.height(), 1))
                      for z in self._strefy_zajete()))

    def _probki_kadru(self):
        """Rysowana trasa razem z wysokością terenu — po niej wpasowujemy kamerę.

        Sama wysokość liczy się raz na dzień i teren: kamera dobiera się w kilku
        podejściach, a przeglądanie wzniesień jest najdroższą częścią tej pracy.
        """
        sciezka = self._sciezka_swiata()        # najpierw trasa, potem jej klucz
        klucz = (self._sciezka_klucz, self._ziarno_terenu,
                 round(self._wznios_trasy, 4))
        if self._probki_klucz == klucz and self._probki_pam is not None:
            return self._probki_pam
        punkty = [p for odcinek in sciezka["odcinki"] for p in odcinek]
        wznios = self._wznios_trasy
        self._probki_pam = tuple((x, y, self._wysokosc(x, y) + wznios)
                                 for (x, y) in punkty)
        self._probki_klucz = klucz
        return self._probki_pam

    @staticmethod
    def _zmiesci(d, dolny, gorny):
        """Największe f ≤ 1, przy którym f·d mieści się między dolny a gorny."""
        if gorny < dolny:              # nie ma jak zmieścić — nie cofamy bez końca
            return 1.0
        if d > 1e-9 and d > gorny:
            return max(0.0, gorny / d)
        if d < -1e-9 and d < dolny:
            return max(0.0, dolny / d)
        return 1.0

    def _zapas_kadru(self, rzut, pole, blask, odn):
        """O ile trzeba cofnąć kamerę, żeby zmieściło się to, co się RYSUJE.

        Kamera wpasowuje w kadr gołą rozpiętość trasy, a na ekranie ląduje
        linia o grubości i świecąca głowa o promieniu kilkudziesięciu pikseli.
        Do tego trasa unosi się nad terenem, więc w perspektywie odsuwa się od
        środka obrazu. Sprawdzamy więc prawdziwe punkty ekranu i zwracamy
        współczynnik, przez który trzeba pomnożyć odległości od środka kadru.
        """
        cx, cy = pole.center().x(), pole.center().y()
        naj = 1.0
        for (x, y, z) in self._probki_kadru():
            pkt = rzut.ekran(x, y, z)
            s = rzut.skala(x, y, z) * odn
            dx, dy = pkt.x() - cx, pkt.y() - cy
            for prostokat, prom in ((pole, PROMIEN_LINII * s),
                                    (blask, PROMIEN_BLASKU * s)):
                naj = min(naj, self._zmiesci(dx, prostokat.left() + prom - cx,
                                             prostokat.right() - prom - cx))
                naj = min(naj, self._zmiesci(dy, prostokat.top() + prom - cy,
                                             prostokat.bottom() - prom - cy))
            if naj <= 0.42:
                return 0.42
        return naj

    def _dopasuj_kamere(self):
        """Kamera, przy której cała rysowana trasa mieści się obok kartki."""
        pole = self._pole()
        obszar = self._obszar_swiata()
        rzut = Rzut(pole, obszar)
        if not self._czynny() or not self._probki_kadru():
            return rzut
        blask = self._pole_blasku()
        odn = self._miara / POLE_SWIATA_X
        ox, oy, sx, sy = obszar
        cx, cy = ox + sx * 0.5, oy + sy * 0.5
        for _ in range(4):
            f = self._zapas_kadru(rzut, pole, blask, odn)
            if f >= 0.995:
                break
            f = max(0.42, f)
            # dalej niż trzy razy kamera się nie cofa: gdyby kadr był tak ciasny,
            # że trasa i tak się nie mieści, lepiej ją przyciąć niż pokazać dzień
            # jako punkt w środku pustego krajobrazu
            if max(sx / f, sy / f) > 3.0 * max(obszar[2], obszar[3]):
                break
            sx, sy = sx / f, sy / f
            rzut = Rzut(pole, (cx - sx * 0.5, cy - sy * 0.5, sx, sy))
        return rzut

    def rzut(self):
        """Kamera dla obecnego kadru — liczona raz i pamiętana."""
        klucz = self._klucz_kadru()
        if self._rzut is not None and self._rzut_klucz == klucz:
            return self._rzut
        self._rzut = self._dopasuj_kamere()
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

    def _zbuduj_pola(self, rzut, r=None):
        """Działki otwartego terenu gotowe do namalowania, od dali do widza.

        Siatka działek jest nieregularna — wierzchołki przesuwa hasz wspólny
        dla czterech sąsiadów, więc między polami nie ma szczelin. Odcień
        bierze się z nachylenia działki względem światła i z mgły odległości,
        dzięki czemu garb terenu widać bez rysowania warstwic. ``r`` to
        prostokąt filmu — domyślnie widżet, przy wypieku przelotu szerszy.
        """
        z = self._ziarno
        kom = self._komorka_pola
        r = QRectF(self.rect()) if r is None else QRectF(r)
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

    def _rysuj_pola(self, p, pola=None):
        """Działki od najdalszej do najbliższej — bliższa zasłania dalszą.

        Każda dostaje cieńszą, ciemniejszą obwódkę: to i miedza między polami,
        i zasłonięcie szwu, który antyaliasing zostawiłby między działkami.
        """
        for wiel, barwa, miedza in (self._pola if pola is None else pola):
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

    def _rysuj_mgle(self, p, rzut, r, pole=None):
        """Mgła odległości: w głębi sceny mniejszy kontrast i jaśniejsze tło.

        ``r`` ustawia gradienty (widżet), ``pole`` mówi, co zamalować —
        na szerszym filmie przelotu to cały film."""
        pole = r if pole is None else pole
        # gdzie na ekranie leży horyzont — od niego idzie cała skala mgły
        ox, oy, osx, osy = self._obszar_swiata()
        y_gora = rzut.ekran(0.0, oy + osy * 0.5 + self._zasieg_terenu, 0.0).y()
        y_dol = rzut.ekran(0.0, oy - osy * 0.30, 0.0).y()
        g = QLinearGradient(QPointF(r.x(), y_gora), QPointF(r.x(), y_dol))
        g.setColorAt(0.0, st.z_alfa(BARWA_MGLY, 46))
        g.setColorAt(0.30, st.z_alfa(BARWA_MGLY, 20))
        g.setColorAt(0.72, st.z_alfa(BARWA_MGLY, 5))
        g.setColorAt(1.0, st.z_alfa(BARWA_MGLY, 0))
        p.fillRect(pole, QBrush(g))
        # światło wpadające z tej strony, z której pada na teren
        lx, ly = rzut.swiatlo_ekran
        rg = QRadialGradient(QPointF(r.center().x() + lx * r.width() * 0.55,
                                     r.center().y() + ly * r.height() * 0.75),
                             max(r.width(), r.height()) * 0.95)
        rg.setColorAt(0.0, st.z_alfa(BARWA_MGLY, 13))
        rg.setColorAt(1.0, st.z_alfa(BARWA_MGLY, 0))
        p.fillRect(pole, QBrush(rg))

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
        zegar = time.perf_counter()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        r = QRectF(self.rect())
        if not self._zegar_terenu.isActive():
            self._dopilnuj_terenu()                    # cała scena z jednego ziarna
        geo = self._geometria() if self._czynny() else None
        odslona = self.postep_rysowania() if geo is not None else 1.0
        gotowa = odslona >= 0.999
        dol, gora = self._warstwy(geo, gotowa)

        zycie = self._anim and not self._ciche
        p.drawPixmap(0, 0, dol)                        # a) scena 3D bez trasy
        if zycie:
            self._rysuj_polysk_rzeki(p)                # a1) rzeka odbija światło
            self._rysuj_swiatla_drog(p)                # a2) ruch na drogach rejonu
        if self._trasa_pix is not None and gotowa:
            p.drawPixmap(0, 0, self._trasa_pix)        # a3) trasa nad życiem
        if geo is not None:
            if gotowa:
                self._rysuj_powrot(p, geo)             # b) kreskowany powrót
                self._rysuj_blask(p, geo)              # c) płynący blask
            else:
                self._rysuj_odslone(p, geo, odslona)   # b–c) trasa rysująca się
        p.drawPixmap(0, 0, gora)                       # d) słupy i tabliczki
        if geo is not None:
            if not gotowa:                             # ...te, do których już doszła
                self._rysuj_slupy(p, self.rzut(), geo, odslona)
                self._rysuj_podpisy(p, geo, odslona)
            if zycie and gotowa:
                self._rysuj_zapal_przystankow(p, geo)  # d1) blask zapala przystanki
            self._rysuj_puls_bazy(p)                   # e) oddech bazy
            if gotowa:
                self._rysuj_nitke(p, geo)              # f) nitka do kartki
        self._poloz_cien_kartki(p)                     # g) kartka kładzie cień
        p.drawPixmap(0, 0, self._wykonczenie())        # h) winieta i ziarno
        p.end()
        self.odnotuj_klatke((time.perf_counter() - zegar) * 1000.0)

    # — efekty ściszają się same, kiedy klatka przestaje się mieścić —
    def odnotuj_klatke(self, ms):
        """Koszt ostatniej klatki; po kilku takich samych zapada decyzja."""
        self._koszt_klatki = (self._koszt_klatki * 0.8 + float(ms) * 0.2
                              if self._koszt_klatki else float(ms))
        chce_cisze = (self._koszt_klatki > SUFIT_KLATKI_MS if not self._ciche
                      else self._koszt_klatki > PROG_POWROTU_MS)
        if chce_cisze == self._ciche:
            self._pod_rzad = 0
            return
        self._pod_rzad += 1
        if self._pod_rzad >= KLATEK_DO_DECYZJI:
            self._ciche = chce_cisze
            self._pod_rzad = 0

    def efekty_ciche(self):
        """True, kiedy mapa sama ściszyła życie, bo klatka się nie mieściła."""
        return self._ciche

    def koszt_klatki(self):
        """Średni koszt klatki w milisekundach — po nim idzie ściszanie."""
        return self._koszt_klatki

    # — warstwy trzymane w pixmapach —
    def _nowa_pixmapa(self):
        dpr = self.devicePixelRatioF()
        pix = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        return pix

    def _warstwy(self, geo, gotowa=True):
        """Dwie pixmapy: pod blaskiem i nad nim. Liczone raz na układ.

        W trakcie rysowania trasy obie warstwy zostają BEZ TRASY: linia, słupy
        i tabliczki dokładają się co klatkę, bo co klatkę jest ich więcej.
        Kiedy trasa dobiegnie do bazy, warstwy przeliczają się raz i reszta
        ruchu (blask, oddech bazy) idzie po gotowym obrazie, jak dotąd.
        """
        rzut = self.rzut()
        klucz = (self._klucz_kadru(), round(self.devicePixelRatioF(), 3),
                 self._geo_klucz, self._stan, bool(gotowa), self._wersja_odkrytych)
        if self._warstwy_klucz == klucz and self._dol is not None:
            return self._dol, self._gora
        # trasa wchodzi do warstw dopiero, gdy skończy się rysować
        w_warstwie = geo if gotowa else None

        cel = QRectF(self.rect())
        dol = self._nowa_pixmapa()
        q = QPainter(dol)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        grunt = self._pixmapa_gruntu()
        q.drawPixmap(cel, grunt, QRectF(grunt.rect()))
        if geo is not None:
            self._rysuj_drogi(q, rzut, geo["dodatkowe"])   # dojazdy spoza sieci
        if w_warstwie is not None:
            self._rysuj_cien_trasy(q, w_warstwie)          # cień trasy leży na gruncie
        bryly = self._pixmapa_bryl()                       # ...więc bryły idą po nim
        q.drawPixmap(cel, bryly, QRectF(bryly.rect()))
        self._rysuj_mgle_rejonu(q, rzut, geo)              # białe plamy: mgła POD trasą
        q.end()

        # Trasa idzie do OSOBNEJ pixmapy, bo między terenem a trasą żyje
        # rejon: połysk na rzece i światła na drogach leżą NA ZIEMI, więc
        # trasa ma je przykrywać, a nie odwrotnie.
        trasa = None
        if w_warstwie is not None:
            trasa = self._nowa_pixmapa()
            q = QPainter(trasa)
            q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self._rysuj_trase(q, w_warstwie)
            q.end()
        self._trasa_pix = trasa

        gora = self._nowa_pixmapa()
        q = QPainter(gora)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        # podziałka i licznik odkryć leżą NAD mgłą rejonu — mierzą i liczą,
        # więc nie wolno ich przyćmić
        self._rysuj_podzialke(q, rzut, cel)
        self._rysuj_licznik_odkryc(q, cel)
        if gotowa:
            self._rysuj_slupy(q, rzut, w_warstwie)
            if w_warstwie is not None:
                self._rysuj_podpisy(q, w_warstwie)
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
        q.end()

        self._statyk = (grunt, bryly)
        self._statyk_klucz = klucz
        return self._statyk

    def _pixmapa_gruntu(self):
        return self._statyka()[0]

    def _pixmapa_bryl(self):
        return self._statyka()[1]

    # — białe plamy: mgła rejonu z wycięciami —
    def _wyciecia_mgly(self, rzut, geo):
        """[(środek ekranu, promień, odkryta)] — gdzie mgła ma dziurę.

        Baza i przystanki dnia zawsze (trasa ma być czytelna), miejscowości ze
        śladem obecności — jako odkryte, czyli z poświatą. Promień wycięcia
        idzie za znakiem miejscowości na ekranie, z podłogą i sufitem w
        pikselach, więc wieś w głębi nie ginie, a baza nie zdejmuje mgły
        z pół rejonu.
        """
        znaki = self._znaki_miejscowosci(rzut)
        odkryte = self._odkryte_na_mapie()
        trasa = set(geo["trasa"]) if geo is not None else set()
        trasa.add(self._baza)
        wysokosc = self._wysokosc
        dol, gora = PROMIEN_ODKRYCIA_PX
        wynik = []
        for m in self._miejscowosci:
            nazwa = m["nazwa"]
            odkryta = nazwa in odkryte
            if not odkryta and nazwa not in trasa:
                continue
            gleb = rzut.glebokosc(m["x"], m["y"], 0.0)
            if gleb < 10.0:
                continue
            srodek = rzut.ekran(m["x"], m["y"], wysokosc(m["x"], m["y"]))
            prom_px = m["promien"] * znaki.get(nazwa, 1.0) * rzut.k / gleb
            promien = max(dol, min(gora, prom_px * PROMIEN_ODKRYCIA))
            wynik.append((srodek, promien, odkryta and nazwa not in trasa))
        return wynik

    def _rysuj_mgle_rejonu(self, q, rzut, geo):
        """Delikatna mgła nad nieodkrytym rejonem — w gotowej warstwie pod trasą."""
        niska = self._mgla_niska(rzut, geo)
        q.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        q.drawPixmap(QRectF(self.rect()), niska, QRectF(niska.rect()))

    def _pixmapa_mgly(self, rzut, geo, poswiata=True):
        """Mgła w rozdzielczości widżetu — do pomiarów i sprawdzeń; sama mapa
        kładzie na warstwę wprost pixmapę z :meth:`_mgla_niska`."""
        niska = self._mgla_niska(rzut, geo, poswiata)
        pix = self._nowa_pixmapa()
        q = QPainter(pix)
        q.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        q.drawPixmap(QRectF(self.rect()), niska, QRectF(niska.rect()))
        q.end()
        return pix

    def _mgla_niska(self, rzut, geo, poswiata=True):
        """Zasłona w jednej pixmapie (w skali SKALA_MGLY): najpierw równy welon
        (gęstszy przy widzu), potem wycięcia miękkim gradientem
        (DestinationOut) przy każdej odsłoniętej miejscowości i korytarz
        wzdłuż trasy dnia, na koniec poświata odkrytych miejscowości
        (``poswiata=False`` zostawia samą zasłonę — do pomiarów). Współrzędne
        podaje się jak na widżecie — skalę bierze na siebie malarz. Rysowane
        raz na układ; klatka animacji tego nie dotyka.
        """
        r = QRectF(self.rect())
        mgla = QPixmap(max(1, int(round(self.width() * SKALA_MGLY))),
                       max(1, int(round(self.height() * SKALA_MGLY))))
        mgla.fill(Qt.GlobalColor.transparent)
        m = QPainter(mgla)
        m.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        m.scale(mgla.width() / max(1.0, r.width()), mgla.height() / max(1.0, r.height()))
        a_dal, a_blisko = ALFA_MGLY_REJONU
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.0, st.z_alfa(BARWA_MGLY_REJONU, a_dal))
        g.setColorAt(0.45, st.z_alfa(BARWA_MGLY_REJONU, (a_dal + a_blisko) // 2))
        g.setColorAt(1.0, st.z_alfa(BARWA_MGLY_REJONU, a_blisko))
        m.fillRect(r, QBrush(g))

        wyciecia = self._wyciecia_mgly(rzut, geo)
        m.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        m.setPen(Qt.PenStyle.NoPen)
        for srodek, promien, _odkryta in wyciecia:
            rg = QRadialGradient(srodek, promien)
            rg.setColorAt(0.0, QColor(0, 0, 0, 255))
            rg.setColorAt(0.5, QColor(0, 0, 0, 236))
            rg.setColorAt(1.0, QColor(0, 0, 0, 0))
            m.setBrush(QBrush(rg))
            m.drawEllipse(srodek, promien, promien)
        if geo is not None:
            # korytarz trasy: droga dnia i jej najbliższe otoczenie bez mgły.
            # Bez wygładzania — przy połowie rozdzielczości i rozciągnięciu
            # brzeg i tak się rozmywa, a szeroki wygładzany pędzel kosztował
            # tyle, co cała reszta mgły razem wzięta.
            k = self._grubosc()
            m.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            m.setBrush(Qt.BrushStyle.NoBrush)
            for szer, alfa in ((28.0 * k, 96), (12.0 * k, 255)):
                pioro = QPen(QColor(0, 0, 0, alfa), max(1.0, szer))
                pioro.setCapStyle(Qt.PenCapStyle.RoundCap)
                pioro.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                m.setPen(pioro)
                m.drawPath(geo["glowna"])
                m.drawPath(geo["powrot"])
            m.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        m.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if poswiata:
            # pod kartką i pod paskami nic nie świeci — leży tam papier,
            # a światło wychodzące spod niego wyglądałoby jak trasa pod kartką
            strefy = self._strefy_zajete()
            for srodek, promien, odkryta in wyciecia:
                if odkryta and not any(s.contains(srodek) for s in strefy):
                    st.punkt_swiatla(m, srodek, promien * 1.05, BARWA_ODKRYCIA, 74)
                    st.punkt_swiatla(m, srodek, promien * 0.36, BARWA_ODKRYCIA, 120)
        m.end()
        return mgla

    def _rysuj_licznik_odkryc(self, p, r):
        """Dwie liczby w prawym dolnym rogu ramy: odkryte / w zasięgu."""
        odkryte, zasieg = self.odkryte_w_zasiegu()
        if zasieg <= 0:
            return
        napis = "%d / %d" % (odkryte, zasieg)
        x = r.right() - r.width() * 0.045
        y = r.bottom() - r.height() * 0.060
        f = st.czcionka(11.0, 600, mono=True)
        szer = QFontMetricsF(f).horizontalAdvance(napis)
        f2 = st.czcionka(8.6, 500, odstep=0.8)
        szer2 = QFontMetricsF(f2).horizontalAdvance("ODKRYTE")
        _poduszka(p, QRectF(x - max(szer, szer2) - 6, y - 26, max(szer, szer2) + 12, 32),
                  sila=104, warstw=4)
        _napis(p, x, y - 13.0, "ODKRYTE", st.z_alfa(st.TEKST_2, 185), 8.6, 500,
               odstep=0.8, prawy=True)
        _napis(p, x, y, napis, st.z_alfa(st.TEKST, 215), 11.0, 600, mono=True, prawy=True)

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

        # a) trasa dnia poprowadzona po drogach — ten sam przebieg, z którego
        #    policzył się kadr, więc linia nie wyjdzie poza to, co obiecał
        sciezka = self._sciezka_swiata()
        dodatkowe = sciezka["dodatkowe"]
        swiat_glowna = sciezka["glowna"]
        swiat_powrot = sciezka["powrot"]

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

        # d) kiedy rysująca się trasa dochodzi do którego przystanku —
        #    po tym zapalają się słupy i tabliczki, każda w swojej chwili
        dl_gl = _narastajaco(pkt_gl)
        dl_pw = _narastajaco(pkt_pw)
        calosc = max(1e-6, dl_gl[-1] + dl_pw[-1])
        udzial_gl = dl_gl[-1] / calosc
        for s in slupy:
            # baza świeci od pierwszej klatki — to z niej trasa wyrusza
            s["postep"] = -self.ZAPALANIE if s["baza"] else \
                udzial_gl * _udzial_punktu(swiat_glowna, dl_gl,
                                           self._miasta.get(s["nazwa"]))

        nitka = self._sciezka_nitki()
        etykiety = self._ulozenie_podpisow(slupy, probki, pkt_pw, nitka)
        for e, s in zip(etykiety, slupy):
            e["postep"] = s["postep"]
        self._geo = {"glowna": glowna, "powrot": powrot, "probki": probki,
                     "skale": skale_probek, "cien_glowna": cien_gl,
                     "cien_powrot": cien_pw, "ska_cglowna": ska_cgl,
                     "ska_cpowrot": ska_cpw, "pkt_glowna": pkt_gl,
                     "ska_glowna": ska_gl, "pkt_powrot": pkt_pw, "ska_powrot": ska_pw,
                     "slupy": slupy, "nitka": nitka, "etykiety": etykiety,
                     "trasa": trasa, "dodatkowe": dodatkowe,
                     "dl_glowna": dl_gl, "dl_powrot": dl_pw,
                     "udzial_glowna": udzial_gl}
        self._geo_klucz = klucz
        return self._geo

    # — trasa rysująca się na oczach —
    def _kawalek_trasy(self, geo, ile):
        """Co jest narysowane przy postępie ``ile``.

        Podróż jest jedna — z bazy przez przystanki i z powrotem do domu — więc
        postęp idzie po SUMIE długości obu łamanych. Zwraca ile punktów drogi
        tam i w jakim ułamku kolejnego odcinka trasa się urywa, to samo dla
        powrotu, i na której z dwóch łamanych stoi w tej chwili czoło.
        """
        ile = max(0.0, min(1.0, float(ile)))
        udzial = geo["udzial_glowna"]
        if ile >= 0.999:
            return (len(geo["pkt_glowna"]), 0.0, len(geo["pkt_powrot"]), 0.0, False)
        if udzial > 1e-6 and ile <= udzial:
            i, t = _uciecie(geo["dl_glowna"], ile / udzial)
            return (i, t, 0, 0.0, True)
        reszta = 0.0 if udzial >= 1.0 else (ile - udzial) / (1.0 - udzial)
        i, t = _uciecie(geo["dl_powrot"], reszta)
        return (len(geo["pkt_glowna"]), 0.0, i, t, False)

    def _rysuj_odslone(self, p, geo, ile):
        """Trasa w trakcie rysowania: linia dobiega do czoła, a czoło świeci."""
        gl, t_gl, pw, t_pw, na_glownej = self._kawalek_trasy(geo, ile)
        kolor = self._kolor_trasy()
        # urwany koniec każdej łamanej liczy się z tego samego odcinka i ułamka,
        # więc cień na gruncie kończy się pod czołem trasy, a nie przy nim
        ur = _punkt_miedzy(geo["pkt_glowna"], gl, t_gl) if na_glownej else None
        s_ur = _miara_miedzy(geo["ska_glowna"], gl, t_gl) if na_glownej else 0.0
        pkt = _domknij(geo["pkt_glowna"][:gl], ur)
        if len(pkt) >= 2:
            ska = _domknij(geo["ska_glowna"][:gl], s_ur if ur is not None else None)
            cien = _domknij(geo["cien_glowna"][:gl],
                            _punkt_miedzy(geo["cien_glowna"], gl, t_gl)
                            if na_glownej else None)
            ska_c = _domknij(geo["ska_cglowna"][:gl],
                             _miara_miedzy(geo["ska_cglowna"], gl, t_gl)
                             if na_glownej else None)
            _poswiata_zmienna(p, cien, ska_c, QColor(0, 0, 0),
                              ((3.1, 52, 4), (1.7, 66, 2), (0.9, 78, 1)))
            _poswiata_zmienna(p, pkt, ska, kolor,
                              ((7.4, 20, 5), (4.1, 42, 3), (2.1, 118, 2), (1.0, 226, 1)))
            _poswiata_zmienna(p, pkt, ska, QColor(232, 255, 255), ((0.36, 185, 1),))
        wrot = _domknij(geo["pkt_powrot"][:pw],
                        None if na_glownej
                        else _punkt_miedzy(geo["pkt_powrot"], pw, t_pw))
        if len(wrot) >= 2:
            k = self._grubosc()
            ska = geo["ska_powrot"][:max(2, pw)] or [1.0]
            sr = sum(ska) / max(1, len(ska))
            _kreskowana(p, _lamana(wrot), st.ZIELEN,
                        warstwy=((4.2 * sr, 30), (2.0 * sr, 76), (0.80 * sr, 235)),
                        kreska=11.0 * k, przerwa=8.0 * k)
            if not na_glownej:
                s_ur = _miara_miedzy(geo["ska_powrot"], pw, t_pw)
        czolo = ur if na_glownej else (wrot[-1] if len(wrot) >= 2 else None)
        if czolo is not None:
            s = max(0.4, s_ur)
            st.punkt_swiatla(p, czolo, PROMIEN_BLASKU * s, kolor, 96)
            st.punkt_swiatla(p, czolo, 5.0 * s, QColor(238, 255, 255), 140)

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
    ZAPALANIE = 0.07        # jaka część rysowania trasy zajmuje rozbłysk słupa

    def _zapal(self, postep, ile):
        """Ile już świeci coś, co zapala się przy postępie ``postep`` (0 = wcale)."""
        if ile >= 0.999:
            return 1.0
        return max(0.0, min(1.0, (ile - postep) / self.ZAPALANIE))

    def _rysuj_slupy(self, p, rzut, geo, ile=1.0):
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
            zapal = self._zapal(s.get("postep", 0.0), ile)
            if zapal <= 0.0:                 # trasa jeszcze tu nie dojechała
                continue
            barwa = st.ZIELEN if s["baza"] else kolor
            waga = (1.0 if s["baza"] else 0.82) * zapal
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

    # — życie na mapie: rzeka, drogi i zapalanie przystanków —
    def _swiatla_na_drogach(self):
        """Które drogi rejonu mają ruch i w którą stronę. Raz na świat."""
        klucz = (self._ziarno, self._wersja_swiata, len(self._drogi))
        if self._swiatla_klucz == klucz and self._swiatla_pam is not None:
            return self._swiatla_pam
        klucze = sorted(self._drogi)
        wybrane = []
        if klucze:
            for i in range(min(SWIATEL_DROG, len(klucze))):
                j = int(_hasz(self._ziarno, "swiatlo", i) * len(klucze)) % len(klucze)
                punkty = self._drogi[klucze[(j + i * 7) % len(klucze)]]
                dlug = [0.0]
                for k in range(1, len(punkty)):
                    dlug.append(dlug[-1] + math.hypot(punkty[k][0] - punkty[k - 1][0],
                                                      punkty[k][1] - punkty[k - 1][1]))
                if dlug[-1] <= 1e-6:
                    continue
                wybrane.append({"punkty": punkty, "dlugosci": dlug,
                                "faza": _hasz(self._ziarno, "swiatlo_f", i),
                                "wstecz": _hasz(self._ziarno, "swiatlo_k", i) > 0.5,
                                "okres": OKRES_DROGI_MS
                                * (0.78 + 0.55 * _hasz(self._ziarno, "swiatlo_t", i))})
        self._swiatla_pam, self._swiatla_klucz = wybrane, klucz
        return wybrane

    def _rysuj_swiatla_drog(self, p):
        """Pojedyncze światła jadące drogami rejonu — ciepłe, nie cyjanowe.

        Cyjan należy do TRASY DNIA. Ruch na pozostałych drogach jest ciepły
        i przygaszony, więc na pierwszy rzut oka wiadomo, co jest twoje.
        """
        rzut = self.rzut()
        odn = self._odniesienie()
        p.setPen(Qt.PenStyle.NoPen)
        for sw in self._swiatla_na_drogach():
            t = (self._czas_zycia / sw["okres"] + sw["faza"]) % 1.0
            if sw["wstecz"]:
                t = 1.0 - t
            dlug = sw["dlugosci"]
            cel = t * dlug[-1]
            i = 1
            while i < len(dlug) - 1 and dlug[i] < cel:
                i += 1
            odc = max(1e-6, dlug[i] - dlug[i - 1])
            u = max(0.0, min(1.0, (cel - dlug[i - 1]) / odc))
            ax, ay = sw["punkty"][i - 1]
            bx, by = sw["punkty"][i]
            x, y = ax + (bx - ax) * u, ay + (by - ay) * u
            gleb = rzut.glebokosc(x, y, 0.0)
            mgla = rzut.mgla(gleb)
            # gaśnie na obu końcach drogi: światło wjeżdża i wyjeżdża, nie znika
            brzeg = min(1.0, min(t, 1.0 - t) / 0.12)
            moc = brzeg * (1.0 - 0.9 * mgla)
            if moc <= 0.02:
                continue
            srodek, ska = rzut.rzutuj(x, y, self._wysokosc(x, y) + 0.12)
            r = max(1.1, ska * odn * 0.85)
            st.punkt_swiatla(p, srodek, r * 4.6, BARWA_SWIATLA_DROGI, int(54 * moc))
            p.setBrush(QBrush(st.z_alfa(BARWA_SWIATLA_DROGI, int(170 * moc))))
            p.drawEllipse(srodek, r, r * 0.72)
        p.setBrush(Qt.BrushStyle.NoBrush)

    def _rysuj_polysk_rzeki(self, p):
        """Połysk przepływający wzdłuż rzeki — po tym poznać, że to woda."""
        rzeka = self._rzeka
        if len(rzeka) < 6:
            return
        rzut = self.rzut()
        szer = self._miara * UDZIAL_RZEKI
        n = len(rzeka)
        okno = max(3, n // 7)
        t = (self._czas_zycia / OKRES_RZEKI_MS) % 1.0
        pocz = int(t * (n - okno))
        kawalek = [(x + SWIATLO_3D[0] * szer * 0.3, y + SWIATLO_3D[1] * szer * 0.3)
                   for (x, y) in rzeka[pocz:pocz + okno]]
        if len(kawalek) < 3:
            return
        # gaśnie na początku i na końcu biegu, żeby nie wskakiwał znikąd
        brzeg = min(1.0, min(t, 1.0 - t) / 0.10)
        for szerokosc, alfa in ((0.62, 26), (0.30, 58)):
            pas = _wstega(rzut, kawalek, szer * szerokosc, self._wysokosc, wznios=0.22)
            p.fillPath(pas, st.z_alfa(st.MIETA, int(alfa * brzeg)))

    # blask płynie po trasie i po drodze ZAPALA przystanki — szerokość
    # świecenia w ułamku długości trasy, po obu stronach czoła
    SZEROKOSC_ZAPALU = 0.115

    def _rysuj_zapal_przystankow(self, p, geo):
        """Przystanek rozjaśnia się w chwili, gdy mija go płynący blask.

        To nie jest miganie w tle: światło idzie po przystankach w tej
        samej kolejności, w jakiej się je odwiedza, i w tym samym rytmie,
        co blask na trasie. Z mapy da się odczytać porządek dnia, a nie
        tylko jego kształt.
        """
        slupy = geo.get("slupy") or ()
        if not slupy:
            return
        czolo = -0.19 + self._faza * 1.19        # tak samo liczy je _rysuj_blask
        kolor = self._kolor_trasy()
        p.setPen(Qt.PenStyle.NoPen)
        for sl in slupy:
            if sl["baza"]:                       # baza ma swój własny oddech
                continue
            odleglosc = abs(czolo - sl.get("postep", 0.0))
            if odleglosc >= self.SZEROKOSC_ZAPALU:
                continue
            moc = (1.0 - odleglosc / self.SZEROKOSC_ZAPALU) ** 2.0
            r = max(2.4, sl["skala_g"] * 9.0)
            st.punkt_swiatla(p, sl["gora"], r * (1.6 + 2.4 * moc), kolor,
                             int(18 + 132 * moc))
            # ślad na gruncie rozchodzi się jak fala po wodzie — po tym widać,
            # że blask właśnie tu dojechał, a nie tylko przechodzi obok
            rp = max(4.0, sl["skala"] * 3.2)
            st.punkt_swiatla(p, sl["dol"], rp * (1.8 + 1.2 * moc), kolor,
                             int(64 * moc))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(st.z_alfa(kolor, int(170 * moc * (1.0 - moc) * 4.0)), 1.4))
            fala = rp * (1.2 + 2.6 * (1.0 - moc))
            p.drawEllipse(sl["dol"], fala, fala * 0.56)
            p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(Qt.BrushStyle.NoBrush)

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
        strefy = self._strefy_zajete()
        zajete, etykiety = [], []
        # baza pierwsza, potem przystanki w kolejności trasy — dokładnie tak,
        # jak zbudowana jest lista słupów. Żadnego sortowania po położeniu na
        # ekranie ani po zbiorze: ta sama trasa ma zawsze dać ten sam układ
        mieszczace = max(60.0, self._pole().width() - 12.0)
        for s in slupy:
            baza = s["baza"]
            napis = f"{s['nazwa']} · start i powrót" if baza else s["nazwa"]
            m = m_baza if baza else m_zwykly
            szer = m.horizontalAdvance(napis) + (baza and 20 or 16)
            if baza and szer > mieszczace:
                # w kadrze węższym niż sama tabliczka zostaje sama nazwa bazy;
                # że to baza, widać po zieleni i po większym piśmie
                napis = s["nazwa"]
                szer = m.horizontalAdvance(napis) + 20
            wys = m.height() + 8
            kotwica = s["gora"]
            pole = self._miejsce_podpisu(kotwica, szer, wys, zajete, brzeg,
                                         strefy, przeszkody, slupy, s)
            zajete.append(pole)
            rozmiar, waga = (rozm_b, 700) if baza else (rozm_z, 600)
            odlegla = math.hypot(pole.center().x() - kotwica.x(),
                                 pole.center().y() - kotwica.y()) > self.NITKA_PODPISU
            etykiety.append({"pole": pole, "napis": napis, "rozmiar": rozmiar,
                             "waga": waga, "baza": baza, "kotwica": kotwica,
                             "powtorka": s["wizyty"] > 1, "nitka": odlegla})
        return etykiety

    def _miejsce_podpisu(self, kotwica, szer, wys, zajete, brzeg, strefy,
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
            for strefa in strefy:          # kartka, pigułka, przełącznik zakresu
                if not pole.intersected(strefa).isEmpty():
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
                for strefa in strefy:
                    # pod kartką tabliczki nie widać w ogóle, a pod cudzą
                    # tabliczką widać choć tyle, co wystaje — papier jest więc
                    # gorszym schronieniem niż sąsiadka
                    w = pole.intersected(strefa)
                    k += w.width() * w.height() * 1.2
                if najkoszt is None or k < najkoszt:
                    najkoszt, najlepszy = k, pole
        return najlepszy

    def _rysuj_podpisy(self, p, geo, ile=1.0):
        """Tabliczki zwrócone do widza: nie pochylają się razem z terenem."""
        kolor = self._kolor_trasy()
        for e in geo["etykiety"]:
            zapal = self._zapal(e.get("postep", 0.0), ile)
            if zapal <= 0.0:                 # tabliczka czeka na swój przystanek
                continue
            p.setOpacity(zapal)
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
        p.setOpacity(1.0)

    # — nitka do kartki —
    def _sciezka_nitki(self):
        """Łuk od trasy do kartki; None, gdy kartka nie podała kotwicy."""
        dzien = self._dzien
        if self._kotwica is None or dzien is None or dzien.wolny:
            return None
        dokad = QPointF(self._kotwica)
        kar = self._pole_kartki()
        if kar is not None:
            # nitka kończy się PRZY krawędzi papieru, a nie pod nim: pod kartką
            # nie ma prawa świecić nic, co należy do trasy
            dokad = QPointF(min(dokad.x(), kar.left() - 4.0),
                            max(kar.top() + 6.0, min(dokad.y(), kar.bottom() - 6.0)))
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
        """Nitka łączy trasę z kartką — jest jej dokładnie tyle, ile kartki."""
        sciezka = geo["nitka"]
        if sciezka is None or self._obecnosc_kar <= 0.02:
            return
        p.save()
        kar = self._pole_kartki()
        if kar is not None:
            # nitka dobiega do papieru i tam się urywa — pod kartką nie świeci
            # nic z trasy, nawet ta jedna kreska, której i tak nie byłoby widać
            p.setClipRegion(QRegion(self.rect()).subtracted(
                QRegion(kar.toAlignedRect())))
        p.setOpacity(self._obecnosc_kar)
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
        p.setOpacity(1.0)
        p.restore()

    # — cień kartki —
    def _pole_kartki(self):
        """Prostokąt kartki: ten podany przez okno, a w ostateczności zgadnięty.

        Okno zna geometrię kartki co do piksela i podaje ją razem z kotwicą.
        Zgadywanie zostaje tylko dla mapy używanej samodzielnie (podgląd,
        zrzuty scen) — i zgaduje ostrożnie, bo kartka nigdy nie sięga niżej
        niż do dolnego marginesu widżetu.
        """
        if self._pole_kar is not None:
            return QRectF(self._pole_kar)
        if self._kotwica is None:
            return None
        lewy = self._kotwica.x() - 8.0
        gora = self._kotwica.y() - 26.0
        prawy = self.width() - 18.0
        if prawy - lewy < 60.0:
            return None
        dol = min(self.height() - 18.0, gora + (prawy - lewy) * 1.46)
        return QRectF(lewy, gora, prawy - lewy, max(60.0, dol - gora))

    def _rysuj_cien_kartki(self, p, kar=None):
        """Kartka unosi się nad terenem, więc kładzie na niego długi cień."""
        if kar is None:
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

    def _pixmapa_cienia(self):
        """Cień kartki policzony RAZ. Nie rusza się, a szedł 25 razy na sekundę."""
        kar = self._pole_kartki()
        pole = None if kar is None else (round(kar.x(), 1), round(kar.y(), 1),
                                         round(kar.width(), 1), round(kar.height(), 1))
        klucz = (pole, self.width(), self.height(),
                 round(self.devicePixelRatioF(), 3), self._klucz_kadru())
        if self._cien_klucz == klucz:
            return self._cien_pix
        pix = None
        if kar is not None:
            pix = self._nowa_pixmapa()
            q = QPainter(pix)
            q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self._rysuj_cien_kartki(q, kar)
            q.end()
        self._cien_pix, self._cien_klucz = pix, klucz
        return pix

    def _poloz_cien_kartki(self, p):
        """Gotowy cień kładziony z przezroczystością — kartka może ustępować."""
        ile = self._obecnosc_kar
        if ile <= 0.02:
            return
        pix = self._pixmapa_cienia()
        if pix is None:
            return
        if ile < 0.999:
            p.setOpacity(ile)
            p.drawPixmap(0, 0, pix)
            p.setOpacity(1.0)
        else:
            p.drawPixmap(0, 0, pix)

    def _wykonczenie(self):
        """Winieta i ziarno: dwie rzeczy zupełnie nieruchome, więc w pixmapie."""
        klucz = (self.width(), self.height(), round(self.devicePixelRatioF(), 3))
        if self._wykonczenie_klucz == klucz and self._wykonczenie_pix is not None:
            return self._wykonczenie_pix
        pix = self._nowa_pixmapa()
        q = QPainter(pix)
        r = QRectF(self.rect())
        st.winieta(q, r, 62)
        st.ziarno(q, r, 10)
        q.end()
        self._wykonczenie_pix, self._wykonczenie_klucz = pix, klucz
        return pix

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
    """Biała kartka polecenia wyjazdu, kładziona przez okno główne na mapie.

    Kartka zna trzy niezależne stany. OBECNOŚĆ to choreografia dnia: przy
    zmianie dnia kartka ustępuje mapie, trasa rysuje się od nowa, a kartka
    wraca dopiero, gdy trasa dobiegnie do bazy. ZWINIĘCIE to wyjście awaryjne
    dla patrzącego: kartka zwija się do paska przy krawędzi i odsłania całą
    mapę. STRONA to przód albo odwrót: przód jest urzędowym poleceniem
    wyjazdu, odwrót tym samym dniem takim, jaki był NAPRAWDĘ — godziny
    wyjazdu i powrotu, postoje z czasem, skąd wzięły się kilometry każdego
    odcinka (realne drogi / pamięć dróg / szacunek) i droga wobec linii
    prostej.

    GESTY. Klik w kartkę OBRACA ją wokół pionowej osi — to gest ciekawości
    i dostaje całą powierzchnię papieru. Zwinięcie idzie w stronę krawędzi
    ekranu, więc jego uchwyt leży na tej krawędzi kartki: wąski, perforowany
    pasek przy prawym brzegu ze strzałką „›" (:attr:`UCHWYT`) — klik w niego
    zwija kartkę. Zwinięty pasek nie ma już nic innego do pokazania, więc klik
    w niego po prostu rozwija kartkę z powrotem, na tę samą stronę.

    Obrót jest PRZEKSZTAŁCENIEM dwóch gotowych pixmap (przód i odwrót leżą
    w pamięci, klatka animacji tylko ściska tę, która jest zwrócona do widza),
    a nie rysowaniem treści co klatkę. Przy wyłączonych animacjach obrót jest
    natychmiastowy, więc zrzuty pozostają powtarzalne.
    """

    przelaczono_zwiniecie = pyqtSignal(bool)
    obecnosc_zmieniona = pyqtSignal(float)
    odwrocono = pyqtSignal(str)            # "przod" albo "tyl" — dokąd zmierza obrót

    SZEROKOSC_WZORCOWA = 342.0     # szerokość kartki z projektu; od niej idzie skala
    SZEROKOSC_ZWINIETA = 26        # pasek, do którego zwija się kartka
    WSUNIECIE = 14.0               # o tyle kartka wjeżdża przy odświeżeniu treści
    CZAS_USTAPIENIA = 260          # jak szybko kartka schodzi mapie z drogi
    CZAS_POWROTU = 420             # ...i jak wraca, gdy trasa jest narysowana
    CZAS_OBROTU = 560              # obrót kartki na drugą stronę
    # pasek uchwytu zwinięcia przy prawym brzegu — mieści się w marginesie
    # papieru (5,5% szerokości), więc treść przodu nie musi się przesuwać
    UCHWYT = 16.0
    STRONY = ("przod", "tyl")

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMinimumSize(self.SZEROKOSC_ZWINIETA, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dzien = None
        self._numer = ""
        self._stan = "pusta"
        self._klucz = None
        self._zwinieta = False
        self._pix = None                # gotowa kartka; wsuwanie tylko ją przesuwa
        self._pix_klucz = None
        self._pix_tyl = None            # gotowy odwrót — rysowany raz, obracany pixmapą
        self._pix_tyl_klucz = None
        self._anim = True
        self._wejscie = st.Plynnie(1.0, czas=380, krzywa="wyjscie", rodzic=self,
                                   przy_zmianie=self.update)
        self._obecnosc = st.Plynnie(1.0, czas=self.CZAS_POWROTU, krzywa="wyjscie",
                                    rodzic=self, przy_zmianie=self._obecnosc_drgnela)
        # 0 = przód zwrócony do widza, 1 = odwrót; między nimi kartka się obraca
        self._obrot = st.Plynnie(0.0, czas=self.CZAS_OBROTU, krzywa="lagodna",
                                 rodzic=self, przy_zmianie=self.update)

    # — interfejs publiczny —
    def ustaw_dzien(self, dzien):
        zmiana = self._klucz_dnia(dzien) != self._klucz
        self._klucz = self._klucz_dnia(dzien)
        self._dzien = dzien
        if dzien is not None and not self._numer:
            self._numer = f"{dzien.data.year}/{dzien.data.month:02d}/{dzien.data.day:02d}"
        # Odświeżenie treści ma swoje własne, krótkie wsunięcie — ale tylko
        # wtedy, gdy kartka leży na miejscu. Kiedy właśnie ustępuje rysującej
        # się trasie, całą drogę wyjścia i powrotu prowadzi ``_obecnosc``;
        # drugie wsunięcie w tej samej chwili zgasiłoby kartkę w pół ruchu.
        if zmiana and self._anim and self.isVisible() \
                and self._obecnosc.cel() >= 0.999:
            self._wejscie.ustaw(0.0)
            self._wejscie.do(1.0)
        elif zmiana:
            self._wejscie.ustaw(1.0)
        self.update()

    # — choreografia: kartka ustępuje rysującej się trasie —
    def ustap(self):
        """Kartka schodzi mapie z drogi — trasa ma się rysować na wolnym polu."""
        if not self._anim:
            return
        self._obecnosc.do(0.0, czas=self.CZAS_USTAPIENIA, krzywa="wejscie")

    def wroc(self):
        """Trasa dobiegła do bazy — kartka wsuwa się jako jej wynik."""
        if not self._anim:
            self._obecnosc.ustaw(1.0)
            return
        self._obecnosc.do(1.0, czas=self.CZAS_POWROTU, krzywa="wyjscie")

    def obecnosc(self):
        """Ile kartki widać: 0 to zeszła z drogi, 1 to leży na swoim miejscu."""
        return max(0.0, min(1.0, self._obecnosc.teraz()))

    def _obecnosc_drgnela(self):
        self.obecnosc_zmieniona.emit(self.obecnosc())
        self.update()

    # — zwinięcie do brzegu —
    def zwinieta(self):
        return self._zwinieta

    def ustaw_zwiniecie(self, zwinieta, zglos=True):
        """Zwija kartkę do paska przy krawędzi albo rozwija ją z powrotem."""
        zwinieta = bool(zwinieta)
        if zwinieta == self._zwinieta:
            return
        self._zwinieta = zwinieta
        self._pix = None
        self._pix_tyl = None
        self.setToolTip("")
        if zglos:
            self.przelaczono_zwiniecie.emit(zwinieta)
        self.update()

    def przelacz_zwiniecie(self):
        self.ustaw_zwiniecie(not self._zwinieta)

    # — druga strona —
    def strona(self):
        """Dokąd zmierza kartka: „przod" albo „tyl" (w trakcie obrotu — cel)."""
        return "tyl" if self._obrot.cel() >= 0.5 else "przod"

    def obrot(self):
        """Faza obrotu 0..1: 0 to przód zwrócony do widza, 1 to odwrót."""
        return max(0.0, min(1.0, self._obrot.teraz()))

    def ustaw_strone(self, nazwa, zglos=True):
        """Przód albo odwrót. Z animacjami — obrót wokół pionowej osi;
        bez nich kartka od razu leży wybraną stroną do góry."""
        cel = 1.0 if nazwa == "tyl" else 0.0
        if abs(self._obrot.cel() - cel) < 1e-9:
            return
        if self._anim and self.isVisible() and not self._zwinieta:
            self._obrot.do(cel, czas=self.CZAS_OBROTU)
        else:
            self._obrot.ustaw(cel)
        if zglos:
            self.odwrocono.emit(self.strona())
        self.update()

    def odwroc(self):
        """Klik w papier: przód → odwrót, odwrót → przód."""
        self.ustaw_strone("przod" if self.strona() == "tyl" else "tyl")

    def szerokosc_uchwytu(self):
        """Pasek uchwytu zwinięcia przy prawym brzegu kartki, w pikselach."""
        kar, _promien = self._pole_kartki()
        return max(12.0, min(self.UCHWYT, kar.width() * 0.09))

    def w_uchwycie(self, punkt):
        """Czy punkt (współrzędne widżetu) leży na uchwycie zwinięcia."""
        if self._zwinieta:
            return False
        kar, _promien = self._pole_kartki()
        punkt = QPointF(punkt)
        return (kar.contains(punkt)
                and punkt.x() >= kar.right() - self.szerokosc_uchwytu())

    def mousePressEvent(self, zdarzenie):
        """Trzy gesty na jednym przycisku: pasek → rozwiń, uchwyt → zwiń,
        papier → obróć na drugą stronę (patrz opis klasy)."""
        if zdarzenie.button() == Qt.MouseButton.LeftButton:
            if self._zwinieta:
                self.ustaw_zwiniecie(False)
            elif self.w_uchwycie(zdarzenie.position()):
                self.ustaw_zwiniecie(True)
            else:
                self.odwroc()
            zdarzenie.accept()
            return
        super().mousePressEvent(zdarzenie)

    def ustaw_numer(self, tekst):
        self._numer = str(tekst or "")
        self.update()

    def resizeEvent(self, zdarzenie):
        self._pix = None
        self._pix_tyl = None
        super().resizeEvent(zdarzenie)

    def ustaw_stan(self, nazwa):
        self._stan = nazwa if nazwa in ("pusta", "zwykla", "podpisana") else "zwykla"
        self.update()

    def ustaw_animacje(self, wlaczone):
        """Włącza albo gasi wsuwanie i obrót kartki. Wyłączona siada od razu
        na miejscu, wybraną stroną do góry."""
        self._anim = bool(wlaczone)
        if not self._anim:
            self._wejscie.zatrzymaj()
            self._wejscie.ustaw(1.0)
            self._obecnosc.zatrzymaj()
            self._obecnosc.ustaw(1.0)
            self._obrot.zatrzymaj()
            self._obrot.ustaw(self._obrot.cel())
        self.update()

    def zatrzymaj_animacje(self):
        self.ustaw_animacje(False)

    def animacje_wlaczone(self):
        return self._anim

    def sizeHint(self):
        return QSize(360, 470)

    def hideEvent(self, zdarzenie):
        self._wejscie.zatrzymaj()
        self._obecnosc.zatrzymaj()
        self._obrot.zatrzymaj()
        super().hideEvent(zdarzenie)

    def closeEvent(self, zdarzenie):
        self._wejscie.zatrzymaj()
        self._obecnosc.zatrzymaj()
        self._obrot.zatrzymaj()
        super().closeEvent(zdarzenie)

    def _klucz_dnia(self, dzien):
        if dzien is None:
            return None
        # odcinki wchodzą do klucza odciskiem: ten sam dzień z innymi
        # kilometrami odcinków albo innym źródłem to inny odwrót kartki
        odcisk = tuple((round(e["km"], 1), e["prosta"], e["zrodlo"], e["wyj"], e["przyj"])
                       for e in etapy_dnia(dzien)) if getattr(dzien, "etapy", None) else ()
        return (dzien.data, dzien.wolny, round(dzien.kwota, 2), tuple(dzien.przystanki),
                odcisk)

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
                 self._stan, self._numer, self._zwinieta)
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
        if self._zwinieta:
            self._rysuj_zakladke(p, kar, pusta)
            p.end()
            self._pix, self._pix_klucz = pix, klucz
            return pix
        self._rysuj_tresc(p, kar, pusta)
        self._rysuj_uchwyt(p, kar, pusta)

        if self._stan == "podpisana" and not pusta:
            p.setPen(QPen(st.z_alfa(st.ZIELEN.darker(130), 190), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(sciezka)
            self._rysuj_pieczatke(p, kar)
        p.end()
        self._pix, self._pix_klucz = pix, klucz
        return pix

    def _pixmapa_tylu(self):
        """Gotowy odwrót kartki — rysowany raz, obrót tylko go ściska."""
        if self._zwinieta:
            return self._pixmapa()
        dpr = self.devicePixelRatioF()
        klucz = (self.width(), self.height(), round(dpr, 3), self._klucz,
                 self._stan, self._numer)
        if self._pix_tyl is not None and self._pix_tyl_klucz == klucz:
            return self._pix_tyl
        pix = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        kar, promien = self._pole_kartki()
        pusta = (self._stan == "pusta") or self._dzien is None or self._dzien.wolny
        _cien_miekki(p, kar, promien, przesun=2, rozmycie=6, sila=110, krok=2)
        _cien_miekki(p, kar, promien, przesun=9, rozmycie=21, sila=96, krok=3)
        _cien_miekki(p, kar, promien, przesun=24, rozmycie=48, sila=64, krok=6)
        sciezka = QPainterPath()
        sciezka.addRoundedRect(kar, promien, promien)
        self._rysuj_papier(p, kar, sciezka, promien, pusta)
        self._rysuj_tresc_tylu(p, kar, pusta)
        self._rysuj_uchwyt(p, kar, pusta)
        p.end()
        self._pix_tyl, self._pix_tyl_klucz = pix, klucz
        return pix

    def paintEvent(self, _zdarzenie):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        obec = self.obecnosc()
        if obec <= 0.004:                    # kartka zeszła mapie z drogi
            p.end()
            return
        t = max(0.0, min(1.0, self._wejscie.teraz()))
        if obec < 0.999:
            # ustąpienie: kartka odjeżdża w prawo, poza własną krawędź, i blednie
            p.setOpacity(obec ** 0.75)
            p.translate((1.0 - obec) * (self.width() + 24.0), 0.0)
        if t < 0.999:
            p.setOpacity(p.opacity() * max(0.0, min(1.0, t * 1.15)))
            p.translate((1.0 - t) * self.WSUNIECIE, (1.0 - t) * self.WSUNIECIE * 0.22)

        # Obrót wokół pionowej osi: kartka to gotowa pixmapa ściśnięta w poziomie
        # o cosinus kąta; do połowy obrotu widać przód, potem odwrót. Nic nie
        # jest rysowane od nowa — to samo przekształcenie, co przy wsuwaniu.
        faza = 0.0 if self._zwinieta else self.obrot()
        kat = faza * math.pi
        cos_k = math.cos(kat)
        pix = self._pixmapa() if cos_k >= 0.0 else self._pixmapa_tylu()
        scisk = abs(cos_k)
        if scisk < 0.012:                    # kartka bokiem do widza — nie ma czego rysować
            p.end()
            return
        kar, promien = self._pole_kartki()
        if scisk < 0.999:
            os_x = kar.center().x()
            p.translate(os_x, 0.0)
            p.scale(scisk, 1.0)
            p.translate(-os_x, 0.0)
        p.drawPixmap(0, 0, pix)
        # w połowie obrotu papier ustawia się bokiem do światła i ciemnieje
        bok = math.sin(kat)
        if bok > 0.004:
            sciezka = QPainterPath()
            sciezka.addRoundedRect(kar, promien, promien)
            p.fillPath(sciezka, QColor(20, 28, 44, int(78 * bok)))
        # rozjaśnienie przy wjeździe — kartka „zapala się” i gaśnie do normy
        rozblysk = max(1.0 - t, max(0.0, (obec - 0.62) / 0.38) * (1.0 - obec) * 2.6)
        if rozblysk > 0.004:
            sciezka = QPainterPath()
            sciezka.addRoundedRect(kar, promien, promien)
            p.fillPath(sciezka, QColor(255, 255, 255, int(80 * min(1.0, rozblysk))))
        p.end()

    def _rysuj_uchwyt(self, p, kar, pusta):
        """Uchwyt zwinięcia: perforowany pasek przy prawym brzegu i „›".

        Żadnego napisu — perforacja mówi „tu się odrywa", a strzałka, w którą
        stronę kartka pojedzie. Pasek leży w marginesie papieru, poza treścią.
        """
        szer = self.szerokosc_uchwytu()
        x0 = kar.right() - szer
        gora = kar.top() + kar.height() * 0.05
        dol = kar.bottom() - kar.height() * 0.05
        p.setBrush(Qt.BrushStyle.NoBrush)
        pioro = QPen(QColor(28, 34, 48, 34 if pusta else 46), 1.0)
        pioro.setDashPattern([1.6, 2.6])
        p.setPen(pioro)
        p.drawLine(QPointF(x0, gora), QPointF(x0, dol))
        sx = x0 + szer * 0.5
        sy = kar.center().y()
        ramie = max(2.6, szer * 0.19)
        barwa = QColor("#8A94A6") if pusta else QColor("#4A5872")
        pioro = QPen(barwa, max(1.3, szer * 0.09))
        pioro.setCapStyle(Qt.PenCapStyle.RoundCap)
        pioro.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pioro)
        # strzałka w prawo: tam pojedzie kartka po zwinięciu
        strzalka = QPainterPath(QPointF(sx - ramie * 0.5, sy - ramie))
        strzalka.lineTo(QPointF(sx + ramie * 0.5, sy))
        strzalka.lineTo(QPointF(sx - ramie * 0.5, sy + ramie))
        p.drawPath(strzalka)

    def _rysuj_zakladke(self, p, kar, pusta):
        """Zwinięta kartka: pasek papieru z zaznaczoną krawędzią i strzałką.

        Żadnego napisu — po zwiniętym pasku widać, że jest co rozwinąć,
        a strzałka mówi, w którą stronę.
        """
        barwa = QColor("#6C7689") if pusta else QColor("#243247")
        # trzy kreski jak brzegi złożonych kartek
        for i in range(3):
            x = kar.left() + kar.width() * (0.30 + 0.20 * i)
            p.setPen(QPen(QColor(28, 34, 48, 46 - 12 * i), 1.0))
            p.drawLine(QPointF(x, kar.top() + kar.height() * 0.06),
                       QPointF(x, kar.bottom() - kar.height() * 0.06))
        sx = kar.center().x()
        sy = kar.center().y()
        ramie = max(4.0, kar.width() * 0.26)
        p.setBrush(Qt.BrushStyle.NoBrush)
        pioro = QPen(barwa, max(1.7, kar.width() * 0.10))
        pioro.setCapStyle(Qt.PenCapStyle.RoundCap)
        pioro.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pioro)
        # strzałka w lewo: tam pojedzie kartka, gdy się ją rozwinie
        strzalka = QPainterPath(QPointF(sx + ramie * 0.5, sy - ramie))
        strzalka.lineTo(QPointF(sx - ramie * 0.5, sy))
        strzalka.lineTo(QPointF(sx + ramie * 0.5, sy + ramie))
        p.drawPath(strzalka)

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
        # uchwyt zwinięcia mieści się w marginesie; wąska kartka oddaje mu miejsce
        prawy = kar.right() - max(pad, self.szerokosc_uchwytu() + 2.0 * s)
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
        menedzer, brak_menedzera = _tekst_menedzera(dn.MENEDZER)
        rubryka(lewy, y, "PRACOWNIK", dn.PRACOWNIK, cw * 0.33)
        rubryka(lewy + cw * 0.355, y, "STANOWISKO", dn.STANOWISKO, cw * 0.34)
        rubryka(lewy + cw * 0.715, y, "MENEDŻER", menedzer, cw * 0.285,
                OSTRZEZENIE_NA_PAPIERZE if brak_menedzera else zielony)

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
            self._rysuj_dzien_wolny(p, kar, (y + y_rubryki) / 2.0, s)
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

    def _rysuj_dzien_wolny(self, p, kar, srodek, s):
        """Napis dnia wolnego z dwiema gasnącymi kreskami — obie strony kartki."""
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

    # — odwrót kartki —
    KOLORY_ZRODEL = {ZRODLO_DROGI: QColor("#0E9B74"), ZRODLO_PAMIEC: QColor("#3B5A9A"),
                     ZRODLO_SZACUNEK: OSTRZEZENIE_NA_PAPIERZE}

    def _rysuj_tresc_tylu(self, p, kar, pusta):
        """Odwrót: ten sam dzień, ale taki, jaki był naprawdę.

        Nagłówek jak na przodzie (żeby było widać, że to ta sama kartka),
        cztery rubryki czasu (wyjazd, powrót, jazda, postoje), oś dnia
        z przystankami i odcinkami między nimi, a u dołu sumy: kilometry,
        linia prosta, droga wobec prostej i z czego wzięły się odcinki.
        Same etykiety i liczby — bez jednego zdania.
        """
        s = kar.width() / self.SZEROKOSC_WZORCOWA
        pad = kar.width() * 0.055
        lewy = kar.x() + pad
        prawy = kar.right() - max(pad, self.szerokosc_uchwytu() + 2.0 * s)
        cw = prawy - lewy

        szary = QColor("#8A94A6")
        ciemny = st.PAPIER_TEKST
        sredni = QColor("#2A3853")
        zielony = QColor("#0E9B74")
        kreska_mocna = QColor(16, 24, 40, 120)

        y = kar.y() + 30 * s
        _napis(p, lewy, y, "Przebieg dnia", ciemny, 17 * s, 700, naglowek=True)
        _napis(p, prawy, kar.y() + 22 * s, "PMT", sredni, 11 * s, 600, prawy=True)
        _napis(p, prawy, kar.y() + 36 * s, dn.BAZA, sredni, 11 * s, 400, prawy=True)
        data = self._dzien.data.strftime("%d.%m.%Y") if self._dzien else ""
        podtytul = f"nr {self._numer} · {data}" if self._numer else data
        y += 15 * s
        _napis(p, lewy, y, podtytul, szary, 10.5 * s, 400)

        y += 12 * s
        p.setBrush(Qt.BrushStyle.NoBrush)
        g = QLinearGradient(QPointF(lewy, y), QPointF(prawy, y))
        g.setColorAt(0.0, st.z_alfa(zielony, 185))
        g.setColorAt(0.16, QColor(16, 24, 40, 140))
        g.setColorAt(0.62, QColor(16, 24, 40, 52))
        g.setColorAt(1.0, QColor(16, 24, 40, 12))
        p.setPen(QPen(QBrush(g), 1.2))
        p.drawLine(QPointF(lewy, y), QPointF(prawy, y))

        def rubryka(x, yy, etykieta, wartosc, kolor=ciemny, waga=700, prawa=False):
            _napis(p, x, yy, etykieta, szary, 8.6 * s, 500, odstep=0.8 * s, prawy=prawa)
            _napis(p, x, yy + 14 * s, wartosc, kolor, 11.5 * s, waga, mono=True, prawy=prawa)

        tresc = {} if pusta else tresc_tylu(self._dzien)

        # — dół liczony od spodu, jak na przodzie —
        dol = kar.bottom() - 18 * s
        y_zrodla = dol - 4 * s
        y_sumy = y_zrodla - 36 * s
        y_linia = y_sumy - 12 * s

        y += 18 * s
        if not tresc:
            self._rysuj_dzien_wolny(p, kar, (y + y_linia) / 2.0, s)
            return

        rubryka(lewy, y, "WYJAZD", tresc["wyjazd"] or "—")
        rubryka(lewy + cw * 0.25, y, "POWRÓT", tresc["powrot"] or "—")
        rubryka(lewy + cw * 0.50, y, "JAZDA", _czas_hm(tresc["jazda_min"]), sredni, 500)
        rubryka(prawy, y, "POSTOJE", _czas_hm(tresc["postoje_min"]), sredni, 500, prawa=True)

        y += 34 * s
        self._rysuj_os_dnia(p, lewy, prawy, y, y_linia - 8 * s, s, tresc,
                            szary, ciemny, sredni)

        p.setPen(QPen(kreska_mocna, 1.0))
        p.drawLine(QPointF(lewy, y_linia), QPointF(prawy, y_linia))
        rubryka(lewy, y_sumy, "RAZEM", f'{tresc["km"]:.1f}'.replace(".", ",") + " km")
        prosta = tresc["prosta"]
        rubryka(lewy + cw * 0.36, y_sumy, "LINIA PROSTA",
                (f"{prosta:.1f}".replace(".", ",") + " km") if prosta is not None else "—",
                sredni, 500)
        _napis(p, prawy, y_sumy, "DROGA / PROSTA", szary, 8.6 * s, 500, odstep=0.8 * s,
               prawy=True)
        wsk = tresc["wskaznik"]
        if wsk:
            napis = "×" + f"{wsk:.2f}".replace(".", ",")
            f = st.czcionka(12 * s, 700, mono=True)
            szer = QFontMetricsF(f).horizontalAdvance(napis)
            pole = QRectF(prawy - szer - 7 * s, y_sumy + 3 * s, szer + 14 * s, 17 * s)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(14, 155, 116, 20)))
            p.drawRoundedRect(pole, 4 * s, 4 * s)
            _napis(p, prawy, y_sumy + 15 * s, napis, ciemny, 12 * s, 700, mono=True, prawy=True)
        else:
            _napis(p, prawy, y_sumy + 15 * s, "—", sredni, 11.5 * s, 500, mono=True, prawy=True)

        # z czego wzięły się odcinki: kropka w barwie źródła i liczba odcinków
        x = lewy
        for zrodlo in KOLEJNOSC_ZRODEL:
            ile = tresc["zrodla"].get(zrodlo, 0)
            if not ile:
                continue
            kolor = self.KOLORY_ZRODEL[zrodlo]
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(kolor))
            p.drawEllipse(QPointF(x + 2.6 * s, y_zrodla - 3.2 * s), 2.6 * s, 2.6 * s)
            napis = "%s %d" % (ETYKIETY_ZRODEL[zrodlo], ile)
            _napis(p, x + 9 * s, y_zrodla, napis, sredni, 9.5 * s, 500)
            x += 9 * s + QFontMetricsF(st.czcionka(9.5 * s, 500)).horizontalAdvance(napis) + 14 * s

    def _rysuj_os_dnia(self, p, lewy, prawy, y_gora, y_dol, s, tresc, szary, ciemny, sredni):
        """Oś dnia: przystanki z godziną przyjazdu i czasem postoju, między
        nimi odcinki — kilometry, źródło i droga wobec linii prostej. Odcinek
        osi ma barwę swojego źródła, więc dzień z szacunku widać na oko."""
        etapy = tresc["etapy"]
        n = len(etapy)
        x_czas = lewy + 34 * s
        x_os = x_czas + 11 * s
        x_tekst = x_os + 10 * s
        wys = max(15.0 * s, min(34.0 * s, (y_dol - y_gora) / n))
        ciasno = wys < 21.0 * s
        y0 = y_gora + 4 * s

        # oś: każdy odcinek w barwie źródła, nieznane źródło — szary papieru
        for i, e in enumerate(etapy):
            kolor = self.KOLORY_ZRODEL.get(e["zrodlo"], QColor(16, 24, 40))
            alfa = 170 if e["zrodlo"] else 70
            pioro = QPen(st.z_alfa(kolor, alfa), max(1.4, 2.0 * s))
            pioro.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pioro)
            p.drawLine(QPointF(x_os, y0 + wys * i), QPointF(x_os, y0 + wys * (i + 1)))

        f_nazwa = st.czcionka(10.5 * s, 500)
        f_nazwa_baza = st.czcionka(10.5 * s, 600)
        f_postoj = st.czcionka(9.5 * s, 500, mono=True)
        for i in range(n + 1):
            y = y0 + wys * i
            baza = i in (0, n)
            p.setPen(Qt.PenStyle.NoPen)
            if baza:
                p.setPen(QPen(QColor("#0E9B74"), max(1.2, 1.6 * s)))
                p.setBrush(QBrush(QColor("#FFFDF9")))
                p.drawEllipse(QPointF(x_os, y), 3.4 * s, 3.4 * s)
            else:
                p.setBrush(QBrush(ciemny))
                p.drawEllipse(QPointF(x_os, y), 2.7 * s, 2.7 * s)
            czas = etapy[0]["wyj"] if i == 0 else etapy[i - 1]["przyj"]
            _napis(p, x_czas, y + 3.6 * s, czas or "—", sredni, 10 * s, 500, mono=True,
                   prawy=True)
            nazwa = etapy[0]["z"] if i == 0 else etapy[i - 1]["do"]
            po_prawej = ""
            if 0 < i < n:
                postoj = tresc["postoje"][i - 1]
                if postoj is not None:
                    po_prawej = _czas_hm(postoj)
            szer_pr = QFontMetricsF(f_postoj).horizontalAdvance(po_prawej) if po_prawej else 0.0
            f = f_nazwa_baza if baza else f_nazwa
            _napis(p, x_tekst, y + 3.6 * s,
                   _przytnij(nazwa, f, prawy - x_tekst - szer_pr - 8 * s),
                   ciemny, 10.5 * s, 600 if baza else 500)
            if po_prawej:
                _napis(p, prawy, y + 3.6 * s, po_prawej, sredni, 9.5 * s, 500, mono=True,
                       prawy=True)

        # odcinki między przystankami
        f_km = st.czcionka(9.5 * s, 600, mono=True)
        f_zr = st.czcionka(9 * s, 500)
        f_wsk = st.czcionka(9.5 * s, 600, mono=True)
        for i, e in enumerate(etapy):
            ym = y0 + wys * (i + 0.5) + 3.2 * s
            km_txt = f'{e["km"]:.1f}'.replace(".", ",") + " km"
            _napis(p, x_tekst, ym, km_txt, ciemny, 9.5 * s, 600, mono=True)
            x = x_tekst + QFontMetricsF(f_km).horizontalAdvance(km_txt) + 6 * s
            if e["zrodlo"]:
                _napis(p, x, ym, ETYKIETY_ZRODEL[e["zrodlo"]],
                       self.KOLORY_ZRODEL[e["zrodlo"]], 9 * s, 500)
                x += QFontMetricsF(f_zr).horizontalAdvance(ETYKIETY_ZRODEL[e["zrodlo"]]) + 6 * s
            if e["prosta"]:
                wsk = "×" + f'{e["km"] / e["prosta"]:.2f}'.replace(".", ",")
                _napis(p, prawy, ym, wsk, ciemny, 9.5 * s, 600, mono=True, prawy=True)
                if not ciasno:
                    x_w = prawy - QFontMetricsF(f_wsk).horizontalAdvance(wsk) - 8 * s
                    prosta_txt = "prosta " + f'{e["prosta"]:.1f}'.replace(".", ",")
                    if x_w - QFontMetricsF(f_zr).horizontalAdvance(prosta_txt) > x:
                        _napis(p, x_w, ym, prosta_txt, szary, 9 * s, 500, prawy=True)

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
# ══════════════════════════════════════════════════════════════════════
#  PRZELOT NAD REJONEM — to, na co patrzy użytkownik, gdy pracuje silnik
#
#  Silnik układa trasy w swoim wątku i melduje postęp; ekran nie ma na co
#  czekać, więc zamienia się w przelot: krajobraz rejonu sunie bokiem
#  z paralaksą (bliższy grunt szybciej niż dalszy), a trasy dni, które
#  silnik już ułożył, zapalają się na nim jedna po drugiej; przy pisaniu
#  plików kolejne dokumenty stemplują swoje trasy jaśniejszą barwą.
#  Kompas obok dalej pokazuje postęp. Gdy silnik skończy, przelot hamuje
#  i osiada na zwykłym widoku dnia, a trasa dnia rysuje się jak zawsze.
#  Przerwanie kończy przelot natychmiast.
#
#  Przelot CZYTA postęp, nigdy odwrotnie: silnik nie czeka na klatkę,
#  a trasy przychodzą sygnałem z wątku jako gotowe krotki.
#
#  Budżet klatki: scena jest upieczona RAZ na filmie szerszym niż widżet
#  (ta sama kamera — MapaDnia.wypiek_przelotu), trasy dni idą do drugiej,
#  przezroczystej pixmapy tego samego filmu. Przesunięcie kamery wzdłuż
#  osi wschód–zachód nie zmienia głębi punktu (kamera nie jest obrócona
#  wokół osi patrzenia), więc każdy wiersz ekranu jedzie w bok o
#  dx · skala(y), a skala rzutu jest w y niemal liniowa: klatka to jedno
#  ŚCINANIE (przekształcenie afiniczne) dwóch gotowych pixmap — ok. 3 ms
#  przy 1404×826. Uczciwy przelot kamerą (scena od nowa co klatkę) to
#  ~100 ms i jest nie do przyjęcia.
# ══════════════════════════════════════════════════════════════════════
UDZIAL_WAHNIECIA = 0.32        # amplituda lotu jako ułamek rozpiętości rejonu
ZAPAS_FILMU_MAX = 0.75         # film nie wystaje bardziej niż tyle szerokości widżetu
OKRES_PRZELOTU_S = 56.0        # jedno pełne wahnięcie kamery: tam i z powrotem
KLATKA_PRZELOTU = 33           # ms między klatkami
CZAS_STARTU_MS = 700           # mapa dnia odchodzi w tył, rejon wchodzi
CZAS_LADOWANIA_MS = 900        # hamowanie i osiadanie na nowym widoku dnia
CZAS_ZAPALANIA_MS = 900        # rozbłysk nowo ułożonej trasy
POWIEKSZENIE_STARTU = 1.05     # mapa dnia lekko rośnie, gdy odchodzi
POWIEKSZENIE_LADOWANIA = 1.04  # rejon lekko rośnie, gdy osiada
SUFIT_PRZELOTU_MS = 40.0       # tak drogie klatki z rzędu gaszą przelot
KLATEK_PRZELOTU_DO_DECYZJI = 12
BARWA_TRASY_PRZELOTU = st.CYJAN
BARWA_DOKUMENTU_PRZELOTU = st.MIETA
WARSTWY_TRASY_PRZELOTU = ((2.6, 16, 4), (1.3, 36, 2), (0.62, 104, 1), (0.30, 214, 1))
RDZEN_TRASY_PRZELOTU = ((0.13, 150, 1),)
PROMIEN_PRZYSTANKU_PRZELOTU = 2.4   # w jednostkach świata, jak grubości trasy
PROMIEN_CZOLA_PRZELOTU = 4.5        # świecąca głowa biegnąca po zapalanej trasie
ZAPAS_OBRYSU_TRASY = 30.0           # px poświaty wokół obrysu trasy na filmie


class PrzelotRejonu(QWidget):
    """Nakładka na mapę na czas pracy silnika — patrz opis wyżej.

    ``rejon`` to niepokazywana MapaDnia z tymi samymi miejscowościami co
    mapa na ekranie, bez dnia — jej kadr obejmuje cały rejon. ``mapa_pod``
    zwraca mapę, na której przelot ma wylądować (po generowaniu okno stawia
    nową). Interfejs zaczepu INTRO_GENEROWANIA: ``ustaw_postep``,
    ``dodaj_trase``, ``ustaw_dokumenty``, ``zakoncz``, ``przerwij``.
    """

    zakonczono = pyqtSignal()

    def __init__(self, rejon, mapa_pod=None, rodzic=None):
        super().__init__(rodzic)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._rejon = rejon
        self._mapa_pod = mapa_pod
        self._anim = True
        self._faza = "start"            # start → lot → ladowanie → koniec
        self._start_pix = None          # to, co było na ekranie przed przelotem
        self._pod = None                # to, na czym przelot osiada
        self._scena = None              # film: cała scena bez tras
        self._rzut = None               # kamera filmu
        self._film_w = 0                # szerokość filmu i jego środka, w px logicznych
        self._srodek_w = 0
        self._srodek_h = 0
        self._zapas_px = 0
        self._a = 0.0                   # skala(y) ≈ a + b·y — współczynniki ścinania
        self._b = 0.0
        self._amplituda = 0.0           # wahnięcie kamery w jednostkach świata
        self._t0 = None                 # chwila startu lotu (monotonic)
        self._chwila = None             # zamrożony czas — do zrzutów i sprawdzeń
        self._t_lad = 0.0
        self._dx_lad = 0.0
        self._v_lad = 0.0
        self._postep = 0.0
        self._trasy = []                # dni w kolejności nadejścia
        self._zapalane = []             # trasy w trakcie rozbłysku
        self._trasy_pix = None          # trasy już zapalone, na filmie
        self._koszt_klatki = 0.0
        self._drogie = 0
        self._wejscie = st.Plynnie(0.0, czas=CZAS_STARTU_MS, krzywa="lagodna",
                                   rodzic=self, klatka=KLATKA_PRZELOTU)
        self._zejscie = st.Plynnie(0.0, czas=CZAS_LADOWANIA_MS, krzywa="wejscie",
                                   rodzic=self, klatka=KLATKA_PRZELOTU)
        self._zejscie.koniec.connect(self._osiadl)
        self._zegar = QTimer(self)
        self._zegar.setInterval(KLATKA_PRZELOTU)
        self._zegar.timeout.connect(self._tik)
        if rodzic is not None:
            rodzic.installEventFilter(self)

    @classmethod
    def nad_mapa(cls, mapa, miasta=None, baza=None, mapa_pod=None, rodzic=None):
        """Przelot nad rejonem mapy ``mapa``: ten sam krajobraz (ziarno) i te
        same miejscowości (``miasta``: {nazwa: (szerokość, długość[, ranga])}),
        bez dnia — więc kadr całego rejonu. Nakładka staje dokładnie na mapie."""
        rejon = MapaDnia()
        rejon.resize(mapa.size())
        rejon._ustaw_ziarno(mapa.ziarno())
        if miasta:
            rejon.ustaw_miasta(miasta, baza=baza)
        rejon.ustaw_animacje(False)
        przelot = cls(rejon, mapa_pod=mapa_pod, rodzic=rodzic)
        przelot.setGeometry(mapa.geometry())
        return przelot

    # — odczyt —
    def faza(self):
        return self._faza

    def postep(self):
        return self._postep

    def przesuniecie(self):
        """Przesunięcie kamery w jednostkach świata w tej chwili."""
        return self._przesuniecie_w(self._czas()) if self._scena is not None else 0.0

    def trasy(self):
        """Ile tras dni już przyszło z silnika."""
        return len(self._trasy)

    def stemple(self):
        """Ile z nich ma już stempel gotowego dokumentu."""
        return sum(1 for t in self._trasy if t["stempel"])

    def koszt_klatki(self):
        """Średni koszt klatki w milisekundach."""
        return self._koszt_klatki

    def scena(self):
        """Film sceny (pixmapa) — None do pierwszego tyknięcia po pokazaniu."""
        return self._scena

    def wspolczynniki(self):
        """(zapas filmu w px, a, b): przesunięcie wiersza y to dx·(a + b·y)."""
        return self._zapas_px, self._a, self._b

    # — sterowanie z okna —
    def ustaw_start(self, pixmapa):
        """Obraz sprzed przelotu — odchodzi w tył w pierwszych klatkach."""
        self._start_pix = pixmapa
        self.update()

    def ustaw_postep(self, t):
        try:
            self._postep = max(0.0, min(1.0, float(t)))
        except (TypeError, ValueError):
            pass

    def ustaw_chwile(self, sekundy):
        """Zamraża zegar lotu na zadanej sekundzie (None = zegar żywy) —
        razem z wejściem i rozbłyskami, żeby ta sama chwila dawała zawsze
        tę samą klatkę (zrzuty, sprawdzenia)."""
        self._chwila = None if sekundy is None else float(sekundy)
        if self._chwila is not None:
            self._wejscie.zatrzymaj()
            self._wejscie.ustaw(st.KRZYWE["lagodna"](
                max(0.0, min(1.0, self._chwila * 1000.0 / CZAS_STARTU_MS))))
            for trasa in list(self._zapalane):
                trasa["zapal"].zatrzymaj()
                self._po_rozblysku(trasa)
        self.update()

    def dodaj_trase(self, punkty, data=None):
        """Silnik ułożył dzień: ``punkty`` to (nazwa, szerokość, długość) od
        bazy przez przystanki do bazy (wolno też same pary szerokość,
        długość). Zwraca True, gdy trasa da się położyć na tej mapie."""
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
                 "obrys": None, "punkty": None, "skale": None, "zapal": None}
        self._trasy.append(trasa)
        if self._scena is not None:
            self._zapal(trasa)
        return True

    def ustaw_dokumenty(self, ile, z_ilu):
        """Silnik pisze dokument ``ile`` z ``z_ilu``: trasy dni w kolejności dat
        dostają stempel — pierwsze ile/z_ilu wszystkich znanych dni."""
        try:
            ile, z_ilu = int(ile), int(z_ilu)
        except (TypeError, ValueError):
            return 0
        if z_ilu <= 0 or not self._trasy:
            return 0
        do_stempla = int(math.ceil(len(self._trasy) * min(ile, z_ilu) / float(z_ilu)))
        kolejnosc = sorted(self._trasy, key=lambda t: (t["data"] is None, t["data"] or 0))
        nowe = 0
        for trasa in kolejnosc[:do_stempla]:
            if trasa["stempel"]:
                continue
            trasa["stempel"] = True
            nowe += 1
            if self._scena is not None and trasa["punkty"] is not None:
                self._upiecz_trase(trasa)
                if trasa["zapal"] is None:
                    self._scal(trasa)          # już scalona — stempel idzie na wierzch
        if nowe:
            self.update()
        return nowe

    def zakoncz(self):
        """Silnik skończył: lądowanie. Wołane, zanim okno przebuduje mapę —
        samo lądowanie rusza po zakończeniu tej pracy (zegar 0 ms)."""
        if self._faza in ("ladowanie", "koniec"):
            return
        QTimer.singleShot(0, self._laduj)

    def przerwij(self):
        """Koniec natychmiast — przerwanie, zgaszone animacje, zamknięcie."""
        if self._faza == "koniec":
            return
        self._faza = "koniec"
        self._zegar.stop()
        self._wejscie.zatrzymaj()
        self._zejscie.zatrzymaj()
        for trasa in self._zapalane:
            if trasa["zapal"] is not None:
                trasa["zapal"].zatrzymaj()
        self._zapalane = []
        if self._pod is not None:
            self._wznow_trase_pod()          # lądowanie było w toku
        self.hide()
        self.zakonczono.emit()
        self._sprzatnij()

    def ustaw_animacje(self, wlaczone):
        """Ten sam wyłącznik co reszta ekranu: zgaszony przelot znika bez śladu."""
        self._anim = bool(wlaczone)
        if not self._anim:
            self.przerwij()

    def animacje_wlaczone(self):
        return self._anim

    def sizeHint(self):
        return QSize(900, 600)

    # — lot —
    def _czas(self):
        if self._chwila is not None:
            return self._chwila
        if self._t0 is None:
            return 0.0
        return time.monotonic() - self._t0

    def _przesuniecie_w(self, t):
        """Kamera waha się jak wahadło o okresie OKRES_PRZELOTU_S; przy lądowaniu
        dojeżdża z prędkością, którą miała, hamując równomiernie do zera."""
        if self._faza == "ladowanie":
            czas = CZAS_LADOWANIA_MS / 1000.0
            u = max(0.0, min(1.0, (t - self._t_lad) / czas))
            return self._dx_lad + self._v_lad * czas * (u - 0.5 * u * u)
        w = 2.0 * math.pi / OKRES_PRZELOTU_S
        return self._amplituda * math.sin(w * t)

    def _predkosc_w(self, t):
        w = 2.0 * math.pi / OKRES_PRZELOTU_S
        return self._amplituda * w * math.cos(w * t)

    def _tik(self):
        if self._scena is None:
            self._upiecz()
        self.update()

    def _upiecz(self):
        """Jedyny drogi krok przelotu: film sceny i współczynniki ścinania."""
        rejon = self._rejon
        W, H = max(1, rejon.width()), max(1, rejon.height())
        rzut0 = rejon.rzut()
        gx, gy = rzut0.na_grunt(W * 0.5, H * 0.94)
        s_blisko = max(1e-6, rzut0.skala(gx, gy, 0.0))
        self._amplituda = UDZIAL_WAHNIECIA * rejon._miara
        zapas = int(math.ceil(self._amplituda * s_blisko)) + 8
        if zapas > ZAPAS_FILMU_MAX * W:
            zapas = int(ZAPAS_FILMU_MAX * W)
            self._amplituda = max(0.0, (zapas - 8) / s_blisko)
        self._zapas_px = zapas
        self._scena, self._rzut = rejon.wypiek_przelotu(zapas)
        self._film_w = W + 2 * zapas
        self._srodek_w, self._srodek_h = W, H
        self._a, self._b = self._szer_paralaksy(self._rzut, self._film_w, H)
        self._trasy_pix = None
        for trasa in self._trasy:
            trasa["punkty"] = None
        for trasa in self._trasy:
            self._zapal(trasa, od_razu=True)
        self._t0 = time.monotonic()
        self._faza = "lot"
        self._wejscie.ustaw(0.0)
        self._wejscie.do(1.0)

    @staticmethod
    def _szer_paralaksy(rzut, szer, wys):
        """Prosta skala(y) ≈ a + b·y dopasowana do wierszy z gruntem w kadrze.

        Głębia punktu gruntu nie zależy od x, więc jedna próbka na wiersz
        wystarcza; wiersze nad horyzontem (promień nie trafia w grunt) nie
        wchodzą do dopasowania — w tej samej prostej dostają skalę bliską
        zera, czyli niebo prawie stoi."""
        ys, ss = [], []
        krok = max(4.0, wys / 48.0)
        y = krok * 0.5
        while y < wys:
            gx, gy = rzut.na_grunt(szer * 0.5, y, dal_max=2600.0)
            if rzut.glebokosc(gx, gy, 0.0) < 2400.0:
                ys.append(y)
                ss.append(rzut.skala(gx, gy, 0.0))
            y += krok
        if len(ys) < 2:
            return (rzut.k / 300.0, 0.0)
        n = float(len(ys))
        sy, ssk = sum(ys) / n, sum(ss) / n
        licznik = sum((y - sy) * (s - ssk) for y, s in zip(ys, ss))
        mianownik = sum((y - sy) ** 2 for y in ys) or 1.0
        b = licznik / mianownik
        return (ssk - b * sy, b)

    # — trasy dni —
    def _nowa_pixmapa_filmu(self):
        pix = QPixmap(self._scena.size())
        pix.setDevicePixelRatio(self._scena.devicePixelRatio())
        pix.fill(Qt.GlobalColor.transparent)
        return pix

    def _upiecz_trase(self, trasa):
        """Świecąca linia dnia na filmie: łagodna krzywa przez przystanki,
        uniesiona nad teren jak trasa dnia na mapie, w barwie dnia albo
        dokumentu. Pixmapa obejmuje tylko obrys trasy — rozbłysk i scalenie
        kosztują tyle, co ten obrys, nie cały film."""
        rejon, rzut = self._rejon, self._rzut
        wznios = rejon._wznios_trasy
        odn = rejon._odniesienie()
        punkty, skale = [], []
        for (x, y) in _gladko_2d(trasa["swiat"], na_odcinek=6):
            pt, s = rzut.rzutuj(x, y, rejon._wysokosc(x, y) + wznios)
            punkty.append(pt)
            skale.append(s * odn)
        film = QRectF(0, 0, self._film_w, self._srodek_h)
        xs = [p.x() for p in punkty]
        ys = [p.y() for p in punkty]
        obrys = QRectF(min(xs) - ZAPAS_OBRYSU_TRASY, min(ys) - ZAPAS_OBRYSU_TRASY,
                       max(xs) - min(xs) + 2 * ZAPAS_OBRYSU_TRASY,
                       max(ys) - min(ys) + 2 * ZAPAS_OBRYSU_TRASY).intersected(film)
        obrys = QRectF(math.floor(obrys.x()), math.floor(obrys.y()),
                       math.ceil(obrys.width()) + 1, math.ceil(obrys.height()) + 1)
        kolor = BARWA_DOKUMENTU_PRZELOTU if trasa["stempel"] else BARWA_TRASY_PRZELOTU
        dpr = self._scena.devicePixelRatio()
        pix = QPixmap(max(1, int(obrys.width() * dpr)), max(1, int(obrys.height() * dpr)))
        pix.setDevicePixelRatio(dpr)
        pix.fill(Qt.GlobalColor.transparent)
        q = QPainter(pix)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        q.translate(-obrys.x(), -obrys.y())
        _poswiata_zmienna(q, punkty, skale, kolor, WARSTWY_TRASY_PRZELOTU)
        _poswiata_zmienna(q, punkty, skale, QColor(232, 255, 255), RDZEN_TRASY_PRZELOTU)
        for (x, y) in trasa["swiat"][1:-1]:
            pt, s = rzut.rzutuj(x, y, rejon._wysokosc(x, y) + wznios)
            st.punkt_swiatla(q, pt, PROMIEN_PRZYSTANKU_PRZELOTU * s * odn, kolor, 120)
        q.end()
        trasa["pix"], trasa["obrys"] = pix, obrys
        trasa["punkty"], trasa["skale"] = punkty, skale

    def _zapal(self, trasa, od_razu=False):
        """Trasa wchodzi na film: rozbłyskiem (zegar), albo od razu."""
        self._upiecz_trase(trasa)
        if od_razu or not self._anim or self._chwila is not None:
            self._scal(trasa)
            return
        zapal = st.Plynnie(0.0, czas=CZAS_ZAPALANIA_MS, krzywa="lagodna",
                           rodzic=self, klatka=KLATKA_PRZELOTU)
        trasa["zapal"] = zapal
        zapal.koniec.connect(lambda t=trasa: self._po_rozblysku(t))
        self._zapalane.append(trasa)
        zapal.do(1.0)
        self.update()

    def _po_rozblysku(self, trasa):
        if trasa in self._zapalane:
            self._zapalane.remove(trasa)
        trasa["zapal"] = None
        self._scal(trasa)
        self.update()

    def _scal(self, trasa):
        """Gotowa trasa przechodzi do wspólnej pixmapy — klatka jej nie liczy."""
        if trasa["pix"] is None:
            return
        if self._trasy_pix is None:
            self._trasy_pix = self._nowa_pixmapa_filmu()
        q = QPainter(self._trasy_pix)
        q.drawPixmap(trasa["obrys"].topLeft(), trasa["pix"])
        q.end()
        if trasa["zapal"] is None:
            trasa["pix"] = None            # scalona — osobna pixmapa niepotrzebna

    # — lądowanie —
    def _laduj(self):
        if self._faza in ("ladowanie", "koniec"):
            return
        if self._scena is None or not self._anim or not self.isVisible():
            self.przerwij()
            return
        mapa = self._mapa_pod() if self._mapa_pod is not None else None
        if mapa is not None:
            try:
                mapa.ustaw_postep_rysowania(0.0)   # trasa dnia narysuje się PO lądowaniu
                mapa.trasa_rysuje_sie.emit()       # ...więc kartka ustępuje już teraz
                mapa.ustaw_obecnosc_kartki(0.0)    # i w obrazie pod nakładką nie ma jej cienia
            except Exception:
                pass
            # sama mapa, bez kartki i pigułki: kartka właśnie ustępuje trasie
            # i w przenikaniu zamarłaby w pół ruchu
            self._pod = mapa.grab()
        t = self._czas()
        self._dx_lad = self._przesuniecie_w(t)
        self._v_lad = self._predkosc_w(t)
        self._t_lad = t
        self._faza = "ladowanie"
        self._zejscie.ustaw(0.0)
        if self._chwila is not None:
            return                                # zamrożony zegar: lądowanie stoi
        self._zejscie.do(1.0)

    def _wznow_trase_pod(self):
        mapa = self._mapa_pod() if self._mapa_pod is not None else None
        self._pod = None
        if mapa is None:
            return
        try:
            mapa.rysuj_trase_od_nowa()
        except Exception:
            pass

    def _osiadl(self):
        if self._faza == "koniec":
            return
        self._faza = "koniec"
        self._zegar.stop()
        self.hide()
        self._wznow_trase_pod()
        self.zakonczono.emit()
        self._sprzatnij()

    def _sprzatnij(self):
        rejon, self._rejon = self._rejon, None
        if rejon is not None:
            rejon.deleteLater()
        self._scena = None
        self._trasy_pix = None
        self._start_pix = None
        rodzic = self.parentWidget()
        if rodzic is not None:
            rodzic.removeEventFilter(self)
            self.setParent(None)           # okno nie ma już tego dziecka — od razu
        self.deleteLater()

    # — zdarzenia —
    def eventFilter(self, obj, zdarzenie):
        if obj is self.parentWidget() and zdarzenie.type() == QEvent.Type.Resize:
            QTimer.singleShot(0, self._dopasuj)
        return False

    def _dopasuj(self):
        mapa = self._mapa_pod() if self._mapa_pod is not None else None
        if mapa is not None and self._faza != "koniec" \
                and mapa.parentWidget() is self.parentWidget():
            self.setGeometry(mapa.geometry())

    def showEvent(self, zdarzenie):
        super().showEvent(zdarzenie)
        if self._anim and self._faza != "koniec" and not self._zegar.isActive():
            self._zegar.start()

    def hideEvent(self, zdarzenie):
        self._zegar.stop()
        super().hideEvent(zdarzenie)

    def mousePressEvent(self, zdarzenie):
        zdarzenie.accept()               # pod nakładką nic nie ma dostać kliknięcia

    # — klatka —
    def _kamera(self, p, r, dx, powiekszenie):
        """Ścinanie paralaksy złożone z lekkim powiększeniem wokół środka."""
        sw = r.width() / float(max(1, self._srodek_w))
        sh = r.height() / float(max(1, self._srodek_h))
        p.translate(r.center().x(), r.center().y())
        p.scale(sw * powiekszenie, sh * powiekszenie)
        p.translate(-self._srodek_w * 0.5, -self._srodek_h * 0.5)
        scinanie = QTransform(1.0, 0.0, -dx * self._b, 1.0,
                              -self._zapas_px - dx * self._a, 0.0)
        p.setWorldTransform(scinanie * p.worldTransform())

    def _rysuj_start(self, p, r, alfa, powiekszenie):
        pix = self._start_pix
        if pix is None:
            st.tlo_sceny(p, r)
            return
        p.setOpacity(alfa)
        cel = QRectF(r.center().x() - r.width() * 0.5 * powiekszenie,
                     r.center().y() - r.height() * 0.5 * powiekszenie,
                     r.width() * powiekszenie, r.height() * powiekszenie)
        p.drawPixmap(cel, pix, QRectF(pix.rect()))
        p.setOpacity(1.0)

    def paintEvent(self, _zdarzenie):
        zegar = time.perf_counter()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        r = QRectF(self.rect())
        if self._scena is None:
            self._rysuj_start(p, r, 1.0, 1.0)       # przed wypiekiem nic się nie rusza
            p.end()
            return
        t = self._czas()
        dx = self._przesuniecie_w(t)
        u = self._zejscie.teraz() if self._faza == "ladowanie" else 0.0
        alfa = 1.0 - u
        if self._pod is not None and u > 0.0:
            p.drawPixmap(r, self._pod, QRectF(self._pod.rect()))
        p.save()
        self._kamera(p, r, dx, 1.0 + (POWIEKSZENIE_LADOWANIA - 1.0) * u)
        p.setOpacity(alfa)
        p.drawPixmap(0, 0, self._scena)
        if self._trasy_pix is not None:
            p.drawPixmap(0, 0, self._trasy_pix)
        for trasa in self._zapalane:                  # rozbłysk nowej trasy
            z = max(0.0, min(1.0, trasa["zapal"].teraz()))
            if trasa["pix"] is not None:
                p.setOpacity(alfa * z)
                p.drawPixmap(trasa["obrys"].topLeft(), trasa["pix"])
            punkty = trasa["punkty"] or ()
            if punkty:
                i = min(len(punkty) - 1, int(z * (len(punkty) - 1)))
                p.setOpacity(alfa * (1.0 - z * z))
                st.punkt_swiatla(p, punkty[i], PROMIEN_CZOLA_PRZELOTU * trasa["skale"][i],
                                 BARWA_TRASY_PRZELOTU, 100)
                st.punkt_swiatla(p, punkty[i], 1.4 * trasa["skale"][i],
                                 QColor(236, 255, 255), 150)
        p.restore()
        p.setOpacity(alfa)
        wyk = self._rejon._wykonczenie()
        p.drawPixmap(r, wyk, QRectF(wyk.rect()))
        p.setOpacity(1.0)
        e = self._wejscie.teraz()
        if e < 0.999:
            self._rysuj_start(p, r, 1.0 - e, 1.0 + (POWIEKSZENIE_STARTU - 1.0) * e)
        p.end()
        self._odnotuj_klatke((time.perf_counter() - zegar) * 1000.0)

    def _odnotuj_klatke(self, ms):
        """Klatka droższa niż sufit przez kilkanaście klatek z rzędu — komputer
        nie wyrabia i przelot gaśnie; zostaje sam postęp na kompasie."""
        self._koszt_klatki = (self._koszt_klatki * 0.8 + float(ms) * 0.2
                              if self._koszt_klatki else float(ms))
        if self._koszt_klatki > SUFIT_PRZELOTU_MS:
            self._drogie += 1
            if self._drogie >= KLATEK_PRZELOTU_DO_DECYZJI and self._faza == "lot":
                QTimer.singleShot(0, self.przerwij)
        else:
            self._drogie = 0


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    def scena(nazwa, dzien, stan_mapy="zwykly", stan_kartki="zwykla", szer=980, wys=620,
              strona="przod", odkryte=()):
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
        mapa.ustaw_odkryte(odkryte)
        mapa.ustaw_kotwice_kartki(QPointF(kartka.x() + 8, kartka.y() + 26),
                                  QRectF(kartka.geometry()))
        kartka.ustaw_dzien(dzien)
        kartka.ustaw_stan(stan_kartki)
        kartka.ustaw_strone(strona)

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
