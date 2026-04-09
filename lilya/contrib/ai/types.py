from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from lilya.contrib.ai.exceptions import AIConfigurationError

MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(slots=True)
class ChatMessage:
    """
    Represents a single chat message exchanged with a model provider.

    The message structure intentionally stays small and provider-agnostic.
    Providers are responsible for translating this dataclass into the wire
    format required by their external APIs.
    """

    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def system(cls, content: str, **kwargs: Any) -> ChatMessage:
        """
        Create a system message.
        """
        return cls(role="system", content=content, **kwargs)

    @classmethod
    def user(cls, content: str, **kwargs: Any) -> ChatMessage:
        """
        Create a user message.
        """
        return cls(role="user", content=content, **kwargs)

    @classmethod
    def assistant(cls, content: str, **kwargs: Any) -> ChatMessage:
        """
        Create an assistant message.
        """
        return cls(role="assistant", content=content, **kwargs)

    @classmethod
    def tool(cls, content: str, *, tool_call_id: str, **kwargs: Any) -> ChatMessage:
        """
        Create a tool message associated with a tool call id.
        """
        return cls(role="tool", content=content, tool_call_id=tool_call_id, **kwargs)


@dataclass(slots=True)
class PromptRequest:
    """
    Provider-agnostic request payload used by Lilya's AI client.
    """

    messages: list[ChatMessage]
    model: str | None = None
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop_sequences: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Validate the prompt request.
        """
        if not self.messages:
            raise AIConfigurationError("PromptRequest requires at least one message.")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise AIConfigurationError("`max_tokens` must be greater than zero when provided.")
        if self.temperature is not None and self.temperature < 0:
            raise AIConfigurationError("`temperature` must be greater than or equal to zero.")
        if self.top_p is not None and not 0 <= self.top_p <= 1:
            raise AIConfigurationError("`top_p` must be between 0 and 1.")

    def with_system_prompt(self, system_prompt: str | None) -> PromptRequest:
        """
        Return a copy of the request with a system prompt override applied.
        """
        return PromptRequest(
            messages=list(self.messages),
            model=self.model,
            system_prompt=system_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            stop_sequences=list(self.stop_sequences),
            metadata=dict(self.metadata),
            extra=dict(self.extra),
        )


@dataclass(slots=True)
class AIUsage:
    """
    Token usage information returned by a provider.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any] | None,
        *,
        input_key: str = "prompt_tokens",
        output_key: str = "completion_tokens",
        total_key: str = "total_tokens",
    ) -> AIUsage | None:
        """
        Build a normalized usage object from a provider-specific mapping.
        """
        if not data:
            return None
        input_tokens = int(data.get(input_key, 0) or 0)
        output_tokens = int(data.get(output_key, 0) or 0)
        total_tokens = int(data.get(total_key, input_tokens + output_tokens) or 0)
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


@dataclass(slots=True)
class AIResponseChunk:
    """
    A single streamed chunk emitted by a provider.
    """

    text: str = ""
    delta: str = ""
    model: str | None = None
    provider: str | None = None
    finish_reason: str | None = None
    raw: Any | None = None


@dataclass(slots=True)
class AIResponse:
    """
    The normalized response object returned by Lilya's AI client.
    """

    text: str
    model: str | None = None
    provider: str | None = None
    finish_reason: str | None = None
    usage: AIUsage | None = None
    raw: Any | None = None
