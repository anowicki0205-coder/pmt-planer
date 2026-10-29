#!/usr/bin/env python3
"""Sztuczne „skany” dokumentu z podpisem odręcznym i bez niego (z przekrzywieniem, przesunięciem, szumem, cieniem i kompresją JPEG) do testu js/podpis_reczny.js.
Wymaga: pip install pillow numpy; poppler (pdftoppm).   Uruchom: python generuj_skany.py   (wyniki w testy/dane/skany/; są też w repozytorium)."""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

KAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'skany'); os.makedirs(KAT, exist_ok=True)
PDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'podpisy', 'oryg.pdf')
DPI = 150; MM = DPI / 25.4
subprocess.run(['pdftoppm', '-r', str(DPI), '-png', '-singlefile', PDF, os.path.join(KAT, '_strona')], check=True)
baza = Image.open(os.path.join(KAT, '_strona.png')).convert('RGB')
# dokładny y linii podpisu pracownika: wiersz z największą liczbą ciemnych pikseli w okolicy 235,7 mm, w kolumnach 143–195 mm
a = np.asarray(baza.convert('L')); x0, x1 = int(143 * MM), int(195 * MM)
wiersze = {y: int((a[y, x0:x1] < 120).sum()) for y in range(int(231 * MM), int(240 * MM))}
ly_px = max(wiersze, key=wiersze.get); LY = ly_px / MM
MIEJSCE = {'strona': 1, 'x': 138.0, 'y': round(LY, 2), 'w': 62.0}
print('linia podpisu pracownika: y =', round(LY, 2), 'mm')
json.dump({'miejsca': [MIEJSCE], 'strony': 1, 'ostatni_y': 190.0}, open(os.path.join(KAT, 'miejsca.json'), 'w'))

def podpis(img, rng, wielkosc=1.0):
    """Podpis odręczny: albo ciąg pętli jak w kursywie (większość), albo prosta falująca kreska — najtrudniejszy przypadek."""
    d = ImageDraw.Draw(img); xs, xe = 144 * MM, 194 * MM; yc = (LY - 6.0) * MM
    kolor = rng.choice([(20, 20, 30), (15, 25, 90), (10, 10, 10), (30, 30, 120)]); szer = rng.choice([2, 3, 3, 4])
    if rng.random() < 0.8:
        punkty = []; x = xs + rng.uniform(0, 3) * MM; liter = rng.randint(5, 9); dl = (xe - xs) * 0.92 / liter
        for j in range(liter):
            r = rng.uniform(1.6, 3.8) * MM * wielkosc; pochylenie = rng.uniform(0.2, 0.7); faza = rng.uniform(0, 6.28)
            for i in range(30):
                t = i / 29; kat = faza + t * 2 * math.pi * rng.uniform(1.0, 1.6)
                punkty.append((x + dl * t + r * math.cos(kat) * 0.6 + pochylenie * r * math.sin(kat), yc + r * math.sin(kat) * 0.9 + rng.uniform(-0.15, 0.15) * MM))
            x += dl
        punkty.append((xe, yc + rng.uniform(-1, 1) * MM))
    else:
        punkty = [(xs + (xe - xs) * t / 259, yc + rng.uniform(2.2, 4.2) * MM * wielkosc * (0.6 * math.sin(7 * t / 259 + rng.random()) + 0.4 * math.sin(17 * t / 259))) for t in range(260)]
    for i in range(len(punkty) - 1):
        if rng.random() < 0.015: continue                      # krótkie podniesienie długopisu
        d.line([punkty[i], punkty[i + 1]], fill=kolor, width=szer)
    d.line([(xs + (xe - xs) * 0.3, yc + 4.2 * MM), (xs + (xe - xs) * 0.9, yc + 5.3 * MM)], fill=kolor, width=max(2, szer - 1))      # kreska pod nazwiskiem

def zepsuj(img, rng, kat_max=1.6, przes_max=2.5):
    kat = rng.uniform(-kat_max, kat_max); dx, dy = rng.uniform(-przes_max, przes_max) * MM, rng.uniform(-przes_max, przes_max) * MM
    img = img.rotate(kat, resample=Image.BICUBIC, fillcolor=(255, 255, 255), translate=(dx, dy))
    arr = np.asarray(img).astype(np.float32)
    h, w, _ = arr.shape; gx = np.linspace(rng.uniform(0.88, 1.0), rng.uniform(0.88, 1.0), w)[None, :, None]; gy = np.linspace(rng.uniform(0.9, 1.0), rng.uniform(0.9, 1.0), h)[:, None, None]
    arr = arr * gx * gy + rng.gauss(0, 1) * 0
    arr += np.random.default_rng(rng.randrange(1 << 30)).normal(0, rng.uniform(2, 9), arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if rng.random() < 0.5: img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.9)))
    return img

wyniki = []
for i in range(40):
    for jest in (True, False):
        rng = random.Random(1000 * i + (1 if jest else 2)); im = baza.copy()
        if jest: podpis(im, rng)
        im = zepsuj(im, rng)
        nazwa = f"{'z' if jest else 'bez'}_{i:02d}.jpg"; im.save(os.path.join(KAT, nazwa), quality=rng.randint(60, 88)); wyniki.append({'plik': nazwa, 'jest': jest})
# kartka na ciemnym stole (zdjęcie): białe pole z marginesem
for i in range(6):
    for jest in (True, False):
        rng = random.Random(77000 + 10 * i + (1 if jest else 2)); im = baza.copy()
        if jest: podpis(im, rng)
        im = zepsuj(im, rng, 1.0, 1.0); stol = Image.new('RGB', (im.width + 160, im.height + 140), (58, 52, 48)); stol.paste(im, (80, 70))
        nazwa = f"stol_{'z' if jest else 'bez'}_{i:02d}.jpg"; stol.save(os.path.join(KAT, nazwa), quality=80); wyniki.append({'plik': nazwa, 'jest': jest, 'stol': True})
json.dump(wyniki, open(os.path.join(KAT, 'lista.json'), 'w'), ensure_ascii=False)
os.remove(os.path.join(KAT, '_strona.png'))
# dwustronicowy PDF ze skanem (jak z aplikacji skanującej): strona 1 z podpisem, strona 2 bez
subprocess.run(['convert', os.path.join(KAT, 'z_00.jpg'), os.path.join(KAT, 'bez_01.jpg'), os.path.join(KAT, 'skan2.pdf')], check=False)
print(len(wyniki), 'obrazów')
