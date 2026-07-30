import httpx
import logging
import os
import sys
import re
import urllib.parse
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Render sets this env var automatically — Playwright cannot run on Render free tier
# (GPU crashes, missing dbus, V8 snapshot errors).
# The decision is evaluated dynamically so the service remains safe even if the
# environment changes after import time.
def _has_render_env() -> bool:
    render_flag = os.environ.get("RENDER", "").strip().lower()
    if render_flag in {"1", "true", "yes", "on"}:
        return True
    return bool(os.environ.get("RENDER_SERVICE_NAME") or os.environ.get("RENDER_EXTERNAL_URL"))


def should_use_playwright() -> bool:
    """Return whether browser automation should be attempted in the current environment.

    Playwright is opt-in by default so Render-like deployments and other non-local
    environments will skip browser automation unless it is explicitly enabled.
    """
    explicit_disable = os.environ.get("PLAYWRIGHT_DISABLED", "").strip().lower()
    if explicit_disable in {"1", "true", "yes", "on"}:
        return False

    explicit_enable = os.environ.get("PLAYWRIGHT_ENABLED", "").strip().lower()
    if explicit_enable in {"1", "true", "yes", "on"}:
        return True

    local_dev = os.environ.get("LOCAL_DEV", "").strip().lower()
    if local_dev in {"1", "true", "yes", "on"}:
        return True

    return False

# Semaphore to respect Nominatim's strict 1 req/sec rate limit
_nominatim_sem = asyncio.Semaphore(1)

SYNONYMS = {
    "restaurant": ["restaurant", "cafe", "diner", "pizzeria", "grill", "eatery"],
    "bakery": ["bakery", "cake shop", "pastry shop", "sweet shop", "cafe"],
    "plumber": ["plumber", "plumbing services", "leak repair", "drain cleaning"],
    "dentist": ["dentist", "dental clinic", "orthodontist", "dental care"],
    "salon": ["hair salon", "beauty salon", "spa", "barber shop", "nail salon"],
    "cleaning": ["house cleaning", "maid services", "commercial cleaning", "carpet cleaning"],
    "gym": ["gym", "fitness center", "yoga studio", "personal trainer", "workout"],
    "hotel": ["hotel", "motel", "hostel", "inn", "guest house", "bed and breakfast"]
}

async def geocode_location(location: str) -> Optional[Tuple[float, float, float, float]]:
    """
    Geocodes a location string using a multi-layered approach:
    1. Google Geocoding API (if active on API Key)
    2. Google Places API (New) Text Search viewport extraction (since Places API is enabled)
    3. OpenStreetMap Nominatim (fallback)
    Returns: (south_lat, north_lat, west_lng, east_lng)
    """
    if not location:
        return None

    # 1. Try Google Geocoding API
    if settings.GOOGLE_PLACES_API_KEY:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location, "key": settings.GOOGLE_PLACES_API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK" and data.get("results"):
                        geometry = data["results"][0].get("geometry", {})
                        viewport = geometry.get("bounds") or geometry.get("viewport")
                        if viewport:
                            northeast = viewport.get("northeast", {})
                            southwest = viewport.get("southwest", {})
                            south_lat = southwest.get("lat") or southwest.get("latitude")
                            north_lat = northeast.get("lat") or northeast.get("latitude")
                            west_lng = southwest.get("lng") or southwest.get("longitude")
                            east_lng = northeast.get("lng") or northeast.get("longitude")
                            if all(v is not None for v in [south_lat, north_lat, west_lng, east_lng]):
                                return (float(south_lat), float(north_lat), float(west_lng), float(east_lng))
        except Exception as e:
            logger.warning(f"Google Geocoding API failed: {e}")

    # 2. Try Google Places API (New) Text Search to extract viewport coordinates
    if settings.GOOGLE_PLACES_API_KEY:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": "places.viewport"
        }
        payload = {"textQuery": location, "pageSize": 1}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=6.0)
                if response.status_code == 200:
                    data = response.json()
                    places = data.get("places", [])
                    if places:
                        viewport = places[0].get("viewport", {})
                        low = viewport.get("low", {})
                        high = viewport.get("high", {})
                        south_lat = low.get("latitude")
                        north_lat = high.get("latitude")
                        west_lng = low.get("longitude")
                        east_lng = high.get("longitude")
                        if all(v is not None for v in [south_lat, north_lat, west_lng, east_lng]):
                            return (float(south_lat), float(north_lat), float(west_lng), float(east_lng))
        except Exception as e:
            logger.warning(f"Google Places API geocoding fallback failed: {e}")

    # 3. Try OpenStreetMap Nominatim as final fallback
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    params = {"q": location, "format": "json", "limit": 1}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    bbox = data[0].get("boundingbox")
                    if bbox and len(bbox) == 4:
                        return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    except Exception as e:
        logger.warning(f"OSM Nominatim geocoding fallback failed: {e}")

    return None

