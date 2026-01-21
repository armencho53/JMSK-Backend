import os
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Reduced from 30 for better security
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Default 7 days
    REFRESH_TOKEN_EXPIRE_DAYS_REMEMBER_ME: int = 30  # 30 days with Remember Me

    # Account lockout settings
    MAX_LOGIN_ATTEMPTS: int = 5  # Lock account after 5 failed attempts
    LOCKOUT_DURATION_MINUTES: int = 15  # Lock for 15 minutes

    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Cache settings to avoid re-reading env vars
        frozen = True

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance - only created once per Lambda container"""
    return Settings()

# Global settings instance (cached)
settings = get_settings()
