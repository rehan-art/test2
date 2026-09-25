from pathlib import Path
from functools import lru_cache
import re
from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 1600, 1000

# Final placard export resolution: 4K-class 16:10 (3840 x 2400).
# The existing design is rendered at its native layout size first, then
# upsampled with high-quality Lanczos resampling so the current layout
# remains pixel-for-pixel consistent while the exported PNG is 4K.
OUTPUT_WIDTH, OUTPUT_HEIGHT = 3840, 2400

BLACK, WHITE = (0, 0, 0), (255, 255, 255)

OUTER_BORDER_MARGIN, INNER_BORDER_MARGIN = 15, 40
OUTER_BORDER_WIDTH, INNER_BORDER_WIDTH = 8, 5

SAFE_MARGIN = 95


BASE_DIR = Path(__file__).resolve().parent

FONT_FAMILIES = {
    "Times New Roman": {
        True: [Path(r"C:\Windows\Fonts\timesbd.ttf"), BASE_DIR / "fonts" / "LiberationSerif-Bold.ttf"],
        False: [Path(r"C:\Windows\Fonts\times.ttf"), BASE_DIR / "fonts" / "LiberationSerif-Regular.ttf"],
    },
    "DejaVu Serif": {
        True: [BASE_DIR / "fonts" / "DejaVuSerif-Bold.ttf"],
        False: [BASE_DIR / "fonts" / "DejaVuSerif.ttf"],
    },
    "DejaVu Sans": {
        True: [BASE_DIR / "fonts" / "DejaVuSans-Bold.ttf"],
        False: [BASE_DIR / "fonts" / "DejaVuSans.ttf"],
    },
    "Liberation Serif": {
        True: [BASE_DIR / "fonts" / "LiberationSerif-Bold.ttf"],
        False: [BASE_DIR / "fonts" / "LiberationSerif-Regular.ttf"],
    },
    "Liberation Sans": {
        True: [BASE_DIR / "fonts" / "LiberationSans-Bold.ttf"],
        False: [BASE_DIR / "fonts" / "LiberationSans-Regular.ttf"],
    },
    "Lato": {
        True: [BASE_DIR / "fonts" / "Lato-Bold.ttf"],
        False: [BASE_DIR / "fonts" / "Lato-Regular.ttf"],
    },
}

DEFAULT_FONT_FAMILY = "Times New Roman"
CUSTOM_FONT_DIR = BASE_DIR / "fonts" / "custom"

def _font_candidates(font_family, bold):
    if font_family in FONT_FAMILIES:
        return FONT_FAMILIES[font_family][bool(bold)]
    custom = CUSTOM_FONT_DIR / str(font_family)
    matches = list(CUSTOM_FONT_DIR.glob(f"{str(font_family)}.*"))
    if matches:
        return matches
    return FONT_FAMILIES[DEFAULT_FONT_FAMILY][bool(bold)]


# ============================================================
# FONT
# ============================================================

@lru_cache(maxsize=1024)
def get_font(size: int, bold=True, font_family=DEFAULT_FONT_FAMILY):

    candidates = _font_candidates(font_family, bold)

    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass

    raise RuntimeError(f"No scalable font found for {font_family}.")


# ============================================================
# TEXT HELPERS
# ============================================================

def text_width(draw, text, font):

    b = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    return b[2] - b[0]


def text_height(draw, text, font):

    b = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    return b[3] - b[1]


def clean_name(name):

    name = "" if name is None else str(name).strip()

    return re.sub(
        r"\s+",
        " ",
        name
    ) or "GUEST"


def separate_passengers(name):

    return [
        p.strip()
        for p in re.split(
            r"\s*(?:/|;)\s*",
            clean_name(name)
        )
        if p.strip()
    ] or ["GUEST"]


def wrap_name(draw, name, font, maximum_width):

    words = name.split()

    lines = []
    current = ""

    for word in words:

        candidate = (
            word
            if not current
            else current + " " + word
        )

        if text_width(
            draw,
            candidate.upper(),
            font
        ) <= maximum_width:

            current = candidate

        else:

            if current:
                lines.append(
                    current.upper()
                )

            current = word

    if current:
        lines.append(
            current.upper()
        )

    return lines


