#!/usr/bin/env python3
"""
=============================================================================
  OG Image Generator  |  og_generator.py
  Generates 1200x630 shareable images for each battle.
  Saves to: public/og/{battle_id}.png

  FIX: Added _fit_font() to scale text down when option names are too wide,
       preventing overlap with the central "VS" label.
  FIX: Added _hex_to_rgb() so all color operations use tuples, not strings.
  FIX: Improved font candidate list with Ubuntu and Noto fonts available
       on ubuntu-latest GitHub Actions runners.
=============================================================================
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont

OG_DIR     = "public/og"
IMAGE_SIZE = (1200, 630)
W, H       = IMAGE_SIZE

CATEGORY_STYLES: dict[str, dict] = {
    "Sports":  {"bg": "#1a1a2e", "accent": "#e94560"},
    "Tech":    {"bg": "#16213e", "accent": "#533483"},
    "Economy": {"bg": "#0f3460", "accent": "#f39c12"},
}

# Ordered by likelihood of being present on ubuntu-latest
FONT_CANDIDATES: list[str] = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]


def _ensure_dir() -> None:
    os.makedirs(OG_DIR, exist_ok=True)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' string to (r, g, b) int tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Return the first available TrueType bold font at the given size."""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Last-resort fallback (very small but always present in Pillow)
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    """Return (width, height) of text rendered with font."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit_font(
    draw:      ImageDraw.ImageDraw,
    text:      str,
    max_size:  int,
    max_width: int,
    min_size:  int = 22,
) -> tuple[ImageFont.FreeTypeFont, int]:
    """
    Return the largest font (and its size) where `text` fits within `max_width`.
    Steps down by 4pt until min_size is reached.
    """
    size = max_size
    while size >= min_size:
        font = _get_font(size)
        w, _ = _text_size(draw, text, font)
        if w <= max_width:
            return font, size
        size -= 4
    return _get_font(min_size), min_size


def generate_battle_og(battle: dict, date_str: str) -> str:
    """
    Render a 1200×630 OG share image for one battle and save it as PNG.
    Returns the saved file path.
    """
    _ensure_dir()

    cat = battle["category"]
    a   = battle["option_a"]
    b   = battle["option_b"]
    bid = battle["id"]

    style      = CATEGORY_STYLES.get(cat, {"bg": "#1a1a2e", "accent": "#e94560"})
    bg_rgb     = _hex_to_rgb(style["bg"])
    accent_rgb = _hex_to_rgb(style["accent"])

    img  = Image.new("RGB", IMAGE_SIZE, bg_rgb)
    draw = ImageDraw.Draw(img)

    # ── Subtle accent side-bars ───────────────────────────────────────────
    # Left edge glow for option A
    for x in range(12):
        alpha = int(180 * (1 - x / 12))
        color = tuple(
            min(255, bg_rgb[i] + int((accent_rgb[i] - bg_rgb[i]) * alpha / 255))
            for i in range(3)
        )
        draw.line([(x, 0), (x, H)], fill=color)

    # Right edge glow for option B
    for x in range(12):
        alpha = int(180 * (1 - x / 12))
        color = tuple(
            min(255, bg_rgb[i] + int((accent_rgb[i] - bg_rgb[i]) * alpha / 255))
            for i in range(3)
        )
        draw.line([(W - 1 - x, 0), (W - 1 - x, H)], fill=color)

    # ── Category badge ────────────────────────────────────────────────────
    font_cat   = _get_font(32)
    badge_text = cat.upper()
    bw, bh     = _text_size(draw, badge_text, font_cat)
    pad_x, pad_y = 18, 9
    draw.rounded_rectangle(
        [50, 44, 50 + bw + pad_x * 2, 44 + bh + pad_y * 2],
        radius=8,
        fill=accent_rgb,
    )
    draw.text((50 + pad_x, 44 + pad_y), badge_text, fill="white", font=font_cat)

    # ── Central "VS" ──────────────────────────────────────────────────────
    font_vs    = _get_font(150)
    vs_text    = "VS"
    vw, vh     = _text_size(draw, vs_text, font_vs)
    vx         = (W - vw) // 2
    vy         = (H - vh) // 2 - 10
    # Drop shadow
    draw.text((vx + 4, vy + 4), vs_text, fill=(0, 0, 0), font=font_vs)
    draw.text((vx, vy),         vs_text, fill=accent_rgb,  font=font_vs)

    # ── Option labels ─────────────────────────────────────────────────────
    # Available width per side: from margin to just before centre VS label
    margin      = 60
    vs_half     = vw // 2
    center_x    = W // 2
    max_side_w  = center_x - vs_half - margin - 20  # small extra buffer

    # Option A — left-aligned
    font_a, _   = _fit_font(draw, a, max_size=52, max_width=max_side_w)
    aw, ah      = _text_size(draw, a, font_a)
    ay          = H // 2 - ah // 2 + 30
    draw.text((margin + 2, ay + 2), a, fill=(0, 0, 0), font=font_a)   # shadow
    draw.text((margin,     ay),     a, fill="white",   font=font_a)

    # Option B — right-aligned
    font_b, _   = _fit_font(draw, b, max_size=52, max_width=max_side_w)
    bw_t, bh_t  = _text_size(draw, b, font_b)
    bx          = W - margin - bw_t
    by          = H // 2 - bh_t // 2 + 30
    draw.text((bx + 2, by + 2), b, fill=(0, 0, 0), font=font_b)   # shadow
    draw.text((bx,     by),     b, fill="white",   font=font_b)

    # ── Footer ────────────────────────────────────────────────────────────
    font_meta = _get_font(22)
    draw.text(
        (margin, H - 55),
        f"Daily Trend Battles  •  {date_str}",
        fill="#888888",
        font=font_meta,
    )
    draw.text(
        (margin, H - 28),
        "daily-trend-battles.vercel.app",
        fill="#666666",
        font=font_meta,
    )

    path = f"{OG_DIR}/{bid}.png"
    img.save(path, "PNG", optimize=True)
    print(f"[OG] Generated: {path}")
    return path


def generate_all_og(data_file: str = "data.json") -> list[str]:
    """Generate OG images for every battle in the given data file."""
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    files: list[str] = []
    for battle in data.get("battles", []):
        try:
            path = generate_battle_og(battle, data["date"])
            files.append(path)
        except Exception as exc:
            print(f"[OG] ERROR generating image for {battle.get('id', '?')}: {exc}")

    return files


if __name__ == "__main__":
    generate_all_og()