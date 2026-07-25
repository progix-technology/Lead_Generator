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
        "google/gemini-2.0-pro-exp-02-05:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "nvidia/llama-3.1-nemotron-70b-instruct:free",
        "google/gemini-2.5-flash"
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
    3. If the email prefix is the company name or a variation of it (e.g. "bayshoretransmissions" for "Bayshore Transmissions"), 
       use the EXACT company name + " Team" (e.g. "Bayshore Transmissions Team"). Do NOT treat it as a person's name.
    4. Keep it brief.
    
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
    We are scraping Google Maps to find local businesses globally (with a heavy focus on USA, UK, Canada, Australia, and UAE/Dubai) that DO NOT have a website, so we can pitch them website design services.
    Recommend a target local business niche/category and a specific target city/state/country (e.g. "Locksmiths", "Davenport, IA, USA" or "Attar and Perfume Shops", "Dubai, UAE") where there is a high probability of finding small businesses without websites.
    
    You MUST NOT choose any of these recently targeted combinations (avoid them!): {recent_targets}
    
    Guidelines for high website-less lead conversion:
    1. Target a balanced mix of these two business types:
       - HIGH-PAYING PREMIUM CLIENTS (High ticket value): Attar and Perfume Shops, Dates and Sweets Shops, Restaurants, Cafes, Bakeries, Spa, Gyms, Travel Agencies, Dentists, Biscuit Factories. (Focus on local, independent shops that might lack websites).
       - EASY VOLUME CLIENTS (Often run without websites): Locksmiths, Towing Services, Junk Removal, Tree Services, Appliance Repair, Drywall Contractors, Concrete Contractors, Fence Contractors, Painting Contractors, Window Cleaning, Carpet Cleaning.
    2. Select smaller or mid-sized cities/suburbs, or specific busy commercial districts in major hubs like Dubai (e.g. "Deira, Dubai" or "Bur Dubai").
    3. STRICT RULE: You MUST NOT recommend any technology, IT services, SEO, digital marketing, software development, web design, or tech consulting categories. We only target brick-and-mortar local businesses, contractors, medical, or lifestyle niches.
    
    The output MUST be a JSON object containing:
    1. "category": "Category Name"
    2. "location": "City, State/Country"
    
    Return ONLY a JSON block, nothing else. Format:
    {{"category": "Attar and Perfume Shops", "location": "Deira, Dubai, UAE"}}
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

def generate_ai_redesign_email_sync(
    company_name: str,
    first_name: str,
    website: str,
    industry: str,
    location: str,
    suggestions: list,
    performance_score: int,
    ui_score: int,
    seo_score: int,
    custom_api_key: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """Uses OpenRouter to write a highly personalized email highlighting the specific flaws found on the website."""
    api_key = custom_api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        return None

    flaws_text = "\\n- ".join(suggestions)
    prompt = f"""
    You are a professional web designer writing a cold email to '{first_name}' at '{company_name}', a {industry} business in {location}.
    We just ran a technical audit on their website ({website}) and found some critical issues:
    - Performance/Speed Score: {performance_score}/100
    - UI/UX Score: {ui_score}/100
    - SEO Score: {seo_score}/100
    
    Here are the main flaws we found:
    - {flaws_text}
    
    Write a short, highly personalized, friendly, and persuasive cold email.
    1. Start by complementing them or mentioning you were looking at their business.
    2. Gently point out 1-2 of the specific flaws found above (don't sound robotic or like a generic audit report).
    3. Conclude by offering to fix these issues with a modern redesign to help them get more local clients.
    4. Keep it concise (under 120 words). Don't use overly formal language.
    
    The output MUST be a JSON object containing:
    1. "subject": "a catchy, non-salesy subject line"
    2. "body": "the personalized email body text (use simple text, no HTML tags, use \\n for newlines)"
    
    Return ONLY a JSON block, nothing else. Format:
    {{"subject": "...", "body": "..."}}
    """
    
    res = make_openrouter_request(prompt, response_format_json=True, max_tokens=400, custom_api_key=api_key)
    if res:
        try:
            clean_res = res.strip()
            if clean_res.startswith("```"):
                clean_res = clean_res.split("json")[-1].split("```")[0].strip()
            parsed = json.loads(clean_res)
            if parsed.get("subject") and parsed.get("body"):
                return {
                    "subject": parsed["subject"],
                    "body": parsed["body"]
                }
        except Exception as e:
            logger.error(f"Failed to parse AI redesign email JSON: {e}")
            
    return None

async def generate_ai_redesign_email(
    company_name: str,
    first_name: str,
    website: str,
    industry: str,
    location: str,
    suggestions: list,
    performance_score: int,
    ui_score: int,
    seo_score: int,
    custom_api_key: Optional[str] = None
) -> Optional[Dict[str, str]]:
    return await asyncio.to_thread(
        generate_ai_redesign_email_sync, company_name, first_name, website, industry, location, 
        suggestions, performance_score, ui_score, seo_score, custom_api_key
    )

