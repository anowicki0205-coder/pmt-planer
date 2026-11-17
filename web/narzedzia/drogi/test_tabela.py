#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test potoku budowania tabeli dróg na atrapie OSRM: kodowanie polilinii, bloki zapytań, braki, format pliku i jego odczyt niezależnym czytnikiem.
    python3 web/narzedzia/drogi/test_tabela.py"""
import json, os, struct, sys, tempfile
KAT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, KAT)
import zbuduj_tabele as Z, atrapa_osrm as A
wyn = []
def ok(opis, w, szcz=""):
    wyn.append(bool(w)); print(("  OK   " if w else "  BŁĄD ") + opis + (" — " + str(szcz) if szcz and not w else ""))

# 1. polilinia: wektor testowy Google („_p~iF~ps|U_ulLnnqC_mqNvxq`@”) i obie strony kodowania
ok("polilinia: znany wektor Google", Z.polilinia([(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]) == "_p~iF~ps|U_ulLnnqC_mqNvxq`@")
pkt = [(50.9071, 14.9561), (52.2297, 21.0122), (54.352, 18.6466), (49.2992, 19.9496)]
ok("polilinia: kodowanie i dekodowanie wracają do punktów (5 miejsc)", all(abs(a[0] - b[0]) < 1e-5 and abs(a[1] - b[1]) < 1e-5 for a, b in zip(pkt, A.dekoduj_polilinie(Z.polilinia(pkt)))))

# 2. cały potok na próbce miejscowości
miasta = json.load(open(os.path.join(KAT, "miasta.json"), encoding="utf-8"))
srv = A.uruchom(0); port = srv.server_address[1]
tmp = tempfile.mkdtemp()
bin_, rap = os.path.join(tmp, "drogi.bin"), os.path.join(tmp, "RAPORT.txt")
kod = Z.main(["--osrm", "http://127.0.0.1:%d" % port, "--miasta", os.path.join(KAT, "miasta.json"), "--wyjscie", bin_, "--raport", rap, "--promien", "120", "--probka", "260"])
ok("budowa na atrapie kończy się sukcesem", kod == 0, kod)
ok("atrapa dostała kilka zapytań blokowych (nie jedno na parę)", 1 <= A.Uchwyt.zapytan <= 40, A.Uchwyt.zapytan)

# 3. niezależny czytnik pliku
b = open(bin_, "rb").read()
ok("nagłówek PMTD, wersja 1", b[:4] == b"PMTD" and b[4] == 1)
_, N, promien, vref = struct.unpack("<BIff", b[4:17])
ok("N = 260, promień 120 km, prędkość odniesienia rozsądna", N == 260 and abs(promien - 120) < 1e-3 and 40 < vref < 90, (N, promien, vref))
poz = 17
wsp = []
for i in range(N):
    la, lo = struct.unpack("<ii", b[poz:poz + 8]); poz += 8; wsp.append((la / 1e4, lo / 1e4))
ok("współrzędne w pliku zgadzają się z miasta.json", all(abs(wsp[i][0] - miasta[i]["lat"]) < 1e-4 and abs(wsp[i][1] - miasta[i]["lng"]) < 1e-4 for i in range(N)))
pary, kolejnosc_ok = {}, True
for i in range(N):
    (k,) = struct.unpack("<H", b[poz:poz + 2]); poz += 2
    poprz = -1
    for _ in range(k):
        j, km10, t10 = struct.unpack("<HHH", b[poz:poz + 6]); poz += 6
        kolejnosc_ok &= j > i and j > poprz; poprz = j
        pary[(i, j)] = (km10 / 10.0, t10 * 10.0)
ok("plik kończy się dokładnie po ostatniej parze, pary i<j, j rosnąco", poz == len(b) and kolejnosc_ok, (poz, len(b)))
# oczekiwane pary liczone wprost
oczek = 0; zle = 0; mod_brak = 0
for i in range(N):
    for j in range(i + 1, N):
        d = Z.linia_prosta_km(miasta[i]["lat"], miasta[i]["lng"], miasta[j]["lat"], miasta[j]["lng"])
        if d <= 120:
            oczek += 1
            if (i, j) in pary:
                km_o = A.droga_km((miasta[i]["lat"], miasta[i]["lng"]), (miasta[j]["lat"], miasta[j]["lng"]))
                if abs(pary[(i, j)][0] - km_o) > 0.06 or abs(pary[(i, j)][1] - A.czas_s(km_o)) > 10.1:
                    zle += 1
            else:
                mod_brak += 1
ok("liczba par w pliku = liczba par w promieniu minus pary „bez trasy” z atrapy", len(pary) + mod_brak == oczek and 0 <= mod_brak <= 40, (len(pary), mod_brak, oczek))
ok("kilometry i czasy każdej pary zgadzają się z odpowiedzią atrapy (zaokrąglenie 0,1 km i 10 s)", zle == 0, zle)
ok("raport powstał i podaje kwantyle", "droga/linia prosta" in open(rap, encoding="utf-8").read())
srv.shutdown()
print("\nWYNIK: %d / %d" % (sum(wyn), len(wyn)))
sys.exit(0 if all(wyn) else 1)
