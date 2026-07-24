"""
StateGraph for Company Research (module 05).

Node shape note: the module spec for this graph names `fetch_website` /
`extract_content` nodes. In this codebase, `CompanyResearchService` (module
05) already fetches and truncates the company's website *before* calling
`AIJobService.run_job(...)` — the fetched material is rendered straight into
the prompt template as the `context` variable, and `run_job` stores the fully
rendered `system_prompt`/`user_prompt` on the AIJob row before this graph
ever runs. Re-fetching inside the graph would duplicate
`CompanyResearchService`'s own HTTP/robots.txt/BeautifulSoup logic — and this
module's constraint is explicit that "none of it required changing a single
line in modules 05-12's own service code". So the steps here reflect what
actually happens once the AIJob exists: preparing the already-gathered
context for the call, running it, then validating the structured result —
each still an independently visible/retryable node with its own streamed
step event, just not literally a website fetch.
"""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.agents.base import call_model, parse_json_content, step


class ResearchState(TypedDict):
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
    company_name: str | None
    data_quality: str | None
    output_content: str | None
    output_json: dict | list | None


@step("prepare_context")
async def prepare_context_node(state: ResearchState, config: RunnableConfig) -> dict:
    # The website fetch + context assembly already happened upstream in
    # CompanyResearchService before this AIJob was created (see module note
    # above) — this node's job is just to surface that as a visible,
    # streamed step rather than silently skipping straight to the model call.
    return {}


@step("run_research_llm")
async def run_research_llm_node(state: ResearchState, config: RunnableConfig) -> dict:
    content = await call_model(state, config)
    return {"output_content": content}


@step("parse_and_validate")
async def parse_and_validate_node(state: ResearchState, config: RunnableConfig) -> dict:
    if state.get("response_format") != "json":
        return {}
    parsed = parse_json_content(state["output_content"] or "")
    return {"output_json": parsed}


def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("prepare_context", prepare_context_node)
    graph.add_node("run_research_llm", run_research_llm_node)
    graph.add_node("parse_and_validate", parse_and_validate_node)
    graph.set_entry_point("prepare_context")
    graph.add_edge("prepare_context", "run_research_llm")
    graph.add_edge("run_research_llm", "parse_and_validate")
    graph.add_edge("parse_and_validate", END)
    return graph
