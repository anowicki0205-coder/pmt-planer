#!/usr/bin/env python3
"""Przygotowuje listę sklepów do DANYCH POKAZOWYCH (przykład na pierwsze uruchomienie): czyta .xlsx (kolumny: sieć, miasto, ulica, region) i zapisuje
oczyszczony plik CSV (Sieć;Miasto;Ulica), który zjada narzedzia/zbuduj_przyklad.js. Wymaga openpyxl (pip install openpyxl).
Czyszczenie: tylko województwo mazowieckie, usunięte wiersze testowe i egzotyczne nazwy sieci (poniżej 3 sklepów, „schengen” itd.), spacje i tabulatory poprawione,
powtórzone adresy scalone, z każdego miasta do 10 sklepów na przemian z różnych sieci (plan pokazowy ma być zróżnicowany i szybki do ułożenia).
Użycie: python narzedzia/przygotuj_liste_przykladu.py lok_test.xlsx lista_przykladu.csv"""
import csv, re, sys
from collections import Counter
from openpyxl import load_workbook

zrodlo, cel = sys.argv[1], sys.argv[2]
ws = load_workbook(zrodlo, read_only=True, data_only=True).active
wiersze = list(ws.iter_rows(values_only=True))
naglowek = [str(c or '').strip().lower() for c in wiersze[0]]
i_siec, i_miasto, i_ulica = naglowek.index('siec'), naglowek.index('miasto'), naglowek.index('ulica')
i_region = naglowek.index('lokalizacja_region') if 'lokalizacja_region' in naglowek else None
sp = lambda t: re.sub(r'\s+', ' ', str(t or '').replace('\t', ' ')).strip()
POPRAWKI = {'Auchan Supermarket': 'Auchan'}
dane = []
for w in wiersze[1:]:
    siec, miasto, ulica = sp(w[i_siec]), sp(w[i_miasto]), sp(w[i_ulica])
    if not (siec and miasto and ulica): continue
    if i_region is not None and not sp(w[i_region]).lower().startswith('mazowiecki'): continue
    siec = POPRAWKI.get(siec, siec)
    if siec.lower() == 'test' or 'schengen' in siec.lower(): continue
    dane.append((siec, miasto, ulica))
ile = Counter(s for s, _, _ in dane)
dane = [d for d in dane if ile[d[0]] >= 3]
# ten sam adres bywa w pliku wiele razy (kolejne zlecenia) — do pokazu zostaje raz; z każdego miasta po kilka sklepów na przemian z różnych sieci,
# żeby pokazowy plan był zróżnicowany (różne miejscowości i sieci), a nie 24 razy ta sama Biedronka
widziane, po_miastach = set(), {}
for siec, miasto, ulica in dane:
    klucz = (siec.lower(), miasto.lower(), ulica.lower())
    if klucz in widziane: continue
    widziane.add(klucz); po_miastach.setdefault(miasto, {}).setdefault(siec, []).append((siec, miasto, ulica))
NA_MIASTO = 10
dane = []
for miasto, sieci in po_miastach.items():
    kolejki = [list(v) for v in sieci.values()]; wybrane = []
    while kolejki and len(wybrane) < NA_MIASTO:
        for k in list(kolejki):
            if k and len(wybrane) < NA_MIASTO: wybrane.append(k.pop(0))
            if not k: kolejki.remove(k)
    dane.extend(wybrane)
with open(cel, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';'); w.writerow(['Sieć', 'Miasto', 'Ulica']); w.writerows(dane)
print(f'{cel}: {len(dane)} sklepów (z {len(wiersze) - 1}), sieci: {dict(Counter(s for s, _, _ in dane).most_common(12))}')
