import asyncio
import httpx
from bs4 import BeautifulSoup

async def test_ddg_session():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    try:
        # Enable HTTP2 support
        async with httpx.AsyncClient(verify=False, timeout=5.0, http2=True) as client:
            # Step 1: Visit homepage to get cookies
            print("Step 1: Visiting homepage...")
            r1 = await client.get("https://lite.duckduckgo.com/lite/", headers=headers)
            print("Homepage Status:", r1.status_code)
            cookies = r1.cookies
            print("Cookies received:", dict(cookies))
            
            # Step 2: Perform search post with cookies
            print("\nStep 2: Performing search...")
            headers["Referer"] = "https://lite.duckduckgo.com/lite/"
            r2 = await client.post(
                "https://lite.duckduckgo.com/lite/",
                data={"q": "San Jose Heating & Cooling San Jose, CA"},
                headers=headers,
                cookies=cookies
            )
            print("Search Status:", r2.status_code)
            soup = BeautifulSoup(r2.text, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href")
                if "uddg=" in href:
                    links.append(href)
            print("Links found:", len(links))
            for l in links[:5]:
                print(" -", l)
    except Exception as e:
        print("Session Test Error:", e)

if __name__ == "__main__":
    asyncio.run(test_ddg_session())
