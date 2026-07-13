from fastapi import HTTPException, status
from typing import Dict, Any, List
import httpx
import time
import re
from datetime import datetime

from app.repositories.audit import WebsiteAuditRepository
from app.repositories.company import CompanyRepository
from app.schemas.audit import WebsiteAuditCreate, WebsiteAuditUpdate

async def perform_live_website_audit(url: str) -> Dict[str, Any]:
    """
    Crawls a target website, analyzes response speed, extracts key HTML elements (SEO/UX),
    and computes scores out of 100 for SEO, Speed/Performance, and UI/Mobile friendliness.
    """
    start_time = time.time()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    seo_score = 100
    ui_score = 100
    performance_score = 100
    suggestions = []
    
    try:
        # Use HTTPX with SSL verification turned off to prevent SSL handshake errors blocking our audit
        async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers=headers, timeout=6.0)
            load_time = time.time() - start_time
            
            # 1. Check HTTP Status
            if response.status_code >= 400:
                suggestions.append(f"Website returned an error status code: {response.status_code}")
                seo_score = max(0, seo_score - 40)
                performance_score = max(0, performance_score - 50)
                
            # 2. Performance (Speed) Scoring
            if load_time < 1.2:
                performance_score = 100
            elif load_time < 2.5:
                performance_score = 85
                suggestions.append(f"Load time is slightly high ({load_time:.2f}s). Optimize page assets.")
            elif load_time < 4.0:
                performance_score = 60
                suggestions.append(f"Slow response time ({load_time:.2f}s). Consider modern hosting or CDN.")
            else:
                performance_score = 30
                suggestions.append(f"Very slow loading time ({load_time:.2f}s). Optimize images, compress script assets.")
                
            # 3. HTML Content checks (SEO and UI)
            html = response.text
            
            # HTTPS check
            if not str(response.url).startswith("https://"):
                seo_score = max(0, seo_score - 30)
                suggestions.append("Website does not use secure HTTPS encryption.")
                
            # Title tag check
            if not re.search(r"<title\b[^>]*>(.*?)</title>", html, re.I):
                seo_score = max(0, seo_score - 25)
                suggestions.append("Missing title tag in website header.")
                
            # Meta description check
            desc_match = re.search(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.I) or \
                         re.search(r'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', html, re.I)
            if not desc_match:
                seo_score = max(0, seo_score - 25)
                suggestions.append("Missing meta description tag for search listings.")
                
            # H1 tag check
            if not re.search(r"<h1\b[^>]*>(.*?)</h1>", html, re.I):
                seo_score = max(0, seo_score - 20)
                suggestions.append("Missing H1 header tag for proper page structure.")
                
            # Viewport tag check (Mobile responsiveness key indicator)
            viewport_match = re.search(r'<meta\s+[^>]*name=["\']viewport["\']', html, re.I)
            if not viewport_match:
                ui_score = max(0, ui_score - 50)
                suggestions.append("Missing viewport tag; page will stretch or render poorly on mobile screens.")
                
            # Responsive indications (media queries or framework references)
            if not any(keyword in html.lower() for keyword in ["@media", "bootstrap", "tailwind", "flex", "grid", "responsive"]):
                ui_score = max(0, ui_score - 30)
                suggestions.append("Incomplete mobile responsive CSS rules detected.")
                
    except Exception as e:
        # Website is completely down or timeout
        seo_score = 0
        ui_score = 0
        performance_score = 0
        suggestions.append(f"Website is completely down or unreachable (Error: {str(e)})")
        
    return {
        "seo_score": seo_score,
        "ui_score": ui_score,
        "performance_score": performance_score,
        "suggestions": suggestions
    }

class WebsiteAuditService:
    def __init__(self, audit_repo: WebsiteAuditRepository, company_repo: CompanyRepository):
        self.audit_repo = audit_repo
        self.company_repo = company_repo

    async def create_audit(self, audit_in: WebsiteAuditCreate) -> Dict[str, Any]:
        # Verify the company exists before adding an audit
        company = await self.company_repo.get_by_id(audit_in.company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            
        audit_data = audit_in.model_dump()
        # Convert HttpUrl to string for database compatibility
        audit_data["website_url"] = str(audit_data["website_url"])
        audit_data["created_at"] = datetime.utcnow()
        audit_data["updated_at"] = datetime.utcnow()
        return await self.audit_repo.create(audit_data)

    async def run_live_audit(self, company_id: str, url: str) -> Dict[str, Any]:
        """Runs a live website audit check, saves it, and updates lead status to Audited."""
        company = await self.company_repo.get_by_id(company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "http://" + clean_url
            
        results = await perform_live_website_audit(clean_url)
        
        audit_data = {
            "company_id": company_id,
            "website_url": clean_url,
            "seo_score": results["seo_score"],
            "ui_score": results["ui_score"],
            "performance_score": results["performance_score"],
            "suggestions": results["suggestions"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.company_repo.update(company_id, {"status": "Audited"})
        return await self.audit_repo.create(audit_data)

    async def get_audit(self, audit_id: str) -> Dict[str, Any]:
        audit = await self.audit_repo.get_by_id(audit_id)
        if not audit:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
        return audit

    async def get_audits_for_company(self, company_id: str) -> List[Dict[str, Any]]:
        return await self.audit_repo.get_by_company_id(company_id)

    async def update_audit(self, audit_id: str, audit_in: WebsiteAuditUpdate) -> Dict[str, Any]:
        await self.get_audit(audit_id) # Validates existence
        
        update_data = audit_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        return await self.audit_repo.update(audit_id, update_data)

    async def delete_audit(self, audit_id: str):
        await self.get_audit(audit_id) # Validates existence
        success = await self.audit_repo.delete(audit_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete audit")