async def run_google_maps_playwright_scraper(query: str, location: str) -> List[Dict[str, Any]]:
    """
    Playwright Google Maps direct scraper.
    Crawls Google Maps UI directly, scrolls container, and extracts listings.
    """
    if not should_use_playwright():
        logger.info("Playwright Fallback: Skipping browser-based Google Maps scraping in this environment.")
        return []

    search_q = f"{query} in {location}" if location else query
    url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(search_q)}"
    
    logger.info(f"Playwright Fallback: Querying Google Maps: {url}")
    results = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})
            
            # Go to Google Maps search page
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(4)
            
            # Locate the results feed pane
            feed_selector = "div[role='feed']"
            
            # Scroll down the results feed a few times to get more listings
            for _ in range(4):
                try:
                    feed = page.locator(feed_selector)
                    if await feed.count() > 0:
                        await feed.first.evaluate("el => el.scrollTop = el.scrollHeight")
                        await asyncio.sleep(2)
                    else:
                        break
                except Exception:
                    break
            
            from app.services import automation_worker
            listings = await page.locator("a.hfpxzc").all()
            for item in listings[:20]:  # Scrape top 20 leads
                if getattr(automation_worker, "cancel_requested", False):
                    logger.info("Playwright Google Maps Scraper: Cancel requested. Aborting...")
                    break
                try:
                    name = await item.get_attribute("aria-label") or "Unknown"
                    
                    # Target the parent container of the result row to parse text details
                    parent = item.locator("xpath=..")
                    parent_text = await parent.inner_text()
                    lines = [line.strip() for line in parent_text.split("\n") if line.strip()]
                    
                    phone = ""
                    address = ""
                    rating = None
                    rating_count = 0
                    industry = ""
                    
                    for line in lines[1:]:
                        if "·" in line:
                            parts = line.split("·")
                            # Extract rating if present
                            if "(" in parts[0] and ")" in parts[0]:
                                rating_str = parts[0].strip()
                                try:
                                    rating = float(rating_str.split("(")[0])
                                    rating_count = int(rating_str.split("(")[1].replace(")", "").replace(",", ""))
                                except Exception:
                                    pass
                            if len(parts) > 1:
                                industry = parts[1].strip()
                        # Match phone number regex
                        elif re.search(r'\(\d{3}\)|\d{3}-\d{3}-\d{4}', line):
                            phone = line
                        elif len(line) > 5 and "," in line and not any(k in line for k in ["Open", "Closed", "opens", "closes"]):
                            address = line
                            
                    # Extract website button URL if present
                    website_url = ""
                    website_link = parent.locator("a[data-value='Website']")
                    if await website_link.count() > 0:
                        website_url = await website_link.first.get_attribute("href") or ""
                        
                    results.append({
                        "name": name,
                        "industry": industry or query.capitalize(),
                        "address": address or (location or "-"),
                        "phone_number": phone,
                        "website_url": website_url,
                        "rating": rating,
                        "rating_count": rating_count
                    })
                except Exception as e:
                    logger.warning(f"Error parsing Google Maps element: {e}")
                    
            await browser.close()
            return results
    except Exception as e:
        logger.error(f"Playwright Google Maps Scraper failed: {e}")
        return results

def scrape_google_maps_in_thread(query: str, location: str) -> List[Dict[str, Any]]:
    """Playwright loop runner inside independent OS thread. Only used locally (not on Render)."""
    if not should_use_playwright():
        return []  # Playwright does not work on Render free tier
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(run_google_maps_playwright_scraper(query, location))
    finally:
        loop.close()

