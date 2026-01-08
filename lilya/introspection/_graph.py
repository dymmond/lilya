from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping

from ._types import GraphEdge, GraphNode, NodeKind


class ApplicationGraph:
    __slots__ = ("_nodes", "_edges", "_by_kind")

    def __init__(self, *, nodes: Iterable[GraphNode], edges: Iterable[GraphEdge]) -> None:
        node_map = {node.id: node for node in nodes}

        self._nodes: Mapping[str, GraphNode] = node_map
        self._edges: tuple[GraphEdge, ...] = tuple(edges)

        by_kind: dict[NodeKind, list[GraphNode]] = defaultdict(list)

        for node in node_map.values():
            by_kind[node.kind].append(node)

        self._by_kind = dict(by_kind)

    @property
    def nodes(self) -> Mapping[str, GraphNode]:
        return self._nodes

    @property
    def edges(self) -> tuple[GraphEdge, ...]:
        return self._edges

    def by_kind(self, kind: NodeKind) -> tuple[GraphNode, ...]:
        return tuple(self._by_kind.get(kind, []))
