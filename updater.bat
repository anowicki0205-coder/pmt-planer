@echo off
setlocal enabledelayedexpansion
rem ============================================================
rem  PMT Planer - skrypt aktualizacji
rem
rem  WAZNE: ten plik jest pobierany SWIEZO z GitHuba przy kazdej
rem  aktualizacji, NIE jest zaszyty w .exe programu. Jesli kiedys
rem  znajdzie sie tu blad, wystarczy poprawic TEN plik w repo -
rem  dziala to natychmiast u WSZYSTKICH uzytkownikow, bez wzgledu
rem  na to, jaka wersje .exe maja aktualnie zainstalowana.
rem
rem  ZABEZPIECZENIE: przed podmiana robimy kopie STAREJ wersji.
rem  Po uruchomieniu nowej wersji SPRAWDZAMY, czy proces naprawde
rem  wystartowal - jesli nie (np. brakuje biblioteki systemowej),
rem  automatycznie przywracamy poprzednia, dzialajaca wersje.
rem  Uzytkownik nigdy nie zostaje bez dzialajacego programu.
rem
rem  Argumenty: %1=nowy plik  %2=plik docelowy  %3=PID starego programu
rem ============================================================
set "NOWY=%~1"
set "CEL=%~2"
set "PID=%~3"
set "LOG=%TEMP%\pmt_aktualizacja.log"
set "PS1=%TEMP%\pmt_copy_elevated.ps1"
set "KOPIA=%CEL%.poprzednia"
for %%F in ("%CEL%") do set "NAZWA_EXE=%%~nxF"

title Aktualizacja PMT Planer
echo ============================== > "%LOG%"
echo Start: %DATE% %TIME%          >> "%LOG%"
echo Nowy plik: %NOWY%             >> "%LOG%"
echo Plik docelowy: %CEL%          >> "%LOG%"
echo PID starego programu: %PID%   >> "%LOG%"

echo.
echo   Aktualizuje PMT Planer...
echo   Program uruchomi sie sam za chwile.
echo.

if not exist "%NOWY%" (
    echo [BLAD] Brak pobranego pliku: %NOWY% >> "%LOG%"
    echo   Nie znaleziono pobranego pliku aktualizacji.
    pause
    exit /b 1
)

rem === 1) Czekaj, az stary program naprawde sie zamknie (do ~2 min) ===
echo [1] Czekam na zamkniecie programu (PID %PID%)... >> "%LOG%"
for /l %%i in (1,1,60) do (
    tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
    if errorlevel 1 goto zamkniety
    ping -n 3 127.0.0.1 >nul
)
echo [1] UWAGA: program nadal widoczny po 2 minutach - probuje mimo to. >> "%LOG%"
:zamkniety
echo [1] OK. >> "%LOG%"

rem === 2) Kopia zapasowa STAREJ, dzialajacej wersji - na wypadek gdyby ===
rem === nowa sie nie uruchomila. Bez tego nie byloby do czego wracac.  ===
echo [2] Zapisuje kopie poprzedniej wersji... >> "%LOG%"
if exist "%CEL%" (
    copy /y "%CEL%" "%KOPIA%" >nul 2>>"%LOG%"
)

rem === 3) Zwykla kopia, z ponawianiem (plik bywa jeszcze chwile zablokowany) ===
echo [3] Kopiuje plik (zwykle uprawnienia)... >> "%LOG%"
for /l %%i in (1,1,15) do (
    copy /y "%NOWY%" "%CEL%" >nul 2>>"%LOG%"
    if not errorlevel 1 goto podmieniono
    ping -n 2 127.0.0.1 >nul
)
echo [3] Zwykla kopia nie powiodla sie. >> "%LOG%"

rem === 3b) Proba z podniesionymi uprawnieniami - rozwiazuje przypadek        ===
rem === instalacji w C:\Program Files, gdzie zwykly zapis jest zablokowany.   ===
rem === Sciezki wstawiamy do OSOBNEGO pliku .ps1 (juz podstawione, jako      ===
rem === zwykly tekst) - bez tego trzeba by przenosic cudzyslowy przez trzy   ===
rem === warstwy (cmd -> powershell -> cmd), co jest bardzo podatne na blad.  ===
echo [3b] Probuje z uprawnieniami administratora (moze pojawic sie okno UAC)... >> "%LOG%"
> "%PS1%" echo Copy-Item -LiteralPath '%NOWY%' -Destination '%CEL%' -Force
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Process -FilePath 'powershell' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','%PS1%') -Verb RunAs -Wait -PassThru | ForEach-Object { exit $_.ExitCode }" >> "%LOG%" 2>&1
del /q "%PS1%" >nul 2>&1
if not errorlevel 1 goto podmieniono
echo [3b] Podniesione uprawnienia rowniez nie pomogly (albo uzytkownik odmowil UAC). >> "%LOG%"

