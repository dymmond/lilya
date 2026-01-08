from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from ._types import EdgeKind, GraphEdge, GraphNode, NodeKind


class ApplicationGraph:
    __slots__ = ("_nodes", "_edges", "_by_kind", "_out", "_in")

    def __init__(self, *, nodes: Iterable[GraphNode], edges: Iterable[GraphEdge]) -> None:
        node_map = {node.id: node for node in nodes}

        self._nodes: Mapping[str, GraphNode] = node_map
        self._edges: tuple[GraphEdge, ...] = tuple(edges)

        by_kind: dict[NodeKind, list[GraphNode]] = defaultdict(list)

        for node in node_map.values():
            by_kind[node.kind].append(node)

        self._by_kind = dict(by_kind)

        out: dict[str, list[tuple[GraphEdge, GraphNode]]] = defaultdict(list)
        rev: dict[str, list[tuple[GraphEdge, GraphNode]]] = defaultdict(list)
        for e in self._edges:
            src = node_map.get(e.source)
            dst = node_map.get(e.target)
            if not src or not dst:
                # Defensive: ignore dangling edges
                continue
            out[src.id].append((e, dst))
            rev[dst.id].append((e, src))

        self._out = {k: tuple(v) for k, v in out.items()}
        self._in = {k: tuple(v) for k, v in rev.items()}

    @property
    def nodes(self) -> Mapping[str, GraphNode]:
        return self._nodes

    @property
    def edges(self) -> tuple[GraphEdge, ...]:
        return self._edges

    def by_kind(self, kind: NodeKind) -> tuple[GraphNode, ...] | Any:
        return self._by_kind.get(kind, ())

    def application(self) -> GraphNode:
        apps = self.by_kind(NodeKind.APPLICATION)
        if not apps:
            raise RuntimeError("ApplicationGraph has no APPLICATION node.")
        if len(apps) > 1:
            # Still fine to return the first, but this flags odd composition.
            # We explicitly raise to avoid ambiguity.
            raise RuntimeError("ApplicationGraph has multiple APPLICATION nodes.")
        return apps[0]

    def middlewares(self) -> tuple[GraphNode, ...]:
        """
        Returns middleware nodes in the order they wrap the app.
        We follow WRAPS edges starting from the application node
        while the next node is of kind MIDDLEWARE.
        """
        current = self.application()
        result: list[GraphNode] = []

        while True:
            outs = self._out.get(current.id, ())
            # Only WRAPS from current
            wraps = [dst for (e, dst) in outs if e.kind == EdgeKind.WRAPS]
            if not wraps:
                break
            # We expect linear chain; if multiple, we keep the order edges were added.
            next_node = wraps[0]
            if next_node.kind != NodeKind.MIDDLEWARE:
                break
            result.append(next_node)
            current = next_node

        return tuple(result)

    def routes(self) -> tuple[GraphNode, ...]:
        return self.by_kind(NodeKind.ROUTE)

    def route_by_path(self, path: str) -> GraphNode | None:
        """
        Exact match on the recorded route `metadata['path']`.
        This is structural introspection, not a runtime matcher.
        """
        for r in self.routes():
            if r.metadata.get("path") == path:
                return r
        return None

    def permissions_for(self, route: GraphNode) -> tuple[GraphNode, ...]:
        """
        Follow WRAPS edges that originate at the given route node
        collecting PERMISSION nodes, in the order they wrap the route.
        """
        if route.kind != NodeKind.ROUTE:
            raise TypeError("permissions_for expects a ROUTE node.")

        result: list[GraphNode] = []
        current = route

        while True:
            outs = self._out.get(current.id, ())
            wraps = [dst for (e, dst) in outs if e.kind == EdgeKind.WRAPS]
            if not wraps:
                break
            next_node = wraps[0]
            if next_node.kind != NodeKind.PERMISSION:
                break
            result.append(next_node)
            current = next_node

        return tuple(result)

    def explain(self, path: str) -> dict[str, Any]:
        """
        Structural explanation for a route:
        - middlewares (classes)
        - route metadata (path/methods)
        - permissions (classes)

        If the route is not found, raises ValueError.
        """
        r = self.route_by_path(path)
        if r is None:
            raise ValueError(f"Route not found for path: {path!r}")

        mws = [
            n.metadata.get("class", str(n.ref.__class__.__qualname__)) for n in self.middlewares()
        ]

        perms = [
            n.metadata.get("class", str(n.ref.__class__.__qualname__))
            for n in self.permissions_for(r)
        ]

        return {
            "app": {
                "debug": bool(self.application().metadata.get("debug", False)),
            },
            "middlewares": tuple(mws),
            "route": {
                "path": r.metadata.get("path"),
                "methods": r.metadata.get("methods", ()),
            },
            "permissions": tuple(perms),
        }
