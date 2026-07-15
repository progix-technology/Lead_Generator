import logging
import re
import asyncio
import urllib.parse
import sys
from urllib.parse import urljoin, urlparse
from typing import Optional, List, Tuple
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Global flag to prevent scraper from running while the browser binaries are being auto-installed
PLAYWRIGHT_INSTALLING = False

def clean_redirect_urls(url: str) -> str:
    """Unwrap search engine redirect links (Yahoo and DuckDuckGo) to retrieve the actual business/social URL."""
    if not url:
        return ""
    if 'r.search.yahoo.com' in url and 'RU=' in url:
        try:
            parts = url.split('RU=')
            if len(parts) > 1:
                target = parts[1].split('/RK=')[0]
                return urllib.parse.unquote(target)
        except Exception:
            pass
    elif 'uddg=' in url:
        try:
            parts = url.split('uddg=')
            if len(parts) > 1:
                target = parts[1].split('&')[0]
                return urllib.parse.unquote(target)
        except Exception:
            pass
    elif 'bing.com/ck/a' in url:
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            u_param = qs.get('u', [])
            if u_param:
                val = u_param[0]
                # Strip leading 'a1' or 'a' to get the clean base64 payload
                if val.startswith('a1'):
                    b64_str = val[2:]
                elif val.startswith('a'):
                    b64_str = val[1:]
                else:
                    b64_str = val
                
                # Correct padding if needed
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                
                import base64
                decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                if decoded.startswith(('http://', 'https://')):
                    return decoded
        except Exception:
            pass
    return url

# Strict Regex to match valid emails
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

def is_valid_email(email: str) -> bool:
    """Validates if an email is real and not a static asset, script, versioned package, or system placeholder."""
    email = email.lower().strip()
    
    # 1. Invalid Suffixes (covering images, scripts, stylesheet, formats, dummy domains)
    invalid_suffixes = (
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.wixpress.com', 
        'example.com', 'rating@', 'wix.com', 'here.com', 'domain.com', 'email.com', 'yourdomain.com', 'company.com',
        '.js', '.css', '.html', '.htm', '.php', '.asp', '.json', '.xml', '.map', '.ico', '.woff', '.woff2', '.ttf', '.eot',
        '.pdf', '.zip', '.tar', '.gz', '.mp3', '.mp4', '.avi', '.mov', '.doc', '.docx', '.xls', '.xlsx'
    )
    
    # 2. Invalid Prefixes (generic generic generic names, system files)
    invalid_prefixes = (
        'noreply@', 'no-reply@', 'privacy@', 'support@instagram.com', 'info@instagram.com',
        'yourname@', 'email@', 'example@', 'placeholder@', 'template@', 'username@', 'test@', 'user@', 'admin@'
    )
    
    # 3. Invalid Substrings (generic directory names, support emails, etc.)
    invalid_substrings = (
        'copyright', 'privacy', 'legal', 'abuse', 'terms', 'security', 'domain', 
        'openstreetmap', 'mapbox', 'sentry', 'wixpress', 'hostmaster',
        'chamberofcommerce', 'yellowpages', 'manta', 'yelp', 'tripadvisor', 'foursquare', 'bbb.org',
        'unsubscribe', 'unsubcribe', 'subscribe', 'usercentrics', 'cookiebot', 'onetrust', 'cookie', 'optout', 'opt-out',
        'sluurpy', 'restaurantji', 'nicelocal', 'yell.com', '192.com', 'ubereats', 'just-eat', 'deliveroo', 
        'menuwithprice', 'find-us-here', 'allbusiness', 'telepages', 'hudsongrouppage', 'trustpilot', 
        'glassdoor', 'indeed', 'bark.com', 'bark.co'
    )
    
    if any(email.endswith(suffix) for suffix in invalid_suffixes):
        return False
    if any(email.startswith(prefix) for prefix in invalid_prefixes):
        return False
    if any(sub in email for sub in invalid_substrings):
        return False
        
    # 4. Filter out package imports, CDNs, and libraries (like jquery@3.6.0.min.js, bootstrap@4)
    parts = email.split('@')
    if len(parts) == 2:
        prefix, domain = parts[0], parts[1]
        
        # Check if domain looks like version numbers (e.g. 1.2.3 or 4.5.6)
        if re.search(r'\d+\.\d+', domain):
            return False
            
        # Check if prefix contains library names or version markers
        library_keywords = [
            'jquery', 'bootstrap', 'popper', 'swiper', 'fontawesome', 'react', 'vue', 
            'npm', 'unpkg', 'cloudflare', 'jsdelivr', 'github', 'ajax', 'google-analytics'
        ]
        if any(lib in prefix for lib in library_keywords) or any(lib in domain for lib in library_keywords):
            return False
            
        # If prefix contains typical version pattern (e.g. name@v1 or name@v2)
        if re.search(r'v\d+$', prefix) or re.search(r'@v\d+', email):
            return False
            
        # Real email prefixes shouldn't contain unusual characters for human names like double dots
        if '..' in prefix or '..' in domain:
            return False
            
        # The TLD (last part of domain) should not contain digits
        tld = domain.split('.')[-1]
        if any(char.isdigit() for char in tld):
            return False
            
    return True


