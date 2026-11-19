import os
import sys
import time
import json
import logging
import re
import html
import urllib.parse
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID", "")).strip()
STATE_FILE = "seen_posts.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

CANDIDATE_DOMAINS = [
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

def get_active_domain():
    global CACHED_DOMAIN, LAST_DOMAIN_CHECK
    now = time.time()
    if CACHED_DOMAIN and (now - LAST_DOMAIN_CHECK < 1800):
        return CACHED_DOMAIN

    for base_url in CANDIDATE_DOMAINS:
        try:
            res = cffi_requests.get(base_url, impersonate="chrome120", timeout=8, headers=HEADERS)
            if res.status_code == 200 and "tamilmv" in res.text.lower():
                CACHED_DOMAIN = res.url.rstrip("/")
                LAST_DOMAIN_CHECK = now
                logging.info(f"Active domain: {CACHED_DOMAIN}")
                return CACHED_DOMAIN
        except Exception:
            continue
    return CACHED_DOMAIN or "https://www.1tamilmv.io"

def load_seen_posts():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                # Filter out old faulty URL strings
                return set(str(x) for x in data if str(x).isdigit())
        except Exception:
            return set()
    return set()

def save_seen_posts(seen_set):
    trimmed = list(str(x) for x in seen_set if str(x).isdigit())[-800:]
    with open(STATE_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)

def clean_topic_url(raw_url, domain):
    """Accurately normalizes 1TamilMV topic URL."""
    if raw_url.startswith("/"):
        raw_url = f"{domain}{raw_url}"
    # Strip URL fragments and anchor tags like #comment
    raw_url = raw_url.split("#")[0]
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

def extract_post_details(topic_url, fallback_title=""):
    try:
        res = cffi_requests.get(topic_url, impersonate="chrome120", timeout=12, headers=HEADERS)
        if res.status_code != 200:
            return {"title": fallback_title or extract_title_from_slug(topic_url), "image": None, "summary": "", "magnet": None}
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 1. Clean Title
        title = ""
        # Find in <title>
        title_tag = soup.find("title")
        if title_tag:
            t = title_tag.get_text(strip=True)
            t = re.sub(r"\s*-\s*1TamilMV.*$", "", t, flags=re.IGNORECASE)
            t = re.sub(r"\s*-\s*Page\s*\d+.*$", "", t, flags=re.IGNORECASE)
            if len(t) > 5 and not t.startswith("["):
                title = t

        # Find in h1
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        # Fallback to URL slug
        slug_t = extract_title_from_slug(topic_url)
        if not title or title.startswith("[") or len(title) < 5:
            if slug_t:
                title = f"{slug_t} {title}".strip()

        if not title:
            title = fallback_title or slug_t or "1TamilMV Release"

        # 2. Content
        post_content = soup.find("div", {"data-role": "commentContent"}) or soup.find("div", class_="cPost_contentWrap")
        image_url, desc_lines, magnet_link = None, [], None

        if post_content:
            for img in post_content.find_all("img"):
                src = img.get("data-src") or img.get("src")
                if src and src.startswith("http") and not any(k in src.lower() for k in ["emoticons", "default_photo", "logo"]):
                    image_url = src
                    break
            
            for a in post_content.find_all("a", href=True):
                if a["href"].startswith("magnet:?"):
                    magnet_link = a["href"]
                    break

            for line in post_content.get_text(separator="\n", strip=True).splitlines():
                line = line.strip()
                if line and 5 < len(line) < 130 and not line.startswith("http") and not line.startswith("magnet:"):
                    desc_lines.append(line)

        return {
            "title": title,
            "image": image_url,
            "summary": "\n".join(desc_lines[:6]),
            "magnet": magnet_link
        }
    except Exception:
        return {"title": fallback_title or extract_title_from_slug(topic_url), "image": None, "summary": "", "magnet": None}

def send_alert(chat_id, title, link, details=None):
    if not BOT_TOKEN or not chat_id:
        return
    d_title = html.escape((details.get("title") if details and details.get("title") else title).strip())
    summary = html.escape(details.get("summary", "") if details else "")
    magnet = details.get("magnet") if details else None
    image_url = details.get("image") if details else None

    caption = f"🎬 <b>{d_title}</b>\n\n"
    if summary:
        caption += f"📋 <i>{summary}</i>\n\n"
    if magnet:
        caption += f"🧲 <a href='{magnet}'><b>Copy Magnet Link</b></a>\n\n"
    caption += f"🔗 <a href='{link}'>Open on 1TamilMV</a>"

    if len(caption) > 1000:
        caption = caption[:960] + "...\n\n🔗 <a href='" + link + "'>Open on 1TamilMV</a>"

    if image_url:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                json={"chat_id": chat_id, "photo": image_url, "caption": caption, "parse_mode": "HTML"},
                timeout=10
            )
            if r.status_code == 200:
                return
        except Exception:
            pass

    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": caption, "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10
        )
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
    """Specifically targets /index.php?/discover/ for new release stream items."""
    new_items = []
    discover_url = f"{domain}/index.php?/discover/"
    try:
        r = cffi_requests.get(discover_url, impersonate="chrome120", timeout=15, headers=HEADERS)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Find stream items on discover feed
            stream_items = soup.find_all(["li", "div"], class_=lambda c: c and ("ipsStreamItem" in c or "cStreamItem" in c))
            if not stream_items:
                stream_items = soup.find_all("article")

            # Fallback if specific stream class not found: scan all topic links
            candidate_links = []
            if stream_items:
                for item in stream_items:
                    a = item.find("a", href=lambda h: h and "/topic/" in h)
                    if a:
                        candidate_links.append(a)
            else:
                candidate_links = soup.find_all("a", href=lambda h: h and "/topic/" in h)

            for a in candidate_links:
                href = a.get("href", "")
                m = re.search(r"/topic/(\d+)-", href)
                if m:
                    tid = str(m.group(1))
                    if tid not in seen_posts and tid not in [x[2] for x in new_items]:
                        full_url = clean_topic_url(href, domain)
                        raw_title = a.get_text(strip=True)
                        slug_title = extract_title_from_slug(full_url)
                        title = slug_title if (slug_title and len(slug_title) > len(raw_title)) else raw_title
                        if not title or len(title) < 4:
                            title = slug_title or "1TamilMV Release"
                        new_items.append((title, full_url, tid))
    except Exception as e:
        logging.warning(f"Error scraping discover feed: {e}")

    return new_items

