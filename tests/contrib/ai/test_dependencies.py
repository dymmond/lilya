from __future__ import annotations

import pytest

from lilya.apps import Lilya
from lilya.contrib.ai import AI, AIClient, AIResponse, ChatMessage, setup_ai
from lilya.dependencies import Provide
from lilya.testclient import TestClient


class InMemoryProvider:
    """
    Small provider used for dependency injection tests.
    """

    name = "memory"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def complete(self, request):
        self.calls.append(request.messages[-1].content)
        return AIResponse(text="done", model=request.model, provider=self.name)

    async def stream(self, request):
        if False:
            yield None


pytestmark = pytest.mark.asyncio


async def test_ai_dependency_injection_works():
    provider = InMemoryProvider()
    client = AIClient(provider, default_model="gpt-test")
    app = Lilya()
    setup_ai(app, client=client)

    @app.post("/generate", dependencies={"ai": AI})
    async def generate(ai: AI):
        response = await ai.chat([ChatMessage.user("explain Lilya")])
        return {"text": response.text}

    http_client = TestClient(app)
    response = http_client.post("/generate")

    assert response.status_code == 200
    assert response.json() == {"text": "done"}
    assert provider.calls == ["explain Lilya"]


async def test_ai_dependency_without_setup_raises():
    app = Lilya()

    @app.get("/broken", dependencies={"ai": AI})
    async def broken(ai: AI):
        return {"ok": True}

    client = TestClient(app)

    with pytest.raises(RuntimeError):
        client.get("/broken")


async def test_ai_dependency_reuses_same_instance():
    provider = InMemoryProvider()
    client = AIClient(provider, default_model="gpt-test")
    app = Lilya()
    setup_ai(app, client=client)

    seen: list[AIClient] = []

    @app.get("/ping", dependencies={"ai": AI})
    async def ping(ai: AI):
        seen.append(ai)
        return {"ok": True}

    http_client = TestClient(app)
    http_client.get("/ping")
    http_client.get("/ping")

    assert seen[0] is seen[1]
    assert seen[0] is client


async def test_ai_dependency_override():
    provider = InMemoryProvider()
    client = AIClient(provider, default_model="gpt-test")
    app = Lilya()
    setup_ai(app, client=client)

    class FakeClient:
        async def chat(self, messages):
            return AIResponse(text="fake", model="fake-model", provider="fake")

    fake_client = FakeClient()

    async def _resolve_fake(request, **kwargs):
        return fake_client

    fake_ai = Provide(_resolve_fake)

    @app.post("/generate", dependencies={"ai": fake_ai})
    async def generate(ai: AI):
        response = await ai.chat([ChatMessage.user("anything")])
        return {"text": response.text}

    http_client = TestClient(app)
    response = http_client.post("/generate")

    assert response.status_code == 200
    assert response.json() == {"text": "fake"}


async def test_ai_dependency_misconfigured_state_raises():
    app = Lilya()
    app.state.ai = object()

    @app.get("/bad", dependencies={"ai": AI})
    async def bad(ai: AI):
        return {"ok": True}

    client = TestClient(app)

    with pytest.raises(RuntimeError):
        client.get("/bad")
