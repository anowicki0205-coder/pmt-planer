# -*- coding: utf-8 -*-
"""Nagrywanie ruchu prototypu do pliku GIF.

Statyczny zrzut nie pokazuje animacji, a to właśnie ruch decyduje o tym, czy
interfejs wygląda żywo. Ten skrypt uruchamia wybraną scenę bez ekranu, łapie
kolejne klatki i skleja je w zapętlony obrazek.

Użycie:
    QT_QPA_PLATFORM=offscreen python film.py kompas   film_kompas.gif
    QT_QPA_PLATFORM=offscreen python film.py okno     film_okno.gif
    QT_QPA_PLATFORM=offscreen python film.py przelot  film_przelot.gif
"""
import sys, time
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication


def _klatki(widget, kroki, ms_klatki=60, szerokosc=760):
    """Odtwarza scenę, łapiąc klatki. kroki to lista par (czas_ms, funkcja)."""
    from PIL import Image
    import io
    klatki = []
    start = time.monotonic()
    zrobione = set()
    czas_konca = max(t for t, _ in kroki) if kroki else 0
    while True:
        minelo = (time.monotonic() - start) * 1000.0
        for i, (t, akcja) in enumerate(kroki):
            if i not in zrobione and minelo >= t:
                zrobione.add(i)
                if akcja is not None:
                    akcja()
        QCoreApplication.processEvents()
        obraz = widget.grab().toImage()
        bufor = obraz.bits().asstring(obraz.sizeInBytes())
        kl = Image.frombytes("RGBA", (obraz.width(), obraz.height()), bufor, "raw", "BGRA")
        if szerokosc and kl.width > szerokosc:
            wys = round(kl.height * szerokosc / kl.width)
            kl = kl.resize((szerokosc, wys), Image.LANCZOS)
        klatki.append(kl.convert("RGB"))
        if minelo > czas_konca + 400:
            break
        time.sleep(max(0.0, ms_klatki / 1000.0 - 0.004))
    return klatki


