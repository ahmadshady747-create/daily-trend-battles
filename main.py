#!/usr/bin/env python3
"""
=============================================================================
  main.py  |  Daily Trend Battle Generator
  - Fetches/fallback trends
  - Generates data.json
  - Generates OG images (Pillow)
  - Generates SEO sitemap.xml
  - Pushes Discord Webhook embeds with image attachments
  - Pushes Telegram Bot photo messages with inline keyboard
=============================================================================
"""

import os
import sys
import json
import random
import hashlib
import requests
from datetime import datetime, timezone
from pathlib import Path

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# CONFIGURATION
# =============================================================================
CATEGORIES = {
    "Sports": ["Football", "NBA", "NFL", "Soccer", "Tennis", "F1", "UFC", "Cricket", "Baseball", "Golf"],
    "Tech": ["iPhone", "Android", "AI", "ChatGPT", "Tesla", "Bitcoin", "PlayStation", "Xbox", "Nintendo", "MacBook"],
    "Economy": ["Stocks", "Crypto", "Gold", "Oil", "Dollar", "Euro", "Bitcoin", "NFT", "Real Estate", "Bonds"]
}

BATTLE_PAIRS = {
    "Sports": [
        ("Kansas City Chiefs", "Philadelphia Eagles"),
        ("Lakers", "Celtics"),
        ("Real Madrid", "Barcelona"),
        ("Chiefs", "49ers"),
        ("Messi", "Ronaldo"),
    ],
    "Tech": [
        ("PlayStation 5", "Xbox Series X"),
        ("iPhone", "Samsung Galaxy"),
        ("MacBook", "Windows PC"),
        ("ChatGPT", "Claude"),
        ("Tesla", "BYD"),
    ],
    "Economy": [
        ("Bonds", "Equities"),
        ("Gold", "Bitcoin"),
        ("Dollar", "Euro"),
        ("Stocks", "Real Estate"),
        ("Crypto", "Gold"),
    ]
}

OG_DIR = Path("public/og")
DATA_FILE = Path("data.json")
SITEMAP_FILE = Path("public/sitemap.xml")

# =============================================================================
# UTILITIES
# =============================================================================
def generate_id(category, option_a, option_b, date_str):
    base = f"{date_str}-{category}-{option_a}-vs-{option_b}"
    return f"{date_str}-{category.lower()}-{hashlib.md5(base.encode()).hexdigest()[:8]}"

def get_today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def ensure_dirs():
    OG_DIR.mkdir(parents=True, exist_ok=True)
    SITEMAP_FILE.parent.mkdir(parents=True, exist_ok=True)

# =============================================================================
# TREND FETCHING (with robust fallback)
# =============================================================================
def fetch_trends():
    """Fetch daily trends from Google Trends or use curated fallback."""
    if TrendReq is None:
        print("[WARN] pytrends not available, using fallback data.")
        return None

    trends = {"Sports": [], "Tech": [], "Economy": []}
    try:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=2)
        for cat, keywords in CATEGORIES.items():
            try:
                pytrends.build_payload(keywords[:5], cat=0, timeframe='now 1-d', geo='US')
                data = pytrends.interest_over_time()
                if data is not None and not data.empty and 'isPartial' in data.columns:
                    data = data.drop('isPartial', axis=1)
                    avg_interest = data.mean().sort_values(ascending=False)
                    top = [str(k) for k in avg_interest.index[:2]]
                    if len(top) >= 2:
                        trends[cat] = [(top[0], top[1])]
            except Exception as e:
                print(f"[WARN] Failed to fetch trends for {cat}: {e}")
                continue
    except Exception as e:
        print(f"[WARN] pytrends initialization failed: {e}")
        return None

    if all(len(v) == 0 for v in trends.values()):
        return None
    return trends

def get_battle_pairs():
    trends = fetch_trends()
    if trends is None:
        print("[INFO] Using fallback battle pairs.")
        return BATTLE_PAIRS

    result = {}
    for cat in CATEGORIES:
        if cat in trends and len(trends[cat]) > 0:
            result[cat] = trends[cat]
        else:
            result[cat] = BATTLE_PAIRS[cat]
    return result

