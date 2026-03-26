from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    REDIS_URL: str = 'redis://localhost:6379'
    ARTIFACT_STORE_URL: str = 'http://artifact-store:8001'
    ORCHESTRATOR_URL: str = 'http://orchestrator:8000'
    LLM_PROVIDER: str = 'anthropic'
    LLM_MODEL: str = 'claude-opus-4-6'
    ANTHROPIC_API_KEY: str = ''
    OPENAI_API_KEY: str = ''
    WORKER_ID: str = 'worker-1'
    LOG_LEVEL: str = 'INFO'
    model_config = {'env_file': '.env'}


@lru_cache
def get_settings() -> Settings:
    return Settings()
