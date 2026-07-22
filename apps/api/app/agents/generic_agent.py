"""
Single-node fallback graph for agent types without a dedicated multi-step
graph (`prospect_analysis`, `meeting`, `crm`, `analytics`, `orchestrator`).
Reproduces module 04's original one-shot-call behavior exactly (call the
model once, parse JSON if requested) but through the same graph/streaming/
checkpointing machinery every other job type uses — so `execute_job` has one
uniform "resolve a graph, invoke it" code path instead of a special case for
"job types without a graph".
"""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.agents.base import call_model, parse_json_content, step


class GenericState(TypedDict):
    job_id: Any
    system_prompt: str
    user_prompt: str
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    api_key: str | None
    base_url: str | None
    response_format: str
    output_content: str | None
    output_json: dict | list | None


@step("run_llm")
async def run_llm_node(state: GenericState, config: RunnableConfig) -> dict:
    content = await call_model(state, config)
    output_json = parse_json_content(content) if state.get("response_format") == "json" else None
    return {"output_content": content, "output_json": output_json}


def build_graph() -> StateGraph:
    graph = StateGraph(GenericState)
    graph.add_node("run_llm", run_llm_node)
    graph.set_entry_point("run_llm")
    graph.add_edge("run_llm", END)
    return graph
