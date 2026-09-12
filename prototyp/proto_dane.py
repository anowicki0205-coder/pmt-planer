# -*- coding: utf-8 -*-
"""Dane przykładowe i uproszczony silnik prototypu.

To NIE jest silnik z programu — liczy z grubsza, ale spójnie, żeby ekran
reagował na zmianę kwoty tak, jak będzie reagował docelowo. Wszystkie dane
osobowe są wymyślone.

Rozkład kwoty trzyma się reguły z PMT_Delegacje.py: jeden dzień pracy to
najwyżej MAX_KWOTA_DNIA, więc liczba dni to sufit z kwoty podzielonej przez
limit, a kwota rozkłada się na te dni równo — nie rozsmarowuje się na kolejne
dni po kilkaset złotych mniej, niż dzień jest w stanie udźwignąć.
"""
import calendar
import datetime as _dt
import math
from dataclasses import dataclass, field

STAWKA = 0.8935                # zł za kilometr
SREDNIA_PREDKOSC = 65.0        # km/h — z niej wychodzą godziny dnia
MNOZNIK_MIN = 1.15
KWOTA_MIN = 50.0
MIN_KWOTA = KWOTA_MIN          # nazwa jak w PMT_Delegacje.py
# Limit jednego dnia pracy — dokładnie jak w PMT_Delegacje.py. Decyduje
# o liczbie dni: kwota / limit, zaokrąglone w górę.
MAX_KWOTA_DNIA = 587.19
# Sufit JEDNEGO DOKUMENTU (jednego PDF) — to zupełnie inna wielkość niż sufit
# dnia. Jeden dokument obejmuje kilka dni; sufit dnia mówi, ile da się
# przejechać w ciągu jednej doby, a sufit dokumentu, ile dni zmieści się na
# jednym poleceniu wyjazdu. Obie nazwy i wartości jak w PMT_Delegacje.py.
MAX_KWOTA_DOKUMENTU = 986.34
MAX_ETAPOW_DOKUMENTU = 30      # ile wierszy trasy mieści strona A4
# Doba pracy: posiłek + jazda + postoje. Każdy przystanek zjada czas, więc
# im więcej wizyt, tym mniej kilometrów mieści się w dniu.
LIMIT_CZASU_MINUTY = 8 * 60
PRZERWA_JEDZENIE_MIN = 30
POSTOJ_SREDNI_MIN = 17         # w programie 12–23 min na miejscowość
# Dzień celuje w 85% limitu, a nie w sam limit — tak liczy dni prawdziwy
# program (ceil(kwota / (MAX_KWOTA_DNIA * 0.85))). Zapas zostaje na to, że
# realna trasa wychodzi dłuższa niż szacunek.
ZAPAS_DNIA = 0.85
MAX_PRZYSTANKOW = 14           # sufit długości trasy dnia
KARA_POWTORKI = 12.0           # km "kary" za powtórzony przystanek w trasie

PRACOWNIK = "Anna Nowak"
STANOWISKO = "merchandiser"
ADRES = "ul. Przykładowa 5/58, 03-580 Warszawa"
BAZA = "Warszawa"
MENEDZER = "(z pliku menedzer.txt)"
SIECI = ["Żabka", "Biedronka", "Lidl", "Stokrotka"]

MIESIACE_PL = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec",
               "sierpień", "wrzesień", "październik", "listopad", "grudzień"]
DNI_PL = ["pn", "wt", "śr", "cz", "pt", "so", "nd"]

# Miasta w układzie znormalizowanym 0..1 względem obszaru mapy.
# Warszawa jest bazą i leży mniej więcej w środku-lewo.
MIASTA = {
    "Warszawa":      (0.30, 0.62),
    "Wołomin":       (0.46, 0.44),
    "Radzymin":      (0.53, 0.35),
    "Wyszków":       (0.66, 0.40),
    "Otwock":        (0.47, 0.83),
    "Piaseczno":     (0.28, 0.86),
    "Grójec":        (0.13, 0.80),
    "Legionowo":     (0.33, 0.35),
    "Mińsk Maz.":    (0.62, 0.66),
    "Siedlce":       (0.86, 0.60),
    "Garwolin":      (0.66, 0.88),
    "Płońsk":        (0.18, 0.22),
    "Ciechanów":     (0.28, 0.12),
    "Sochaczew":     (0.06, 0.52),
    "Żyrardów":      (0.08, 0.66),
    "Radom":         (0.40, 0.97),
    "Kozienice":     (0.58, 0.95),
    "Nowy Dwór":     (0.24, 0.30),
}