# ============================================================
# PASSENGER NAME LAYOUT
# ============================================================

def calculate_name_layout(draw, passenger_name, font_family=DEFAULT_FONT_FAMILY):

    safe_left = (
        INNER_BORDER_MARGIN +
        SAFE_MARGIN
    )

    safe_right = (
        WIDTH -
        INNER_BORDER_MARGIN -
        SAFE_MARGIN
    )

    maximum_width = (
        safe_right -
        safe_left
    )

    name_top = 500

    name_bottom = (
        HEIGHT -
        INNER_BORDER_MARGIN -
        SAFE_MARGIN
    )

    maximum_height = (
        name_bottom -
        name_top
    )

    passengers = separate_passengers(
        passenger_name
    )

    lo, hi, best = 35, 180, None

    while lo <= hi:

        size = (
            lo + hi
        ) // 2

        font = get_font(
            size,
            True,
            font_family
        )

        lines = [
            line
            for passenger in passengers
            for line in wrap_name(
                draw,
                passenger,
                font,
                maximum_width
            )
        ]

        heights = [
            text_height(
                draw,
                line,
                font
            )
            for line in lines
        ]

        gap = max(
            62,
            int(size * 0.42)
        )

        total = (
            sum(heights)
            +
            gap *
            max(
                0,
                len(lines) - 1
            )
        )

        if (
            all(
                text_width(
                    draw,
                    line,
                    font
                ) <= maximum_width
                for line in lines
            )
            and
            total <= maximum_height
        ):

            best = (
                font,
                lines,
                gap,
                total
            )

            lo = size + 1

        else:

            hi = size - 1

    if best is None:

        font = get_font(
            35,
            True,
            font_family
        )

        lines = [
            line
            for passenger in passengers
            for line in wrap_name(
                draw,
                passenger,
                font,
                maximum_width
            )
        ]

        gap = 62

        total = (
            sum(
                text_height(
                    draw,
                    x,
                    font
                )
                for x in lines
            )
            +
            gap *
            max(
                0,
                len(lines) - 1
            )
        )

    else:

        font, lines, gap, total = best

    return (
        lines,
        font,
        gap,
        total,
        safe_left,
        safe_right,
        name_top,
        name_bottom
    )


# ============================================================
# LOGO FITTING
# ============================================================

def _fit_logo(
    image,
    max_w=1250,
    max_h=800
):

    """
    Prepare a large logo for use
    as a subtle centered watermark.
    """

    logo = image.convert(
        "RGBA"
    )

    # Trim transparent margins first.
    alpha = logo.getchannel(
        "A"
    )

    bbox = alpha.getbbox()

    if bbox:
        logo = logo.crop(
            bbox
        )

    # Trim large uniform white/black
    # margins commonly present in
    # supplied logo screenshots.
    if (
        logo.width > 4
        and
        logo.height > 4
    ):

        rgb = logo.convert(
            "RGB"
        )

        px = rgb.load()

        corners = [
            px[0, 0],
            px[rgb.width - 1, 0],
            px[0, rgb.height - 1],
            px[
                rgb.width - 1,
                rgb.height - 1
            ]
        ]

        avg = tuple(
            sum(
                c[i]
                for c in corners
            ) // 4
            for i in range(3)
        )

        uniform = (
            max(
                max(
                    abs(
                        c[i] -
                        avg[i]
                    )
                    for i in range(3)
                )
                for c in corners
            )
            < 18
        )

        near_white = (
            min(avg) > 235
        )

        near_black = (
            max(avg) < 20
        )

        if (
            uniform
            and
            (
                near_white
                or
                near_black
            )
        ):

            threshold = 28

            mask = Image.new(
                "L",
                rgb.size,
                0
            )

            mp = mask.load()

            for yy in range(
                rgb.height
            ):

                for xx in range(
                    rgb.width
                ):

                    r, g, b = px[
                        xx,
                        yy
                    ]

                    if near_white:

                        is_content = (
                            min(r, g, b)
                            <
                            255 - threshold
                        )

                    else:

                        is_content = (
                            max(r, g, b)
                            >
                            threshold
                        )

                    if is_content:

                        mp[
                            xx,
                            yy
                        ] = 255

            bg_bbox = mask.getbbox()

            if bg_bbox:

                logo = logo.crop(
                    bg_bbox
                )

    scale = min(
        max_w / logo.width,
        max_h / logo.height
    )

    if abs(
        scale - 1.0
    ) > 0.001:

        logo = logo.resize(
            (
                max(
                    1,
                    round(
                        logo.width *
                        scale
                    )
                ),
                max(
                    1,
                    round(
                        logo.height *
                        scale
                    )
                )
            ),
            Image.Resampling.LANCZOS
        )

    return logo


