from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.csrf import verify_csrf
from app.auth.dependencies import get_client_ip, get_current_user
from app.auth.security import (
    REFRESH_TOKEN_COOKIE,
    as_aware_utc,
    create_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.database import get_db
from app.middleware.rate_limit import rate_limit
from app.models.audit_log import AuditLog
from app.models.session import Session as SessionModel
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_session(db: AsyncSession, response: Response, user: User, request: Request) -> None:
    raw_refresh, refresh_hash, expires_at = generate_refresh_token()
    session = SessionModel(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        user_agent=request.headers.get("user-agent", "")[:500],
        ip_address=get_client_ip(request),
        expires_at=expires_at,
    )
    db.add(session)

    access_token = create_access_token(user.id, user.role.value)
    csrf_token = generate_csrf_token()
    set_auth_cookies(response, access_token, raw_refresh, csrf_token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _rl: None = rate_limit("auth", 10),
) -> User:
    existing = await db.execute(
        select(User).where(or_(User.username == payload.username, User.email == payload.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username or email is already registered")

    user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()

    db.add(AuditLog(actor_user_id=user.id, action="register", target=user.username, ip_address=get_client_ip(request)))
    await _issue_session(db, response, user, request)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=UserRead)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _rl: None = rate_limit("auth", 10),
) -> User:
    result = await db.execute(
        select(User).where(
            or_(User.username == payload.username_or_email, User.email == payload.username_or_email)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        db.add(AuditLog(action="login", target=payload.username_or_email, ip_address=get_client_ip(request), result="failure"))
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username/email or password")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled")

    db.add(AuditLog(actor_user_id=user.id, action="login", target=user.username, ip_address=get_client_ip(request)))
    await _issue_session(db, response, user, request)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw_refresh = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not raw_refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token")

    token_hash = hash_refresh_token(raw_refresh)
    result = await db.execute(select(SessionModel).where(SessionModel.refresh_token_hash == token_hash))
    session = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not session or session.revoked_at or as_aware_utc(session.expires_at) < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token is invalid or expired")

    user = await db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not available")

    session.revoked_at = now  # rotate: old refresh token is single-use
    await _issue_session(db, response, user, request)
    await db.commit()

    return {"status": "ok"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)])
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    raw_refresh = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if raw_refresh:
        token_hash = hash_refresh_token(raw_refresh)
        result = await db.execute(select(SessionModel).where(SessionModel.refresh_token_hash == token_hash))
        session = result.scalar_one_or_none()
        if session and not session.revoked_at:
            session.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    clear_auth_cookies(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)])
async def logout_all(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(SessionModel).where(SessionModel.user_id == user.id, SessionModel.revoked_at.is_(None))
    )
    now = datetime.now(timezone.utc)
    for session in result.scalars().all():
        session.revoked_at = now

    db.add(AuditLog(actor_user_id=user.id, action="logout_all", target=user.username))
    await db.commit()
    clear_auth_cookies(response)


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
