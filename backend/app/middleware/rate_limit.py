import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status

from app.auth.dependencies import get_client_ip

WINDOW_SECONDS = 60.0

# In-memory sliding-window counters, keyed by "bucket:identity".
# Dev-only: does not share state across multiple worker processes.
# Swap for a Redis-backed limiter (INCR + EXPIRE or a sorted set) before scaling
# beyond a single process.
_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(bucket: str, limit_per_minute: int) -> Callable:
    async def dependency(request: Request) -> None:
        identity = request.cookies.get("ase_access_token") or get_client_ip(request)
        key = f"{bucket}:{identity}"
        now = time.monotonic()
        window = _hits[key]

        while window and now - window[0] > WINDOW_SECONDS:
            window.popleft()

        if len(window) >= limit_per_minute:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests. Please slow down and try again shortly.",
            )

        window.append(now)

    return Depends(dependency)
