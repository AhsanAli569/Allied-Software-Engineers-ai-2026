import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import ACCESS_TOKEN_COOKIE, decode_access_token
from app.database import get_db
from app.models.user import User, UserRole


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please log in again")

    user_id = uuid.UUID(payload["sub"])
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not available")

    return user


def require_role(*allowed_roles: UserRole) -> Callable:
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action")
        return user

    return checker


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
