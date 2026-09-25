from pathlib import Path
import json
import re
from PIL import Image

LOGO_DIR = Path(__file__).resolve().parent / "assets" / "logos"
CUSTOM_MAP_FILE = LOGO_DIR / "custom_logo_map.json"
LOGO_DIR.mkdir(parents=True, exist_ok=True)

# Matching is based on the Excel Customer field. The aliases make matching
# tolerant of Pvt/Pvt., Private/Private Limited, ampersands, etc.
LOGOS = {
    "AMBASSADOR TOURS & TRAVELS LLP": "ambassador_tours.png",
    "INDIAN TRAVEL HOUSE": "indian_travel_house.png",
    "DENEB & POLLUX TOURS AND TRAVEL PVT. LTD.": "deneb_pollux.png",
    "GIRIRAJ MOBILITY SERVICES PRIVATE LIMITED": "giriraj_mobility.png",
    "VOLT MOBILITY PRIVATE LIMITED": "volt_mobility.png",
    "VERSETRA TRAVEL PVT LTD": "versetra_travel.png",
    "TRAVEL TOGETHER": "travel_together.png",
    "SWIFT ELITE CARS PRIVATE LIMITED": "swift_elite.png",
    "SHRIJI CAR RENTALS PRIVATE LIMITED": "shriji_car_rentals.png",
    "SKIL CABS PRIVATE LIMITED": "skil_cabs.png",
    "RAMISRO CARS": "ramisro_cars.png",
    "KARUNADU SERVICES PVT LIMITED": "karunadu_services.png",
    "EMINENT TRANSIT": "eminent_transit.png",
    "EURO CAB SERVICES PRIVATE LIMITED": "euro_cab.png",
    "1 TO 1 CAR RENTALS": "one_to_one.png",
    "ALLY CAR RENTAL": "ally_car_rental.png",
}


def normalize(value):
    value = "" if value is None else str(value)
    value = value.upper().replace("&", " AND ")
    value = value.replace("PRIVATE LIMITED", "PVT LTD")
    value = value.replace("PRIVATE LTD", "PVT LTD")
    value = value.replace("PVT. LTD.", "PVT LTD")
    value = value.replace("PVT LTD.", "PVT LTD")
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _load_custom_map():
    if not CUSTOM_MAP_FILE.exists():
        return {}
    try:
        data = json.loads(CUSTOM_MAP_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_custom_map(data):
    CUSTOM_MAP_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _all_logo_mappings():
    mappings = dict(LOGOS)
    mappings.update(_load_custom_map())
    return mappings


def _safe_filename(company_name):
    normalized = normalize(company_name).lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return (normalized or "custom_logo") + ".png"


def _remove_edge_background(image, threshold=35):
    """Remove a near-uniform background connected to the image edges.

    Transparent PNGs are left transparent. For RGB/RGBA images with a white,
    black, or other near-uniform edge background, only pixels connected to the
    outside edge and sufficiently close to the sampled edge color are removed.
    This avoids painting a new background behind the uploaded logo.
    """
    image = image.convert("RGBA")
    if image.getchannel("A").getextrema() == (0, 0):
        return image

    # If the file already has meaningful transparency, preserve it.
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] < 255:
        return image

    w, h = image.size
    px = image.load()
    samples = []
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        samples.append(px[x, y][:3])

    bg = tuple(round(sum(c[i] for c in samples) / len(samples)) for i in range(3))

    # Background removal is safest for light/dark neutral backgrounds.
    if max(bg) - min(bg) > 30 and not (max(bg) > 235 or max(bg) < 25):
        return image

    def close(rgb):
        return max(abs(rgb[i] - bg[i]) for i in range(3)) <= threshold

    from collections import deque
    q = deque()
    visited = bytearray(w * h)

    def add(x, y):
        idx = y * w + x
        if not visited[idx] and close(px[x, y][:3]):
            visited[idx] = 1
            q.append((x, y))

    for x in range(w):
        add(x, 0)
        add(x, h - 1)
    for y in range(h):
        add(0, y)
        add(w - 1, y)

    while q:
        x, y = q.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h:
                add(nx, ny)

    out = image.copy()
    out_px = out.load()
    for y in range(h):
        for x in range(w):
            if visited[y * w + x]:
                r, g, b, _ = out_px[x, y]
                out_px[x, y] = (r, g, b, 0)
    return out


def save_logo(company_name, uploaded_file, remove_background=False):
    """Add or replace a logo and persist the Customer -> PNG mapping."""
    company_name = str(company_name or "").strip()
    if not company_name:
        raise ValueError("Customer/company name is required.")
    if uploaded_file is None:
        raise ValueError("Please upload a logo image.")

    image = Image.open(uploaded_file)
    image = image.convert("RGBA")

    # Never add a background. Existing transparency is preserved exactly.
    if remove_background:
        image = _remove_edge_background(image)

    filename = _safe_filename(company_name)
    path = LOGO_DIR / filename
    image.save(path, format="PNG", optimize=True)

    custom_map = _load_custom_map()
    custom_map[normalize(company_name)] = filename
    _save_custom_map(custom_map)

    return path


def available_logo_customers():
    """Return all built-in and user-added customer names."""
    result = list(LOGOS.keys())
    for normalized_name in _load_custom_map():
        if normalized_name not in [normalize(x) for x in result]:
            result.append(normalized_name)
    return sorted(result, key=str.upper)


def resolve_logo(company_name):
    """Return the logo Path matching an Excel company/customer name, or None."""
    n = normalize(company_name)
    if not n:
        return None

    mappings = _all_logo_mappings()
    normalized_mappings = {normalize(k): LOGO_DIR / v for k, v in mappings.items()}

    exact = normalized_mappings.get(n)
    if exact and exact.exists():
        return exact

    matches = sorted(normalized_mappings.items(), key=lambda x: len(x[0]), reverse=True)
    for key, path in matches:
        if key in n or n in key:
            if path.exists():
                return path

    return None


def logo_name(company_name):
    path = resolve_logo(company_name)
    return path.name if path else ""
