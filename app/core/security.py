from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from .config import get_settings


async def require_api_key(authorization: str | None = Header(default=None), x_api_key: str | None = Header(default=None)) -> str | None:
    settings = get_settings()
    if not settings.require_api_key:
        return None
    candidate = x_api_key or ""
    if authorization and authorization.lower().startswith("bearer "):
        candidate = authorization.split(" ", 1)[1].strip()
    if candidate and candidate in settings.api_keys:
        return candidate
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid API key required")
