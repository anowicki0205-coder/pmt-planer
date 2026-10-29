"""Odczytuje kod QR z obrazu (do testów: sprawdza, że kod NAPRAWDĘ zawiera oczekiwany adres). Użycie: python dekoduj_qr.py obraz.png  (wymaga: pip install opencv-python-headless)."""
import sys, cv2
obraz = cv2.imread(sys.argv[1])
if obraz is None: sys.exit(2)
obraz = cv2.copyMakeBorder(obraz, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=(255, 255, 255))      # cicha strefa wokół kodu
tekst, _, _ = cv2.QRCodeDetector().detectAndDecode(obraz)
print(tekst); sys.exit(0 if tekst else 1)
