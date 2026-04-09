from __future__ import annotations

import json

import httpx
import pytest

from lilya.contrib.ai import (
    AIConfigurationError,
    AIResponseError,
    ChatMessage,
    GroqConfig,
    GroqProvider,
    MistralConfig,
    MistralProvider,
    OpenAICompatibleProvider,
    OpenAIConfig,
    OpenAIProvider,
    PromptRequest,
)

pytestmark = pytest.mark.asyncio


def build_provider(handler, provider_cls=OpenAIProvider, config=None):
    config = config or OpenAIConfig(api_key="secret")
    provider = provider_cls(config)
    provider._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), headers={})
    return provider


async def test_openai_provider_parses_chat_completion_response():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert request.url.path == "/v1/chat/completions"
        assert payload["model"] == "gpt-4o-mini"
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["content"] == "hello"
        return httpx.Response(
            200,
            json={
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "Hello there"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 4,
                    "total_tokens": 15,
                },
            },
        )

    provider = build_provider(handler)
    response = await provider.complete(
        PromptRequest(
            model="gpt-4o-mini",
            system_prompt="You are helpful.",
            messages=[ChatMessage.user("hello")],
        )
    )

    assert response.text == "Hello there"
    assert response.provider == "openai"
    assert response.usage is not None
    assert response.usage.total_tokens == 15


async def test_openai_provider_streams_chunks():
    body = "\n\n".join(
        [
            'data: {"choices":[{"delta":{"content":"Hel"},"finish_reason":null}],"model":"gpt-4o-mini"}',
            'data: {"choices":[{"delta":{"content":"lo"},"finish_reason":null}],"model":"gpt-4o-mini"}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"model":"gpt-4o-mini"}',
            "data: [DONE]",
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
            PromptRequest(model="gpt-4o-mini", messages=[ChatMessage.user("hello")])
        )
    ]

    assert [chunk.delta for chunk in chunks] == ["Hel", "lo", ""]
    assert chunks[-1].finish_reason == "stop"


async def test_openai_compatible_provider_supports_groq_name_and_url():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["host"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "model": "llama-3.3-70b-versatile",
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            },
        )

    provider = build_provider(
        handler,
        provider_cls=GroqProvider,
        config=GroqConfig(api_key="secret"),
    )
    response = await provider.complete(
        PromptRequest(model="llama-3.3-70b-versatile", messages=[ChatMessage.user("hello")])
    )

    assert response.provider == "groq"
    assert captured["host"].startswith("https://api.groq.com/openai/v1/chat/completions")


async def test_openai_compatible_provider_supports_mistral_name_and_url():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["host"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "model": "mistral-small-latest",
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            },
        )

    provider = build_provider(
        handler,
        provider_cls=MistralProvider,
        config=MistralConfig(api_key="secret"),
    )
    response = await provider.complete(
        PromptRequest(model="mistral-small-latest", messages=[ChatMessage.user("hello")])
    )

    assert response.provider == "mistral"
    assert captured["host"].startswith("https://api.mistral.ai/v1/chat/completions")


async def test_openai_provider_requires_model():
    provider = OpenAICompatibleProvider(OpenAIConfig(api_key="secret"))

    with pytest.raises(AIConfigurationError):
        provider._build_payload(PromptRequest(messages=[ChatMessage.user("hello")]), stream=False)


async def test_openai_provider_rejects_invalid_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = build_provider(handler)

    with pytest.raises(AIResponseError):
        await provider.complete(
            PromptRequest(model="gpt-4o-mini", messages=[ChatMessage.user("hello")])
        )