def main_loop(max_duration=19800):  # 5.5 hour cycle per runner
    start_time = time.time()
    seen_posts = load_seen_posts()
    domain = get_active_domain()
    offset = 0
    last_scrape = 0
    scrape_interval = 300

    logging.info(f"Live worker started on {domain}. Already tracking {len(seen_posts)} topics.")

    while time.time() - start_time < max_duration:
        # 1. Real-time command polling
        try:
            upd_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=2"
            if offset:
                upd_url += f"&offset={offset}"
            res = requests.get(upd_url, timeout=5)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for u in updates:
                    offset = u["update_id"] + 1
                    msg = u.get("message", {})
                    text = msg.get("text", "").strip()
                    cid = str(msg.get("chat", {}).get("id", ""))
                    if not text or not cid:
                        continue
                    if ALLOWED_CHAT_ID and cid != ALLOWED_CHAT_ID:
                        continue

                    cmd = text.split()[0].lower()
                    if cmd in ["/check", "/scan"]:
                        send_msg(cid, "🔍 <i>Checking 1TamilMV discover feed for new releases...</i>")
                        domain = get_active_domain()
                        items = scrape_discover_feed(domain, seen_posts)
                        if not items:
                            send_msg(cid, "✅ <b>Up to date!</b> No new releases found since last scan.")
                        else:
                            send_msg(cid, f"🎉 Found <b>{len(items)}</b> new release(s)!")
                            for t, l, tid in reversed(items[:10]):
                                details = extract_post_details(l, fallback_title=t)
                                send_alert(cid, t, l, details)
                                seen_posts.add(tid)
                            save_seen_posts(seen_posts)

                    elif cmd == "/status":
                        send_msg(cid, (
                            f"⚡ <b>1TamilMV Live Notifier</b>\n\n"
                            f"🌐 <b>Active Mirror:</b> {domain}\n"
                            f"🎯 <b>Target Feed:</b> /discover/ stream\n"
                            f"📁 <b>Tracked:</b> {len(seen_posts)} releases saved\n"
                            f"⚡ <b>Response Time:</b> Instant (< 1s)\n"
                            f"🔄 <b>Auto-Scan:</b> Continuous every 5 mins"
                        ))

                    elif cmd == "/ping":
                        send_msg(cid, "🏓 <b>Pong!</b> Active and responsive.")

                    elif cmd == "/latest":
                        send_msg(cid, "🔍 <i>Fetching latest discover post...</i>")
                        try:
                            domain = get_active_domain()
                            items = scrape_discover_feed(domain, set())  # Empty set to get latest
                            if items:
                                t, l, tid = items[0]
                                dt = extract_post_details(l, fallback_title=t)
                                send_alert(cid, t, l, dt)
                            else:
                                send_msg(cid, "⚠️ Could not parse latest topic.")
                        except Exception as e:
                            send_msg(cid, f"⚠️ Error: {e}")

                    elif cmd in ["/start", "/help"]:
                        send_msg(cid, (
                            "🤖 <b>1TamilMV Live Notifier Menu:</b>\n\n"
                            "👉 /check - Scan discover feed now for new releases\n"
                            "👉 /latest - Preview the most recently posted release\n"
                            "👉 /status - Show active mirror & stats\n"
                            "👉 /ping - Test response speed\n"
                            "👉 /help - Show this menu"
                        ))
        except Exception:
            pass

        # 2. Automated background check every 5 minutes
        if time.time() - last_scrape > scrape_interval:
            last_scrape = time.time()
            try:
                domain = get_active_domain()
                new_items = scrape_discover_feed(domain, seen_posts)
                if new_items:
                    logging.info(f"Discover feed found {len(new_items)} new releases")
                    for t, l, tid in reversed(new_items[:10]):
                        details = extract_post_details(l, fallback_title=t)
                        send_alert(ALLOWED_CHAT_ID, t, l, details)
                        seen_posts.add(tid)
                    save_seen_posts(seen_posts)
            except Exception as e:
                logging.warning(f"Auto-scan error: {e}")

        time.sleep(1)

    save_seen_posts(seen_posts)

if __name__ == "__main__":
    main_loop()
