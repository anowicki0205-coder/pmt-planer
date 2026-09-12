# -*- coding: utf-8 -*-
"""Taca gotowych dokumentów oraz panele podpisu i wysyłki.

Taca wysuwa się od dołu po wygenerowaniu i zostaje NAD programem, żeby nie
trzeba było szukać plików w folderze. Panele podpisu i wysyłki otwierają się
z tacy. Zgodnie z wolą właściciela nigdzie nie tłumaczymy działania programu —
są nazwy, liczby i stany.
"""
from PyQt6.QtCore import Qt, QRectF, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor, QLinearGradient, QBrush
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLabel, QPushButton, QLineEdit, QComboBox, QRadioButton,
                             QButtonGroup, QProgressBar, QFrame)

import proto_styl as S
import proto_dane as D


# ── kafel jednego dokumentu ──────────────────────────────────────────
class KafelDokumentu(QWidget):
    def __init__(self, dzien, numer, rodzic=None):
        super().__init__(rodzic)
        self.dzien = dzien
        self.numer = numer
        self.setFixedSize(154, 150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -8)
        S.cien(p, r, 8, sila=110, rozmycie=10, przesun=4)
        # papier z grubością
        sciezka = QPainterPath(); sciezka.addRoundedRect(r, 7, 7)
        p.fillPath(sciezka, QBrush(S.PAPIER))
        p.fillRect(QRectF(r.x() + 5, r.bottom() - 1.5, r.width() - 10, 1.5),
                   QColor(200, 194, 182))
        d = self.dzien
        data = f"{d.data.day:02d}.{d.data.month:02d}"
        S.tekst(p, r.x() + 11, r.y() + 22, data, S.PAPIER_TEKST, 14, 700)
        S.tekst(p, r.x() + 11, r.y() + 37, D.DNI_PL[d.data.weekday()], QColor(120, 130, 148), 10, 400)
        S.tekst(p, r.x() + 11, r.y() + 58, f"POLECENIE WYJAZDU", QColor(120, 130, 148), 8, 600, odstep=0.4)
        S.tekst(p, r.x() + 11, r.y() + 70, f"NR 2026/09/{self.numer:02d}", QColor(120, 130, 148), 8, 400)
        # imitacja wierszy dokumentu
        for i in range(3):
            y = r.y() + 82 + i * 8
            p.fillRect(QRectF(r.x() + 11, y, (r.width() - 30) * (0.9 - i * 0.13), 2.5),
                       QColor(196, 202, 214))
        # stopka kafla
        S.tekst(p, r.x() + 11, r.bottom() - 12, f"{d.km:.0f} km", QColor(120, 130, 148), 10, 500, mono=True)
        napis = f"{D.zl(d.kwota)} zł"
        p.setFont(S.czcionka(11, 700, mono=True))
        szer = p.fontMetrics().horizontalAdvance(napis)
        S.tekst(p, r.right() - 11 - szer, r.bottom() - 12, napis, S.PAPIER_TEKST, 11, 700, mono=True)
        # plakietka PDF
        pr = QRectF(r.right() - 42, r.y() + 10, 32, 15)
        pp = QPainterPath(); pp.addRoundedRect(pr, 4, 4)
        p.fillPath(pp, QBrush(S.z_alfa(S.ZIELEN, 210)))
        S.tekst(p, pr.x() + 7, pr.y() + 11, "PDF", QColor("#04121A"), 9, 700)
        if d.podpisany:
            p.setPen(QPen(S.z_alfa(S.ZIELEN, 220), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(sciezka)
            p.save()
            p.translate(r.center().x(), r.bottom() - 48)
            p.rotate(-7)
            pieczec = QRectF(-50, -11, 100, 22)
            pp2 = QPainterPath(); pp2.addRoundedRect(pieczec, 5, 5)
            p.fillPath(pp2, QBrush(S.z_alfa(S.ZIELEN, 40)))
            p.setPen(QPen(S.z_alfa(S.ZIELEN, 190), 1.2)); p.drawPath(pp2)
            S.tekst(p, -42, -1, "PODPISANO", QColor("#0B7A5A"), 10, 700, odstep=0.6)
            S.tekst(p, -42, 8, "profil zaufany · 14:20", QColor("#2E8B72"), 7, 500)
            p.restore()
        p.end()


# ── taca ─────────────────────────────────────────────────────────────
class TacaDokumentow(QWidget):
    zwin = pyqtSignal()
    otworz_podpis = pyqtSignal()
    otworz_wysylke = pyqtSignal()
    otworz_wszystkie = pyqtSignal()

    def __init__(self, rodzic=None):
        super().__init__(rodzic)
        self.dni = []
        self._buduj()

    def _buduj(self):
        z = QVBoxLayout(self)
        z.setContentsMargins(26, 22, 26, 20)
        z.setSpacing(14)

        gora = QHBoxLayout(); gora.setSpacing(16)
        lewo = QVBoxLayout(); lewo.setSpacing(2)
        self.l_tytul = QLabel("Otwórz dokumenty")
        self.l_tytul.setFont(S.czcionka(24, 700, naglowek=True))
        self.l_sciezka = QLabel("")
        self.l_sciezka.setFont(S.czcionka(12))
        self.l_sciezka.setStyleSheet(f"color: {S.TEKST_2.name()};")
        lewo.addWidget(self.l_tytul); lewo.addWidget(self.l_sciezka)
        gora.addLayout(lewo); gora.addStretch(1)

        self.liczby = QHBoxLayout(); self.liczby.setSpacing(10)
        gora.addLayout(self.liczby)
        b_zwin = QPushButton("Zwiń tacę")
        b_zwin.clicked.connect(self.zwin.emit)
        gora.addWidget(b_zwin)
        z.addLayout(gora)

        self.pas = QHBoxLayout(); self.pas.setSpacing(10)
        z.addLayout(self.pas)

        dol = QHBoxLayout(); dol.setSpacing(10)
        self.l_stan = QLabel("")
        self.l_stan.setFont(S.czcionka(12, 600))
        self.l_stan.setStyleSheet(f"color: {S.MIETA.name()};")
        dol.addWidget(self.l_stan); dol.addStretch(1)
        b_folder = QPushButton("Otwórz folder")
        b_podpis = QPushButton("Podpisz elektronicznie"); b_podpis.setProperty("rola", "zielony")
        b_mail = QPushButton("Wyślij e-mailem"); b_mail.setProperty("rola", "zielony")
        b_wszystkie = QPushButton("Otwórz wszystkie dokumenty"); b_wszystkie.setProperty("rola", "glowny")
        for b in (b_folder, b_podpis, b_mail, b_wszystkie):
            b.setMinimumHeight(40); dol.addWidget(b)
        b_podpis.clicked.connect(self.otworz_podpis.emit)
        b_mail.clicked.connect(self.otworz_wysylke.emit)
        b_wszystkie.clicked.connect(self.otworz_wszystkie.emit)
        z.addLayout(dol)

    def _kafel_liczby(self, wartosc, opis, wyroznij=False):
        w = QFrame(); w.setFixedSize(148, 56)
        w.setStyleSheet(
            "QFrame { background: rgba(9,16,28,200); border-radius: 12px; border: 1px solid %s; }"
            % ("rgba(0,228,161,0.55)" if wyroznij else "rgba(255,255,255,0.10)"))
        l = QVBoxLayout(w); l.setContentsMargins(12, 7, 12, 7); l.setSpacing(0)
        a = QLabel(wartosc); a.setFont(S.czcionka(17, 700, mono=True))
        a.setStyleSheet(f"color: {(S.MIETA if wyroznij else S.TEKST).name()}; border: none;")
        b = QLabel(opis); b.setFont(S.czcionka(9, 600, odstep=0.6))
        b.setStyleSheet(f"color: {S.TEKST_3.name()}; border: none;")
        l.addWidget(a); l.addWidget(b)
        return w

    def ustaw_dni(self, dni, folder="Pulpit / Rozliczenie_Anna_Nowak_wrzesień_2026r"):
        self.dni = [d for d in dni if not d.wolny and not d.wylaczony]
        p = D.podsumowanie(dni)
        self.l_sciezka.setText(f"wrzesień 2026 · {len(self.dni) + 1} plików PDF w  {folder}")
        while self.liczby.count():
            it = self.liczby.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self.liczby.addWidget(self._kafel_liczby(f"{D.zl(p['kwota'])} zł", "CO DO GROSZA", True))
        self.liczby.addWidget(self._kafel_liczby(f"{p['km']:,.0f}".replace(",", " ") + " km", "REALNE DROGI"))
        self.liczby.addWidget(self._kafel_liczby(f"{p['dni']} z {p['dni_wszystkie']}", "DELEGACJE"))
        while self.pas.count():
            it = self.pas.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        for i, d in enumerate(self.dni[:7], start=1):
            self.pas.addWidget(KafelDokumentu(d, i))
        self.pas.addStretch(1)
        ile = sum(1 for d in self.dni if d.podpisany)
        self.l_stan.setText(f"{ile} z {len(self.dni)} podpisanych" if ile else "")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        sciezka = QPainterPath()
        sciezka.addRoundedRect(r.adjusted(0, 0, 0, 26), 26, 26)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0.0, QColor(22, 38, 58, 248))
        g.setColorAt(1.0, QColor(11, 19, 32, 252))
        p.fillPath(sciezka, QBrush(g))
        p.fillRect(QRectF(r.x() + 26, r.y(), r.width() - 52, 1.2), S.z_alfa(S.CYJAN, 120))
        p.setPen(QPen(S.OBRYS_MOCNY, 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(sciezka)
        ucho = QRectF(r.center().x() - 24, r.y() + 8, 48, 3)
        pu = QPainterPath(); pu.addRoundedRect(ucho, 1.5, 1.5)
        p.fillPath(pu, QBrush(S.z_alfa(QColor(255, 255, 255), 60)))
        p.end()


# ── wspólna podstawa paneli ──────────────────────────────────────────
class Panel(QDialog):
    def __init__(self, tytul, rodzic=None):
        super().__init__(rodzic)
        self.setWindowTitle(tytul)
        self.setModal(True)
        self.setStyleSheet(S.qss())
        self.setMinimumWidth(560)
        self.z = QVBoxLayout(self)
        self.z.setContentsMargins(24, 20, 24, 20)
        self.z.setSpacing(14)
        t = QLabel(tytul); t.setFont(S.czcionka(18, 700, naglowek=True))
        self.z.addWidget(t)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        S.tlo_sceny(p, r, plamy=False)
        S.szklo(p, r, 16, mocne=True)
        p.end()

    def wiersz(self, etykieta, widget):
        w = QHBoxLayout(); w.setSpacing(12)
        l = QLabel(etykieta); l.setFixedWidth(120)
        l.setFont(S.czcionka(10, 600, odstep=0.6))
        l.setStyleSheet(f"color: {S.TEKST_3.name()};")
        w.addWidget(l); w.addWidget(widget, 1)
        self.z.addLayout(w)
        return widget


class PanelPodpisu(Panel):
    """Wybór bezpłatnej ścieżki podpisu i jego przebieg."""
    def __init__(self, dni, rodzic=None):
        super().__init__("Podpisz elektronicznie", rodzic)
        self.dni = dni
        self.grupa = QButtonGroup(self)
        for i, (nazwa, opis) in enumerate((
                ("Profil zaufany", "gov.pl · bezpłatny"),
                ("e-dowód · podpis osobisty", "dowód z certyfikatem · NFC lub czytnik"),
                ("Mam już podpisany plik", "wskaż plik z dysku"))):
            r = QRadioButton(f"  {nazwa}          {opis}")
            r.setFont(S.czcionka(13, 600 if i == 0 else 400))
            r.setMinimumHeight(42)
            if i == 0: r.setChecked(True)
            self.grupa.addButton(r, i)
            self.z.addWidget(r)
        self.z.addSpacing(6)
        self.postep = QProgressBar(); self.postep.setRange(0, len(dni) or 1)
        self.postep.setTextVisible(False); self.postep.setFixedHeight(6)
        self.postep.setStyleSheet(
            "QProgressBar { background: rgba(255,255,255,0.08); border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: %s; border-radius: 3px; }" % S.CYJAN.name())
        self.z.addWidget(self.postep)
        self.l_stan = QLabel("gotowe do podpisu: %d" % len(dni))
        self.l_stan.setFont(S.czcionka(12)); self.l_stan.setStyleSheet(f"color: {S.TEKST_2.name()};")
        self.z.addWidget(self.l_stan)
        d = QHBoxLayout(); d.addStretch(1)
        self.b_anuluj = QPushButton("Anuluj"); self.b_anuluj.clicked.connect(self.reject)
        self.b_dalej = QPushButton("Dalej"); self.b_dalej.setProperty("rola", "glowny")
        self.b_dalej.setMinimumWidth(130); self.b_dalej.clicked.connect(self._dalej)
        d.addWidget(self.b_anuluj); d.addWidget(self.b_dalej)
        self.z.addLayout(d)
        self._licznik = 0
        self._zegar = QTimer(self); self._zegar.timeout.connect(self._tyk)

    def _dalej(self):
        self.b_dalej.setEnabled(False)
        for b in self.grupa.buttons(): b.setEnabled(False)
        self.l_stan.setText("czekam na podpisane pliki…")
        self._zegar.start(420)

    def _tyk(self):
        self._licznik += 1
        self.postep.setValue(self._licznik)
        self.l_stan.setText(f"{self._licznik} z {len(self.dni)} podpisanych")
        if self._licznik >= len(self.dni):
            self._zegar.stop()
            self.postep.setStyleSheet(
                "QProgressBar { background: rgba(255,255,255,0.08); border: none; border-radius: 3px; }"
                "QProgressBar::chunk { background: %s; border-radius: 3px; }" % S.ZIELEN.name())
            self.l_stan.setText(f"podpisano {len(self.dni)} z {len(self.dni)} · profil zaufany")
            self.b_dalej.setText("Zamknij"); self.b_dalej.setEnabled(True)
            try: self.b_dalej.clicked.disconnect()
            except Exception: pass
            self.b_dalej.clicked.connect(self.accept)

    def reject(self):
        self._zegar.stop(); super().reject()

    def accept(self):
        self._zegar.stop(); super().accept()


class PanelWysylki(Panel):
    """Adresat, gotowy temat i załączniki."""
    def __init__(self, dni, rodzic=None):
        super().__init__("Wyślij e-mailem", rodzic)
        self.dni = dni
        self.e_do = self.wiersz("DO", QLineEdit("kadry@pmt.pl"))
        self.e_dw = self.wiersz("DW", QLineEdit(""))
        temat = f"Delegacje — {D.PRACOWNIK} — {D.nazwa_miesiaca(9)} 2026"
        self.e_temat = self.wiersz("TEMAT", QLineEdit(temat))
        self.e_temat.setFont(S.czcionka(13, 600))
        lista = QLabel("\n".join(
            f"delegacja_{i:02d}_{D.PRACOWNIK.replace(' ', '_')}_wrzesień_2026r.pdf"
            for i in range(1, min(len(dni), 6) + 1)) + f"\n… razem {len(dni) + 1} plików")
        lista.setFont(S.czcionka(11, mono=True))
        lista.setStyleSheet(f"color: {S.TEKST_2.name()};")
        self.wiersz("ZAŁĄCZNIKI", lista)
        self.postep = QProgressBar(); self.postep.setRange(0, len(dni) + 1)
        self.postep.setTextVisible(False); self.postep.setFixedHeight(6)
        self.postep.setStyleSheet(
            "QProgressBar { background: rgba(255,255,255,0.08); border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: %s; border-radius: 3px; }" % S.ZIELEN.name())
        self.z.addWidget(self.postep)
        self.l_stan = QLabel(""); self.l_stan.setFont(S.czcionka(12))
        self.l_stan.setStyleSheet(f"color: {S.TEKST_2.name()};")
        self.z.addWidget(self.l_stan)
        d = QHBoxLayout(); d.addStretch(1)
        b_anuluj = QPushButton("Anuluj"); b_anuluj.clicked.connect(self.reject)
        self.b_wyslij = QPushButton("Wyślij"); self.b_wyslij.setProperty("rola", "glowny")
        self.b_wyslij.setMinimumWidth(130); self.b_wyslij.clicked.connect(self._wyslij)
        d.addWidget(b_anuluj); d.addWidget(self.b_wyslij)
        self.z.addLayout(d)
        self._i = 0
        self._zegar = QTimer(self); self._zegar.timeout.connect(self._tyk)

    def _wyslij(self):
        self.b_wyslij.setEnabled(False)
        self._zegar.start(260)

    def _tyk(self):
        self._i += 1
        self.postep.setValue(self._i)
        self.l_stan.setText(f"{self._i} z {len(self.dni) + 1} załączników")
        if self._i >= len(self.dni) + 1:
            self._zegar.stop()
            self.l_stan.setText(f"wysłano 14:26 · {self.e_do.text()} · {len(self.dni) + 1} załączników")
            self.b_wyslij.setText("Zamknij"); self.b_wyslij.setEnabled(True)
            try: self.b_wyslij.clicked.disconnect()
            except Exception: pass
            self.b_wyslij.clicked.connect(self.accept)

    def reject(self):
        self._zegar.stop(); super().reject()

    def accept(self):
        self._zegar.stop(); super().accept()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dni = D.oblicz_miesiac(1850, wolne=(14, 15))
    okno = QWidget(); okno.resize(1440, 430)
    okno.setStyleSheet(S.qss())
    l = QVBoxLayout(okno); l.setContentsMargins(0, 0, 0, 0)
    taca = TacaDokumentow(); taca.ustaw_dni(dni)
    l.addStretch(1); l.addWidget(taca)
    okno.show()
    if "--zrzut" in sys.argv:
        okno.grab().save("zrzut_taca.png")
        print("zapisano zrzut_taca.png")
        sys.exit(0)
    sys.exit(app.exec())
