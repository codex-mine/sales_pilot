"""
Shared pytest fixtures for the auth test suite.

Test isolation strategy:
- A dedicated Postgres database (never the dev database) is created once per
  session from the current models (`Base.metadata.create_all`), bypassing
  Alembic for speed — migration correctness is verified separately via
  `alembic check` (see MIGRATIONS.md), so tests only need the schema to exist.
- Tables are truncated after every test. A per-test SAVEPOINT/rollback
  wouldn't work here: AuthService commits mid-flow (register, login, password
  reset all call `db.commit()` themselves), which ends any wrapping
  transaction early, so truncation is the only reliable reset.
- Redis uses a dedicated logical DB (index 15) and is flushed after every
  test, so rate-limit/lockout counters never leak across tests.
"""

import os
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/ai_sales_agent_test",
)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')

from app.core.redis import get_redis  # noqa: E402
from app.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
TEST_REDIS_URL = os.environ["REDIS_URL"]

_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Module 13's LangGraph checkpointer tables — must be created once here,
    # before any test executes an AI job, never lazily inside one (see
    # `bootstrap_checkpoint_tables`'s docstring for the deadlock this avoids).
    from app.agents.base import bootstrap_checkpoint_tables

    await bootstrap_checkpoint_tables()
    yield
    await _engine.dispose()


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionLocal() as session:
        yield session
    # A single TRUNCATE listing every table sidesteps FK ordering entirely
    # (Postgres only enforces FK constraints against tables *not* in the
    # statement) — necessary here since organizations<->users has a genuine
    # constraint cycle that `sorted_tables` cannot fully order.
    table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with _engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))


@pytest_asyncio.fixture
async def redis() -> AsyncGenerator[Redis, None]:
    client = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def client(db: AsyncSession, redis: Redis) -> AsyncGenerator[AsyncClient, None]:
    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        yield db

    async def _get_redis_override() -> AsyncGenerator[Redis, None]:
        yield redis

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_redis] = _get_redis_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


REGISTER_PAYLOAD = {
    "password": "Str0ng!Passw0rd",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "organization_name": "Acme Inc",
}


async def register_user(client: AsyncClient, *, email: str | None = None) -> dict:
    payload = {**REGISTER_PAYLOAD, "email": email or unique_email()}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
