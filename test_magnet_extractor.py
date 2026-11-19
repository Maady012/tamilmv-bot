import re
import urllib.parse
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

domain = "https://www.1tamilmv.io"
discover_url = f"{domain}/index.php?/discover/"

print(f"[1] Connecting to discover feed: {discover_url}")
res = cffi_requests.get(discover_url, impersonate="chrome120", timeout=15, headers=HEADERS)
print(f"    Discover HTTP status: {res.status_code}")

soup = BeautifulSoup(res.text, "html.parser")

# Find first 3 distinct topic URLs from discover
topic_urls = []
for a in soup.find_all("a", href=lambda h: h and "/topic/" in h):
    href = a["href"]
    m = re.search(r"/topic/(\d+)-", href)
    if m:
        tid = m.group(1)
        clean_url = href.split("#")[0]
        if clean_url.startswith("/"):
            clean_url = f"{domain}{clean_url}"
        if clean_url not in topic_urls:
            topic_urls.append(clean_url)
            if len(topic_urls) >= 3:
                break

print(f"[2] Sample topic URLs found for testing ({len(topic_urls)}):")
for u in topic_urls:
    print(f"    - {u}")

print("\n[3] Testing magnet link extraction on sample topics...")
results = []
for idx, u in enumerate(topic_urls, 1):
    print(f"\n--- Testing Topic #{idx}: {u} ---")
    page_res = cffi_requests.get(u, impersonate="chrome120", timeout=15, headers=HEADERS)
    print(f"    Page Status: {page_res.status_code}")
    page_soup = BeautifulSoup(page_res.text, "html.parser")
    
    # 1. Check title
    title_tag = page_soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Unknown Title"
    print(f"    Extracted Title: {title[:60]}")

    # 2. Inspect first post container
    post_wrap = page_soup.find("div", {"data-role": "commentContent"}) or page_soup.find("div", class_="cPost_contentWrap")
    
    magnets_found = []
    torrent_files_found = []
    
    if post_wrap:
        # Search all <a> tags
        for a in post_wrap.find_all("a", href=True):
            href = a["href"].strip()
            # Direct magnet link
            if href.startswith("magnet:?"):
                # Extract dn (display name) parameter if available
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                name = parsed.get("dn", [a.get_text(strip=True)])[0]
                magnets_found.append({"url": href, "label": name or "Magnet Link"})
            # Torrent file attachment link (Invision forum attachment)
            elif "/applications/core/interface/file/attachment.php" in href or ".torrent" in href:
                label = a.get_text(strip=True) or "Torrent Attachment"
                torrent_files_found.append({"url": href, "label": label})
    
    print(f"    Direct Magnets Found: {len(magnets_found)}")
    for m in magnets_found[:2]:
        print(f"      🧲 {m['label'][:40]} -> {m['url'][:45]}...")
        
    print(f"    Torrent Attachments Found: {len(torrent_files_found)}")
    for t in torrent_files_found[:2]:
        print(f"      📎 {t['label'][:40]} -> {t['url'][:45]}...")

    results.append({
        "topic": u,
        "title": title,
        "magnets": len(magnets_found),
        "attachments": len(torrent_files_found)
    })

print("\n=== SUMMARY OF EXTRACTION TEST ===")
for r in results:
    print(f"Topic: {r['title'][:40]} | Magnets: {r['magnets']} | Torrents: {r['attachments']}")
