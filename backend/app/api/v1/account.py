from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import clear_auth_cookies
from app.auth.csrf import verify_csrf
from app.auth.dependencies import get_current_user
from app.auth.security import hash_password, verify_password
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.session import Session as SessionModel
from app.models.user import User
from app.schemas.account import AccountUpdate, ChangePasswordRequest
from app.schemas.user import UserRead

router = APIRouter(prefix="/account", tags=["account"], dependencies=[Depends(verify_csrf)])


@router.patch("", response_model=UserRead)
async def update_account(
    payload: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    if payload.full_name is not None:
        user.full_name = payload.full_name
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")

    user.password_hash = hash_password(payload.new_password)

    result = await db.execute(
        select(SessionModel).where(SessionModel.user_id == user.id, SessionModel.revoked_at.is_(None))
    )
    now = datetime.now(timezone.utc)
    for session in result.scalars().all():
        session.revoked_at = now

    db.add(AuditLog(actor_user_id=user.id, action="change_password", target=user.username))
    await db.commit()
    clear_auth_cookies(response)
