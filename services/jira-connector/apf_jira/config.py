from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    JIRA_URL: str = ''
    JIRA_USER: str = ''
    JIRA_API_TOKEN: str = ''
    JIRA_PROJECT_KEY: str = 'APF'
    ORCHESTRATOR_URL: str = 'http://localhost:8000'

    class Config:
        env_file = '.env'
        extra = 'ignore'


@lru_cache()
def get_settings() -> Settings:
    return Settings()
