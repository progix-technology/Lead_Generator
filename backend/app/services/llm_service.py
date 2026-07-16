import urllib.request
import json
import logging
import asyncio
from typing import Dict, Optional, Tuple
from app.config.settings import settings

logger = logging.getLogger(__name__)

def make_openrouter_request(prompt: str, response_format_json: bool = False, max_tokens: int = 500, custom_api_key: Optional[str] = None) -> Optional[str]:
    api_key = custom_api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        logger.warning("No OpenRouter API key provided (neither dynamic nor .env).")
        return None
        
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://leadgenpro.local",
        "X-Title": "LeadGen Pro"
    }
    
    models = [
        "google/gemini-2.5-flash",
        "meta-llama/llama-3.2-3b-instruct:free",
        "google/gemma-4-31b-it:free"
    ]
    
    last_error = ""
    for model in models:
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens
        }
        if response_format_json and "llama" not in model:
            data["response_format"] = {"type": "json_object"}
            
        try:
            req_body = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=4) as response:
                res_body = response.read().decode("utf-8")
                res_data = json.loads(res_body)
                choices = res_data.get("choices", [])
                if choices:
                    content = choices[0]["message"]["content"]
                    # Double check if choice had a mid-stream rate limit error
                    if choices[0].get("finish_reason") == "error" or not content or len(content.strip()) < 2:
                        logger.warning(f"Model {model} returned error/empty content in OpenRouter stream. Trying next...")
                        continue
                    return content
        except Exception as e:
            logger.warning(f"OpenRouter model {model} failed: {e}. Trying next...")
            last_error = str(e)
            
    logger.error(f"All OpenRouter models failed. Last error: {last_error}")
    return None

def get_fallback_template(agency_name: str, services: str, cta: str) -> Dict[str, str]:
    return {
        "subject": "Quick question for {{company}} about their website",
        "body": f"Hi {{first_name}},\n\nI noticed your website {{website}} has a few technical issues that might be affecting your search rankings.\n\nAt {agency_name}, we specialize in {services} and help local businesses get more clients.\n\nWould you be open to {cta}?\n\nBest,\nTeam {agency_name}"
    }

def generate_ai_email_template_sync(
    agency_name: str,
    services: str,
    portfolio: str,
    cta: str,
    custom_api_key: Optional[str] = None
) -> Dict[str, str]:
    """Generates a personalized cold email template using OpenRouter AI."""
    api_key = custom_api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        logger.warning("No OpenRouter API key configured. Falling back to default static template.")
        return get_fallback_template(agency_name, services, cta)
        
    prompt = f"""
    Write a highly professional, short cold outreach email template for a agency.
    Our details:
    - Agency Name: {agency_name}
    - Core Services: {services}
    - Special Case Study / Portfolio / Offer details: {portfolio}
    - Call to Action (CTA): {cta}

    The output MUST be a JSON object containing:
    1. "subject": "a catchy subject line targeting the business"
    2. "body": "a persuasive, short email body template"

    You MUST use these exact bracket placeholders in the generated text:
    - {{{{first_name}}}} for the prospect's first name
    - {{{{company}}}} for the prospect's company name
    - {{{{website}}}} for the prospect's website url
    - {{{{industry}}}} for the prospect's industry
    - {{{{location}}}} for the prospect's location

    Guidelines:
    - Keep it short, crisp and clear.
    - Avoid generic spam phrases.
    - Sound genuine, helpful and real.
    
    Return ONLY a JSON block, nothing else. Format:
    {{"subject": "...", "body": "..."}}
    """
    
    res = make_openrouter_request(prompt, response_format_json=True, max_tokens=600, custom_api_key=api_key)
    if res:
        try:
            clean_res = res.strip()
            if clean_res.startswith("```"):
                clean_res = clean_res.split("json")[-1].split("```")[0].strip()
            parsed = json.loads(clean_res)
            return {
                "subject": parsed.get("subject", "Quick question about {{website}}"),
                "body": parsed.get("body", "")
            }
        except Exception as e:
            logger.error(f"Failed to parse AI template JSON output: {e}")
            
    return get_fallback_template(agency_name, services, cta)

async def generate_ai_email_template(
    agency_name: str,
    services: str,
    portfolio: str,
    cta: str,
    custom_api_key: Optional[str] = None
) -> Dict[str, str]:
    """Asynchronous wrapper for OpenRouter template generation."""
    return await asyncio.to_thread(generate_ai_email_template_sync, agency_name, services, portfolio, cta, custom_api_key)

