from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    GITHUB_APP_ID: str = ''
    GITHUB_APP_PRIVATE_KEY: str = ''
    GITHUB_WEBHOOK_SECRET: str = ''
    GITHUB_TOKEN: str = ''
    LOG_LEVEL: str = 'INFO'
    model_config = {'env_file': '.env'}


@lru_cache
def get_settings() -> Settings:
    return Settings()
