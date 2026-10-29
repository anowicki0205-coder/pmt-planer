#!/usr/bin/env python3
"""Generuje web/sw.js: lista plików do pamięci podręcznej + wersja z sumy zawartości (nowe wdrożenie = nowa wersja)."""
import os, json, hashlib
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# tylko to, co aplikacja naprawdę ładuje (lista dozwolonych wzorców)
import fnmatch
DOZWOLONE = ['index.html', 'manifest.webmanifest', 'css/*.css', 'js/*.js', 'ikony/*', 'silnik/*.py', 'silnik/sieci_cel.txt', 'silnik/fonty/*.ttf', 'vendor/czcionki/*.woff2',
             'vendor/pyodide/pyodide.asm.js', 'vendor/pyodide/pyodide.asm.wasm', 'vendor/pyodide/pyodide.mjs', 'vendor/pyodide/python_stdlib.zip',
             'vendor/pyodide/pyodide-lock.json', 'vendor/paczki/*.whl', 'vendor/qr/qrcode.mjs', 'przyklad/*.json']
pliki = []
for kat, dirs, nazwy in os.walk(R):
    dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__', 'testy', 'zrodlo_makiety', 'czesci', 'narzedzia', '.git')]
    for n in nazwy:
        r = os.path.relpath(os.path.join(kat, n), R).replace('\\', '/')
        if any(fnmatch.fnmatch(r, w) for w in DOZWOLONE): pliki.append(r)
pliki = sorted(pliki)
h = hashlib.sha256()
for r in pliki:
    h.update(r.encode()); h.update(open(os.path.join(R, r), 'rb').read())
szablon = open(os.path.join(R, 'narzedzia/sw.szablon.js'), encoding='utf-8').read()
lista = ['./'] + ['./' + r for r in pliki]
open(os.path.join(R, 'sw.js'), 'w', encoding='utf-8').write(szablon.replace('__WERSJA__', h.hexdigest()[:12]).replace('__LISTA__', json.dumps(lista, ensure_ascii=False, indent=1)))
print('sw.js:', len(lista), 'plików, wersja', h.hexdigest()[:12], '| rozmiar danych', sum(os.path.getsize(os.path.join(R, r)) for r in pliki) // 1024, 'KB')