def clean_first_name_with_ai_sync(email: str, company_name: str, custom_api_key: Optional[str] = None) -> Optional[str]:
    """Uses OpenRouter to extract/format a clean first name or fallback team name."""
    prompt = f"""
    Given the business name "{company_name}" and their email address "{email}", 
    determine a clean, professional, personalized greeting name to use after "Hi " or "Dear ".
    
    Instructions:
    1. If the email prefix looks like a personal name (e.g. "john.smith@gmail.com" or "kazimkilic81@gmail.com" or "sarah@company.com"), 
       extract just the clean personal first name capitalized (e.g. "John", "Kazim", "Sarah"). Strip any numbers, suffixes or special characters.
    2. If the email prefix is generic (e.g. "info@", "contact@", "support@", "admin@", "sales@", "server@", "hello@", "team@"), 
       use the company name + " Team" (e.g. "Gerson Bakery Team" or "Narala Bakery Team").
    3. Keep it brief.
    
    The output MUST be a JSON object containing a single key "first_name":
    {{"first_name": "extracted_name"}}
    
    Return ONLY a JSON block, nothing else. Format:
    {{"first_name": "..."}}
    """
    
    res = make_openrouter_request(prompt, response_format_json=True, max_tokens=100, custom_api_key=custom_api_key)
    if res:
        try:
            clean_res = res.strip()
            if clean_res.startswith("```"):
                clean_res = clean_res.split("json")[-1].split("```")[0].strip()
            parsed = json.loads(clean_res)
            return parsed.get("first_name")
        except Exception as e:
            logger.error(f"Failed to parse AI greeting JSON output: {e}")
    return None

async def clean_first_name_with_ai(email: str, company_name: str, custom_api_key: Optional[str] = None) -> Optional[str]:
    return await asyncio.to_thread(clean_first_name_with_ai_sync, email, company_name, custom_api_key)

def generate_ai_search_query_sync(recent_targets: list, custom_api_key: Optional[str] = None) -> Tuple[str, str]:
    """Uses OpenRouter to recommend a high-converting local service category and location."""
    api_key = custom_api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        logger.warning("No OpenRouter API key provided for target search query generation.")
        return "Plumbers", "Sacramento, CA"

    prompt = f"""
    We are scraping Google Maps to find US businesses that DO NOT have a website, so we can pitch them website design services.
    Recommend a target US local business niche/category and a specific target US city and state (e.g. "Locksmiths", "Davenport, IA") where there is a high probability of finding small businesses without websites.
    
    You MUST NOT choose any of these recently targeted combinations (avoid them!): {recent_targets}
    
    Guidelines for high website-less lead conversion:
    1. Target a balanced mix of these two business types:
       - HIGH-PAYING PREMIUM CLIENTS (High ticket value): Restaurants, Cafes, Bakeries, Laundry Services, Bars, Gyms, Spas, Hotels, Travel Agencies, Dentists, Biscuit Factories. (Focus on local, independent, or newly opened ones that might lack websites).
       - EASY VOLUME CLIENTS (Often run without websites): Locksmiths, Towing Services, Junk Removal, Tree Services, Appliance Repair, Drywall Contractors, Concrete Contractors, Fence Contractors, Painting Contractors, Window Cleaning, Carpet Cleaning.
    2. Select smaller or mid-sized US cities, towns, or outer suburbs (population 30k - 150k) in states like TX, FL, NC, OH, GA, MI, PA, etc. 
       - Smaller towns and rural-suburban hubs have much lower website adoption than major metropolitan or tech-heavy cities.
    3. STRICT RULE: You MUST NOT recommend any technology, IT services, SEO, digital marketing, software development, web design, or tech consulting categories. We only target brick-and-mortar local businesses, contractors, medical, or lifestyle niches.
    
    The output MUST be a JSON object containing:
    1. "category": "Category Name"
    2. "location": "City, State"
    
    Return ONLY a JSON block, nothing else. Format:
    {{"category": "Locksmiths", "location": "Davenport, IA"}}
    """

    res = make_openrouter_request(prompt, response_format_json=True, max_tokens=200, custom_api_key=api_key)
    if res:
        try:
            clean_res = res.strip()
            if clean_res.startswith("```"):
                clean_res = clean_res.split("json")[-1].split("```")[0].strip()
            parsed = json.loads(clean_res)
            category = parsed.get("category", "").strip()
            location = parsed.get("location", "").strip()
            if category and location:
                return category, location
        except Exception as e:
            logger.error(f"Failed to parse AI search query JSON: {e}")

    # Return None, None on failure to let the worker fall back to the user's manually configured rotation list
    return None, None

async def generate_ai_search_query(recent_targets: list, custom_api_key: Optional[str] = None) -> Tuple[str, str]:
    """Asynchronously calls generate_ai_search_query_sync."""
    return await asyncio.to_thread(generate_ai_search_query_sync, recent_targets, custom_api_key)

