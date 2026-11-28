#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atrapa serwera OSRM do testów zbuduj_tabele.py bez internetu i bez danych OpenStreetMap: odpowiada na /table/v1/driving/polyline(...)
z drogą = linia prosta × współczynnik zależny od pary (od 1,12 do 1,42) i czasem z prędkości zależnej od długości (dłuższe odcinki szybciej).
Dekoder polilinii jest niezależny od kodera w zbuduj_tabele.py — test sprawdza więc także samo kodowanie."""
import json, math, re, sys, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer


def dekoduj_polilinie(tekst, precyzja=5):
    m, i, lat, lng, wynik = 10 ** precyzja, 0, 0, 0, []
    def liczba():
        nonlocal i
        w, przes = 0, 0
        while True:
            b = ord(tekst[i]) - 63; i += 1
            w |= (b & 0x1f) << przes; przes += 5
            if b < 0x20:
                break
        return ~(w >> 1) if (w & 1) else (w >> 1)
    while i < len(tekst):
        lat += liczba(); lng += liczba()
        wynik.append((lat / m, lng / m))
    return wynik


def prosta(a, b):
    p = math.pi / 180.0
    return 6371.0 * math.hypot((b[1] - a[1]) * p * math.cos((a[0] + b[0]) * p / 2.0), (b[0] - a[0]) * p)


def droga_km(a, b):
    d = prosta(a, b)
    if d < 1e-9:
        return 0.0
    w = 1.12 + 0.30 * (((int(abs(a[0] * 1e4)) * 7 + int(abs(a[1] * 1e4)) * 13 + int(abs(b[0] * 1e4)) * 3 + int(abs(b[1] * 1e4)) * 5) % 100) / 100.0)
    return d * w


def czas_s(km):
    v = 38.0 + 40.0 * (1.0 - math.exp(-km / 60.0))       # 38 km/h dla krótkich, do ~78 km/h dla długich
    return km / v * 3600.0


class Uchwyt(BaseHTTPRequestHandler):
    zapytan = 0
    def log_message(self, *a):
        pass
    def do_GET(self):
        Uchwyt.zapytan += 1
        u = urllib.parse.urlsplit(self.path)
        m = re.match(r"^/table/v1/driving/polyline\((.*)\)$", urllib.parse.unquote(u.path))
        if not m:
            self.send_response(400); self.end_headers(); self.wfile.write(b'{"code":"InvalidUrl"}'); return
        pkt = dekoduj_polilinie(m.group(1))
        q = urllib.parse.parse_qs(u.query)
        zr = [int(x) for x in q["sources"][0].split(";")]
        ce = [int(x) for x in q["destinations"][0].split(";")]
        if "duration,distance" not in q.get("annotations", [""])[0] and "distance,duration" not in q.get("annotations", [""])[0]:
            self.send_response(400); self.end_headers(); self.wfile.write(b'{"code":"InvalidQuery"}'); return
        odl = [[droga_km(pkt[a], pkt[b]) * 1000.0 for b in ce] for a in zr]
        czas = [[czas_s(droga_km(pkt[a], pkt[b])) for b in ce] for a in zr]
        # jedna para „bez trasy” (None), żeby sprawdzić obsługę braków
        if len(zr) > 1 and len(ce) > 2:
            odl[0][1] = None; czas[0][1] = None
        cialo = json.dumps({"code": "Ok", "distances": odl, "durations": czas}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(cialo)


def uruchom(port=0):
    s = HTTPServer(("127.0.0.1", port), Uchwyt)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


if __name__ == "__main__":
    s = uruchom(int(sys.argv[1]) if len(sys.argv) > 1 else 5000)
    print("atrapa OSRM na porcie", s.server_address[1]); threading.Event().wait()
