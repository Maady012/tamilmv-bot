from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import re
import urllib.parse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

domain = "https://www.1tamilmv.io"
url = f"{domain}/index.php?/discover/"
print("Testing fetch from", url)
res = cffi_requests.get(url, impersonate="chrome120", timeout=15, headers=HEADERS)
print("Status:", res.status_code)

soup = BeautifulSoup(res.text, "html.parser")
articles = soup.find_all(["li", "div"], class_=lambda c: c and "ipsStreamItem" in c)
print("Stream items found:", len(articles))

for item in articles[:5]:
    title_link = item.find("a", href=lambda h: h and "/topic/" in h)
    if title_link:
        print("Title:", title_link.get_text(strip=True))
        print("Link:", title_link["href"])
        print("---")
