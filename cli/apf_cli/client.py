import httpx
from .config_schema import get_cli_settings


def get_client() -> httpx.AsyncClient:
    settings = get_cli_settings()
    headers = {}
    if settings.APF_TOKEN:
        headers['Authorization'] = f'Bearer {settings.APF_TOKEN}'
    return httpx.AsyncClient(base_url=settings.APF_API_URL, headers=headers, timeout=30.0)
