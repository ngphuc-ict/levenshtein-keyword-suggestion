@echo off
setlocal

set "HEALTH_URL=http://127.0.0.1:8000/health"
echo Calling backend health endpoint:
echo %HEALTH_URL%
echo.

curl.exe --fail --silent --show-error -i "%HEALTH_URL%"
if errorlevel 1 (
  echo.
  echo Health check failed. Start the backend first with run.bat.
  pause
  exit /b 1
)

echo.
pause
endlocal
