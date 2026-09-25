from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 3840, 2400
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

OUTER_BORDER_MARGIN = 36
INNER_BORDER_MARGIN = 96
OUTER_BORDER_WIDTH = 19
INNER_BORDER_WIDTH = 12
SAFE_MARGIN = 228

BASE_DIR = Path(__file__).resolve().parent
FONT_DIR = BASE_DIR / "fonts"

FONT_FILES = {
    "DejaVu Sans": "DejaVuSans.ttf",
    "DejaVu Serif": "DejaVuSerif.ttf",
    "Liberation Sans": "LiberationSans-Regular.ttf",
    "Liberation Serif": "LiberationSerif-Regular.ttf",
}

def _find_font_file(name, bold=False):
    candidates = []
    if name == "Times New Roman":
        candidates = ["timesbd.ttf" if bold else "times.ttf"]
    elif name == "DejaVu Sans":
        candidates = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    elif name == "DejaVu Serif":
        candidates = ["DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"]
    elif name == "Liberation Sans":
        candidates = ["LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"]
    elif name == "Liberation Serif":
        candidates = ["LiberationSerif-Bold.ttf" if bold else "LiberationSerif-Regular.ttf"]
    else:
        candidates = [name]
    for c in candidates:
        p = FONT_DIR / c
        if p.exists():
            return p
        p = Path("/usr/share/fonts/truetype") / c
        if p.exists():
            return p
    return None

def get_font(size, font_family="DejaVu Serif"):
    p = _find_font_file(font_family, bold=True)
    if p:
        return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()

def bbox(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)

def text_width(draw, text, font):
    b = bbox(draw, text, font)
    return b[2] - b[0]

def text_height(draw, text, font):
    b = bbox(draw, text, font)
    return b[3] - b[1]

def clean_name(name):
    name = "GUEST" if name is None else str(name).strip()
    name = re.sub(r"\s+", " ", name)
    return name or "GUEST"

def separate_passengers(name):
    return [x.strip() for x in re.split(r"\s*(?:/|;)\s*", clean_name(name)) if x.strip()] or ["GUEST"]

def wrap_name(draw, name, font, max_width):
    words = name.split()
    lines, current = [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if text_width(draw, candidate.upper(), font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current.upper())
            current = word
    if current:
        lines.append(current.upper())
    return lines

def calculate_layout(draw, passenger_name, font_family):
    safe_left = INNER_BORDER_MARGIN + SAFE_MARGIN
    safe_right = WIDTH - INNER_BORDER_MARGIN - SAFE_MARGIN
    max_width = safe_right - safe_left
    name_top = 1164
    name_bottom = HEIGHT - INNER_BORDER_MARGIN - SAFE_MARGIN
    max_height = name_bottom - name_top
    passengers = separate_passengers(passenger_name)

    for size in range(432, 82, -4):
        font = get_font(size, font_family)
        lines = []
        for passenger in passengers:
            lines.extend(wrap_name(draw, passenger, font, max_width))
        if not lines:
            continue
        heights = [text_height(draw, line, font) for line in lines]
        gap = max(19, int(size * 0.10))
        total = sum(heights) + gap * (len(lines) - 1)
        if total <= max_height and all(text_width(draw, line, font) <= max_width for line in lines):
            return dict(lines=lines, font=font, line_gap=gap, total_height=total,
                        safe_left=safe_left, safe_right=safe_right,
                        name_top=name_top, name_bottom=name_bottom)
    font = get_font(86, font_family)
    lines = []
    for p in passengers:
        lines.extend(wrap_name(draw, p, font, max_width))
    heights = [text_height(draw, line, font) for line in lines]
    gap = 12
    return dict(lines=lines, font=font, line_gap=gap,
                total_height=sum(heights)+gap*max(0, len(lines)-1),
                safe_left=safe_left, safe_right=safe_right,
                name_top=name_top, name_bottom=name_bottom)

def draw_welcome(draw, font_family):
    safe_left = INNER_BORDER_MARGIN + SAFE_MARGIN
    safe_right = WIDTH - INNER_BORDER_MARGIN - SAFE_MARGIN
    max_width = safe_right - safe_left
    for size in range(492, 216, -4):
        font = get_font(size, font_family)
        width = text_width(draw, "WELCOME", font)
        if width <= max_width:
            height = text_height(draw, "WELCOME", font)
            x = (WIDTH - width) / 2
            y = 252
            if y + height < 1032:
                draw.text((x, y), "WELCOME", fill=BLACK, font=font)
                return

def generate_placard(passenger_name, output_path, font_family="DejaVu Serif"):
    image = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)
    draw.rectangle((OUTER_BORDER_MARGIN, OUTER_BORDER_MARGIN,
                    WIDTH-OUTER_BORDER_MARGIN, HEIGHT-OUTER_BORDER_MARGIN),
                   outline=BLACK, width=OUTER_BORDER_WIDTH)
    draw.rectangle((INNER_BORDER_MARGIN, INNER_BORDER_MARGIN,
                    WIDTH-INNER_BORDER_MARGIN, HEIGHT-INNER_BORDER_MARGIN),
                   outline=BLACK, width=INNER_BORDER_WIDTH)
    draw_welcome(draw, font_family)
    layout = calculate_layout(draw, passenger_name, font_family)
    y = layout["name_top"] + (layout["name_bottom"] - layout["name_top"] - layout["total_height"]) / 2
    for line in layout["lines"]:
        b = bbox(draw, line, layout["font"])
        w, h = b[2]-b[0], b[3]-b[1]
        x = max(layout["safe_left"], min((WIDTH-w)/2, layout["safe_right"]-w))
        y = max(layout["name_top"], min(y, layout["name_bottom"]-h))
        draw.text((x, y), line, fill=BLACK, font=layout["font"])
        y += h + layout["line_gap"]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "PNG", optimize=True)
    return output_path
