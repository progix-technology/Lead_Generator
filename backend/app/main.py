from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import asyncio
import warnings
import inspect

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Silence noisy Python 3.14 deprecations from Motor/asyncio wrappers on Render.
warnings.filterwarnings(
    "ignore",
    message=r"'asyncio\.iscoroutinefunction' is deprecated.*",
    category=DeprecationWarning,
    module=r"motor\.frameworks\.asyncio",
)

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
    
    # Auto-install Playwright Chromium browser asynchronously so it doesn't block server startup
    def install_playwright():
        import os
        from app.services.places import should_use_playwright

        if not should_use_playwright():
            logger.info("FastAPI Lifespan: Skipping Playwright browser install because browser automation is disabled in this environment.")
            return

        # Cross-platform check if Playwright Chromium folder exists
        paths = []
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            paths.append(os.path.join(user_profile, "AppData", "Local", "ms-playwright"))
        home = os.environ.get("HOME")
        if home:
            paths.append(os.path.join(home, ".cache", "ms-playwright"))
            paths.append(os.path.join(home, "Library", "Caches", "ms-playwright"))

        is_installed = False
        for path in paths:
            if os.path.exists(path):
                try:
                    for item in os.listdir(path):
                        if item.startswith("chromium-"):
                            is_installed = True
                            break
                except Exception:
                    pass
            if is_installed:
                break

        if is_installed:
            logger.info("FastAPI Lifespan: Playwright Chromium browser is already installed. Skipping auto-install.")
            return

        import app.services.email_scraper as email_scraper
        try:
            import subprocess
            import sys
            email_scraper.PLAYWRIGHT_INSTALLING = True
            logger.info("FastAPI Lifespan: Auto-installing Playwright Chromium browser...")
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            logger.info("FastAPI Lifespan: Playwright Chromium browser installed successfully!")
        except Exception as err:
            logger.error(f"FastAPI Lifespan: Playwright auto-install failed: {err}")
        finally:
            email_scraper.PLAYWRIGHT_INSTALLING = False
            
    import threading
    threading.Thread(target=install_playwright, daemon=True).start()
    
    # Start the decoupled background autopilot schedulers
    from app.services.automation_worker import run_scraper_scheduler, run_mailer_scheduler
    asyncio.create_task(run_scraper_scheduler())
    asyncio.create_task(run_mailer_scheduler())
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
import os
origins_str = os.environ.get("ALLOWED_ORIGINS", "")
if origins_str:
    origins = [o.strip() for o in origins_str.split(",") if o.strip()]
else:
    # Default local dev origins
    origins = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:5174"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex="https://.*\\.vercel\\.app",  # Automatically allows all Vercel deployments
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

@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint to confirm API status.
    """
    return {
        "message": "LeadGen Pro API is running!",
        "status": "healthy"
    }
