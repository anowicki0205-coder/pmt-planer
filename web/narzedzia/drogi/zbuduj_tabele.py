#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Buduje tabelę dróg między miejscowościami z bazy silnika (drogi.bin) na podstawie lokalnego serwera OSRM (dane OpenStreetMap).

Dla każdej pary miejscowości odległych w linii prostej o najwyżej PROMIEN km zapisuje drogę w km i czas jazdy samochodem (OSRM, profil „car”, bez korków).
Plik czyta silnik (PMT_Delegacje.wczytaj_tabele_drog): zamiast „linia prosta × 1,28” daje realne kilometry, a z czasów — względną prędkość każdego odcinka
(autostrada szybciej, miasto wolniej), przy zachowaniu tej samej średniej prędkości (patrz PREDKOSC_ODNIESIENIA).

Uruchamia go zadanie GitHub Actions „Drogi OSRM” (.github/workflows/drogi-osrm.yml) — tylko stdlib Pythona:
    python3 zbuduj_tabele.py --osrm http://127.0.0.1:5000 --miasta miasta.json --wyjscie ../../silnik/drogi.bin --raport RAPORT.txt

FORMAT PLIKU (little-endian):
    4 B   'PMTD'      u8 wersja (=1)   u32 N (liczba miejscowości)   f32 promień (km)   f32 prędkość odniesienia (km/h)
    N ×   i32 lat×1e4, i32 lng×1e4            (współrzędne dokładnie z miasta.json, w kolejności indeksów)
    N ×   u16 k, potem k × (u16 j, u16 km×10, u16 czas w jednostkach 10 s)     — tylko pary i<j; j rosnąco
