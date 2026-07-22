"""
Provider-agnostic chat-model factory. This module is the ONLY place in the
codebase where provider SDKs are imported and where provider branching
happens — every LangGraph node calls `get_chat_model(...)` and never
constructs a provider client directly.

This used to hand-roll a `LLMClient` protocol with per-provider request/
response parsing (module 04). It now returns a LangChain `BaseChatModel`
instead: LangChain already normalizes request shape, streaming, and
`AIMessage.usage_metadata` across providers, so there is nothing left for a
hand-rolled result type to add — `LLMCompletionResult`/manual token parsing
are gone, not migrated.

Provider SDK imports are deferred into each branch so a missing optional SDK
only fails when that specific provider is actually used (and so tests can run
with all providers mocked and none installed) — same reasoning module 04's
version used, just applied to LangChain's provider packages instead of the
raw SDKs.

Provider coverage note: the spec for this module's dependency list asked only
for `langchain-anthropic`/`langchain-openai`. This app's platform default
provider (`Settings.ai_default_provider`) is `"groq"`, and orgs may already
have GROQ/GOOGLE/LOCAL configured via `AISettingsService` (module 04) — since
this module is an internal engine swap that must stay backward compatible
("not a breaking change to anything already built on top of it"), dropping
those providers would silently break existing jobs. `langchain-groq`,
`langchain-google-genai`, and `langchain-ollama` were added alongside the two
mandated packages for exact provider parity with the client this replaces
(same five providers `get_llm_client` supported; MISTRAL remains unsupported,
matching the prior behavior exactly).
"""

from app.exceptions.errors import LLMProviderError
from app.models.enums import LLMProviderEnum

# LangChain's own alias for "any chat model" — used purely as a return-type
# annotation here so callers don't need to know which concrete subclass a
# given provider resolves to.
from langchain_core.language_models.chat_models import BaseChatModel


def get_chat_model(
    provider: LLMProviderEnum,
    model_name: str,
    *,
    api_key: str | None,
    base_url: str | None = None,
    temperature: float,
    max_tokens: int,
) -> BaseChatModel:
    """The single point of provider branching. `api_key` is required for every
    hosted provider; `base_url` only applies to LOCAL (Ollama)."""
    if provider == LLMProviderEnum.LOCAL:
        if not base_url:
            raise LLMProviderError("Ollama base URL is not configured.")
        from langchain_ollama import ChatOllama

        return ChatOllama(model=model_name, base_url=base_url, temperature=temperature, num_predict=max_tokens)

    if not api_key:
        raise LLMProviderError(f"No API key configured for provider '{provider.value}'.")

    if provider == LLMProviderEnum.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name, api_key=api_key, temperature=temperature, max_tokens=max_tokens)
    if provider == LLMProviderEnum.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model_name, api_key=api_key, temperature=temperature, max_tokens=max_tokens)
    if provider == LLMProviderEnum.GROQ:
        from langchain_groq import ChatGroq

        return ChatGroq(model=model_name, api_key=api_key, temperature=temperature, max_tokens=max_tokens)
    if provider == LLMProviderEnum.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_name, google_api_key=api_key, temperature=temperature, max_output_tokens=max_tokens
        )

    raise LLMProviderError(f"Unsupported provider for LangGraph engine: '{provider.value}'.")
