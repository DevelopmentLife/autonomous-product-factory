from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    CONFLUENCE_URL: str = ''
    CONFLUENCE_USER: str = ''
    CONFLUENCE_API_TOKEN: str = ''
    CONFLUENCE_SPACE_KEY: str = 'APF'
    CONFLUENCE_PARENT_PAGE_ID: str = ''
    ORCHESTRATOR_URL: str = 'http://localhost:8000'

    class Config:
        env_file = '.env'
        extra = 'ignore'


@lru_cache()
def get_settings() -> Settings:
    return Settings()
