from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Application Configuration
    APP_NAME: str = "LeadGen Pro Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # MongoDB Configuration
    MONGODB_URI: str
    DATABASE_NAME: str = "leadgen_pro"

    # Security Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    # AI and Third Party APIs
    GOOGLE_PLACES_API_KEY: Optional[str] = None

    # SMTP Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None

    # AI Configurations
    OPENROUTER_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=True,
        extra="ignore"
    )

def get_settings() -> Settings:
    """
    Dependency injection for settings.
    Caches the settings object so it's not re-read from the .env file on every request.
    """
    return Settings()

settings = get_settings()
