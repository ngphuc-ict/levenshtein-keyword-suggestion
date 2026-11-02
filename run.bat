@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "UI=%ROOT%UI"
set "PYTHON=%BACKEND%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Creating Python virtual environment...
  py -3.12 -m venv "%BACKEND%\.venv"
  if errorlevel 1 py -3 -m venv "%BACKEND%\.venv"
  if errorlevel 1 (
    echo Could not create a Python virtual environment. Install Python 3.12 or newer.
    pause
    exit /b 1
  )
)

"%PYTHON%" -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo Installing backend dependencies...
  "%PYTHON%" -m pip install -r "%BACKEND%\requirements.txt"
  if errorlevel 1 (
    echo Backend dependency installation failed.
    pause
    exit /b 1
  )
)

if not exist "%UI%\node_modules" (
  echo Installing UI dependencies...
  pushd "%UI%"
  call npm install
  if errorlevel 1 (
    popd
    echo UI dependency installation failed.
    pause
    exit /b 1
  )
  popd
)

curl.exe -fsS "http://127.0.0.1:8000/health" >nul 2>&1
if errorlevel 1 (
  start "Keyword Suggestion Backend" cmd /k "cd /d ""%BACKEND%"" && ""%PYTHON%"" -m uvicorn app.main:app --reload --no-access-log --port 8000"
) else (
  echo Backend is already running at http://127.0.0.1:8000
)

start "Keyword Suggestion UI" cmd /k "cd /d ""%UI%"" && npm run dev -- --host 127.0.0.1"
echo Started the backend and UI. Keep their terminal windows open while using the app.
endlocal
