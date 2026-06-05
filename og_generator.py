#!/usr/bin/env python3
"""
=============================================================================
  OG Image Generator  |  og_generator.py
  Generates 1200x630 shareable images for each battle.
  Saves to: public/og/{battle_id}.png
=============================================================================
"""

import json
import os
from PIL import Image, ImageDraw, ImageFont

OG_DIR = "public/og"
IMAGE_SIZE = (1200, 630)

CATEGORY_STYLES = {
    "Sports":  {"bg": "#1a1a2e", "accent": "#e94560", "emoji": "⚽"},
    "Tech":    {"bg": "#16213e",  "accent": "#533483", "emoji": "💻"},
    "Economy": {"bg": "#0f3460",  "accent": "#f39c12", "emoji": "📈"},
}

def _ensure_dir():
    os.makedirs(OG_DIR, exist_ok=True)

def _get_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def _text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def generate_battle_og(battle, date_str):
    _ensure_dir()
    cat = battle["category"]
    a = battle["option_a"]
    b = battle["option_b"]
    bid = battle["id"]

    style = CATEGORY_STYLES.get(cat, {"bg": "#1a1a2e", "accent": "#e94560"})

    img = Image.new("RGB", IMAGE_SIZE, style["bg"])
    draw = ImageDraw.Draw(img)

    font_cat = _get_font(36)
    font_title = _get_font(56)
    font_vs = _get_font(160)
    font_meta = _get_font(24)

    # Category badge
    tw, th = _text_size(draw, cat.upper(), font_cat)
    draw.rectangle([50, 50, 80 + tw, 110], fill=style["accent"])
    draw.text((60, 58), cat.upper(), fill="white", font=font_cat)

    # VS
    vw, vh = _text_size(draw, "VS", font_vs)
    vx = (IMAGE_SIZE[0] - vw) // 2
    vy = (IMAGE_SIZE[1] - vh) // 2 - 10
    draw.text((vx, vy), "VS", fill=style["accent"], font=font_vs)

    # Option A (left)
    draw.text((80, 260), a, fill="white", font=font_title)

    # Option B (right-aligned)
    bw, _ = _text_size(draw, b, font_title)
    draw.text((IMAGE_SIZE[0] - bw - 80, 260), b, fill="white", font=font_title)

    # Meta
    draw.text((80, 560), f"Daily Trend Battles • {date_str}", fill="#888888", font=font_meta)
    draw.text((80, 590), "daily-trend-battles.vercel.app", fill="#666666", font=font_meta)

    path = f"{OG_DIR}/{bid}.png"
    img.save(path, "PNG")
    print(f"[OG] {path}")
    return path

def generate_all_og(data_file="data.json"):
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    files = []
    for battle in data["battles"]:
        files.append(generate_battle_og(battle, data["date"]))
    return files

if __name__ == "__main__":
    generate_all_og()
