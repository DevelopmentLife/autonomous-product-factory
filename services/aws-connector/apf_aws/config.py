from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    AWS_ACCESS_KEY_ID: str = ''
    AWS_SECRET_ACCESS_KEY: str = ''
    AWS_DEFAULT_REGION: str = 'us-east-1'
    AWS_ECS_CLUSTER: str = ''
    AWS_ECS_SERVICE: str = ''
    AWS_ECS_TASK_DEFINITION: str = ''
    AWS_ECR_REGISTRY: str = ''
    ORCHESTRATOR_URL: str = 'http://localhost:8000'

    class Config:
        env_file = '.env'
        extra = 'ignore'


@lru_cache()
def get_settings() -> Settings:
    return Settings()
