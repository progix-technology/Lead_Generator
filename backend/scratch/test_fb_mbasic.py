import asyncio
import httpx
import re

async def test_facebook_mbasic():
    # Example Facebook page
    url = "https://mbasic.facebook.com/sanjoseheatandcooling/about"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    try:
        async with httpx.AsyncClient(verify=False, timeout=5.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            print("Status code:", r.status_code)
            print("Final URL:", r.url)
            
            # Use regex to find emails
            EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
            matches = EMAIL_REGEX.findall(r.text)
            print("Emails found on page:", list(set(matches)))
            
            # Print page title or body snippet
            print("\nBody Snippet:")
            print(r.text[:800])
    except Exception as e:
        print("Error fetching mbasic Facebook:", e)

if __name__ == "__main__":
    asyncio.run(test_facebook_mbasic())
