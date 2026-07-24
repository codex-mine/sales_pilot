"""
LangChain callback handler that accumulates token usage across every LLM call
made during a single LangGraph run — a graph can call the model more than
once per run (e.g. Email Generation's `self_critique` regeneration pass), so
this sums across all calls in that run rather than overwriting on each one.

One instance is attached per graph invocation (`graph.ainvoke(..., config={
"callbacks": [handler]})`), never shared globally — cost must stay scoped to
the single AIJob that invocation belongs to. Reuses the exact pricing table
already built in module 04 (`app/services/ai/pricing.py`); this file does not
duplicate a second one.
"""

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from app.models.enums import LLMProviderEnum
from app.services.ai.pricing import compute_cost_usd


class CostTrackingCallbackHandler(AsyncCallbackHandler):
    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.call_count = 0

    async def on_llm_end(self, response: LLMResult, **kwargs: object) -> None:
        self.call_count += 1
        input_tokens, output_tokens = _extract_usage(response)
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def cost_usd(self, provider: LLMProviderEnum, model_name: str) -> float:
        return compute_cost_usd(provider, model_name, self.input_tokens, self.output_tokens)


def _extract_usage(response: LLMResult) -> tuple[int, int]:
    """Chat models populate `AIMessage.usage_metadata` (LangChain's
    standardized shape: `{"input_tokens", "output_tokens", "total_tokens"}`)
    on every generation — this is the primary source. `llm_output["token_usage"]`
    is kept as a fallback for any provider integration that only fills the
    provider-specific free-form field."""
    for generation_list in response.generations:
        for generation in generation_list:
            message = getattr(generation, "message", None)
            usage = getattr(message, "usage_metadata", None) if message is not None else None
            if usage:
                return int(usage.get("input_tokens", 0) or 0), int(usage.get("output_tokens", 0) or 0)

    llm_output = response.llm_output or {}
    token_usage = llm_output.get("token_usage") or llm_output.get("usage") or {}
    input_tokens = token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0
    output_tokens = token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0
    return int(input_tokens), int(output_tokens)