# =============================================================================
# DATA GENERATION
# =============================================================================
def generate_battles():
    date_str = get_today_str()
    pairs = get_battle_pairs()
    battles = []

    for category, pair_list in pairs.items():
        option_a, option_b = random.choice(pair_list)
        battle_id = generate_id(category, option_a, option_b, date_str)
        voting_key = f"battles/{category.lower()}/{option_a.lower().replace(' ', '-')}-vs-{option_b.lower().replace(' ', '-')}/{date_str}"

        battle = {
            "id": battle_id,
            "category": category,
            "battle_title": f"The Ultimate {category} Clash: {option_a} vs {option_b} — Who Wins Today?",
            "option_a": option_a,
            "option_b": option_b,
            "voting_api_key": voting_key,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        battles.append(battle)

    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": date_str,
        "battles": battles
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[DATA] Generated {len(battles)} battles in {DATA_FILE}")
    return data

# =============================================================================
# OG IMAGE GENERATION
# =============================================================================
IMAGE_SIZE = (1200, 630)

CATEGORY_STYLES = {
    "Sports":  {"bg": "#1a1a2e", "accent": "#e94560", "emoji": "⚽"},
    "Tech":    {"bg": "#16213e",  "accent": "#533483", "emoji": "💻"},
    "Economy": {"bg": "#0f3460",  "accent": "#f39c12", "emoji": "📈"},
}

def _get_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def _text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def generate_battle_og(battle, date_str):
    cat = battle["category"]
    a = battle["option_a"]
    b = battle["option_b"]
    bid = battle["id"]

    style = CATEGORY_STYLES.get(cat, {"bg": "#1a1a2e", "accent": "#e94560", "emoji": "🔥"})

    img = Image.new("RGB", IMAGE_SIZE, style["bg"])
    draw = ImageDraw.Draw(img)

    font_cat = _get_font(36)
    font_title = _get_font(56)
    font_vs = _get_font(160)
    font_meta = _get_font(24)

    # Category badge
    cat_text = f"{style['emoji']} {cat.upper()}"
    tw, th = _text_size(draw, cat_text, font_cat)
    padding = 20
    draw.rounded_rectangle([50, 50, 70 + tw + padding, 110], radius=10, fill=style["accent"])
    draw.text((60, 58), cat_text, fill="white", font=font_cat)

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
    site_url = os.environ.get("SITE_URL", "daily-trend-battles.vercel.app").replace("https://", "").replace("http://", "")
    draw.text((80, 560), f"Daily Trend Battles • {date_str}", fill="#888888", font=font_meta)
    draw.text((80, 590), site_url, fill="#666666", font=font_meta)

    path = OG_DIR / f"{bid}.png"
    img.save(path, "PNG")
    print(f"[OG] {path}")
    return str(path)

def generate_all_og(data):
    files = []
    for battle in data["battles"]:
        files.append(generate_battle_og(battle, data["date"]))
    return files

# =============================================================================
# SITEMAP GENERATION
# =============================================================================
def generate_sitemap(data):
    site_url = os.environ.get("SITE_URL", "https://daily-trend-battles.vercel.app").rstrip("/")

    urls = []
    # Home page
    urls.append({
        "loc": site_url + "/",
        "lastmod": data["date"],
        "changefreq": "daily",
        "priority": "1.0"
    })

    # Battle pages
    for battle in data["battles"]:
        urls.append({
            "loc": f"{site_url}/battle/{battle['id']}",
            "lastmod": data["date"],
            "changefreq": "daily",
            "priority": "0.8"
        })

    # Preserve previous URLs from existing sitemap (SEO history)
    existing_urls = []
    if SITEMAP_FILE.exists():
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(SITEMAP_FILE)
            root = tree.getroot()
            ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
            for url in root.findall(f".//{ns}url"):
                loc = url.find(f"{ns}loc")
                lastmod = url.find(f"{ns}lastmod")
                if loc is not None and loc.text and loc.text not in [u["loc"] for u in urls]:
                    existing_urls.append({
                        "loc": loc.text,
                        "lastmod": lastmod.text if lastmod is not None else data["date"],
                        "changefreq": "weekly",
                        "priority": "0.6"
                    })
        except Exception as e:
            print(f"[WARN] Could not parse existing sitemap: {e}")

    all_urls = urls + existing_urls[:50]  # Keep last 50 old URLs max

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    for url in all_urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{url['loc']}</loc>")
        xml_lines.append(f"    <lastmod>{url['lastmod']}</lastmod>")
        xml_lines.append(f"    <changefreq>{url['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{url['priority']}</priority>")
        xml_lines.append("  </url>")

    xml_lines.append("</urlset>")

    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_lines))

    print(f"[SITEMAP] Generated {SITEMAP_FILE} with {len(all_urls)} URLs")

