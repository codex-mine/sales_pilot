"""
Static per-model pricing table (USD per 1K tokens) used to estimate
`AIJob.cost_usd`. Estimates, not invoices — providers change prices; update
this table when they do. Lookup is by longest matching model-name prefix so
dated snapshots ("claude-sonnet-5-20250929") resolve without listing every
variant. Unknown models cost $0 rather than failing the job — a missing
pricing row must never block AI execution.
"""

from app.models.enums import LLMProviderEnum

# (input $/1K tokens, output $/1K tokens)
_PRICING: dict[LLMProviderEnum, dict[str, tuple[float, float]]] = {
    LLMProviderEnum.OPENAI: {
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4o": (0.0025, 0.01),
        "gpt-4.1-mini": (0.0004, 0.0016),
        "gpt-4.1": (0.002, 0.008),
        "o3": (0.002, 0.008),
    },
    LLMProviderEnum.ANTHROPIC: {
        "claude-haiku-4-5": (0.001, 0.005),
        "claude-sonnet-5": (0.003, 0.015),
        "claude-fable-5": (0.005, 0.025),
        "claude-opus-4": (0.015, 0.075),
        "claude-3-5-haiku": (0.0008, 0.004),
    },
    LLMProviderEnum.GROQ: {
        "llama-3.3-70b": (0.00059, 0.00079),
        "llama-3.1-8b": (0.00005, 0.00008),
        "mixtral-8x7b": (0.00024, 0.00024),
    },
    LLMProviderEnum.GOOGLE: {
        "gemini-2.5-pro": (0.00125, 0.01),
        "gemini-2.5-flash": (0.0003, 0.0025),
        "gemini-2.0-flash": (0.0001, 0.0004),
    },
    # Local models have no per-token cost.
    LLMProviderEnum.LOCAL: {},
}


def compute_cost_usd(
    provider: LLMProviderEnum, model_name: str, input_tokens: int, output_tokens: int
) -> float:
    table = _PRICING.get(provider, {})
    match = max(
        (prefix for prefix in table if model_name.startswith(prefix)),
        key=len,
        default=None,
    )
    if match is None:
        return 0.0
    input_rate, output_rate = table[match]
    return round((input_tokens / 1000) * input_rate + (output_tokens / 1000) * output_rate, 6)
