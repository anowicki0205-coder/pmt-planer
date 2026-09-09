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
rem Lista plikow, ktore FAKTYCZNIE skladaja sie na program.
rem Wczesniej byly tu nazwy z innej, nigdy niewydanej paczki
rem (intro_zywa_mapa.py, karta_testera.py, wyglad_3d.py) - przez to skrypt
rem zawsze konczyl sie komunikatem "brakuje plikow" i nie dalo sie go uzyc.
set "BRAK="
for %%F in (PMT_Delegacje.py intro_wideo.py zbuduj.py wersja_pomocnik.py wersja_exe.txt) do if not exist "%%F" set "BRAK=%BRAK% %%F"
if not defined BRAK goto :dodaj
echo [UWAGA] W folderze brakuje plikow:%BRAK%
echo Skopiuj je z paczki i uruchom ponownie.
goto :stop

:dodaj
rem Kontrola bezpieczenstwa: menedzer.txt to dane osobowe i NIE MOZE
rem trafic do repozytorium. Plik .gitignore tego pilnuje, ale sprawdzamy
rem jeszcze raz - blad w tym miejscu jest nie do cofniecia.
git check-ignore -q menedzer.txt
if errorlevel 1 if exist "menedzer.txt" goto :dane_osobowe

echo Dodaje pliki zrodlowe...
git add PMT_Delegacje.py intro_wideo.py zbuduj.py wersja_pomocnik.py wersja_exe.txt
git add testy_pmt.py START_TUTAJ.txt BEZ_BLOKADY_WINDOWS.txt BACKEND_APPS_SCRIPT.txt
git add INSTRUKCJA_BUDOWY.txt .gitignore
git add ZBUDUJ_EXE.bat ZBUDUJ_EXE_FOLDER.bat SPRAWDZ_WERSJE.bat URUCHOM_PROGRAM.bat
git add UTWORZ_SKROT.bat PODPISZ_EXE.bat DODAJ_WYJATEK_WINDOWS.bat URUCHOM_PMT.bat
git add updater.bat updater_folder.bat updater.sh
git add .github/workflows/build.yml .github/workflows/testy.yml
if exist "pmt_logo.png" git add pmt_logo.png
if exist "pmt_logo.ico" git add pmt_logo.ico
if exist "ciemny.png" git add ciemny.png
if exist "jasny.png" git add jasny.png
echo(
echo UWAGA: wersja.txt NIE jest wysylany - po zbudowaniu wydania GitHub podbije go SAM.
echo(
git commit -m "PMT: aktualizacja zrodel"
git push
if errorlevel 1 goto :zle
echo(
echo GOTOWE. Teraz opublikuj wydanie z tagiem vX.Y.Z (nic nie przeciagaj).
echo GitHub zbuduje paczki i po paczce Windows sam podbije wersja.txt.
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

:dane_osobowe
echo [STOP] W folderze lezy menedzer.txt, a nie jest ignorowany przez git.
echo        To dane osobowe - nie moga trafic do repozytorium.
echo        Sprawdz, czy w folderze jest plik .gitignore z wpisem menedzer.txt
echo        (jest w paczce), albo usun menedzer.txt z tego folderu.
goto :stop

:brak_plikow
echo [BLAD] Brak PMT_Delegacje.py w tym folderze.

:stop
echo(
pause
