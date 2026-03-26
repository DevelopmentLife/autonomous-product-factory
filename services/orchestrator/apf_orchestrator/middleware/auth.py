"""JWT bearer token validation middleware.

This middleware validates the ``Authorization: Bearer <token>`` header on every
request **except** public paths (health checks, metrics, auth endpoints and the
WebSocket handshake).  It sets ``request.state.user_id`` on success.

Note: route-level ``get_current_user`` dependency performs the *full* user
lookup; this middleware is a lighter first-pass guard that rejects obviously
invalid tokens early.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from jose import JWTError, jwt

from ..config import OrchestratorConfig

# Paths that do not require authentication
_PUBLIC_PREFIXES = (
    "/healthz",
    "/readyz",
    "/metrics",
    "/api/v1/auth/",
    "/docs",
    "/openapi.json",
    "/ws/",
)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT tokens for protected routes."""

    def __init__(self, app, config: OrchestratorConfig) -> None:
        super().__init__(app)
        self._config = config

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip validation for public paths
        if any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Authorization header missing or malformed"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(
                token,
                self._config.APF_SECRET_KEY,
                algorithms=[self._config.APF_JWT_ALGORITHM],
            )
            request.state.user_id = payload.get("sub")
        except JWTError as exc:
            return JSONResponse(
                {"detail": f"Invalid or expired token: {exc}"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
