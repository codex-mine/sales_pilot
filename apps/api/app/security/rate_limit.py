"""
Redis-backed brute-force protection.

Two independent counters guard the login endpoint:
- A per-IP fixed-window rate limit (`login_rate_limit_*`) — cheap DoS/credential-
  stuffing throttle that doesn't care whose account is being tried.
- A per-user lockout counter (`account_lockout_*`) — protects one specific
  account from being hammered even from many IPs (distributed brute force).

Both live in Redis rather than Postgres because they are naturally
self-expiring (TTL) and are read/written on every login attempt — a hot path
that should not add write load to the primary database.
"""

from redis.asyncio import Redis

from app.core.config import get_settings
from app.exceptions.errors import AccountLockedError, RateLimitExceededError


def _ip_key(ip_address: str) -> str:
    return f"ratelimit:login:ip:{ip_address}"


def _lockout_failures_key(user_id: str) -> str:
    return f"lockout:failures:{user_id}"


def _lockout_key(user_id: str) -> str:
    return f"lockout:locked:{user_id}"


async def check_login_rate_limit(redis: Redis, ip_address: str) -> None:
    settings = get_settings()
    key = _ip_key(ip_address)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, settings.login_rate_limit_window_seconds)
    if count > settings.login_rate_limit_attempts:
        raise RateLimitExceededError("Too many login attempts. Please try again later.")


async def check_account_lockout(redis: Redis, user_id: str) -> None:
    if await redis.exists(_lockout_key(user_id)):
        raise AccountLockedError()


async def record_failed_login(redis: Redis, user_id: str) -> None:
    settings = get_settings()
    key = _lockout_failures_key(user_id)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, settings.account_lockout_window_seconds)
    if count >= settings.account_lockout_threshold:
        await redis.set(_lockout_key(user_id), "1", ex=settings.account_lockout_duration_seconds)


async def clear_login_failures(redis: Redis, user_id: str) -> None:
    await redis.delete(_lockout_failures_key(user_id), _lockout_key(user_id))
