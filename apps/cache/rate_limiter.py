"""Rate limiting using Redis."""

import logging
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .redis_manager import RedisManager

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter using Redis."""

    def __init__(
        self,
        redis_manager: RedisManager,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_manager: Redis manager instance
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
        """
        self.redis = redis_manager
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.prefix_minute = "ratelimit:minute:"
        self.prefix_hour = "ratelimit:hour:"

    def _get_identifier(self, request: Request) -> str:
        """
        Get client identifier from request.

        Args:
            request: FastAPI request

        Returns:
            Client identifier (IP or user_id)
        """
        # Try to get user_id from session/auth (placeholder for now)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    async def check_rate_limit(
        self, identifier: str, window: str = "minute"
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Client identifier
            window: Rate limit window ("minute" or "hour")

        Returns:
            Tuple of (allowed, current_count, limit)
        """
        if window == "minute":
            prefix = self.prefix_minute
            limit = self.requests_per_minute
            ttl = 60
        else:
            prefix = self.prefix_hour
            limit = self.requests_per_hour
            ttl = 3600

        key = f"{prefix}{identifier}"

        # Get current count
        current = await self.redis.get(key)
        current_count = int(current) if current else 0

        # Check if over limit
        if current_count >= limit:
            logger.warning(
                f"Rate limit exceeded for {identifier}: {current_count}/{limit} ({window})"
            )
            return False, current_count, limit

        # Increment counter
        new_count = await self.redis.incr(key)

        # Set TTL on first request
        if new_count == 1:
            await self.redis.expire(key, ttl)

        return True, new_count, limit

    async def is_allowed(self, identifier: str) -> tuple[bool, dict]:
        """
        Check if request is allowed (both minute and hour limits).

        Args:
            identifier: Client identifier

        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        # Check minute limit
        minute_allowed, minute_count, minute_limit = await self.check_rate_limit(
            identifier, "minute"
        )

        # Check hour limit
        hour_allowed, hour_count, hour_limit = await self.check_rate_limit(
            identifier, "hour"
        )

        allowed = minute_allowed and hour_allowed

        rate_limit_info = {
            "minute": {
                "count": minute_count,
                "limit": minute_limit,
                "remaining": max(0, minute_limit - minute_count),
            },
            "hour": {
                "count": hour_count,
                "limit": hour_limit,
                "remaining": max(0, hour_limit - hour_count),
            },
        }

        return allowed, rate_limit_info

    async def reset_limit(self, identifier: str):
        """
        Reset rate limits for identifier.

        Args:
            identifier: Client identifier
        """
        minute_key = f"{self.prefix_minute}{identifier}"
        hour_key = f"{self.prefix_hour}{identifier}"

        await self.redis.delete(minute_key)
        await self.redis.delete(hour_key)

        logger.info(f"Reset rate limits for {identifier}")

    async def get_remaining_ttl(
        self, identifier: str, window: str = "minute"
    ) -> int:
        """
        Get remaining TTL for rate limit window.

        Args:
            identifier: Client identifier
            window: Rate limit window

        Returns:
            Remaining TTL in seconds
        """
        prefix = (
            self.prefix_minute if window == "minute" else self.prefix_hour
        )
        key = f"{prefix}{identifier}"
        return await self.redis.ttl(key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI."""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/v1/health"]:
            return await call_next(request)

        # Get client identifier
        identifier = self.rate_limiter._get_identifier(request)

        # Check rate limit
        try:
            allowed, rate_limit_info = await self.rate_limiter.is_allowed(
                identifier
            )

            # Add rate limit headers to response
            response = None
            if allowed:
                response = await call_next(request)
            else:
                # Rate limit exceeded
                ttl = await self.rate_limiter.get_remaining_ttl(
                    identifier, "minute"
                )
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "retry_after": ttl,
                        "rate_limit": rate_limit_info,
                    },
                )

            # Add rate limit headers
            response.headers["X-RateLimit-Limit-Minute"] = str(
                rate_limit_info["minute"]["limit"]
            )
            response.headers["X-RateLimit-Remaining-Minute"] = str(
                rate_limit_info["minute"]["remaining"]
            )
            response.headers["X-RateLimit-Limit-Hour"] = str(
                rate_limit_info["hour"]["limit"]
            )
            response.headers["X-RateLimit-Remaining-Hour"] = str(
                rate_limit_info["hour"]["remaining"]
            )

            return response

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # On error, allow request to proceed
            return await call_next(request)


# Decorator for route-specific rate limiting
def rate_limit(
    requests_per_minute: Optional[int] = None,
    requests_per_hour: Optional[int] = None,
):
    """
    Decorator for route-specific rate limiting.

    Args:
        requests_per_minute: Custom per-minute limit
        requests_per_hour: Custom per-hour limit
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This is a placeholder for route-specific limiting
            # Implementation would require accessing rate limiter from request state
            return await func(*args, **kwargs)

        return wrapper

    return decorator
