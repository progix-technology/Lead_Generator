from fastapi import APIRouter
from app.routes import auth, companies, users, audits, scores, automation

api_router = APIRouter()

# Grouping routers and adding prefixes/tags for Swagger documentation
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(companies.router, prefix="/companies", tags=["Companies"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(audits.router, prefix="/audits", tags=["Website Audits"])
api_router.include_router(scores.router, prefix="/scores", tags=["Lead Scores"])
api_router.include_router(automation.router, prefix="/automation", tags=["Autopilot"])
