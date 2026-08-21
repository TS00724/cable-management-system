from __future__ import annotations

import hmac
import math
import threading
import time
import uuid
from dataclasses import dataclass

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_epoch: int


class FixedWindowRateLimiter:
    """Small single-process development limiter.

    Production replicas must replace this with a shared atomic backend; the class is deliberately
    isolated so that swap does not affect endpoint authorization code.
    """

    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, int]] = {}

    def consume(self, key: str, *, now: float | None = None) -> RateLimitDecision:
        timestamp = now if now is not None else time.time()
        window_start = int(timestamp // self.window_seconds) * self.window_seconds
        reset_epoch = window_start + self.window_seconds
        with self._lock:
            previous = self._windows.get(key)
            count = previous[1] if previous and previous[0] == window_start else 0
            count += 1
            self._windows[key] = (window_start, count)
            # Opportunistic cleanup keeps cardinality bounded in long-running development servers.
            if len(self._windows) > 10000:
                stale_before = window_start - self.window_seconds
                self._windows = {
                    item_key: item for item_key, item in self._windows.items() if item[0] >= stale_before
                }
        allowed = count <= self.limit
        return RateLimitDecision(
            allowed=allowed,
            limit=self.limit,
            remaining=max(self.limit - count, 0),
            reset_epoch=reset_epoch,
        )


class SecurityBoundaryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.settings = settings
        self.limiter = FixedWindowRateLimiter(
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )

    def _trusted_proxy(self, request: Request) -> bool:
        peer = request.client.host if request.client else ""
        return peer in self.settings.trusted_proxy_ips

    def _client_address(self, request: Request) -> str:
        if self._trusted_proxy(request):
            forwarded = request.headers.get("x-forwarded-for", "")
            candidate = forwarded.split(",", 1)[0].strip()
            if candidate:
                return candidate
        return request.client.host if request.client else "unknown"

    def _secure_request(self, request: Request) -> bool:
        if request.url.scheme == "https":
            return True
        if self._trusted_proxy(request):
            return request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip() == "https"
        return False

    def _add_security_headers(
        self,
        response: Response,
        *,
        request_id: str,
        secure_request: bool,
        rate: RateLimitDecision | None,
    ) -> None:
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'self'; frame-ancestors 'none'"
        )
        if secure_request and self.settings.hsts_max_age > 0:
            value = f"max-age={self.settings.hsts_max_age}"
            if self.settings.hsts_include_subdomains:
                value += "; includeSubDomains"
            if self.settings.hsts_preload:
                value += "; preload"
            response.headers["Strict-Transport-Security"] = value
        if rate is not None:
            response.headers["X-RateLimit-Limit"] = str(rate.limit)
            response.headers["X-RateLimit-Remaining"] = str(rate.remaining)
            response.headers["X-RateLimit-Reset"] = str(rate.reset_epoch)

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        secure_request = self._secure_request(request)

        if self.settings.require_https and not secure_request:
            response = JSONResponse(
                status_code=426,
                content={"detail": "HTTPS is required", "request_id": request_id},
            )
            self._add_security_headers(
                response, request_id=request_id, secure_request=False, rate=None
            )
            return response

        rate: RateLimitDecision | None = None
        if (
            self.settings.rate_limit_enabled
            and request.method != "OPTIONS"
            and request.url.path not in self.settings.rate_limit_exempt_paths
        ):
            rate = self.limiter.consume(self._client_address(request))
            if not rate.allowed:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "request_id": request_id},
                )
                response.headers["Retry-After"] = str(
                    max(rate.reset_epoch - math.floor(time.time()), 1)
                )
                self._add_security_headers(
                    response,
                    request_id=request_id,
                    secure_request=secure_request,
                    rate=rate,
                )
                return response

        if (
            self.settings.cookie_auth_enabled
            and request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
            and request.cookies.get(self.settings.auth_cookie_name)
            and not request.headers.get("authorization")
        ):
            cookie_token = request.cookies.get(self.settings.csrf_cookie_name)
            header_token = request.headers.get(self.settings.csrf_header_name)
            if (
                not cookie_token
                or not header_token
                or not hmac.compare_digest(cookie_token, header_token)
            ):
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token validation failed", "request_id": request_id},
                )
                self._add_security_headers(
                    response,
                    request_id=request_id,
                    secure_request=secure_request,
                    rate=rate,
                )
                return response

        response = await call_next(request)
        if request.url.path.startswith(self.settings.api_prefix):
            response.headers.setdefault("Cache-Control", "no-store")
        self._add_security_headers(
            response,
            request_id=request_id,
            secure_request=secure_request,
            rate=rate,
        )
        return response
