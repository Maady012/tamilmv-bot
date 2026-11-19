import os
import json
import logging
import re
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

STATE_FILE = "seen_posts.json"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = str(os.getenv("TELEGRAM_CHAT_ID", "")).strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def get_active_domain():
    for base_url in CANDIDATE_DOMAINS:
        try:
            logging.info(f"Probing {base_url}...")
            res = cffi_requests.get(base_url, impersonate="chrome120", timeout=12, headers=HEADERS)
            if res.status_code == 200 and "tamilmv" in res.text.lower():
                final_url = res.url.rstrip("/")
                logging.info(f"Active domain identified: {final_url}")
                return final_url
        except Exception as e:
            logging.warning(f"Failed to reach {base_url}: {e}")
            continue
    return None

def load_seen_posts():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return set(str(x) for x in data)
        except Exception:
            return set()
    return set()

def save_seen_posts(seen_set):
    trimmed = list(str(x) for x in seen_set)[-600:]
    with open(STATE_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)

def extract_post_details(topic_url):
    """Extracts poster, clean title, tech specs, and magnet link."""
    try:
        res = cffi_requests.get(topic_url, impersonate="chrome120", timeout=15, headers=HEADERS)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 1. Title
        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        # 2. Content
        post_content = soup.find("div", {"data-role": "commentContent"}) or soup.find("div", class_="cPost_contentWrap")
        
        image_url = None
        description_lines = []
        magnet_link = None
        
        if post_content:
            # Poster image
            for img in post_content.find_all("img"):
                src = img.get("data-src") or img.get("src")
                if src and src.startswith("http") and not any(skip in src.lower() for skip in ["emoticons", "default_photo", "logo"]):
                    image_url = src
                    break
            
            # Magnet link
            for a in post_content.find_all("a", href=True):
                if a["href"].startswith("magnet:?"):
                    magnet_link = a["href"]
                    break

            # Descriptions (skip excessively long forum disclaimer paragraphs)
            text_block = post_content.get_text(separator="\n", strip=True)
            for line in text_block.splitlines():
                line = line.strip()
                if line and 5 < len(line) < 120 and not line.startswith("http"):
                    description_lines.append(line)
        
        desc_summary = "\n".join(description_lines[:6])
        return {
            "title": title,
            "image": image_url,
            "summary": desc_summary,
            "magnet": magnet_link
        }
    except Exception as e:
        logging.warning(f"Failed to extract details for {topic_url}: {e}")
        return None

