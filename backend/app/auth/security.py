import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

settings = get_settings()
_hasher = PasswordHasher()

ACCESS_TOKEN_COOKIE = "ase_access_token"
REFRESH_TOKEN_COOKIE = "ase_refresh_token"
CSRF_COOKIE = "ase_csrf_token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Returns (raw_token, sha256_hash, expires_at). Only the hash is persisted."""
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
    return raw, token_hash, expires_at


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def as_aware_utc(value: datetime) -> datetime:
    """SQLite (used for local dev fallback / tests) doesn't persist tzinfo on DateTime
    columns, so values read back are naive even though they were written as UTC. Postgres
    (production) does not have this issue, but comparisons against `datetime.now(timezone.utc)`
    need to work against either backend.
    """
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
