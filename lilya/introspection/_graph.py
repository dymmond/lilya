from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any, cast

from lilya.serializers import serializer

from ._types import EdgeKind, GraphEdge, GraphNode, NodeKind


def _to_json_safe(obj: Any) -> Any:
    """Recursively convert Python objects into JSON-friendly, deterministic values.

    Conversion rules:
        * Enum -> enum.value
        * Mapping -> dict with JSON-safe values (keys left as-is)
        * tuple/list -> list with JSON-safe values
        * set -> sorted list of JSON-safe values (for determinism)
        * Other types -> returned unchanged

    Args:
        obj: Any Python object to be converted.

    Returns:
        A JSON-serializable representation with deterministic ordering where applicable.
    """
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Mapping):
        # Keys are preserved; values are normalized.
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(v) for v in obj]
    if isinstance(obj, set):
        # Sort after normalizing for determinism.
        return sorted(_to_json_safe(v) for v in obj)
    return obj


class ApplicationGraph:
    """Immutable structural graph of an application composition.

    The graph contains nodes (application, routes, middleware, permissions, includes, etc.)
    and directed edges with an `EdgeKind` that encode structural relationships
    (e.g., WRAPS). The class provides read-only views and helpers to traverse
    common structures such as middleware and permission chains.

    This graph is *structural*, not an executable router or runtime matcher.

    Attributes:
        _nodes_by_id: Mapping from node id to `GraphNode`.
        _edges: Tuple of all `GraphEdge` instances.
        _nodes_by_kind: Mapping from `NodeKind` to tuple of nodes of that kind.
        _outgoing: Adjacency list mapping node id -> tuple of (edge, dst_node).
        _incoming: Reverse adjacency list mapping node id -> tuple of (edge, src_node).
    """

    __slots__ = ("_nodes_by_id", "_edges", "_nodes_by_kind", "_outgoing", "_incoming")

    def __init__(self, *, nodes: Iterable[GraphNode], edges: Iterable[GraphEdge]) -> None:
        """Build a graph from nodes and edges.

        Dangling edges (edges whose source/target are not present among nodes)
        are ignored defensively.

        Args:
            nodes: Iterable of graph nodes.
            edges: Iterable of graph edges.
        """
        nodes_by_id = {node.id: node for node in nodes}

        self._nodes_by_id: Mapping[str, GraphNode] = nodes_by_id
        self._edges: tuple[GraphEdge, ...] = tuple(edges)

        nodes_by_kind_dict: dict[NodeKind, list[GraphNode]] = defaultdict(list)
        for node in nodes_by_id.values():
            nodes_by_kind_dict[node.kind].append(node)
        # Freeze for immutability semantics.
        self._nodes_by_kind: Mapping[NodeKind, tuple[GraphNode, ...]] = {
            kind: tuple(kind_nodes) for kind, kind_nodes in nodes_by_kind_dict.items()
        }

        outgoing: dict[str, list[tuple[GraphEdge, GraphNode]]] = defaultdict(list)
        incoming: dict[str, list[tuple[GraphEdge, GraphNode]]] = defaultdict(list)

        for edge in self._edges:
            src = nodes_by_id.get(edge.source)
            dst = nodes_by_id.get(edge.target)
            if not src or not dst:
                # Ignore dangling edges to keep traversals clean.
                continue
            outgoing[src.id].append((edge, dst))
            incoming[dst.id].append((edge, src))

        # Freeze adjacency lists.
        self._outgoing = {k: tuple(v) for k, v in outgoing.items()}
        self._incoming = {k: tuple(v) for k, v in incoming.items()}

    @property
    def nodes(self) -> Mapping[str, GraphNode]:
        """All nodes indexed by their identifier."""
        return self._nodes_by_id

    @property
    def edges(self) -> tuple[GraphEdge, ...]:
        """All edges in insertion order."""
        return self._edges

    def by_kind(self, kind: NodeKind) -> tuple[GraphNode, ...]:
        """Return all nodes of the given kind.

        Args:
            kind: NodeKind to filter by.

        Returns:
            A tuple of nodes of the requested kind. Empty if none exist.
        """
        return self._nodes_by_kind.get(kind, ())

    def application(self) -> GraphNode:
        """Return the single APPLICATION node.

        Returns:
            The application node.

        Raises:
            RuntimeError: If there is no application node or if multiple exist.
        """
        apps = self.by_kind(NodeKind.APPLICATION)
        if not apps:
            raise RuntimeError("ApplicationGraph has no APPLICATION node.")
        if len(apps) > 1:
            # Raise to avoid ambiguity.
            raise RuntimeError("ApplicationGraph has multiple APPLICATION nodes.")
        return apps[0]

    def middlewares(self) -> tuple[GraphNode, ...]:
        """Return global middleware nodes in outer-to-inner wrapping order.

        Follows a linear chain of `EdgeKind.WRAPS` starting from the application node.
        Traversal stops when the next node is not of kind MIDDLEWARE or no WRAPS edge exists.

        Returns:
            A tuple of middleware nodes in the order they wrap the app.
        """
        current = self.application()
        ordered: list[GraphNode] = []

        while True:
            outgoing_edges = self._outgoing.get(current.id, ())
            wraps_targets = [dst for (edge, dst) in outgoing_edges if edge.kind == EdgeKind.WRAPS]
            if not wraps_targets:
                break
            next_node = wraps_targets[0]  # Keep insertion order; assume linear chain.
            if next_node.kind != NodeKind.MIDDLEWARE:
                break
            ordered.append(next_node)
            current = next_node

        return tuple(ordered)

    def routes(self) -> tuple[GraphNode, ...]:
        """Return all route nodes."""
        return self.by_kind(NodeKind.ROUTE)

    def route_by_path(self, path: str) -> GraphNode | None:
        """Return the route node with an exact metadata path match.

        This is a structural lookup against `metadata['path']`, not a runtime pattern match.

        Args:
            path: Exact path to match.

        Returns:
            The matching route node, or None if not found.
        """
        for route_node in self.routes():
            if route_node.metadata.get("path") == path:
                return route_node
        return None

    def permissions_for(self, route: GraphNode) -> tuple[GraphNode, ...]:
        """Return permission nodes attached to the given route in wrapping order.

        Follows a linear chain of `EdgeKind.WRAPS` starting from the route node.
        Stops when the next node is not of kind PERMISSION or no WRAPS edge exists.

        Args:
            route: A node of kind ROUTE.

        Returns:
            A tuple of permission nodes.

        Raises:
            TypeError: If `route` is not a ROUTE node.
        """
        if route.kind != NodeKind.ROUTE:
            raise TypeError("permissions_for expects a ROUTE node.")

        ordered: list[GraphNode] = []
        current = route

        while True:
            outgoing_edges = self._outgoing.get(current.id, ())
            wraps_targets = [dst for (edge, dst) in outgoing_edges if edge.kind == EdgeKind.WRAPS]
            if not wraps_targets:
                break
            next_node = wraps_targets[0]
            if next_node.kind != NodeKind.PERMISSION:
                break
            ordered.append(next_node)
            current = next_node

        return tuple(ordered)

    def explain(self, path: str) -> dict[str, Any]:
        """Return a structural explanation for a route.

        The explanation includes:
            * app.debug flag (from application node metadata)
            * global middlewares (class names, outer-to-inner)
            * route (path, methods)
            * route permissions (class names, outer-to-inner)

        Args:
            path: Exact route path to look up (matches `metadata['path']`).

        Returns:
            A dictionary describing the structural composition.

        Raises:
            ValueError: If no route is found for the given path.
        """
        route_node = self.route_by_path(path)
        if route_node is None:
            raise ValueError(f"Route not found for path: {path!r}")

        middleware_classes = [
            node.metadata.get("class", str(node.ref.__class__.__qualname__))
            for node in self.middlewares()
        ]
        permission_classes = [
            node.metadata.get("class", str(node.ref.__class__.__qualname__))
            for node in self.permissions_for(route_node)
        ]

        app_debug = bool(self.application().metadata.get("debug", False))

        return {
            "app": {"debug": app_debug},
            "middlewares": tuple(middleware_classes),
            "route": {
                "path": route_node.metadata.get("path"),
                "methods": route_node.metadata.get("methods", ()),
            },
            "permissions": tuple(permission_classes),
        }

    def includes(self) -> tuple[GraphNode, ...]:
        """Return all include nodes."""
        return self.by_kind(NodeKind.INCLUDE)

    def route_middlewares(self, route: GraphNode) -> tuple[GraphNode, ...]:
        """Return middleware nodes that wrap a specific route, in order.

        Traverses a WRAPS chain starting from the route node and collects
        consecutive MIDDLEWARE nodes.

        Args:
            route: A node of kind ROUTE.

        Returns:
            A tuple of middleware nodes.

        Raises:
            TypeError: If `route` is not a ROUTE node.
        """
        if route.kind != NodeKind.ROUTE:
            raise TypeError("route_middlewares expects a ROUTE node.")

        ordered: list[GraphNode] = []
        current = route

        while True:
            outgoing_edges = self._outgoing.get(current.id, ())
            wraps_targets = [dst for (edge, dst) in outgoing_edges if edge.kind == EdgeKind.WRAPS]
            if not wraps_targets:
                break
            next_node = wraps_targets[0]
            if next_node.kind != NodeKind.MIDDLEWARE:
                break
            ordered.append(next_node)
            current = next_node

        return tuple(ordered)

    def include_layers(self, include: GraphNode) -> dict[str, tuple[GraphNode, ...]]:
        """Return middleware and permission layers directly attached to an Include node.

        Traverses a WRAPS chain starting from the include node and collects
        consecutive MIDDLEWARE and PERMISSION nodes, in the order they wrap.

        Args:
            include: A node of kind INCLUDE.

        Returns:
            A dictionary with:
                * "middlewares": tuple of middleware nodes
                * "permissions": tuple of permission nodes

        Raises:
            TypeError: If `include` is not an INCLUDE node.
        """
        if include.kind != NodeKind.INCLUDE:
            raise TypeError("include_layers expects an INCLUDE node.")

        middlewares: list[GraphNode] = []
        permissions: list[GraphNode] = []

        current = include
        while True:
            outgoing_edges = self._outgoing.get(current.id, ())
            wraps_targets = [dst for (edge, dst) in outgoing_edges if edge.kind == EdgeKind.WRAPS]
            if not wraps_targets:
                break
            next_node = wraps_targets[0]
            if next_node.kind == NodeKind.MIDDLEWARE:
                middlewares.append(next_node)
                current = next_node
                continue
            if next_node.kind == NodeKind.PERMISSION:
                permissions.append(next_node)
                current = next_node
                continue
            break

        return {"middlewares": tuple(middlewares), "permissions": tuple(permissions)}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation of the graph.

        Notes:
            * The `ref` attribute of nodes is intentionally excluded.
            * Output is read-only and tooling-friendly.
        """
        return {
            "nodes": [
                {
                    "id": node.id,
                    "kind": node.kind.value,
                    "metadata": _to_json_safe(node.metadata),
                }
                for node in self._nodes_by_id.values()
            ],
            "edges": [
                {"source": edge.source, "target": edge.target, "kind": edge.kind.value}
                for edge in self._edges
            ],
        }

    def to_json(self, *, indent: int | None = 2, sort_keys: bool = False) -> str:
        """Return a JSON string representation of the graph.

        Args:
            indent: JSON indentation (None for the most compact).
            sort_keys: Whether to sort keys for deterministic output.

        Returns:
            A JSON string.
        """
        return cast(
            str,
            serializer.dumps(
                self.to_dict(),
                indent=indent,
                sort_keys=sort_keys,
            ),
        )
