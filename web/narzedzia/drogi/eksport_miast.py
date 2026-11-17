#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eksportuje miejscowości z bazy silnika (współrzędne dokładnie takie, jakich używa silnik) do miasta.json —
wejście dla zbuduj_tabele.py. Uruchamiać po każdej zmianie bazy miejscowości (nowe miejscowości = nowa tabela dróg;
pary, których w tabeli nie ma, silnik liczy po staremu: linia prosta × 1,28).
    python3 web/narzedzia/drogi/eksport_miast.py"""
import json, os, sys
KOR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, KOR)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import PMT_Delegacje as P

baza = P.zaladuj_baze(52.0, 21.0)
widziane, lista = set(), []
for woj, miasta in baza.items():
    for m in miasta:
        k = (round(m.lat, 4), round(m.lng, 4))
        if k in widziane:
            continue
        widziane.add(k)
        lista.append({"n": m.n, "lat": round(m.lat, 4), "lng": round(m.lng, 4)})
lista.sort(key=lambda x: (x["lat"], x["lng"]))
wyj = os.path.join(os.path.dirname(__file__), "miasta.json")
with open(wyj, "w", encoding="utf-8") as f:
    json.dump(lista, f, ensure_ascii=False, separators=(",", ":"))
print("zapisano", wyj, "—", len(lista), "miejscowości")