def _zapisz(klatki, plik, ms_klatki=60):
    if not klatki:
        print("brak klatek"); return
    # paleta liczona z klatki w połowie sceny — tam jest najwięcej barw
    srodek = klatki[len(klatki) // 2].quantize(colors=200, method=2)
    male = [k.quantize(palette=srodek, dither=1) for k in klatki]
    male[0].save(plik, save_all=True, append_images=male[1:],
                 duration=ms_klatki, loop=0, optimize=True)
    print(f"{plik}: {len(klatki)} klatek, {klatki[0].width}x{klatki[0].height}")


def scena_kompas():
    import proto_kompas as KM
    from PyQt6.QtWidgets import QWidget, QVBoxLayout
    import proto_styl as S
    class Tlo(QWidget):
        def paintEvent(self, _):
            from PyQt6.QtGui import QPainter
            from PyQt6.QtCore import QRectF
            p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            S.tlo_sceny(p, QRectF(self.rect())); p.end()
    okno = Tlo(); okno.resize(520, 380)
    okno.setStyleSheet(S.qss())
    l = QVBoxLayout(okno); l.setContentsMargins(40, 30, 40, 30)
    karta = KM.KartaKompasu(); l.addWidget(karta)
    okno.show()
    k = karta.kompas
    k.ustaw_stan("gotowy")
    kroki = [(0, None)]
    etapy = [("dane", 0.20), ("trasy", 0.60), ("PDF", 0.85), ("mapa", 0.97)]
    stan_etapow = {n: "czeka" for n, _ in etapy}
    def ustaw(nazwa, w, etap_stan):
        k.ustaw_postep(w); k.ustaw_etap(nazwa)
        stan_etapow[nazwa] = etap_stan
        try:
            karta.ustaw_etapy(dict(stan_etapow))
        except Exception:
            pass
    def start():
        k.ustaw_stan("praca")
    kroki.append((700, start))
    t = 900
    for nazwa, docelowo in etapy:
        for i in range(10):
            p = (docelowo - 0.02) * (i + 1) / 10.0
            stan = "gotowe" if i == 9 else "w_toku"
            kroki.append((t, (lambda w=p, n=nazwa, st=stan: ustaw(n, w, st))))
            t += 110
    kroki.append((t + 200, lambda: (k.ustaw_postep(1.0), k.ustaw_stan("sukces"))))
    kroki.append((t + 1800, None))
    return okno, kroki


def scena_okno():
    import proto_okno as OK
    okno = OK.OknoPrototypu()
    okno.resize(1240, 780)
    okno.show()
    QCoreApplication.processEvents()
    kroki = [(0, None)]
    # wybieramy WYŁĄCZNIE dni, które naprawdę mają trasę — inaczej mapa stoi pusta
    import proto_dane as D
    dni = D.oblicz_miesiac(1850, wolne=(14, 15))
    z_trasa = [d.data.day for d in dni if not d.wolny]
    tasma = getattr(okno, "tasma", None)
    if tasma is not None and len(z_trasa) >= 2:
        for opoznienie, dzien in ((600, z_trasa[1]), (2000, z_trasa[3 % len(z_trasa)])):
            kroki.append((opoznienie, (lambda d=dzien: tasma.wybrano.emit(d))))
    # Pokaz generowania prowadzimy WPROST, klatka po klatce. Zegar programu
    # zwalnia przy nagrywaniu (każda klatka to zrzut całego okna), więc taca
    # nie zdążyłaby się wysunąć w rozsądnym czasie filmu.
    kompas = okno.k_kompas.kompas
    def start_pokazu():
        okno._po_generacji = False
        kompas.ustaw_stan("praca")
        okno.ustaw_postep_pokazu(0.0)
        if hasattr(okno, "_zegar_gen"):
            okno._zegar_gen.stop()
    kroki.append((3200, start_pokazu))
    t = 3400
    for i in range(34):
        kroki.append((t, (lambda u=(i + 1) / 34.0: okno.ustaw_postep_pokazu(u))))
        t += 105
    kroki.append((t + 150, lambda: okno.zakoncz_pokaz(animacja=True)))
    kroki.append((t + 3200, None))
    return okno, kroki


def scena_przelot():
    """Przelot nad rejonem w czasie generowania — na PRAWDZIWYM oknie programu
    (nowy_wyglad), z własnym katalogiem domowym. Silnika nie uruchamiamy:
    dni przychodzą z zegara sceny jako prawdziwe miejscowości rejonu, więc
    film jest powtarzalny i nie zależy od sieci."""
    import os, random, tempfile
    os.environ["HOME"] = tempfile.mkdtemp(prefix="pmt_film_")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import PMT_Delegacje as P
    P.zaproszenie_testera = lambda *a, **k: False
    import nowy_wyglad as NW
    import proto_styl as S
    app = QApplication.instance()
    app.setFont(S.czcionka(13))
    app.setStyleSheet(NW.arkusz())
    okno = NW.OknoNowegoWygladu(
        profil=NW.ProfilWidoku("Jan Testowy", "85010112345",
                               "ul. Kwiatowa 5, 26-600 Radom", "KR"),
        rok=2026, miesiac=6)
    okno.showNormal()
    okno.resize(1440, 900)
    okno.ustaw_animacje(True)
    for _ in range(30):
        QCoreApplication.processEvents()
    geo, baza = okno.geo, okno.baza_miasto
    nazwy = sorted(n for n in geo if n != baza)
    los = random.Random(7)
    kroki = [(0, None)]

    def start():
        okno._zacznij_intro_generowania()
        okno.k_kompas.TYTUL = "Przerwij"
        okno.k_kompas.kompas.ustaw_stan("praca")
        okno._etap_silnika = "trasy"
        okno.ustaw_postep_pokazu(0.05)
    kroki.append((900, start))

    def dzien(i, t):
        przystanki = los.sample(nazwy, los.randint(3, 6))
        punkty = ([(baza,) + tuple(geo[baza])] + [(n,) + tuple(geo[n]) for n in przystanki]
                  + [(baza,) + tuple(geo[baza])])
        film = okno._intro_generowania
        if film is not None:
            film.dodaj_trase(punkty, data=i)
        okno._postep_generacji("Klastrowanie GPS (Dzień %d/8)..." % (i + 1), t)
    t = 2200
    for i in range(8):
        kroki.append((t, (lambda i=i, u=0.30 + 0.05 * i: dzien(i, u))))
        t += 650

    def dokument(i, t):
        okno._postep_generacji("Renderowanie pliku PDF (%d/3)..." % i, t)
    for i in range(1, 4):
        kroki.append((t, (lambda i=i, u=0.80 + 0.05 * i: dokument(i, u))))
        t += 700

    def koniec():
        okno._etap_silnika = ""
        okno._koniec_sekwencji()
        okno.zakoncz_pokaz(animacja=True)
    kroki.append((t + 400, koniec))
    kroki.append((t + 4200, None))
    return okno, kroki


SCENY = {"kompas": scena_kompas, "okno": scena_okno, "przelot": scena_przelot}

if __name__ == "__main__":
    nazwa = sys.argv[1] if len(sys.argv) > 1 else "kompas"
    plik = sys.argv[2] if len(sys.argv) > 2 else f"film_{nazwa}.gif"
    app = QApplication(sys.argv[:1])
    widget, kroki = SCENY[nazwa]()
    klatki = _klatki(widget, kroki)
    _zapisz(klatki, plik)
    widget.close()
