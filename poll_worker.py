import os
import sys
import time
import json
import logging
import random
import re
import html
import urllib.parse
from datetime import datetime, timezone, timedelta
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID", "565062030")).strip()
TORBOX_API_KEY = os.getenv("TORBOX_API_KEY", "").strip()
STATE_FILE = "seen_posts.json"
DEBUG_LOG_FILE = "bot_activity.log"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

CANDIDATE_DOMAINS = [
    "https://www.1tamilmv.ceo",
    "https://www.1tamilmv.io",
    "https://www.1tamilmv.fi",
    "https://www.1tamilmv.pm",
    "https://www.1tamilmv.dad",
    "https://www.1tamilmv.app",
    "https://www.1tamilmv.biz",
    "https://www.1tamilmv.yt",
    "https://www.1tamilmv.wf",
]

CACHED_DOMAIN = None
LAST_DOMAIN_CHECK = 0
CALLBACK_CACHE = {}  # In-memory map for inline buttons: button_id -> magnet_url

IST = timezone(timedelta(hours=5, minutes=30))

def get_now_ist_str():
    return datetime.now(IST).strftime("%Y-%m-%d %I:%M:%S %p IST")

def log_event(event_type, details):
    line = f"[{get_now_ist_str()}] [{event_type}] {details}\n"
    try:
        with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    logging.info(f"[{event_type}] {details}")

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }

def get_active_domain():
    global CACHED_DOMAIN, LAST_DOMAIN_CHECK
    now = time.time()
    if CACHED_DOMAIN and (now - LAST_DOMAIN_CHECK < 1800):
        return CACHED_DOMAIN

    for base_url in CANDIDATE_DOMAINS:
        try:
            res = cffi_requests.get(base_url, impersonate="chrome120", timeout=8, headers=get_headers())
            if res.status_code == 200 and "tamilmv" in res.text.lower():
                CACHED_DOMAIN = res.url.rstrip("/")
                LAST_DOMAIN_CHECK = now
                log_event("DOMAIN", f"Active mirror resolved: {CACHED_DOMAIN}")
                return CACHED_DOMAIN
        except Exception:
            continue
            
    # Auto-Health Notification if all mirrors fail
    log_event("HEALTH_ALERT", "All candidate mirrors failed responsiveness check")
    send_msg(ALLOWED_CHAT_ID, "⚠️ <b>Health Alert:</b> All candidate mirrors are currently unreachable. Waiting for active domain redirect...")
    return CACHED_DOMAIN or "https://www.1tamilmv.io"

def load_seen_posts():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return set(str(x) for x in data if str(x).isdigit())
        except Exception:
            return set()
    return set()

def save_seen_posts(seen_set):
    trimmed = list(str(x) for x in seen_set if str(x).isdigit())[-1000:]
    with open(STATE_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)

def clean_topic_url(raw_url, domain):
    if raw_url.startswith("/"):
        raw_url = f"{domain}{raw_url}"
    else:
        raw_url = re.sub(r"https?://(?:www\.)?1tamilmv\.[a-z]+", domain, raw_url)
    raw_url = raw_url.split("&do=findComment")[0].split("#")[0]
    return raw_url

def extract_title_from_slug(url):
    match = re.search(r"/topic/\d+-([^/?#&]+)", url)
    if match:
        raw = match.group(1)
        decoded = urllib.parse.unquote(raw)
        clean = decoded.replace("-", " ").strip()
        if clean:
            return clean
    return ""

def clean_magnet_label(label, fallback="Option"):
    if not label:
        return fallback
    clean = re.sub(r"(?i)www\.1tamilmv\.\w+\s*-\s*", "", label)
    m = re.search(r"(\b(?:4K|2160p|1080p|720p|HDRip|BluRay|HEVC|AVC|x264|x265)\b.*)", clean, re.IGNORECASE)
    if m:
        short = m.group(1).strip(" -_")
        return short[:30] if len(short) > 3 else clean[:30]
    return clean[:30] if clean else fallback

