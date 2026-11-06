@echo off
setlocal
cd /d "%~dp0"
title iBanking OneClick - ONECLICK-3-E2E
echo =============================================
echo  iBanking - ONECLICK-3-E2E
echo =============================================
rem Reset ONLY the isolated disposable E2E database and containers.
rem Never touch the main docker-compose.yml project.
if exist ".env" (
  echo [INFO] Resetting disposable E2E environment...
  docker compose -f docker-compose.e2e.yml down -v --remove-orphans
  if errorlevel 1 (
    echo [FAILED] Could not reset E2E environment. Check Docker Desktop.
    pause
    exit /b 1
  )
) else (
  echo [INFO] No .env yet; OneClick will create it before first startup.
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\oneclick.ps1" -Mode e2e
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
