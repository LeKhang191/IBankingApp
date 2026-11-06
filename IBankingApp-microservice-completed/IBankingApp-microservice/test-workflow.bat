@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\test-workflow.ps1" %*
set EXITCODE=%ERRORLEVEL%
echo.
if not "%EXITCODE%"=="0" (
  echo Workflow test FAILED. Exit code: %EXITCODE%
) else (
  echo Workflow test PASSED.
)
pause
exit /b %EXITCODE%