def extract_emails_from_html(html: str) -> List[str]:
    """Extract valid emails from raw HTML without loading images or interactive assets."""
    if not html:
        return []

    candidates: List[str] = []
    for match in EMAIL_REGEX.findall(html):
        if is_valid_email(match):
            candidates.append(match.lower())

    mailto_matches = re.findall(r'mailto:([^"\'\s<>]+)', html, re.I)
    for match in mailto_matches:
        cleaned = match.strip().rstrip('>').lower()
        if is_valid_email(cleaned):
            candidates.append(cleaned)

    seen = set()
    ordered: List[str] = []
    for email in candidates:
        if email not in seen:
            seen.add(email)
            ordered.append(email)
    return ordered


def build_priority_candidate_urls(website_url: str) -> List[str]:
    """Build a small list of likely contact/about URLs to inspect before any browser work."""
    if not website_url:
        return []

    normalized = _normalize_site_url(website_url).rstrip('/')
    candidates = [normalized]
    for suffix in ["/contact", "/contact-us", "/about", "/about-us", "/team", "/support", "/help", "/get-in-touch"]:
        candidates.append(urljoin(normalized + '/', suffix.lstrip('/')))
    return candidates


def extract_social_links_from_html(html: str, base_url: str = "") -> List[str]:
    """Extract Facebook/LinkedIn/Instagram links referenced from a page's HTML."""
    if not html:
        return []

    links: List[str] = []
    seen = set()
    for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.I):
        href = match.group(1).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        if not href.startswith(("http://", "https://")):
            href = urljoin(base_url, href)
        if not href.startswith(("http://", "https://")):
            continue
        lower_href = href.lower()
        if any(domain in lower_href for domain in ["facebook.com", "instagram.com", "linkedin.com"]):
            if href not in seen:
                seen.add(href)
                links.append(href)
    return links


