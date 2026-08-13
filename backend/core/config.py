import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application environment configuration settings container.
    Loads values from environment variables or local .env file.
    """

    MONGODB_URL: str = "mongodb://127.0.0.1:27017"
    DATABASE_NAME: str = "whitfield_wms"
    JWT_SECRET: str = "change-this-secret-in-environment"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
