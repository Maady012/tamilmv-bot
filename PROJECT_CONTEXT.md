# Project Blueprint: 1TamilMV Telegram Stealth Notifier

**Owner:** Maady012  
**Telegram Chat ID:** 565062030  
**Bot Username:** @Maddy_Brain_bot  
**GitHub Repository:** [github.com/Maady012/tamilmv-bot](https://github.com/Maady012/tamilmv-bot)  
**Local Workspace Path:** `/data/data/com.termux/files/home/tamilmv-bot`  

---

## 1. System Architecture
- **Hosting Engine:** GitHub Actions Cloud Runner (`ubuntu-latest`) running 24/7 continuous cycles.
- **Scraping Engine:** `curl_cffi` using Chrome 120 browser TLS fingerprint impersonation to bypass Cloudflare.
- **Target Feed:** `https://www.1tamilmv.io/index.php?/discover/` (Live stream items).
- **Domain Resolver:** Automatic probing across candidate mirrors (`.io`, `.fi`, `.pm`, `.dad`, `.app`, `.biz`, `.yt`, `.wf`) with automatic redirect following.
- **Deduplication Engine:** Numeric Forum Topic IDs (`topic/<id>-<slug>`) stored and updated in `seen_posts.json`. Prevents duplicate alerts even across mirror flips.

---

## 2. Interactive Telegram Commands
- `/check` or `/scan` — Scans the discover stream immediately for new releases.
- `/latest` — Previews the latest post; includes smart caching so identical previews aren't repeatedly spammed.
- `/status` — Displays active domain mirror, count of tracked IDs, and system health.
- `/logs` — Displays the last 12 timestamped event logs for in-chat debugging.
- `/ping` — Verifies latency and connectivity.

---

## 3. Security & Stealth Hardening
- **Strict Single-User Access:** Hardcoded filter for Chat ID `565062030`. Any message from other users is silently dropped.
- **Anti-Blocking Jitter:** Dynamic randomized delays (5–7 minutes) and humanized pauses (1.0s–2.5s) between requests.
- **Secrets Management:** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` stored securely in GitHub Action Secrets.

---

## 4. Key Files in Repository
- `poll_worker.py`: Main continuous polling worker script with real-time command processing and discover feed scraping.
- `.github/workflows/notifier.yml`: GitHub Actions automated workflow for continuous cloud execution.
- `requirements.txt`: Python dependencies (`curl_cffi`, `beautifulsoup4`, `requests`).
- `seen_posts.json`: Persistent history of dispatched topic IDs.
- `bot_activity.log`: Timestamped activity and debug event log.
