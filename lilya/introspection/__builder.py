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


def _make_node_id(prefix: str) -> str:
    """Generate a unique, readable node id with a stable prefix.

    Args:
        prefix: A short string describing the node category (e.g., "app", "route").

    Returns:
        A unique identifier of the form: "<prefix>:<uuid_hex>".
    """
    return f"{prefix}:{uuid4().hex}"


def _resolve_middleware_class(middleware_like: Any) -> Any:
    """Resolve a middleware class from a `DefineMiddleware` or a raw class.

    `DefineMiddleware` is typically iterable and yields `(cls, args, kwargs)`.
    This function returns the class (`cls`). If a raw class was passed instead of
    `DefineMiddleware`, that class is returned unchanged.

    Args:
        middleware_like: Either a `DefineMiddleware` instance or a class.

    Returns:
        The middleware class object.
    """
    if isinstance(middleware_like, DefineMiddleware):
        try:
            middleware_class, _args, _kwargs = middleware_like
            return middleware_class
        except Exception:
            # Fallback for alternative implementations carrying the class as attribute.
            return getattr(middleware_like, "middleware", middleware_like)
    # Raw class (user passed class instead of DefineMiddleware)
    return middleware_like


def _resolve_permission_class(permission_like: Any) -> Any:
    """Resolve a permission class from a `DefinePermission` or a raw class.

    `DefinePermission` is typically tuple-like and yields `(cls, args, kwargs)`.
    This function returns the class (`cls`). If a raw class was passed, that
    class is returned unchanged.

    Args:
        permission_like: Either a `DefinePermission` instance or a class.

    Returns:
        The permission class object.
    """
    if isinstance(permission_like, DefinePermission):
        try:
            permission_class, _args, _kwargs = permission_like
            return permission_class
        except Exception:
            # Fallback for implementations carrying the class as attribute.
            return getattr(permission_like, "permission", permission_like)
    return permission_like


