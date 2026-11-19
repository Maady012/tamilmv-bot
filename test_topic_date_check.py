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

print("Inspecting topic dates...")
topics = {}
for item in stream_items:
    a = item.find("a", href=lambda h: h and "/topic/" in h)
    if not a:
        continue
    m = re.search(r"/topic/(\d+)-", a["href"])
    if not m or int(m.group(1)) < 10000:
        continue
    tid = m.group(1)
    if tid in topics:
        continue
    time_tag = item.find("time")
    date_str = time_tag["datetime"] if time_tag and time_tag.has_attr("datetime") else "No time"
    title = a.get_text(strip=True)[:45]
    topics[tid] = (title, date_str, a["href"])

# Sort by numeric Topic ID descending (highest topic ID = newest created topic!)
sorted_by_id = sorted(topics.items(), key=lambda x: int(x[0]), reverse=True)

print(f"\nDiscovered {len(sorted_by_id)} unique releases. Sorted by Highest Topic ID (Newest First):")
for tid, data in sorted_by_id[:6]:
    print(f"  TID: {tid} | Date: {data[1]} | Title: {data[0]}")
