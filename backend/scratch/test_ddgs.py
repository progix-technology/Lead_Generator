import asyncio
from duckduckgo_search import DDGS

async def test_ddgs():
    print("Initializing DuckDuckGo Search client...")
    try:
        # DDGS class is synchronous by default, but supports async or context manager
        with DDGS() as ddgs:
            query = "San Jose Heating & Cooling San Jose, CA"
            print(f"Searching for: '{query}'")
            results = ddgs.text(query, max_results=10)
            print("Results count:", len(results))
            for r in results[:5]:
                print(" - Title:", r.get("title"))
                print("   Link:", r.get("href"))
                print("   Snippet:", r.get("body")[:100])
    except Exception as e:
        print("DDGS Error:", e)

if __name__ == "__main__":
    asyncio.run(test_ddgs())
