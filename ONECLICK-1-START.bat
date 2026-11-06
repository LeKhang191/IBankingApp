@echo off
setlocal
cd /d "%~dp0"
title iBanking OneClick - ONECLICK-1-START
echo =============================================
echo  iBanking - ONECLICK-1-START
echo =============================================
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\oneclick.ps1" -Mode app
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" (
  echo OneClick failed with exit code %RESULT%.
) else (
  echo OneClick finished successfully.
)
echo.
pause
exit /b %RESULT%