# Stałe pętle dzienne: lista przystanków bez bazy. To materiał wyjściowy —
# silnik skraca je i wydłuża tak, żeby długość trasy trafiła w kilometry dnia.
PETLE = [
    ["Wołomin", "Radzymin", "Wyszków", "Otwock", "Piaseczno"],
    ["Żyrardów", "Sochaczew", "Grójec"],
    ["Legionowo", "Nowy Dwór", "Płońsk", "Ciechanów"],
    ["Mińsk Maz.", "Siedlce", "Garwolin"],
    ["Piaseczno", "Grójec", "Radom"],
    ["Otwock", "Kozienice", "Garwolin", "Mińsk Maz."],
    ["Radzymin", "Wyszków", "Wołomin"],
    ["Nowy Dwór", "Legionowo"],
]

@dataclass
class Dzien:
    data: _dt.date
    przystanki: list = field(default_factory=list)   # nazwy miast, bez bazy
    km: float = 0.0
    kwota: float = 0.0
    start: str = "07:20"
    koniec: str = "15:41"
    wolny: bool = False          # brak trasy tego dnia
    wylaczony: bool = False      # użytkownik sam wyłączył ten dzień
    podpisany: bool = False
    dokument: int = 0            # numer polecenia wyjazdu, do którego trafia ten dzień

    @property
    def etykieta(self):
        return f"{DNI_PL[self.data.weekday()]} {self.data.day}"

    @property
    def postoje(self):
        return len(self.przystanki)

    @property
    def trasa(self):
        return [BAZA] + list(self.przystanki) + [BAZA]

    @property
    def czas(self):
        return f"{self.start}–{self.koniec}"

