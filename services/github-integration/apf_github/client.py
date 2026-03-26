from __future__ import annotations
import httpx


class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        self._headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        self._base = 'https://api.github.com'

    async def create_branch(self, owner: str, repo: str, branch: str, from_branch: str = 'main') -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f'{self._base}/repos/{owner}/{repo}/git/ref/heads/{from_branch}',
                                  headers=self._headers)
            r.raise_for_status()
            sha = r.json()['object']['sha']
            payload = {'ref': f'refs/heads/{branch}', 'sha': sha}
            r2 = await client.post(f'{self._base}/repos/{owner}/{repo}/git/refs',
                                    json=payload, headers=self._headers)
            r2.raise_for_status()
            return r2.json()

    async def create_pull_request(self, owner: str, repo: str, title: str,
                                   head: str, base: str = 'main', body: str = '') -> dict:
        async with httpx.AsyncClient() as client:
            payload = {'title': title, 'head': head, 'base': base, 'body': body}
            r = await client.post(f'{self._base}/repos/{owner}/{repo}/pulls',
                                   json=payload, headers=self._headers)
            r.raise_for_status()
            return r.json()

    async def get_repo(self, owner: str, repo: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f'{self._base}/repos/{owner}/{repo}', headers=self._headers)
            r.raise_for_status()
            return r.json()
