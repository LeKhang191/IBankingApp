@echo off
setlocal
cd /d "%~dp0"
title iBanking OneClick - ONECLICK-2-AUTOMATION
echo =============================================
echo  iBanking - ONECLICK-2-AUTOMATION
echo =============================================
rem Reset ONLY the disposable E2E Compose project (never the main app).
where docker >nul 2>&1
if errorlevel 1 (
  echo [FAILED] Docker CLI not found. Install or start Docker Desktop.
  pause
  exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
  echo [FAILED] Docker Engine is not running. Start Docker Desktop and retry.
  pause
  exit /b 1
)
if exist ".env" (
  echo [INFO] Deleting old E2E containers and E2E database volume...
  docker compose -f docker-compose.e2e.yml down -v --remove-orphans
  if errorlevel 1 (
    echo [FAILED] Could not reset isolated E2E environment.
    pause
    exit /b 1
  )
) else (
  echo [INFO] No .env yet. OneClick will create it first.
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\oneclick.ps1" -Mode automation
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