def send_telegram_alert(chat_id, title, link, details=None):
    if not BOT_TOKEN or not chat_id:
        return

    display_title = (details.get("title") if details and details.get("title") else title).strip()
    image_url = details.get("image") if details else None
    summary = details.get("summary") if details else ""
    magnet = details.get("magnet") if details else None

    caption = f"🎬 <b>{display_title}</b>\n\n"
    if summary:
        caption += f"📋 <i>{summary}</i>\n\n"
    if magnet:
        caption += f"🧲 <a href='{magnet}'><b>Copy Magnet Link</b></a>\n\n"
    caption += f"🔗 <a href='{link}'>Open on 1TamilMV</a>"

    if len(caption) > 1000:
        caption = caption[:980] + "...\n\n🔗 <a href='" + link + "'>Open on 1TamilMV</a>"

    if image_url:
        photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        photo_payload = {
            "chat_id": chat_id,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        try:
            r = requests.post(photo_url, json=photo_payload, timeout=12)
            if r.status_code == 200:
                return
        except Exception:
            pass

    text_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    text_payload = {
        "chat_id": chat_id,
        "text": caption,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(text_url, json=text_payload, timeout=10)
    except Exception as e:
        logging.error(f"Error sending message: {e}")

def send_plain_message(chat_id, text):
    if not BOT_TOKEN or not chat_id:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        logging.error(f"Error sending plain message: {e}")

def scrape_recent_topics(domain, seen_posts):
    """Reliable deduplication by numeric topic ID."""
    targets = [f"{domain}/", f"{domain}/index.php?/discover/"]
    new_topics = []

    for url in targets:
        try:
            res = cffi_requests.get(url, impersonate="chrome120", timeout=15, headers=HEADERS)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/topic/" in href:
                    match = re.search(r"/topic/(\d+)-", href)
                    if match:
                        topic_id = str(match.group(1))
                        clean_url = href.split("?")[0].rstrip("/")
                        title = a.get_text(strip=True)
                        if topic_id not in seen_posts and topic_id not in [t[2] for t in new_topics]:
                            new_topics.append((title or "New Release", clean_url, topic_id))
        except Exception as e:
            logging.warning(f"Error scraping {url}: {e}")
            continue

    return new_topics

def handle_incoming_commands(domain, seen_posts):
    """Processes user commands like /check, /status, /ping, /latest, /help."""
    if not BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return
        updates = res.json().get("result", [])
    except Exception:
        return

    if not updates:
        return

    # Acknowledge updates by setting offset to latest update_id + 1
    last_update_id = updates[-1]["update_id"]
    requests.get(f"{url}?offset={last_update_id + 1}", timeout=5)

    for item in updates:
        msg = item.get("message", {})
        text = msg.get("text", "").strip()
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not text or not chat_id:
            continue

        # Security check: ignore commands from unauthorized users
        if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID:
            continue

        cmd = text.split()[0].lower()

        if cmd in ["/check", "/scan"]:
            send_plain_message(chat_id, "🔍 <i>Checking for new releases...</i>")
            new_topics = scrape_recent_topics(domain, seen_posts)
            if not new_topics:
                send_plain_message(chat_id, "✅ <b>Up to date!</b> No new releases found since last scan.")
            else:
                send_plain_message(chat_id, f"🎉 Found <b>{len(new_topics)}</b> new release(s)!")
                for title, link, topic_id in reversed(new_topics[:10]):
                    details = extract_post_details(link)
                    send_telegram_alert(chat_id, title, link, details)
                    seen_posts.add(topic_id)
                save_seen_posts(seen_posts)

        elif cmd == "/status":
            status_msg = (
                f"📊 <b>Bot Status</b>\n\n"
                f"🌐 <b>Active Mirror:</b> {domain}\n"
                f"📁 <b>Tracked Posts:</b> {len(seen_posts)} releases saved\n"
                f"⏱ <b>Auto Scan Interval:</b> Every 15 minutes\n"
                f"🛡 <b>Deduplication:</b> Active (Strict Topic-ID Matching)"
            )
            send_plain_message(chat_id, status_msg)

        elif cmd == "/ping":
            send_plain_message(chat_id, "🏓 <b>Pong!</b> Bot is fully operational on GitHub Actions.")

        elif cmd == "/latest":
            send_plain_message(chat_id, "🔍 <i>Fetching the most recent post...</i>")
            # Fetch without modifying seen_posts
            targets = [f"{domain}/"]
            for u in targets:
                try:
                    res = cffi_requests.get(u, impersonate="chrome120", timeout=12, headers=HEADERS)
                    soup = BeautifulSoup(res.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if "/topic/" in href and re.search(r"/topic/(\d+)-", href):
                            clean_url = href.split("?")[0].rstrip("/")
                            details = extract_post_details(clean_url)
                            send_telegram_alert(chat_id, a.get_text(strip=True), clean_url, details)
                            break
                    break
                except Exception:
                    pass

        elif cmd in ["/start", "/help"]:
            help_text = (
                "🤖 <b>1TamilMV Notifier Bot Commands:</b>\n\n"
                "👉 /check - Scan right now for new releases (never duplicates old ones)\n"
                "👉 /latest - Preview the most recently posted release\n"
                "👉 /status - Check current active domain mirror and stats\n"
                "👉 /ping - Test if bot and server are responsive\n"
                "👉 /help - Show this command list\n\n"
                "<i>Auto-notifications run automatically in the background every 15 minutes.</i>"
            )
            send_plain_message(chat_id, help_text)

def run():
    domain = get_active_domain()
    if not domain:
        logging.error("Could not find responsive domain.")
        return

    seen_posts = load_seen_posts()
    logging.info(f"Loaded {len(seen_posts)} seen post IDs.")

    # 1. Process any pending manual commands sent to the bot
    handle_incoming_commands(domain, seen_posts)

    # 2. Perform automated scheduled release check
    new_topics = scrape_recent_topics(domain, seen_posts)
    logging.info(f"Found {len(new_topics)} new release(s) during scheduled check.")

    for title, link, topic_id in reversed(new_topics[:10]):
        details = extract_post_details(link)
        send_telegram_alert(ALLOWED_CHAT_ID, title, link, details)
        seen_posts.add(topic_id)

    save_seen_posts(seen_posts)

if __name__ == "__main__":
    run()
