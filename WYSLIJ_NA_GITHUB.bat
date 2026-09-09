@echo off
setlocal EnableExtensions
title PMT - wyslij zrodla na GitHub
cd /d "%~dp0"
echo ============================================================
echo  WYSYLANIE ZRODEL NA GITHUB
echo  Uruchom TEN plik w folderze repozytorium pmt-planer,
echo  po skopiowaniu do niego plikow z paczki.
echo ============================================================
echo(
where git >nul 2>nul
if errorlevel 1 goto :brak_git
if not exist ".git" goto :nie_repo
if not exist "PMT_Delegacje.py" goto :brak_plikow

echo Pobieram zmiany z serwera...
git pull
echo(
set "BRAK="
for %%F in (intro_zywa_mapa.py karta_testera.py wyglad_3d.py wersja_pomocnik.py) do if not exist "%%F" set "BRAK=%BRAK% %%F"
if not defined BRAK goto :dodaj
echo [UWAGA] W folderze brakuje plikow:%BRAK%
echo Skopiuj je z paczki i uruchom ponownie.
goto :stop

:dodaj
echo Dodaje pliki zrodlowe...
git add PMT_Delegacje.py intro_zywa_mapa.py karta_testera.py wyglad_3d.py wersja_pomocnik.py wersja_exe.txt
if exist "pmt_logo.png" git add pmt_logo.png
if exist "pmt_logo.ico" git add pmt_logo.ico
git add logo_zabka.png logo_biedronka.png logo_groszek.png logo_stokrotka.png logo_abc.png logo_lewiatan.png 2>nul
echo(
echo UWAGA: wersja.txt NIE jest wysylany - zrobisz to po opublikowaniu wydania.
echo(
git commit -m "3.21.0: pelna kwota delegacji, mniej dokumentow, nowe intro, karta testera, wyglad 3D"
git push
if errorlevel 1 goto :zle
echo(
echo GOTOWE. Teraz opublikuj wydanie v3.21.0 z plikiem ZIP,
echo a dopiero potem wyslij wersja.txt.
goto :stop

:zle
echo [BLAD] Wysylka nie powiodla sie - sprawdz komunikat powyzej.
goto :stop

:brak_git
echo [BLAD] Nie znaleziono git. Zainstaluj z git-scm.com
goto :stop

:nie_repo
echo [BLAD] To nie jest folder repozytorium - brak katalogu .git
goto :stop

:brak_plikow
echo [BLAD] Brak PMT_Delegacje.py w tym folderze.

:stop
echo(
pause
