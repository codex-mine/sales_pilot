"""
StateGraph for Reply Classification (module 09): `classify` -> conditional
edge on classification value -> `detect_meeting_intent` (only when
classification is `meeting_requested`) -> `finalize`.

`detect_meeting_intent` is new behavior this module adds: extracting
explicit time/date mentions from the reply so a future scheduling flow can
pre-fill proposed times, using the `detect_meeting` prompt template that
already existed as a seeded-but-unused template (see `system_prompts.py`) —
nothing previously rendered it. It writes its findings onto the SAME
`AIOutput.content_json` dict `InboundEmailService.finalize_classification`
(module 09) already reads, as additive keys that method's `.get(...)` calls
simply ignore today — wiring those keys into `Meeting.proposed_times` would
mean editing module 09/10 service code, which is out of scope per this
module's "don't touch modules 05-12 service code" constraint. The detection
itself is fully implemented and the data is captured; consuming it into the
meeting-creation flow is a natural follow-up for whichever module owns that.
"""

from dataclasses import dataclass
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.agents.base import call_model, parse_json_content, step


@dataclass(frozen=True)
class _RenderableTemplate:
    """Duck-types the two attributes `render_prompt` (module 04's
    `PromptService`) needs off a `PromptVersion` ORM row, without persisting
    one — `detect_meeting` has no PromptVersion of its own in play here since
    no service calls `run_job` for it; reusing `render_prompt` for the exact
    same Jinja rendering + variable-validation instead of hand-rolling a
    second templating mechanism."""

    variables: list[str]
    user_prompt_template: str
    system_prompt: str


class ReplyState(TypedDict):
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
    reply_body: str | None
    classification: dict | None
    meeting_intent: dict | None
    output_content: str | None
    output_json: dict | list | None


@step("classify")
async def classify_node(state: ReplyState, config: RunnableConfig) -> dict:
    content = await call_model(state, config)
    parsed = parse_json_content(content)
    classification = parsed if isinstance(parsed, dict) else {}
    return {"classification": classification, "output_content": content}


def route_after_classify(state: ReplyState) -> str:
    classification = (state.get("classification") or {}).get("classification")
    return "detect_meeting_intent" if classification == "meeting_requested" else "finalize"


@step("detect_meeting_intent")
async def detect_meeting_intent_node(state: ReplyState, config: RunnableConfig) -> dict:
    from app.services.ai.prompt_service import render_prompt
    from app.services.ai.system_prompts import SYSTEM_PROMPT_TEMPLATES

    _agent_type, _description, system_prompt, user_prompt_template, variables = SYSTEM_PROMPT_TEMPLATES[
        "detect_meeting"
    ]
    template = _RenderableTemplate(
        variables=variables, user_prompt_template=user_prompt_template, system_prompt=system_prompt
    )
    rendered_system, rendered_user = render_prompt(template, {"message_body": state.get("reply_body") or ""})

    call_state = {**state, "system_prompt": rendered_system, "user_prompt": rendered_user}
    content = await call_model(call_state, config)
    parsed = parse_json_content(content)
    return {"meeting_intent": parsed if isinstance(parsed, dict) else {}}


@step("finalize")
async def finalize_node(state: ReplyState, config: RunnableConfig) -> dict:
    classification = dict(state.get("classification") or {})
    meeting_intent = state.get("meeting_intent")
    if meeting_intent:
        classification["proposed_times"] = meeting_intent.get("proposed_times")
        classification["meeting_duration_minutes"] = meeting_intent.get("duration_minutes")
        classification["meeting_notes"] = meeting_intent.get("notes")
    return {"output_json": classification, "output_content": state.get("output_content")}


def build_graph() -> StateGraph:
    graph = StateGraph(ReplyState)
    graph.add_node("classify", classify_node)
    graph.add_node("detect_meeting_intent", detect_meeting_intent_node)
    graph.add_node("finalize", finalize_node)
    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify", route_after_classify, {"detect_meeting_intent": "detect_meeting_intent", "finalize": "finalize"}
    )
    graph.add_edge("detect_meeting_intent", "finalize")
    graph.add_edge("finalize", END)
    return graph
