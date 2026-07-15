import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("SECRET_KEY", "test-secret")

from app.services import places


def test_playwright_is_disabled_on_render(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("PLAYWRIGHT_ENABLED", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_DISABLED", raising=False)
    assert places.should_use_playwright() is False


def test_playwright_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_ENABLED", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_DISABLED", raising=False)
    monkeypatch.delenv("LOCAL_DEV", raising=False)
    assert places.should_use_playwright() is False


def test_playwright_is_enabled_when_explicitly_requested(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("PLAYWRIGHT_ENABLED", "true")
    monkeypatch.delenv("PLAYWRIGHT_DISABLED", raising=False)
    monkeypatch.delenv("LOCAL_DEV", raising=False)
    assert places.should_use_playwright() is True
