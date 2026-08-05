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
    Crawls a target website, analyzes response speed, extracts key HTML elements (SEO/UX/Conversion),
    and computes strict scores out of 100 for SEO, Speed/Performance, and UI/Mobile friendliness.
    Generates detailed, actionable bullet points of website deficiencies.
    """
    start_time = time.time()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    seo_score = 100
    ui_score = 100
    performance_score = 100
    suggestions = []
    
    try:
        # Use HTTPX with SSL verification turned off to prevent SSL handshake errors blocking our audit
        async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers=headers, timeout=7.0)
            load_time = time.time() - start_time
            
            # 1. Check HTTP Status
            if response.status_code == 403 or response.status_code == 401:
                raise ValueError(f"Website blocked audit with HTTP {response.status_code} (bot protection active)")

            if response.status_code >= 400:
                suggestions.append(f"Server returning HTTP error status {response.status_code}.")
                seo_score = max(0, seo_score - 40)
                performance_score = max(0, performance_score - 50)
                ui_score = max(0, ui_score - 40)
                
            # 2. Strict Performance (Speed & Payload) Scoring
            if load_time < 0.8:
                performance_score = 100
            elif load_time < 1.5:
                performance_score = 80
                suggestions.append(f"Load time is slightly delayed ({load_time:.2f}s). Asset optimization recommended.")
            elif load_time < 3.0:
                performance_score = 55
                suggestions.append(f"Slow page response speed ({load_time:.2f}s). Server latency & uncompressed assets detected.")
            else:
                performance_score = 30
                suggestions.append(f"Critical load speed bottleneck ({load_time:.2f}s). Heavy scripts and unoptimized images.")

            # Payload size check
            content_len = len(response.content)
            if content_len > 1_500_000:  # > 1.5 MB HTML payload
                performance_score = max(0, performance_score - 20)
                suggestions.append(f"Uncompressed DOM payload size ({content_len / (1024*1024):.1f} MB). Slows mobile rendering.")

            # 3. HTML Content Checks (SEO, Mobile UI, Conversion & Schema)
            html = response.text
            html_lower = html.lower()
            
            # A. Security & HTTPS Check
            if not str(response.url).startswith("https://"):
                seo_score = max(0, seo_score - 35)
                suggestions.append("Missing SSL certificate / Non-HTTPS connection (causes 'Not Secure' browser warning).")

            # B. Title Tag Check
            title_match = re.search(r"<title\b[^>]*>(.*?)</title>", html, re.I | re.S)
            if not title_match or not title_match.group(1).strip():
                seo_score = max(0, seo_score - 30)
                suggestions.append("Missing page 'title' tag in HTML head.")
            elif len(title_match.group(1).strip()) < 15:
                seo_score = max(0, seo_score - 15)
                suggestions.append("Short or unoptimized page title tag (<15 characters).")

            # C. Meta Description Check
            desc_match = re.search(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.I) or \
                         re.search(r'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']', html, re.I)
            if not desc_match or not desc_match.group(1).strip():
                seo_score = max(0, seo_score - 25)
                suggestions.append("Missing meta description tag for search engine snippets.")

            # D. H1 Header Structure Check
            h1_match = re.search(r"<h1\b[^>]*>(.*?)</h1>", html, re.I | re.S)
            if not h1_match or not h1_match.group(1).strip():
                seo_score = max(0, seo_score - 20)
                suggestions.append("Missing primary H1 heading tag for Google hierarchy.")

            # E. Schema.org / Structured Data Check
            if "application/ld+json" not in html_lower and 'itemtype="http://schema.org' not in html_lower:
                seo_score = max(0, seo_score - 15)
                suggestions.append("Missing Schema.org LocalBusiness structured data markup for Google Local Pack rank.")

            # F. OpenGraph Social Sharing Tags Check
            if "og:title" not in html_lower and "og:image" not in html_lower:
                seo_score = max(0, seo_score - 15)
                suggestions.append("Missing OpenGraph social meta tags (previews will break when shared on social media).")

            # G. Image Alt Attributes Check
            img_tags = re.findall(r'<img\b[^>]*>', html, re.I)
            if img_tags:
                imgs_without_alt = [img for img in img_tags if 'alt=' not in img.lower()]
                if len(imgs_without_alt) > len(img_tags) * 0.4:
                    seo_score = max(0, seo_score - 15)
                    suggestions.append(f"{len(imgs_without_alt)} website images are missing ALT tags for accessibility and image search.")

            # H. Mobile Viewport & Responsiveness Checks
            viewport_match = re.search(r'<meta\s+[^>]*name=["\']viewport["\']', html, re.I)
            if not viewport_match:
                ui_score = max(0, ui_score - 55)
                suggestions.append("Missing viewport tag; layout stretches or renders broken on mobile devices.")

            # Responsive styling check
            if not any(kw in html_lower for kw in ["@media", "bootstrap", "tailwind", "flex", "grid", "responsive"]):
                ui_score = max(0, ui_score - 30)
                suggestions.append("Incomplete mobile responsive CSS framework detected.")

            # Favicon check
            if not re.search(r'<link\s+[^>]*rel=["\'](shortcut )?icon["\']', html, re.I):
                ui_score = max(0, ui_score - 15)
                suggestions.append("Missing favicon icon in browser tab.")

            # I. Conversion & Lead Capture CTA Check
            has_form = "<form" in html_lower
            has_tel = "tel:" in html_lower or re.search(r'\(\d{3}\)\s*\d{3}-\d{4}|\d{3}-\d{3}-\d{4}', html)
            has_booking = any(kw in html_lower for kw in ["book", "appointment", "quote", "contact", "schedule", "get started"])
            
            if not has_form and not has_booking:
                ui_score = max(0, ui_score - 25)
                suggestions.append("No direct lead capture form or online booking CTA found on homepage.")

    except Exception as e:
        raise
        
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
