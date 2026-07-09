from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime

# Shared properties for a Company
class CompanyBase(BaseModel):
    name: str = Field(..., description="Name of the company")
    industry: Optional[str] = None
    employees: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    status: str = Field(default="Pending", description="Status of the lead (e.g. Pending, Audited, Active Lead)")
    email_source: Optional[str] = None

# Properties required to create a new company
class CompanyCreate(CompanyBase):
    pass

# Properties required to update an existing company
class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    employees: Optional[str] = None
    location: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    status: Optional[str] = None
    email_source: Optional[str] = None

# Properties to return in API responses
class CompanyResponse(CompanyBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Pagination wrapper for listing companies
class CompanyListResponse(BaseModel):
    total_count: int
    data: list[CompanyResponse]
