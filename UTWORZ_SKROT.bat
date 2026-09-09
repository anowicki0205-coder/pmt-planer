@echo off
setlocal EnableExtensions
title PMT - skrot na pulpicie
cd /d "%~dp0"
echo ============================================================
echo  Tworze skrot "PMT Planer" na pulpicie.
echo  Skrot uruchamia program bez pliku EXE - przez Pythona,
echo  ktory jest podpisany, wiec Windows go nie blokuje.
echo ============================================================
echo(
if not exist "URUCHOM_PROGRAM.bat" goto :brak
set "IKONA=%~dp0pmt_logo.ico"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\PMT Planer.lnk'); $s.TargetPath='%~dp0URUCHOM_PROGRAM.bat'; $s.WorkingDirectory='%~dp0'; if (Test-Path '%IKONA%') { $s.IconLocation='%IKONA%' }; $s.WindowStyle=7; $s.Description='PMT Planer'; $s.Save()"
if errorlevel 1 goto :zle
echo GOTOWE. Skrot "PMT Planer" jest na pulpicie.
goto :stop
:zle
echo [BLAD] Nie udalo sie utworzyc skrotu.
goto :stop
:brak
echo [BLAD] Brak URUCHOM_PROGRAM.bat w tym folderze.
:stop
echo(
pause
