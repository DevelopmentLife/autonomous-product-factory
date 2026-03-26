from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    STORAGE_BACKEND: str = 'local'
    LOCAL_STORAGE_PATH: str = '/data/artifacts'
    MAX_ARTIFACT_SIZE_MB: int = 100
    LOG_LEVEL: str = 'INFO'
    model_config = {'env_file': '.env'}


@lru_cache
def get_settings() -> Settings:
    return Settings()
