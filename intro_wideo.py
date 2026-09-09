# -*- coding: utf-8 -*-
"""
PMT PLANER — intro wideo (warstwa aplikacyjna)
==============================================

Odtwarza prerenderowany film intro (Blender, pmt_intro_geo.py) i rysuje
na nim żywą nakładkę aplikacji:

  • moneta-logo „PMT PLANER" na środku (0–2 s), potem dokowanie w rogu,
  • HUD: TRASA / SIECI / POWRÓT — liczniki liczone z osi czasu filmu,
    z plateau podczas postojów (Żabka, Biedronka),
  • panel meldunków (start, potwierdzenia węzłów, powrót do DOM),
  • pasek RZECZYWISTEGO ładowania aplikacji (callback 0..1) albo
    animacja nieokreślona, gdy postępu nie znamy,
  • przycisk „Pomiń" i klawisz Esc.

Użycie w PMT_Delegacje.py (3 linie):

    from intro_wideo import sprobuj_intro_wideo
    if not sprobuj_intro_wideo(okno_glowne, motyw=motyw,
                               postep_ladowania=moj_postep,
                               po_zakonczeniu=start_aplikacji):
        stare_intro()          # fallback: dotychczasowa animacja QPainter

Moduł jest samowystarczalny i ostrożny: każdy brak (PyQt6, multimedia,
plik MP4) kończy się zwrotem False — nigdy wyjątkiem w aplikacji.

Test bez aplikacji:  python intro_wideo.py [ciemny|jasny]
"""

import os, sys, time

# ── OŚ CZASU FILMU (zgodna z INSTRUKCJA_GEO_INTRO.txt) ─────────────
KM_CALK        = 236.0
T_START_JAZDY  = 1.5          # zjazd kamery 0–1,5 s
CZAS_JAZDY     = 10.5         # czysty ruch
POSTOJE        = [(3.19, 1.8), (6.65, 0.5), (7.93, 0.5), (8.85, 1.8), (11.91, 0.5), (16.07, 0.5)]
T_KONIEC_JAZDY = T_START_JAZDY + CZAS_JAZDY + sum(d for _, d in POSTOJE)  # 17.6
T_IMPULS       = (17.6, 18.5)
T_KONIEC       = 21.1

WEZLY = [   # (sekunda przyjazdu, nazwa, km narastająco, czy postój)
    ( 2.77, "ŻABKA",   29, False),
    ( 3.19, "BIEDRONKA",   38, True ),
    ( 6.27, "ŻABKA",   67, False),
    ( 6.65, "GROSZEK",   75, True ),
    ( 7.93, "STOKROTKA",   93, True ),
    ( 8.85, "ŻABKA",  102, True ),
    (11.02, "BIEDRONKA",  111, False),
    (11.91, "ABC",  131, True ),
    (13.33, "STOKROTKA",  151, False),
    (16.07, "LEWIATAN",  213, True ),
]
LICZBA_SIECI = 3   # BIEDRONKA, ŻABKA, STOKROTKA (trasa Warszawa-Białołęka)

MOTYWY = {
    "ciemny": dict(tekst="#E9FDF4", tekst2="#9AD8C0",
                   chip=(8, 20, 15, 205),  chip_ramka="#10B981",
                   akcent="#10B981", dom="#F59E0B",
                   pasek_tlo=(255, 255, 255, 36), przycisk="#0D392B"),
    "jasny":  dict(tekst="#07281D", tekst2="#256A52",
                   chip=(255, 255, 255, 215), chip_ramka="#0E9F6E",
                   akcent="#0E9F6E", dom="#B45309",
                   pasek_tlo=(0, 0, 0, 40),   przycisk="#D9F3E7"),
}


def przelicz_km(t):
    """Kilometry przejechane w sekundzie t filmu (stoją w postojach)."""
    if t <= T_START_JAZDY:
        return 0.0
    t = min(t, T_KONIEC_JAZDY)
    postoj = 0.0
    for ta, d in POSTOJE:
        if t > ta:
            postoj += min(t - ta, d)
    ruch = (t - T_START_JAZDY) - postoj
    return max(0.0, min(KM_CALK, ruch / CZAS_JAZDY * KM_CALK))


