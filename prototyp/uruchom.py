# -*- coding: utf-8 -*-
"""Uruchamia prototyp nowego wyglądu PMT Planera.

Bez argumentów otwiera okno dopasowane do ekranu (F11 — pełny ekran).
Z „--zrzut” zapisuje zrzuty ekranów zamiast otwierać okno.
"""
import os
import sys

# katalog prototypu w ścieżce — plik działa też wywołany spoza swojego katalogu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proto_okno import main

if __name__ == "__main__":
    sys.exit(main())
