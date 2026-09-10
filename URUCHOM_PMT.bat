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

rem 0) NAJCZESTSZY blad przy pierwszej instalacji: uruchomienie z WNETRZA
rem    archiwum ZIP otwartego w Eksploratorze. Windows wypakowuje wtedy do
rem    folderu tymczasowego TYLKO klikniety plik - bez katalogu _internal -
rem    i program konczy sie bledem "Failed to load Python DLL ... python313.dll".
rem    Rozpoznajemy to po sciezce: folder tymczasowy uzytkownika.
set "ZTEMP="
echo "%~dp0" | find /i "\AppData\Local\Temp\" >nul && set "ZTEMP=1"
if defined TEMP echo "%~dp0" | find /i "%TEMP%\" >nul && set "ZTEMP=1"
if defined ZTEMP (
    echo   STOP: ten plik zostal uruchomiony z WNETRZA archiwum ZIP
    echo   ^(albo z folderu tymczasowego^). Windows wypakowal tylko ten jeden
    echo   plik - a program potrzebuje CALEGO folderu.
    echo.
    echo   Zrob tak:
    echo     1. zamknij to okno i okno z zawartoscia archiwum,
    echo     2. kliknij PRAWYM przyciskiem pobrany plik PMT_Planer.Windows.zip
    echo        i wybierz "Wyodrebnij wszystkie...",
    echo     3. jako miejsce docelowe wpisz np. C:\PMT i kliknij "Wyodrebnij",
    echo     4. wejdz do C:\PMT\PMT_Planer i uruchom URUCHOM_PMT stamtad.
    echo.
    pause
    exit /b 1
)

rem 1) zdejmujemy znacznik "plik z internetu" z wszystkich plikow
rem    BEZ POWERSHELLA. Znacznik to zwykly dodatkowy strumien NTFS o nazwie
rem    Zone.Identifier - kasujemy go poleceniem del. Wczesniej byl tu
rem    powershell z omijaniem zasad wykonywania skryptow; to jeden ze
rem    wzorcow, po ktorych Defender i firmowy EDR podnosza alarm - a byl to
rem    PIERWSZY krok, jaki uzytkownik wykonywal po rozpakowaniu paczki.
for /r "%~dp0" %%F in (*) do del "%%~fF:Zone.Identifier" >nul 2>&1

rem    kontrola: czy znacznik faktycznie zszedl z pliku programu
if exist "%~dp0PMT_Planer.exe:Zone.Identifier" (
    echo   UWAGA: nie udalo sie zdjac znacznika "plik z internetu".
    echo   Kliknij PMT_Planer.exe prawym przyciskiem - Wlasciwosci
    echo   i zaznacz "Odblokuj" na dole okna, potem OK.
    echo.
)

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
