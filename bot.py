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
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_posts(seen_set):
    trimmed = list(seen_set)[-500:]
    with open(STATE_FILE, "w") as f:
        json.dump(trimmed, f, indent=2)

def extract_post_details(topic_url):
    """Fetches full post page and extracts title, poster image, and text content."""
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

        # 2. First post content
        post_content = soup.find("div", {"data-role": "commentContent"}) or soup.find("div", class_="cPost_contentWrap")
        
        image_url = None
        description_lines = []
        magnet_link = None
        
        if post_content:
            # Extract poster image
            img = post_content.find("img")
            if img:
                image_url = img.get("data-src") or img.get("src")
                if image_url and not image_url.startswith("http"):
                    image_url = None
            
            # Extract magnet link if present
            for a in post_content.find_all("a", href=True):
                if a["href"].startswith("magnet:?"):
                    magnet_link = a["href"]
                    break

            # Extract clean text snippets (movie info, audio specs, size)
            text_block = post_content.get_text(separator="\n", strip=True)
            for line in text_block.splitlines():
                line = line.strip()
                if line and len(line) < 150:
                    description_lines.append(line)
        
        desc_summary = "\n".join(description_lines[:8])  # First 8 informative lines
        return {
            "title": title,
            "image": image_url,
            "summary": desc_summary,
            "magnet": magnet_link
        }
    except Exception as e:
        logging.warning(f"Failed to extract details for {topic_url}: {e}")
        return None

def send_telegram_alert(title, link, details=None):
    if not BOT_TOKEN or not CHAT_ID:
        logging.error("Missing credentials")
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

    # Truncate to Telegram 1024-character caption limit if image is attached
    if len(caption) > 1000:
        caption = caption[:990] + "...\n\n🔗 <a href='" + link + "'>Open on 1TamilMV</a>"

    # Send with Photo if image exists
    if image_url:
        photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        photo_payload = {
            "chat_id": CHAT_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        try:
            r = requests.post(photo_url, json=photo_payload, timeout=12)
            if r.status_code == 200:
                return
            logging.warning(f"sendPhoto failed ({r.text}), falling back to text.")
        except Exception as e:
            logging.warning(f"sendPhoto exception: {e}, falling back to text.")

    # Fallback to text message
    text_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    text_payload = {
        "chat_id": CHAT_ID,
        "text": caption,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(text_url, json=text_payload, timeout=10)
    except Exception as e:
        logging.error(f"Error sending text message: {e}")

def run():
    domain = get_active_domain()
    if not domain:
        logging.error("Could not find responsive domain.")
        return

    seen_posts = load_seen_posts()
    logging.info(f"Tracking {len(seen_posts)} existing post IDs.")

    # Target the forum index
    candidates_to_scrape = [
        f"{domain}/",
        f"{domain}/index.php?/discover/",
    ]

    found_topics = []
    for scrape_url in candidates_to_scrape:
        try:
            logging.info(f"Fetching topics from {scrape_url}...")
            response = cffi_requests.get(scrape_url, impersonate="chrome120", timeout=15, headers=HEADERS)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # Must match forum topic format
                if "/index.php?/forums/topic/" in href or "/forums/topic/" in href:
                    title = a.get_text(strip=True)
                    clean_url = href.split("?")[0].rstrip("/")
                    
                    # Ensure it has a topic ID in the URL structure
                    match = re.search(r"/topic/(\d+)-", clean_url)
                    if match:
                        topic_id = match.group(1)
                        if topic_id not in seen_posts and clean_url not in [t[1] for t in found_topics]:
                            found_topics.append((title or "New Release", clean_url, topic_id))
        except Exception as e:
            logging.warning(f"Error fetching {scrape_url}: {e}")

    logging.info(f"Found {len(found_topics)} new posts to notify.")

    for title, link, topic_id in reversed(found_topics[:10]):  # Limit batch to 10
        details = extract_post_details(link)
        send_telegram_alert(title, link, details)
        seen_posts.add(topic_id)

    save_seen_posts(seen_posts)

if __name__ == "__main__":
    run()
