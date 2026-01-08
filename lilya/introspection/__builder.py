from __future__ import annotations

from typing import Any
from uuid import uuid4

from lilya.apps import Lilya
from lilya.introspection._graph import ApplicationGraph
from lilya.introspection._types import EdgeKind, GraphEdge, GraphNode, NodeKind


def _node_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex}"


class GraphBuilder:
    """
    Internal-only utility that extracts a structural ASGI graph
    from a Lilya application instance. Read-only, no execution changes.
    """

    __slots__ = ("_nodes", "_edges")

    def __init__(self) -> None:
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []

    def build(self, app: Lilya) -> ApplicationGraph:
        app_node = self._add_application(app)

        last = app_node
        for mw in self._iter_middleware_stack(app):
            mw_node = self._add_middleware(mw)
            self._edge(last, mw_node, EdgeKind.WRAPS)
            last = mw_node

        router = self._discover_router(app)
        if router is not None:
            router_node = self._add_router(router)
            self._edge(last, router_node, EdgeKind.DISPATCHES_TO)
            self._walk_router(router, router_node)

        return ApplicationGraph(nodes=self._nodes, edges=self._edges)

    def _iter_middleware_stack(self, app: Lilya) -> tuple[Any, ...]:
        """
        Returns the middleware instances from app.middleware_stack.
        Assumes stack is iterable in the order they wrap the app.
        """
        stack = getattr(app, "middleware_stack", None)
        if stack is None:
            return ()

        try:
            return tuple(stack)
        except TypeError:
            for name in ("stack", "middlewares", "_stack"):
                seq = getattr(stack, name, None)
                if isinstance(seq, (list, tuple)):
                    return tuple(seq)
        return ()

    def _discover_router(self, app: Lilya) -> Any | None:
        """
        Prefer app.router if present; otherwise, try common fallbacks.
        """
        if hasattr(app, "router") and app.router is not None:
            return app.router
        for name in ("_router", "routes"):
            obj = getattr(app, name, None)
            if obj is not None and hasattr(obj, "routes"):
                return obj
        return None

    def _add_application(self, app: Lilya) -> GraphNode:
        node = GraphNode(
            id=_node_id("app"),
            kind=NodeKind.APPLICATION,
            ref=app,
            metadata={"debug": getattr(app, "debug", False)},
        )
        self._nodes.append(node)
        return node

    def _add_middleware(self, middleware: Any) -> GraphNode:
        node = GraphNode(
            id=_node_id("middleware"),
            kind=NodeKind.MIDDLEWARE,
            ref=middleware,
            metadata={"class": type(middleware).__qualname__},
        )
        self._nodes.append(node)
        return node

    def _add_router(self, router: Any) -> GraphNode:
        node = GraphNode(
            id=_node_id("router"),
            kind=NodeKind.ROUTER,
            ref=router,
            metadata={},
        )
        self._nodes.append(node)
        return node

    def _add_route(self, path: Any) -> GraphNode:
        path_str = getattr(path, "path", None) or getattr(path, "pattern", None)
        methods = getattr(path, "methods", None)
        if methods is None and hasattr(path, "http_methods"):
            methods = path.http_methods
        node = GraphNode(
            id=_node_id("route"),
            kind=NodeKind.ROUTE,
            ref=path,
            metadata={
                "path": path_str,
                "methods": tuple(methods) if methods is not None else (),
            },
        )
        self._nodes.append(node)
        return node

    def _add_permission(self, permission: Any) -> GraphNode:
        node = GraphNode(
            id=_node_id("permission"),
            kind=NodeKind.PERMISSION,
            ref=permission,
            metadata={"class": type(permission).__qualname__},
        )
        self._nodes.append(node)
        return node

    def _walk_router(self, router: Any, router_node: GraphNode) -> None:
        routes = getattr(router, "routes", None)
        if not routes:
            return

        for route in routes:
            route_node = self._add_route(route)
            self._edge(router_node, route_node, EdgeKind.DISPATCHES_TO)

            permissions = getattr(route, "permissions", None)
            if permissions:
                last = route_node
                for perm in permissions:
                    perm_node = self._add_permission(perm)
                    self._edge(last, perm_node, EdgeKind.WRAPS)
                    last = perm_node

    def _edge(self, src: GraphNode, dst: GraphNode, kind: EdgeKind) -> None:
        self._edges.append(GraphEdge(source=src.id, target=dst.id, kind=kind))
