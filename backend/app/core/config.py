import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "Enterprise Document Intelligence Assistant"
    API_V1_STR: str = "/api/v1"
    ENV: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # PostgreSQL Configurations
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgrespassword"
    POSTGRES_DB: str = "document_intelligence"

    # Redis Configurations
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Security & JWT Settings
    # Generate a secure key in production (e.g. openssl rand -hex 32)
    SECRET_KEY: str = "7e15291b0f19c25f1b1c55bc6d01e1498b671a532321bc36efc0d8f07df590ad"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OCR Configurations
    OCR_PROVIDER: Literal["tesseract", "easyocr", "paddleocr", "mock"] = "tesseract"
    TESSERACT_CMD: str = "tesseract"

    # Embedding Configurations
    EMBEDDING_PROVIDER: Literal["openai", "huggingface", "mock"] = "mock"
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    HUGGINGFACE_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"



    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Asynchronous database connection URI using asyncpg."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def SQLALCHEMY_SYNC_DATABASE_URI(self) -> str:
        """Synchronous database connection URI using psycopg2 (primarily for migrations/Alembic)."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

settings = Settings()
