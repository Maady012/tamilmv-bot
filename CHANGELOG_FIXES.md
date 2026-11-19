# 1TamilMV Bot - Complete Architecture & Fixes Changelog

**Repository:** [github.com/Maady012/tamilmv-bot](https://github.com/Maady012/tamilmv-bot) (Public, 24/7 Cloud Polling)  
**Telegram Bot:** `@Maddy_Brain_bot`  
**Gated Chat ID:** `565062030`  
**Last Updated:** November 19, 2026

---

## 1. Executive Summary
The bot is a fully autonomous, cloud-hosted Telegram notifier monitoring 1TamilMV for newly uploaded torrent releases. It excludes non-torrent posts, discards comment bumps on older movies, extracts clean titles, posters, and magnet links, provides 1-tap magnet copying, and integrates 1-click cloud push to **TorBox**.

---

## 2. Issues Diagnosed & Resolved

### A. Telegram Message Parsing & Poster Slicing Fixes
1. **Unescaped HTML in `/status` Template**:
   - Fixed raw `<` in `Latency: Instant (< 1s)` causing `HTTP 400 Bad Request: can't parse entities: Unsupported start tag`.
   - Replaced with `&lt;` and added plain-text fallback mechanism to `send_msg`.
2. **Broken `<code>` Magnet Tag Truncation**:
   - Fixed `caption[:940]` slicing across magnet links and cutting off `</code>`.
   - Removed arbitrary slice so complete release cards render without tag breakage.
3. **Poster Hotlink Failure (`failed to get HTTP URL content`)**:
   - When external image hosts block Telegram's IP, the bot uses `curl_cffi` (Chrome impersonation) to download the image directly and upload it via `multipart/form-data`.

---

### B. Torrent vs. Non-Torrent / DDL Filtering
1. **Direct Download Link (DDL) Exclusion**:
   - Posts with **0 magnets** that contain external links (Mega, MediaFire, Terabox, PixelDrain, Byseraguci, GDrive) are marked `is_ddl = True` and permanently discarded into `seen_posts`.
2. **Comment Bump & Archive Topic Blocking**:
   - Discards comment bumps by stripping `&do=findComment` and filtering out old archive topics (e.g. *The Odyssey* topic `118763`).

---

### C. State Persistence & Restart Isolation
1. **Blind Range Over-Seeding Fixed**:
   - Purged the range `201130..201165` that accidentally blocked *Anbil Avan* before it was alerted.
2. **Immediate Git State Persistence**:
   - `save_seen_posts` immediately stages and commits state so that runner restarts never re-alert duplicate releases.
3. **Variable Scope Ordering**:
   - Fixed `UnboundLocalError` on `scrape_interval` so the runner starts smoothly on boot.

---

### D. Interactive UI & TorBox Integration
1. **Compact Poster Card with 1-Tap Copy Buttons**:
   - `[🧲 Copy 1080p]` - Sends the pure copyable magnet string directly into chat.
   - `[⚡ TorBox]` - Queues the torrent directly to your TorBox cloud.
   - `[🌐 Open on 1TamilMV]` - Direct web link to the forum release.
2. **TorBox API Key Update**:
   - Configured active API token (`0e4230fc-d5dc-4cc5-8aae-4c03bba5b48c`), encrypted it with libsodium, and stored it in GitHub Encrypted Secrets (`TORBOX_API_KEY`).

---

### E. 24/7 Cloud Runtime & Zero Quota Constraints
1. **Public Repository Migration**:
   - Hosted publicly on GitHub for **unlimited free GitHub Actions runner minutes 24/7**.
   - No bot tokens or secrets are exposed in the repository; access control is hardcoded to chat ID `565062030`.
2. **Fast 45–60 Second Scanning & Silent Heartbeats**:
   - Scans every 45–60 seconds and alerts within a minute of new uploads.
   - Chat notifications for empty scans removed; heartbeats are written to internal engine logs only (`/logs`).
