from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./apf.db"
    REDIS_URL: str = "redis://localhost:6379"
    ARTIFACT_STORE_URL: str = "http://artifact-store:8001"
    APF_SECRET_KEY: str = "dev-secret-change-in-production"
    APF_JWT_ALGORITHM: str = "HS256"
    APF_JWT_EXPIRE_MINUTES: int = 1440
    LOG_LEVEL: str = "INFO"
    MAX_CONCURRENT_PIPELINES: int = 5
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
