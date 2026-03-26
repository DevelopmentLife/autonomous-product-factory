from pydantic_settings import BaseSettings
from functools import lru_cache


class CLISettings(BaseSettings):
    APF_API_URL: str = 'http://localhost:8000'
    APF_TOKEN: str = ''
    model_config = {'env_file': '.env'}


@lru_cache
def get_cli_settings() -> CLISettings:
    return CLISettings()
