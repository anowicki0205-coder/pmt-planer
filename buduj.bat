@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo ============================================
echo  PMT Planer - budowa exe od zera (3.20.2)
echo ============================================
echo.

rem --- 1) kontrola zrodla ---
if not exist "PMT_Delegacje.py" (
  echo [BLAD] Brak pliku PMT_Delegacje.py w tym folderze.
  pause & exit /b 1
)
findstr /C:"WERSJA_PROGRAMU = \"3.20.2\"" PMT_Delegacje.py >nul
if errorlevel 1 (
  echo [BLAD] PMT_Delegacje.py w tym folderze to NIE wersja 3.20.2.
  echo        Podmien plik na ten z paczki i uruchom ponownie.
  pause & exit /b 1
)
echo [OK] Zrodlo: PMT_Delegacje.py w wersji 3.20.2
if not exist "ciemny.png" ( echo [BLAD] Brak ciemny.png obok skryptu. & pause & exit /b 1 )
if not exist "jasny.png"  ( echo [BLAD] Brak jasny.png obok skryptu.  & pause & exit /b 1 )
echo [OK] Tla: ciemny.png, jasny.png

rem --- 2) narzedzia i biblioteki ---
python --version >nul 2>&1
if errorlevel 1 (
  echo [BLAD] Nie znaleziono Pythona w PATH.
  echo        Uruchom ten skrypt w konsoli, w ktorej dziala polecenie "python".
  pause & exit /b 1
)
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 ( echo [BLAD] Brak biblioteki PyQt6. Zainstaluj: python -m pip install PyQt6 & pause & exit /b 1 )
python -c "import fpdf" >nul 2>&1
if errorlevel 1 ( echo [BLAD] Brak biblioteki fpdf2. Zainstaluj: python -m pip install fpdf2 & pause & exit /b 1 )
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo [INFO] Brak PyInstallera - instaluje...
  python -m pip install pyinstaller
  if errorlevel 1 ( echo [BLAD] Instalacja PyInstallera nie powiodla sie. & pause & exit /b 1 )
)
echo [OK] Python, PyQt6, fpdf2, PyInstaller - gotowe

rem --- 3) czyszczenie starych buildow ---
echo [INFO] Czyszcze stare artefakty: build, dist, PMT_Planer.spec ...
rmdir /s /q build 2>nul
rmdir /s /q dist  2>nul
del /q PMT_Planer.spec 2>nul

rem --- 4) opcjonalne zasoby (logo / ikona, jesli lezy obok) ---
set "DODATKI="
set "IKONA="
if exist "pmt_logo.ico" set "IKONA=--icon pmt_logo.ico"
if not defined IKONA if exist "pmt.ico" set "IKONA=--icon pmt.ico"
for %%F in (pmt_logo.ico pmt_logo.png pmt_logo.jpg pmt.ico pmt.png pmt.jpg) do (
  if exist "%%F" set DODATKI=!DODATKI! --add-data "%%F;."
)

rem --- 5) budowa od zera ---
echo [INFO] Buduje swiezy program (PyInstaller --onedir --windowed)...
python -m PyInstaller --noconfirm --clean --onedir --windowed --name PMT_Planer !IKONA! --add-data "ciemny.png;." --add-data "jasny.png;." !DODATKI! PMT_Delegacje.py
if errorlevel 1 ( echo [BLAD] Budowa nie powiodla sie - szczegoly powyzej. & pause & exit /b 1 )

echo.
echo [OK] Gotowe. Swiezy program:
echo      %cd%\dist\PMT_Planer\PMT_Planer.exe
echo      Na GitHub wrzucasz spakowany folder dist\PMT_Planer - jak dotychczas.
echo.
set /p ODP=Uruchomic teraz swiezy build? [T/N]: 
if /I "!ODP!"=="T" start "" "dist\PMT_Planer\PMT_Planer.exe"
pause
