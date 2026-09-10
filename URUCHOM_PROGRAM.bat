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
echo [BLAD] Nie udalo sie doinstalowac bibliotek. Wyslij PMT_log.txt
goto :stop

:blad_startu
echo [BLAD] Program zakonczyl sie bledem. Koncowka raportu:
echo ------------------------------------------------------------
powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 18"
echo ------------------------------------------------------------
echo Wyslij na czacie plik PMT_log.txt
goto :stop

:brak
echo [BLAD] Brak PMT_Delegacje.py - rozpakuj CALE archiwum do jednego folderu.

:stop
echo(
pause
