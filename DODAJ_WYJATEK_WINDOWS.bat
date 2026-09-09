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
rem Wykluczamy KATALOG PROGRAMU, nigdy katalogu, w ktorym akurat lezy ten
rem plik. Wczesniej wystarczylo uruchomic go z Pobranych albo z Pulpitu,
rem zeby TRWALE wylaczyc skanowanie calego tego folderu - to powazna dziura,
rem a komunikat i tak melodowal sukces.
set "CEL=%~dp0dist\PMT_Planer"
if exist "%CEL%\PMT_Planer.exe" goto :mam_cel
set "CEL=%~dp0dist"
if exist "%CEL%\PMT_Planer.exe" goto :mam_cel
echo [BLAD] Nie znalazlem zbudowanego programu w podfolderze dist.
echo        Najpierw zbuduj program (ZBUDUJ_EXE_FOLDER.bat), potem
echo        uruchom ten plik ponownie.
goto :stop

:mam_cel
echo "%CEL%" | find /i "\Downloads\" >nul && goto :niebezpieczne
echo "%CEL%" | find /i "\Pobrane\"  >nul && goto :niebezpieczne
echo "%CEL%" | find /i "\Desktop\"  >nul && goto :niebezpieczne
echo "%CEL%" | find /i "\Pulpit\"   >nul && goto :niebezpieczne
echo Dodaje wyjatek dla folderu programu: %CEL%
powershell -NoProfile -Command "Add-MpPreference -ExclusionPath '%CEL%'"
if errorlevel 1 goto :zle
echo(
echo GOTOWE. Folder programu jest teraz pomijany przez skaner Windows.
echo Sprawdzenie: Zabezpieczenia Windows - Ochrona przed wirusami -
echo Zarzadzaj ustawieniami - Wykluczenia. Na liscie ma byc powyzsza sciezka.
goto :stop

:niebezpieczne
echo [ODMOWA] Program lezy w Pobranych, na Pulpicie albo w Dokumentach.
echo          Wykluczenie objeloby CALY ten folder - to za duzo.
echo          Przenies folder programu np. do C:\PMT i uruchom ponownie.
goto :stop

:zle
echo [BLAD] Nie udalo sie dodac wyjatku. Zrob to recznie:
echo Zabezpieczenia Windows - Ochrona przed wirusami - Zarzadzaj
echo ustawieniami - Wykluczenia - Dodaj folder.

:stop
echo(
pause
