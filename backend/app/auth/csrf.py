from fastapi import HTTPException, Request, status

from app.auth.security import CSRF_COOKIE

CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def verify_csrf(request: Request) -> None:
    """Double-submit cookie check: the CSRF cookie value must match a header the JS client set.

    A cross-site page can trigger the cookie to be sent automatically but cannot read it
    (or the frontend origin) to set the matching header, so this blocks CSRF on state-changing
    requests made with cookie-based auth.
    """
    if request.method in SAFE_METHODS:
        return

    cookie_value = request.cookies.get(CSRF_COOKIE)
    header_value = request.headers.get(CSRF_HEADER)

    if not cookie_value or not header_value or cookie_value != header_value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF validation failed")
