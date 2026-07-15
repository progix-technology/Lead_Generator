import httpx
import logging
import sys
import re
import urllib.parse
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright
from app.config.settings import settings

logger = logging.getLogger(__name__)

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
    """Playwright loop runner inside independent OS thread."""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(run_google_maps_playwright_scraper(query, location))
    finally:
        loop.close()

def query_ddg_local_sync(query: str, location: str) -> List[Dict[str, Any]]:
    """Synchronous crawler querying DDG local search using urllib."""
    import urllib.request
    import urllib.parse
    import json
    
    q_str = f"{query} {location}"
    url = f"https://duckduckgo.com/local.js?q={urllib.parse.quote_plus(q_str)}&tg=maps_places&l=us-en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://duckduckgo.com/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Connection": "keep-alive",
    }
    
    req = urllib.request.Request(url, headers=headers)
    # Increased timeout to 8s for Render's slower network
    with urllib.request.urlopen(req, timeout=8.0) as response:
        html = response.read().decode('utf-8')
        data = json.loads(html)
        results = data.get("results", [])
        
        companies = []
        for item in results:
            # Safely resolve rating_count
            reviews = item.get("reviews")
            rating_count = 0
            if isinstance(reviews, list):
                rating_count = len(reviews)
            elif isinstance(reviews, (int, float)):
                rating_count = int(reviews)
            elif isinstance(item.get("review_count"), (int, float)):
                rating_count = int(item.get("review_count"))
                
            company = {
                "name": item.get("name", "Unknown"),
                "industry": query.capitalize(),
                "address": item.get("address", location),
                "phone_number": item.get("display_phone") or item.get("phone", ""),
                "website_url": item.get("website") or item.get("url") or "",
                "rating": item.get("rating"),
                "rating_count": rating_count
            }
            companies.append(company)
        return companies

async def query_nominatim_businesses(query: str, location: str) -> List[Dict[str, Any]]:
    """Free OpenStreetMap Nominatim search as a reliable non-Playwright fallback."""
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
    Completely free keyless fallback search using DuckDuckGo Local Map search API.
    Chain: DDG Local → OpenStreetMap Nominatim → Playwright (last resort)
    """
    from app.services import automation_worker
    if automation_worker.cancel_requested:
        return []
        
    # 1. Try DuckDuckGo Local (fast, free)
    logger.info(f"Free Fallback: Querying DuckDuckGo Local Maps via urllib for '{query}' in '{location}'")
    try:
        companies = await asyncio.to_thread(query_ddg_local_sync, query, location)
        if companies:
            logger.info(f"Free Fallback: DuckDuckGo Local found {len(companies)} businesses successfully!")
            return companies
    except Exception as e:
        logger.warning(f"Free Fallback: DuckDuckGo Local API search failed: {e}. Trying Nominatim...")

    if automation_worker.cancel_requested:
        return []

    # 2. Try OpenStreetMap Nominatim (reliable, no browser needed)
    nom_results = await query_nominatim_businesses(query, location)
    if nom_results:
        return nom_results

    if automation_worker.cancel_requested:
        return []

    # 3. Final fallback: Playwright (only if browser is installed)
    logger.info(f"Playwright Fallback: Querying Google Maps: https://www.google.com/maps/search/{urllib.parse.quote_plus(query + ' ' + location)}")
    return await asyncio.to_thread(scrape_google_maps_in_thread, query, location)


async def search_companies_google_places(
    query: str, 
    location: str = "", 
    page_token: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Use optimized search strategy to fetch, expand, query and deduplicate local businesses.
    """
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


