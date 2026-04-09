from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from lilya.contrib.ai.config import GroqConfig, MistralConfig, OpenAICompatibleConfig, OpenAIConfig
from lilya.contrib.ai.exceptions import AIConfigurationError, AIProviderError, AIResponseError
from lilya.contrib.ai.providers.base import BaseHTTPProvider
from lilya.contrib.ai.types import AIResponse, AIResponseChunk, AIUsage, ChatMessage, PromptRequest


class OpenAICompatibleProvider(BaseHTTPProvider):
    """
    Provider implementation for OpenAI-compatible chat completion APIs.

    This provider works with OpenAI itself and any vendor that mirrors the
    `/chat/completions` contract closely enough, such as Groq and Mistral.
    """

    name = "openai-compatible"

    def __init__(self, config: OpenAICompatibleConfig) -> None:
        """
        Initialize the provider with an OpenAI-compatible configuration object.
        """
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            **config.headers,
        }
        if config.organization:
            headers["OpenAI-Organization"] = config.organization
        if config.project:
            headers["OpenAI-Project"] = config.project

        super().__init__(timeout=config.timeout, headers=headers)
        self.config = config
        self.name = config.provider_name

    async def complete(self, request: PromptRequest) -> AIResponse:
        """
        Execute a non-streaming chat completion request.
        """
        client = await self._get_client()
        payload = self._build_payload(request, stream=False)

        try:
            response = await client.post(f"{self.config.base_url}/chat/completions", json=payload)
            response.raise_for_status()
        except Exception as exc:
            raise AIProviderError(f"OpenAI request failed: {exc}") from exc

        data = response.json()
        return self._parse_response(data)

    async def stream(self, request: PromptRequest) -> AsyncIterator[AIResponseChunk]:
        """
        Execute a streaming chat completion request and yield normalized chunks.
        """
        client = await self._get_client()
        payload = self._build_payload(request, stream=True)

        try:
            async with client.stream(
                "POST",
                f"{self.config.base_url}/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for event_data in self._iter_sse_data(response):
                    if event_data == "[DONE]":
                        break
                    chunk = self._parse_stream_event(self._decode_json(event_data))
                    if chunk is not None:
                        yield chunk
        except Exception as exc:
            raise AIProviderError(f"OpenAI streaming request failed: {exc}") from exc

    def _build_payload(self, request: PromptRequest, *, stream: bool) -> dict[str, Any]:
        """
        Build the OpenAI-compatible chat completions payload.
        """
        if not request.model:
            raise AIConfigurationError("OpenAIProvider requires a model to be set on the request.")

        messages = self._serialize_messages(request.messages, request.system_prompt)
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "stream": stream,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop_sequences:
            payload["stop"] = request.stop_sequences
        if request.metadata:
            payload["metadata"] = request.metadata
        payload.update(request.extra)
        return payload

    @staticmethod
    def _serialize_messages(
        messages: list[ChatMessage], system_prompt: str | None
    ) -> list[dict[str, Any]]:
        """
        Translate Lilya chat messages into OpenAI's message format.
        """
        serialized: list[dict[str, Any]] = []
        if system_prompt:
            serialized.append({"role": "system", "content": system_prompt})

        for message in messages:
            payload: dict[str, Any] = {"role": message.role, "content": message.content}
            if message.name:
                payload["name"] = message.name
            if message.tool_call_id:
                payload["tool_call_id"] = message.tool_call_id
            serialized.append(payload)
        return serialized

    def _parse_response(self, data: dict[str, Any]) -> AIResponse:
        """
        Parse a full OpenAI chat completion response.
        """
        try:
            choice = data["choices"][0]
            message = choice["message"]
            text = message.get("content") or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("OpenAI response did not contain a valid choice.") from exc

        usage = AIUsage.from_mapping(data.get("usage"))
        return AIResponse(
            text=text,
            model=data.get("model"),
            provider=self.name,
            finish_reason=choice.get("finish_reason"),
            usage=usage,
            raw=data,
        )

    def _parse_stream_event(self, data: dict[str, Any]) -> AIResponseChunk | None:
        """
        Parse a streaming OpenAI delta event.
        """
        try:
            choice = data["choices"][0]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIResponseError("OpenAI stream event did not contain a valid choice.") from exc

        delta_payload = choice.get("delta") or {}
        delta = delta_payload.get("content") or ""
        finish_reason = choice.get("finish_reason")

        if not delta and not finish_reason:
            return None

        return AIResponseChunk(
            text=delta,
            delta=delta,
            model=data.get("model"),
            provider=self.name,
            finish_reason=finish_reason,
            raw=data,
        )


class OpenAIProvider(OpenAICompatibleProvider):
    """
    Convenience provider for OpenAI's hosted API.
    """

    def __init__(self, config: OpenAIConfig) -> None:
        """
        Initialize the provider with OpenAI defaults.
        """
        super().__init__(config)


class GroqProvider(OpenAICompatibleProvider):
    """
    Convenience provider for Groq's OpenAI-compatible API.
    """

    def __init__(self, config: GroqConfig) -> None:
        """
        Initialize the provider with Groq defaults.
        """
        super().__init__(config)


class MistralProvider(OpenAICompatibleProvider):
    """
    Convenience provider for Mistral's OpenAI-compatible API.
    """

    def __init__(self, config: MistralConfig) -> None:
        """
        Initialize the provider with Mistral defaults.
        """
        super().__init__(config)