def _odleglosc(a, b):
    ax, ay = MIASTA[a]; bx, by = MIASTA[b]
    # przelicznik na kilometry dobrany tak, żeby dzienne trasy wychodziły realnie
    return (((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5) * 235.0

def km_petli(przystanki):
    punkty = [BAZA] + list(przystanki) + [BAZA]
    return sum(_odleglosc(punkty[i], punkty[i + 1]) for i in range(len(punkty) - 1))

def dni_robocze(rok, miesiac, tryb="Tydzień"):
    ile = calendar.monthrange(rok, miesiac)[1]
    dni = []
    for d in range(1, ile + 1):
        data = _dt.date(rok, miesiac, d)
        if tryb == "Tydzień" and data.weekday() >= 5:
            continue
        if tryb == "Weekendy" and data.weekday() < 5:
            continue
        dni.append(data)
    return dni

# ── rozkład kwoty ───────────────────────────────────────────────────────────

def _rozdziel_rowno(kwota_zl, ile_dni):
    """Dzieli kwotę na ile_dni części równych co do grosza.

    Suma części jest równa kwocie zaokrąglonej do grosza — bez domykania
    różnicy na ostatnim dniu. Reszta groszy trafia na pierwsze dni, więc
    dni różnią się najwyżej o grosz."""
    grosze = int(round(kwota_zl * 100))
    baza, reszta = divmod(grosze, ile_dni)
    return [(baza + (1 if i < reszta else 0)) / 100.0 for i in range(ile_dni)]

def _ile_dni(kwota_zl, limit_dnia, dostepnych):
    """Ile dni trzeba, żeby żaden nie przekroczył limitu dnia.

    Sufit z kwoty podzielonej przez limit dnia pomniejszony o zapas — przy
    1850 zł wychodzą 4 dni dla limitu 587,19 zł i 3 dni dla limitu 999 zł."""
    ile = max(1, math.ceil(round(kwota_zl / (limit_dnia * ZAPAS_DNIA), 9)))
    # równy podział mógłby po zaokrągleniu do grosza dobić ponad limit —
    # wtedy dokładamy dzień
    while ile < dostepnych and max(_rozdziel_rowno(kwota_zl, ile)) > limit_dnia:
        ile += 1
    return min(ile, dostepnych)

def _wybierz_dni(kandydaci, ile):
    """Dni rozłożone równomiernie po miesiącu, a nie sklejone na początku."""
    if ile >= len(kandydaci):
        return list(kandydaci)
    krok = len(kandydaci) / ile
    indeksy = sorted({int(i * krok) for i in range(ile)})
    i = 0
    while len(indeksy) < ile and i < len(kandydaci):
        if i not in indeksy:
            indeksy.append(i)
            indeksy.sort()
        i += 1
    return [kandydaci[i] for i in indeksy[:ile]]

# ── dobór trasy pod kilometry dnia ──────────────────────────────────────────

def _obrot(lista, ziarno):
    if not lista:
        return []
    k = ziarno % len(lista)
    return list(lista[k:]) + list(lista[:k])

def _start_trasy(cel_km, ziarno):
    """Pętla z PETLE skrócona do kroku, który nie przekracza celu.

    Co drugie okrążenie listy pętla idzie w odwrotną stronę, żeby w długim
    miesiącu dni nie powtarzały tej samej trasy."""
    petla = PETLE[ziarno % len(PETLE)]
    if (ziarno // len(PETLE)) % 2:
        petla = list(reversed(petla))
    najlepsza = []
    for k in range(1, len(petla) + 1):
        if km_petli(petla[:k]) <= cel_km:
            najlepsza = list(petla[:k])
        else:
            break
    if najlepsza:
        return najlepsza
    # nawet jeden przystanek z tej pętli jest za daleko — bierzemy miasto,
    # które samo trafia w cel najbliżej
    miasta = _obrot([m for m in MIASTA if m != BAZA], ziarno)
    return [min(miasta, key=lambda m: abs(km_petli([m]) - cel_km))]

def dobierz_trase(cel_km, ziarno=0):
    """Trasa, której długość jest możliwie bliska cel_km.

    Startuje od pętli z PETLE (skróconej do celu), a potem dokłada przystanki —
    także powtórzone i dalsze miasta — dopóki zbliżają trasę do celu. Żadnych
    mnożników: długość bierze się z prawdziwych odcinków."""
    if cel_km <= 1.0:
        return []
    trasa = _start_trasy(cel_km, ziarno)
    miasta = _obrot([m for m in MIASTA if m != BAZA], ziarno * 5)
    while len(trasa) < MAX_PRZYSTANKOW:
        blad = abs(km_petli(trasa) - cel_km)
        lepsza = None
        for m in miasta:
            kara = KARA_POWTORKI if m in trasa else 0.0
            for i in range(len(trasa) + 1):
                kand = trasa[:i] + [m] + trasa[i:]
                b = abs(km_petli(kand) - cel_km) + kara
                if b < blad - 1e-6:
                    blad = b
                    lepsza = kand
        if lepsza is None:
            break
        trasa = lepsza
    return trasa

def _hhmm(minuty):
    minuty = int(min(max(minuty, 0), 23 * 60 + 59))
    return f"{minuty // 60:02d}:{minuty % 60:02d}"

def _godziny_dnia(km, postoje, ziarno):
    start = 7 * 60 + 20 + (ziarno % 3) * 15
    praca = km / SREDNIA_PREDKOSC * 60.0 + postoje * 12
    return _hhmm(start), _hhmm(start + praca)

# ── silnik ──────────────────────────────────────────────────────────────────

def pojemnosc_dnia_km(postoje):
    """Ile kilometrów mieści się w jednej dobie przy takiej liczbie przystanków."""
    minuty = LIMIT_CZASU_MINUTY - PRZERWA_JEDZENIE_MIN - int(postoje) * POSTOJ_SREDNI_MIN
    return max(0.0, minuty / 60.0 * SREDNIA_PREDKOSC)

def pojemnosc_dnia_zl(postoje, limit_dnia=MAX_KWOTA_DNIA):
    """Sufit kwoty dnia: mniejsza z dwóch wartości — fizyczna i regulaminowa."""
    return round(min(pojemnosc_dnia_km(postoje) * STAWKA, float(limit_dnia)), 2)

def maks_kwota_miesiaca(rok=2026, miesiac=9, tryb="Tydzień", wolne=(),
                        limit_dnia=MAX_KWOTA_DNIA):
    """Górna granica kwoty miesiąca: liczba dni roboczych × realny sufit dnia."""
    wolne = set(wolne or ())
    dni = [d for d in dni_robocze(rok, miesiac, tryb) if d.day not in wolne]
    return round(len(dni) * pojemnosc_dnia_zl(4, limit_dnia), 2)

def _zbuduj_dzien(cel_zl, ziarno, limit_dnia):
    """Układa jeden dzień na zadaną kwotę, pilnując, żeby dało się go przejechać.

    Trasa jest dobierana pod kilometry, a potem sprawdzana czasem: jazda plus
    postoje plus posiłek nie mogą przekroczyć doby. Gdy nie mieści się, dzień
    jest skracany — bo przystanki zjadają czas tak samo jak kilometry."""
    cel_zl = float(cel_zl)
    for _ in range(8):
        km = cel_zl / STAWKA
        trasa = dobierz_trase(km, ziarno)
        mieszczace = pojemnosc_dnia_km(len(trasa))
        if km <= mieszczace + 0.5 and cel_zl <= float(limit_dnia) + 1e-9:
            return trasa, km, round(cel_zl, 2)
        cel_zl = min(cel_zl, mieszczace * STAWKA, float(limit_dnia)) * 0.995
        if cel_zl < KWOTA_MIN:
            break
    trasa = dobierz_trase(max(cel_zl, KWOTA_MIN) / STAWKA, ziarno)
    return trasa, max(cel_zl, KWOTA_MIN) / STAWKA, round(max(cel_zl, KWOTA_MIN), 2)

def oblicz_miesiac(kwota_zl, rok=2026, miesiac=9, tryb="Tydzień", wolne=(),
                   limit_dnia=MAX_KWOTA_DNIA, limit_dokumentu=MAX_KWOTA_DOKUMENTU):
    """Rozkłada kwotę miesiąca na dni, a potem dni na dokumenty.

    Dzień jest zapełniany do granicy fizycznej: tyle kilometrów, ile da się
    przejechać w dobie po odjęciu czasu postojów i posiłku. Dopiero gotowe dni
    grupują się w polecenia wyjazdu, a to grupowanie ogranicza sufit kwoty
    dokumentu i liczba wierszy mieszczących się na stronie."""
    kwota_zl = max(0.0, float(kwota_zl or 0))
    limit_dnia = max(1.0, float(limit_dnia or MAX_KWOTA_DNIA))
    ile = calendar.monthrange(rok, miesiac)[1]
    wolne = set(wolne or ())
    wszystkie = {d: Dzien(_dt.date(rok, miesiac, d), wolny=True) for d in range(1, ile + 1)}
    for d in wolne:
        if d in wszystkie:
            wszystkie[d].wylaczony = True
    wszystko = [wszystkie[d] for d in range(1, ile + 1)]
    if kwota_zl < KWOTA_MIN:
        return wszystko

    kandydaci = [d for d in dni_robocze(rok, miesiac, tryb) if d.day not in wolne]
    if not kandydaci:
        return wszystko

    # NAJPIERW DOKUMENTY, POTEM DNI. Sufit 986,34 zł dotyczy jednego polecenia
    # wyjazdu, a nie jednego dnia — jeden dokument obejmuje kilka dni. Liczymy
    # więc najpierw, ile poleceń trzeba wystawić, a dopiero w każdym z nich, na
    # ile dni rozłożyć jego kwotę, żeby dało się ją fizycznie przejechać.
    limit_dokumentu = max(1.0, float(limit_dokumentu or MAX_KWOTA_DOKUMENTU))
    sufit = pojemnosc_dnia_zl(4, limit_dnia)
    ile_dok = max(1, math.ceil((kwota_zl - 1e-9) / limit_dokumentu))
    kwoty_dok = _rozdziel_rowno(kwota_zl, ile_dok)

    plan = []                       # [(numer dokumentu, kwota dnia), ...]
    for nr_dok, kwota_dok in enumerate(kwoty_dok, start=1):
        ile_dni = max(1, math.ceil((kwota_dok - 1e-9) / sufit))
        for kwota_dnia in _rozdziel_rowno(kwota_dok, ile_dni):
            plan.append((nr_dok, kwota_dnia))
    if len(plan) > len(kandydaci):          # miesiąc się nie mieści — przycinamy
        plan = plan[:len(kandydaci)]

    daty = _wybierz_dni(kandydaci, len(plan))
    zbudowane = []
    for nr, (data, (nr_dok, kwota)) in enumerate(zip(daty, plan)):
        trasa, km, kwota_dnia = _zbuduj_dzien(kwota, nr, limit_dnia)
        d = wszystkie[data.day]
        d.wolny = False
        d.przystanki = trasa
        d.km = round(km, 1)
        d.kwota = kwota_dnia
        d.dokument = nr_dok
        d.start, d.koniec = _godziny_dnia(km, d.postoje, nr)
        zbudowane.append(d)

    # różnicę z zaokrągleń dokładamy do ostatniego dnia
    brak = round(kwota_zl - sum(d.kwota for d in zbudowane), 2)
    if zbudowane and abs(brak) >= 0.01:
        ost = zbudowane[-1]
        ost.kwota = round(ost.kwota + brak, 2)
        ost.km = round(ost.kwota / STAWKA, 1)

    if zbudowane:
        zbudowane[0].podpisany = True
    return wszystko

def pogrupuj_w_dokumenty(dni, limit_dokumentu=MAX_KWOTA_DOKUMENTU):
    """Przydziela dni do kolejnych poleceń wyjazdu.

    Jeden dokument zbiera tyle dni, ile zmieści się pod sufitem kwoty i na
    jednej stronie A4. Zwraca listę dokumentów."""
    limit_dokumentu = float(limit_dokumentu or MAX_KWOTA_DOKUMENTU)
    dokumenty = []
    biezacy = None
    for d in sorted([x for x in dni if not x.wolny], key=lambda x: x.data):
        wiersze = len(d.trasa) - 1
        if (biezacy is None
                or biezacy["kwota"] + d.kwota > limit_dokumentu + 1e-9
                or biezacy["wiersze"] + wiersze > MAX_ETAPOW_DOKUMENTU):
            biezacy = {"nr": len(dokumenty) + 1, "dni": [], "kwota": 0.0, "km": 0.0, "wiersze": 0}
            dokumenty.append(biezacy)
        biezacy["dni"].append(d)
        biezacy["kwota"] = round(biezacy["kwota"] + d.kwota, 2)
        biezacy["km"] = round(biezacy["km"] + d.km, 1)
        biezacy["wiersze"] += wiersze
        d.dokument = biezacy["nr"]
    return dokumenty

def dokumenty(dni, limit_dokumentu=MAX_KWOTA_DOKUMENTU):
    """Lista dokumentów dla już policzonych dni (bez zmiany przydziału)."""
    return pogrupuj_w_dokumenty(dni, limit_dokumentu)

def podsumowanie(dni):
    w_trasie = [d for d in dni if not d.wolny]
    return {
        "dni": len(w_trasie),
        "dni_wszystkie": len(dni),
        "km": round(sum(d.km for d in w_trasie), 1),
        "kwota": round(sum(d.kwota for d in w_trasie), 2),
        "postoje": sum(d.postoje for d in w_trasie),
        "dokumenty": (max((d.dokument for d in w_trasie), default=0)),
    }

def nazwa_miesiaca(miesiac):
    return MIESIACE_PL[miesiac - 1]

def zl(wartosc, grosze=True):
    s = f"{wartosc:,.2f}" if grosze else f"{wartosc:,.0f}"
    return s.replace(",", " ").replace(".", ",")

if __name__ == "__main__":
    KWOTY = [200, 587, 1850, 5000]
    LIMITY = [MAX_KWOTA_DNIA, 999.0]
    bledy = 0
    for limit in LIMITY:
        print(f"═══ limit dnia {zl(limit)} zł ═══  "
              f"(maks. miesiąca {zl(maks_kwota_miesiaca(limit_dnia=limit), False)} zł)")
        for kwota in KWOTY:
            dni = oblicz_miesiac(kwota, limit_dnia=limit)
            w_trasie = [d for d in dni if not d.wolny]
            p = podsumowanie(dni)
            suma = p["kwota"]
            naj = max((d.kwota for d in w_trasie), default=0.0)
            ok_suma = abs(suma - round(kwota, 2)) < 0.005
            ok_limit = naj <= limit + 1e-9
            bledy += (not ok_suma) + (not ok_limit)
            print(f"  {zl(kwota, False):>6} zł → dni: {p['dni']:>2} | "
                  f"kwoty: {', '.join(zl(d.kwota) for d in w_trasie)} | "
                  f"suma: {zl(suma)} zł  {'OK' if ok_suma else 'ŹLE'} | "
                  f"maks. dzień: {zl(naj)} zł  {'OK' if ok_limit else 'PONAD LIMIT'}")
            for d in w_trasie:
                roznica = km_petli(d.przystanki) - d.km
                print(f"      {d.etykieta:>5}  {zl(d.km, False):>5} km  {d.czas}  "
                      f"trasa {zl(km_petli(d.przystanki), False):>5} km "
                      f"({roznica:+.0f} km)  {' → '.join(d.trasa)}")
    print("BŁĘDY:", bledy)
