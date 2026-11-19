import os
import re
import html
import urllib.parse
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import requests

BOT_TOKEN = "8386941685:AAEvrhutltXAT25CEf91ZFEP_AJjI9N9zLE"
CHAT_ID = "565062030"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

domain = "https://www.1tamilmv.io"
discover_url = f"{domain}/index.php?/discover/"

print(f"Fetching discover: {discover_url}")
res = cffi_requests.get(discover_url, impersonate="chrome120", timeout=15, headers=HEADERS)
soup = BeautifulSoup(res.text, "html.parser")

candidate_urls = []
for a in soup.find_all("a", href=lambda h: h and "/topic/" in h):
    m = re.search(r"/topic/(\d+)-", a["href"])
    if m and int(m.group(1)) > 10000:
        url = a["href"].split("#")[0]
        if url.startswith("/"):
            url = f"{domain}{url}"
        if url not in candidate_urls:
            candidate_urls.append((a.get_text(strip=True), url, m.group(1)))

print(f"Candidate releases found: {len(candidate_urls)}")
for c in candidate_urls[:3]:
    print(" ", c)

# Test extracting and sending the first valid candidate
for raw_title, topic_url, tid in candidate_urls[:3]:
    print(f"\nProcessing candidate: {topic_url}")
    p_res = cffi_requests.get(topic_url, impersonate="chrome120", timeout=15, headers=HEADERS)
    p_soup = BeautifulSoup(p_res.text, "html.parser")
    
    # Title
    title = ""
    title_tag = p_soup.find("title")
    if title_tag:
        t = title_tag.get_text(strip=True)
        t = re.sub(r"\s*-\s*1TamilMV.*$", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*-\s*Page\s*\d+.*$", "", t, flags=re.IGNORECASE)
        if len(t) > 5 and not t.startswith("["):
            title = t
    if not title:
        title = raw_title
        
    print(f"Extracted Title: {title}")

    post_wrap = p_soup.find("div", {"data-role": "commentContent"}) or p_soup.find("div", class_="cPost_contentWrap")
    magnets = []
    image_url = None
    desc_lines = []
    
    if post_wrap:
        for img in post_wrap.find_all("img"):
            src = img.get("data-src") or img.get("src")
            if src and src.startswith("http") and not any(k in src.lower() for k in ["emoticons", "default_photo", "logo"]):
                image_url = src
                break
                
        seen_h = set()
        for a in post_wrap.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("magnet:?"):
                m = re.search(r"urn:btih:([a-zA-Z0-9]+)", href)
                h = m.group(1).lower() if m else href
                if h not in seen_h:
                    seen_h.add(h)
                    # clean label
                    raw_l = a.get_text(strip=True)
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    dn = parsed.get("dn", [""])[0]
                    label = dn or raw_l or f"Option {len(magnets)+1}"
                    # short label
                    clean = re.sub(r"(?i)www\.1tamilmv\.\w+\s*-\s*", "", label)
                    match_q = re.search(r"(\b(?:4K|2160p|1080p|720p|HDRip|BluRay|HEVC|AVC|x264|x265)\b.*)", clean, re.IGNORECASE)
                    if match_q:
                        label = match_q.group(1).strip(" -_")[:40]
                    else:
                        label = clean[:40]
                    magnets.append({"url": href, "label": label})

        for l in post_wrap.get_text(separator="\n", strip=True).splitlines():
            l = l.strip()
            if l and 5 < len(l) < 130 and not l.startswith("http") and not l.startswith("magnet:"):
                desc_lines.append(l)

    print(f"Image URL: {image_url}")
    print(f"Magnets count: {len(magnets)}")
    for mag in magnets:
        print("  -", mag["label"], "->", mag["url"][:40])

    # Now test Telegram delivery
    caption = f"🎬 <b>{html.escape(title)}</b>\n\n"
    if desc_lines:
        caption += f"📋 <i>{html.escape(chr(10).join(desc_lines[:6]))}</i>\n\n"
    if magnets:
        caption += "🧲 <b>Direct Magnet Links:</b>\n"
        for m in magnets[:6]:
            caption += f"• <a href='{m['url']}'><b>{html.escape(m['label'])}</b></a>\n"
        caption += "\n"
    caption += f"🔗 <a href='{topic_url}'>Open on 1TamilMV</a>"

    print("Attempting to send message via Telegram API...")
    sent = False
    if image_url:
        p_res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            json={"chat_id": CHAT_ID, "photo": image_url, "caption": caption, "parse_mode": "HTML"},
            timeout=10
        )
        print("sendPhoto response:", p_res.status_code, p_res.text)
        if p_res.status_code == 200:
            sent = True

    if not sent:
        m_res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": caption, "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10
        )
        print("sendMessage response:", m_res.status_code, m_res.text)
    break
