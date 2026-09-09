@echo off
setlocal EnableExtensions
title PMT PLANER - budowanie - jeden plik
cd /d "%~dp0"
if not exist "zbuduj.py" goto :brak
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto :mam
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto :mam
echo [BLAD] Nie znaleziono Pythona. Zainstaluj z python.org
echo i zaznacz opcje "Add python.exe to PATH".
goto :stop

:mam
echo(
echo   ============================================================
echo    UWAGA - wariant JEDNOPLIKOWY (--onefile)
echo   ============================================================
echo    Ten wariant przy KAZDYM uruchomieniu rozpakowuje ok. 48 MB
echo    bibliotek do folderu tymczasowego i stamtad je uruchamia.
echo    To wlasnie taki sposob dzialania najczesciej zatrzymuje
echo    Windows ("Inteligentna kontrola aplikacji", reguly ASR)
echo    i stoi za bledem "Failed to load Python DLL".
echo(
echo    DO ROZSYLANIA ZESPOLOWI uzywaj ZBUDUJ_EXE_FOLDER.bat.
echo    Wariant jednoplikowy ma sens tylko na wlasne testy.
echo   ============================================================
echo(
choice /c TN /n /m "  Budowac mimo to? [T/N] "
if errorlevel 2 goto :stop
%PY% zbuduj.py --jeden
goto :stop

:brak
echo [BLAD] Brak pliku zbuduj.py - rozpakuj CALA paczke do jednego folderu.

:stop
echo(
pause
