@echo off
chcp 65001 >nul
rem PMT Planer (web) — lokalny serwer do testów na tym komputerze. Wymaga Pythona (jest już potrzebny do programu).
cd /d "%~dp0"
if not exist sekret.txt echo UWAGA: brak pliku sekret.txt obok tego pliku - logowanie zadziala, ale zapytania pojda bez podpisu.
if not exist menedzer.txt echo UWAGA: brak pliku menedzer.txt obok tego pliku - generowanie dokumentow bedzie zablokowane.
echo Uruchamiam PMT Planer na http://localhost:8080 ... (okno zostaw otwarte; Ctrl+C konczy)
start "" http://localhost:8080/index.html
where py >nul 2>nul && (py -3 serwer_lokalny.py 8080) || (python serwer_lokalny.py 8080)
pause