"""
import argparse, json, math, statistics, struct, sys, time, urllib.error, urllib.parse, urllib.request

WERSJA = 1
PROMIEN_DOMYSLNY_KM = 200.0
BLOK_ZRODEL = 25


def polilinia(punkty, precyzja=5):
    """Kodowanie „encoded polyline” (to samo co w Google/OSRM): krótsze adresy zapytań niż „lon,lat;lon,lat;…”. punkty: [(lat, lng), …]."""
    mnoznik = 10 ** precyzja
    wynik, plat, plng = [], 0, 0
    def liczba(v):
        v = ~(v << 1) if v < 0 else (v << 1)
        s = ""
        while v >= 0x20:
            s += chr((0x20 | (v & 0x1f)) + 63)
            v >>= 5
        return s + chr(v + 63)
    for lat, lng in punkty:
        la, lo = int(round(lat * mnoznik)), int(round(lng * mnoznik))
        wynik.append(liczba(la - plat)); wynik.append(liczba(lo - plng))
        plat, plng = la, lo
    return "".join(wynik)


def linia_prosta_km(lat1, lng1, lat2, lng2):
    p = math.pi / 180.0
    x = (lng2 - lng1) * p * math.cos((lat1 + lat2) * p / 2.0)
    y = (lat2 - lat1) * p
    return 6371.0 * math.hypot(x, y)


class Osrm:
    def __init__(self, adres, proby=4, limit=300):
        self.adres, self.proby, self.limit = adres.rstrip("/"), proby, limit

    def tabela(self, zrodla, cele):
        """zrodla, cele: [(lat, lng)]; → (odleglosci_m, czasy_s) jako listy list (None = brak trasy)."""
        pkt = list(zrodla) + list(cele)
        s = ";".join(str(i) for i in range(len(zrodla)))
        d = ";".join(str(len(zrodla) + i) for i in range(len(cele)))
        url = "%s/table/v1/driving/polyline(%s)?sources=%s&destinations=%s&annotations=duration,distance" % (
            self.adres, urllib.parse.quote(polilinia(pkt), safe=""), s, d)
        ostatni = None
        for nr in range(self.proby):
            try:
                with urllib.request.urlopen(url, timeout=self.limit) as r:
                    dane = json.loads(r.read().decode("utf-8"))
                if dane.get("code") != "Ok":
                    raise RuntimeError("OSRM: %s %s" % (dane.get("code"), dane.get("message", "")))
                return dane["distances"], dane["durations"]
            except (urllib.error.URLError, RuntimeError, ValueError, TimeoutError) as e:
                ostatni = e
                time.sleep(2 * (nr + 1))
        raise RuntimeError("zapytanie do OSRM nie powiodło się: %s" % ostatni)


def zbuduj(miasta, osrm, promien, log=print):
    """miasta: [{'n','lat','lng'}…] w kolejności z pliku (indeksy tabeli = indeksy listy). → słownik z parami i statystykami."""
    N = len(miasta)
    lat = [m["lat"] for m in miasta]; lng = [m["lng"] for m in miasta]
    # kolejność przetwarzania: miejscowości blisko siebie w jednym bloku (mała suma celów)
    kolejnosc = sorted(range(N), key=lambda i: (int(lat[i] / 0.3), lng[i]))
    pary = {}                      # i<j -> (km, sekundy)
    brak = 0
    t0 = time.time()
    for b in range(0, N, BLOK_ZRODEL):
        blok = kolejnosc[b:b + BLOK_ZRODEL]
        cele = [j for j in range(N) if any(linia_prosta_km(lat[i], lng[i], lat[j], lng[j]) <= promien for i in blok)]
        odl, czas = osrm.tabela([(lat[i], lng[i]) for i in blok], [(lat[j], lng[j]) for j in cele])
        for a, i in enumerate(blok):
            for c, j in enumerate(cele):
                if j <= i:
                    continue                      # parę i<j liczy blok, w którym i jest źródłem (symetria dróg przyjęta)
                if linia_prosta_km(lat[i], lng[i], lat[j], lng[j]) > promien:
                    continue
                m, s = odl[a][c], czas[a][c]
                if m is None or s is None:
                    brak += 1
                    continue
                pary[(i, j)] = (float(m) / 1000.0, float(s))
        if (b // BLOK_ZRODEL) % 10 == 0:
            log("  blok %d/%d, par %d, %.0f s" % (b // BLOK_ZRODEL + 1, (N + BLOK_ZRODEL - 1) // BLOK_ZRODEL, len(pary), time.time() - t0))
    return {"pary": pary, "brak": brak, "N": N, "lat": lat, "lng": lng}


def statystyki(wynik, miasta, promien):
    pary, lat, lng = wynik["pary"], wynik["lat"], wynik["lng"]
    krzywizna, predkosci, podejrzane = [], [], 0
    for (i, j), (km, s) in pary.items():
        prosta = linia_prosta_km(lat[i], lng[i], lat[j], lng[j])
        if prosta >= 5.0:
            krzywizna.append(km / prosta)
        if 30.0 <= prosta <= 120.0 and s > 0:
            predkosci.append(km / (s / 3600.0))
        if prosta >= 5.0 and (km < prosta * 0.97 or km > prosta * 3.5):
            podejrzane += 1
    return {"krzywizna": krzywizna, "predkosci": predkosci, "podejrzane": podejrzane}


def kwantyle(w, q=(0.05, 0.25, 0.5, 0.75, 0.95)):
    if not w:
        return []
    s = sorted(w)
    return [s[min(len(s) - 1, int(round(x * (len(s) - 1))))] for x in q]


def zapisz(wynik, sciezka, promien, predkosc_odniesienia):
    N, pary, lat, lng = wynik["N"], wynik["pary"], wynik["lat"], wynik["lng"]
    sasiedzi = [[] for _ in range(N)]
    for (i, j), (km, s) in pary.items():
        sasiedzi[i].append((j, min(65535, int(round(km * 10))), min(65535, int(round(s / 10.0)))))
    with open(sciezka, "wb") as f:
        f.write(b"PMTD" + struct.pack("<BIff", WERSJA, N, promien, predkosc_odniesienia))
        for i in range(N):
            f.write(struct.pack("<ii", int(round(lat[i] * 1e4)), int(round(lng[i] * 1e4))))
        for i in range(N):
            lista = sorted(sasiedzi[i])
            f.write(struct.pack("<H", len(lista)))
            for j, km10, t10 in lista:
                f.write(struct.pack("<HHH", j, km10, t10))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--osrm", default="http://127.0.0.1:5000")
    ap.add_argument("--miasta", default="miasta.json")
    ap.add_argument("--wyjscie", default="drogi.bin")
    ap.add_argument("--raport", default="RAPORT.txt")
    ap.add_argument("--promien", type=float, default=PROMIEN_DOMYSLNY_KM)
    ap.add_argument("--probka", type=int, default=0, help="tylko tyle pierwszych miejscowości (próba potoku)")
    a = ap.parse_args(argv)
    with open(a.miasta, encoding="utf-8") as f:
        miasta = json.load(f)
    if a.probka:
        miasta = miasta[:a.probka]
    print("miejscowości:", len(miasta), "promień:", a.promien, "km")
    t0 = time.time()
    wynik = zbuduj(miasta, Osrm(a.osrm), a.promien)
    st = statystyki(wynik, miasta, a.promien)
    kw_k, kw_v = kwantyle(st["krzywizna"]), kwantyle(st["predkosci"])
    vref = statystyka_mediany(st["predkosci"])
    razem = len(wynik["pary"]) + wynik["brak"]
    zapisz(wynik, a.wyjscie, a.promien, vref)
    linie = [
        "TABELA DRÓG (OSRM, profil car, dane OpenStreetMap) — raport z budowy",
        "miejscowości: %d, promień par: %.0f km, par zapisanych: %d, bez trasy: %d (%.2f %%), czas budowy: %.0f s" % (
            wynik["N"], a.promien, len(wynik["pary"]), wynik["brak"], 100.0 * wynik["brak"] / max(1, razem), time.time() - t0),
        "droga/linia prosta (pary ≥ 5 km), kwantyle 5/25/50/75/95 %%: %s" % " ".join("%.3f" % x for x in kw_k),
        "prędkość km/h (pary 30–120 km), kwantyle 5/25/50/75/95 %%: %s" % " ".join("%.1f" % x for x in kw_v),
        "prędkość odniesienia (mediana, zapisana w pliku): %.2f km/h" % vref,
        "pary podejrzane (droga < 0,97 prostej albo > 3,5 prostej): %d" % st["podejrzane"],
    ]
    # kontrola przykładowych par po nazwach (jeśli obie miejscowości są w bazie)
    po_nazwie = {}
    for i, m in enumerate(miasta):
        po_nazwie.setdefault(m["n"], i)
    for a1, b1 in (("Radom", "Warszawa"), ("Kielce", "Radom"), ("Lublin", "Puławy"), ("Zakopane", "Nowy Targ"), ("Gdańsk", "Gdynia"), ("Poznań", "Konin")):
        if a1 in po_nazwie and b1 in po_nazwie:
            i, j = sorted((po_nazwie[a1], po_nazwie[b1]))
            if (i, j) in wynik["pary"]:
                km, s = wynik["pary"][(i, j)]
                prosta = linia_prosta_km(wynik["lat"][i], wynik["lng"][i], wynik["lat"][j], wynik["lng"][j])
                linie.append("  %s – %s: %.1f km drogą (prosta %.1f km, ×%.2f), %.0f min" % (a1, b1, km, prosta, km / prosta, s / 60.0))
    tekst = "\n".join(linie) + "\n"
    print(tekst)
    with open(a.raport, "w", encoding="utf-8") as f:
        f.write(tekst)
    # kontrole rozsądku: lepiej przerwać zadanie niż wypuścić zepsutą tabelę
    problemy = []
    if len(wynik["pary"]) < 50 and not a.probka:
        problemy.append("za mało par")
    if kw_k and not (1.05 <= kw_k[2] <= 1.6):
        problemy.append("mediana droga/prosta %.3f poza 1,05–1,6" % kw_k[2])
    if kw_v and not (35.0 <= vref <= 110.0):
        problemy.append("prędkość odniesienia %.1f poza 35–110 km/h" % vref)
    if razem and wynik["brak"] / razem > 0.05 and not a.probka:
        problemy.append("zbyt wiele par bez trasy (%.1f %%)" % (100.0 * wynik["brak"] / razem))
    if problemy:
        print("BŁĄD:", "; ".join(problemy), file=sys.stderr)
        return 1
    return 0


def statystyka_mediany(w):
    return statistics.median(w) if w else 65.0


if __name__ == "__main__":
    sys.exit(main())
