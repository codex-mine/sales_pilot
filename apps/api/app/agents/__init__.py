"""
LangGraph agent graphs for the AI execution engine (module 13).

Each `*_agent.py` file exports `build_graph() -> StateGraph`, an uncompiled
graph builder — compilation happens per Celery-task-invocation in
`AIJobService.execute_job`, together with a per-invocation checkpointer (see
`app/agents/base.py` for why: the same "no long-lived event-loop-bound
resource across `asyncio.run` calls" constraint `app/workers/session_utils.py`
already documents for the DB engine applies here too).

`get_graph_builder(agent_type)` is the one dispatch point mapping an
`AIAgentTypeEnum` to its graph builder, used by `execute_job` so it never
branches on agent type itself.
"""

from collections.abc import Callable

from langgraph.graph import StateGraph

from app.models.enums import AIAgentTypeEnum

_BUILDERS: dict[AIAgentTypeEnum, Callable[[], StateGraph]] = {}


def _registry() -> dict[AIAgentTypeEnum, Callable[[], StateGraph]]:
    if not _BUILDERS:
        from app.agents.email_agent import build_graph as build_email_graph
        from app.agents.generic_agent import build_graph as build_generic_graph
        from app.agents.reply_agent import build_graph as build_reply_graph
        from app.agents.research_agent import build_graph as build_research_graph

        _BUILDERS[AIAgentTypeEnum.RESEARCH] = build_research_graph
        _BUILDERS[AIAgentTypeEnum.EMAIL_GENERATION] = build_email_graph
        _BUILDERS[AIAgentTypeEnum.REPLY_ANALYSIS] = build_reply_graph
        for agent_type in AIAgentTypeEnum:
            _BUILDERS.setdefault(agent_type, build_generic_graph)
    return _BUILDERS


def get_graph_builder(agent_type: AIAgentTypeEnum) -> Callable[[], StateGraph]:
    """Every agent type resolves to *some* graph — research/email_generation/
    reply_analysis get their dedicated multi-step graph; everything else
    (orchestrator, prospect_analysis, meeting, crm, analytics) falls back to
    `generic_agent`'s single-node graph, which reproduces module 04's
    original one-shot-call behavior exactly, just running through the same
    graph/streaming/checkpointing machinery so `execute_job` has one uniform
    code path instead of a special case for "jobs without a graph"."""
    return _registry()[agent_type]
