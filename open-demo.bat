@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "DEMO_FILE=%PROJECT_ROOT%dashboard\portfolio-dashboard.html"

if not exist "%DEMO_FILE%" (
  echo.
  echo [ERROR] Dashboard file not found:
  echo %DEMO_FILE%
  echo.
  echo Keep open-demo.bat inside the project root and try again.
  pause
  exit /b 1
)

start "Sports Product Analytics Demo" "%DEMO_FILE%"

if errorlevel 1 (
  echo.
  echo [ERROR] Windows could not open the dashboard in your default browser.
  pause
  exit /b 1
)

endlocal
exit /b 0
