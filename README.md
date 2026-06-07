# 🌍 Automated Dynamic Trend Battles Platform

An automated JAMstack platform that fetches real-time global search trends daily, orchestrates competitive A vs B viral matchups, and enables live public voting.

## 🛠️ System Architecture

* **Backend:** Python script (`main.py`) powered by `pytrends` with built-in exponential back-off and 4-tier pairing priority logic.
* **Automation:** Managed completely via GitHub Actions workflows executing daily at 00:00 UTC.
* **Frontend:** Responsive, high-performance static SPA layout optimized for mobile ad-clicks.
* **Data Layer:** Event-driven real-time synchronized vote tracking utilizing Firebase Realtime Database.

## 🚀 Live Updates
The data orchestration pipeline automatically rewrites `data.json` every 24 hours, triggering decentralized builds to keep content fresh without manual intervention.


yes