# ============================================================
# LOGO LOADING
# ============================================================

@lru_cache(maxsize=32)
def load_logo(path_string):

    return _fit_logo(
        Image.open(
            path_string
        )
    )


# ============================================================
# WATERMARK
# ============================================================

def _watermark_logo(
    logo,
    opacity=0.23
):

    """
    Return a cached-size logo
    with low opacity for watermarking.
    """

    result = logo.copy()

    alpha = result.getchannel(
        "A"
    )

    alpha = alpha.point(
        lambda a:
        round(
            a * opacity
        )
    )

    result.putalpha(
        alpha
    )

    return result


@lru_cache(maxsize=32)
def load_watermark_logo(
    path_string
):

    return _watermark_logo(
        load_logo(
            path_string
        ),
        0.24
    )


# ============================================================
# TOP LOGO
# ============================================================

def draw_logo_top_right(
    canvas,
    logo_path
):

    """
    Place the company logo centered
    horizontally at the top with a
    soft drop shadow.

    Shadow equivalent to:

    filter:
        drop-shadow(
            -4px
            10px
            12px
            rgba(0,0,0,0.50)
        );
    """

    if not logo_path:
        return False

    path = Path(
        logo_path
    )

    if not path.exists():
        return False

    # ========================================================
    # LOAD LOGO
    # ========================================================

    logo = load_logo(
        str(path)
    ).copy()

    # ========================================================
    # INDIVIDUAL LOGO SIZE SETTINGS
    # ========================================================

    if (
        path.name.lower()
        ==
        "karunadu_services.png"
    ):

        max_w, max_h = (
            700,
            500
        )

    elif (
        path.name.lower()
        ==
        "shriji_car_rentals.png"
    ):

        max_w, max_h = (
            700,
            500
        )

    elif (
        path.name.lower()
        ==
        "swift_elite.png"
    ):

        max_w, max_h = (
            700,
            500
        )

    elif (
        path.name.lower()
        ==
        "euro_cab.png"
    ):

        max_w, max_h = (
            500,
            300
        )

    elif (
        path.name.lower()
        ==
        "indian_travel_house.png"
    ):

        max_w, max_h = (
            700,
            500
        )

    elif (
        path.name.lower()
        ==
        "versetra_travel.png"
    ):

        max_w, max_h = (
            700,
            500
        )

    else:

        max_w, max_h = (
            330,
            220
        )

    # ========================================================
    # RESIZE WHILE KEEPING ORIGINAL PROPORTIONS
    # ========================================================

    scale = min(
        max_w / logo.width,
        max_h / logo.height,
        1.0
    )

    if scale < 1.0:

        logo = logo.resize(
            (
                max(
                    1,
                    round(
                        logo.width *
                        scale
                    )
                ),
                max(
                    1,
                    round(
                        logo.height *
                        scale
                    )
                )
            ),
            Image.Resampling.LANCZOS
        )

    # Keep original transparency
    alpha = logo.getchannel(
        "A"
    )

    logo.putalpha(
        alpha
    )

    # ========================================================
    # CENTER LOGO HORIZONTALLY
    # ========================================================

    x = (
        WIDTH -
        logo.width
    ) // 2

    # Vertical position
    y = (
        INNER_BORDER_MARGIN +
        25
    )

    # ========================================================
    # DRAW LOGO (NO DROP SHADOW)
    # ========================================================

    canvas.paste(
        logo,
        (x, y),
        logo
    )

    return True


# ============================================================
# WELCOME TEXT
# ============================================================

