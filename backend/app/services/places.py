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
            
            # Google Maps listings links have class "hfpxzc"
            listings = await page.locator("a.hfpxzc").all()
            
            for item in listings[:20]:  # Scrape top 20 leads
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://duckduckgo.com/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=12.0) as response:
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

async def scrape_google_maps_fallback(query: str, location: str) -> List[Dict[str, Any]]:
    """
    Completely free keyless fallback search using DuckDuckGo Local Map search API.
    If it fails, falls back to direct Playwright scraping in an independent thread.
    """
    logger.info(f"Free Fallback: Querying DuckDuckGo Local Maps via urllib for '{query}' in '{location}'")
    try:
        companies = await asyncio.to_thread(query_ddg_local_sync, query, location)
        if companies:
            logger.info(f"Free Fallback: DuckDuckGo Local found {len(companies)} businesses successfully!")
            return companies
    except Exception as e:
        logger.warning(f"Free Fallback: DuckDuckGo Local API search failed: {e}. Trying Playwright...")

    # Final fallback if DDG Local fails
    return await asyncio.to_thread(scrape_google_maps_in_thread, query, location)

async def search_companies_google_places(
    query: str, 
    location: str = "", 
    page_token: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Use Google Places API (New) to search for companies (Text Search).
    If API quota is exhausted (429) or Key is missing, falls back to direct Playwright scraper.
    """
    # Fallback immediately if Places API key is missing
    if not settings.GOOGLE_PLACES_API_KEY:
        logger.warning("GOOGLE_PLACES_API_KEY missing. Falling back to direct Google Maps crawling.")
        fallback_results = await scrape_google_maps_fallback(query, location)
        return fallback_results, None

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.primaryTypeDisplayName,nextPageToken"
    }

    bbox = await geocode_location(location)
    
    payload = {
        "pageSize": 20
    }
    
    if bbox:
        south_lat, north_lat, west_lng, east_lng = bbox
        payload["textQuery"] = query
        payload["locationRestriction"] = {
            "rectangle": {
                "low": {"latitude": south_lat, "longitude": west_lng},
                "high": {"latitude": north_lat, "longitude": east_lng}
            }
        }
    else:
        # Avoid using 'in' in searchText queries to bypass Google semantic query parsing failures
        payload["textQuery"] = f"{query}, {location}" if location else query
        
    if page_token:
        payload["pageToken"] = page_token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=12.0)
            
            # Fallback if API key is rate limited / quota exhausted
            if response.status_code == 429 or "quota" in response.text.lower():
                logger.warning(f"Google Places API quota exceeded ({response.status_code}). Triggering Playwright fallback.")
                fallback_results = await scrape_google_maps_fallback(query, location)
                return fallback_results, None
                
            if response.status_code != 200:
                logger.error(f"Google Places API error ({response.status_code}): {response.text}")
                fallback_results = await scrape_google_maps_fallback(query, location)
                return fallback_results, None
                
            data = response.json()
            places = data.get("places", [])
            if not places:
                logger.info("Google Places API returned 0 results. Triggering free fallback.")
                fallback_results = await scrape_google_maps_fallback(query, location)
                return fallback_results, None
                
            next_page_token = data.get("nextPageToken")
            
            companies = []
            for place in places:
                company = {
                    "name": place.get("displayName", {}).get("text", "Unknown"),
                    "industry": place.get("primaryTypeDisplayName", {}).get("text", query.capitalize()),
                    "address": place.get("formattedAddress", ""),
                    "phone_number": place.get("nationalPhoneNumber", ""),
                    "website_url": place.get("websiteUri", ""),
                    "rating": place.get("rating"),
                    "rating_count": place.get("userRatingCount")
                }
                companies.append(company)
                
            return companies, next_page_token
            
    except Exception as e:
        logger.error(f"Failed to fetch data from Google Places: {str(e)}. Attempting Playwright fallback.")
        fallback_results = await scrape_google_maps_fallback(query, location)
        return fallback_results, None

