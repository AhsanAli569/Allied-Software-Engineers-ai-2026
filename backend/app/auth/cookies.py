from fastapi import Response

from app.auth.security import ACCESS_TOKEN_COOKIE, CSRF_COOKIE, REFRESH_TOKEN_COOKIE
from app.config import get_settings

settings = get_settings()


def _secure() -> bool:
    return settings.environment != "development"


def _samesite() -> str:
    return settings.cookie_samesite


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    secure = _secure()
    samesite = _samesite()
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=settings.access_token_ttl_minutes * 60,
        path="/",
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )
    # Not httpOnly: the frontend JS reads this to echo it back in the X-CSRF-Token header
    # (double-submit pattern). It carries no authority on its own.
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=secure,
        samesite=samesite,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        path="/",
    )


def set_csrf_cookie(response: Response, csrf_token: str) -> None:
    """Used when re-issuing just the CSRF cookie (GET /auth/csrf) without touching the
    access/refresh tokens — same attributes as set_auth_cookies uses for consistency.
    """
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=_secure(),
        samesite=_samesite(),
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    secure = _secure()
    samesite = _samesite()
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/", secure=secure, samesite=samesite)
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path="/api/v1/auth", secure=secure, samesite=samesite)
    response.delete_cookie(CSRF_COOKIE, path="/", secure=secure, samesite=samesite)