def draw_welcome(
    draw,
    y=270,
    font_family=DEFAULT_FONT_FAMILY
):

    safe_left = (
        INNER_BORDER_MARGIN +
        SAFE_MARGIN
    )

    safe_right = (
        WIDTH -
        INNER_BORDER_MARGIN -
        SAFE_MARGIN
    )

    maximum_width = (
        safe_right -
        safe_left
    )

    for font_size in range(
        205,
        90,
        -2
    ):

        font = get_font(
            font_size,
            True,
            font_family
        )

        width = text_width(
            draw,
            "WELCOME",
            font
        )

        if width <= maximum_width:

            height = text_height(
                draw,
                "WELCOME",
                font
            )

            x = (
                WIDTH -
                width
            ) / 2

            if (
                y + height
                < 455
            ):

                draw.text(
                    (
                        x,
                        y
                    ),
                    "WELCOME",
                    fill=BLACK,
                    font=font
                )

                return


# ============================================================
# PASSENGER NAME
# ============================================================

def draw_passenger_name(
    draw,
    passenger_name,
    font_family=DEFAULT_FONT_FAMILY
):

    (
        lines,
        font,
        line_gap,
        total_height,
        safe_left,
        safe_right,
        name_top,
        name_bottom
    ) = calculate_name_layout(
        draw,
        passenger_name,
        font_family=font_family
    )

    start_y = (
        name_top
        +
        (
            (
                name_bottom -
                name_top -
                total_height
            )
            / 2
        )
    )

    current_y = start_y

    for line in lines:

        bbox = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        tw = (
            bbox[2] -
            bbox[0]
        )

        th = (
            bbox[3] -
            bbox[1]
        )

        x = max(
            safe_left,
            min(
                (
                    WIDTH -
                    tw
                ) / 2,
                safe_right -
                tw
            )
        )

        current_y = max(
            name_top,
            min(
                current_y,
                name_bottom -
                th
            )
        )

        draw.text(
            (
                x,
                current_y
            ),
            line,
            fill=BLACK,
            font=font
        )

        current_y += (
            th +
            line_gap
        )


# ============================================================
# GENERATE PLACARD
# ============================================================

def generate_placard(
    passenger_name,
    output_path,
    logo_path=None,
    font_family=DEFAULT_FONT_FAMILY
):

    # ========================================================
    # CREATE WHITE CANVAS
    # ========================================================

    image = Image.new(
        "RGB",
        (
            WIDTH,
            HEIGHT
        ),
        WHITE
    )

    draw = ImageDraw.Draw(
        image
    )

    # ========================================================
    # OUTER BORDER
    # ========================================================

    draw.rectangle(
        (
            OUTER_BORDER_MARGIN,
            OUTER_BORDER_MARGIN,
            WIDTH -
            OUTER_BORDER_MARGIN,
            HEIGHT -
            OUTER_BORDER_MARGIN
        ),
        outline=BLACK,
        width=OUTER_BORDER_WIDTH
    )

    # ========================================================
    # INNER BORDER
    # ========================================================

    draw.rectangle(
        (
            INNER_BORDER_MARGIN,
            INNER_BORDER_MARGIN,
            WIDTH -
            INNER_BORDER_MARGIN,
            HEIGHT -
            INNER_BORDER_MARGIN
        ),
        outline=BLACK,
        width=INNER_BORDER_WIDTH
    )

    # ========================================================
    # COMPANY LOGO
    # ========================================================

    has_logo = draw_logo_top_right(
        image,
        logo_path
    )

    # Recreate draw object after logo
    draw = ImageDraw.Draw(
        image
    )

    # ========================================================
    # WELCOME
    # ========================================================

    draw_welcome(
        draw,
        y=270,
        font_family=font_family
    )

    # ========================================================
    # PASSENGER NAME
    # ========================================================

    draw_passenger_name(
        draw,
        passenger_name,
        font_family=font_family
    )

    # ========================================================
    # SAVE
    # ========================================================

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Export every generated placard at 3840 x 2400.
    # Keep the existing 1600 x 1000 design coordinates unchanged so all
    # current spacing, logo positioning, borders and typography remain intact.
    if image.size != (OUTPUT_WIDTH, OUTPUT_HEIGHT):
        image = image.resize(
            (OUTPUT_WIDTH, OUTPUT_HEIGHT),
            Image.Resampling.LANCZOS
        )

    image.save(
        output_path,
        "PNG",
        compress_level=1
    )

    return output_path