async def scrape_url_for_emails(page, url: str) -> List[str]:
    """Visits a URL using httpx (fast) or Playwright (fallback) and extracts all unique valid emails."""
    logger.info(f"Agent: Scanning {url}...")
    try:
        if not url.startswith(('http://', 'https://')):
            return []
            
        # FAST PATH: Try httpx first (milliseconds)
        try:
            import httpx
            async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
                response = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if response.status_code == 200:
                    matches = EMAIL_REGEX.findall(response.text)
                    valid_emails = [m.lower() for m in matches if is_valid_email(m)]
                    if valid_emails:
                        logger.info(f"Agent: Found emails via HTTPX on {url} (Fast Path)")
                        return list(set(valid_emails))
        except Exception as http_err:
            pass # Ignore httpx errors, fallback to playwright
            
        if not page:
            return []
            
        # SLOW PATH: Fallback to Playwright for JS-rendered sites
        logger.info(f"Agent: HTTPX found no emails. Falling back to Playwright for {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=12000)
        await asyncio.sleep(2) # Give dynamic JavaScript time to render
        
        content = await page.content()
        matches = EMAIL_REGEX.findall(content)
        
        valid_emails = [m.lower() for m in matches if is_valid_email(m)]
        return list(set(valid_emails))
    except Exception as e:
        logger.warning(f"Error scraping {url}: {e}")
        return []

def _normalize_site_url(url: str) -> str:
    if not url:
        return ""
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url
    return clean_url

async def find_email_from_company_website(website_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Scans a company's own website using lightweight HTML requests first,
    prioritizing homepage/contact/about pages and avoiding image-heavy loads.
    """
    from app.services.places import should_use_playwright

    website_url = _normalize_site_url(website_url)
    if not website_url:
        return None, None

    logger.info(f"Company website email scan: trying lightweight HTML scan for {website_url}")
    try:
        import httpx
        from bs4 import BeautifulSoup

        seen_pages = {website_url.rstrip("/")}
        candidate_pages = build_priority_candidate_urls(website_url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(verify=False, timeout=6.0, follow_redirects=True) as client:
            social_candidates: List[str] = []
            for candidate_url in candidate_pages[:8]:
                try:
                    response = await client.get(candidate_url, headers=headers)
                    if response.status_code >= 400:
                        continue

                    html = response.text or ""
                    html_emails = extract_emails_from_html(html)
                    if html_emails:
                        return html_emails[0], candidate_url

                    social_links = extract_social_links_from_html(html, candidate_url)
                    for social_link in social_links:
                        if social_link not in seen_pages:
                            seen_pages.add(social_link)
                            social_candidates.append(social_link)

                    soup = BeautifulSoup(html, "html.parser")
                    for anchor in soup.find_all("a", href=True):
                        href = anchor.get("href", "")
                        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                            continue
                        if not href.startswith(("http://", "https://")):
                            href = urljoin(candidate_url, href)
                        if not href.startswith(("http://", "https://")):
                            continue
                        lower_href = href.lower()
                        if any(term in lower_href for term in ["contact", "about", "team", "support", "help", "privacy", "legal", "reach-us", "get-in-touch"]):
                            normalized = href.split("#")[0].rstrip("/")
                            if normalized not in seen_pages:
                                seen_pages.add(normalized)
                                candidate_pages.append(normalized)
                except Exception as page_err:
                    logger.warning(f"HTML contact scan failed for {candidate_url}: {page_err}")

            for social_candidate in social_candidates[:8]:
                try:
                    social_emails = await scrape_url_for_emails(None, social_candidate)
                    if social_emails:
                        return social_emails[0], social_candidate
                except Exception as social_err:
                    logger.warning(f"Social link scan failed for {social_candidate}: {social_err}")

        if should_use_playwright():
            logger.info("HTML scan found no emails; falling back to Playwright for %s", website_url)
            candidate_pages = [website_url]
            seen_pages = {website_url.rstrip("/")}
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    page = await context.new_page()

                    async def block_resources(route):
                        if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                            await route.abort()
                        else:
                            await route.continue_()

                    await page.route("**/*", block_resources)

                    try:
                        await page.goto(website_url, wait_until="domcontentloaded", timeout=12000)
                        await asyncio.sleep(1.5)
                        homepage_emails = await scrape_url_for_emails(page, website_url)
                        if homepage_emails:
                            await browser.close()
                            return homepage_emails[0], website_url

                        links = await page.evaluate("""() => {
                            const anchors = Array.from(document.querySelectorAll('a[href]'));
                            return anchors.map(a => a.href);
                        }""")

                        priority_terms = [
                            "contact", "about", "team", "support", "help", "privacy", "legal",
                            "impressum", "company", "our-story", "get-in-touch", "reach-us"
                        ]

                        for raw_link in links:
                            if not raw_link or not raw_link.startswith(("http://", "https://")):
                                continue
                            if urlparse(raw_link).netloc and urlparse(raw_link).netloc != urlparse(website_url).netloc:
                                continue

                            lower_link = raw_link.lower()
                            if any(term in lower_link for term in priority_terms):
                                normalized = raw_link.split("#")[0].rstrip("/")
                                if normalized not in seen_pages:
                                    seen_pages.add(normalized)
                                    candidate_pages.append(normalized)

                        for suffix in ["/contact", "/contact-us", "/about", "/about-us", "/team"]:
                            guessed = urljoin(website_url.rstrip("/") + "/", suffix.lstrip("/"))
                            normalized = guessed.rstrip("/")
                            if normalized not in seen_pages:
                                seen_pages.add(normalized)
                                candidate_pages.append(normalized)

                        for candidate_url in candidate_pages[1:6]:
                            try:
                                page_emails = await scrape_url_for_emails(page, candidate_url)
                                if page_emails:
                                    await browser.close()
                                    return page_emails[0], candidate_url
                            except Exception as page_err:
                                logger.warning(f"Website contact scan failed for {candidate_url}: {page_err}")

                    finally:
                        await browser.close()
            except Exception as e:
                logger.warning(f"Playwright fallback failed for {website_url}: {e}")
    except Exception as e:
        logger.warning(f"Company website email scan failed for {website_url}: {e}")

    return None, None

async def query_bing_for_links(page, query: str) -> List[str]:
    """Queries Bing Search and returns all href links found on the page."""
    bing_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}"
    try:
        logger.info(f"Scraper: Querying Bing: {bing_url}")
        await page.goto(bing_url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(0.5)
        
        # Extract all result links
        links = await page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a[href]'));
            return anchors.map(a => a.href);
        }""")
        return [clean_redirect_urls(l) for l in links]
    except Exception as e:
        logger.warning(f"Bing query failed for '{query}': {e}")
        return []

async def check_website_on_social_page(page) -> Optional[str]:
    """Scans a social profile page for external website links."""
    try:
        links = await page.evaluate("""() => {
            const anchors = Array.from(document.querySelectorAll('a[href]'));
            return anchors.map(a => a.href);
        }""")
        for link in links:
            # Clean/unwrap facebook redirect if present
            if 'l.facebook.com/l.php' in link and 'u=' in link:
                try:
                    param = link.split('u=')[1].split('&')[0]
                    link = urllib.parse.unquote(param)
                except Exception:
                    pass
            
            if not link.startswith(('http://', 'https://')):
                continue
                
            link_lower = link.lower()
            # Ignore standard social networks and directories and search engines
            ignore_domains = [
                'facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com', 'x.com',
                'youtube.com', 'pinterest.com', 'tiktok.com', 'linktr.ee', 'google.com',
                'yahoo.com', 'bing.com', 'duckduckgo.com', 'messenger.com', 'yelp.com',
                'yellowpages.com', 'yp.com', 'angi.com', 'thumbtack.com', 'forbes.com',
                'bbb.org', 'foursquare.com', 'manta.com', 'tripadvisor.com', 'houzz.com',
                'meta.com', 'whatsapp.com', 'wa.me', 'about.facebook.com'
            ]
            if any(d in link_lower for d in ignore_domains):
                continue
                
            # If we find any external custom domain, it's a website!
            return link
    except Exception as e:
        logger.warning(f"Error checking website on social page: {e}")
    return None

async def ddg_lite_search(query: str, extract_snippets: bool = False) -> List[str]:
    """Lightning fast search using DuckDuckGo Lite via HTTPX."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        import urllib.parse
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://lite.duckduckgo.com/"
        }
        url = "https://lite.duckduckgo.com/lite/"
        
        async with httpx.AsyncClient(verify=False, timeout=3.0) as client:
            r = await client.post(url, data={"q": query}, headers=headers, timeout=3.0)
            if r.status_code != 200:
                return []

            soup = BeautifulSoup(r.text, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "uddg=" in href:
                    try:
                        parts = href.split("uddg=")
                        if len(parts) > 1:
                            target = parts[1].split("&")[0]
                            href = urllib.parse.unquote(target)
                            links.append(href)
                    except Exception:
                        pass
            results = []
            
            if extract_snippets:
                for td in soup.find_all("td", class_="snippet"):
                    snippet_text = td.get_text(separator=' ', strip=True)
                    if snippet_text:
                        results.append(snippet_text)
                if results:
                    return results

            return links if links else results
    except Exception as e:
        return []

async def find_email_for_company(company_name: str, location: str, phone_number: str = "") -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Lightning-fast HTTPX search via DuckDuckGo Lite to find social links and extract emails.
    Returns: Tuple[Optional[str], Optional[str], Optional[str]] -> (email, website_url, email_source)
    """
    clean_name = (company_name or "").replace("'", "").replace('"', '')
    search_query = f"{clean_name} {location}"
    
    logger.info(f"Agent: Fast searching DDG Lite for '{search_query}'")
    
    facebook_url = None
    instagram_url = None
    linkedin_url = None

    links = await ddg_lite_search(search_query)
    for link in links:
        if not link.startswith(('http://', 'https://')): continue
        if any(domain in link for domain in ['yahoo.com', 'microsoft.com', 'google.com']): continue
        
        if 'facebook.com' in link and not facebook_url and '/public/' not in link and '/events/' not in link:
            facebook_url = link
        elif 'instagram.com' in link and not instagram_url and '/p/' not in link:
            instagram_url = link
        elif 'linkedin.com' in link and not linkedin_url and ('/company/' in link or '/in/' in link):
            linkedin_url = link

    from app.services import automation_worker
    
    if facebook_url:
        if getattr(automation_worker, "cancel_requested", False): return None, None, None
        clean_fb = facebook_url.split('?')[0].rstrip('/')
        fb_pages = [clean_fb, f"{clean_fb}/about"]
        for fb_page in fb_pages:
            if getattr(automation_worker, "cancel_requested", False): return None, None, None
            logger.info(f"Agent: Fast scanning Facebook page: {fb_page}")
            emails = await scrape_url_for_emails(None, fb_page)
            if emails:
                logger.info(f"Agent: Scraped email '{emails[0]}' from Facebook profile.")
                return emails[0], None, "Facebook"

    if instagram_url:
        if getattr(automation_worker, "cancel_requested", False): return None, None, None
        logger.info(f"Agent: Fast scanning Instagram page: {instagram_url}")
        emails = await scrape_url_for_emails(None, instagram_url)
        if emails:
            logger.info(f"Agent: Scraped email '{emails[0]}' from Instagram profile.")
            return emails[0], None, "Instagram"

    if linkedin_url:
        if getattr(automation_worker, "cancel_requested", False): return None, None, None
        clean_li = linkedin_url.split('?')[0].rstrip('/')
        li_pages = [clean_li]
        if '/company/' in clean_li:
            li_pages.append(f"{clean_li}/about")
        for li_page in li_pages:
            if getattr(automation_worker, "cancel_requested", False): return None, None, None
            logger.info(f"Agent: Fast scanning LinkedIn page: {li_page}")
            emails = await scrape_url_for_emails(None, li_page)
            if emails:
                logger.info(f"Agent: Scraped email '{emails[0]}' from LinkedIn profile.")
                return emails[0], None, "LinkedIn"

    if getattr(automation_worker, "cancel_requested", False): return None, None, None
    direct_query = f'"{clean_name}" "{location}" email'
    snippets = await ddg_lite_search(direct_query, extract_snippets=True)
    for snippet in snippets:
        matches = EMAIL_REGEX.findall(snippet)
        emails = [m.lower() for m in matches if is_valid_email(m)]
        if emails:
            logger.info(f"Agent: Scraped email '{emails[0]}' directly from DDG snippet for query '{direct_query}'.")
            return emails[0], None, "Direct Search"

    if phone_number:
        if getattr(automation_worker, "cancel_requested", False): return None, None, None
        try:
            clean_phone = re.sub(r'[^\d+]', '', phone_number)
            if len(clean_phone) >= 7:
                phone_query = f'"{phone_number}" email'
                snippets = await ddg_lite_search(phone_query, extract_snippets=True)
                for snippet in snippets:
                    matches = EMAIL_REGEX.findall(snippet)
                    emails = [m.lower() for m in matches if is_valid_email(m)]
                    if emails:
                        logger.info(f"Agent: Scraped email '{emails[0]}' via Reverse Phone mapping on DDG.")
                        return emails[0], None, "Reverse Phone Search"
        except Exception:
            pass

    return None, None, None
