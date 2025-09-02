from googlesearch import search
import requests
import re

KEYWORDS = ["dsoclient", "dlcache", "nz2", "drakensang", ".rar", ".zip", ".7z"]
DRIVE_REGEX = re.compile(r"https?://drive\.google\.com/file/d/[a-zA-Z0-9_-]+")

found_links = set()

query = 'site:pastebin.com "drive.google.com/file/d/"'
print(f"[🌐] Searching Google: {query}\n")

for result in search(query, num_results=50, lang="en"):
    if "/archive" in result or "/search" in result:
        continue
    raw_url = result.replace("pastebin.com/", "pastebin.com/raw/")
    print(f"[🔍] Checking: {raw_url}")

    try:
        r = requests.get(raw_url, timeout=10)
        text = r.text.lower()

        if any(k in text for k in KEYWORDS):
            matches = DRIVE_REGEX.findall(text)
            for link in matches:
                if link not in found_links:
                    print(f"[✅] Found: {link}")
                    found_links.add(link)

    except Exception as e:
        print(f"[⚠️] Failed: {raw_url} | {e}")

with open("gdrive_dsoclient_links.txt", "w") as f:
    for link in sorted(found_links):
        f.write(link + "\n")

print(f"\n[🎯] Total filtered links: {len(found_links)}")
