"""
Shared Redis client.

Used for auth-adjacent ephemeral state that does not belong in PostgreSQL:
login rate limiting and account-lockout counters. Both are self-expiring by
nature (sliding/fixed windows), which is a poor fit for a durable relational
table — Redis TTLs give us that for free without a cleanup job.
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings


@lru_cache
def get_redis_pool() -> ConnectionPool:
    return ConnectionPool.from_url(get_settings().redis_url, decode_responses=True)


async def get_redis() -> AsyncGenerator[Redis, None]:
    client = Redis(connection_pool=get_redis_pool())
    try:
        yield client
    finally:
        await client.aclose()
