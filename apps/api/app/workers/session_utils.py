"""Shared per-invocation DB session helper for Celery task bodies.

Celery tasks are synchronous; each invocation runs its async service body in
a fresh event loop with a task-local engine/session (asyncpg connections are
loop-bound, so reusing the web process's global engine across `asyncio.run`
calls would break — a per-invocation engine, disposed in `finally`, is the
reliable pattern). Extracted here so every task module (`ai_tasks.py`,
`research_tasks.py`, ...) shares one implementation instead of copying it.
"""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


async def run_with_fresh_session(coro_factory: Callable[[AsyncSession], Awaitable[None]]) -> None:
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            await coro_factory(session)
    finally:
        await engine.dispose()
