import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_gibiru():
    url = "https://gibiru.com/results.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            r = await client.get(url, params={"q": "San Jose Heating & Cooling San Jose, CA"}, headers=headers)
            print("Gibiru Status:", r.status_code)
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Extract links
            links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href")
                if href.startswith(("http://", "https://")) and "gibiru" not in href:
                    links.append(href)
            print("Gibiru Links found:", len(links))
            for l in links[:10]:
                print(" -", l)
    except Exception as e:
        print("Gibiru Error:", e)

if __name__ == "__main__":
    asyncio.run(test_gibiru())
