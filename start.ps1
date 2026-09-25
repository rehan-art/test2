$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  py -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$PWD\.venv\Scripts\python.exe' '$PWD\backend\app.py'"

if (-not (Test-Path "node_modules")) {
  npm install
}

Write-Host "Frontend: http://localhost:3000"
Write-Host "Python API: http://127.0.0.1:5001"
npm run dev
