"""
Celery task for asynchronous AI job execution (the `ai` queue).

Celery tasks are synchronous; each invocation runs the async service body in
a fresh event loop with a task-local engine/session (asyncpg connections are
loop-bound, so reusing the web process's global engine across `asyncio.run`
calls would break — a per-invocation engine, disposed in `finally`, is the
reliable pattern).

Retries: bounded by `ai_max_retries`. Between attempts the job row is marked
RETRYING with retry_count incremented; after the final attempt it stays
FAILED — the failure is never silently swallowed.
"""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.workers.celery_app import celery_app


async def _run_with_fresh_session(coro_factory) -> None:
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with session_factory() as session:
            await coro_factory(session)
    finally:
        await engine.dispose()


@celery_app.task(
    bind=True,
    name="ai.execute_ai_job",
    max_retries=None,  # bounded manually below from settings/job state
    acks_late=True,
)
def execute_ai_job(self, job_id: str, organization_id: str) -> None:
    from app.services.ai.ai_job_service import AIJobService

    job_uuid = uuid.UUID(job_id)
    org_uuid = uuid.UUID(organization_id)
    settings = get_settings()

    async def _execute(session: AsyncSession) -> None:
        await AIJobService(session).execute_job(job_uuid, org_uuid)

    async def _mark_retrying(session: AsyncSession) -> None:
        await AIJobService(session).mark_retrying(job_uuid, org_uuid)

    try:
        asyncio.run(_run_with_fresh_session(_execute))
    except Exception as exc:
        if self.request.retries < settings.ai_max_retries:
            asyncio.run(_run_with_fresh_session(_mark_retrying))
            raise self.retry(exc=exc, countdown=2**self.request.retries * 5) from exc
        # Final attempt: execute_job already left the row FAILED with the
        # error captured — re-raise so Celery records the task failure too.
        raise
