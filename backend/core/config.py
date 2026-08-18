import os
from typing import Optional, List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application environment configuration settings container.
    Loads values from environment variables or local .env file.
    """

    MONGODB_URI: Optional[str] = None
    MONGODB_URL: str = "mongodb://127.0.0.1:27017"

    MONGODB_DATABASE: Optional[str] = None
    DATABASE_NAME: str = "whitfield_wms"

    JWT_SECRET: str = "change-this-secret-in-environment"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    GEMINI_API_KEY: Optional[str] = None
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    KNOWLEDGE_PDF_PATH: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def sync_env_and_aliases(self) -> "Settings":
        # Resolve MongoDB URI / URL
        if self.MONGODB_URI:
            self.MONGODB_URL = self.MONGODB_URI
        else:
            self.MONGODB_URI = self.MONGODB_URL

        # Resolve Database Name
        if self.MONGODB_DATABASE:
            self.DATABASE_NAME = self.MONGODB_DATABASE
        else:
            self.MONGODB_DATABASE = self.DATABASE_NAME

        # Sync Gemini API key into os.environ for google.genai Client
        if self.GEMINI_API_KEY:
            os.environ["GEMINI_API_KEY"] = self.GEMINI_API_KEY
        elif "GEMINI_API_KEY" in os.environ:
            self.GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

        return self

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
        origins = [orig.strip() for orig in self.CORS_ORIGINS.split(",") if orig.strip()]
        return origins if origins else ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