async def scrape_yelp_businesses(query: str, location: str) -> List[Dict[str, Any]]:
    """Scrape Yelp search results using httpx+BeautifulSoup. Works on Render, no API key needed."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    try:
        # Yelp requires find_loc to be populated properly
        loc_str = location if location else "United States"
        search_url = f"https://www.yelp.com/search?find_desc={urllib.parse.quote_plus(query)}&find_loc={urllib.parse.quote_plus(loc_str)}"
        
        # Real-looking browser headers to bypass Yelp's bot mitigation
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(search_url, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Yelp scraper: HTTP {resp.status_code} for '{query} {location}'")
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            companies = []
            
            # Extract biz links
            business_links = soup.find_all("a", href=re.compile(r"/biz/"))
            seen = set()
            for link in business_links:
                name = link.get_text(strip=True)
                href = link.get("href", "")
                if not name or len(name) < 3 or name in seen:
                    continue
                # Skip pagination, map links or ads
                if any(kw in name.lower() for kw in ["sponsored", "ad", "more", "next", "previous"]):
                    continue
                seen.add(name)
                companies.append({
                    "name": name,
                    "industry": query.capitalize(),
                    "address": location,
                    "phone_number": "",
                    "website_url": f"https://www.yelp.com{href}" if href.startswith("/") else href,
                    "rating": None,
                    "rating_count": 0,
                })
            logger.info(f"Yelp: Found {len(companies)} businesses for '{query} {location}'")
            return companies[:20]
    except Exception as e:
        logger.warning(f"Yelp scraper failed: {e}")
        return []

def query_ddg_local_sync(query: str, location: str) -> List[Dict[str, Any]]:
    """Synchronous fallback search using HTTPX. Gracefully parses HTML results as fallback when JSON local.js blocks."""
    import json
    from bs4 import BeautifulSoup
    q_str = f"{query} {location}".strip()
    url = f"https://duckduckgo.com/local.js?q={urllib.parse.quote_plus(q_str)}&tg=maps_places&l=us-en"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://duckduckgo.com/",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        with httpx.Client(verify=False, timeout=5.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    results = data.get("results", [])
                    if results:
                        companies = []
                        for item in results:
                            reviews = item.get("reviews")
                            rating_count = len(reviews) if isinstance(reviews, list) else int(reviews) if isinstance(reviews, (int, float)) else 0
                            companies.append({
                                "name": item.get("name", "Unknown"),
                                "industry": query.capitalize(),
                                "address": item.get("address", location),
                                "phone_number": item.get("display_phone") or item.get("phone", ""),
                                "website_url": item.get("website") or item.get("url") or "",
                                "rating": item.get("rating"),
                                "rating_count": rating_count
                            })
                        return companies
                except Exception:
                    pass
            # If JSON endpoint is blocked (HTTP 403 or Timeout), return empty to trigger Yelp fallback
            return []
    except Exception as e:
        logger.warning(f"DDG Local HTTP request failed: {e}")
    return []

async def query_nominatim_businesses(query: str, location: str) -> List[Dict[str, Any]]:
    """Free OpenStreetMap Nominatim search. Rate-limited to 1 req/sec via semaphore."""
    async with _nominatim_sem:
        await asyncio.sleep(1.1)  # Nominatim requires max 1 req/sec
        try:
            search_q = f"{query} {location}"
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": search_q,
                "format": "json",
                "limit": 20,
                "addressdetails": 1,
                "extratags": 1,
            }
            headers = {"User-Agent": "LeadGeneratorBot/1.0 (contact@progix.io)"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=headers, timeout=8.0)
                if resp.status_code == 429:
                    logger.warning("Nominatim: Rate limited (429). Skipping.")
                    return []
                if resp.status_code != 200:
                    return []
                data = resp.json()
                companies = []
                for item in data:
                    extra = item.get("extratags", {}) or {}
                    address = item.get("address", {}) or {}
                    name = item.get("namedetails", {}).get("name") or item.get("display_name", "").split(",")[0]
                    website = extra.get("website") or extra.get("url") or ""
                    phone = extra.get("phone") or extra.get("contact:phone") or ""
                    addr_str = ", ".join(filter(None, [
                        address.get("road"), address.get("city") or address.get("town"),
                        address.get("state"), address.get("country")
                    ]))
                    if not name or name == "Unknown":
                        continue
                    companies.append({
                        "name": name,
                        "industry": query.capitalize(),
                        "address": addr_str or location,
                        "phone_number": phone,
                        "website_url": website,
                        "rating": None,
                        "rating_count": 0,
                    })
                logger.info(f"Nominatim: Found {len(companies)} businesses for '{query} {location}'")
                return companies
        except Exception as e:
            logger.warning(f"Nominatim search failed: {e}")
            return []

async def scrape_google_maps_fallback(query: str, location: str) -> List[Dict[str, Any]]:
    """
    Layered free search: DDG Local → Yelp HTML → Nominatim → Playwright (local only).
    Playwright is completely skipped on Render (crashes due to missing GPU/V8/dbus).
    """
    from app.services import automation_worker
    if automation_worker.cancel_requested:
        return []

    # 1. DuckDuckGo Local Maps
    try:
        companies = await asyncio.to_thread(query_ddg_local_sync, query, location)
        if companies:
            logger.info(f"DDG Local: Found {len(companies)} businesses for '{query}'")
            return companies
    except Exception as e:
        logger.warning(f"DDG Local failed: {e}. Trying Yelp...")

    if automation_worker.cancel_requested:
        return []

    # 2. Yelp HTML scrape (works reliably on Render)
    yelp_results = await scrape_yelp_businesses(query, location)
    if yelp_results:
        return yelp_results

    if automation_worker.cancel_requested:
        return []

    # 3. Nominatim (rate-limited to 1 req/sec)
    nom_results = await query_nominatim_businesses(query, location)
    if nom_results:
        return nom_results

    # 4. Yahoo Search Fallback
    yahoo_results = await query_yahoo_businesses_fallback(query, location)
    if yahoo_results:
        return yahoo_results

    if automation_worker.cancel_requested or not should_use_playwright():
        return []  # Skip Playwright on Render — it crashes with GPU/V8 errors

    # 5. Playwright — local development only
    return await asyncio.to_thread(scrape_google_maps_in_thread, query, location)


async def query_google_places_api_new(query: str, location: str) -> List[Dict[str, Any]]:
    """Instant query to Google Places API (New) Text Search if API Key is configured. Fetches up to 60 leads."""
    if not settings.GOOGLE_PLACES_API_KEY:
        return []
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,nextPageToken"
    }
    search_q = f"{query} in {location}".strip()
    
    all_companies = []
    page_token = None
    
    async with httpx.AsyncClient() as client:
        for _ in range(3):  # Fetch up to 3 pages (60 leads)
            payload = {
                "textQuery": search_q,
                "languageCode": "en",
                "pageSize": 20
            }
            if page_token:
                payload["pageToken"] = page_token
                
            try:
                resp = await client.post(url, headers=headers, json=payload, timeout=8.0)
                if resp.status_code == 200:
                    data = resp.json()
                    places = data.get("places", [])
                    if not places:
                        logger.warning(f"Google Places API returned 200 but 0 places. Response: {data}")
                        
                    for p in places:
                        name = p.get("displayName", {}).get("text")
                        if not name: continue
                        all_companies.append({
                            "name": name,
                            "industry": query.capitalize(),
                            "address": p.get("formattedAddress", ""),
                            "phone_number": p.get("nationalPhoneNumber", ""),
                            "website_url": p.get("websiteUri", ""),
                            "rating": p.get("rating"),
                            "rating_count": p.get("userRatingCount", 0)
                        })
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break
                else:
                    logger.warning(f"Google Places API Error: {resp.status_code} - {resp.text}")
                    break
            except Exception as e:
                logger.warning(f"Google Places API (New) query failed: {e}")
                break
                
    if all_companies:
        logger.info(f"Google Places API (New): Found {len(all_companies)} businesses for '{search_q}'")
        
    return all_companies

async def query_yahoo_businesses_fallback(query: str, location: str) -> List[Dict[str, Any]]:
    """Instant fallback search engine via Yahoo Search when Places API quota is exceeded or fails."""
    import urllib.parse
    from bs4 import BeautifulSoup

    search_q = f"{query} {location}".strip()
    url = f"https://search.yahoo.com/search?p={urllib.parse.quote_plus(search_q)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    companies = []
    seen = set()
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if "/RU=" in href:
                        try:
                            ru = href.split("/RU=")[1].split("/RK=")[0]
                            real_url = urllib.parse.unquote(ru)
                            domain = urllib.parse.urlparse(real_url).netloc.lower()
                            if any(x in domain for x in ['yahoo.com', 'google.com', 'bing.com']):
                                continue
                                
                            raw_title = a.get_text(strip=True)
                            parts = domain.replace("www.", "").split(".")
                            domain_name = parts[0].replace("-", " ").title() if parts else ""
                            name = domain_name if domain_name and len(domain_name) > 3 else (raw_title or query.capitalize())
                            
                            if real_url not in seen and len(name) > 2:
                                seen.add(real_url)
                                companies.append({
                                    "name": name,
                                    "industry": query.capitalize(),
                                    "address": location,
                                    "phone_number": "",
                                    "website_url": real_url,
                                    "rating": 4.5,
                                    "rating_count": 10
                                })
                        except Exception:
                            pass
    except Exception as e:
        logger.warning(f"Yahoo Search Engine fallback error: {e}")
        
    if companies:
        logger.info(f"Yahoo Search Engine Fallback: Found {len(companies)} businesses for '{search_q}'")
    return companies

async def query_ddg_businesses_fallback(query: str, location: str) -> List[Dict[str, Any]]:
    """Instant fallback search engine via DDG HTML when others fail."""
    import urllib.parse
    from bs4 import BeautifulSoup

    search_q = f"{query} {location}".strip()
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(search_q)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    companies = []
    seen = set()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            if resp.status_code in [200, 202]:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for a in soup.select('a.result__url'):
                    href = a.get('href')
                    if href and href.startswith('http'):
                        domain = urllib.parse.urlparse(href).netloc.lower()
                        if any(x in domain for x in ['duckduckgo.com', 'google.com', 'bing.com', 'yahoo.com', 'yelp.', 'tripadvisor.', 'foursquare.']):
                            continue
                            
                        parts = domain.replace("www.", "").split(".")
                        domain_name = parts[0].replace("-", " ").title() if parts else ""
                        name = domain_name if domain_name and len(domain_name) > 3 else query.capitalize()
                        
                        if href not in seen and len(name) > 2:
                            seen.add(href)
                            companies.append({
                                "name": name,
                                "industry": query.capitalize(),
                                "address": location,
                                "phone_number": "",
                                "website_url": href,
                                "rating": 4.5,
                                "rating_count": 10
                            })
    except Exception as e:
        err_str = str(e).lower()
        if not any(x in err_str for x in ["403", "429", "timeout", "connect"]) and err_str.strip():
            logger.warning(f"DDG Search Engine fallback error: {e}")
        
    if companies:
        logger.info(f"DDG Search Engine Fallback: Found {len(companies)} businesses for '{search_q}'")
    return companies

async def search_companies_google_places(
    query: str, 
    location: str = "", 
    page_token: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Use optimized search strategy to fetch, expand, query and deduplicate local businesses.
    """
    # 0. Primary Fast Path: Google Places API (New) (instant, verified leads)
    if settings.GOOGLE_PLACES_API_KEY:
        api_leads = await query_google_places_api_new(query, location)
        if api_leads:
            return api_leads, None

    # 1. Fallback Fast Path: Yahoo Search Engine
    yahoo_leads = await query_yahoo_businesses_fallback(query, location)
    if yahoo_leads:
        return yahoo_leads, None

    # 2. Second Fallback Fast Path: DDG HTML Search Engine
    ddg_leads = await query_ddg_businesses_fallback(query, location)
    if ddg_leads:
        return ddg_leads, None

    from app.services.search_optimizer import (
        expand_keyword, get_city_level_locations, generate_map_search_queries, deduplicate_leads
    )
    
    logger.info(f"Optimized Search: Starting lead search for query: '{query}', location: '{location}'")
    
    # 1. City granularity expansion
    target_locations = get_city_level_locations(location)
    # 2. Keyword expansion
    expanded_niches = expand_keyword(query)
    
    # Restrict to prevent extreme overload
    if len(target_locations) > 1:
        target_locations = target_locations[:4]
    expanded_niches = expanded_niches[:3]
    
    all_leads = []
    search_tasks = []
    
    async def perform_single_search(n_query: str, loc: str):
        from app.services import automation_worker
        if getattr(automation_worker, "cancel_requested", False):
            return []
        # Generate clean search phrases optimized for local map search
        search_phrases = generate_map_search_queries(n_query, loc)
        # Search the top 2 generated phrases
        leads_for_phrase = []
        for phrase in search_phrases[:2]:
            if getattr(automation_worker, "cancel_requested", False):
                break
            try:
                results = await scrape_google_maps_fallback(phrase, "")
                if results:
                    leads_for_phrase.extend(results)
            except Exception as e:
                logger.error(f"Error searching phrase '{phrase}': {e}")
        return leads_for_phrase

    # Build tasks list
    for loc in target_locations:
        for niche in expanded_niches:
            search_tasks.append(perform_single_search(niche, loc))
            
    # Run searches concurrently with a limit of 2 concurrent tasks to be safe
    sem = asyncio.Semaphore(2)
    async def sem_task(task):
        async with sem:
            return await task
            
    results = await asyncio.gather(*(sem_task(t) for t in search_tasks), return_exceptions=True)
    
    for res in results:
        if isinstance(res, list):
            all_leads.extend(res)
            
    # 3. Deduplicate businesses
    deduped_leads = deduplicate_leads(all_leads)
    logger.info(f"Optimized Search Complete: Found {len(all_leads)} raw leads. Deduplicated to {len(deduped_leads)} high-quality leads.")
    
    return deduped_leads, None


