#!/usr/bin/env python3
"""Zgodność: silnik wyciągnięty (web/silnik/pmt_silnik.py) daje WYNIK IDENTYCZNY jak PMT_Delegacje.py.
Uruchamiaj:  python zgodnosc_silnika.py oryginal|wyciag  > wynik.json   (potem porównaj pliki)"""
import sys, os, json, importlib, tempfile, warnings
warnings.filterwarnings("ignore")
tryb = sys.argv[1]
os.environ["HOME"] = tempfile.mkdtemp(prefix="pmt_home_")      # puste cache'e: żadnych śladów z innych przebiegów
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
RAZEM = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if tryb == "oryginal":
    sys.path.insert(0, RAZEM); S = importlib.import_module("PMT_Delegacje")
else:
    sys.path.insert(0, os.path.join(RAZEM, "web", "silnik")); S = importlib.import_module("pmt_silnik")
# bez sieci: dystans drogowy z formuły (jak program offline) — ten sam mechanizm w obu wariantach
def _brak_sieci(*a, **k): raise OSError("test bez sieci")
S.urllib.request.urlopen = _brak_sieci
def dane_dnia(d):
    return {"data": d.data.isoformat(), "suma": round(d.suma, 2) if hasattr(d, "suma") else None,
            "etapy": [[e.skad, e.dokad, e.godz_wyj, e.godz_przyj, round(e.kwota, 2)] for e in d.etapy]}
wyniki = {}
PRZYPADKI = [
    ("wrzesien_650km_wieczory", 3095.26, "Warszawa", 52.2297, 21.0122, "mazowieckie", 2026, 9, "90010112345", 1.15, "wieczor"),
    ("maly_dzien", 140.54, "Warszawa", 52.2297, 21.0122, "mazowieckie", 2026, 9, "90010112345", 1.15, "tydzien"),
    ("silnik_maly", 1500.00, "Lublin", 51.2465, 22.5684, "lubelskie", 2026, 10, "85050554321", 0.89, "tydzien"),
]
for nazwa, kwota, miasto, lat, lng, woj, rok, mies, pesel, stawka, tryb_pracy in PRZYPADKI:
    if tryb_pracy == "wieczor": S.ustaw_tryb_pracy("wieczor")
    else: S.ustaw_tryb_pracy("tydzien")
    dni_rob = S.pobierz_dni_robocze(rok, mies)
    wyn = S.generuj_trasy(kwota, miasto, lat, lng, woj, dni_rob, pesel, stawka)
    wyniki[nazwa] = {"liczba_dni": len(wyn), "dni": [dane_dnia(d) for d in wyn],
                     "suma": round(sum(d.suma for d in wyn), 2),
                     "kwota_niepelna": bool(getattr(wyn, "kwota_niepelna", False)),
                     "dokumenty": S.ile_dokumentow(kwota)}
json.dump(wyniki, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
