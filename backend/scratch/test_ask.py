import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_ask_correct():
    url = "https://www.ask.com/web"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            r = await client.get(url, params={"q": "San Jose Heating & Cooling San Jose, CA"}, headers=headers)
            print("Ask Status:", r.status_code)
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Ask.com results are usually anchors with class="algo-title" or containing redirects
            links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href")
                if href.startswith(("http://", "https://")) and "ask.com" not in href:
                    links.append(href)
            print("Ask Links found:", len(links))
            for l in links[:10]:
                print(" -", l)
    except Exception as e:
        print("Ask Error:", e)

if __name__ == "__main__":
    asyncio.run(test_ask_correct())
