"""
Shared LangChain `BaseChatModel` test double for every AI-job test suite
(test_ai.py, test_research.py, test_email_generation.py, test_inbox.py).

Module 04's `_StubLLMClient` mocked `LLMClient.complete(...)`, which no
longer exists now that module 13 replaced the execution engine with
LangGraph — `get_chat_model(...)` is the new seam
(`app/agents/base.py:call_model`), and its return value must be a real
`BaseChatModel` subclass rather than a bare duck-typed object: LangChain only
fires `on_llm_end` — which `CostTrackingCallbackHandler` depends on — through
its own Runnable callback machinery, which a plain object with an `ainvoke`
method never goes through.
"""

from collections.abc import Callable
from typing import Any, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.exceptions.errors import LLMProviderError

Responder = Callable[[str, str], str]


class FakeChatModel(BaseChatModel):
    """`content` is used verbatim when no `responder` is given (the simple
    single-response case); `responder(system_prompt, user_prompt) -> str`
    lets a test branch its canned response by which prompt is in play, for
    flows that make more than one LLM call per job (e.g. Email Generation's
    `generate_variants` + `self_critique`, or a service that auto-chains
    research -> prospect analysis -> email generation in one test)."""

    content: str = "stub output"
    fail: bool = False
    responder: Optional[Responder] = None
    calls: list[dict] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        system_prompt = str(messages[0].content) if messages else ""
        user_prompt = str(messages[1].content) if len(messages) > 1 else ""
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        if self.fail:
            raise LLMProviderError("stubbed provider failure")
        content = self.responder(system_prompt, user_prompt) if self.responder else self.content
        message = AIMessage(
            content=content,
            usage_metadata={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        )
        return ChatResult(generations=[ChatGeneration(message=message)])
