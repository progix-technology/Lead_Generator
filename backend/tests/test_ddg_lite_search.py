import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import types

from app.services import email_scraper


def test_ddg_lite_search_accepts_extract_snippets_argument(monkeypatch):
    class DummyResponse:
        status_code = 200
        text = '<html><body><table><tr><td class="snippet">hello@acme.com</td></tr></table></body></html>'

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return DummyResponse()

    dummy_httpx = types.SimpleNamespace(AsyncClient=DummyClient)
    monkeypatch.setitem(sys.modules, "httpx", dummy_httpx)

    class DummyTag:
        def __init__(self, text):
            self._text = text

        def get_text(self, separator=" ", strip=True):
            return self._text

    class DummySoup:
        def __init__(self, html, parser=None):
            self.html = html
            self.parser = parser

        def find_all(self, tag_name, href=True, class_=None):
            if tag_name == "a":
                return []
            if tag_name == "td" and class_ == "snippet":
                return [DummyTag("hello@acme.com")]
            return []

    monkeypatch.setitem(sys.modules, "bs4", types.SimpleNamespace(BeautifulSoup=DummySoup))

    results = asyncio.run(email_scraper.ddg_lite_search("test query", extract_snippets=True))
    assert results == ["hello@acme.com"]
