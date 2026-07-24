"""
Module 13 (AI -> LangGraph Agent Engine + Live Execution Streaming) tests
specific to what this module adds on top of module 04's execution engine —
the job-lifecycle/output-shape regression coverage for research/email/reply
already lives in test_research.py/test_email_generation.py/test_inbox.py
(updated to mock the new `get_chat_model` seam, still exercising the exact
same behavior those suites always asserted). This file covers what's new:

- CostTrackingCallbackHandler sums tokens across multiple LLM calls in one
  graph run (not just the module 04-era single-call case).
- publish_step lands messages on the correct Redis channel.
- email_agent's self_critique node actually triggers one regeneration pass
  when it fails, and stops after exactly one retry.
- The WebSocket endpoint rejects missing/invalid auth and cross-tenant job
  access, and sends the job's current state immediately on connect (mid-run
  join).
"""

import json
import uuid
from contextlib import asynccontextmanager

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient, WebSocketDisconnect

from app.core.config import get_settings
from app.database.session import engine as real_engine
from app.database.session import get_db
from app.main import app
from app.models.enums import AIAgentTypeEnum, LLMProviderEnum
from app.services.ai.cost_tracking_callback import CostTrackingCallbackHandler
from app.tests.ai_fakes import FakeChatModel
from app.tests.conftest import register_user

pytestmark = pytest.mark.asyncio


@asynccontextmanager
async def _real_db_for_ws():
    """`TestClient.websocket_connect` runs the ASGI app in its own thread
    with its own event loop (via an anyio portal) — a different loop each
    time a *new* `TestClient` is entered, and a different loop than
    pytest-asyncio's, which the `client`/`db` fixtures' `get_db` override is
    bound to (asyncpg connections are loop-bound, same reasoning
    `app/workers/session_utils.py` documents). Temporarily removing the
    override lets the route use the real `get_db` instead — the committed
    data from the fixture-driven setup above is still visible to it, since
    it's a separate connection to the same Postgres database, not a
    separate database — but the real `get_db`'s module-level `engine` is
    itself a *pool*, so a connection it hands out during one WS test can
    still be sitting in the pool, bound to that test's now-dead loop, when
    the next WS test's differently-threaded `TestClient` asks for one;
    disposing it up front forces a fresh connection on the current loop."""
    saved = app.dependency_overrides.pop(get_db, None)
    await real_engine.dispose()
    try:
        yield
    finally:
        if saved is not None:
            app.dependency_overrides[get_db] = saved


# ─── Cost callback: sums across multiple calls in one run ────────────────────


async def test_cost_callback_sums_tokens_across_multiple_calls(monkeypatch) -> None:
    from langchain_core.messages import HumanMessage, SystemMessage

    stub = FakeChatModel(content="ok")
    handler = CostTrackingCallbackHandler()

    await stub.ainvoke([SystemMessage(content="s"), HumanMessage(content="u")], config={"callbacks": [handler]})
    await stub.ainvoke([SystemMessage(content="s"), HumanMessage(content="u")], config={"callbacks": [handler]})

    assert handler.call_count == 2
    assert handler.input_tokens == 200  # 100 per call, summed not overwritten
    assert handler.output_tokens == 100  # 50 per call, summed not overwritten
    assert handler.cost_usd(LLMProviderEnum.ANTHROPIC, "claude-sonnet-5") > 0


# ─── publish_step -> Redis channel ────────────────────────────────────────────


async def test_publish_step_lands_on_the_correct_redis_channel(redis) -> None:
    from app.agents.base import StepEvent, publish_step

    job_id = uuid.uuid4()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"ai_job:{job_id}")
    await pubsub.get_message(timeout=1)  # discard the subscribe confirmation

    from datetime import datetime, timezone

    await publish_step(job_id, StepEvent(node="run_llm", status="started", timestamp=datetime.now(timezone.utc)))

    message = await pubsub.get_message(timeout=2)
    assert message is not None
    payload = json.loads(message["data"])
    assert payload["node"] == "run_llm"
    assert payload["status"] == "started"
    await pubsub.unsubscribe()
    await pubsub.aclose()


# ─── email_agent self_critique: one regeneration pass, then stop ─────────────


async def test_self_critique_triggers_exactly_one_regeneration_then_finalizes(monkeypatch) -> None:
    from app.agents.base import checkpointer_context
    from app.agents.email_agent import build_graph

    generate_calls: list[str] = []

    def responder(system_prompt: str, user_prompt: str) -> str:
        if "strict editor" in system_prompt:
            # Fails the FIRST time (when the generation prompt has not yet
            # been retried), passes on the second — proves the loop
            # actually re-runs generate_variants with feedback rather than
            # always passing or looping forever.
            already_retried = len(generate_calls) >= 2
            return json.dumps({"passes": already_retried, "feedback": "Too generic, mentions no specifics."})
        generate_calls.append(user_prompt)
        return json.dumps([{"subject": "Hi", "body_html": "<p>Hi</p>", "body_text": "Hi", "reasoning": "x"}])

    stub = FakeChatModel(responder=responder)
    monkeypatch.setattr("app.agents.base.get_chat_model", lambda *a, **k: stub)

    job_id = uuid.uuid4()
    initial_state = {
        "job_id": job_id,
        "system_prompt": "You are an expert sales development representative.",
        "user_prompt": "Write an email.",
        "provider": "anthropic",
        "model_name": "claude-haiku-4-5",
        "temperature": 0.7,
        "max_tokens": 512,
        "api_key": "fake",
        "base_url": None,
        "response_format": "json",
        "variants": None,
        "critique_passed": None,
        "critique_feedback": None,
        "critique_attempts": 0,
        "output_content": None,
        "output_json": None,
    }

    async with checkpointer_context() as checkpointer:
        graph = build_graph().compile(checkpointer=checkpointer)
        final_state = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": str(job_id)}})

    # generate_variants ran twice: once, got rejected, ran again with the
    # critique's feedback folded into the retry prompt.
    assert len(generate_calls) == 2
    assert "Too generic" in generate_calls[1]
    assert final_state["critique_attempts"] == 2
    assert final_state["output_json"][0]["subject"] == "Hi"


