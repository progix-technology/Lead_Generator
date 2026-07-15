import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.email_scraper import (
    extract_emails_from_html,
    build_priority_candidate_urls,
    extract_social_links_from_html,
)


def test_extract_emails_from_html_filters_valid_addresses():
    html = """
    <html><body>
      <a href="/contact">Contact Us</a>
      <p>hello@acme.com</p>
      <p>sales@acme.com</p>
      <p>example@company.com</p>
      <p>info@acme.com</p>
    </body></html>
    """

    emails = extract_emails_from_html(html)

    assert emails == ["hello@acme.com", "sales@acme.com", "info@acme.com"]


def test_build_priority_candidate_urls_prioritizes_contact_and_about_pages():
    base_url = "https://example.com"
    candidates = build_priority_candidate_urls(base_url)

    assert candidates[0] == "https://example.com"
    assert "https://example.com/contact" in candidates
    assert "https://example.com/about" in candidates


def test_extract_social_links_from_html_collects_social_profiles():
    html = """
    <html><body>
      <a href="https://facebook.com/acme">Facebook</a>
      <a href="https://www.linkedin.com/company/acme">LinkedIn</a>
      <a href="https://instagram.com/acme">Instagram</a>
    </body></html>
    """

    links = extract_social_links_from_html(html, "https://example.com")

    assert "https://facebook.com/acme" in links
    assert "https://www.linkedin.com/company/acme" in links
    assert "https://instagram.com/acme" in links
