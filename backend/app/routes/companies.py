from pydantic import BaseModel
from fastapi import APIRouter, Depends, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict, Optional

from app.database.connection import get_database
from app.repositories.company import CompanyRepository
from app.services.company import CompanyService
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate, CompanyListResponse
from app.auth.deps import get_current_user
from app.services.places import search_companies_google_places
from app.services.email_scraper import find_email_for_company
from app.services.email_sender import send_smtp_email
from app.services.llm_service import generate_ai_email_template, clean_first_name_with_ai
from app.services.whois_scraper import extract_email_from_whois
from app.services.email_verifier import verify_email_existence

router = APIRouter()

# Dependency to get CompanyService
def get_company_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> CompanyService:
    return CompanyService(CompanyRepository(db))

class CampaignRequest(BaseModel):
    subject_template: str
    body_template: str
    company_id: Optional[str] = None

class AITemplateRequest(BaseModel):
    agency_name: str
    services: str
    portfolio: str
    cta: str

@router.post("/ai-template", response_model=Dict[str, str])
async def ai_generate_template(
    payload: AITemplateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Generates an email template using OpenRouter AI based on user company details."""
    from app.repositories.automation import AutomationRepository
    auto_repo = AutomationRepository(db)
    auto_settings = await auto_repo.get_settings()
    custom_key = auto_settings.get("openrouter_api_key")
    
    template_data = await generate_ai_email_template(
        agency_name=payload.agency_name,
        services=payload.services,
        portfolio=payload.portfolio,
        cta=payload.cta,
        custom_api_key=custom_key
    )
    return template_data

@router.post("/send-campaign", response_model=Dict[str, Any])
async def send_campaign(
    campaign_in: CampaignRequest,
    company_service: CompanyService = Depends(get_company_service),
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """
    Sends personalized cold emails. If company_id is provided, sends only to that 
    specific lead. Otherwise, sends to all saved leads that have an email 
    and a 'Pending' status.
    """
    from app.repositories.automation import AutomationRepository
    auto_repo = AutomationRepository(db)
    auto_settings = await auto_repo.get_settings()
    custom_openrouter_key = auto_settings.get("openrouter_api_key")
    
    if campaign_in.company_id:
        # Target only this specific company
        try:
            target_company = await company_service.get_company(campaign_in.company_id)
            companies = [target_company]
        except Exception:
            companies = []
    else:
        # Fetch all companies from DB
        companies = await company_service.company_repo.get_all(
            skip=0, 
            limit=1000, 
            query={"email": {"$ne": None}, "status": "Pending"}
        )
    
    sent_count = 0
    failed_count = 0
    
    for company in companies:
        email_addr = company.get("email")
        if not email_addr:
            continue
            
        # Parse template variables
        co_name = company.get("name", "there")
        co_website = company.get("website", "your business") or "your business"
        co_industry = company.get("industry", "business") or "business"
        co_location = company.get("location", "your area") or "your area"
        co_email_source = company.get("email_source")
        
        # Resolve smart greeting name using AI first (falls back to rules if API key is missing or fails)
        greeting_name = None
        if email_addr and co_name:
            greeting_name = await clean_first_name_with_ai(email_addr, co_name, custom_api_key=custom_openrouter_key)
            
        if not greeting_name:
            greeting_name = "Team"
            if co_name:
                personal_email = True
                if email_addr:
                    prefix = email_addr.split("@")[0].lower()
                    for generic in ["info", "contact", "support", "hello", "sales", "admin", "jobs", "office", "team", "server"]:
                        if prefix.startswith(generic):
                            personal_email = False
                            break
                    if personal_email:
                        name_part = prefix.replace(".", "_").replace("-", "_").split("_")[0]
                        if len(name_part) > 2:
                            greeting_name = name_part.capitalize()
                            personal_email = True
                        else:
                            personal_email = False
                
                if not personal_email:
                    business_keywords = ["bakery", "restaurant", "llp", "plumbing", "inc", "co", "corp", "tech", "services", "clinic", "dent", "shop", "salon", "group", "ltd", "limited", "firm", "agency", "bar", "cafe", "pizzeria"]
                    lower_name = co_name.lower()
                    is_business = any(k in lower_name for k in business_keywords)
                    if is_business:
                        words = co_name.split()
                        if len(words) > 3:
                            greeting_name = " ".join(words[:2]) + " Team"
                        else:
                            greeting_name = co_name + " Team"
                    else:
                        greeting_name = co_name.split()[0]
        
        # Resolve current_platform
        current_platform = "social media profiles"
        if co_email_source == "Facebook":
            current_platform = "Facebook"
        elif co_email_source == "Instagram":
            current_platform = "Instagram"
        elif co_email_source == "LinkedIn":
            current_platform = "LinkedIn"
        elif company.get("website"):
            current_platform = "directories and online listings"
            
        # Resolve service_type
        service_type = "services and offerings"
        ind_lower = co_industry.lower()
        if "bakery" in ind_lower or "bake" in ind_lower:
            service_type = "bakery products and custom cakes"
        elif "restaurant" in ind_lower or "food" in ind_lower or "cafe" in ind_lower:
            service_type = "menu offerings and dining experience"
        elif "plumb" in ind_lower:
            service_type = "plumbing services and rapid repairs"
        elif "dent" in ind_lower or "clinic" in ind_lower:
            service_type = "dental treatments and patient care"
        elif "salon" in ind_lower or "hair" in ind_lower or "beauty" in ind_lower:
            service_type = "beauty treatments and styling services"
            
        subject = campaign_in.subject_template.replace("{{company}}", co_name)\
                                              .replace("{{first_name}}", greeting_name)\
                                              .replace("{{website}}", co_website)\
                                              .replace("{{industry}}", co_industry)\
                                              .replace("{{location}}", co_location)\
                                              .replace("{{current_platform}}", current_platform)\
                                              .replace("{{service_type}}", service_type)
                                              
        body = campaign_in.body_template.replace("{{company}}", co_name)\
                                        .replace("{{first_name}}", greeting_name)\
                                        .replace("{{website}}", co_website)\
                                        .replace("{{industry}}", co_industry)\
                                        .replace("{{location}}", co_location)\
                                        .replace("{{current_platform}}", current_platform)\
                                        .replace("{{service_type}}", service_type)
                                        
        # Convert simple linebreaks to HTML
        html_body = f"<html><body><p>{body.replace(chr(10), '<br>')}</p></body></html>"
        
        # Send email
        success = await send_smtp_email(email_addr, subject, html_body, smtp_config=auto_settings)
        
        if success:
            sent_count += 1
            # Update status to Emailed
            await company_service.update_company(company["id"], CompanyUpdate(status="Emailed"))
        else:
            failed_count += 1
            
    return {"sent_count": sent_count, "failed_count": failed_count}

def is_social_url(url: str) -> bool:
    if not url:
        return False
    social_domains = [
        "facebook.com", "instagram.com", "linkedin.com", "twitter.com", 
        "x.com", "youtube.com", "yelp.com", "t.co", "pinterest.com"
    ]
    url_lower = url.lower()
    return any(domain in url_lower for domain in social_domains)

@router.get("/find-email", response_model=Dict[str, Any])
async def find_company_email(
    company_name: str,
    location: str = "",
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """
    Smarter agent to find company email.
    Uses Playwright web-search, falls back to raw WHOIS registry checks,
    and runs SMTP Handshake Verification to guarantee delivery.
    """
    # 1. Playwright Web-search (Yahoo + Website Crawling)
    email, website_url, email_source = await find_email_for_company(company_name, location)
    
    # 2. Fallback: WHOIS Registry Email Crawler (if website exists but no email was found)
    if not email and website_url:
        whois_data = extract_email_from_whois(website_url)
        if whois_data:
            email, email_source = whois_data
            
    # 3. SMTP Verification Check (to prevent spam & bounce)
    if email:
        is_valid, reason = await verify_email_existence(email)
        if not is_valid:
            # If SMTP check fails, reject this address so the user doesn't bounce
            email = None
            email_source = None
            
    # Filter out social links from being returned as a real company website
    if website_url and is_social_url(website_url):
        website_url = None

    return {"email": email, "website_url": website_url, "email_source": email_source}

@router.get("/search-live", response_model=Dict[str, Any])
async def search_live_companies(
    query: str,
    location: str = "",
    pageToken: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Search for companies live using Google Places API with Playwright direct-scraping fallback and pagination."""
    results, next_page_token = await search_companies_google_places(query, location, page_token=pageToken)
    return {"data": results, "nextPageToken": next_page_token}

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_in: CompanyCreate,
    company_service: CompanyService = Depends(get_company_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Create new company lead."""
    return await company_service.create_company(company_in)

@router.get("/", response_model=CompanyListResponse)
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    company_service: CompanyService = Depends(get_company_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Retrieve companies with pagination."""
    companies = await company_service.get_companies(skip=skip, limit=limit)
    total_count = await company_service.get_total_count()
    return {"total_count": total_count, "data": companies}

@router.get("/{id}", response_model=CompanyResponse)
async def get_company(
    id: str,
    company_service: CompanyService = Depends(get_company_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Get a specific company by ID."""
    return await company_service.get_company(id)

@router.put("/{id}", response_model=CompanyResponse)
async def update_company(
    id: str,
    company_in: CompanyUpdate,
    company_service: CompanyService = Depends(get_company_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Any:
    """Update a company."""
    return await company_service.update_company(id, company_in)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    id: str,
    company_service: CompanyService = Depends(get_company_service),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a company."""
    await company_service.delete_company(id)
