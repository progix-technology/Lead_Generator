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
        '.pdf', '.zip', '.tar', '.gz', '.mp3', '.mp4', '.avi', '.mov', '.doc', '.docx', '.xls', '.xlsx',
        '.mx', '.ru', '.cn', '.br', '.vn', '.id', '.th', '.pl', '.tr'
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
        'glassdoor', 'indeed', 'bark.com', 'bark.co', 'uservoice.com', 'uservoice'
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
            
    # 5. DNS Deliverability (MX Record) Check
    # This prevents sending to expired domains or fake addresses which cause bounces.
    try:
        from email_validator import validate_email
        validate_email(email, check_deliverability=True)
    except Exception as e:
        logger.info(f"Agent: Rejected email '{email}' due to deliverability check failure ({e})")
        return False
            
    return True


def get_best_email(emails: List[str], target_website: str = "") -> Optional[str]:
    """Select the best email from a list by prioritizing domain matches and generic providers."""
    if not emails: return None
    
    valid_emails = []
    for e in emails:
        if e not in valid_emails:
            valid_emails.append(e)
            
    if not target_website: return valid_emails[0]
    
    try:
        from urllib.parse import urlparse
        domain = urlparse(target_website).netloc.lower().replace('www.', '')
    except Exception:
        domain = ""
        
    # 1. Exact domain match
    if domain:
        for e in valid_emails:
            if e.endswith(f"@{domain}"): return e
            
    # 2. Substring domain match (e.g. crazypets.ae -> crazypets)
    if domain:
        base = domain.split('.')[0]
        if len(base) > 3:
            for e in valid_emails:
                if base in e.split('@')[1]: return e
                
    # 3. Generic emails (gmail, yahoo, etc.)
    generics = ['gmail.com', 'yahoo', 'hotmail', 'outlook', 'icloud', 'aol']
    for e in valid_emails:
        if any(g in e for g in generics): return e
        
    # 4. Filter out common web agency/marketing domains if they don't match the company domain
    agency_keywords = ['design', 'studio', 'agency', 'media', 'creative', 'digital', 'marketing', 'web', 'tech']
    filtered = []
    for e in valid_emails:
        domain_part = e.split('@')[1] if '@' in e else ''
        if not any(kw in domain_part for kw in agency_keywords):
            filtered.append(e)
            
    if filtered:
        return filtered[0]
        
    return valid_emails[0]


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


