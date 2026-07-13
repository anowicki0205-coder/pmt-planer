@echo off
setlocal enabledelayedexpansion
rem ============================================================
rem  PMT Planer - skrypt aktualizacji
rem
rem  WAZNE: ten plik jest pobierany SWIEZO z GitHuba przy kazdej
rem  aktualizacji, NIE jest zaszyty w .exe programu. Jesli kiedys
rem  znajdzie sie tu blad, wystarczy poprawic TEN plik w repo -
rem  dziala to natychmiast u WSZYSTKICH uzytkownikow, bez wzgledu
rem  na to, jaka wersje .exe maja aktualnie zainstalowana.
rem
rem  Argumenty: %1=nowy plik  %2=plik docelowy  %3=PID starego programu
rem ============================================================
set "NOWY=%~1"
set "CEL=%~2"
set "PID=%~3"
set "LOG=%TEMP%\pmt_aktualizacja.log"
set "PS1=%TEMP%\pmt_copy_elevated.ps1"

title Aktualizacja PMT Planer
echo ============================== > "%LOG%"
echo Start: %DATE% %TIME%          >> "%LOG%"
echo Nowy plik: %NOWY%             >> "%LOG%"
echo Plik docelowy: %CEL%          >> "%LOG%"
echo PID starego programu: %PID%   >> "%LOG%"

echo.
echo   Aktualizuje PMT Planer...
echo   Program uruchomi sie sam za chwile.
echo.

if not exist "%NOWY%" (
    echo [BLAD] Brak pobranego pliku: %NOWY% >> "%LOG%"
    echo   Nie znaleziono pobranego pliku aktualizacji.
    pause
    exit /b 1
)

rem === 1) Czekaj, az stary program naprawde sie zamknie (do ~2 min) ===
echo [1] Czekam na zamkniecie programu (PID %PID%)... >> "%LOG%"
for /l %%i in (1,1,60) do (
    tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
    if errorlevel 1 goto zamkniety
    ping -n 3 127.0.0.1 >nul
)
echo [1] UWAGA: program nadal widoczny po 2 minutach - probuje mimo to. >> "%LOG%"
:zamkniety
echo [1] OK. >> "%LOG%"

rem === 2) Zwykla kopia, z ponawianiem (plik bywa jeszcze chwile zablokowany) ===
echo [2] Kopiuje plik (zwykle uprawnienia)... >> "%LOG%"
for /l %%i in (1,1,15) do (
    copy /y "%NOWY%" "%CEL%" >nul 2>>"%LOG%"
    if not errorlevel 1 goto podmieniono
    ping -n 2 127.0.0.1 >nul
)
echo [2] Zwykla kopia nie powiodla sie. >> "%LOG%"

rem === 2b) Proba z podniesionymi uprawnieniami - rozwiazuje przypadek        ===
rem === instalacji w C:\Program Files, gdzie zwykly zapis jest zablokowany.   ===
rem === Sciezki wstawiamy do OSOBNEGO pliku .ps1 (juz podstawione, jako      ===
rem === zwykly tekst) - bez tego trzeba by przenosic cudzyslowy przez trzy   ===
rem === warstwy (cmd -> powershell -> cmd), co jest bardzo podatne na blad.  ===
echo [2b] Probuje z uprawnieniami administratora (moze pojawic sie okno UAC)... >> "%LOG%"
> "%PS1%" echo Copy-Item -LiteralPath '%NOWY%' -Destination '%CEL%' -Force
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Process -FilePath 'powershell' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','%PS1%') -Verb RunAs -Wait -PassThru | ForEach-Object { exit $_.ExitCode }" >> "%LOG%" 2>&1
del /q "%PS1%" >nul 2>&1
if not errorlevel 1 goto podmieniono
echo [2b] Podniesione uprawnienia rowniez nie pomogly (albo uzytkownik odmowil UAC). >> "%LOG%"

echo.
echo   ================================================================
echo    Nie udalo sie automatycznie podmienic pliku programu.
echo    Stara wersja pozostala nienaruszona - nic nie zostalo uszkodzone.
echo.
echo    Najczestsza przyczyna: program lezy w folderze wymagajacym
echo    uprawnien administratora (np. C:\Program Files). Warto trzymac
echo    PMT Planer w folderze uzytkownika (Pulpit, Dokumenty) - wtedy
echo    kolejne aktualizacje beda przebiegac bez pytania o uprawnienia.
echo.
echo    Nowa wersja czeka gotowa tutaj:
echo    %NOWY%
echo    Mozesz ja recznie skopiowac w miejsce starego pliku.
echo.
echo    Pelny przebieg aktualizacji zapisany w:
echo    %LOG%
echo   ================================================================
echo.
pause
exit /b 1

:podmieniono
echo [2/2b] Plik podmieniony pomyslnie. >> "%LOG%"
del /q "%NOWY%" >nul 2>&1

echo [3] Uruchamiam nowa wersje... >> "%LOG%"
start "" "%CEL%"
echo [3] Gotowe: %DATE% %TIME% >> "%LOG%"

rem === Skrypt kasuje sam siebie ===
(goto) 2>nul & del "%~f0"
