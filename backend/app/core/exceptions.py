from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

def add_exception_handlers(app):
    """
    Registers global exception handlers to the FastAPI application.
    """
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Catches standard HTTP Exceptions raised by our code (e.g., 404 Not Found)"""
        logger.warning(f"HTTP Exception {exc.status_code} at {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Catches errors when the frontend sends bad data that fails Pydantic validation"""
        logger.warning(f"Validation Error at {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "Validation Error",
                "details": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catches all other unhandled exceptions to prevent server crashes"""
        logger.error(f"Unhandled Exception at {request.url}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal Server Error"}
        )
