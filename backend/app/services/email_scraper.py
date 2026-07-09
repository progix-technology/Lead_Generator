import logging
import re
import asyncio
import urllib.parse
import sys
from typing import Optional, List, Tuple
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

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

async def scrape_url_for_emails(page, url: str) -> List[str]:
    """Visits a URL using Playwright and extracts all unique valid emails."""
    logger.info(f"Agent: Scanning {url}...")
    try:
        # Ignore javascript protocols or empty inputs
        if not url.startswith(('http://', 'https://')):
            return []
            
        await page.goto(url, wait_until="domcontentloaded", timeout=12000)
        await asyncio.sleep(2) # Give dynamic JavaScript time to render
        
        content = await page.content()
        matches = EMAIL_REGEX.findall(content)
        
        valid_emails = [m.lower() for m in matches if is_valid_email(m)]
        return list(set(valid_emails))
    except Exception as e:
        logger.warning(f"Error scraping {url}: {e}")
        return []

async def run_playwright_scraper(company_name: str, location: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Internal Playwright Scraper logic that runs inside the dedicated loop thread.
    Returns: Tuple[Optional[str], Optional[str], Optional[str]] -> (email, website_url, email_source)
    """
    clean_name = company_name.replace("'", "").replace('"', '')
    search_query = urllib.parse.quote_plus(f'{clean_name} {location}')
    yahoo_url = f"https://search.yahoo.com/search?p={search_query}"
    
    logger.info(f"Agent Thread: Starting search for '{clean_name}' on Yahoo")
    
    facebook_url = None
    instagram_url = None
    linkedin_url = None
    website_url = None

    # Social links discovered by crawling the company's website
    discovered_facebook_url = None
    discovered_instagram_url = None

    async def extract_socials_from_page(page_obj) -> Tuple[Optional[str], Optional[str]]:
        """Helper to find Facebook & Instagram links on a page."""
        fb, ig = None, None
        try:
            links = await page_obj.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('a[href]'));
                return anchors.map(a => a.href);
            }""")
            for link in links:
                if not link.startswith(('http://', 'https://')):
                    continue
                if 'facebook.com' in link and '/public/' not in link and '/events/' not in link:
                    fb = link
                elif 'instagram.com' in link and '/p/' not in link:
                    ig = link
        except Exception as e:
            logger.warning(f"Error extracting socials: {e}")
        return fb, ig

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # 1. Search Yahoo
            try:
                await page.goto(yahoo_url, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                
                links = await page.locator("a[href]").evaluate_all("elements => elements.map(e => e.href)")
                
                # Categorize found links
                for link in links:
                    if not link.startswith(('http://', 'https://')):
                        continue
                    if any(domain in link for domain in ['yahoo.com', 'yahoo.co', 'yimg.com', 'microsoft.com', 'google.com']):
                        continue
                        
                    if 'facebook.com' in link and not facebook_url and '/public/' not in link and '/events/' not in link:
                        facebook_url = link
                    elif 'instagram.com' in link and not instagram_url and '/p/' not in link:
                        instagram_url = link
                    elif 'linkedin.com' in link and not linkedin_url and ('/company/' in link or '/in/' in link):
                        linkedin_url = link
                    elif not any(s in link for s in [
                        'facebook', 'instagram', 'linkedin', 'youtube', 'yelp', 'twitter', 'tiktok', 
                        'mapbox', 'openstreetmap', 'here.com', 'google.com/maps', 'chamberofcommerce',
                        'yellowpages', 'yellowbook', 'manta', 'local.com', 'mapquest', 'tripadvisor',
                        'foursquare', 'bbb.org', 'dandb.com', 'zoominfo', 'whitepages', 'groupon',
                        'restaurantguru', 'zmenu', 'menupix', 'sirved', 'countyoffice', 'opendi',
                        'bizapedia', 'cylex', 'sluurpy', 'restaurantji', 'nicelocal', 'yell.com', 
                        '192.com', 'ubereats', 'just-eat', 'deliveroo', 'menuwithprice', 'find-us-here', 
                        'allbusiness', 'telepages', 'bark.com'
                    ]):
                        if not website_url:
                            website_url = link

            except Exception as e:
                logger.warning(f"Yahoo search query failed: {e}")

            # 2. Deep scrape direct social links first
            # If facebook_url is missing, try a targeted Yahoo search to find it!
            if not facebook_url:
                try:
                    logger.info(f"Agent: Facebook URL not in general search. Executing targeted query for '{clean_name}'")
                    fb_search_query = urllib.parse.quote_plus(f'{clean_name} {location} facebook')
                    fb_search_url = f"https://search.yahoo.com/search?p={fb_search_query}"
                    await page.goto(fb_search_url, wait_until="domcontentloaded", timeout=12000)
                    await asyncio.sleep(1.5)
                    fb_links = await page.locator("a[href]").evaluate_all("elements => elements.map(e => e.href)")
                    for l in fb_links:
                        if 'facebook.com' in l and '/public/' not in l and '/events/' not in l:
                            facebook_url = l
                            break
                except Exception as e:
                    logger.warning(f"Targeted Facebook search failed: {e}")

            if facebook_url:
                clean_fb = facebook_url.split('?')[0].rstrip('/')
                fb_pages = [clean_fb, f"{clean_fb}/about", f"{clean_fb}/about_details"]
                for fb_page in fb_pages:
                    emails = await scrape_url_for_emails(page, fb_page)
                    if emails:
                        await browser.close()
                        return emails[0], website_url, "Facebook"

            # If instagram_url is missing, try a targeted Yahoo search to find it!
            if not instagram_url:
                try:
                    logger.info(f"Agent: Instagram URL not in general search. Executing targeted query for '{clean_name}'")
                    ig_search_query = urllib.parse.quote_plus(f'{clean_name} {location} instagram')
                    ig_search_url = f"https://search.yahoo.com/search?p={ig_search_query}"
                    await page.goto(ig_search_url, wait_until="domcontentloaded", timeout=12000)
                    await asyncio.sleep(1.5)
                    ig_links = await page.locator("a[href]").evaluate_all("elements => elements.map(e => e.href)")
                    for l in ig_links:
                        if 'instagram.com' in l and '/p/' not in l:
                            instagram_url = l
                            break
                except Exception as e:
                    logger.warning(f"Targeted Instagram search failed: {e}")

            if instagram_url:
                emails = await scrape_url_for_emails(page, instagram_url)
                if emails:
                    await browser.close()
                    return emails[0], website_url, "Instagram"

            if linkedin_url:
                clean_li = linkedin_url.split('?')[0].rstrip('/')
                li_pages = [clean_li]
                if '/company/' in clean_li:
                    li_pages.append(f"{clean_li}/about")
                for li_page in li_pages:
                    emails = await scrape_url_for_emails(page, li_page)
                    if emails:
                        await browser.close()
                        return emails[0], website_url, "LinkedIn"

            # 3. Check Website (and extract potential social links if no email is found)
            if website_url:
                emails = await scrape_url_for_emails(page, website_url)
                if emails:
                    await browser.close()
                    return emails[0], website_url, "Website"
                
                # Check homepage for social links
                fb_disc, ig_disc = await extract_socials_from_page(page)
                if fb_disc:
                    discovered_facebook_url = fb_disc
                if ig_disc:
                    discovered_instagram_url = ig_disc

                # Find and crawl Contact/About links
                try:
                    logger.info("Agent: Homepage scanned. Looking for contact/about links...")
                    internal_links = await page.evaluate("""() => {
                        const anchors = Array.from(document.querySelectorAll('a[href]'));
                        const matches = anchors.filter(a => {
                            const text = (a.innerText || '').toLowerCase();
                            const href = (a.getAttribute('href') || '').toLowerCase();
                            return text.includes('contact') || text.includes('about') || text.includes('support') ||
                                   href.includes('contact') || href.includes('about') || href.includes('support');
                        });
                        return [...new Set(matches.map(a => a.href))];
                    }""")
                    
                    for deep_link in internal_links[:3]:
                        if deep_link.startswith(('http://', 'https://')):
                            emails = await scrape_url_for_emails(page, deep_link)
                            if emails:
                                await browser.close()
                                return emails[0], website_url, "Website"
                            
                            # Also check contact pages for social links
                            fb_disc, ig_disc = await extract_socials_from_page(page)
                            if fb_disc and not discovered_facebook_url:
                                discovered_facebook_url = fb_disc
                            if ig_disc and not discovered_instagram_url:
                                discovered_instagram_url = ig_disc
                except Exception as e:
                    logger.warning(f"Error crawl-searching website internal links: {e}")

            # 4. Scrape Discovered Socials if still no email found
            if discovered_facebook_url:
                logger.info(f"Agent: Trying Facebook URL discovered from website -> {discovered_facebook_url}")
                clean_fb = discovered_facebook_url.split('?')[0].rstrip('/')
                fb_pages = [clean_fb, f"{clean_fb}/about", f"{clean_fb}/about_details"]
                for fb_page in fb_pages:
                    emails = await scrape_url_for_emails(page, fb_page)
                    if emails:
                        await browser.close()
                        return emails[0], website_url or discovered_facebook_url, "Facebook"

            if discovered_instagram_url:
                logger.info(f"Agent: Trying Instagram URL discovered from website -> {discovered_instagram_url}")
                emails = await scrape_url_for_emails(page, discovered_instagram_url)
                if emails:
                    await browser.close()
                    return emails[0], website_url or discovered_instagram_url, "Instagram"

            await browser.close()
            
    except Exception as e:
        logger.error(f"Playwright pipeline crash inside thread: {e}")

    return None, website_url, None

def find_email_for_company_in_thread(company_name: str, location: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Synchronous worker running in a separate OS thread to execute the Playwright coroutine
    with a fresh ProactorEventLoop.
    """
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(run_playwright_scraper(company_name, location))
    finally:
        loop.close()

async def find_email_for_company(company_name: str, location: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Public API of the email scraper.
    Delegates execution to a separate thread to prevent asyncio loop clashes in Uvicorn on Windows.
    """
    return await asyncio.to_thread(find_email_for_company_in_thread, company_name, location)
