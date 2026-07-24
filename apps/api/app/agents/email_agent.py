"""
StateGraph for AI Email Generation (module 06): `gather_context` ->
`generate_variants` -> `self_critique` -> `finalize`.

`gather_context` is a passthrough step for the same reason `research_agent`'s
`prepare_context` is: `EmailGenerationService._build_context` (module 06)
already pulls CompanyResearch + ProspectAnalysis + any prior-rejected-draft
context into the rendered prompt before `run_job` creates this AIJob, per the
"don't touch modules 05-12 service code" constraint — this node exists so
that step is still visible in the live timeline.

`self_critique` is the genuine new capability this graph adds over module
04's single call: it reviews the freshly generated variants against the
"no generic filler" rule from module 06's prompt design and, on failure,
triggers exactly one regeneration pass with the critique's feedback folded
into the retry prompt (`critique_attempts` caps this at one retry so a
stubborn model can't loop forever).
"""

import json
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.agents.base import call_model, parse_json_content, step

_CRITIQUE_SYSTEM_PROMPT = (
    "You are a strict editor reviewing sales outreach emails. Reject any email "
    "that uses generic filler phrases like 'I hope this email finds you well', "
    "vague platitudes, or boilerplate that could apply to any recipient — every "
    "email must read as genuinely written for its specific recipient. Respond "
    "with valid JSON only: {\"passes\": boolean, \"feedback\": string}."
)


class EmailState(TypedDict):
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
    variants: list[dict] | None
    critique_passed: bool | None
    critique_feedback: str | None
    critique_attempts: int
    output_content: str | None
    output_json: dict | list | None


@step("gather_context")
async def gather_context_node(state: EmailState, config: RunnableConfig) -> dict:
    # See module docstring: context (CompanyResearch/ProspectAnalysis/prior
    # rejected draft) is already baked into `user_prompt` by
    # EmailGenerationService before this AIJob exists.
    return {}


@step("generate_variants")
async def generate_variants_node(state: EmailState, config: RunnableConfig) -> dict:
    call_state = dict(state)
    if state.get("critique_feedback"):
        call_state["user_prompt"] = (
            state["user_prompt"] + "\n\nA previous draft was rejected by editorial review for this reason: "
            f"{state['critique_feedback']} Write genuinely different, specific copy that fixes this."
        )
    content = await call_model(call_state, config)
    parsed = parse_json_content(content)
    variants = parsed if isinstance(parsed, list) else [parsed]
    return {"variants": variants, "output_content": content}


@step("self_critique")
async def self_critique_node(state: EmailState, config: RunnableConfig) -> dict:
    critique_state = {
        **state,
        "system_prompt": _CRITIQUE_SYSTEM_PROMPT,
        "user_prompt": f"Review these email variants:\n\n{json.dumps(state['variants'])}",
    }
    content = await call_model(critique_state, config)
    parsed = parse_json_content(content)
    passes = bool(parsed.get("passes", True)) if isinstance(parsed, dict) else True
    feedback = parsed.get("feedback") if isinstance(parsed, dict) else None
    return {
        "critique_passed": passes,
        "critique_feedback": None if passes else feedback,
        "critique_attempts": state.get("critique_attempts", 0) + 1,
    }


def route_after_critique(state: EmailState) -> str:
    # `critique_attempts` is incremented by self_critique_node BEFORE this
    # routes, so after the *first* critique pass it's already 1 — >= 2 is
    # what actually means "a retry already happened, stop regardless of
    # pass/fail" (1 would stop before ever retrying at all).
    if state.get("critique_passed") or state.get("critique_attempts", 0) >= 2:
        return "finalize"
    return "generate_variants"


@step("finalize")
async def finalize_node(state: EmailState, config: RunnableConfig) -> dict:
    return {"output_json": state.get("variants"), "output_content": state.get("output_content")}


def build_graph() -> StateGraph:
    graph = StateGraph(EmailState)
    graph.add_node("gather_context", gather_context_node)
    graph.add_node("generate_variants", generate_variants_node)
    graph.add_node("self_critique", self_critique_node)
    graph.add_node("finalize", finalize_node)
    graph.set_entry_point("gather_context")
    graph.add_edge("gather_context", "generate_variants")
    graph.add_edge("generate_variants", "self_critique")
    graph.add_conditional_edges(
        "self_critique", route_after_critique, {"finalize": "finalize", "generate_variants": "generate_variants"}
    )
    graph.add_edge("finalize", END)
    return graph
