from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeKind(Enum):
    APPLICATION = "application"
    MIDDLEWARE = "middleware"
    ROUTER = "router"
    ROUTE = "route"
    PERMISSION = "permission"
    HANDLER = "handler"
    INCLUDE = "include"
    HOST = "host"
    WEBSOCKET = "websocket"


class EdgeKind(str, Enum):
    WRAPS = "wraps"
    DISPATCHES_TO = "dispatches_to"


@dataclass(frozen=True, slots=True)
class GraphNode:
    """
    A read-only representation of a structural ASGI support.

    Note:
        - `ref` is a opaque and should never be relied of for execution
        - metadata must be a JSON-serializable.
    """

    id: str
    kind: NodeKind
    ref: Any | None
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """
    A read-only representation of a relationship between two ASGI support structures.
    """

    source: str
    target: str
    kind: EdgeKind
