import httpx
from typing import Any
from .config import Settings


class ConfluenceClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base = settings.CONFLUENCE_URL.rstrip('/')
        self._auth = (settings.CONFLUENCE_USER, settings.CONFLUENCE_API_TOKEN)
        self._headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    async def create_page(
        self,
        title: str,
        body: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'type': 'page',
            'title': title,
            'space': {'key': self._settings.CONFLUENCE_SPACE_KEY},
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage',
                }
            },
        }
        if parent_id or self._settings.CONFLUENCE_PARENT_PAGE_ID:
            payload['ancestors'] = [
                {'id': parent_id or self._settings.CONFLUENCE_PARENT_PAGE_ID}
            ]
        async with httpx.AsyncClient(auth=self._auth, headers=self._headers) as client:
            resp = await client.post(
                f'{self._base}/wiki/rest/api/content', json=payload
            )
            resp.raise_for_status()
            return resp.json()

    async def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version: int,
    ) -> dict[str, Any]:
        payload = {
            'type': 'page',
            'title': title,
            'version': {'number': version},
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage',
                }
            },
        }
        async with httpx.AsyncClient(auth=self._auth, headers=self._headers) as client:
            resp = await client.put(
                f'{self._base}/wiki/rest/api/content/{page_id}', json=payload
            )
            resp.raise_for_status()
            return resp.json()

    async def get_page_by_title(self, title: str) -> dict[str, Any] | None:
        params = {
            'spaceKey': self._settings.CONFLUENCE_SPACE_KEY,
            'title': title,
            'expand': 'version',
        }
        async with httpx.AsyncClient(auth=self._auth, headers=self._headers) as client:
            resp = await client.get(
                f'{self._base}/wiki/rest/api/content', params=params
            )
            resp.raise_for_status()
            results = resp.json().get('results', [])
            return results[0] if results else None
