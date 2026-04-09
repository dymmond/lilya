from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from lilya.contrib.ai.exceptions import AIConfigurationError, ProviderNotConfigured
from lilya.contrib.ai.providers.base import AIProvider
from lilya.contrib.ai.types import AIResponse, AIResponseChunk, ChatMessage, PromptRequest


class AIClient:
    """
    High-level, provider-agnostic client used by Lilya applications.

    The client offers a stable API for prompt and chat-style interactions
    while delegating provider-specific transport logic to an `AIProvider`.
    """

    def __init__(
        self,
        provider: AIProvider | None,
        *,
        default_model: str | None = None,
        default_system_prompt: str | None = None,
    ) -> None:
        """
        Initialize the AI client.

        Args:
            provider: A configured provider implementation.
            default_model: Default model used when a request does not set one.
            default_system_prompt: Optional global system prompt applied by default.
        """
        if provider is None:
            raise ProviderNotConfigured("AIClient requires a configured provider instance.")
        self.provider = provider
        self.default_model = default_model
        self.default_system_prompt = default_system_prompt

    async def startup(self) -> None:
        """
        Start the underlying provider, if it uses a lifecycle.
        """
        await self.provider.startup()

    async def shutdown(self) -> None:
        """
        Shut down the underlying provider, if it uses a lifecycle.
        """
        await self.provider.shutdown()

    async def prompt(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop_sequences: Sequence[str] | None = None,
        metadata: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AIResponse:
        """
        Send a single prompt as a one-message chat request.
        """
        return await self.chat(
            messages=[ChatMessage.user(prompt)],
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop_sequences=stop_sequences,
            metadata=metadata,
            extra=extra,
        )

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop_sequences: Sequence[str] | None = None,
        metadata: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AIResponse:
        """
        Send a normalized chat request through the configured provider.
        """
        request = self._build_request(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop_sequences=stop_sequences,
            metadata=metadata,
            extra=extra,
        )
        return await self.provider.complete(request)

    async def stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop_sequences: Sequence[str] | None = None,
        metadata: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[AIResponseChunk]:
        """
        Stream a single prompt as incremental output chunks.
        """
        async for chunk in self.stream_chat(
            messages=[ChatMessage.user(prompt)],
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop_sequences=stop_sequences,
            metadata=metadata,
            extra=extra,
        ):
            yield chunk

    async def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop_sequences: Sequence[str] | None = None,
        metadata: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AsyncIterator[AIResponseChunk]:
        """
        Stream a chat request through the configured provider.
        """
        request = self._build_request(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop_sequences=stop_sequences,
            metadata=metadata,
            extra=extra,
        )
        async for chunk in self.provider.stream(request):
            yield chunk

    def _build_request(
        self,
        *,
        messages: Sequence[ChatMessage],
        model: str | None,
        system_prompt: str | None,
        temperature: float | None,
        max_tokens: int | None,
        top_p: float | None,
        stop_sequences: Sequence[str] | None,
        metadata: dict[str, Any] | None,
        extra: dict[str, Any] | None,
    ) -> PromptRequest:
        """
        Build a normalized prompt request with client defaults applied.
        """
        if not messages:
            raise AIConfigurationError("AIClient requires at least one message.")

        resolved_model = model or self.default_model
        if not resolved_model:
            raise AIConfigurationError(
                "No model was provided. Set `default_model` on the AIClient or pass `model=`."
            )

        return PromptRequest(
            messages=list(messages),
            model=resolved_model,
            system_prompt=system_prompt or self.default_system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop_sequences=list(stop_sequences or []),
            metadata=dict(metadata or {}),
            extra=dict(extra or {}),
        )
