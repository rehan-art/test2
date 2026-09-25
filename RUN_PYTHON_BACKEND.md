# HTML + Python Placard Generator

This project keeps the original Feane HTML template and adds a Python FastAPI backend.

## Run on Windows

1. Open PowerShell in this folder.
2. Create/activate a virtual environment:
   `python -m venv .venv`
   `.venv\Scripts\Activate.ps1`
3. Install:
   `pip install -r requirements.txt`
4. Start:
   `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
5. Open:
   `http://127.0.0.1:8000/placard-generator.html`

The browser UI calls Python through `/api/*`. Placards are generated as 3840x2400 PNG files.
