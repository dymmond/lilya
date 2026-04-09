from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from lilya.contrib.ai.config import AnthropicConfig
from lilya.contrib.ai.exceptions import AIConfigurationError, AIProviderError, AIResponseError
from lilya.contrib.ai.providers.base import BaseHTTPProvider
from lilya.contrib.ai.types import AIResponse, AIResponseChunk, AIUsage, ChatMessage, PromptRequest


class AnthropicProvider(BaseHTTPProvider):
    """
    Provider implementation for Anthropic's messages API.
    """

    name = "anthropic"

    def __init__(self, config: AnthropicConfig) -> None:
        """
        Initialize the provider with an Anthropic configuration object.
        """
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": config.anthropic_version,
            "Content-Type": "application/json",
            **config.headers,
        }
        super().__init__(timeout=config.timeout, headers=headers)
        self.config = config

    async def complete(self, request: PromptRequest) -> AIResponse:
        """
        Execute a non-streaming Anthropic messages request.
        """
        client = await self._get_client()
        payload = self._build_payload(request, stream=False)

        try:
            response = await client.post(f"{self.config.base_url}/messages", json=payload)
            response.raise_for_status()
        except Exception as exc:
            raise AIProviderError(f"Anthropic request failed: {exc}") from exc

        data = response.json()
        return self._parse_response(data)

    async def stream(self, request: PromptRequest) -> AsyncIterator[AIResponseChunk]:
        """
        Execute a streaming Anthropic request and yield normalized chunks.
        """
        client = await self._get_client()
        payload = self._build_payload(request, stream=True)

        try:
            async with client.stream(
                "POST",
                f"{self.config.base_url}/messages",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for event_data in self._iter_sse_data(response):
                    chunk = self._parse_stream_event(self._decode_json(event_data))
                    if chunk is not None:
                        yield chunk
        except Exception as exc:
            raise AIProviderError(f"Anthropic streaming request failed: {exc}") from exc

    def _build_payload(self, request: PromptRequest, *, stream: bool) -> dict[str, Any]:
        """
        Build the Anthropic messages payload.
        """
        if not request.model:
            raise AIConfigurationError(
                "AnthropicProvider requires a model to be set on the request."
            )

        system_prompt, messages = self._split_system_messages(
            request.messages, request.system_prompt
        )
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or self.config.default_max_tokens,
            "stream": stream,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences
        if request.metadata:
            payload["metadata"] = request.metadata
        payload.update(request.extra)
        return payload

    @staticmethod
    def _split_system_messages(
        messages: list[ChatMessage], system_prompt: str | None
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """
        Extract system messages into Anthropic's top-level `system` field.
        """
        system_parts: list[str] = []
        if system_prompt:
            system_parts.append(system_prompt)

        serialized: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
                continue
            payload: dict[str, Any] = {"role": message.role, "content": message.content}
            if message.name:
                payload["name"] = message.name
            serialized.append(payload)

        system = "\n\n".join(part for part in system_parts if part) or None
        return system, serialized

    def _parse_response(self, data: dict[str, Any]) -> AIResponse:
        """
        Parse a full Anthropic messages response.
        """
        content = data.get("content") or []
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        if not content and not text_parts:
            raise AIResponseError("Anthropic response did not contain any content blocks.")

        usage_data = data.get("usage") or {}
        usage = AIUsage(
            input_tokens=int(usage_data.get("input_tokens", 0) or 0),
            output_tokens=int(usage_data.get("output_tokens", 0) or 0),
            total_tokens=int(usage_data.get("input_tokens", 0) or 0)
            + int(usage_data.get("output_tokens", 0) or 0),
        )

        return AIResponse(
            text="".join(text_parts),
            model=data.get("model"),
            provider=self.name,
            finish_reason=data.get("stop_reason"),
            usage=usage,
            raw=data,
        )

    def _parse_stream_event(self, data: dict[str, Any]) -> AIResponseChunk | None:
        """
        Parse an Anthropic streaming event into a normalized chunk.
        """
        event_type = data.get("type")

        if event_type == "content_block_delta":
            delta = ((data.get("delta") or {}).get("text")) or ""
            if not delta:
                return None
            return AIResponseChunk(
                text=delta,
                delta=delta,
                model=data.get("model"),
                provider=self.name,
                raw=data,
            )

        if event_type == "message_stop":
            return AIResponseChunk(
                text="",
                delta="",
                model=data.get("model"),
                provider=self.name,
                finish_reason=data.get("stop_reason"),
                raw=data,
            )

        return None
