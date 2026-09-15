@echo off
setlocal EnableExtensions
title PMT PLANER - uruchomienie ze zrodel
cd /d "%~dp0"
set "LOG=%~dp0PMT_log.txt"
echo ===== START %date% %time% =====>"%LOG%"

echo ============================================================
echo  PMT PLANER - uruchomienie programu ze zrodel
echo  Pierwsze uruchomienie doinstaluje potrzebne biblioteki.
echo ============================================================
echo(

if not exist "PMT_Delegacje.py" goto :brak
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto :mam
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto :mam
echo [BLAD] Brak Pythona. Zainstaluj z python.org
echo i zaznacz "Add python.exe to PATH".
goto :stop

:mam
echo Python: %PY%
%PY% -c "import PyQt6, openpyxl, fpdf" >>"%LOG%" 2>&1
if not errorlevel 1 goto :start
rem Brak bibliotek albo Windows nie wpuscil ich plikow - to drugie
rem rozpoznajemy po tresci bledu, zanim cokolwiek doinstalujemy.
call :blokada_windows && goto :stop
echo Doinstalowuje biblioteki - jednorazowo, chwile potrwa...
%PY% -m pip install --upgrade pip >>"%LOG%" 2>&1
rem --no-binary fonttools: bez skompilowanych .pyd, ktore Windows potrafi zablokowac
%PY% -m pip install --no-binary fonttools PyQt6 openpyxl fpdf2 >>"%LOG%" 2>&1
%PY% -c "import PyQt6, openpyxl, fpdf" >>"%LOG%" 2>&1
if errorlevel 1 goto :blad_bibliotek

:start
echo Uruchamiam program...
%PY% PMT_Delegacje.py >>"%LOG%" 2>&1
if errorlevel 1 goto :blad_startu
echo Program zamkniety.
goto :stop

:blad_bibliotek
call :blokada_windows && goto :stop
echo [BLAD] Nie udalo sie doinstalowac bibliotek. Wyslij PMT_log.txt
goto :stop

:blad_startu
call :blokada_windows && goto :stop
echo [BLAD] Program zakonczyl sie bledem. Koncowka raportu:
echo ------------------------------------------------------------
call :koncowka
echo ------------------------------------------------------------
echo Wyslij na czacie plik PMT_log.txt
goto :stop

:blokada_windows
rem Konczy sie powodzeniem (errorlevel 0), gdy w raporcie jest slad blokady
rem zasad kontroli aplikacji Windows: Inteligentnej kontroli aplikacji
rem (Smart App Control) albo firmowej polityki WDAC / Device Guard.
rem W polskim Windows: "Zasady kontroli aplikacji zablokowaly ten plik",
rem kod bledu 4551 (WinError 4551). Blokada obejmuje takze biblioteki DLL i .pyd, nie
rem tylko pliki EXE - dlatego moze trafic program uruchamiany Pythonem.
findstr /i /c:"kontroli aplikacji" /c:"Application Control policy" /c:"Device Guard" /c:"WinError 4551" /c:"error 4551" "%LOG%" >nul 2>nul
if errorlevel 1 exit /b 1
echo ============================================================
echo  WINDOWS ZABLOKOWAL WCZYTANIE PLIKU PROGRAMU
echo ============================================================
echo  To nie jest blad programu. Zasady kontroli aplikacji Windows
echo  (Inteligentna kontrola aplikacji albo polityka firmowa) nie
echo  wpuscily jednego z plikow bibliotek. Slad z raportu:
findstr /i /c:"DLL load failed" /c:"kontroli aplikacji" /c:"Application Control policy" /c:"Device Guard" "%LOG%"
echo(
echo  Co dalej - szczegoly w BEZ_BLOKADY_WINDOWS.txt:
echo   1. Zabezpieczenia Windows - Kontrola aplikacji i przegladarki -
echo      Inteligentna kontrola aplikacji: sprawdz stan (Ocena / Wlaczona /
echo      Wylaczona). Zmiana wymaga uprawnien administratora.
echo   2. Na komputerze firmowym: przekaz do IT plik WNIOSEK_DO_IT.txt.
echo   3. Wyslij na czacie plik PMT_log.txt - nazwa zablokowanego pliku
echo      mowi, ktora biblioteka nie przeszla.
exit /b 0

:koncowka
rem Ostatnie linie raportu wypisuje Python, bo juz tu jest; PowerShell
rem to zapalnik dla zabezpieczen firmowych, wiec go nie wolamy.
%PY% -c "import io;print(''.join(io.open(r'%LOG%',encoding='utf-8',errors='replace').readlines()[-18:]))" 2>nul
exit /b 0

:brak
echo [BLAD] Brak PMT_Delegacje.py - rozpakuj CALE archiwum do jednego folderu.

:stop
echo(
pause
