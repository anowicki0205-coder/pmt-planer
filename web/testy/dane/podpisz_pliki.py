#!/usr/bin/env python3
"""Podpisuje (testowo) prawdziwe PDF-y wygenerowane przez aplikację — do testów całego obiegu w przeglądarce.
Użycie: python podpisz_pliki.py <katalog z PDF-ami> <katalog wyjściowy> <plan.json>
plan.json: { "nazwa.pdf": "jan" | "anna" | "zmieniony" | "dopisek" | "niepodpisany" | "xades" | "ecdsa" }   (brak wpisu = „jan”)
  jan = poprawny podpis Jana Testowego (PESEL 90010112349), anna = podpis innej osoby, zmieniony = zmiana bajtu po podpisie, dopisek = dane dopisane po podpisie,
  niepodpisany = plik bez zmian, xades = osobny plik <nazwa>.xades (PDF nie jest kopiowany), ecdsa = podpis kluczem eliptycznym.
Wymaga: pip install pyhanko lxml cryptography."""
import json, os, sys
from podpisy_lib import *

wej, wyj, plan = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3], encoding='utf8')) if len(sys.argv) > 3 else {}
os.makedirs(wyj, exist_ok=True)
jan, k_jan, c_jan = podpisujacy('Jan', 'Testowy', '90010112349'); anna, _, _ = podpisujacy('Anna', 'Kowalska', '85010100000'); jan_ec, _, _ = podpisujacy('Jan', 'Testowy', '90010112349', ec_klucz=True)
for f in sorted(os.listdir(wej)):
    if not f.lower().endswith('.pdf'): continue
    dane = open(os.path.join(wej, f), 'rb').read(); co = plan.get(f, 'jan'); wynik = None
    if co == 'jan': wynik = podpisz_pdf(dane, jan)
    elif co == 'anna': wynik = podpisz_pdf(dane, anna)
    elif co == 'ecdsa': wynik = podpisz_pdf(dane, jan_ec)
    elif co == 'zmieniony': z = bytearray(podpisz_pdf(dane, jan)); z[len(dane) // 2] ^= 1; wynik = bytes(z)
    elif co == 'dopisek': wynik = podpisz_pdf(dane, jan) + b'\n% dopisek po podpisaniu\n'
    elif co == 'niepodpisany': wynik = dane
    elif co == 'xades': open(os.path.join(wyj, f + '.xades'), 'wb').write(xades(dane, k_jan, c_jan, nazwa=f)); continue
    open(os.path.join(wyj, f), 'wb').write(wynik)
print('podpisano', len(os.listdir(wyj)), 'plików')
