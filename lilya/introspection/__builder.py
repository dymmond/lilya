from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from lilya.introspection._graph import ApplicationGraph
from lilya.introspection._types import EdgeKind, GraphEdge, GraphNode, NodeKind
from lilya.middleware import DefineMiddleware
from lilya.permissions import DefinePermission
from lilya.routing import Include, Path

if TYPE_CHECKING:
    from lilya.apps import Lilya


def _node_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex}"


def _extract_middleware_class(mw: Any) -> Any:
    """
    mw is expected to be a DefineMiddleware; it iterates to (cls, args, kwargs).
    Fall back gracefully if a raw class is passed.
    """
    if isinstance(mw, DefineMiddleware):
        try:
            middleware_class, _args, _kwargs = mw
            return middleware_class
        except Exception:
            # Some implementations might store it under an attribute
            return getattr(mw, "middleware", mw)
    # Raw class (user passed class instead of DefineMiddleware)
    return mw


def _extract_permission_class(p: Any) -> Any:
    """
    p is expected to be a DefinePermission (tuple-like) or a class.
    """
    if isinstance(p, DefinePermission):
        try:
            permission_class, _args, _kwargs = p
            return permission_class
        except Exception:
            return getattr(p, "permission", p)
    return p


class GraphBuilder:
    """
    Internal-only utility that extracts a structural ASGI graph
    from a Lilya application instance. Read-only, no execution changes.
    """

    __slots__ = ("_nodes", "_edges", "_visited_apps")

    def __init__(self) -> None:
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []
        self._visited_apps: set[int] = set()

    def build(self, app: Lilya) -> ApplicationGraph:
        app_node = self._add_application(app)

        last = app_node
        for mw in getattr(app, "custom_middleware", ()):
            cls = _extract_middleware_class(mw)
            mw_node = self._add_middleware(cls)
            self._edge(last, mw_node, EdgeKind.WRAPS)
            last = mw_node

        router = self._discover_router(app)
        if router is not None:
            router_node = self._add_router(router)
            self._edge(last, router_node, EdgeKind.DISPATCHES_TO)
            self._walk_router(router, router_node)

        return ApplicationGraph(nodes=self._nodes, edges=self._edges)

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
        name = getattr(middleware, "__name__", str(middleware))
        node = GraphNode(
            id=_node_id("middleware"),
            kind=NodeKind.MIDDLEWARE,
            ref=middleware,
            metadata={"class": name},
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

    def _add_route(self, path: Path) -> GraphNode:
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
        name = getattr(permission, "__name__", str(permission))
        node = GraphNode(
            id=_node_id("permission"),
            kind=NodeKind.PERMISSION,
            ref=permission,
            metadata={"class": name},
        )
        self._nodes.append(node)
        return node

    def _add_include(self, include: Include) -> GraphNode:
        node = GraphNode(
            id=_node_id("include"),
            kind=NodeKind.INCLUDE,
            ref=include,
            metadata={
                "path": getattr(include, "path", None),
                "name": getattr(include, "name", None),
            },
        )
        self._nodes.append(node)
        return node

    def _walk_router(self, router: Any, router_node: GraphNode) -> None:
        from lilya.apps import ChildLilya, Lilya

        routes = getattr(router, "routes", None)
        if not routes:
            return

        for entry in routes:
            # Include?
            if isinstance(entry, Include):
                inc_node = self._add_include(entry)
                self._edge(router_node, inc_node, EdgeKind.DISPATCHES_TO)

                # include-level middleware (declared order)
                last = inc_node
                inc_mw = getattr(entry, "middleware", None) or ()
                for mw in inc_mw:
                    cls = _extract_middleware_class(mw)
                    mw_node = self._add_middleware(cls)
                    self._edge(last, mw_node, EdgeKind.WRAPS)
                    last = mw_node

                # include-level permissions (declared order)
                inc_perms = getattr(entry, "permissions", None) or ()
                for perm in inc_perms:
                    pcls = _extract_permission_class(perm)
                    perm_node = self._add_permission(pcls)
                    self._edge(last, perm_node, EdgeKind.WRAPS)
                    last = perm_node

                # Dive into child app, if present
                child = getattr(entry, "app", None)
                if isinstance(child, (Lilya, ChildLilya)) and id(child) not in self._visited_apps:
                    self._visited_apps.add(id(child))
                    child_router = getattr(child, "router", None)
                    if child_router is not None:
                        child_router_node = self._add_router(child_router)
                        self._edge(last, child_router_node, EdgeKind.DISPATCHES_TO)
                        self._walk_router(child_router, child_router_node)

                # If entry has its own `routes` list (raw), walk those too.
                if child is None:
                    raw_routes = getattr(entry, "routes", None)
                    if raw_routes:
                        # Treat them like normal paths hanging from the include
                        base = inc_node
                        for r in raw_routes:
                            path_node = self._add_route(r)
                            self._edge(base, path_node, EdgeKind.DISPATCHES_TO)
                            self._attach_route_local_layers(r, path_node)

                continue  # handled include

            # Path/WebSocketPath, etc. → normal route
            route_node = self._add_route(entry)
            self._edge(router_node, route_node, EdgeKind.DISPATCHES_TO)
            self._attach_route_local_layers(entry, route_node)

    def _attach_route_local_layers(self, route: Any, route_node: GraphNode) -> None:
        # Route-level middleware (declared order)
        last = route_node
        r_mw = getattr(route, "middleware", None) or ()
        for mw in r_mw:
            cls = _extract_middleware_class(mw)
            mw_node = self._add_middleware(cls)
            self._edge(last, mw_node, EdgeKind.WRAPS)
            last = mw_node

        # Route-level permissions (declared order)
        r_perms = getattr(route, "permissions", None) or ()
        for perm in r_perms:
            pcls = _extract_permission_class(perm)
            perm_node = self._add_permission(pcls)
            self._edge(last, perm_node, EdgeKind.WRAPS)
            last = perm_node

    def _edge(self, src: GraphNode, dst: GraphNode, kind: EdgeKind) -> None:
        self._edges.append(GraphEdge(source=src.id, target=dst.id, kind=kind))