class GraphBuilder:
    """Extract a structural graph representation from a Lilya application.

    This utility inspects a Lilya application instance and builds a read-only
    `ApplicationGraph` depicting the app's composition:

    * Global middleware wrapping the application
    * Router dispatch relationships
    * Includes and their local middleware/permissions
    * Routes and their local middleware/permissions

    Notes:
        - The graph is *structural* only; it does not perform runtime matching.
        - Edge insertion order is preserved, and WRAPS chains are treated as linear.

    Attributes:
        _nodes: Accumulated nodes for the final graph.
        _edges: Accumulated edges for the final graph.
        _visited_apps: Set of visited app identities (via `id(...)`) to avoid cycles.
    """

    __slots__ = ("_nodes", "_edges", "_visited_apps")

    def __init__(self) -> None:
        """Initialize a new, empty builder."""
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []
        self._visited_apps: set[int] = set()

    def build(self, app: Lilya, external: bool = False) -> ApplicationGraph:
        """Build an `ApplicationGraph` from a Lilya application instance.

        The resulting graph contains:
            - One APPLICATION node
            - A linear WRAPS chain for global middleware
            - A DISPATCHES_TO edge to the router (if discovered)
            - Router traversal that attaches includes, routes, and their layers

        Args:
            app: Lilya application instance.

        Returns:
            An `ApplicationGraph` representing the app's structure.
        """
        app_node = self._add_application(app)

        # Global middleware chain, in declared order (outer -> inner).
        last_wrapped_node = app_node
        for middleware_like in getattr(app, "custom_middleware", ()):
            middleware_class = _resolve_middleware_class(middleware_like)
            middleware_node = self._add_middleware(middleware_class)
            self._add_edge(last_wrapped_node, middleware_node, EdgeKind.WRAPS)
            last_wrapped_node = middleware_node

        router = self._resolve_router(app)
        if router is not None:
            router_node = self._add_router(router)
            self._add_edge(last_wrapped_node, router_node, EdgeKind.DISPATCHES_TO)
            self._traverse_router(router, router_node)

        return ApplicationGraph(nodes=self._nodes, edges=self._edges)

    def _resolve_router(self, app: Lilya) -> Any | None:
        """Discover a router-like object from the application.

        Preference order:
            1. `app.router` if present and non-None
            2. Common fallbacks: `app._router`, `app.routes` (if it has a `.routes` attribute)

        Args:
            app: Lilya application.

        Returns:
            A router-like object or None if not found.
        """
        if hasattr(app, "router") and app.router is not None:
            return app.router
        for attr_name in ("_router", "routes"):
            candidate = getattr(app, attr_name, None)
            if candidate is not None and hasattr(candidate, "routes"):
                return candidate
        return None

    def _add_application(self, app: Lilya) -> GraphNode:
        """Create and register an APPLICATION node for the given app."""
        node = GraphNode(
            id=_make_node_id("app"),
            kind=NodeKind.APPLICATION,
            ref=app,
            metadata={"debug": getattr(app, "debug", False)},
        )
        self._nodes.append(node)
        return node

    def _add_middleware(self, middleware_class: Any) -> GraphNode:
        """Create and register a MIDDLEWARE node."""
        class_name = getattr(middleware_class, "__name__", str(middleware_class))
        node = GraphNode(
            id=_make_node_id("middleware"),
            kind=NodeKind.MIDDLEWARE,
            ref=middleware_class,
            metadata={"class": class_name},
        )
        self._nodes.append(node)
        return node

    def _add_router(self, router: Any) -> GraphNode:
        """Create and register a ROUTER node."""
        node = GraphNode(
            id=_make_node_id("router"),
            kind=NodeKind.ROUTER,
            ref=router,
            metadata={},
        )
        self._nodes.append(node)
        return node

    def _add_route(self, route_path: Path) -> GraphNode:
        """Create and register a ROUTE node from a `Path`-like object.

        Attempts to read:
            - path string from `.path` or `.pattern`
            - methods from `.methods` or `.http_methods`

        Args:
            route_path: A `Path`-like routing entry.

        Returns:
            The new route node.
        """
        path_str = getattr(route_path, "path", None) or getattr(route_path, "pattern", None)
        methods = getattr(route_path, "methods", None)
        if methods is None and hasattr(route_path, "http_methods"):
            methods = route_path.http_methods

        node = GraphNode(
            id=_make_node_id("route"),
            kind=NodeKind.ROUTE,
            ref=route_path,
            metadata={
                "path": path_str,
                "methods": tuple(methods) if methods is not None else (),
            },
        )
        self._nodes.append(node)
        return node

    def _add_permission(self, permission_class: Any) -> GraphNode:
        """Create and register a PERMISSION node."""
        class_name = getattr(permission_class, "__name__", str(permission_class))
        node = GraphNode(
            id=_make_node_id("permission"),
            kind=NodeKind.PERMISSION,
            ref=permission_class,
            metadata={"class": class_name},
        )
        self._nodes.append(node)
        return node

    def _add_include(self, include: Include) -> GraphNode:
        """Create and register an INCLUDE node."""
        node = GraphNode(
            id=_make_node_id("include"),
            kind=NodeKind.INCLUDE,
            ref=include,
            metadata={
                "path": getattr(include, "path", None),
                "name": getattr(include, "name", None),
            },
        )
        self._nodes.append(node)
        return node

    def _traverse_router(self, router: Any, router_node: GraphNode) -> None:
        """Traverse a router-like object and attach includes and routes.

        For each entry in `router.routes`:
            * If `Include`:
                - Attach INCLUDE node via DISPATCHES_TO
                - Add include-level middleware then permissions (WRAPS chain)
                - If include has a child app, descend into its router
                - If include has raw `routes`, attach them under the include
            * Else:
                - Treat as a route path entry and attach its local layers

        Args:
            router: A router-like object with a `routes` attribute.
            router_node: The ROUTER node from which we dispatch.
        """
        from lilya.apps import ChildLilya, Lilya

        routes = getattr(router, "routes", None)
        if not routes:
            return

        for route_entry in routes:
            # Include?
            if isinstance(route_entry, Include):
                include_node = self._add_include(route_entry)
                self._add_edge(router_node, include_node, EdgeKind.DISPATCHES_TO)

                # Include-level middleware (declared outer -> inner)
                last_wrapped_node = include_node
                include_middleware = getattr(route_entry, "middleware", None) or ()
                for middleware_like in include_middleware:
                    middleware_class = _resolve_middleware_class(middleware_like)
                    middleware_node = self._add_middleware(middleware_class)
                    self._add_edge(last_wrapped_node, middleware_node, EdgeKind.WRAPS)
                    last_wrapped_node = middleware_node

                # Include-level permissions (declared order)
                include_permissions = getattr(route_entry, "permissions", None) or ()
                for permission_like in include_permissions:
                    permission_class = _resolve_permission_class(permission_like)
                    permission_node = self._add_permission(permission_class)
                    self._add_edge(last_wrapped_node, permission_node, EdgeKind.WRAPS)
                    last_wrapped_node = permission_node

                # Dive into child app, if present
                child_app = getattr(route_entry, "app", None)
                if (
                    isinstance(child_app, (Lilya, ChildLilya))
                    and id(child_app) not in self._visited_apps
                ):
                    self._visited_apps.add(id(child_app))
                    child_router = getattr(child_app, "router", None)
                    if child_router is not None:
                        child_router_node = self._add_router(child_router)
                        self._add_edge(
                            last_wrapped_node, child_router_node, EdgeKind.DISPATCHES_TO
                        )
                        self._traverse_router(child_router, child_router_node)

                # If entry has its own `routes` list (raw), walk those too.
                if child_app is None:
                    raw_routes = getattr(route_entry, "routes", None)
                    if raw_routes:
                        base_dispatch_node = include_node
                        for raw_route in raw_routes:
                            path_node = self._add_route(raw_route)
                            self._add_edge(base_dispatch_node, path_node, EdgeKind.DISPATCHES_TO)
                            self._attach_route_layers(raw_route, path_node)

                continue  # handled include

            # Path/WebSocketPath, etc. → normal route
            route_node = self._add_route(route_entry)
            self._add_edge(router_node, route_node, EdgeKind.DISPATCHES_TO)
            self._attach_route_layers(route_entry, route_node)

    def _attach_route_layers(self, route_entry: Any, route_node: GraphNode) -> None:
        """Attach route-level middleware and permissions to a route node.

        Order of attachment:
            1. Route middleware (declared order; WRAPS chain)
            2. Route permissions (declared order; WRAPS chain)

        Args:
            route_entry: A route-like object with optional `middleware` / `permissions`.
            route_node: The route node to which layers will be attached.
        """
        # Route-level middleware (declared outer -> inner)
        last_wrapped_node = route_node
        route_middleware = getattr(route_entry, "middleware", None) or ()
        for middleware_like in route_middleware:
            middleware_class = _resolve_middleware_class(middleware_like)
            middleware_node = self._add_middleware(middleware_class)
            self._add_edge(last_wrapped_node, middleware_node, EdgeKind.WRAPS)
            last_wrapped_node = middleware_node

        # Route-level permissions (declared order)
        route_permissions = getattr(route_entry, "permissions", None) or ()
        for permission_like in route_permissions:
            permission_class = _resolve_permission_class(permission_like)
            permission_node = self._add_permission(permission_class)
            self._add_edge(last_wrapped_node, permission_node, EdgeKind.WRAPS)
            last_wrapped_node = permission_node

    def _add_edge(self, src: GraphNode, dst: GraphNode, kind: EdgeKind) -> None:
        """Create and register a directed edge between two nodes.

        Args:
            src: Source node.
            dst: Target node.
            kind: Edge kind (e.g., WRAPS, DISPATCHES_TO).
        """
        self._edges.append(GraphEdge(source=src.id, target=dst.id, kind=kind))
