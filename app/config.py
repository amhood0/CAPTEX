"""
Application configuration
"""
from pathlib import Path
import os
import sys
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

IS_FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)).resolve()
DEFAULT_DATA_DIR = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "CAPTEX"
                    if IS_FROZEN else BASE_DIR / ".data")

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATA_DIR: Path = Field(DEFAULT_DATA_DIR, validation_alias="CAPTEX_DATA_DIR")
    DATABASE_URL: str = Field("", validation_alias="DATABASE_URL")
    
    # Application
    APP_NAME: str = "Capability Test Management Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = Field(False, validation_alias="CAPTEX_DEBUG")
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
settings.DATA_DIR = settings.DATA_DIR.expanduser().resolve()
if not settings.DATABASE_URL:
    settings.DATABASE_URL = f"sqlite:///{settings.DATA_DIR / 'captex.db'}" if IS_FROZEN else f"sqlite:///{BASE_DIR / 'app.db'}"

RUNTIME_DIR = settings.DATA_DIR / "runtime"
MANAGED_ROOT = settings.DATA_DIR if IS_FROZEN else BASE_DIR
