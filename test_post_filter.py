from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

domain = "https://www.1tamilmv.io"
url = f"{domain}/index.php?/discover/"

res = cffi_requests.get(url, impersonate="chrome120", timeout=15, headers=HEADERS)
soup = BeautifulSoup(res.text, "html.parser")

print("Parsing stream items...")
stream_items = soup.find_all(["li", "div"], class_=lambda c: c and ("ipsStreamItem" in c or "cStreamItem" in c))
print(f"Total stream items: {len(stream_items)}")

topic_creations = []
replies_and_comments = []

for item in stream_items:
    text = item.get_text()
    title_a = item.find("a", href=lambda h: h and "/topic/" in h)
    if not title_a:
        continue
        
    href = title_a.get("href", "")
    title = title_a.get_text(strip=True)
    
    # Check if this stream entry is a comment/reply or a new topic
    is_reply = False
    if "replied to" in text.lower() or "commented on" in text.lower() or "do=findComment" in href:
        is_reply = True
        
    # Also check if title is just reply count like "2 replies"
    if re.search(r"^\d+\s+repl(?:y|ies)", title.lower()):
        is_reply = True

    if is_reply:
        replies_and_comments.append((title[:50], href[:60]))
    else:
        topic_creations.append((title[:50], href[:60]))

print(f"\n✅ PURE NEW TOPIC CREATIONS ({len(topic_creations)}):")
for t, h in topic_creations[:5]:
    print(f"  • {t} -> {h}")

print(f"\n❌ FILTERED OUT REPLIES/COMMENTS ({len(replies_and_comments)}):")
for t, h in replies_and_comments[:5]:
    print(f"  • {t} -> {h}")
