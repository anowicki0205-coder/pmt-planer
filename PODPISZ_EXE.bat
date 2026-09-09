@echo off
setlocal EnableExtensions
title PMT - podpisanie pliku EXE
cd /d "%~dp0"
echo ============================================================
echo  PODPISYWANIE PROGRAMU CERTYFIKATEM
echo  Potrzebny jest wlasny certyfikat do podpisywania kodu
echo  oraz narzedzie signtool z Windows SDK.
echo ============================================================
echo(
set "PLIK=dist\PMT_Planer\PMT_Planer.exe"
if exist "%PLIK%" goto :mam_plik
set "PLIK=dist\PMT_Planer.exe"
if exist "%PLIK%" goto :mam_plik
echo [BLAD] Nie znalazlem zbudowanego programu w folderze dist.
goto :stop

:mam_plik
where signtool >nul 2>nul
if not errorlevel 1 goto :mam_signtool
echo [BLAD] Brak signtool. Zainstaluj Windows SDK:
echo   https://developer.microsoft.com/windows/downloads/windows-sdk/
goto :stop

:mam_signtool
if exist "certyfikat.pfx" goto :pfx
echo Nie widze pliku certyfikat.pfx w tym folderze.
echo Jesli masz certyfikat w magazynie Windows, uzyj:
echo   signtool sign /a /fd SHA256 /tr http://timestamp.sectigo.com /td SHA256 "%PLIK%"
goto :stop

:pfx
set /p HASLO=Podaj haslo do certyfikat.pfx: 
signtool sign /f certyfikat.pfx /p %HASLO% /fd SHA256 /tr http://timestamp.sectigo.com /td SHA256 "%PLIK%"
if errorlevel 1 goto :zle
echo(
echo GOTOWE. Plik podpisany. Sprawdz: prawy przycisk - Wlasciwosci - Podpisy cyfrowe
goto :stop

:zle
echo [BLAD] Podpisywanie nie powiodlo sie.

:stop
echo(
pause