echo.
echo   ================================================================
echo    Nie udalo sie automatycznie podmienic pliku programu.
echo    Stara wersja pozostala nienaruszona - nic nie zostalo uszkodzone.
echo.
echo    Najczestsza przyczyna: program lezy w folderze wymagajacym
echo    uprawnien administratora (np. C:\Program Files). Warto trzymac
echo    PMT Planer w folderze uzytkownika (Pulpit, Dokumenty) - wtedy
echo    kolejne aktualizacje beda przebiegac bez pytania o uprawnienia.
echo.
echo    Nowa wersja czeka gotowa tutaj:
echo    %NOWY%
echo    Mozesz ja recznie skopiowac w miejsce starego pliku.
echo.
echo    Pelny przebieg aktualizacji zapisany w:
echo    %LOG%
echo   ================================================================
echo.
pause
exit /b 1

:podmieniono
echo [3/3b] Plik podmieniony pomyslnie. >> "%LOG%"
del /q "%NOWY%" >nul 2>&1

rem === 4) Usun stary znacznik "program zyje" (z ewentualnego poprzedniego ===
rem === uruchomienia) - zeby nie dac falszywego pozytywnego wyniku nizej.  ===
set "FLAGA=%TEMP%\pmt_zyje.flag"
if exist "%FLAGA%" del /q "%FLAGA%" >nul 2>&1

rem === 5) Krotka przerwa PRZED pierwszym uruchomieniem - realny przypadek ===
rem === pokazal, ze odpalenie NATYCHMIAST po kopiowaniu czasem konczylo    ===
rem === sie bledem brakujacej biblioteki (antywirus/system jeszcze         ===
rem === "trzymal" swiezo skopiowany plik) - mimo ze plik byl w 100% OK:    ===
rem === reczne uruchomienie chwile pozniej dzialalo bez zarzutu.           ===
echo [4] Czekam przed uruchomieniem (antywirus bywa jeszcze zajety plikiem)... >> "%LOG%"
ping -n 4 127.0.0.1 >nul

rem === 4a) CZEKAMY, AZ STARY PROCES NAPRAWDE ZNIKNIE ===================
rem === Dopoki poprzednia wersja siedzi w pamieci, nowa potrafi wystartowac ===
rem === i natychmiast zgasnac (wspolny katalog tymczasowy _MEI).            ===
rem NAZWA_EXE jest ustawiona na gorze skryptu z %CEL% (plik docelowy).
rem Wczesniej brana byla z %1 — a to plik TYMCZASOWY, ktorego w pamieci
rem nigdy nie ma. Efekt: skrypt "widzial" zamkniety program natychmiast
rem i startowal nowa wersje, gdy stara wciaz zylа. Stad brak restartu.
if "%NAZWA_EXE%"=="" set "NAZWA_EXE=PMT_Planer.exe"
for /l %%p in (1,1,15) do (
    tasklist /fi "imagename eq %NAZWA_EXE%" 2>nul | find /i "%NAZWA_EXE%" >nul
    if errorlevel 1 (
        echo [4] Stary proces zamkniety (proba %%p). >> "%LOG%"
        goto proces_zamkniety
    )
    echo [4] Stary proces jeszcze dziala - czekam (proba %%p)... >> "%LOG%"
    ping -n 3 127.0.0.1 >nul
)
echo [4] UWAGA: stary proces nadal widoczny - probuje mimo to. >> "%LOG%"
:proces_zamkniety

rem === 5a) TEST DOSTEPNOSCI PLIKU - probujemy go skopiowac do %TEMP%.      ===
rem === Jesli antywirus lub system wciaz trzymaja plik na wylacznosc, kopia ===
rem === sie nie uda. Czekamy do 30 s, zamiast strzelac na oslep - to wlasnie ===
rem === powodowalo blad "Failed to load Python DLL ... python313.dll".      ===
set "PROBNY=%TEMP%\pmt_test_dostepu.tmp"
for /l %%t in (1,1,10) do (
    copy /y "%CEL%" "%PROBNY%" >nul 2>&1
    if not errorlevel 1 (
        del /q "%PROBNY%" >nul 2>&1
        echo [4] Plik gotowy do uruchomienia (proba %%t). >> "%LOG%"
        goto plik_gotowy
    )
    echo [4] Plik jeszcze zajety - czekam (proba %%t)... >> "%LOG%"
    ping -n 4 127.0.0.1 >nul
)
:plik_gotowy

rem === 5b) Sprzatanie porzuconych katalogow _MEI (tylko gdy nikt ich nie uzywa). ===
for /d %%d in ("%TEMP%\_MEI*") do rd /s /q "%%d" >nul 2>&1

