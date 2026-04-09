from __future__ import annotations

import json

import httpx
import pytest

from lilya.contrib.ai import (
    AIConfigurationError,
    AIResponseError,
    AnthropicConfig,
    AnthropicProvider,
    ChatMessage,
    PromptRequest,
)

pytestmark = pytest.mark.asyncio


def build_provider(handler):
    provider = AnthropicProvider(AnthropicConfig(api_key="secret"))
    provider._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={})
    return provider


async def test_anthropic_provider_parses_response_and_hoists_system_prompt():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert request.url.path == "/v1/messages"
        assert payload["system"] == "You are helpful.\n\nSpeak briefly."
        assert payload["messages"] == [{"role": "user", "content": "hello"}]
        assert payload["max_tokens"] == 1024
        return httpx.Response(
            200,
            json={
                "model": "claude-3-5-sonnet-latest",
                "content": [{"type": "text", "text": "Hello there"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 9, "output_tokens": 3},
            },
        )

    provider = build_provider(handler)
    response = await provider.complete(
        PromptRequest(
            model="claude-3-5-sonnet-latest",
            system_prompt="You are helpful.",
            messages=[ChatMessage.system("Speak briefly."), ChatMessage.user("hello")],
        )
    )

    assert response.text == "Hello there"
    assert response.provider == "anthropic"
    assert response.usage is not None
    assert response.usage.total_tokens == 12


async def test_anthropic_provider_streams_chunks():
    body = "\n\n".join(
        [
            'data: {"type":"content_block_delta","delta":{"text":"Hel"}}',
            'data: {"type":"content_block_delta","delta":{"text":"lo"}}',
            'data: {"type":"message_stop","stop_reason":"end_turn"}',
            "",
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["stream"] is True
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    provider = build_provider(handler)
    chunks = [
        chunk
        async for chunk in provider.stream(
            PromptRequest(model="claude-3-5-sonnet-latest", messages=[ChatMessage.user("hello")])
        )
    ]

    assert [chunk.delta for chunk in chunks] == ["Hel", "lo", ""]
    assert chunks[-1].finish_reason == "end_turn"


async def test_anthropic_provider_uses_request_max_tokens():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["max_tokens"] == 256
        return httpx.Response(
            200,
            json={
                "model": "claude-3-5-sonnet-latest",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    provider = build_provider(handler)
    response = await provider.complete(
        PromptRequest(
            model="claude-3-5-sonnet-latest",
            max_tokens=256,
            messages=[ChatMessage.user("hello")],
        )
    )

    assert response.text == "ok"


async def test_anthropic_provider_requires_model():
    provider = AnthropicProvider(AnthropicConfig(api_key="secret"))

    with pytest.raises(AIConfigurationError):
        provider._build_payload(PromptRequest(messages=[ChatMessage.user("hello")]), stream=False)


async def test_anthropic_provider_rejects_invalid_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": []})

    provider = build_provider(handler)

    with pytest.raises(AIResponseError):
        await provider.complete(
            PromptRequest(model="claude-3-5-sonnet-latest", messages=[ChatMessage.user("hello")])
        )
