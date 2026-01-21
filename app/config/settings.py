"""
Application configuration loaded from environment variables.
"""
import os
from typing import Optional


class Config:
    """Base configuration class."""
    
    # Flask settings
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "1") == "1"
    
    # Application settings
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    
    # Third-party API keys (for backward compatibility, but microservices handle these now)
    FANTASYNERDS_API_KEY: Optional[str] = os.getenv("FANTASYNERDS_API_KEY")
    THE_ODDS_API_KEY: Optional[str] = os.getenv("THE_ODDS_API_KEY")
    
    # Microservices URLs
    FANTASYNERDS_SERVICE_URL: str = os.getenv("FANTASYNERDS_SERVICE_URL", "http://fantasynerds-service:8001")
    FANTASYNERDS_SERVICE_PREFIX: str = os.getenv("FANTASYNERDS_SERVICE_PREFIX", "/api/v1/fantasynerds")
    NBA_API_SERVICE_URL: str = os.getenv("NBA_API_SERVICE_URL", "http://nba-api-service:8002")
    NBA_API_SERVICE_PREFIX: str = os.getenv("NBA_API_SERVICE_PREFIX", "/api/v1/nba")
    ODDS_API_SERVICE_URL: str = os.getenv("ODDS_API_SERVICE_URL", "http://odds-api-service:8003")
    ODDS_API_SERVICE_PREFIX: str = os.getenv("ODDS_API_SERVICE_PREFIX", "/api/v1/odds")

    # NBA API request/timeouts
    NBA_API_REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("NBA_API_REQUEST_TIMEOUT_SECONDS", "60"))
    NBA_API_GAME_LOG_THREAD_TIMEOUT_SECONDS: float = float(os.getenv("NBA_API_GAME_LOG_THREAD_TIMEOUT_SECONDS", "65"))
    
    # Cache settings
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "120"))
    
    # MySQL Database settings
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "mysql")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "nba_user")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "nba_password")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "nba_edge")
    
    @property
    def mysql_connection_string(self) -> str:
        """Get MySQL connection string."""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

