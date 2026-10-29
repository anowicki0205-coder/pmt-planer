#!/usr/bin/env python3
"""Pakuje aplikację do dystrybucja/PMT_Planer_web.zip (folder PMT_Planer_web/ w środku) — do testów u właściciela.
Pomija rzeczy poufne i techniczne: sekret.txt, menedzer.txt, node_modules, __pycache__, stare części składania (js/czesci), poprzednie paczki."""
import os, re, sys, zipfile
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
POMIN_KAT = {'node_modules', '__pycache__', '.git', 'dystrybucja', 'czesci', 'skany'}      # skany: sztuczne skany do testu podpisu odręcznego (ok. 40 MB, powstają z testy/dane/generuj_skany.py)
POMIN_PLIK = {'sekret.txt', 'menedzer.txt', 'pmt_kod.txt'}
POUFNE = re.compile(r'^(sekret|menedzer|pmt_kod)|\.(pfx|p12|pem|key|env)$|^\.env', re.I)      # także kopie typu sekret.txt.bak, menedzer.txt.txt, certyfikat.pfx, .env
WZORZEC_SEKRETU = re.compile(rb'PMT-\d{4}-[A-Za-z0-9]{24,}')      # kształt sekretu aplikacji (PMT-rok-28 znaków): paczka z takim napisem w treści się nie zbuduje
wyj = os.path.join(R, 'dystrybucja', 'PMT_Planer_web.zip'); os.makedirs(os.path.dirname(wyj), exist_ok=True)
n = 0
tmp = wyj + '.tmp'      # budujemy obok i podmieniamy na końcu: przerwana budowa nie zostawia pół-paczki
with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for kat, dirs, nazwy in os.walk(R):
        dirs[:] = sorted(d for d in dirs if d not in POMIN_KAT)
        for f in sorted(nazwy):
            if f in POMIN_PLIK or POUFNE.search(f) or f.endswith('.pyc'): continue
            sciezka = os.path.join(kat, f); rel = os.path.relpath(sciezka, R).replace('\\', '/')
            if rel.endswith('.bat'):          # skrypty Windows z końcówkami CRLF zostają bez zmian
                pass
            if f.endswith(('.js', '.mjs', '.py', '.txt', '.md', '.html', '.json', '.gs', '.bat', '.yml', '.szablon', '.css')) and os.path.getsize(sciezka) < 8_000_000:
                with open(sciezka, 'rb') as fh:
                    if WZORZEC_SEKRETU.search(fh.read()): sys.exit('PRZERWANO: w pliku %s jest napis w kształcie sekretu aplikacji — usuń go przed budowaniem paczki.' % rel)
            z.write(sciezka, 'PMT_Planer_web/' + rel); n += 1
os.replace(tmp, wyj)
print('zip:', wyj, n, 'plików,', round(os.path.getsize(wyj) / 1048576, 1), 'MB')
