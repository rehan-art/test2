@echo off
setlocal
cd /d "%~dp0"

echo.
echo ================================================
echo   Gallery + Airport Placard Studio
echo ================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating Python virtual environment...
  py -m venv .venv
  if errorlevel 1 (
    echo Could not create the Python environment.
    pause
    exit /b 1
  )
) else (
  echo [1/4] Python environment already exists.
)

echo [2/4] Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo Python dependency installation failed.
  pause
  exit /b 1
)

echo [3/4] Starting Python backend...
start "Airport Placard API" cmd /k ""%CD%\.venv\Scripts\python.exe" "%CD%\backend\app.py""

if not exist "node_modules" (
  echo [4/4] Installing Node dependencies...
  call npm install
  if errorlevel 1 (
    echo Node dependency installation failed.
    pause
    exit /b 1
  )
) else (
  echo [4/4] Node dependencies already installed.
)

echo.
echo Frontend starting at http://localhost:3000
echo Python API at http://127.0.0.1:5001
echo.
call npm run dev