def extract_post_details(topic_url, fallback_title=""):
    try:
        pass
        domain = get_active_domain()
        clean_url = clean_topic_url(topic_url, domain)
        res = cffi_requests.get(clean_url, impersonate="chrome120", timeout=12, headers=get_headers())
        if res.status_code != 200:
            return None
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 1. Title Extraction
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            t = title_tag.get_text(strip=True)
            if "not find that" in t.lower() or "error" in t.lower():
                return None
            t = re.sub(r"\s*-\s*1TamilMV.*$", "", t, flags=re.IGNORECASE)
            t = re.sub(r"\s*-\s*Page\s*\d+.*$", "", t, flags=re.IGNORECASE)
            if len(t) > 5 and not t.startswith("["):
                title = t

        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        slug_t = extract_title_from_slug(clean_url)
        if not title or title.startswith("[") or len(title) < 5:
            if slug_t:
                title = f"{slug_t} {title}".strip()

        if not title:
            title = fallback_title or slug_t or "1TamilMV Release"

        # Explicit GDrive exclusion
        if "gdrive" in f"{title} {clean_url}".lower():
            return None

        # 2. Content & Magnets
        post_content = soup.find("div", {"data-role": "commentContent"}) or soup.find("div", class_="cPost_contentWrap")
        image_url, desc_lines = None, []
        magnets = []

        if post_content:
            for img in post_content.find_all("img"):
                src = img.get("data-src") or img.get("src")
                if src and src.startswith("http") and not any(k in src.lower() for k in ["emoticons", "default_photo", "logo"]):
                    image_url = src
                    break
            
            seen_hashes = set()
            for a in post_content.find_all("a", href=True):
                href = a["href"].strip()
                # Magnet Link
                if href.startswith("magnet:?"):
                    hash_match = re.search(r"urn:btih:([a-zA-Z0-9]+)", href)
                    bt_hash = hash_match.group(1).lower() if hash_match else href
                    if bt_hash not in seen_hashes:
                        seen_hashes.add(bt_hash)
                        raw_label = a.get_text(strip=True)
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        dn = parsed.get("dn", [""])[0]
                        label = clean_magnet_label(dn or raw_label, f"Option {len(magnets)+1}")
                        magnets.append({"url": href, "label": label})

            for line in post_content.get_text(separator="\n", strip=True).splitlines():
                line = line.strip()
                if line and 5 < len(line) < 130 and not line.startswith("http") and not line.startswith("magnet:"):
                    if not any(skip in line.lower() for skip in ["telegram channel", "click here", "audio credits", "official channel"]):
                        desc_lines.append(line)

        return {
            "title": title,
            "image": image_url,
            "summary": "\n".join(desc_lines[:3]),
            "magnets": magnets
        }
    except Exception as e:
        log_event("EXTRACT_ERR", f"Error on {topic_url}: {e}")
        return None

def add_to_torbox(magnet_url):
    """Adds a magnet directly to your TorBox cloud."""
    if not TORBOX_API_KEY:
        return False, "TorBox API Key is not configured."
    url = "https://api.torbox.app/v1/api/torrents/createtorrent"
    headers = {"Authorization": f"Bearer {TORBOX_API_KEY}"}
    data = {"magnet": magnet_url, "seed": 1}
    try:
        r = requests.post(url, headers=headers, data=data, timeout=12)
        res = r.json()
        if res.get("success"):
            return True, res.get("detail", "Torrent queued on your TorBox Cloud!")
        return False, res.get("detail", "TorBox API error.")
    except Exception as e:
        return False, str(e)

def send_alert(chat_id, title, link, details=None):
    if not BOT_TOKEN or not chat_id:
        return
    d_title = html.escape((details.get("title") if details and details.get("title") else title).strip())
    summary = html.escape(details.get("summary", "") if details else "")
    magnets = details.get("magnets", []) if details else []
    image_url = details.get("image") if details else None
    clean_url = clean_topic_url(link, get_active_domain())

    caption = "━━━━━━━━━━━━━━━━━━━━━━\n"
    caption += f"🎬 <b>{d_title}</b>\n"
    caption += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    if summary:
        caption += f"📋 <b>Release Info:</b>\n<i>{summary}</i>\n\n"

    # Build Interactive Buttons for Torbox Cloud Push
    inline_keyboard = []
    if magnets:
        caption += "🧲 <b>Magnets (Tap to Copy):</b>\n"
        for idx, m in enumerate(magnets[:3], 1):
            safe_label = html.escape(m["label"])
            caption += f"🔹 <b>{safe_label}:</b> <code>{m['url']}</code>\n"
            # Cache button callback data (Telegram callback_data max 64 bytes)
            btn_key = f"tb_{int(time.time())}_{idx}_{random.randint(100, 999)}"
            CALLBACK_CACHE[btn_key] = m["url"]
            inline_keyboard.append([{"text": f"⚡ Add {safe_label[:20]} to TorBox", "callback_data": btn_key}])
        caption += "\n"
    else:
        caption += "🧲 <b>Magnets:</b> <i>No magnet link available for this post</i>\n\n"

    inline_keyboard.append([{"text": "🌐 Open on 1TamilMV", "url": clean_url}])
    reply_markup = {"inline_keyboard": inline_keyboard}

    if len(caption) > 1000:
        caption = caption[:940] + "...\n\n🌐 <a href='" + clean_url + "'><b>[View on 1TamilMV]</b></a>"

    photo_sent = False
    if image_url:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                json={"chat_id": chat_id, "photo": image_url, "caption": caption, "parse_mode": "HTML", "reply_markup": reply_markup},
                timeout=10
            )
            if r.status_code == 200:
                photo_sent = True
                log_event("NOTIFY", f"Photo alert sent: {d_title[:60]}")
        except Exception:
            pass

    if not photo_sent:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": caption, "parse_mode": "HTML", "disable_web_page_preview": True, "reply_markup": reply_markup},
                timeout=10
            )
            log_event("NOTIFY", f"Text alert sent: {d_title[:60]}")
        except Exception:
            pass

