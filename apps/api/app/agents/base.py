"""
Shared LangGraph plumbing: step-event streaming, the Postgres checkpointer,
and the JSON output parser every graph's final "produce the AIOutput payload"
node uses.

--- Checkpointer lifecycle ---
`AsyncPostgresSaver` holds a live psycopg connection, which — exactly like
`app/workers/session_utils.py`'s async SQLAlchemy engine — is bound to the
event loop it was created on. Celery tasks run each invocation in a fresh
`asyncio.run(...)` loop, so a single long-lived module-level checkpointer
would break the same way a shared global DB engine would. `checkpointer_context()`
therefore opens one per graph invocation (mirroring `run_with_fresh_session`'s
per-invocation engine) rather than once at import time — this is why the
graph builders in this package export an *uncompiled* `StateGraph`
(`build_graph()`) instead of a module-level `graph.compile(checkpointer=...)`:
compiation (pure Python wiring, no I/O) happens fresh alongside the
checkpointer in `AIJobService.execute_job`.

Uses the existing `database_url` — no new datastore, just new tables
(`checkpoints`/`checkpoint_writes`/...) in the same Postgres, created
idempotently by `.setup()` the first time a process needs them.
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Literal
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel
from redis.asyncio import Redis

from app.core.config import get_settings
from app.exceptions.errors import AIOutputParsingError
from app.models.enums import LLMProviderEnum
from app.services.ai.llm_client import get_chat_model

def _psycopg_conn_string() -> str:
    """`database_url` is a SQLAlchemy asyncpg URL (`postgresql+asyncpg://...`);
    `langgraph-checkpoint-postgres` uses psycopg3 (already an app dependency
    for Alembic's sync migrations), which wants the plain `postgresql://` form."""
    return get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://")


# Arbitrary fixed key for the advisory lock below — any int64 works, it just
# needs to be the same constant every caller uses.
_BOOTSTRAP_LOCK_KEY = 0x53414C_43_484B  # "SALES_CHK" as hex-ish, unique to this purpose


async def bootstrap_checkpoint_tables() -> None:
    """Creates the checkpointer's tables (`checkpoints`/`checkpoint_writes`/...)
    if they don't exist yet. Must run exactly once, before any job execution
    — NOT lazily on first use inside `checkpointer_context()` — because
    `AsyncPostgresSaver.setup()` runs `CREATE INDEX CONCURRENTLY`, which
    blocks until every transaction that was already open anywhere in the
    database finishes. Since `AIJobService.execute_job`'s own `db` session
    always has an implicit transaction open by the time it would reach the
    checkpointer (from the `resolve_credentials` SELECT immediately before
    it), calling `.setup()` from inside that same call path deadlocks the
    process against itself. Called once at true process startup instead
    (`app/main.py`'s lifespan, `app/workers/celery_app.py`'s import time, and
    the test suite's session-scoped schema fixture) — see each call site.

    `docker-compose.yml` starts `api`/`worker`/`beat` without sequencing them
    relative to each other, so on a brand-new database more than one process
    can call this at once — wrapped in a Postgres advisory lock (held on a
    connection separate from the checkpointer's own) so they serialize
    instead of racing each other's `CREATE INDEX CONCURRENTLY IF NOT EXISTS`."""
    import psycopg

    async with await psycopg.AsyncConnection.connect(_psycopg_conn_string(), autocommit=True) as lock_conn:
        await lock_conn.execute("SELECT pg_advisory_lock(%s)", (_BOOTSTRAP_LOCK_KEY,))
        try:
            async with AsyncPostgresSaver.from_conn_string(_psycopg_conn_string()) as checkpointer:
                await checkpointer.setup()
        finally:
            await lock_conn.execute("SELECT pg_advisory_unlock(%s)", (_BOOTSTRAP_LOCK_KEY,))


@asynccontextmanager
async def checkpointer_context() -> AsyncIterator[AsyncPostgresSaver]:
    async with AsyncPostgresSaver.from_conn_string(_psycopg_conn_string()) as checkpointer:
        yield checkpointer


# ─── Step-event streaming ────────────────────────────────────────────────────


class StepEvent(BaseModel):
    node: str
    status: Literal["started", "completed", "failed"]
    detail: str | None = None
    timestamp: datetime


async def publish_step(job_id: UUID, event: StepEvent) -> None:
    """The ONE place streaming events get published — every graph node calls
    this the same way (via the `@step(...)` decorator below), never
    constructing the Redis publish call itself.

    Deliberately does NOT use `app.core.redis.get_redis_pool()` — that pool
    is `@lru_cache`d at process scope, which is safe for the API process
    (one long-lived event loop for the process's whole life) but not here:
    a Celery task's `asyncio.run(...)` (see `app/workers/session_utils.py`)
    creates a fresh event loop per invocation, and a pooled connection
    handed out on one invocation's loop is unusable — and breaks with
    "Event loop is closed" — on the next. Same fresh-per-invocation
    reasoning as `checkpointer_context()` and `run_with_fresh_session`."""
    client = Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        await client.publish(f"ai_job:{job_id}", event.model_dump_json())
    finally:
        await client.aclose()


def step(node_name: str):
    """Wraps a LangGraph node coroutine so entering/leaving it always
    publishes the matching `StepEvent` — nodes never call `publish_step`
    themselves, so the publish shape can't drift between agents. The wrapped
    node must return a state dict containing `job_id`."""

    def decorator(fn):
        @wraps(fn)
        async def wrapper(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
            job_id = state["job_id"]
            await publish_step(job_id, StepEvent(node=node_name, status="started", timestamp=_now()))
            try:
                result = await fn(state, config)
            except Exception as exc:  # noqa: BLE001 — re-raised so the graph's/AIJob's own failure path still fires
                await publish_step(
                    job_id, StepEvent(node=node_name, status="failed", detail=str(exc), timestamp=_now())
                )
                raise
            await publish_step(job_id, StepEvent(node=node_name, status="completed", timestamp=_now()))
            return result

        return wrapper

    return decorator


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Shared model-call primitive ─────────────────────────────────────────────
# Every LLM-calling node across research/email/reply/generic builds the model
# and sends the same system+user message pair the same way — one
# implementation, imported everywhere, instead of copied per agent.


async def call_model(state: dict[str, Any], config: RunnableConfig) -> str:
    model = get_chat_model(
        LLMProviderEnum(state["provider"]),
        state["model_name"],
        api_key=state.get("api_key"),
        base_url=state.get("base_url"),
        temperature=state["temperature"],
        max_tokens=state["max_tokens"],
    )
    messages = [SystemMessage(content=state["system_prompt"]), HumanMessage(content=state["user_prompt"])]
    response = await model.ainvoke(messages, config=config)
    content = response.content
    return content if isinstance(content, str) else str(content)


# ─── Structured-output parsing ───────────────────────────────────────────────
# Moved here (as `parse_json_content`, was `AIJobService._parse_json_content`)
# since every LLM-calling node across research/email/reply/generic needs the
# exact same defensive parse — kept as the one implementation, imported
# everywhere instead of copied.


def parse_json_content(text: str) -> dict | list:
    """Defensive JSON parse for `response_format="json"` jobs: strips a
    ```json fence some models still wrap output in despite being told to
    return raw JSON, then requires a JSON object or array (not a bare
    scalar/null)."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise AIOutputParsingError(f"Model returned malformed JSON: {exc}") from exc
    if not isinstance(parsed, (dict, list)):
        raise AIOutputParsingError("Model output was valid JSON but not a JSON object or array.")
    return parsed
