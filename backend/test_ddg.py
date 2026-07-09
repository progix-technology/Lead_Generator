import re
from duckduckgo_search import DDGS

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def test():
    with DDGS() as ddgs:
        results = ddgs.text('"Dave\'s Dairy" united kingdom email OR contact "@"', max_results=5)
        if not results:
            print("No results")
            return
            
        for r in results:
            print("Title:", r.get('title'))
            print("Link:", r.get('href'))
            snippet = r.get('body', '') + " " + r.get('title', '')
            print("Snippet:", snippet)
            print("Emails:", EMAIL_REGEX.findall(snippet))
            print("-" * 50)

if __name__ == "__main__":
    test()
