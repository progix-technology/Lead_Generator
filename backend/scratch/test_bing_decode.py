import asyncio
import httpx
from bs4 import BeautifulSoup
import urllib.parse
import base64

def clean_redirect_urls(url: str) -> str:
    if not url:
        return ""
    if 'bing.com/ck/a' in url:
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            u_param = qs.get('u', [])
            if u_param:
                val = u_param[0]
                if val.startswith('a1'):
                    b64_str = val[2:]
                elif val.startswith('a'):
                    b64_str = val[1:]
                else:
                    b64_str = val
                
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                
                decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                if decoded.startswith(('http://', 'https://')):
                    return decoded
        except Exception as e:
            print("Error decoding Bing link:", e)
    return url

async def test_bing_parse():
    url = "https://www.bing.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
        r = await client.get(url, params={"q": "San Jose Heating & Cooling San Jose, CA"}, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            cleaned = clean_redirect_urls(href)
            if cleaned.startswith(('http://', 'https://')) and "bing.com" not in cleaned:
                links.append(cleaned)
        print("Bing parsed links:", len(links))
        for l in links[:10]:
            print(" -", l)

if __name__ == "__main__":
    asyncio.run(test_bing_parse())
