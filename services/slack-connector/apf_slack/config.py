from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SLACK_BOT_TOKEN: str = ''
    SLACK_SIGNING_SECRET: str = ''
    SLACK_APP_TOKEN: str = ''
    ORCHESTRATOR_URL: str = 'http://orchestrator:8000'
    SLACK_CHANNEL: str = '#apf-notifications'
    model_config = {'env_file': '.env'}


@lru_cache
def get_settings() -> Settings:
    return Settings()
