import httpx
from typing import Any
from .config import Settings


class JiraClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base = settings.JIRA_URL.rstrip('/')
        self._auth = (settings.JIRA_USER, settings.JIRA_API_TOKEN)
        self._headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    async def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: str = 'Story',
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'fields': {
                'project': {'key': self._settings.JIRA_PROJECT_KEY},
                'summary': summary,
                'description': {
                    'type': 'doc',
                    'version': 1,
                    'content': [
                        {
                            'type': 'paragraph',
                            'content': [{'type': 'text', 'text': description}],
                        }
                    ],
                },
                'issuetype': {'name': issue_type},
            }
        }
        if labels:
            payload['fields']['labels'] = labels
        async with httpx.AsyncClient(auth=self._auth, headers=self._headers) as client:
            resp = await client.post(f'{self._base}/rest/api/3/issue', json=payload)
            resp.raise_for_status()
            return resp.json()

    async def transition_issue(self, issue_key: str, transition_name: str) -> None:
        async with httpx.AsyncClient(auth=self._auth, headers=self._headers) as client:
            t_resp = await client.get(
                f'{self._base}/rest/api/3/issue/{issue_key}/transitions'
            )
            t_resp.raise_for_status()
            transitions = t_resp.json()['transitions']
            tid = next(
                (t['id'] for t in transitions if t['name'].lower() == transition_name.lower()),
                None,
            )
            if tid is None:
                raise ValueError(f'Transition not found: {transition_name}')
            resp = await client.post(
                f'{self._base}/rest/api/3/issue/{issue_key}/transitions',
                json={'transition': {'id': tid}},
            )
            resp.raise_for_status()

    async def add_comment(self, issue_key: str, body: str) -> dict[str, Any]:
        payload = {
            'body': {
                'type': 'doc',
                'version': 1,
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [{'type': 'text', 'text': body}],
                    }
                ],
            }
        }
        async with httpx.AsyncClient(auth=self._auth, headers=self._headers) as client:
            resp = await client.post(
                f'{self._base}/rest/api/3/issue/{issue_key}/comment', json=payload
            )
            resp.raise_for_status()
            return resp.json()
