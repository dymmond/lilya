from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from lilya.contrib.ai import (
    AIClient,
    AIConfigurationError,
    AIResponse,
    AIResponseChunk,
    ChatMessage,
)


class DummyProvider:
    """
    Small fake provider used to test client behavior without external HTTP calls.
    """

    name = "dummy"

    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.last_request = None

    async def startup(self) -> None:
        self.started = True

    async def shutdown(self) -> None:
        self.stopped = True

    async def complete(self, request):
        self.last_request = request
        return AIResponse(text="ok", model=request.model, provider=self.name)

    async def stream(self, request) -> AsyncIterator[AIResponseChunk]:
        self.last_request = request
        yield AIResponseChunk(text="he", delta="he", model=request.model, provider=self.name)
        yield AIResponseChunk(text="llo", delta="llo", model=request.model, provider=self.name)


@pytest.mark.asyncio
async def test_ai_client_prompt_uses_defaults():
    provider = DummyProvider()
    client = AIClient(
        provider,
        default_model="gpt-test",
        default_system_prompt="You are helpful.",
    )

    response = await client.prompt("Hello")

    assert response.text == "ok"
    assert provider.last_request.model == "gpt-test"
    assert provider.last_request.system_prompt == "You are helpful."
    assert provider.last_request.messages[0].role == "user"
    assert provider.last_request.messages[0].content == "Hello"


@pytest.mark.asyncio
async def test_ai_client_chat_requires_model():
    provider = DummyProvider()
    client = AIClient(provider)

    with pytest.raises(AIConfigurationError):
        await client.chat([ChatMessage.user("hello")])


@pytest.mark.asyncio
async def test_ai_client_stream_yields_chunks():
    provider = DummyProvider()
    client = AIClient(provider, default_model="gpt-test")

    chunks = [chunk async for chunk in client.stream("Hello")]

    assert [chunk.delta for chunk in chunks] == ["he", "llo"]
    assert provider.last_request.model == "gpt-test"


@pytest.mark.asyncio
async def test_ai_client_lifecycle_delegates_to_provider():
    provider = DummyProvider()
    client = AIClient(provider, default_model="gpt-test")

    await client.startup()
    await client.shutdown()

    assert provider.started is True
    assert provider.stopped is True
