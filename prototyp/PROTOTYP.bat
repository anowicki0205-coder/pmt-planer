@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3.13 uruchom.py
if errorlevel 1 (
  echo.
  echo Nie udalo sie uruchomic. Sprawdz, czy masz Pythona 3.13 i PyQt6:
  echo     py -3.13 -m pip install PyQt6
  pause
)