rem === 5c) ZDEJMUJEMY BLOKADE "PLIK Z INTERNETU" ======================
rem === Plik pobrany z sieci dostaje ukryty znacznik strefy. Windows     ===
rem === potrafi wtedy CICHO zablokowac uruchomienie z poziomu skryptu -  ===
rem === bez zadnego komunikatu. To najczestsza przyczyna "nie wystartowal". ===
del "%CEL%:Zone.Identifier" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%CEL%'" >nul 2>&1
echo [4] Zdjeto blokade pliku z internetu (jesli byla). >> "%LOG%"

echo [4] Uruchamiam nowa wersje: "%CEL%" >> "%LOG%"
for %%f in ("%CEL%") do set "KATALOG=%%~dpf"
if "%KATALOG:~-1%"=="\" set "KATALOG=%KATALOG:~0,-1%"
cd /d "%KATALOG%" 2>nul
echo [4] Katalog roboczy: %KATALOG% >> "%LOG%"
start "" "%CEL%"
if errorlevel 1 echo [4] BLAD startu (sposob 1), kod %errorlevel% >> "%LOG%"

rem === 6) WERYFIKACJA PRZEZ ZNACZNIK - nie samo istnienie procesu!        ===
rem === Bootloader PyInstallera, ktoremu nie udalo sie wczytac biblioteki  ===
rem === Pythona, pokazuje natywne okno bledu Windows i CZEKA na klikniecie ===
rem === OK - proces w tym czasie WCIAZ ISTNIEJE (tasklist by go znalazl!). ===
rem === Prawdziwy dowod, ze program dziala: sam program zapisal znacznik  ===
rem === zaraz po starcie. Brak znacznika = program sie nie uruchomil,     ===
rem === niezaleznie od tego, co widac w tasklist.                        ===
set "WYSTARTOWALA=0"
set "PROBA_2=0"
set "PROBA_3=0"
rem UWAGA: rozpakowanie ~48 MB przy aktywnym antywirusie potrafi trwac
rem kilkanascie sekund - dlatego czekamy do ~45 s, a druga probe podejmujemy
rem dopiero po ~12 s (wczesniej bylo 6 s, co bywalo przedwczesne).
for /l %%i in (1,1,20) do (
    ping -n 3 127.0.0.1 >nul
    if exist "%FLAGA%" (
        set "WYSTARTOWALA=1"
        goto po_weryfikacji
    )
    if "!PROBA_2!"=="1" if %%i GEQ 12 if "!PROBA_3!"=="0" (
        echo [4] Sposob 3: uruchomienie przez powloke systemu... >> "%LOG%"
        explorer.exe "%CEL%"
        set "PROBA_3=1"
    )
    if "!PROBA_2!"=="0" if %%i GEQ 6 (
        echo [4] Znacznik sie nie pojawil - probuje uruchomic ponownie (drugie podejscie)... >> "%LOG%"
        start "" "%CEL%"
        set "PROBA_2=1"
    )
)
:po_weryfikacji

if "%WYSTARTOWALA%"=="1" goto sukces

rem === 6b) OSTATNIA PROBA: pelne odczekanie i jeszcze jeden start ========
echo [4] Sposob 4: dluga przerwa i ponowny start... >> "%LOG%"
ping -n 8 127.0.0.1 >nul
start "" "%CEL%"
for /l %%z in (1,1,8) do (
    ping -n 3 127.0.0.1 >nul
    if exist "%FLAGA%" (
        echo [OK] Wystartowala za czwartym podejsciem. >> "%LOG%"
        goto sukces
    )
)
goto porazka

:sukces
echo [4] Nowa wersja dziala poprawnie. >> "%LOG%"
if exist "%KOPIA%" del /q "%KOPIA%" >nul 2>&1
echo [OK] Gotowe: %DATE% %TIME% >> "%LOG%"
(goto) 2>nul & del "%~f0"

:porazka
rem === 5) Nowa wersja NIE wystartowala - automatyczny odwrot ===
echo [4] BLAD: nowa wersja sie nie uruchomila. Przywracam poprzednia... >> "%LOG%"
if not exist "%KOPIA%" goto brak_kopii

copy /y "%KOPIA%" "%CEL%" >nul 2>>"%LOG%"
del /q "%KOPIA%" >nul 2>&1
start "" "%CEL%"
echo.
echo   ================================================================
echo    Nowa wersja programu nie uruchomila sie poprawnie.
echo    Automatycznie przywrocono poprzednia, dzialajaca wersje -
echo    powinna wlasnie sie otworzyc.
echo.
echo    Sprobuj zaktualizowac ponownie pozniej. Jesli problem
echo    sie powtorzy, skontaktuj sie z autorem programu.
echo    Szczegoly: %LOG%
echo   ================================================================
echo.
pause
exit /b 1

:brak_kopii
echo.
echo   ================================================================
echo    Nowa wersja programu nie uruchomila sie, a nie znalazlem
echo    kopii poprzedniej wersji do przywrocenia.
echo    Szczegoly: %LOG%
echo   ================================================================
echo.
pause
exit /b 1
