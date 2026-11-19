# Project Blueprint & Complete System Architecture: 1TamilMV Telegram Stealth Notifier

**Owner:** Maady012  
**Telegram Chat ID:** `565062030` (Strictly private; all other user IDs are silently dropped)  
**Bot Username:** `@Maddy_Brain_bot`  
**GitHub Repository:** [github.com/Maady012/tamilmv-bot](https://github.com/Maady012/tamilmv-bot)  
**Local Workspace Path:** `/data/data/com.termux/files/home/tamilmv-bot`  
**Persistent Local Anchor:** `/data/data/com.termux/files/home/.agy_context_1tamilmv.md`  
**Last Updated:** November 19, 2026  

---

## 1. System Architecture & Cloud Infrastructure
- **100% Cloud-Hosted (Zero Local Termux Resource Burden):** Runs autonomously on GitHub Actions Cloud Runner (`ubuntu-latest`) via `.github/workflows/notifier.yml` without burning local phone battery or process limits.
- **Bypassing Anti-Bot & Cloudflare:** Built using `curl_cffi` with Chrome 120 browser TLS fingerprint impersonation (`impersonate="chrome120"`).
- **Candidate Domain Auto-Resolution:** Dynamically cycles through candidate mirrors (`.io`, `.fi`, `.pm`, `.dad`, `.app`, `.biz`, `.yt`, `.wf`), tracks redirects, and uses cached responsive domains.
- **Mirror Health Alerts:** Automatically notifies Telegram Chat `565062030` if all candidate domains become unresponsive.

---

## 2. Scraping & Strict Original Post Logic
- **Comment Bump & Reply Discarder:** 
  1TamilMV's `/discover/` stream mixes new topics with comment replies and thread bumps (`&do=findComment`, `comment=...`). The scraper discards all comment-related items, strictly isolating **genuine original post creations**.
- **GDrive Post Filter:**
  Topics that explicitly state `gdrive` in their title or URL are strictly excluded, as the bot is dedicated exclusively to torrent & TorBox-based releases.
- **Torrent/Magnet Requirement:**
  Only releases containing valid magnet links are broadcast. Posts without magnets are silently dropped to ensure 100% utility for TorBox.
- **Chronological Topic ID Ordering:**
  Each release topic URL contains a unique numeric identifier (`/forums/topic/<topic_id>-<slug>/`).
  - Releases are sorted strictly in descending order of numeric Topic ID (`int(topic_id)`).
  - Pinned legacy threads (Topic ID < 10000, like `183-0`) are ignored.
- **Duplicate Prevention:**
  - Sent topic IDs are persisted in `seen_posts.json` and automatically synchronized/committed back to GitHub.
  - Releases already sent are never re-alerted, preventing repeated notifications.

---

## 3. Telegram Release Card Formatting
- **Card Presentation:** Clean, single-message layout:
  - Poster image preview (`sendPhoto` with HTML fallback).
  - Cleaned movie/series release title.
  - Release specifications (Audio formats, bitrate, resolutions).
  - 1-Tap Copy Magnets using code blocks (`<code>magnet:?xt=...</code>`) to avoid Telegram hyperlink stripping.
  - Interactive Inline Button: **⚡ Add [Quality] to TorBox** for 1-click cloud push.
  - Direct forum link button: `🌐 Open on 1TamilMV`.
- **Torrent File Attachment Policy:**
  - Separate `.torrent` attachment dispatches are intentionally disabled to eliminate unrelated attachment noise.

---

## 4. TorBox Cloud Integration
- **API Endpoint:** `https://api.torbox.app/v1/api/torrents/createtorrent`
- **Authentication:** `TORBOX_API_KEY` stored securely in GitHub Action Secrets.
- **Callback Routing:** Because Telegram `callback_data` has a strict 64-byte limit, buttons use an in-memory button key cache (`CALLBACK_CACHE[btn_key] = magnet_url`). When tapped, the worker pushes the magnet directly to your TorBox subscription and confirms with a Telegram alert popup (`✅ Added to your TorBox Cloud!`).

---

## 5. Telegram Commands
- `/check` or `/scan` — Manually forces an immediate scan of the feed for newly created releases.
- `/latest` — Immediately fetches and previews the newest original release card with 1-tap magnets and TorBox buttons.
- `/status` — Displays active domain mirror, count of tracked IDs, and duplicate guard status.
- `/logs` — Displays the last 12 timestamped event logs in an HTML `<pre>` block for easy in-chat debugging.
- `/ping` — Verifies latency and connectivity.

---

## 6. Secrets & Security Configuration
The following secrets are configured in GitHub Actions (`Settings > Secrets and variables > Actions`):
- `TELEGRAM_BOT_TOKEN`: Token for `@Maddy_Brain_bot`.
- `TELEGRAM_CHAT_ID`: `565062030`.
- `TORBOX_API_KEY`: API key for TorBox cloud torrent adding.
