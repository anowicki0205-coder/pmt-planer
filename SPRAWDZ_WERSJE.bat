@echo off
setlocal EnableExtensions
title PMT - ktora wersja jest gdzie
cd /d "%~dp0"
echo ============================================================
echo  KTORA WERSJA JEST GDZIE
echo ============================================================
echo(
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto :mam
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if defined PY goto :mam
echo [BLAD] Nie znaleziono Pythona.
goto :stop

:mam
if not exist "PMT_Delegacje.py" goto :brak
set "WER="
for /f "delims=" %%V in ('%PY% wersja_pomocnik.py') do set "WER=%%V"
echo   zrodlo PMT_Delegacje.py    : %WER%
if not exist "wersja.txt" goto :po_txt
set "WTXT="
for /f "delims=" %%W in (wersja.txt) do if not defined WTXT set "WTXT=%%W"
echo   wersja.txt                 : %WTXT%

:po_txt
if not exist "dist\PMT_Planer.exe" goto :spr_folder
%PY% wersja_pomocnik.py "dist\PMT_Planer.exe"
if errorlevel 1 echo   dist\PMT_Planer.exe        : STARA kompilacja
if not errorlevel 1 echo   dist\PMT_Planer.exe        : %WER%

:spr_folder
if not exist "dist\PMT_Planer\PMT_Planer.exe" goto :koniec_spr
%PY% wersja_pomocnik.py "dist\PMT_Planer\PMT_Planer.exe"
if errorlevel 1 echo   dist\PMT_Planer\PMT_Planer.exe : STARA kompilacja
if not errorlevel 1 echo   dist\PMT_Planer\PMT_Planer.exe : %WER%

:koniec_spr
echo(
echo Jesli numery sie roznia - zbuduj ponownie w PUSTYM folderze.
goto :stop

:brak
echo [BLAD] Brak PMT_Delegacje.py w tym folderze.

:stop
echo(
pause
