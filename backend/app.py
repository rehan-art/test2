
from __future__ import annotations

import io
import json
import re
import shutil
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from airport_detector import is_airport_reporting_address
from logo_manager import (
    resolve_logo,
    save_logo,
    available_logo_customers,
    normalize,
)
from placard_generator import generate_placard, FONT_FAMILIES, DEFAULT_FONT_FAMILY
from pdf_generator import create_pdf

BASE_DIR = Path(__file__).resolve().parent
JOBS_DIR = BASE_DIR / "generated_jobs"
CUSTOM_FONT_DIR = BASE_DIR / "fonts" / "custom"
LOGO_DIR = BASE_DIR / "assets" / "logos"
JOBS_DIR.mkdir(exist_ok=True)
CUSTOM_FONT_DIR.mkdir(parents=True, exist_ok=True)
LOGO_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_DATA_EXTENSIONS = {".xlsx", ".xls", ".csv"}
ALLOWED_FONT_EXTENSIONS = {".ttf", ".otf"}

DISPLAY_COLUMNS = [
    "Duty Id",
    "Customer",
    "Passengers",
    "Passenger Phone Numbers",
    "Status",
    "From city",
    "Requested Vehicle Type",
    "Start Date",
    "Reporting Time",
    "Reporting Address",
    "Drop Address",
    "Vehicle Type",
    "Vehicle Number",
    "Driver Name",
    "Driver Number",
    "Flight/Train Number",
]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024
CORS(app, resources={r"/api/*": {"origins": "*"}})


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def json_row(row: pd.Series) -> dict[str, str]:
    return {str(k): clean_value(v) for k, v in row.to_dict().items()}


def read_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_DATA_EXTENSIONS:
        raise ValueError("Please upload an XLSX, XLS, or CSV file.")
    source = io.BytesIO(file_bytes)
    if ext == ".csv":
        frame = pd.read_csv(source, dtype=str)
    else:
        frame = pd.read_excel(source, dtype=str)
    frame = frame.fillna("")
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame


def filter_airport_rows(df: pd.DataFrame, date_mode: str = "Today", selected_date: str = ""):
    missing = [c for c in ("Passengers", "Reporting Address") if c not in df.columns]
    if missing:
        raise ValueError("Required columns missing: " + ", ".join(missing))

    working = df.copy()

    if "Start Date" in working.columns:
        mode = (date_mode or "Today").strip()
        if mode == "Today":
            today = pd.Timestamp.now(tz="Asia/Kolkata").date()
            parsed = pd.to_datetime(working["Start Date"], dayfirst=True, errors="coerce")
            working = working[parsed.dt.date == today].copy()
        elif mode == "Select Date":
            if not selected_date:
                raise ValueError("Select a date before filtering.")
            target = pd.to_datetime(selected_date, errors="coerce")
            if pd.isna(target):
                raise ValueError("The selected date is invalid.")
            parsed = pd.to_datetime(working["Start Date"], dayfirst=True, errors="coerce")
            working = working[parsed.dt.date == target.date()].copy()

    airport_mask = working["Reporting Address"].map(is_airport_reporting_address)
    return working[airport_mask].copy()


def preview_payload(df: pd.DataFrame, airport_df: pd.DataFrame) -> dict[str, Any]:
    available = [c for c in DISPLAY_COLUMNS if c in airport_df.columns]
    rows = [json_row(row) for _, row in airport_df[available].iterrows()]
    total = len(df)
    airport = len(airport_df)
    return {
        "total_duties": total,
        "airport_reporting": airport,
        "other_duties": max(0, total - airport),
        "columns": available,
        "rows": rows,
    }


