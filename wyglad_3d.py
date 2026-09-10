# -*- coding: utf-8 -*-
"""
WYGLĄD 3D — głębia dla całego interfejsu PMT Planera.

Nie przerysowuje programu od nowa: dokłada warstwę przestrzeni do tego,
co już jest. Trzy zabiegi, te same, których używa się w interfejsach
mobilnych i w Material Design:

  1. CIEŃ RZUCANY  — każda karta, panel i przycisk unosi się nad tłem;
     im ważniejszy element, tym wyżej (większe rozmycie i przesunięcie).
  2. UNIESIENIE POD KURSOREM — najechanie myszą podnosi element:
     cień się rozlewa, krawędź rozjaśnia. To daje wrażenie dotykania
     fizycznego obiektu.
  3. WYPUKŁA KRAWĘDŹ — jasna linia u góry i ciemniejsza u dołu, czyli
     klasyczny sposób na wypukłość: światło pada z góry.

Wyłączenie: plik BEZ_3D.txt obok programu albo zastosuj(okno, wlaczone=False).
"""

import os

try:
    from PyQt6.QtCore import Qt, QEvent, QPropertyAnimation, QEasingCurve, QObject
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import (QGraphicsDropShadowEffect, QPushButton, QFrame,
                                 QGroupBox, QAbstractScrollArea, QWidget)
except Exception:            # brak PyQt — moduł milczy
    Qt = None

# elementy rozpoznawane jako „karty" (unoszą się najwyżej)
KARTY = ("PmtKarta", "WykBox", "WykBoxDel", "karta", "panel", "Panel")
# elementy paska górnego i belek — unoszą się nad treścią
BELKI = ("topbar", "TopBar", "pasek", "Pasek", "sidebar", "SideBar")


def _cien(widget, rozmycie, y, alfa, kolor=(0, 0, 0)):
    ef = QGraphicsDropShadowEffect(widget)
    ef.setBlurRadius(rozmycie)
    ef.setXOffset(0)
    ef.setYOffset(y)
    ef.setColor(QColor(kolor[0], kolor[1], kolor[2], alfa))
    widget.setGraphicsEffect(ef)
    return ef


class _Uniesienie(QObject):
    """Podnosi element pod kursorem — płynnie, bez skoków."""

    def __init__(self, rodzic, spoczynek, uniesienie):
        super().__init__(rodzic)
        self.spoczynek = spoczynek
        self.uniesienie = uniesienie
        self.anim = {}

    def _animuj(self, w, rozmycie, y, alfa):
        ef = w.graphicsEffect()
        if ef is None:
            return
        for wlasciwosc, cel in ((b"blurRadius", rozmycie), (b"yOffset", y)):
            a = QPropertyAnimation(ef, wlasciwosc, w)
            a.setDuration(140)
            a.setEndValue(cel)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        k = ef.color()
        k.setAlpha(alfa)
        ef.setColor(k)

    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QEvent.Type.Enter:
                self._animuj(obj, *self.uniesienie)
            elif ev.type() == QEvent.Type.Leave:
                self._animuj(obj, *self.spoczynek)
        except Exception:
            pass
        return False


def _kolor_tla(w):
    """Odczytuje kolor tła elementu z jego własnego stylu."""
    import re
    for zrodlo in (w.styleSheet() or "", ""):
        m = re.search(r"background(?:-color)?\s*:\s*#([0-9a-fA-F]{6})", zrodlo)
        if m:
            h = m.group(1)
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    try:
        k = w.palette().color(w.backgroundRole())
        if k.alpha() > 200:
            return (k.red(), k.green(), k.blue())
    except Exception:
        pass
    return None


def _jasniej(k, ile):
    return tuple(max(0, min(255, int(v + ile))) for v in k)


def _gradient(w, sila=1.0):
    """Zamienia płaskie tło w gradient: jaśniej u góry, ciemniej u dołu.
    To właśnie ta różnica sprawia, że element wygląda na wypukły.

    Nakładamy go WYŁĄCZNIE na elementy z własną nazwą (objectName) —
    reguła dla nazwy klasy dotyczyłaby wszystkich elementów tego typu
    w oknie i nadpisywała kolory ustawione przez program."""
    if not w.objectName():
        return False
    k = _kolor_tla(w)
    if not k:
        return False
    gora = _jasniej(k, 16 * sila)
    dol = _jasniej(k, -14 * sila)
    nazwa = w.objectName()
    sel = "#%s" % nazwa if nazwa else w.metaObject().className()
    regula = ("\n%s{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
              "stop:0 rgb(%d,%d,%d), stop:1 rgb(%d,%d,%d));}"
              % ((sel,) + gora + dol))
    if regula not in (w.styleSheet() or ""):
        w.setStyleSheet((w.styleSheet() or "") + regula)
    return True


def _powietrze(*a, **k):
    """NIEUŻYWANE — zostawione jako przestroga.

    Rozsuwanie odstępów wyglądało dobrze na przykładzie, ale w programie
    panele mają ustalone wysokości: powiększone marginesy wypychały
    zawartość poza ramkę (znikał wybór trybu pracy). Głębię robimy
    wyłącznie cieniem i gradientem, bez dotykania układów."""
    return


