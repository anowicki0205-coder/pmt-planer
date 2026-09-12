# -*- coding: utf-8 -*-
"""Dane przykładowe i uproszczony silnik prototypu.

To NIE jest silnik z programu — liczy z grubsza, ale spójnie, żeby ekran
reagował na zmianę kwoty tak, jak będzie reagował docelowo. Wszystkie dane
osobowe są wymyślone.
"""
import calendar
import datetime as _dt
from dataclasses import dataclass, field

STAWKA = 0.8935                # zł za kilometr
MNOZNIK_MIN = 1.15
KWOTA_MIN = 50.0

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

# Stałe pętle dzienne: (nazwa dnia roboczego, lista przystanków bez bazy)
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

def oblicz_miesiac(kwota_zl, rok=2026, miesiac=9, tryb="Tydzień", wolne=()):
    """Zwraca listę dni miesiąca (wszystkich), z wypełnionymi trasami tam,
    gdzie starczyło kwoty. Rozkłada kwotę na kolejne dni robocze."""
    kwota_zl = max(0.0, float(kwota_zl or 0))
    ile = calendar.monthrange(rok, miesiac)[1]
    wszystkie = {d: Dzien(_dt.date(rok, miesiac, d), wolny=True) for d in range(1, ile + 1)}
    for d in wolne:
        if d in wszystkie:
            wszystkie[d].wylaczony = True
    if kwota_zl < KWOTA_MIN:
        return [wszystkie[d] for d in range(1, ile + 1)]

    kandydaci = [d for d in dni_robocze(rok, miesiac, tryb) if d.day not in wolne]
    # dni rozłożone równomiernie po miesiącu, a nie sklejone na początku
    km_budzet = kwota_zl / STAWKA
    wybrane = []
    i = 0
    zostalo = km_budzet
    krok = max(1, len(kandydaci) // 8)
    while i < len(kandydaci) and zostalo > 40:
        data = kandydaci[i]
        petla = PETLE[len(wybrane) % len(PETLE)]
        km = km_petli(petla)
        if km > zostalo:
            # skracamy pętlę, zamiast nadmuchiwać mnożnik
            while len(petla) > 1 and km_petli(petla[:-1]) > zostalo * 0.55:
                petla = petla[:-1]
            km = km_petli(petla)
            if km > zostalo * 1.35:
                break
        zostalo -= km
        d = wszystkie[data.day]
        d.wolny = False
        d.przystanki = list(petla)
        d.km = round(km, 1)
        d.kwota = round(km * STAWKA, 2)
        godz_start = 7 + (len(wybrane) % 2)
        d.start = f"{godz_start:02d}:20"
        d.koniec = f"{godz_start + 5 + len(petla) // 2:02d}:41"
        wybrane.append(d)
        i += krok
    if wybrane:
        # domknięcie do pełnej kwoty co do grosza na ostatnim dniu
        suma = sum(d.kwota for d in wybrane)
        roznica = round(kwota_zl - suma, 2)
        wybrane[-1].kwota = round(wybrane[-1].kwota + roznica, 2)
        wybrane[-1].km = round(wybrane[-1].kwota / STAWKA, 1)
        wybrane[0].podpisany = True
    return [wszystkie[d] for d in range(1, ile + 1)]

def podsumowanie(dni):
    w_trasie = [d for d in dni if not d.wolny]
    return {
        "dni": len(w_trasie),
        "dni_wszystkie": len(dni),
        "km": round(sum(d.km for d in w_trasie), 1),
        "kwota": round(sum(d.kwota for d in w_trasie), 2),
        "postoje": sum(d.postoje for d in w_trasie),
    }

def nazwa_miesiaca(miesiac):
    return MIESIACE_PL[miesiac - 1]

def zl(wartosc, grosze=True):
    s = f"{wartosc:,.2f}" if grosze else f"{wartosc:,.0f}"
    return s.replace(",", " ").replace(".", ",")

if __name__ == "__main__":
    dni = oblicz_miesiac(1850)
    p = podsumowanie(dni)
    print("dni w trasie:", p["dni"], "| km:", p["km"], "| kwota:", zl(p["kwota"]), "zł")
    for d in dni:
        if not d.wolny:
            print(" ", d.etykieta, d.km, "km", zl(d.kwota), "zł", "->", " → ".join(d.trasa))
