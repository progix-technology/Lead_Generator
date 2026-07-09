from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime

class WebsiteAuditBase(BaseModel):
    company_id: str = Field(..., description="ID of the company this audit belongs to")
    website_url: HttpUrl
    seo_score: int = Field(default=0, ge=0, le=100)
    ui_score: int = Field(default=0, ge=0, le=100)
    performance_score: int = Field(default=0, ge=0, le=100)
    suggestions: List[str] = Field(default_factory=list, description="List of improvement suggestions")
    
class WebsiteAuditCreate(WebsiteAuditBase):
    pass

class WebsiteAuditUpdate(BaseModel):
    seo_score: Optional[int] = Field(None, ge=0, le=100)
    ui_score: Optional[int] = Field(None, ge=0, le=100)
    performance_score: Optional[int] = Field(None, ge=0, le=100)
    suggestions: Optional[List[str]] = None

class WebsiteAuditResponse(WebsiteAuditBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WebsiteAuditListResponse(BaseModel):
    total_count: int
    data: List[WebsiteAuditResponse]
