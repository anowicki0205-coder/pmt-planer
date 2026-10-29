#!/usr/bin/env python3
"""Sztuczne skany (jak z aplikacji skanującej) prawdziwych PDF-ów wygenerowanych przez aplikację — do testów obiegu w przeglądarce.
Użycie: python skanuj_pliki.py <katalog z PDF-ami> <miejsca.json> <katalog wyjściowy> <plan.json>
miejsca.json: { "nazwa.pdf": { "strony": 1, "miejsca": [{ "strona": 1, "x": 138, "y": 235.9, "w": 62 }], "ostatni_y": 170 } }  (z danych aplikacji: wynik.miejsca_podpisu)
plan.json: { "nazwa.pdf": "z" (z podpisem) | "bez" (bez podpisu) | "stol" (z podpisem, kartka na stole) | "pominiety" }
Wymaga: pillow, numpy, poppler (pdftoppm)."""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
wej, miejsca, wyj, plan = sys.argv[1], json.load(open(sys.argv[2], encoding='utf8')), sys.argv[3], json.load(open(sys.argv[4], encoding='utf8'))
os.makedirs(wyj, exist_ok=True); DPI = 150; MM = DPI / 25.4

def podpis(img, rng, x, ly, w, h):
    d = ImageDraw.Draw(img); xs, xe = (x + 6) * MM, (x + w - 6) * MM; yc = (ly - 6.0) * MM
    kolor = rng.choice([(20, 20, 30), (15, 25, 90), (10, 10, 10)]); szer = rng.choice([2, 3, 3]); punkty = []; px = xs; liter = rng.randint(5, 9); dl = (xe - xs) * 0.92 / liter
    for j in range(liter):
        r = rng.uniform(1.6, 3.4) * MM; poch = rng.uniform(0.2, 0.7); faza = rng.uniform(0, 6.28)
        for i in range(30):
            t = i / 29; kat = faza + t * 2 * math.pi * rng.uniform(1.0, 1.6)
            punkty.append((px + dl * t + r * math.cos(kat) * 0.6 + poch * r * math.sin(kat), yc + r * math.sin(kat) * 0.9))
        px += dl
    for i in range(len(punkty) - 1): d.line([punkty[i], punkty[i + 1]], fill=kolor, width=szer)
    d.line([(xs + (xe - xs) * .3, yc + 4.2 * MM), (xs + (xe - xs) * .9, yc + 5.3 * MM)], fill=kolor, width=2)

def zepsuj(img, rng):
    img = img.rotate(rng.uniform(-1.2, 1.2), resample=Image.BICUBIC, fillcolor=(255, 255, 255), translate=(rng.uniform(-1.5, 1.5) * MM, rng.uniform(-1.5, 1.5) * MM))
    arr = np.asarray(img).astype(np.float32); arr += np.random.default_rng(rng.randrange(1 << 30)).normal(0, 4, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

for f in sorted(os.listdir(wej)):
    if not f.lower().endswith('.pdf'): continue
    co = plan.get(f, 'z')
    if co == 'pominiety': continue
    base = f[:-4]; tmp = os.path.join(wyj, '_t'); subprocess.run(['pdftoppm', '-r', str(DPI), '-png', '-singlefile', os.path.join(wej, f), tmp], check=True)
    im = Image.open(tmp + '.png').convert('RGB'); os.remove(tmp + '.png'); rng = random.Random(hash(f) & 0xffff)
    m = (miejsca.get(f) or {}).get('miejsca') or []
    if co in ('z', 'stol'):
        if m: podpis(im, rng, m[0]['x'], m[0]['y'], m[0]['w'], 9.7)
        else:   # dokument bez wyznaczonego miejsca (rozliczenie): podpis pod tabelą
            y0 = (miejsca.get(f) or {}).get('ostatni_y', 170) + 20; podpis(im, rng, 60, y0 + 12, 100, 9.7)
    im = zepsuj(im, rng)
    if co == 'stol':
        s = Image.new('RGB', (im.width + 160, im.height + 140), (58, 52, 48)); s.paste(im, (80, 70)); im = s
    im.save(os.path.join(wyj, base + '_skan.jpg'), quality=78)
print('zeskanowano', len(os.listdir(wyj)), 'plików')
