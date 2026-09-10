# -*- coding: utf-8 -*-
"""
KARTA TESTERA PMT PLANERA

Moduł WBUDOWANY w program — nie wymaga żadnych dodatkowych plików.
Prowadzi przez wszystkie możliwości PMT Planera, zbiera werdykt
„działa / nie działa / uwaga", nagradza punktami i poziomami, a na
koniec tworzy raport dla autora oraz imienny certyfikat testera.

Wywołanie z programu:   from karta_testera import pokaz_karte
                        pokaz_karte(self)
Uruchomienie osobno:    python karta_testera.py
"""

import datetime
import json
import os
import sys

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QPen, QIcon
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QScrollArea, QLineEdit,
                             QTextEdit, QFrame, QProgressBar, QMessageBox,
                             QFileDialog)

WERSJA_KARTY = "1.0"
PLIK_STANU = os.path.join(os.path.expanduser("~"), ".pmt_tester.json")

# ── scenariusze: (obszar, tytuł, jak sprawdzić, oczekiwany wynik, punkty) ──
SCENARIUSZE = [
    ("Logowanie", "Wejście do programu",
     "Uruchom program i wpisz swój kod oraz hasło.",
     "Po wpisaniu poprawnego hasła program loguje się sam, bez klikania.", 10),
    ("Logowanie", "Błędne hasło",
     "Wpisz celowo złe hasło.",
     "Pojawia się czytelny komunikat, a pola pozostają aktywne.", 10),

    ("Intro", "Powitanie",
     "Obejrzyj animację startową do końca.",
     "Widać kulę ziemską, zejście do Twojego miasta i trasę ze sklepami.", 10),
    ("Intro", "Twoje miasto",
     "Sprawdź, czy nazwa miasta w intrze zgadza się z Twoim adresem.",
     "Nazwa miasta i punkt na globie odpowiadają Twojej bazie.", 15),
    ("Intro", "Dźwięki",
     "Posłuchaj: ładowanie, pojawienie się Polski, kolejne sklepy.",
     "Dźwięki są łagodne i wznoszą się wraz z postępem.", 10),
    ("Intro", "Pominięcie",
     "Kliknij myszą albo naciśnij klawisz w trakcie animacji.",
     "Intro natychmiast się kończy i wchodzisz do programu.", 10),

    ("Plan wizyt", "Dodanie sklepu",
     "Dodaj do planu nową wizytę w wybranym dniu.",
     "Wizyta pojawia się na liście i w podsumowaniu dnia.", 10),
    ("Plan wizyt", "Edycja i usunięcie",
     "Zmień adres istniejącej wizyty, potem usuń jedną z nich.",
     "Zmiany zapisują się i są widoczne po ponownym wejściu.", 10),
    ("Plan wizyt", "Wyłączenie dni",
     "Oznacz kilka dni jako wolne (urlop, święto).",
     "Generator pomija te dni przy układaniu tras.", 15),

    ("Delegacje", "Generowanie na kwotę",
     "Wygeneruj delegację na kwotę powyżej 4000 zł.",
     "Suma wszystkich dni zgadza się z zamówioną kwotą co do grosza.", 20),
    ("Delegacje", "Liczba dokumentów",
     "Sprawdź, ile powstało plików PDF.",
     "Dokumentów jest mniej niż dawniej; każdy mieści się na jednej stronie A4.", 15),
    ("Delegacje", "Tryb wieczorno-weekendowy",
     "Przełącz tryb pracy i wygeneruj delegację ponownie.",
     "Trasy mieszczą się w krótszym oknie, także w weekendy.", 15),
    ("Delegacje", "Rozłożenie w miesiącu",
     "Wygeneruj małą kwotę, np. 1200 zł, i spójrz na kalendarz.",
     "Dni są rozrzucone po całym miesiącu, a nie tylko na początku.", 10),
    ("Delegacje", "Zawartość PDF",
     "Otwórz kilka dokumentów i sprawdź dane.",
     "Imię, adres, daty, trasy i kwoty są poprawne i czytelne.", 15),

    ("Mapy i historia", "Mapa trasy",
     "Otwórz mapę wygenerowanej trasy.",
     "Punkty i przebieg odpowiadają wygenerowanym dniom.", 10),
    ("Mapy i historia", "Historia delegacji",
     "Zajrzyj do historii wcześniejszych rozliczeń.",
     "Poprzednie miesiące są widoczne i można je otworzyć.", 10),

    ("Stabilność", "Praca ciągła",
     "Popracuj w programie kilkanaście minut, przełączaj zakładki.",
     "Program nie zwalnia, nie zawiesza się, nic nie znika.", 15),
    ("Stabilność", "Ponowne uruchomienie",
     "Zamknij program i uruchom go ponownie.",
     "Dane, plan i ustawienia pozostają na miejscu.", 10),
    ("Stabilność", "Aktualizacja",
     "Sprawdź, czy program informuje o nowej wersji.",
     "Komunikat pojawia się, a aktualizacja przebiega bez błędu.", 10),

    ("Próby na złość", "Błędny PESEL",
     "Wpisz PESEL z literą, za krótki albo z niemożliwą datą urodzenia.",
     "Program odmawia i tłumaczy dlaczego — zamiast zapisać śmieci.", 15),
    ("Próby na złość", "Adres, którego nie ma",
     "Podaj adres z wymyśloną miejscowością, np. „Zażółcice Górne 12”.",
     "Program mówi, że nie rozpoznaje adresu, i nie wysypuje się.", 15),
    ("Próby na złość", "Baza po drugiej stronie Polski",
     "Ustaw adres w Szczecinie (albo innym odległym mieście) i wygeneruj trasy.",
     "Trasy układają się wokół nowej bazy, a nie wokół poprzedniej.", 20),
    ("Próby na złość", "Bardzo wysoka kwota",
     "Zamów delegację na 20 000 zł w jednym miesiącu.",
     "Program uprzedza, że kwota nie mieści się w miesiącu, i podaje maksimum.", 20),
    ("Próby na złość", "Bardzo niska kwota",
     "Zamów 50 zł na cały miesiąc.",
     "Powstaje kilka krótkich dni, suma zgadza się co do grosza.", 10),
    ("Próby na złość", "Miesiąc prawie bez dni",
     "Wyłącz prawie wszystkie dni i spróbuj wygenerować dużą kwotę.",
     "Program tłumaczy, że brakuje dni — zamiast po cichu dać mniej.", 15),
    ("Próby na złość", "Brak internetu",
     "Wyłącz Wi-Fi i uruchom program.",
     "Program startuje i mówi, czego nie może zrobić bez połączenia.", 10),
    ("Próby na złość", "Dwa okna naraz",
     "Uruchom program drugi raz, gdy pierwszy jest otwarty.",
     "Nie dochodzi do konfliktu ani utraty danych.", 10),

    ("Zdrowy rozsądek", "Czy trasy są realne",
     "Weź jeden dzień i sprawdź trasę w mapach Google.",
     "Odległości i czasy są zbliżone — dzień da się przejechać w 8 godzin.", 25),
    ("Zdrowy rozsądek", "Czy kwota odpowiada realiom",
     "Porównaj kilometry i kwotę dnia ze swoim zwykłym dniem pracy.",
     "Wartości nie odbiegają od tego, co realnie jeździsz.", 25),
    ("Zdrowy rozsądek", "Powtarzalność",
     "Wygeneruj ten sam miesiąc dwa razy pod rząd.",
     "Wyniki są sensowne za każdym razem, bez dziwnych skoków.", 10),

    ("Twoja opinia", "Co poprawić",
     "Napisz w polu uwag, co najbardziej przeszkadza w codziennej pracy.",
     "Jedna konkretna rzecz do poprawy — najcenniejsza informacja zwrotna.", 25),
]

