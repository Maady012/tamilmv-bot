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

stream_items = soup.find_all(["li", "div"], class_=lambda c: c and ("ipsStreamItem" in c or "cStreamItem" in c))
print(f"Total stream items: {len(stream_items)}")

entries = []
for idx, item in enumerate(stream_items):
    text = item.get_text()
    title_a = item.find("a", href=lambda h: h and "/topic/" in h)
    if not title_a:
        continue
    href = title_a.get("href", "")
    m = re.search(r"/topic/(\d+)-", href)
    if not m:
        continue
    tid = m.group(1)
    
    # Check if reply or topic creation
    is_reply = ("replied to" in text.lower() or "commented on" in text.lower() or "do=findComment" in href)
    entries.append({
        "index": idx,
        "tid": tid,
        "title": title_a.get_text(strip=True)[:45],
        "is_reply": is_reply
    })

print(f"Parsed {len(entries)} entries. Top 15:")
for e in entries[:15]:
    status = "REPLY" if e["is_reply"] else "TOPIC_CREATION"
    print(f" [{e['index']:02d}] TID: {e['tid']} | {status:14s} | {e['title']}")
