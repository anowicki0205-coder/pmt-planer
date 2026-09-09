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
%PY% zbuduj.py --jeden
goto :stop

:brak
echo [BLAD] Brak pliku zbuduj.py - rozpakuj CALA paczke do jednego folderu.

:stop
echo(
pause
