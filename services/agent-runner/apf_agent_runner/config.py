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
    LITELLM_BASE_URL: str = ''
    # Set MOCK_LLM=true to run the full pipeline without any API key.
    # Agents will return realistic-looking stub artifacts — useful for
    # testing pipeline flow, connector wiring, and the dashboard locally.
    MOCK_LLM: bool = False
    WORKER_ID: str = 'worker-1'
    LOG_LEVEL: str = 'INFO'
    model_config = {'env_file': '.env'}


AgentRunnerConfig = Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()