def zbuduj_meldunki():
    m = [(0.4, "PMT PLANER — inicjalizacja systemu")]
    m.append((T_START_JAZDY, f"Delegacja rozpoczęta · {KM_CALK:.1f} km trasy"))
    for ta, nazwa, km, postoj in WEZLY:
        m.append((ta, f"{nazwa} · {km} km — potwierdzono ✓"))
        if postoj:
            m.append((ta + 0.6, f"Postój: wizyta w {nazwa.title()}"))
    m.append((T_IMPULS[0], "Powrót do DOM — delegacja rozliczona ✓"))
    m.append((T_IMPULS[1] + 0.3, "System gotowy do pracy"))
    return m


def _znajdz_wideo(katalog_zasobow, motyw):
    """Zwraca ścieżkę MP4 dla motywu albo None."""
    nazwy = (["intro_zmierzch.mp4", "intro_zloty.mp4"] if motyw == "ciemny"
             else ["intro_zloty.mp4", "intro_zmierzch.mp4"])
    kandydaci = []
    if katalog_zasobow:
        kandydaci.append(katalog_zasobow)
        kandydaci.append(os.path.join(katalog_zasobow, "zasoby"))
    baza = os.path.dirname(os.path.abspath(__file__))
    kandydaci += [os.path.join(baza, "zasoby"), baza, os.getcwd()]
    for kat in kandydaci:
        for n in nazwy:
            p = os.path.join(kat, n)
            if os.path.isfile(p):
                return p
    return None


