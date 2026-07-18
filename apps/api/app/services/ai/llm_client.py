"""
Provider-agnostic LLM client layer. This module is the ONLY place in the
codebase where provider SDKs are imported and where provider branching
happens — every feature calls `get_llm_client(...).complete(...)` through
AIJobService and never touches an SDK directly.

Provider SDK imports are deferred into each client class so a missing
optional SDK only fails when that specific provider is actually used (and so
tests can run with all providers mocked and none installed).

Every SDK exception is caught and re-raised as `LLMProviderError` so the
AIJob failure/retry path is uniform across providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.exceptions.errors import LLMProviderError
from app.models.enums import LLMProviderEnum


@dataclass
class LLMCompletionResult:
    content: str
    input_tokens: int
    output_tokens: int
    raw_response: dict = field(default_factory=dict)


class LLMClient(ABC):
    @abstractmethod
    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMCompletionResult: ...


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def complete(
        self, *, system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int
    ) -> LLMCompletionResult:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            usage = response.usage
            return LLMCompletionResult(
                content=response.choices[0].message.content or "",
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                raw_response=response.model_dump(),
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 — uniform provider-error boundary
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def complete(
        self, *, system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int
    ) -> LLMCompletionResult:
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=self.api_key)
            response = await client.messages.create(
                model=model,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = "".join(block.text for block in response.content if block.type == "text")
            return LLMCompletionResult(
                content=content,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                raw_response=response.model_dump(),
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc


class GroqClient(LLMClient):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def complete(
        self, *, system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int
    ) -> LLMCompletionResult:
        try:
            from groq import AsyncGroq

            client = AsyncGroq(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            usage = response.usage
            return LLMCompletionResult(
                content=response.choices[0].message.content or "",
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                raw_response=response.model_dump(),
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(f"Groq request failed: {exc}") from exc


class GeminiClient(LLMClient):
    """Google Gemini via the official `google-genai` SDK (LLMProviderEnum.GOOGLE)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def complete(
        self, *, system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int
    ) -> LLMCompletionResult:
        try:
            from google import genai
            from google.genai import types as genai_types

            client = genai.Client(api_key=self.api_key)
            response = await client.aio.models.generate_content(
                model=model,
                contents=user_prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            usage = response.usage_metadata
            return LLMCompletionResult(
                content=response.text or "",
                input_tokens=(usage.prompt_token_count or 0) if usage else 0,
                output_tokens=(usage.candidates_token_count or 0) if usage else 0,
                raw_response=response.model_dump(mode="json"),
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc


class OllamaClient(LLMClient):
    """Local/self-hosted models via Ollama (LLMProviderEnum.LOCAL). Addressed
    by base URL instead of an API key — cost is always $0."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    async def complete(
        self, *, system_prompt: str, user_prompt: str, model: str, temperature: float, max_tokens: int
    ) -> LLMCompletionResult:
        try:
            from ollama import AsyncClient

            client = AsyncClient(host=self.base_url)
            response = await client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": temperature, "num_predict": max_tokens},
            )
            raw: dict[str, Any] = dict(response) if not isinstance(response, dict) else response
            message = raw.get("message") or {}
            return LLMCompletionResult(
                content=(message.get("content") if isinstance(message, dict) else message.content) or "",
                input_tokens=raw.get("prompt_eval_count") or 0,
                output_tokens=raw.get("eval_count") or 0,
                raw_response={k: v for k, v in raw.items() if k != "context"},
            )
        except LLMProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc


def get_llm_client(
    provider: LLMProviderEnum, api_key: str | None, *, base_url: str | None = None
) -> LLMClient:
    """The single point of provider branching. `api_key` is required for every
    hosted provider; `base_url` only applies to LOCAL (Ollama)."""
    if provider == LLMProviderEnum.LOCAL:
        if not base_url:
            raise LLMProviderError("Ollama base URL is not configured.")
        return OllamaClient(base_url=base_url)

    if not api_key:
        raise LLMProviderError(f"No API key configured for provider '{provider.value}'.")

    if provider == LLMProviderEnum.OPENAI:
        return OpenAIClient(api_key=api_key)
    if provider == LLMProviderEnum.ANTHROPIC:
        return AnthropicClient(api_key=api_key)
    if provider == LLMProviderEnum.GROQ:
        return GroqClient(api_key=api_key)
    if provider == LLMProviderEnum.GOOGLE:
        return GeminiClient(api_key=api_key)

    raise LLMProviderError(f"Unsupported LLM provider: '{provider.value}'.")
