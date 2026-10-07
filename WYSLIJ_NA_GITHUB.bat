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
rem Tylko JEDEN plik musi tu byc - bez niego nie ma czego wysylac.
rem Wyliczanej listy nazw tu JUZ NIE MA. Skrypt wymienial pliki po jednym
rem i przy kazdym porzadku w repozytorium stawal na nazwie, ktorej juz nie
rem ma (ostatnio intro_zywa_mapa.py, usuniety w 3.23.0), a nowych modulow
rem - prototyp\proto_*.py, nowy_wyglad.py, okno_logowania.py - nie wysylal
rem wcale, bo nikt ich do listy nie dopisal.
if exist "PMT_Delegacje.py" goto :dodaj
echo [UWAGA] W tym folderze nie ma PMT_Delegacje.py.
echo Uruchom skrypt w folderze ze zrodlami programu.
goto :stop

:dodaj
rem Kontrola bezpieczenstwa: te trzy pliki to dane osobowe albo sekrety
rem i NIE MOGA trafic do repozytorium. Plik .gitignore tego pilnuje, ale
rem sprawdzamy jeszcze raz - blad w tym miejscu jest nie do cofniecia,
rem bo repozytorium pamieta kazda swoja wersje.
for %%S in (menedzer.txt sekret.txt pmt_kod.txt) do if exist "%%S" (
  git check-ignore -q "%%S"
  if errorlevel 1 set "JAWNY=%%S"
)
if defined JAWNY goto :dane_osobowe

echo Dodaje pliki zrodlowe...
rem Wszystko, co nie jest pominiete przez .gitignore. Jedna komenda zamiast
rem listy nazw - dzieki temu nowy modul jedzie na GitHub sam, a usuniety
rem przestaje blokowac skrypt.
git add -A
rem wersja.txt podbija CI po zbudowaniu paczki - nasza kopia nie ma go nadpisac.
git reset -q wersja.txt
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
echo [STOP] W folderze lezy %JAWNY%, a nie jest ignorowany przez git.
echo        To dane osobowe albo sekret - nie moga trafic do repozytorium.
echo        Sprawdz, czy w folderze jest plik .gitignore z wpisami
echo        menedzer.txt, sekret.txt i pmt_kod.txt (jest w paczce),
echo        albo usun ten plik z tego folderu.
goto :stop

:brak_plikow
echo [BLAD] Brak PMT_Delegacje.py w tym folderze.

:stop
echo(
pause