POZIOMY = [(0, "Nowicjusz"), (90, "Zwiadowca"), (200, "Tropiciel"),
           (320, "Weteran"), (430, "Mistrz testów")]

T_OK, T_BLAD, T_UWAGA = "dziala", "blad", "uwaga"
BARWY = {T_OK: "#10b881", T_BLAD: "#e04b4b", T_UWAGA: "#e8a33d"}


def poziom(pkt):
    naz = POZIOMY[0][1]
    for prog, n in POZIOMY:
        if pkt >= prog:
            naz = n
    return naz


class Karta(QFrame):
    """Pojedynczy scenariusz do sprawdzenia."""

    def __init__(self, nr, dane, przy_zmianie):
        super().__init__()
        obszar, tytul, jak, oczek, pkt = dane
        self.nr, self.pkt, self.przy_zmianie = nr, pkt, przy_zmianie
        self.stan, self.uwaga = None, ""
        self.setObjectName("karta")
        L = QVBoxLayout(self)
        L.setContentsMargins(16, 14, 16, 14)
        L.setSpacing(6)

        g = QHBoxLayout()
        et = QLabel("%d. %s" % (nr, tytul))
        et.setStyleSheet("color:#eafaf2;font:600 15px 'Segoe UI';")
        g.addWidget(et)
        g.addStretch()
        self.odznaka = QLabel("%d pkt" % pkt)
        self.odznaka.setStyleSheet("color:#9fd4b8;font:600 12px 'Segoe UI';")
        g.addWidget(self.odznaka)
        L.addLayout(g)

        op = QLabel("Jak sprawdzić: " + jak)
        op.setWordWrap(True)
        op.setStyleSheet("color:#c9eedb;font:13px 'Segoe UI';")
        L.addWidget(op)
        oc = QLabel("Powinno być: " + oczek)
        oc.setWordWrap(True)
        oc.setStyleSheet("color:#8fb3a3;font:italic 12px 'Segoe UI';")
        L.addWidget(oc)

        pas = QHBoxLayout()
        pas.setSpacing(8)
        self.przyciski = {}
        for kod, tekst in ((T_OK, "✓  Działa"), (T_UWAGA, "!  Uwaga"), (T_BLAD, "✕  Nie działa")):
            b = QPushButton(tekst)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(32)
            b.clicked.connect(lambda _, k=kod: self.ustaw(k))
            self.przyciski[kod] = b
            pas.addWidget(b)
        pas.addStretch()
        L.addLayout(pas)

        self.pole = QLineEdit()
        self.pole.setPlaceholderText("Uwagi do tego punktu (opcjonalnie)…")
        self.pole.setFixedHeight(30)
        self.pole.setStyleSheet(
            "QLineEdit{background:#07231a;border:1px solid #14523c;border-radius:8px;"
            "padding:2px 10px;color:#eafaf2;font:12px 'Segoe UI';}"
            "QLineEdit:focus{border-color:#10b881;}")
        self.pole.textChanged.connect(self._uwaga)
        L.addWidget(self.pole)
        self._maluj()

    def _uwaga(self, t):
        self.uwaga = t
        self.przy_zmianie()

    def ustaw(self, kod):
        self.stan = None if self.stan == kod else kod
        self._maluj()
        self.przy_zmianie()

    def _maluj(self):
        for kod, b in self.przyciski.items():
            wybrany = (kod == self.stan)
            b.setStyleSheet(
                "QPushButton{border-radius:8px;padding:4px 14px;font:600 13px 'Segoe UI';"
                "background:%s;color:%s;border:1px solid %s;}"
                "QPushButton:hover{border-color:%s;}" % (
                    BARWY[kod] if wybrany else "#0c2a20",
                    "#04140d" if wybrany else "#9fd4b8",
                    BARWY[kod] if wybrany else "#1e6e50", BARWY[kod]))
        self.setStyleSheet(
            "#karta{background:#07231a;border-radius:14px;border:1px solid %s;}"
            % (BARWY.get(self.stan, "#123c2e")))

    def zdobyte(self):
        return self.pkt if self.stan == T_OK else (self.pkt // 2 if self.stan in (T_UWAGA, T_BLAD) else 0)


class Tester(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PMT Planer — karta testera")
        self.resize(880, 780)
        # BEZ RAMKI SYSTEMOWEJ — okno ma wyglądać jak część programu.
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.karty = []
        self._przesuw = None

        ZEW = QVBoxLayout(self)
        ZEW.setContentsMargins(0, 0, 0, 0)
        self.ramka = QFrame(self)
        self.ramka.setObjectName("ramkaKarty")
        self.ramka.setStyleSheet(
            "#ramkaKarty{background:#04140d;border:1px solid #1e6e50;"
            "border-radius:16px;}")
        ZEW.addWidget(self.ramka)

        G = QVBoxLayout(self.ramka)
        G.setContentsMargins(22, 14, 22, 16)
        G.setSpacing(12)

        pasek = QHBoxLayout()
        tyt = QLabel("KARTA TESTERA")
        tyt.setStyleSheet("color:#eafaf2;font:700 24px 'Segoe UI';")
        pasek.addWidget(tyt)
        pasek.addStretch()
        b_zamknij = QPushButton("✕")
        b_zamknij.setFixedSize(34, 30)
        b_zamknij.setCursor(Qt.CursorShape.PointingHandCursor)
        b_zamknij.setStyleSheet(
            "QPushButton{background:transparent;color:#9fd4b8;border:none;"
            "font:600 16px 'Segoe UI';border-radius:8px;}"
            "QPushButton:hover{background:#7a2222;color:#ffffff;}")
        b_zamknij.clicked.connect(self.close)
        pasek.addWidget(b_zamknij)
        G.addLayout(pasek)
        pod = QLabel("Przejdź program punkt po punkcie i powiedz, co działa, a co nie. "
                     "Każdy sprawdzony punkt to punkty i wyższy poziom — na końcu odbierasz certyfikat.")
        pod.setWordWrap(True)
        pod.setStyleSheet("color:#9fd4b8;font:13px 'Segoe UI';")
        G.addWidget(pod)

        g = QHBoxLayout()
        self.imie = QLineEdit()
        self.imie.setPlaceholderText("Twoje imię i nazwisko (trafi na certyfikat)")
        self.imie.setFixedHeight(34)
        self.imie.setStyleSheet(
            "QLineEdit{background:#07231a;border:1px solid #1e6e50;border-radius:9px;"
            "padding:4px 12px;color:#eafaf2;font:13px 'Segoe UI';}")
        self.imie.textChanged.connect(self.odswiez)
        g.addWidget(self.imie, 3)
        self.etykieta_poziom = QLabel()
        self.etykieta_poziom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etykieta_poziom.setStyleSheet(
            "background:#07231a;border:1px solid #1e6e50;border-radius:9px;"
            "color:#3fe0a3;font:600 13px 'Segoe UI';padding:6px 14px;")
        g.addWidget(self.etykieta_poziom, 2)
        G.addLayout(g)

        self.pasek = QProgressBar()
        self.pasek.setFixedHeight(16)
        self.pasek.setTextVisible(True)
        self.pasek.setStyleSheet(
            "QProgressBar{background:#07231a;border:1px solid #1e6e50;border-radius:8px;"
            "color:#eafaf2;font:600 11px 'Segoe UI';text-align:center;}"
            "QProgressBar::chunk{background:#10b881;border-radius:7px;}")
        G.addWidget(self.pasek)

        przew = QScrollArea()
        przew.setWidgetResizable(True)
        przew.setStyleSheet("QScrollArea{border:none;}")
        wnetrze = QWidget()
        wnetrze.setObjectName("wnetrzeKarty")
        wnetrze.setStyleSheet("#wnetrzeKarty{background:#04140d;}")
        przew.setViewportMargins(0, 0, 0, 0)
        try:
            przew.viewport().setStyleSheet("background:#04140d;")
        except Exception:
            pass
        W = QVBoxLayout(wnetrze)
        W.setContentsMargins(0, 4, 8, 4)
        W.setSpacing(10)
        obszar_teraz = None
        for i, dane in enumerate(SCENARIUSZE, start=1):
            if dane[0] != obszar_teraz:
                obszar_teraz = dane[0]
                n = QLabel(obszar_teraz.upper())
                n.setStyleSheet("color:#3fe0a3;font:700 12px 'Segoe UI';letter-spacing:2px;padding-top:6px;")
                W.addWidget(n)
            k = Karta(i, dane, self.odswiez)
            self.karty.append(k)
            W.addWidget(k)
        W.addStretch()
        przew.setWidget(wnetrze)
        G.addWidget(przew, 1)

        self.uwagi = QTextEdit()
        self.uwagi.setPlaceholderText("Uwagi ogólne, pomysły, czego brakuje…")
        self.uwagi.setFixedHeight(70)
        self.uwagi.setStyleSheet(
            "QTextEdit{background:#07231a;border:1px solid #1e6e50;border-radius:10px;"
            "padding:8px;color:#eafaf2;font:13px 'Segoe UI';}")
        self.uwagi.textChanged.connect(self.zapisz_stan)
        G.addWidget(self.uwagi)

        d = QHBoxLayout()
        d.setSpacing(10)
        for tekst, fn, glowny in (("Zapisz raport", self.zapisz_raport, True),
                                  ("Kopiuj do schowka", self.kopiuj, False),
                                  ("Certyfikat testera", self.certyfikat, False)):
            b = QPushButton(tekst)
            b.setFixedHeight(38)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(fn)
            b.setStyleSheet(
                "QPushButton{border-radius:10px;padding:6px 18px;font:600 14px 'Segoe UI';"
                "background:%s;color:%s;border:1px solid #1e6e50;}"
                "QPushButton:hover{border-color:#10b881;}" % (
                    "#10b881" if glowny else "#07231a",
                    "#04140d" if glowny else "#c9eedb"))
            d.addWidget(b)
        d.addStretch()
        self.info = QLabel("")
        self.info.setStyleSheet("color:#9fd4b8;font:12px 'Segoe UI';")
        d.addWidget(self.info)
        G.addLayout(d)

        self.wczytaj_stan()
        self.odswiez()

    # ── przesuwanie okna bez ramki systemowej ──
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() < 58:
            self._przesuw = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._przesuw is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._przesuw)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._przesuw = None
        super().mouseReleaseEvent(e)

    # ── stan ──
    def odswiez(self):
        pkt = sum(k.zdobyte() for k in self.karty)
        maks = sum(k.pkt for k in self.karty)
        zrobione = sum(1 for k in self.karty if k.stan)
        self.pasek.setMaximum(len(self.karty))
        self.pasek.setValue(zrobione)
        self.pasek.setFormat("sprawdzone %d z %d  ·  %d pkt" % (zrobione, len(self.karty), pkt))
        self.etykieta_poziom.setText("%s · %d/%d pkt" % (poziom(pkt), pkt, maks))
        self.zapisz_stan()

    def zapisz_stan(self):
        try:
            with open(PLIK_STANU, "w", encoding="utf-8") as f:
                json.dump({"imie": self.imie.text(),
                           "uwagi": self.uwagi.toPlainText(),
                           "punkty": [[k.stan, k.uwaga] for k in self.karty]}, f)
        except Exception:
            pass

    def wczytaj_stan(self):
        try:
            with open(PLIK_STANU, encoding="utf-8") as f:
                d = json.load(f)
            self.imie.setText(d.get("imie", ""))
            self.uwagi.setPlainText(d.get("uwagi", ""))
            for k, (stan, uw) in zip(self.karty, d.get("punkty", [])):
                k.stan = stan
                k.uwaga = uw or ""
                k.pole.setText(k.uwaga)
                k._maluj()
        except Exception:
            pass

    # ── raport ──
    def tekst_raportu(self):
        pkt = sum(k.zdobyte() for k in self.karty)
        maks = sum(k.pkt for k in self.karty)
        w = ["RAPORT TESTERA PMT PLANERA",
             "tester: %s" % (self.imie.text().strip() or "(nie podano)"),
             "data: %s   ·   karta v%s" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M"), WERSJA_KARTY),
             "wynik: %d / %d pkt   ·   poziom: %s" % (pkt, maks, poziom(pkt)), ""]
        for k, dane in zip(self.karty, SCENARIUSZE):
            znak = {T_OK: "[DZIALA]", T_UWAGA: "[UWAGA ]", T_BLAD: "[BLAD  ]"}.get(k.stan, "[ ---- ]")
            w.append("%s %s — %s" % (znak, dane[0], dane[1]))
            if k.uwaga.strip():
                w.append("          uwaga: " + k.uwaga.strip())
        og = self.uwagi.toPlainText().strip()
        if og:
            w += ["", "UWAGI OGÓLNE:", og]
        braki = [d[1] for k, d in zip(self.karty, SCENARIUSZE) if not k.stan]
        if braki:
            w += ["", "JESZCZE NIESPRAWDZONE: " + ", ".join(braki)]
        return "\n".join(w)

    def zapisz_raport(self):
        nazwa = "raport_testera_%s_%s.txt" % (
            (self.imie.text().strip().split()[0] if self.imie.text().strip() else "anonim"),
            datetime.datetime.now().strftime("%Y%m%d_%H%M"))
        sc, _ = QFileDialog.getSaveFileName(
            self, "Zapisz raport", os.path.join(os.path.expanduser("~"), "Desktop", nazwa),
            "Pliki tekstowe (*.txt)")
        if not sc:
            return
        try:
            with open(sc, "w", encoding="utf-8") as f:
                f.write(self.tekst_raportu())
            self.info.setText("Zapisano: " + os.path.basename(sc))
        except Exception as e:
            QMessageBox.warning(self, "Błąd", str(e))

    def kopiuj(self):
        QApplication.clipboard().setText(self.tekst_raportu())
        self.info.setText("Raport skopiowany — wklej go w wiadomości do autora.")

    def certyfikat(self):
        imie = self.imie.text().strip()
        if not imie:
            QMessageBox.information(self, "Certyfikat", "Wpisz imię i nazwisko na górze karty.")
            return
        pkt = sum(k.zdobyte() for k in self.karty)
        maks = sum(k.pkt for k in self.karty)
        px = QPixmap(1000, 620)
        px.fill(QColor("#04140d"))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor("#10b881"), 3))
        p.drawRoundedRect(24, 24, 952, 572, 18, 18)
        p.setPen(QColor("#3fe0a3"))
        p.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        p.drawText(0, 90, 1000, 40, int(Qt.AlignmentFlag.AlignCenter), "PMT PLANER")
        p.setPen(QColor("#eafaf2"))
        p.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
        p.drawText(0, 150, 1000, 60, int(Qt.AlignmentFlag.AlignCenter), "CERTYFIKAT TESTERA")
        p.setPen(QColor("#9fd4b8"))
        p.setFont(QFont("Segoe UI", 13))
        p.drawText(0, 232, 1000, 30, int(Qt.AlignmentFlag.AlignCenter), "zaświadcza, że")
        p.setPen(QColor("#eafaf2"))
        p.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        p.drawText(0, 276, 1000, 50, int(Qt.AlignmentFlag.AlignCenter), imie)
        p.setPen(QColor("#c9eedb"))
        p.setFont(QFont("Segoe UI", 13))
        p.drawText(80, 350, 840, 90, int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
                                          | Qt.TextFlag.TextWordWrap),
                   "sprawdził(a) działanie programu w codziennej pracy i przekazał(a) uwagi, "
                   "dzięki którym narzędzie stało się lepsze dla całego zespołu.")
        p.setPen(QColor("#3fe0a3"))
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(0, 452, 1000, 34, int(Qt.AlignmentFlag.AlignCenter),
                   "%s  ·  %d / %d punktów" % (poziom(pkt), pkt, maks))
        p.setPen(QColor("#7fae9c"))
        p.setFont(QFont("Segoe UI", 11))
        p.drawText(0, 530, 1000, 30, int(Qt.AlignmentFlag.AlignCenter),
                   datetime.datetime.now().strftime("%d.%m.%Y"))
        p.end()
        sc = os.path.join(os.path.expanduser("~"), "Desktop",
                          "certyfikat_testera_%s.png" % imie.split()[0].lower())
        try:
            px.save(sc, "PNG")
            self.info.setText("Certyfikat zapisany na pulpicie.")
        except Exception as e:
            QMessageBox.warning(self, "Błąd", str(e))


_OKNO = None          # utrzymuje okno przy życiu, gdy otwiera je program


def pokaz_karte(rodzic=None):
    """Otwiera kartę testera W PROGRAMIE — jako osobne okno, bez
    uruchamiania czegokolwiek z dysku. Zawsze dostępna, bo jest
    częścią programu."""
    global _OKNO
    try:
        if _OKNO is not None and _OKNO.isVisible():
            _OKNO.raise_()
            _OKNO.activateWindow()
            return True
        _OKNO = Tester()
        _OKNO.setWindowFlag(Qt.WindowType.Window, True)
        if rodzic is not None:
            try:
                g = rodzic.geometry()
                _OKNO.move(g.center().x() - 440, max(0, g.center().y() - 380))
            except Exception:
                pass
        _OKNO.show()
        _OKNO.raise_()
        _OKNO.activateWindow()
        return True
    except Exception:
        return False


def main():
    app = QApplication(sys.argv)
    ikona = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pmt_logo.ico")
    if os.path.exists(ikona):
        app.setWindowIcon(QIcon(ikona))
    w = Tester()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
