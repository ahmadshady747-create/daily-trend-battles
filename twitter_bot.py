#!/usr/bin/env python3
"""
=============================================================================
  Twitter/X Auto-Poster via Playwright  |  twitter_bot.py
  Logs in like a real user and posts the daily battles thread.
  FREE — no Twitter API subscription required.
  
  REQUIRED GitHub Secrets:
    TWITTER_USERNAME  (email or @handle)
    TWITTER_PASSWORD
    TWITTER_PHONE     (optional, for 2FA/verification challenges)
=============================================================================
"""

import json
import os
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def _load_battles(data_file="data.json"):
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["date"], data["battles"]


def _build_tweet(date_str, battles):
    lines = [f"🔥 Daily Trend Battles — {date_str}", ""]
    emojis = {"Sports": "⚽", "Tech": "💻", "Economy": "📈"}
    for b in battles:
        emoji = emojis.get(b["category"], "⚔️")
        lines.append(f"{emoji} {b['category']}: {b['option_a']} vs {b['option_b']}")
    lines.extend(["", "Cast your vote 👇", "https://daily-trend-battles.vercel.app"])
    return "\n".join(lines)


def post_battles(data_file="data.json"):
    username = os.environ.get("TWITTER_USERNAME")
    password = os.environ.get("TWITTER_PASSWORD")
    phone    = os.environ.get("TWITTER_PHONE", "")

    if not username or not password:
        print("[Twitter] TWITTER_USERNAME or TWITTER_PASSWORD not set. Skipping.")
        return

    date_str, battles = _load_battles(data_file)
    tweet_text = _build_tweet(date_str, battles)

    print("[Twitter] Starting Playwright browser...")

    with sync_playwright() as p:
        # Launch headless browser (GitHub Actions supports this)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            # ── Step 1: Login page ───────────────────────────────────────────
            print("[Twitter] Navigating to login...")
            page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
            time.sleep(2)

            # ── Step 2: Enter username/email ─────────────────────────────────
            print("[Twitter] Entering username...")
            page.wait_for_selector("input[autocomplete='username']", timeout=15000)
            page.fill("input[autocomplete='username']", username)
            page.keyboard.press("Enter")
            time.sleep(2)

            # ── Step 2b: Handle "Enter your phone number or username" challenge
            try:
                phone_input = page.wait_for_selector(
                    "input[data-testid='ocfEnterTextTextInput']", timeout=5000
                )
                if phone_input:
                    print("[Twitter] Phone/username challenge detected.")
                    page.fill("input[data-testid='ocfEnterTextTextInput']", phone or username)
                    page.keyboard.press("Enter")
                    time.sleep(2)
            except PlaywrightTimeout:
                pass  # No challenge, continue

            # ── Step 3: Enter password ───────────────────────────────────────
            print("[Twitter] Entering password...")
            page.wait_for_selector("input[name='password']", timeout=15000)
            page.fill("input[name='password']", password)
            page.keyboard.press("Enter")
            time.sleep(4)

            # ── Step 4: Verify login success ─────────────────────────────────
            if "login" in page.url or page.query_selector("input[name='password']"):
                print("[Twitter] Login may have failed or requires manual check.")
                # Take screenshot for debugging (saved in repo root)
                page.screenshot(path="twitter_debug.png")
                browser.close()
                return

            print("[Twitter] Logged in successfully.")

            # ── Step 5: Compose tweet ────────────────────────────────────────
            print("[Twitter] Composing tweet...")
            page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
            time.sleep(3)

            # Wait for the draft editor (contenteditable div)
            editor = page.wait_for_selector(
                "div[data-testid='tweetTextarea_0'] div[contenteditable='true']",
                timeout=15000,
            )

            # Type tweet text
            editor.click()
            page.keyboard.type(tweet_text, delay=10)
            time.sleep(1)

            # ── Step 6: Click Post ───────────────────────────────────────────
            post_btn = page.wait_for_selector(
                "button[data-testid='tweetButton']", timeout=10000
            )
            # Ensure button is enabled
            if post_btn.is_enabled():
                post_btn.click()
                print("[Twitter] Tweet posted successfully.")
            else:
                print("[Twitter] Post button disabled. Screenshot saved.")
                page.screenshot(path="twitter_debug.png")

            time.sleep(3)

        except Exception as exc:
            print(f"[Twitter] Error during automation: {exc}")
            try:
                page.screenshot(path="twitter_debug.png")
                print("[Twitter] Screenshot saved to twitter_debug.png for debugging.")
            except Exception:
                pass

        finally:
            browser.close()


if __name__ == "__main__":
    post_battles()
