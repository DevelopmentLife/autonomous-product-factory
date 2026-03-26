import hmac, hashlib
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = 'sha256=' + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post('/webhooks/github')
async def github_webhook(request: Request):
    settings = request.app.state.settings
    body = await request.body()
    sig = request.headers.get('X-Hub-Signature-256', '')
    if settings.GITHUB_WEBHOOK_SECRET and not verify_github_signature(body, sig, settings.GITHUB_WEBHOOK_SECRET):
        raise HTTPException(401, 'Invalid webhook signature')
    event_type = request.headers.get('X-GitHub-Event', 'unknown')
    return {'received': True, 'event': event_type}


@router.get('/healthz')
async def healthz():
    return {'status': 'ok', 'service': 'github-integration'}
