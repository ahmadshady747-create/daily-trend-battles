#!/usr/bin/env python3
"""
=============================================================================
  Twitter/X Auto-Poster  |  twitter_bot.py
  Posts the daily battles thread to Twitter/X.
  Requires: TWITTER_API_KEY, TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
  (GitHub Secrets)
=============================================================================
"""

import json
import os

def post_battles(data_file="data.json"):
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        print("[Twitter] Credentials not configured. Skipping.")
        print("[Twitter] To enable: add TWITTER_API_KEY, TWITTER_API_SECRET, "
              "TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET to GitHub Secrets.")
        return

    try:
        import tweepy
    except ImportError:
        print("[Twitter] tweepy not installed. Skipping.")
        return

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    date_str = data["date"]
    battles = data["battles"]

    lines = [f"🔥 Daily Trend Battles — {date_str}", ""]
    emojis = {"Sports": "⚽", "Tech": "💻", "Economy": "📈"}

    for b in battles:
        emoji = emojis.get(b["category"], "⚔️")
        lines.append(f"{emoji} {b['category']}: {b['option_a']} vs {b['option_b']}")

    lines.extend(["", "Cast your vote 👇", "https://daily-trend-battles.vercel.app"])
    tweet_text = "\n".join(lines)

    try:
        resp = client.create_tweet(text=tweet_text)
        tid = resp.data["id"]
        print(f"[Twitter] Posted: https://x.com/i/status/{tid}")
    except Exception as e:
        print(f"[Twitter] Error: {e}")

if __name__ == "__main__":
    post_battles()