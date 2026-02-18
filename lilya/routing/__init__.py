from __future__ import annotations

from lilya import status as status
from lilya._internal._events import (
    AsyncLifespan as AsyncLifespan,
    handle_lifespan_events as handle_lifespan_events,
)
from lilya.conf import _monkay as _monkay
from lilya.conf.global_settings import Settings as Settings
from lilya.contrib.documentation import Doc as Doc
from lilya.datastructures import (
    URL as URL,
    SendReceiveSniffer as SendReceiveSniffer,
)
from lilya.enums import EventType as EventType
from lilya.exceptions import (
    ContinueRouting as ContinueRouting,
    HTTPException as HTTPException,
)
from lilya.requests import Request as Request
from lilya.responses import (
    PlainText as PlainText,
    RedirectResponse as RedirectResponse,
    Response as Response,
)
from lilya.types import Lifespan as Lifespan
from lilya.websockets import WebSocket as WebSocket, WebSocketClose as WebSocketClose

from .base import BasePath as BasePath
from .host import Host as Host
from .include import Include as Include
from .mixins import RoutingMethodsMixin as RoutingMethodsMixin
from .path import Path as Path
from .router import BaseRouter as BaseRouter, Router as Router
from .types import (
    NoMatchFound as NoMatchFound,
    PassPartialMatches as PassPartialMatches,
    PathHandler as PathHandler,
    T as T,
    get_name as get_name,
)
from .websocket import WebSocketPath as WebSocketPath

# Wire Include.router_class to Router (CRITICAL - must be AFTER imports)
Include.router_class = Router

# Aliases
RoutePath = Path
Route = Path
WebSocketRoute = WebSocketPath

# Public API
__all__ = [
    "BasePath",
    "BaseRouter",
    "Host",
    "Include",
    "NoMatchFound",
    "PassPartialMatches",
    "Path",
    "PathHandler",
    "Route",
    "RoutePath",
    "Router",
    "RoutingMethodsMixin",
    "WebSocketPath",
    "WebSocketRoute",
    "get_name",
]
