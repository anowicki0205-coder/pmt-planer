@echo off
setlocal EnableExtensions
title PMT - wyjatek w zabezpieczeniach Windows
cd /d "%~dp0"
net session >nul 2>nul
if not errorlevel 1 goto :admin
echo Ten plik musi byc uruchomiony jako administrator.
echo Kliknij go prawym przyciskiem i wybierz "Uruchom jako administrator".
pause
exit /b 1

:admin
echo Dodaje wyjatek dla folderu: %~dp0
powershell -NoProfile -Command "Add-MpPreference -ExclusionPath '%~dp0'"
if errorlevel 1 goto :zle
echo(
echo GOTOWE. Folder jest teraz pomijany przez skaner Windows.
echo Zbuduj EXE ponownie i sprobuj uruchomic.
goto :stop

:zle
echo [BLAD] Nie udalo sie dodac wyjatku. Zrob to recznie:
echo Zabezpieczenia Windows - Ochrona przed wirusami - Zarzadzaj
echo ustawieniami - Wykluczenia - Dodaj folder.

:stop
echo(
pause