def _wypuklosc(w, ciemny=True, promien=14):
    """Dokłada jasną krawędź u góry i ciemną u dołu — światło z góry."""
    try:
        gora = "rgba(255,255,255,0.10)" if ciemny else "rgba(255,255,255,0.85)"
        dol = "rgba(0,0,0,0.35)" if ciemny else "rgba(0,0,0,0.10)"
        nazwa = w.objectName()
        sel = "#%s" % nazwa if nazwa else w.metaObject().className()
        dodatek = (
            "\n%s{border-top:1px solid %s; border-bottom:1px solid %s;"
            " border-radius:%dpx;}" % (sel, gora, dol, promien))
        if dodatek not in (w.styleSheet() or ""):
            w.setStyleSheet((w.styleSheet() or "") + dodatek)
    except Exception:
        pass


# BEZPIECZNIK WYDAJNOŚCI. Każdy QGraphicsDropShadowEffect to osobne
# renderowanie elementu do bitmapy i rozmycie przy KAŻDYM przemalowaniu.
# W 3.21.0 (PMT_NOWY) nakładało się ich 991 — także na wielkie panele
# i obszary przewijania — i na słabszych komputerach interfejs mulił,
# a przy nieszczęśliwym sterowniku zostawał ciemny. Dlatego:
#   · żadnych cieni na elementach większych niż UDZIAL_MAX okna,
#   · obszary przewijania i grupy dostają tylko wypukłą krawędź (bez cienia),
#   · łączny limit LIMIT_EFEKTOW — przyciski i karty mają pierwszeństwo.
LIMIT_EFEKTOW = 260
UDZIAL_MAX = 0.35


def zastosuj(okno, ciemny=True, sila=1.0, wlaczone=True, limit=LIMIT_EFEKTOW):
    """Nadaje głębię całemu oknu. Bezpieczne: każdy element osobno,
    a błąd na jednym nie psuje pozostałych."""
    if Qt is None or not wlaczone:
        return 0
    try:
        _pole_okna = max(1, okno.width() * okno.height())
    except Exception:
        _pole_okna = 1
    try:
        kat = os.path.dirname(os.path.abspath(getattr(okno, "__file__", ".") or "."))
    except Exception:
        kat = "."
    for stop in (os.path.join(kat, "BEZ_3D.txt"),
                 os.path.join(os.path.expanduser("~"), "BEZ_3D.txt")):
        if os.path.exists(stop):
            return 0

    zrobione = 0
    filtr_przyciskow = _Uniesienie(okno, (18 * sila, 5 * sila, 150), (32 * sila, 11 * sila, 200))
    filtr_kart = _Uniesienie(okno, (38 * sila, 12 * sila, 190), (58 * sila, 20 * sila, 225))

    # przyciski i karty najpierw — gdy zabraknie limitu, tracą tylko ramki i belki
    _dzieci = okno.findChildren(QWidget)
    _pierwsze = [w for w in _dzieci if isinstance(w, QPushButton)
                 or any(k in (w.objectName() or "") for k in KARTY)]
    _reszta = [w for w in _dzieci if w not in _pierwsze]
    for w in _pierwsze + _reszta:
        if zrobione >= limit:
            break
        try:
            nazwa = w.objectName() or ""
            klasa = w.metaObject().className()
            try:
                if w.width() * w.height() > UDZIAL_MAX * _pole_okna and w.width() > 200:
                    continue                       # wielki panel: bez cienia
            except Exception:
                pass

            if isinstance(w, QPushButton):
                # UWAGA: przyciskom NIE dotykamy tła. Wcześniej dokładałem im
                # gradient regułą dla całej klasy QPushButton — nadpisywała ona
                # kolory ustawione przez program, więc przycisk „Generuj” robił
                # się niewidoczny i wracał dopiero pod kursorem. Zostaje sam
                # cień i uniesienie: głębia bez ruszania kolorów.
                _cien(w, 18 * sila, 5 * sila, 150)
                w.installEventFilter(filtr_przyciskow)
                zrobione += 1
                continue

            if any(k in nazwa for k in KARTY) or any(k in klasa for k in KARTY):
                _gradient(w, sila)
                _cien(w, 38 * sila, 12 * sila, 190)
                _wypuklosc(w, ciemny, 16)
                w.installEventFilter(filtr_kart)
                zrobione += 1
                continue

            if any(k in nazwa for k in BELKI):
                _gradient(w, sila * 0.8)
                _cien(w, 34 * sila, 8 * sila, 180)
                zrobione += 1
                continue

            if isinstance(w, (QGroupBox, QAbstractScrollArea)):
                _wypuklosc(w, ciemny, 12)         # sama krawędź: cień na
                zrobione += 1                     # przewijanym obszarze kosztuje najwięcej
                continue

            if isinstance(w, QFrame) and w.frameShape() != QFrame.Shape.NoFrame:
                _cien(w, 18 * sila, 5 * sila, 100)
                zrobione += 1
        except Exception:
            continue
    return zrobione


def tlo_z_glebia(widget, ciemny=True):
    """Tło z głębią: rozjaśnienie u góry, wygaszenie przy krawędziach —
    dzięki temu treść wydaje się unosić nad podłożem."""
    if Qt is None:
        return
    try:
        if ciemny:
            grad = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                    "stop:0 #0f2a24, stop:0.45 #0a1f1a, stop:1 #061512)")
        else:
            grad = ("qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                    "stop:0 #ffffff, stop:0.5 #eef5f2, stop:1 #dfe9e5)")
        widget.setStyleSheet((widget.styleSheet() or "") +
                             "\nQWidget#tlo3d{background:%s;}" % grad)
        widget.setObjectName("tlo3d")
    except Exception:
        pass
