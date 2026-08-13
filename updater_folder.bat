@echo off
setlocal enabledelayedexpansion
rem ============================================================
rem  PMT Planer — aktualizacja wersji FOLDEROWEJ
rem
rem  Program nie jest juz jednym plikiem .exe, tylko folderem:
rem      PMT_Planer\PMT_Planer.exe
rem      PMT_Planer\_internal\...   (biblioteki)
rem
rem  Dzieki temu nic sie nie rozpakowuje przy starcie — znika blad
rem  "Failed to load Python DLL", ktory towarzyszyl nam przy wersji
rem  jednoplikowej. Ten skrypt podmienia CALY folder.
rem
rem  Argumenty:  %1 = folder z nowa wersja (rozpakowany)
rem              %2 = plik .exe dzialajacego programu
rem              %3 = PID starego procesu
rem ============================================================
set "NOWY_FOLDER=%~1"
set "CEL_EXE=%~2"
set "PID=%~3"
set "LOG=%TEMP%\pmt_aktualizacja.log"
for %%F in ("%CEL_EXE%") do set "NAZWA_EXE=%%~nxF"
for %%F in ("%CEL_EXE%") do set "FOLDER_CEL=%%~dpF"
if "%FOLDER_CEL:~-1%"=="\" set "FOLDER_CEL=%FOLDER_CEL:~0,-1%"
set "KOPIA=%FOLDER_CEL%_poprzednia"

rem KLUCZOWE: przechodzimy do katalogu tymczasowego. Jesli skrypt "stoi"
rem w folderze programu, Windows nie pozwoli go przeniesc ani usunac
rem (komunikat "Odmowa dostepu") — i cala aktualizacja pada.
cd /d "%TEMP%"

title Aktualizacja PMT Planer
echo ============================== > "%LOG%"
echo Start: %DATE% %TIME%          >> "%LOG%"
echo Nowy folder: %NOWY_FOLDER%    >> "%LOG%"
echo Folder docelowy: %FOLDER_CEL% >> "%LOG%"
echo.
echo   Aktualizuje PMT Planer...
echo   Program uruchomi sie sam za chwile.
echo.

if not exist "%NOWY_FOLDER%\%NAZWA_EXE%" (
    echo [BLAD] W nowej wersji brak pliku %NAZWA_EXE%. >> "%LOG%"
    echo   Nie znalazlem programu w pobranej paczce.
    pause
    exit /b 1
)

rem --- 1) czekamy, az stary proces zniknie z pamieci ---
echo [1] Czekam na zamkniecie programu - PID %PID%... >> "%LOG%"
for /l %%i in (1,1,20) do (
    tasklist /fi "imagename eq %NAZWA_EXE%" 2>nul | find /i "%NAZWA_EXE%" >nul
    if errorlevel 1 goto zamkniety
    ping -n 3 127.0.0.1 >nul
)
taskkill /f /im "%NAZWA_EXE%" >nul 2>&1
ping -n 3 127.0.0.1 >nul
:zamkniety
echo [1] OK. >> "%LOG%"

rem --- 2) kopia zapasowa poprzedniej wersji ---
echo [2] Zapisuje kopie poprzedniej wersji... >> "%LOG%"
if exist "%KOPIA%" rd /s /q "%KOPIA%" >nul 2>&1
rem Kopiujemy zamiast przenosic: folder programu zostaje na miejscu, wiec
rem nie ryzykujemy "Odmowy dostepu" ani utraty programu przy bledzie.
xcopy "%FOLDER_CEL%" "%KOPIA%\" /e /i /y /q >nul 2>>"%LOG%"
if errorlevel 1 echo [2] UWAGA: kopia zapasowa niepelna. >> "%LOG%"

rem --- 3) wgrywamy nowa wersje ---
echo [3] Kopiuje nowa wersje... >> "%LOG%"
rem robocopy radzi sobie z plikami w uzyciu i dlugimi sciezkami lepiej niz xcopy;
rem kody wyjscia 0-7 oznaczaja sukces, dopiero 8+ to blad.
robocopy "%NOWY_FOLDER%" "%FOLDER_CEL%" /e /is /it /r:2 /w:2 /nfl /ndl /njh /njs >>"%LOG%" 2>&1
if errorlevel 8 (
    echo [3] robocopy zawiodl - probuje xcopy... >> "%LOG%"
    xcopy "%NOWY_FOLDER%" "%FOLDER_CEL%\" /e /i /y >nul 2>>"%LOG%"
)
if not exist "%CEL_EXE%" goto porazka
echo [3] Podmieniono pomyslnie. >> "%LOG%"

rem --- 4) zdejmujemy blokade "plik z internetu" i uruchamiamy ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath '%FOLDER_CEL%' -Recurse | Unblock-File" >nul 2>&1
set "FLAGA=%TEMP%\pmt_zyje.flag"
if exist "%FLAGA%" del /q "%FLAGA%" >nul 2>&1
echo [4] Uruchamiam nowa wersje... >> "%LOG%"
cd /d "%FOLDER_CEL%"
start "" "%CEL_EXE%"

rem --- 5) weryfikacja: czy nowa wersja zglosila gotowosc ---
set "WYSTARTOWALA=0"
for /l %%i in (1,1,15) do (
    ping -n 2 127.0.0.1 >nul
    if exist "%FLAGA%" (
        set "WYSTARTOWALA=1"
        goto po_weryfikacji
    )
)
:po_weryfikacji
if "%WYSTARTOWALA%"=="1" (
    echo [OK] Nowa wersja dziala. %DATE% %TIME% >> "%LOG%"
    if exist "%KOPIA%" rd /s /q "%KOPIA%" >nul 2>&1
    (goto) 2>nul & del "%~f0"
)

:porazka
echo [BLAD] Nowa wersja nie wystartowala - przywracam poprzednia. >> "%LOG%"
if exist "%KOPIA%" (
    xcopy "%KOPIA%" "%FOLDER_CEL%\" /e /i /y /q >nul 2>&1
    start "" "%CEL_EXE%"
    echo.
    echo   Nowa wersja nie uruchomila sie poprawnie.
    echo   Przywrocilem poprzednia - powinna sie wlasnie otworzyc.
) else (
    echo.
    echo   Aktualizacja nie powiodla sie. Pobierz program recznie ze strony wydania.
)
echo   Szczegoly: %LOG%
echo.
pause
