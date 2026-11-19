import os
import json
import logging
import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Candidate domain patterns to probe
CANDIDATE_DOMAINS = [
    "https://www.1tamilmv.pm",
    "https://www.1tamilmv.fi",
    "https://www.1tamilmv.dad",
    "https://www.1tamilmv.app",
    "https://www.1tamilmv.biz",
    "https://www.1tamilmv.yt",
    "https://www.1tamilmv.wf",
]

STATE_FILE = "seen_posts.json"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_active_domain():
    """Finds the current working domain by probing candidates."""
    for base_url in CANDIDATE_DOMAINS:
        try:
            logging.info(f"Probing {base_url}...")
            res = cffi_requests.get(
                base_url,
                impersonate="chrome120",
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
            )
            # Check if valid forum page returned
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
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_posts(seen_set):
    # Keep only the last 500 post IDs to avoid file bloat
    trimmed = list(seen_set)[-500:]
    with open(STATE_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)

def send_telegram_alert(title, link):
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    text = f"🎬 *New 1TamilMV Release*\n\n📌 *{title}*\n\n🔗 [Open Post]({link})"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            logging.error(f"Telegram API error: {r.text}")
    except Exception as e:
        logging.error(f"Error sending alert: {e}")

def run():
    domain = get_active_domain()
    if not domain:
        logging.error("Could not find any responsive domain.")
        return

    seen_posts = load_seen_posts()
    logging.info(f"Tracking {len(seen_posts)} existing post IDs.")

    # Fetch recent topics
    target_url = f"{domain}/index.php?/discover/"
    try:
        response = cffi_requests.get(
            target_url,
            impersonate="chrome120",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
        )
    except Exception as e:
        logging.error(f"Failed to fetch content from {target_url}: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", href=True)
    new_found = []

    for a in links:
        href = a["href"]
        if "/index.php?/forums/topic/" in href:
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            clean_url = href.split("?")[0]
            if clean_url not in seen_posts:
                new_found.append((title, clean_url))
                seen_posts.add(clean_url)

    logging.info(f"Found {len(new_found)} new posts.")
    for title, link in reversed(new_found):  # Send oldest first
        send_telegram_alert(title, link)

    save_seen_posts(seen_posts)

if __name__ == "__main__":
    run()
