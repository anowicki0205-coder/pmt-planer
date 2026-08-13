@echo off
rem ============================================================
rem  PMT Planer — pierwsze uruchomienie po pobraniu z internetu
rem
rem  DLACZEGO TEN PLIK ISTNIEJE:
rem  Windows oznacza KAZDY plik z pobranego archiwum znacznikiem
rem  "pochodzi z internetu". Przy programie zlozonym z wielu plikow
rem  konczy sie to komunikatem:
rem     "System Windows nie moze uzyskac dostepu do okreslonej
rem      sciezki lub pliku. Mozesz nie miec odpowiednich uprawnien"
rem
rem  Ten skrypt zdejmuje ten znacznik z calego folderu i uruchamia
rem  program. Wystarczy uruchomic go RAZ, po rozpakowaniu paczki.
rem ============================================================
setlocal
cd /d "%~dp0"
echo.
echo   Przygotowuje PMT Planer do pierwszego uruchomienia...
echo.

rem 1) zdejmujemy znacznik "plik z internetu" z wszystkich plikow
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-ChildItem -LiteralPath '%~dp0' -Recurse -File | Unblock-File -ErrorAction SilentlyContinue" 2>nul

rem 2) sprawdzamy, czy program jest na miejscu
if not exist "%~dp0PMT_Planer.exe" (
    echo   BLAD: nie znalazlem pliku PMT_Planer.exe w tym folderze.
    echo   Upewnij sie, ze rozpakowales CALA paczke, a nie pojedynczy plik.
    echo.
    pause
    exit /b 1
)

rem 3) ostrzezenie, gdy program zostal w folderze Pobrane
echo "%~dp0" | find /i "\Downloads\" >nul
if not errorlevel 1 (
    echo   UWAGA: program jest w folderze Pobrane.
    echo   Zalecam przeniesc caly folder np. do C:\PMT — z Pobranych
    echo   Windows i programy antywirusowe czesto blokuja uruchamianie.
    echo.
)

echo   Uruchamiam program...
start "" "%~dp0PMT_Planer.exe"
timeout /t 3 >nul
