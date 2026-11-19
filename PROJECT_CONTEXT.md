# Project Blueprint & Complete System Architecture: 1TamilMV Telegram Stealth Notifier

**Owner:** Maady012  
**Telegram Chat ID:** `565062030` (Strictly private; all other user IDs are silently dropped)  
**Bot Username:** `@Maddy_Brain_bot`  
**GitHub Repository:** [github.com/Maady012/tamilmv-bot](https://github.com/Maady012/tamilmv-bot) (Public; unlimited free GitHub Actions runner minutes 24/7)  
**Local Workspace Path:** `/data/data/com.termux/files/home/tamilmv-bot`  
**Persistent Local Anchor:** `/data/data/com.termux/files/home/.agy_context_1tamilmv.md`  
**Changelog & Fixes Documentation:** `/data/data/com.termux/files/home/tamilmv-bot/CHANGELOG_FIXES.md`  
**Last Updated:** November 19, 2026  

---

## 1. System Architecture & Cloud Infrastructure
- **100% Cloud-Hosted (Zero Local Termux Resource Burden):** Runs autonomously on GitHub Actions Cloud Runner (`ubuntu-latest`) via `.github/workflows/notifier.yml`.
- **Public Repo & Unlimited 24/7 Polling:** 
  Migrated to **Public** repository to unlock **100% free, unlimited GitHub Actions runner minutes 24/7**. Runs continuous long polling and fast background feed scraping (every 45–60 seconds).
- **Anti-Bot & Cloudflare Bypass:** Built using `curl_cffi` with Chrome 120 browser TLS fingerprint impersonation (`impersonate="chrome120"`).
- **Candidate Domain Auto-Resolution:** Dynamically cycles through candidate mirrors (`.ceo`, `.io`, `.fi`, `.pm`, `.dad`, `.app`, `.biz`, `.yt`, `.wf`), tracks redirects, and uses cached responsive domains.
- **Mirror Health Alerts:** Automatically notifies Telegram Chat `565062030` if candidate domains become unresponsive.

---

## 2. Scraping & Strict Filtering Logic
- **Comment Bump & Reply Discarder:** 
  1TamilMV's `/discover/` stream mixes new topics with comment replies and thread bumps (`&do=findComment`, `comment=...`). The scraper strips comment parameters to obtain canonical topic URLs, and enforces topic ID thresholds (`>= 10000`) to strictly isolate **genuine original post creations**.
- **GDrive & DDL-Only Post Filter:**
  Topics that explicitly state `gdrive` in their title or URL, or posts containing 0 magnets and only external download links (Mega, MediaFire, Terabox, PixelDrain, Byseraguci), are flagged as `is_ddl = True`, permanently added to `seen_posts.json`, and discarded so they are never polled again.
- **Delayed Magnet Handling:**
  Only releases containing valid magnet links are broadcast. If an uploader creates a new thread before uploading the magnet, the topic ID is kept pending until uploaders add magnets, after which the card is dispatched.
- **Duplicate Prevention & Instant Persistence:**
  - Sent topic IDs are saved into `seen_posts.json` and immediately committed/pushed to GitHub so runner restarts never re-alert duplicate releases.
  - Blind over-seeding ranges have been purged.

---

## 3. Telegram Release Card Formatting & Poster Handling
- **Card Presentation:** Clean, single-message layout:
  - Poster image preview. If external image hosts block Telegram's IP (`failed to get HTTP URL content`), the bot downloads the image directly using Chrome impersonation and uploads it via `multipart/form-data`.
  - Cleaned movie/series release title.
  - Release specifications (Audio formats, bitrate, resolutions).
  - Interactive Action Buttons:
    - **`[🧲 Copy <Resolution>]`** — Tapping drops the pure, formatted magnet code block into chat for 1-tap copy without cluttering the main poster card.
    - **`[⚡ TorBox]`** — 1-click instant cloud torrent queueing.
    - **`[🌐 Open on 1TamilMV]`** — Direct web link to the forum release.
  - Slicing safeguards: Zero destructive slicing; complete release cards render without tag breakage.

---

## 4. TorBox Cloud Integration
- **API Endpoint:** `https://api.torbox.app/v1/api/torrents/createtorrent`
- **Authentication:** Active API token (`0e4230fc-d5dc-4cc5-8aae-4c03bba5b48c`), encrypted using libsodium and stored securely in GitHub Action Secrets (`TORBOX_API_KEY`). Account: `madhanskumar.hr@gmail.com`.
- **Callback Routing:** Because Telegram `callback_data` has a 64-byte limit, buttons use `CALLBACK_CACHE[btn_key] = ("torbox", magnet_url, label)`. When tapped, the worker pushes the magnet directly to TorBox and confirms with a Telegram toast (`✅ Added to your TorBox Cloud!`).

---

## 5. Telegram Commands
- `/check` or `/scan` — Manually forces an immediate scan of the feed for newly created releases.
- `/latest` — Previews the newest original torrent release with 1-tap magnets and TorBox buttons (respects duplicate filter).
- `/status` — Displays active domain mirror, count of tracked IDs, and TorBox status.
- `/logs` — Displays the last 12 timestamped event logs in an HTML `<pre>` block for easy in-chat debugging.
- `/ping` — Verifies latency and connectivity.

---

## 6. Secrets & Security Configuration
The following secrets are configured in GitHub Actions (`Settings > Secrets and variables > Actions`):
- `TELEGRAM_BOT_TOKEN`: Token for `@Maddy_Brain_bot`.
- `TELEGRAM_CHAT_ID`: `565062030`.
- `TORBOX_API_KEY`: API token for TorBox cloud torrent adding (`0e4230fc-d5dc-4cc5-8aae-4c03bba5b48c`).
