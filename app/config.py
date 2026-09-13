"""
Application configuration
"""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/app.db"
    
    # Application
    APP_NAME: str = "Capability Test Management Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(False, validation_alias="CAPTEX_DEBUG")
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
