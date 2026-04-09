from __future__ import annotations

from typing import Any

from lilya.contrib.ai.client import AIClient
from lilya.dependencies import Provide
from lilya.requests import Request


async def _resolve_ai_client(request: Request, **kwargs: Any) -> AIClient:
    """
    Resolve the configured global AI client from `request.app.state`.

    This dependency mirrors the existing Lilya contrib pattern used by
    optional services such as mail: configuration happens once during
    startup, and endpoints receive a ready-to-use client through DI.
    """
    client = getattr(request.app.state, "ai", None)
    if not isinstance(client, AIClient):
        raise RuntimeError(
            "No AIClient configured. Did you forget to call `setup_ai(app, client=...)`?"
        )
    return client


AI = Provide(_resolve_ai_client)