async def test_self_critique_stops_after_one_retry_even_if_still_failing(monkeypatch) -> None:
    """Never loops forever: if the critique keeps failing, the graph still
    finalizes after exactly one regeneration pass."""
    from app.agents.base import checkpointer_context
    from app.agents.email_agent import build_graph

    call_count = {"generate": 0}

    def responder(system_prompt: str, _user_prompt: str) -> str:
        if "strict editor" in system_prompt:
            return json.dumps({"passes": False, "feedback": "Still too generic."})
        call_count["generate"] += 1
        return json.dumps([{"subject": "Hi", "body_html": "<p>Hi</p>", "body_text": "Hi", "reasoning": "x"}])

    stub = FakeChatModel(responder=responder)
    monkeypatch.setattr("app.agents.base.get_chat_model", lambda *a, **k: stub)

    job_id = uuid.uuid4()
    initial_state = {
        "job_id": job_id, "system_prompt": "sys", "user_prompt": "usr", "provider": "anthropic",
        "model_name": "claude-haiku-4-5", "temperature": 0.7, "max_tokens": 512, "api_key": "fake",
        "base_url": None, "response_format": "json", "variants": None, "critique_passed": None,
        "critique_feedback": None, "critique_attempts": 0, "output_content": None, "output_json": None,
    }
    async with checkpointer_context() as checkpointer:
        graph = build_graph().compile(checkpointer=checkpointer)
        final_state = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": str(job_id)}})

    assert call_count["generate"] == 2  # original + exactly one retry, never more
    assert final_state["critique_attempts"] == 2
    assert final_state["output_json"] is not None  # still finalizes despite never "passing"


# ─── WebSocket endpoint ────────────────────────────────────────────────────────


def _org_id(registration: dict) -> str:
    return registration["data"]["organization_id"]


async def _run_completed_research_job(db: AsyncSession, organization_id: str) -> str:
    from app.services.ai.ai_job_service import AIJobService

    job = await AIJobService(db).run_job(
        organization_id=uuid.UUID(organization_id),
        job_type="research_company", entity_type=None, entity_id=None,
        prompt_template_name="research_company",
        variables={"company_name": "Acme", "context": "A SaaS company."},
        agent_type=AIAgentTypeEnum.RESEARCH, initiated_by=None,
    )
    return str(job.id)


async def test_websocket_rejects_missing_token(client: AsyncClient) -> None:
    await register_user(client)
    # A syntactically valid but nonexistent job id is enough to test the
    # missing-token rejection path — auth is checked before the job lookup.
    fake_job_id = uuid.uuid4()
    async with _real_db_for_ws():
        with TestClient(app) as test_client:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                with test_client.websocket_connect(f"/api/v1/ws/ai-jobs/{fake_job_id}"):
                    pass
            assert excinfo.value.code == 4401


async def test_websocket_rejects_invalid_token(client: AsyncClient) -> None:
    await register_user(client)
    fake_job_id = uuid.uuid4()
    async with _real_db_for_ws():
        with TestClient(app) as test_client:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                with test_client.websocket_connect(f"/api/v1/ws/ai-jobs/{fake_job_id}?token=not-a-real-jwt"):
                    pass
            assert excinfo.value.code == 4401


async def test_websocket_sends_current_state_immediately_on_connect(
    db: AsyncSession, client: AsyncClient, monkeypatch
) -> None:
    """Mid-run join: a client connecting to an already-terminal job still
    gets its state immediately (no need to wait on a step event that will
    never come, since the graph already finished)."""
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    stub = FakeChatModel(content=json.dumps({"summary": "ok"}))
    monkeypatch.setattr("app.agents.base.get_chat_model", lambda *a, **k: stub)

    registration = await register_user(client)
    job_id = await _run_completed_research_job(db, _org_id(registration))

    access_token = client.cookies.get("access_token")
    assert access_token

    async with _real_db_for_ws():
        with TestClient(app) as test_client:
            with test_client.websocket_connect(f"/api/v1/ws/ai-jobs/{job_id}?token={access_token}") as ws:
                message = ws.receive_json()
                assert message["type"] == "job_state"
                assert message["job"]["id"] == job_id
                assert message["job"]["status"] == "completed"
                # Already terminal — the server closes right after, no
                # further messages should ever arrive.


async def test_websocket_rejects_cross_tenant_job_access(
    db: AsyncSession, client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "ai_execute_jobs_eagerly", True)
    stub = FakeChatModel(content=json.dumps({"summary": "ok"}))
    monkeypatch.setattr("app.agents.base.get_chat_model", lambda *a, **k: stub)

    registration = await register_user(client)
    job_id = await _run_completed_research_job(db, _org_id(registration))

    other_client = AsyncClient(transport=client._transport, base_url="http://test")
    await register_user(other_client)
    other_token = other_client.cookies.get("access_token")
    assert other_token
    await other_client.aclose()

    async with _real_db_for_ws():
        with TestClient(app) as test_client:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                with test_client.websocket_connect(f"/api/v1/ws/ai-jobs/{job_id}?token={other_token}"):
                    pass
            assert excinfo.value.code == 4404
