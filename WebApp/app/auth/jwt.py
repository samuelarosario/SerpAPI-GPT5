from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4
from jose import jwt

from WebApp.app.core.config import settings


def _expire(minutes: int = 15) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def create_access_token(subject: str) -> str:
    to_encode: Dict[str, Any] = {"sub": subject, "exp": _expire(settings.access_token_minutes), "jti": str(uuid4())}
    return jwt.encode(to_encode, settings.webapp_jwt_secret, algorithm=settings.algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    to_encode: Dict[str, Any] = {"sub": subject, "exp": expire, "type": "refresh", "jti": str(uuid4())}
    return jwt.encode(to_encode, settings.webapp_jwt_secret, algorithm=settings.algorithm)