def safe_stem(value: str, fallback: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return (value or fallback)[:90]


def generate_job(airport_df: pd.DataFrame, job_id: str, font_family: str):
    job_dir = JOBS_DIR / job_id
    png_dir = job_dir / "png"
    pdf_dir = job_dir / "pdf"
    png_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for number, (index, row) in enumerate(airport_df.iterrows(), start=1):
        passenger = clean_value(row.get("Passengers")) or "GUEST"
        duty_id = clean_value(row.get("Duty Id")) or f"DUTY-{number}"
        logo_path = resolve_logo(clean_value(row.get("Customer")))
        base = f"{safe_stem(duty_id, f'DUTY-{number}')}_{safe_stem(passenger, 'GUEST')}"
        rows.append({
            "number": number,
            "index": int(index) if isinstance(index, int) else number - 1,
            "row": json_row(row),
            "passenger": passenger,
            "duty_id": duty_id,
            "customer": clean_value(row.get("Customer")),
            "logo": logo_path.name if logo_path else "",
            "logo_path": str(logo_path) if logo_path else "",
            "png_path": png_dir / f"{base}.png",
            "pdf_path": pdf_dir / f"{base}.pdf",
        })

    def one(item):
        generate_placard(
            item["passenger"],
            item["png_path"],
            logo_path=item["logo_path"] or None,
            font_family=font_family,
        )
        create_pdf(item["png_path"], item["pdf_path"])
        return item

    workers = min(4, max(1, len(rows)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        generated = list(executor.map(one, rows))

    zip_path = job_dir / "Airport_Placards_PDF.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in generated:
            zf.write(item["pdf_path"], arcname=item["pdf_path"].name)

    response_rows = []
    for item in generated:
        response_rows.append({
            "number": item["number"],
            "passenger": item["passenger"],
            "duty_id": item["duty_id"],
            "customer": item["customer"],
            "logo": item["logo"],
            "row": item["row"],
            "png_url": f"/api/jobs/{job_id}/png/{item['png_path'].name}",
            "pdf_url": f"/api/jobs/{job_id}/pdf/{item['pdf_path'].name}",
        })

    return {
        "job_id": job_id,
        "count": len(response_rows),
        "zip_url": f"/api/jobs/{job_id}/zip",
        "items": response_rows,
    }


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "airport-placard-backend"})


@app.post("/api/preview")
def preview():
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "Please choose an XLSX, XLS, or CSV file."}), 400
    try:
        data = uploaded.read()
        df = read_dataframe(data, uploaded.filename or "")
        result = preview_payload(
            df,
            filter_airport_rows(
                df,
                request.form.get("date_mode", "Today"),
                request.form.get("selected_date", ""),
            ),
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/generate")
def generate():
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "Please choose an XLSX, XLS, or CSV file."}), 400
    try:
        data = uploaded.read()
        df = read_dataframe(data, uploaded.filename or "")
        airport_df = filter_airport_rows(
            df,
            request.form.get("date_mode", "Today"),
            request.form.get("selected_date", ""),
        )
        if airport_df.empty:
            return jsonify({
                "error": "No airport reporting duties found for the selected date/filter.",
                "preview": preview_payload(df, airport_df),
            }), 400

        font_family = request.form.get("font_family", DEFAULT_FONT_FAMILY) or DEFAULT_FONT_FAMILY
        if font_family not in FONT_FAMILIES and not (CUSTOM_FONT_DIR / font_family).exists():
            font_family = DEFAULT_FONT_FAMILY

        job_id = uuid.uuid4().hex
        result = generate_job(airport_df, job_id, font_family)
        result["preview"] = preview_payload(df, airport_df)
        result["font_family"] = font_family
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/jobs/<job_id>/png/<path:filename>")
def job_png(job_id, filename):
    directory = JOBS_DIR / job_id / "png"
    return send_from_directory(directory, filename, as_attachment=False)


@app.get("/api/jobs/<job_id>/pdf/<path:filename>")
def job_pdf(job_id, filename):
    directory = JOBS_DIR / job_id / "pdf"
    return send_from_directory(directory, filename, as_attachment=True)


@app.get("/api/jobs/<job_id>/zip")
def job_zip(job_id):
    path = JOBS_DIR / job_id / "Airport_Placards_PDF.zip"
    if not path.exists():
        return jsonify({"error": "Job not found."}), 404
    return send_from_directory(path.parent, path.name, as_attachment=True)


@app.get("/api/logos")
def logos():
    from logo_manager import _all_logo_mappings
    mappings = _all_logo_mappings()
    return jsonify({
        "logos": [
            {"customer": name, "file": filename}
            for name, filename in sorted(mappings.items(), key=lambda x: x[0].upper())
            if (LOGO_DIR / filename).exists()
        ]
    })


@app.post("/api/logos")
def upload_logo():
    company = request.form.get("company", "").strip()
    uploaded = request.files.get("logo")
    remove_bg = request.form.get("remove_background", "false").lower() == "true"
    if not company or not uploaded:
        return jsonify({"error": "Company name and logo image are required."}), 400
    try:
        path = save_logo(company, uploaded.stream, remove_background=remove_bg)
        return jsonify({
            "success": True,
            "message": "Logo uploaded successfully.",
            "company": company,
            "filename": path.name,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/fonts")
def fonts():
    builtins = list(FONT_FAMILIES.keys())
    customs = sorted(p.name for p in CUSTOM_FONT_DIR.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_FONT_EXTENSIONS)
    return jsonify({"fonts": builtins + customs, "custom": customs})


@app.post("/api/fonts")
def upload_font():
    uploaded = request.files.get("font")
    if not uploaded:
        return jsonify({"error": "Please choose a TTF or OTF font file."}), 400
    filename = secure_filename(uploaded.filename or "")
    if Path(filename).suffix.lower() not in ALLOWED_FONT_EXTENSIONS:
        return jsonify({"error": "Only TTF and OTF fonts are supported."}), 400
    target = CUSTOM_FONT_DIR / filename
    uploaded.save(target)
    return jsonify({"success": True, "message": "Font uploaded successfully.", "filename": filename})


@app.delete("/api/fonts/<path:filename>")
def delete_font(filename):
    safe = Path(secure_filename(filename)).name
    path = CUSTOM_FONT_DIR / safe
    if not path.exists():
        return jsonify({"error": "Font not found."}), 404
    path.unlink()
    return jsonify({"success": True, "message": "Font removed successfully.", "filename": safe})


if __name__ == "__main__":
    print("Airport placard API running on http://127.0.0.1:5001")
    app.run(host="127.0.0.1", port=5001, debug=False)