def send_msg(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception:
        pass

def scrape_discover_feed(domain, seen_posts):
    discovered_topics = {}
    discover_url = f"{domain}/index.php?/discover/"
    try:
        r = cffi_requests.get(discover_url, impersonate="chrome120", timeout=15, headers=get_headers())
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            stream = soup.find("ol", class_="ipsStream") or soup
            for li in stream.find_all("li", class_="ipsStreamItem"):
                title_el = li.find("h2", class_="ipsStreamItem_title") or li.find("a", href=re.compile(r"/topic/"))
                if not title_el:
                    continue
                a_tag = title_el.find("a") if title_el.name != "a" else title_el
                if not a_tag or not a_tag.get("href"):
                    continue
                
                href = a_tag["href"].strip()
                # Clean comment params to get base topic
                href = href.split("&do=findComment")[0].split("#")[0]

                m = re.search(r"/topic/(\d+)-", href)
                if not m:
                    continue
                tid_int = int(m.group(1))
                if tid_int < 10000:
                    continue
                tid = str(tid_int)
                if tid in seen_posts:
                    continue

                if tid not in discovered_topics:
                    clean_url = clean_topic_url(href, domain)
                    raw_title = a_tag.get_text(strip=True)
                    slug_title = extract_title_from_slug(clean_url)
                    title = slug_title if (slug_title and len(slug_title) > len(raw_title)) else raw_title
                    if not title or len(title) < 4:
                        title = slug_title or "1TamilMV Release"

                    # Exclude topics that explicitly say 'gdrive' in title or url
                    combined_check = f"{title} {clean_url}".lower()
                    if "gdrive" in combined_check:
                        continue

                    discovered_topics[tid] = (title, clean_url, tid)
    except Exception as e:
        log_event("ERROR", f"Discover feed error: {e}")

    # Descending numeric Topic ID ensures newest releases first
    return sorted(discovered_topics.values(), key=lambda x: int(x[2]), reverse=True)

def main_loop(max_duration=19800):
    start_time = time.time()
    seen_posts = load_seen_posts()
    domain = get_active_domain()
    offset = 0
    last_scrape = 0
    scrape_interval = random.randint(300, 420)

    log_event("START", f"Production worker initialized on {domain}. Tracked: {len(seen_posts)}")

    while time.time() - start_time < max_duration:
        try:
            upd_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=2"
            if offset:
                upd_url += f"&offset={offset}"
            res = requests.get(upd_url, timeout=10)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for u in updates:
                    offset = u["update_id"] + 1
                    
                    # 1. Handle Callback Query from Inline Buttons ("Add to TorBox")
                    callback = u.get("callback_query")
                    if callback:
                        cb_id = callback.get("id")
                        cb_data = callback.get("data")
                        cb_user = str(callback.get("from", {}).get("id"))
                        
                        if cb_user == ALLOWED_CHAT_ID and cb_data in CALLBACK_CACHE:
                            magnet_to_send = CALLBACK_CACHE[cb_data]
                            success, msg = add_to_torbox(magnet_to_send)
                            ans_text = "✅ Added to your TorBox Cloud!" if success else f"⚠️ {msg}"
                            requests.post(
                                f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                                json={"callback_query_id": cb_id, "text": ans_text, "show_alert": True},
                                timeout=5
                            )
                            log_event("TORBOX", f"Button tapped: {ans_text}")
                        continue

                    # 2. Handle Text Commands
                    msg = u.get("message", {})
                    text = msg.get("text", "").strip()
                    cid = str(msg.get("chat", {}).get("id", ""))
                    
                    if not text or not cid:
                        continue

                    if cid != ALLOWED_CHAT_ID:
                        log_event("SECURITY", f"Dropped message from {cid}")
                        continue

                    raw_cmd = text.split()[0].lower()
                    cmd = raw_cmd.split("@")[0]
                    log_event("COMMAND", f"Processing '{cmd}' from {cid}")

                    if cmd in ["/check", "/scan"]:
                        send_msg(cid, "🔍 <i>Checking for newly created releases...</i>")
                        domain = get_active_domain()
                        items = scrape_discover_feed(domain, seen_posts)
                        if not items:
                            send_msg(cid, "✅ <b>Up to date!</b> No new releases found since last scan.")
                        else:
                            new_alerts = 0
                            for t, l, tid in reversed(items[:8]):
                                details = extract_post_details(l, fallback_title=t)
                                if details and details.get("magnets"):
                                    send_alert(cid, t, l, details)
                                    seen_posts.add(tid)
                                    new_alerts += 1
                                else:
                                    log_event("WAIT_MAGNET", f"Topic {tid} has no magnet yet. Kept pending.")
                            if new_alerts > 0:
                                save_seen_posts(seen_posts)
                            else:
                                send_msg(cid, "ℹ️ New posts found, but awaiting magnet link upload by uploader.")

                    elif cmd == "/status":
                        send_msg(cid, (
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "🛡 <b>1TamilMV Live Status</b>\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"👤 <b>Access:</b> Locked to ID <code>{ALLOWED_CHAT_ID}</code>\n"
                            f"🌐 <b>Active Mirror:</b> {domain}\n"
                            f"📁 <b>Tracked Topics:</b> <b>{len(seen_posts)}</b> releases\n"
                            f"⚡ <b>TorBox Integration:</b> Active (Instant Cloud Push)\n"
                            f"🛡 <b>Duplicate Guard:</b> Strict Topic ID Filtering\n"
                            f"🕒 <b>Server Time:</b> <i>{get_now_ist_str()}</i>\n"
                            f"⚡ <b>Latency:</b> Instant (< 1s)"
                        ))

                    elif cmd == "/ping":
                        send_msg(cid, f"🏓 <b>Pong!</b> Responsive as of <i>{get_now_ist_str()}</i>.")

                    elif cmd == "/latest":
                        send_msg(cid, "🔍 <i>Fetching the newest torrent release on 1TamilMV...</i>")
                        try:
                            domain = get_active_domain()
                            all_topics = scrape_discover_feed(domain, set())
                            if not all_topics:
                                send_msg(cid, "⚠️ Could not parse feed at this moment.")
                            else:
                                dispatched = False
                                for t_title, t_link, t_tid in all_topics:
                                    dt = extract_post_details(t_link, fallback_title=t_title)
                                    if dt and dt.get("magnets"):
                                        send_alert(cid, t_title, t_link, dt)
                                        seen_posts.add(t_tid)
                                        save_seen_posts(seen_posts)
                                        log_event("LATEST", f"Dispatched release {t_tid}: {t_title[:50]}")
                                        dispatched = True
                                        break
                                if not dispatched:
                                    send_msg(cid, "ℹ️ No recent torrent-based releases found right now.")
                        except Exception as e:
                            send_msg(cid, f"⚠️ Error: {e}")

                    elif cmd == "/logs":
                        try:
                            if os.path.exists(DEBUG_LOG_FILE):
                                with open(DEBUG_LOG_FILE, "r", encoding="utf-8") as f:
                                    recent = f.readlines()[-12:]
                                log_text = (
                                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                                    "📜 <b>Recent Bot Event Logs</b>\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                    "<pre>" + html.escape("".join(recent)) + "</pre>"
                                )
                                send_msg(cid, log_text)
                            else:
                                send_msg(cid, "ℹ️ No event logs recorded yet.")
                        except Exception as e:
                            send_msg(cid, f"⚠️ Error reading logs: {e}")

                    elif cmd in ["/start", "/help"]:
                        send_msg(cid, (
                            "━━━━━━━━━━━━━━━━━━━━━━\n"
                            "🤖 <b>1TamilMV Notifier Commands</b>\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            "👉 <b>/check</b> - Scan for new releases now\n"
                            "👉 <b>/latest</b> - Preview the newest release\n"
                            "👉 <b>/status</b> - System health & TorBox status\n"
                            "👉 <b>/logs</b> - View recent event logs\n"
                            "👉 <b>/ping</b> - Test response speed"
                        ))
        except Exception:
            pass

        if time.time() - last_scrape > scrape_interval:
            last_scrape = time.time()
            scrape_interval = random.randint(300, 420)
            try:
                domain = get_active_domain()
                new_items = scrape_discover_feed(domain, seen_posts)
                if new_items:
                    log_event("AUTOSCAN", f"Found {len(new_items)} new releases automatically.")
                    new_alerts = 0
                    for t, l, tid in reversed(new_items[:8]):
                        details = extract_post_details(l, fallback_title=t)
                        if details and details.get("magnets"):
                            send_alert(ALLOWED_CHAT_ID, t, l, details)
                            seen_posts.add(tid)
                            new_alerts += 1
                        else:
                            log_event("WAIT_MAGNET", f"Topic {tid} has no magnet yet. Kept pending.")
                    if new_alerts > 0:
                        save_seen_posts(seen_posts)
            except Exception as e:
                log_event("ERROR", f"Auto-scan exception: {e}")

        time.sleep(1)

    save_seen_posts(seen_posts)
    log_event("CYCLE", "Worker cycle completed cleanly.")

if __name__ == "__main__":
    main_loop()
