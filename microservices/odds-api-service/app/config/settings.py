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
    APP_PORT: int = int(os.getenv("APP_PORT", "8003"))
    
    # The Odds API settings
    THE_ODDS_API_KEY: Optional[str] = os.getenv("THE_ODDS_API_KEY")
    THE_ODDS_API_BASE_URL: str = os.getenv("THE_ODDS_API_BASE_URL", "https://api.the-odds-api.com")
    
    # MySQL Database settings (shared database)
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "mysql")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "nba_user")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "nba_password")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "nba_edge")
