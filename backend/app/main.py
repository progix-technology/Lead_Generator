from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.config.settings import get_settings
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.routes import api_router
from app.core.exceptions import add_exception_handlers

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI.
    Executes startup and shutdown events securely.
    """
    # Startup: Connect to Database
    await connect_to_mongo()
    # Start the background autopilot scheduler
    from app.services.automation_worker import run_automation_scheduler
    asyncio.create_task(run_automation_scheduler())
    yield
    # Shutdown: Close Database connection
    await close_mongo_connection()

# Initialize FastAPI App
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for LeadGen Pro",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",  # Swagger Documentation
    redoc_url="/redoc"
)

# Activate Global Exception Handlers
add_exception_handlers(app)

# Configure CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with frontend URL (e.g., http://localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Health Check Route
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple health check endpoint to verify the API is running.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT
    }
