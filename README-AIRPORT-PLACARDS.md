# Gallery + Airport Placard Studio

This project keeps the original **Nimmal Gallery** Next.js site and integrates the working Python Airport Placard Generator as a `/placards` section.

## Architecture

- `app/` — original Next.js gallery plus the new Airport Placards UI.
- `backend/` — Python/Flask API using the working placard-generation modules.
- `backend/assets/logos/` — built-in customer logos and persistent customer mapping.
- `backend/fonts/` — placard fonts.
- `backend/generated_jobs/` — generated PNG/PDF/ZIP files (created at runtime).

The browser talks to Flask for Excel parsing, airport detection, logo matching, placard rendering, PDF creation, ZIP creation, logo management, and custom font management.

## Windows quick start

### Option A — one-click launcher

Double-click:

`start.bat`

It creates `.venv` if needed, installs the Python requirements, starts the Flask API, installs Node dependencies if needed, and starts Next.js.

Open:

`http://localhost:3000`

### Option B — two terminals

Terminal 1:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\app.py
```

Terminal 2:

```powershell
npm install
npm run dev
```

Open `http://localhost:3000`.

This method intentionally uses `.venv\Scripts\python.exe` directly, so PowerShell's `Activate.ps1` execution-policy restriction does not matter.

## Integrated features

- Indecab XLSX/XLS/CSV upload
- Today / All Dates / Select Date filters
- Airport detection from `Reporting Address`
- Total / airport / other-duty metrics
- 3840 × 2400 placard PNG output
- PDF output
- Download-all PDF ZIP
- Passenger name wrapping and multiple passengers
- Existing customer logo matching
- Add/replace customer logos
- Optional connected edge-background removal for logos
- Transparent logo preservation
- Built-in fonts
- TTF/OTF custom font upload
- Custom font removal
- Per-placard PNG preview
- Individual PDF download
- Complete duty details
- Responsive mobile-friendly interface
- Original gallery routes remain available

## Production

For deployment, run Flask behind a production WSGI server and set:

```text
NEXT_PUBLIC_API_URL=https://your-api-domain.example
```

The current `start.bat` setup is intended for local Windows use.