# ═══════════════════════════════════════════════════════════════════
def sprobuj_intro_wideo(rodzic, motyw="ciemny", postep_ladowania=None,
                        po_zakonczeniu=None, katalog_zasobow=None,
                        pomijalne=True):
    """Uruchamia intro wideo nad oknem `rodzic`.

    Zwraca True, jeśli intro wystartowało (wtedy `po_zakonczeniu`
    zostanie wywołane po filmie/pominięciu). Zwraca False, gdy czegoś
    brakuje (PyQt6-Multimedia, plik MP4) — wtedy wywołujący odpala
    dotychczasowe intro. Nigdy nie rzuca wyjątku.
    """
    try:
        from PyQt6.QtCore import Qt, QTimer, QUrl, QEvent, QRectF
        from PyQt6.QtGui import (QPainter, QColor, QFont, QPen, QBrush,
                                 QLinearGradient, QFontMetrics, QPixmap)
        from PyQt6.QtWidgets import QWidget, QPushButton
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PyQt6.QtMultimediaWidgets import QVideoWidget
    except Exception as e:
        print("intro_wideo: brak PyQt6/Multimedia →", e)
        return False

    plik = _znajdz_wideo(katalog_zasobow, motyw)
    if not plik:
        print("intro_wideo: nie znaleziono intro_zmierzch/zloty.mp4")
        return False
    pal = MOTYWY.get(motyw, MOTYWY["ciemny"])
    meldunki = zbuduj_meldunki()

    class _Intro(QWidget):
        def __init__(self, rodzic):
            super().__init__(rodzic)
            self._rodzic = rodzic
            self._t0 = time.monotonic()
            self._koniec_filmu = False
            self._zamkniete = False
            self.setGeometry(rodzic.rect())
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setStyleSheet("background:#04140D;")
            # wideo
            self.wideo = QVideoWidget(self)
            self.wideo.setGeometry(self.rect())
            try:
                self.wideo.setAspectRatioMode(
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding)
            except Exception:
                pass
            self.player = QMediaPlayer(self)
            self.audio = QAudioOutput(self)
            self.audio.setMuted(True)
            self.player.setAudioOutput(self.audio)
            self.player.setVideoOutput(self.wideo)
            self.player.setSource(QUrl.fromLocalFile(plik))
            self.player.mediaStatusChanged.connect(self._status)
            self.player.errorOccurred.connect(
                lambda *a: self._koniec(True))
            # nakładka
            self.nakladka = QWidget(self)
            self.nakladka.setGeometry(self.rect())
            self.nakladka.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.nakladka.paintEvent = self._maluj
            self._rozpad = None
            self._po_wywolane = False
            self._logo_pix = None
            try:
                for _kat in (katalog_zasobow, os.path.dirname(plik)):
                    if not _kat:
                        continue
                    _lp = os.path.join(_kat, "logo_pmt.png")
                    if os.path.exists(_lp):
                        _px = QPixmap(_lp)
                        if not _px.isNull():
                            self._logo_pix = _px
                            break
            except Exception:
                pass
            # przycisk Pomiń
            self.btn = QPushButton("Pomiń  (Esc)", self)
            self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn.setStyleSheet(
                "QPushButton{background:%s;color:%s;border:1px solid %s;"
                "border-radius:14px;padding:6px 16px;font-weight:600;}"
                "QPushButton:hover{border-color:%s;}"
                % (pal["przycisk"], pal["tekst"], pal["chip_ramka"],
                   pal["akcent"]))
            self.btn.clicked.connect(lambda: self._koniec(True))
            self.btn.setVisible(False)
            self._ustaw_geometrie()
            rodzic.installEventFilter(self)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._tik)
            self.timer.start(33)
            self.raise_(); self.show()
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.setFocus()
            self.player.play()

        # ── zdarzenia ──
        def eventFilter(self, obj, ev):
            if obj is self._rodzic and ev.type() in (
                    QEvent.Type.Resize, QEvent.Type.Show):
                self._ustaw_geometrie()
            return False

        def keyPressEvent(self, ev):
            if ev.key() == Qt.Key.Key_Escape and pomijalne:
                self._koniec(True)

        def _ustaw_geometrie(self):
            r = self._rodzic.rect()
            self.setGeometry(r)
            self.wideo.setGeometry(self.rect())
            self.nakladka.setGeometry(self.rect())
            self.btn.move(self.width() - self.btn.sizeHint().width() - 22,
                          self.height() - 46)
            self.nakladka.raise_(); self.btn.raise_()

        def _status(self, st):
            from PyQt6.QtMultimedia import QMediaPlayer as MP
            if st == MP.MediaStatus.EndOfMedia:
                self._koniec_filmu = True
                try:
                    self.player.pause()
                except Exception:
                    pass

        # ── logika czasu ──
        def _t(self):
            return time.monotonic() - self._t0

        def _postep(self):
            if postep_ladowania is None:
                return None
            try:
                return max(0.0, min(1.0, float(postep_ladowania())))
            except Exception:
                return None

        def _tik(self):
            if self._zamkniete:
                return
            t = self._t()
            p = self._postep()
            gotowe = (p is None) or (p >= 1.0)
            if pomijalne and not self.btn.isVisible() and (
                    t > 2.5 or (p is not None and p >= 1.0)):
                self.btn.setVisible(True)
            if (t >= T_KONIEC or self._koniec_filmu) and gotowe:
                self._koniec(False)
                return
            self.nakladka.update()

        def _koniec(self, natychmiast):
            if self._zamkniete:
                return
            if not natychmiast and self._rozpad is None:
                try:
                    self._start_rozpadu()
                    return
                except Exception as e:
                    print("intro_wideo: rozpad pominięty:", e)
            self._zamkniete = True
            try:
                self.timer.stop()
                self.player.stop()
            except Exception:
                pass
            self.hide(); self.deleteLater()
            if po_zakonczeniu and not self._po_wywolane:
                self._po_wywolane = True
                try:
                    po_zakonczeniu()
                except Exception as e:
                    print("intro_wideo: błąd po_zakonczeniu:", e)

        def _start_rozpadu(self):
            pix = self.grab()
            if po_zakonczeniu and not self._po_wywolane:
                self._po_wywolane = True
                try:
                    po_zakonczeniu()
                except Exception as e:
                    print("intro_wideo: błąd po_zakonczeniu:", e)
            try:
                self.player.stop(); self.wideo.hide(); self.btn.hide()
            except Exception:
                pass
            self.setStyleSheet("background:transparent;")
            self.setAttribute(
                Qt.WidgetAttribute.WA_TranslucentBackground, True)
            import random as _r
            W, H = max(1, pix.width()), max(1, pix.height())
            nx, ny = 8, 5
            cw, ch = W / nx, H / ny
            kaf = []
            for iy in range(ny):
                for ix in range(nx):
                    r = pix.copy(int(ix*cw), int(iy*ch),
                                 int(cw)+1, int(ch)+1)
                    cxk = ix*cw + cw/2 - W/2
                    cyk = iy*ch + ch/2 - H/2
                    kaf.append([r, ix*cw, iy*ch,
                                cxk*2.4 + _r.uniform(-80, 80),
                                cyk*2.4 + _r.uniform(-80, 80),
                                _r.uniform(-160, 160)])
            self._rozpad = {"t0": time.monotonic(),
                            "kafle": kaf, "dur": 0.75}
            self._rt = QTimer(self)
            self._rt.timeout.connect(self.nakladka.update)
            self._rt.start(16)

        # ── rysowanie nakładki ──
        def _maluj(self, ev):
            t = self._t()
            w, h = self.nakladka.width(), self.nakladka.height()
            q = QPainter(self.nakladka)
            q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            if self._rozpad:
                _rz = self._rozpad
                p = min(1.0, (time.monotonic()-_rz["t0"])/_rz["dur"])
                ease = p*p
                for r, x0, y0, vx, vy, vr in _rz["kafle"]:
                    q.save()
                    q.translate(x0+vx*ease+r.width()/2,
                                y0+vy*ease+r.height()/2)
                    q.rotate(vr*ease)
                    q.setOpacity(max(0.0, 1.0-p*1.15))
                    q.drawPixmap(int(-r.width()/2),
                                 int(-r.height()/2), r)
                    q.restore()
                q.end()
                if p >= 1.0:
                    self._rozpad = None
                    try:
                        self._rt.stop()
                    except Exception:
                        pass
                    self._koniec(True)
                return
            tx = QColor(pal["tekst"]); tx2 = QColor(pal["tekst2"])
            ak = QColor(pal["akcent"]); dom = QColor(pal["dom"])
            chip = QColor(*pal["chip"])

            def zaokr(x, y, sw, sh, r, kolor, ramka=None):
                q.setPen(QPen(QColor(ramka), 1) if ramka else
                         Qt.PenStyle.NoPen)
                q.setBrush(QBrush(kolor))
                q.drawRoundedRect(QRectF(x, y, sw, sh), r, r)

            # 1) moneta-logo: środek → dok w rogu
            uu = max(0.0, min(1.0, (t - T_START_JAZDY) / 0.7))
            e = uu * uu * (3 - 2 * uu)
            duzy = min(w, h) * 0.115
            maly = 26.0
            cx = (w / 2) * (1 - e) + (30 + maly) * e
            cy = (h / 2 - duzy * 0.2) * (1 - e) + (30 + maly) * e
            rr = duzy * (1 - e) + maly * e
            pojaw = max(0.0, min(1.0, t / 0.8))
            q.setOpacity(pojaw)
            g = QLinearGradient(cx - rr, cy - rr, cx + rr, cy + rr)
            g.setColorAt(0, QColor("#123B2C")); g.setColorAt(1, QColor("#0A241A"))
            q.setBrush(QBrush(g)); q.setPen(QPen(ak, max(2.0, rr * 0.10)))
            q.drawEllipse(QRectF(cx - rr, cy - rr, 2 * rr, 2 * rr))
            if self._logo_pix is not None:
                _sp = self._logo_pix.scaledToWidth(
                    int(rr*1.55),
                    Qt.TransformationMode.SmoothTransformation)
                q.drawPixmap(int(cx-_sp.width()/2),
                             int(cy-_sp.height()/2), _sp)
            else:
                f = QFont("Segoe UI", -1, QFont.Weight.Black)
                f.setPixelSize(int(rr * 0.62))
                q.setFont(f); q.setPen(QPen(tx))
                q.drawText(QRectF(cx - rr, cy - rr, 2*rr, 2*rr),
                           Qt.AlignmentFlag.AlignCenter, "PMT")
            try:
                _pp = max(0.0, min(1.0, self._postep()))
            except Exception:
                _pp = uu
            q.setBrush(Qt.BrushStyle.NoBrush)
            q.setPen(QPen(QColor(18, 48, 36, 210), max(3.0, rr*0.14)))
            q.drawArc(QRectF(cx-rr*1.28, cy-rr*1.28, 2.56*rr, 2.56*rr),
                      0, 360*16)
            q.setPen(QPen(ak, max(3.0, rr*0.14)))
            q.drawArc(QRectF(cx-rr*1.28, cy-rr*1.28, 2.56*rr, 2.56*rr),
                      90*16, -int(360*16*_pp))
            if e < 0.55:
                f2 = QFont("Segoe UI", -1, QFont.Weight.DemiBold)
                f2.setPixelSize(int(duzy * 0.34))
                f2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
                q.setFont(f2); q.setOpacity(pojaw * (1 - e / 0.55))
                q.setPen(QPen(tx))
                q.drawText(QRectF(0, cy + rr + 8, w, duzy),
                           Qt.AlignmentFlag.AlignHCenter |
                           Qt.AlignmentFlag.AlignTop, "PMT PLANER")
            q.setOpacity(1.0)

            # 2) chipy HUD po zadokowaniu
            if e >= 0.999:
                km = przelicz_km(t)
                sieci = len({n for ta, n, _, _ in WEZLY if ta <= t})
                dane = [("TRASA",  f"{km:5.1f} km", ak),
                        ("SIECI",  f"{sieci}/{LICZBA_SIECI}", tx2),
                        ("POWRÓT", f"{KM_CALK - km:5.1f} km", dom)]
                y = 30 + maly * 2 + 14
                f3 = QFont("Segoe UI"); f3.setPixelSize(12); 
                for tytul, wart, kol in dane:
                    zaokr(24, y, 150, 40, 9, chip, pal["chip_ramka"])
                    q.setFont(f3); q.setPen(QPen(tx2))
                    q.drawText(QRectF(36, y + 5, 130, 14),
                               Qt.AlignmentFlag.AlignLeft, tytul)
                    f4 = QFont("Consolas"); f4.setPixelSize(17)
                    f4.setBold(True)
                    q.setFont(f4); q.setPen(QPen(kol))
                    q.drawText(QRectF(36, y + 18, 130, 20),
                               Qt.AlignmentFlag.AlignLeft, wart)
                    y += 48

            # 3) meldunki (ostatnie 3, wygaszane wiekiem)
            akt = [(ta, ms) for ta, ms in meldunki if ta <= t][-3:]
            fy = h - 118
            f5 = QFont("Segoe UI"); f5.setPixelSize(13)
            fm = QFontMetrics(f5)
            for ta, ms in akt:
                wiek = t - ta
                al = 1.0 if wiek < 5 else max(0.25, 1 - (wiek - 5) / 6)
                q.setOpacity(al)
                sw = fm.horizontalAdvance(ms) + 30
                zaokr(24, fy, sw, 28, 8, chip, pal["chip_ramka"])
                q.setFont(f5); q.setPen(QPen(tx))
                q.drawText(QRectF(39, fy, sw - 20, 28),
                           Qt.AlignmentFlag.AlignVCenter, ms)
                fy -= 34
            q.setOpacity(1.0)

            # 4) pasek rzeczywistego ładowania
            p = self._postep()
            pw = int(w * 0.42); px0 = (w - pw) // 2; py0 = h - 42
            zaokr(px0, py0, pw, 8, 4, QColor(*pal["pasek_tlo"]))
            if p is None:
                # animacja nieokreślona: wędrujący segment
                seg = pw * 0.22
                x = px0 + ((t * 160.0) % (pw + seg)) - seg
                zaokr(max(px0, x), py0,
                      min(seg, px0 + pw - max(px0, x)), 8, 4, ak)
                opis = "Ładowanie systemu…"
            else:
                zaokr(px0, py0, max(6, int(pw * p)), 8, 4, ak)
                opis = ("Gotowe — kończenie intro…" if p >= 1.0
                        else f"Ładowanie systemu…  {int(p * 100)} %")
            f6 = QFont("Segoe UI"); f6.setPixelSize(11)
            q.setFont(f6); q.setPen(QPen(tx2))
            q.drawText(QRectF(px0, py0 - 20, pw, 16),
                       Qt.AlignmentFlag.AlignHCenter, opis)
            q.end()

    try:
        _Intro(rodzic)
        return True
    except Exception as e:
        print("intro_wideo: start nieudany →", e)
        return False


# ── szybki test bez aplikacji ──────────────────────────────────────
if __name__ == "__main__":
    try:
        from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
        from PyQt6.QtCore import Qt
    except Exception as e:
        print("Do testu potrzebny PyQt6:", e); sys.exit(1)
    motyw = sys.argv[1] if len(sys.argv) > 1 else "ciemny"
    app = QApplication(sys.argv)
    okno = QMainWindow(); okno.resize(1280, 720)
    okno.setWindowTitle("PMT PLANER — test intro")
    ety = QLabel("TU JEST APLIKACJA (po intro)",
                 alignment=Qt.AlignmentFlag.AlignCenter)
    ety.setStyleSheet("font-size:24px;")
    okno.setCentralWidget(ety); okno.show()
    t0 = time.monotonic()
    ok = sprobuj_intro_wideo(
        okno, motyw=motyw,
        postep_ladowania=lambda: (time.monotonic() - t0) / 6.0,
        po_zakonczeniu=lambda: print("intro zakończone → start aplikacji"))
    print("sprobuj_intro_wideo →", ok)
    if ok:
        sys.exit(app.exec())
