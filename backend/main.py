from pathlib import Path
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .placard_generator import generate_placard, FONT_DIR

BASE = Path(__file__).resolve().parent
GENERATED = BASE / "generated"
GENERATED.mkdir(exist_ok=True)
FONT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Placard Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def available_fonts():
    builtins = ["DejaVu Serif", "DejaVu Sans", "Liberation Serif", "Liberation Sans", "Times New Roman"]
    custom = sorted(p.stem for p in FONT_DIR.iterdir() if p.suffix.lower() in {".ttf", ".otf"})
    return list(dict.fromkeys(builtins + custom))

@app.get("/api/fonts")
def fonts():
    return {"fonts": available_fonts()}

@app.post("/api/fonts/add")
async def add_font(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".ttf", ".otf"}:
        raise HTTPException(400, "Only .TTF and .OTF fonts are supported.")
    safe_name = Path(file.filename).name
    dest = FONT_DIR / safe_name
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return {"ok": True, "fonts": available_fonts()}

@app.delete("/api/fonts/{font_name}")
def remove_font(font_name: str):
    if font_name in {"DejaVu Serif", "DejaVu Sans", "Liberation Serif", "Liberation Sans", "Times New Roman"}:
        raise HTTPException(400, "Built-in fonts cannot be removed.")
    for p in FONT_DIR.iterdir():
        if p.stem == font_name and p.suffix.lower() in {".ttf", ".otf"}:
            p.unlink()
            return {"ok": True, "fonts": available_fonts()}
    raise HTTPException(404, "Font not found.")

@app.post("/api/generate")
def generate(passenger_name: str = Form(...), font_family: str = Form("DejaVu Serif")):
    if font_family not in available_fonts():
        raise HTTPException(400, "Font is not available.")
    file_name = f"placard_{uuid.uuid4().hex}.png"
    out = GENERATED / file_name
    generate_placard(passenger_name, out, font_family)
    return {"ok": True, "width": 3840, "height": 2400, "file": f"/generated/{file_name}"}

app.mount("/generated", StaticFiles(directory=str(GENERATED)), name="generated")
app.mount("/", StaticFiles(directory=str(BASE.parent), html=True), name="site")