# =============================================================================
# DISCORD NOTIFICATION
# =============================================================================
def send_discord(data):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[DISCORD] No webhook URL configured, skipping.")
        return

    site_url = os.environ.get("SITE_URL", "https://daily-trend-battles.vercel.app").rstrip("/")

    for battle in data["battles"]:
        og_path = OG_DIR / f"{battle['id']}.png"

        embed = {
            "title": battle["battle_title"],
            "url": f"{site_url}/battle/{battle['id']}",
            "color": 0x58a6ff,
            "fields": [
                {"name": "🔥 Option A", "value": battle["option_a"], "inline": True},
                {"name": "⚡ Option B", "value": battle["option_b"], "inline": True},
                {"name": "🏷️ Category", "value": battle["category"], "inline": True}
            ],
            "image": {"url": f"attachment://{og_path.name}"},
            "footer": {"text": f"Daily Trend Battles • {data['date']}"},
            "timestamp": data["generated_at"]
        }

        payload = {"embeds": [embed]}

        try:
            with open(og_path, "rb") as f:
                files = {"file": (og_path.name, f, "image/png")}
                response = requests.post(
                    webhook_url,
                    data={"payload_json": json.dumps(payload)},
                    files=files,
                    timeout=30
                )

            if response.status_code in (200, 204):
                print(f"[DISCORD] Sent battle: {battle['id']}")
            else:
                print(f"[DISCORD] Failed for {battle['id']}: HTTP {response.status_code}")
        except Exception as e:
            print(f"[DISCORD] Error sending {battle['id']}: {e}")

# =============================================================================
# TELEGRAM NOTIFICATION
# =============================================================================
def send_telegram(data):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHANNEL_ID") or os.environ.get("TELEGRAM_MY_CHAT_ID")

    if not bot_token or not chat_id:
        print("[TELEGRAM] No bot token or chat ID configured, skipping.")
        return

    site_url = os.environ.get("SITE_URL", "https://daily-trend-battles.vercel.app").rstrip("/")
    api_url = f"https://api.telegram.org/bot{bot_token}"

    for battle in data["battles"]:
        og_path = OG_DIR / f"{battle['id']}.png"

        message = (
            f"🔥 *{battle['battle_title']}*\n\n"
            f"⚔️ *{battle['option_a']}* vs *{battle['option_b']}*\n"
            f"🏷️ Category: *{battle['category']}*\n\n"
            f"🗳️ [Vote Now]({site_url}/battle/{battle['id']})"
        )

        try:
            with open(og_path, "rb") as f:
                files = {"photo": f}
                payload = {
                    "chat_id": chat_id,
                    "caption": message,
                    "parse_mode": "Markdown",
                    "reply_markup": json.dumps({
                        "inline_keyboard": [[
                            {"text": f"🔥 {battle['option_a']}", "url": f"{site_url}/battle/{battle['id']}"},
                            {"text": f"⚡ {battle['option_b']}", "url": f"{site_url}/battle/{battle['id']}"}
                        ]]
                    })
                }

                response = requests.post(
                    f"{api_url}/sendPhoto",
                    data=payload,
                    files=files,
                    timeout=30
                )

            if response.status_code == 200:
                print(f"[TELEGRAM] Sent battle: {battle['id']}")
            else:
                print(f"[TELEGRAM] Failed for {battle['id']}: HTTP {response.status_code} - {response.text[:200]}")
        except Exception as e:
            print(f"[TELEGRAM] Error sending {battle['id']}: {e}")

# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("Daily Trend Battle Generator")
    print("=" * 60)

    ensure_dirs()

    # Step 1: Generate battles
    data = generate_battles()

    # Step 2: Generate OG images
    generate_all_og(data)

    # Step 3: Generate sitemap
    generate_sitemap(data)

    # Step 4: Send notifications
    send_discord(data)
    send_telegram(data)

    print("=" * 60)
    print("Done!")
    print("=" * 60)

if __name__ == "__main__":
    main()