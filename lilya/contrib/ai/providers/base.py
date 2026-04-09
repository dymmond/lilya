from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Protocol

from lilya.contrib.ai.exceptions import AIProviderError
from lilya.contrib.ai.types import AIResponse, AIResponseChunk, PromptRequest

if TYPE_CHECKING:
    import httpx


class AIProvider(Protocol):
    """
    Protocol implemented by all AI providers supported by Lilya.
    """

    name: str

    async def startup(self) -> None:
        """
        Prepare the provider for use.
        """

    async def shutdown(self) -> None:
        """
        Dispose any provider resources.
        """

    async def complete(self, request: PromptRequest) -> AIResponse:
        """
        Execute a non-streaming completion request.
        """

    def stream(self, request: PromptRequest) -> AsyncIterator[AIResponseChunk]:
        """
        Execute a streaming completion request.
        """


class BaseAIProvider:
    """
    Convenience base class for providers that do not require lifecycle hooks.
    """

    name = "base"

    async def startup(self) -> None:
        """
        Prepare the provider for use.
        """

    async def shutdown(self) -> None:
        """
        Dispose any provider resources.
        """


class BaseHTTPProvider(BaseAIProvider):
    """
    Base class for providers backed by HTTP APIs.
    """

    def __init__(self, *, timeout: float, headers: dict[str, str] | None = None) -> None:
        """
        Initialize the HTTP provider with shared client settings.
        """
        self._timeout = timeout
        self._headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        """
        Lazily create the internal HTTP client.
        """
        if self._client is None:
            self._client = self._build_client()

    async def shutdown(self) -> None:
        """
        Close the internal HTTP client if it exists.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_client(self) -> httpx.AsyncClient:
        """
        Create the shared `httpx.AsyncClient`.
        """
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError(
                "httpx is required for lilya.contrib.ai. Install the `lilya[ai]` extra."
            ) from exc

        return httpx.AsyncClient(timeout=self._timeout, headers=self._headers)

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Retrieve or lazily create the internal HTTP client.
        """
        if self._client is None:
            self._client = self._build_client()
        return self._client

    @staticmethod
    async def _iter_sse_data(response: httpx.Response) -> AsyncIterator[str]:
        """
        Iterate server-sent-event `data:` payloads from an HTTP response.
        """
        buffer: list[str] = []
        async for line in response.aiter_lines():
            if not line:
                if buffer:
                    yield "\n".join(buffer)
                    buffer = []
                continue
            if line.startswith("data:"):
                buffer.append(line[5:].lstrip())

        if buffer:
            yield "\n".join(buffer)

    @staticmethod
    def _decode_json(payload: str) -> dict[str, Any]:
        """
        Decode a JSON payload and wrap parse failures in a provider error.
        """
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise AIProviderError("Provider returned invalid JSON payload.") from exc
        if not isinstance(data, dict):
            raise AIProviderError("Provider returned a non-object JSON payload.")
        return data