def build_direct_search_queries(company_name: str, location: str) -> List[str]:
    """Create a short list of lightweight direct-search queries to increase the chance of finding an email quickly."""
    clean_name = (company_name or "").strip().replace("'", "").replace('"', "")
    if not clean_name:
        return []
    normalized_name = re.sub(r"\s+", " ", clean_name).strip()
    queries = []
    if normalized_name and location:
        queries.extend([
            f'"{normalized_name}" "{location}" email',
            f'"{normalized_name}" "{location}" contact',
            f'"{normalized_name}" "{location}" info',
            f'"{normalized_name}" {location} @gmail.com',
            f'"{normalized_name}" {location} @yahoo.com',
        ])
    elif normalized_name:
        queries.extend([
            f'"{normalized_name}" email',
            f'"{normalized_name}" contact',
            f'"{normalized_name}" info',
        ])
    return list(dict.fromkeys(queries))[:5]


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
    Scans a company's own website using lightweight concurrent HTML requests.
    Playwright is completely bypassed to prevent heavy CPU usage and speed up scan times.
    """
    website_url = _normalize_site_url(website_url)
    if not website_url:
        return None, None

    logger.info(f"Company website scan: launching fast HTTPX scan for {website_url}")
    try:
        import httpx
        from bs4 import BeautifulSoup

        seen_pages = {website_url.rstrip("/")}
        candidate_pages = build_priority_candidate_urls(website_url)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Scan candidate pages concurrently in batches of 4 to save time
        async with httpx.AsyncClient(verify=False, timeout=5.0, follow_redirects=True) as client:
            social_candidates: List[str] = []
            
            async def scan_single_page(url):
                try:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code < 400:
                        return url, resp.text
                except Exception:
                    pass
                return url, None

            # Concurrently crawl top 8 priority candidate pages (Homepage, Contact, About, Staff, Team)
            tasks = [scan_single_page(u) for u in candidate_pages[:8]]
            results = await asyncio.gather(*tasks)

            all_emails = []
            for page_url, html in results:
                if not html:
                    continue
                
                # Check for emails in HTML content
                emails = extract_emails_from_html(html)
                if emails:
                    all_emails.extend(emails)

                # Pull social media connections
                social_links = extract_social_links_from_html(html, page_url)
                for link in social_links:
                    if link not in seen_pages:
                        seen_pages.add(link)
                        social_candidates.append(link)

            if all_emails:
                best_email = get_best_email(all_emails, website_url)
                if best_email:
                    logger.info(f"Agent: Found best email '{best_email}' for website {website_url} via HTTPX")
                    return best_email, website_url

            # If no website email was found, try the scraped social pages
            for social_url in social_candidates[:3]:
                try:
                    social_emails = await scrape_url_for_emails(None, social_url)
                    if social_emails:
                        return social_emails[0], social_url
                except Exception:
                    pass

    except Exception as e:
        logger.warning(f"Fast HTTPX scan failed for {website_url}: {e}")

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

import random

_ddg_semaphore = asyncio.Semaphore(1)

async def ddg_lite_search(query: str, extract_snippets: bool = False) -> List[str]:
    """Lightning fast search using custom HTTPX scraper targeting DuckDuckGo HTML."""
    async with _ddg_semaphore:
        await asyncio.sleep(random.uniform(1.0, 2.0))
        try:
            import httpx
            from bs4 import BeautifulSoup
            
            USER_AGENTS = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
            ]
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }
            import urllib.parse
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                r = await client.get(url, headers=headers)
                if r.status_code not in (200, 201, 202):
                    if r.status_code not in (403, 429):
                        logger.warning(f"DDG search failed for query '{query}': HTTP {r.status_code}")
                    return []

                soup = BeautifulSoup(r.text, "html.parser")
                
                if extract_snippets:
                    results = []
                    for snippet in soup.select("a.result__snippet"):
                        text = snippet.get_text(strip=True)
                        if text:
                            results.append(text)
                    return results

                results = []
                for a in soup.select('a.result__url'):
                    href = a.get('href')
                    if href and href.startswith('http'):
                        results.append(href)

                return results
        except Exception as e:
            err_str = str(e).lower()
            if not any(x in err_str for x in ["403", "429", "timeout", "connect"]) and err_str.strip():
                logger.error(f"DDG search error: {e}")
            return []

async def ddg_lite_search_fanout(queries: List[str], extract_snippets: bool = False, max_results: int = 5) -> List[str]:
    """Run a small set of DDG Lite queries concurrently and return the first useful results."""
    if not queries:
        return []

    async def run_query(query: str) -> List[str]:
        return await ddg_lite_search(query, extract_snippets=extract_snippets)

    tasks = [run_query(query) for query in queries[:max_results]]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    results: List[str] = []
    for response in responses:
        if isinstance(response, Exception):
            continue
        if response:
            results.extend(response)
    return results

async def query_yahoo_fallback(query: str) -> Tuple[List[str], List[str]]:
    import httpx
    import urllib.parse
    import re
    from bs4 import BeautifulSoup
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
    ]
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }
    subdomain = random.choice(['search', 'uk.search', 'in.search', 'ca.search', 'au.search'])
    url = f"https://{subdomain}.yahoo.com/search?p={urllib.parse.quote_plus(query)}"
    links = []
    text_emails = []
    
    try:
        await asyncio.sleep(random.uniform(1.0, 3.0))
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Extract links
            for a in soup.find_all('a', href=True):
                href = a['href']
                if "/RU=" in href:
                    ru_part = href.split("/RU=")[1].split("/RK=")[0]
                    real_url = urllib.parse.unquote(ru_part)
                    links.append(real_url)
                elif href.startswith('http') and not any(x in href.lower() for x in ['yahoo.com', 'yimg.com', 'microsoft.com', 'google.com', 'bing.com']):
                    links.append(href)
                    
            # 2. Extract direct emails from snippet text
            page_text = soup.get_text()
            matches = EMAIL_REGEX.findall(page_text)
            for m in matches:
                m_lower = m.lower()
                if not any(x in m_lower for x in ['yahoo', 'yimg', 'microsoft', 'google', 'png', 'jpg', 'example', 'sentry', 'bootstrap', 'w3.org']):
                    text_emails.append(m_lower)
    except Exception as e:
        err_str = str(e).lower()
        if not any(x in err_str for x in ["403", "429", "timeout", "connect"]) and err_str.strip():
            logger.warning(f"Yahoo Search fallback error: {e}")
        
    return links, text_emails

async def find_email_for_company(company_name: str, location: str, phone_number: str = "") -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Deep multi-engine search using DDG Lite + Yahoo Search concurrently.
    Extracts emails from snippet text, social profiles (Facebook/Instagram/LinkedIn), custom websites, and directory listings.
    Returns: Tuple[Optional[str], Optional[str], Optional[str]] -> (email, website_url, email_source)
    """
    clean_name = (company_name or "").replace("'", "").replace('"', '').strip()
    search_queries = [
        f'"{clean_name}" {location} email',
        f"{clean_name} {location} facebook",
        f"{clean_name} {location} instagram",
        f"{clean_name} {location}"
    ]
    
    logger.info(f"Agent: Executing deep multi-engine search for '{company_name}' in '{location}'...")
    
    # 1. Run DDG & Yahoo queries concurrently for maximum coverage
    ddg_task = ddg_lite_search_fanout(search_queries, extract_snippets=False, max_results=3)
    yahoo_tasks = [query_yahoo_fallback(q) for q in search_queries[:3]]
    
    results = await asyncio.gather(ddg_task, *yahoo_tasks, return_exceptions=True)
    
    links: List[str] = []
    snippet_emails: List[str] = []
    
    for r in results:
        if isinstance(r, Exception) or not r:
            continue
        if isinstance(r, list): # DDG links
            links.extend(r)
        elif isinstance(r, tuple): # Yahoo (links, text_emails)
            y_links, y_emails = r
            links.extend(y_links)
            snippet_emails.extend(y_emails)

    # 2. Check if a valid email was found directly in search result snippets
    for se in snippet_emails:
        if is_valid_email(se):
            logger.info(f"Agent: Found email '{se}' directly in search result snippets!")
            return se, None, "Direct Search"

    if not links:
        return None, None, None
        
    facebook_url = None
    instagram_url = None
    linkedin_url = None
    discovered_web = None

    INVALID_WEBSITE_DOMAINS = [
        'yelp.com', 'facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com', 'x.com',
        'apple.com', 'maps.apple.com', 'yellowpages.com', 'yp.com', 'foursquare.com', 'bbb.org',
        'manta.com', 'tripadvisor.com', 'angi.com', 'houzz.com', 'chamberofcommerce.com',
        'local.yahoo.com', 'mapquest.com', 'greatschools.org', 'privateschoolreview.com',
        'childcarecenter.us', 'allbiz.com', 'schoolandcollegelistings.com', 'restaurantguru.com',
        'placewing.com', 'mymenuweb.com', 'cloveronline.com', 'seamless.com', 'grubhub.com',
        'doordash.com', 'ubereats.com', 'postmates.com', 'menupix.com', 'singleplatform.com',
        'chownow.com', 'toasttab.com', 'zmenu.com', 'allmenus.com', 'sirved.com',
        'loc8nearme.com', 'findglocal.com', 'top-rated.online', 'us-businesses.com',
        'companycheck.com', 'dnb.com', 'bizzlist.com', 'youtube.com', 'youtubekids.com',
        'wikipedia.org', 'wikihow.com', 'softonic.com', 'overleaf.com', 'cermati.com',
        'merriam-webster.com', 'uidai.gov.in', 'dailymotion.com', 'konglongdao.com',
        'glassdoor.com', 'indeed.com', 'duckduckgo.com', 'google.com', 'yahoo.com',
        'bing.com', 'microsoft.com', 'heavenlydelightsbakery.com', 'localoria.com',
        'findcoffeeshop.com', 'atly.com', 'roadtrippers.com', 'checkle.com', 'alltopplaces.com'
    ]

    other_candidate_urls = []

    for link in links:
        if not link.startswith(('http://', 'https://')): continue
        link_lower = link.lower()
        if any(domain in link_lower for domain in ['yahoo.com', 'microsoft.com', 'google.com', 'bing.com']): continue
        
        if 'facebook.com' in link_lower and not facebook_url and '/public/' not in link_lower and '/events/' not in link_lower:
            facebook_url = link
        elif 'instagram.com' in link_lower and not instagram_url and '/p/' not in link_lower:
            instagram_url = link
        elif 'linkedin.com' in link_lower and not linkedin_url and ('/company/' in link_lower or '/in/' in link_lower):
            linkedin_url = link
        else:
            if not any(invalid in link_lower for invalid in INVALID_WEBSITE_DOMAINS):
                if not discovered_web:
                    discovered_web = link
            else:
                other_candidate_urls.append(link)

    from app.services import automation_worker
    
    # 3. Deep Scan Facebook Profile (Main Page + /about)
    if facebook_url:
        if getattr(automation_worker, "cancel_requested", False): return None, None, None
        clean_fb = facebook_url.split('?')[0].rstrip('/')
        fb_pages = [clean_fb, f"{clean_fb}/about"]
        for fb_page in fb_pages:
            logger.info(f"Agent: Fast scanning Facebook page: {fb_page}")
            emails = await scrape_url_for_emails(None, fb_page)
            if emails:
                return emails[0], discovered_web, "Facebook"

    # 4. Deep Scan Instagram Profile
    if instagram_url:
        if getattr(automation_worker, "cancel_requested", False): return None, None, None
        logger.info(f"Agent: Fast scanning Instagram page: {instagram_url}")
        emails = await scrape_url_for_emails(None, instagram_url)
        if emails:
            return emails[0], discovered_web, "Instagram"

    # 5. Deep Scan Discovered Website if present
    if discovered_web:
        if getattr(automation_worker, "cancel_requested", False): return None, None, None
        logger.info(f"Agent: Deep scanning discovered website for emails: {discovered_web}")
        try:
            site_email, site_page = await find_email_from_company_website(discovered_web)
            if site_email:
                return site_email, discovered_web, "Discovered Website"
        except Exception:
            pass
        emails = await scrape_url_for_emails(None, discovered_web)
        if emails:
            best = get_best_email(emails, discovered_web)
            return best, discovered_web, "Discovered Website"

    # 6. Deep Scan Candidate Directory URLs for email matches
    for cand in other_candidate_urls[:5]:
        if getattr(automation_worker, "cancel_requested", False): return None, None, None
        logger.info(f"Agent: Deep scanning candidate directory for email: {cand}")
        emails = await scrape_url_for_emails(None, cand)
        if emails:
            return emails[0], discovered_web, "Directory Listing"

    return None, discovered_web, None
