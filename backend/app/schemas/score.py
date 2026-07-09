from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class LeadScoreBase(BaseModel):
    company_id: str = Field(..., description="ID of the company this score belongs to")
    score: int = Field(default=0, ge=0, le=100, description="Overall lead score 0-100")
    factors: Dict[str, int] = Field(
        default_factory=dict, 
        description="Key-value pairs of factors affecting the score (e.g., {'seo_poor': 20, 'email_opened': 10})"
    )

class LeadScoreCreate(LeadScoreBase):
    pass

class LeadScoreUpdate(BaseModel):
    score: Optional[int] = Field(None, ge=0, le=100)
    factors: Optional[Dict[str, int]] = None

class LeadScoreResponse(LeadScoreBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LeadScoreListResponse(BaseModel):
    total_count: int
    data: list[LeadScoreResponse]
