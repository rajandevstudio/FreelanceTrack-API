import time
from collections import defaultdict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# RATE LIMITING — IN-MEMORY
#
# How it works:
#   We keep a dict: { ip_address: [timestamp1, timestamp2, ...] }
#   On every request, we:
#     1. Clean up timestamps older than the time window
#     2. Count remaining timestamps
#     3. If count >= limit → reject with 429 Too Many Requests
#     4. Otherwise → add current timestamp and allow the request
#
# Example with limit=5, window=60s:
#   IP 1.2.3.4 makes 5 requests in 30 seconds → all allowed
#   IP 1.2.3.4 makes a 6th request → 429 rejected
#   60 seconds later → window resets, requests allowed again
#
# WHY IN-MEMORY AND NOT REDIS?
#   Redis rate limiting survives server restarts and works across multiple
#   server instances. In-memory resets when the app restarts.
#   For a single-server portfolio project, in-memory is fine.
#   When we scale to multiple servers, swap this for Redis.
#
# LIMITATION: This is per-process. If you run multiple uvicorn workers
#   (--workers 4), each worker has its own dict. A user could make
#   4x the limit of requests by hitting different workers.
#   Again — Redis solves this. Fine for now.
# -----------------------------------------------------------------------------

# Stores request timestamps per IP: {"1.2.3.4": [1712345678.1, 1712345679.4, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)

# Stricter limits for auth endpoints — brute force protection
AUTH_RATE_LIMIT = 10      # max requests
AUTH_RATE_WINDOW = 60     # per 60 seconds

# General API limit — prevents scraping and abuse
GENERAL_RATE_LIMIT = 100  # max requests
GENERAL_RATE_WINDOW = 60  # per 60 seconds


def _get_client_ip(request: Request) -> str:
    """
    Gets the real client IP address.

    `request.client.host` gives the direct connection IP.
    But if you're behind a proxy (Nginx, Railway, Render), the real client IP
    is in the X-Forwarded-For header — the proxy puts it there.
    We check that first.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_rate_limited(ip: str, limit: int, window: int) -> bool:
    """
    Returns True if this IP has exceeded the rate limit.
    Cleans up old timestamps as it goes — no memory leak.
    """
    now = time.time()
    window_start = now - window

    # Keep only timestamps within the current window
    _request_log[ip] = [t for t in _request_log[ip] if t > window_start]

    if len(_request_log[ip]) >= limit:
        return True

    # Record this request
    _request_log[ip].append(now)
    return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware runs on EVERY request before it reaches your router.
    This is different from a dependency (which is per-route).
    Middleware is the right place for cross-cutting concerns like rate limiting.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.ENVIRONMENT in ["local", "development"] or settings.TESTING:
            return await call_next(request)
        ip = _get_client_ip(request)
        path = request.url.path

        # Apply stricter limits to auth endpoints
        if path.startswith("/api/v1/auth"):
            if _is_rate_limited(ip, AUTH_RATE_LIMIT, AUTH_RATE_WINDOW):
                logger.warning("Auth rate limit exceeded for IP: %s on %s", ip, path)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Max {AUTH_RATE_LIMIT} per {AUTH_RATE_WINDOW}s.",
                )
        else:
            if _is_rate_limited(ip, GENERAL_RATE_LIMIT, GENERAL_RATE_WINDOW):
                logger.warning("Rate limit exceeded for IP: %s on %s", ip, path)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Max {GENERAL_RATE_LIMIT} per {GENERAL_RATE_WINDOW}s.",
                )

        return await call_next(request)


# -----------------------------------------------------------------------------
# SECURITY HEADERS MIDDLEWARE
#
# These HTTP headers tell browsers how to behave with your API responses.
# They're a first line of defence against common web attacks.
#
# X-Content-Type-Options: nosniff
#   Stops browsers "guessing" the content type. Prevents a PNG that secretly
#   contains HTML from being executed as HTML (MIME sniffing attack).
#
# X-Frame-Options: DENY
#   Stops your API responses from being loaded inside an <iframe>.
#   Prevents clickjacking — attacker overlays your UI invisibly inside theirs.
#
# X-XSS-Protection: 1; mode=block
#   Tells older browsers to block pages if XSS is detected.
#   Modern browsers have this built in, but good to include for compatibility.
#
# Strict-Transport-Security (HSTS)
#   Tells browsers: "always use HTTPS for this domain, never HTTP".
#   max-age=31536000 = 1 year. Only active in production (needs real HTTPS).
#
# Content-Security-Policy
#   The most powerful header — controls what resources the browser can load.
#   "default-src 'none'" blocks everything by default. Then we allow
#   only what we need. For a pure API (no HTML pages), this is simple.
# -----------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.ENVIRONMENT in ["local", "development"] or settings.TESTING:
            return await call_next(request)
        
        response = await call_next(request)

        # Common headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        path = request.url.path

        # 🔥 Route-based CSP
        if path.startswith("/docs") or path.startswith("/redoc"):
            # Swagger / ReDoc needs relaxed policy
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net;"
            )
        else:
            # 🔒 Strict CSP for API
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none'; "
                "base-uri 'none'; "
                "form-action 'self';"
            )


        return response