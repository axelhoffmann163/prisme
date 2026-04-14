import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

class Settings:
    DB_HOST:     str = os.getenv("DB_HOST", "localhost")
    DB_PORT:     int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME:     str = os.getenv("DB_NAME", "presswatch")
    DB_USER:     str = os.getenv("DB_USER", "presswatch_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_POOL_SIZE:    int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    FETCH_TIMEOUT:  int = int(os.getenv("FETCH_TIMEOUT", "15"))
    FETCH_WORKERS:  int = int(os.getenv("FETCH_WORKERS", "20"))
    USER_AGENT:     str = os.getenv("USER_AGENT", "PressWatch/1.0")
    MAX_ARTICLES_PER_SOURCE: int = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "500"))
    RETENTION_DAYS: int = int(os.getenv("RETENTION_DAYS", "90"))

    LOG_LEVEL:     str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE:      str = os.getenv("LOG_FILE", "logs/collector.log")
    LOG_ROTATION:  str = os.getenv("LOG_ROTATION", "10 MB")
    LOG_RETENTION: str = os.getenv("LOG_RETENTION", "30 days")

    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    DRY_RUN:    bool = os.getenv("DRY_RUN", "false").lower() == "true"

settings = Settings()
