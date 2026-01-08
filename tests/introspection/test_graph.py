from lilya.apps import Lilya
from lilya.introspection import NodeKind
from lilya.protocols.permissions import PermissionProtocol
from lilya.routing import Path


def test_graph_contains_application_node(test_client_factory):
    app = Lilya()
    graph = app.graph
    apps = graph.by_kind(NodeKind.APPLICATION)

    assert len(apps) == 1
    assert apps[0].ref is app


class MiddlewareA: ...


class MiddlewareB: ...


def test_middleware_order_is_preserved(test_client_factory):
    app = Lilya(middleware=[MiddlewareA, MiddlewareB])
    graph = app.graph

    names = [node.metadata["class"] for node in graph.by_kind(NodeKind.MIDDLEWARE)]
    assert names == ["MiddlewareA", "MiddlewareB"]


class Allow(PermissionProtocol):
    async def __call__(self, scope, receive, send):
        return await super().__call__(scope, receive, send)


class Deny(PermissionProtocol):
    async def __call__(self, scope, receive, send):
        return await super().__call__(scope, receive, send)


async def handler():
    return "Hello"


def test_route_permissions_chain(test_client_factory):
    app = Lilya(
        routes=[
            Path(
                "/users/{id}",
                handler,
                permissions=[Allow, Deny],
            )
        ]
    )

    graph = app.graph
    route = graph.route_by_path("/users/{id}")

    perms = graph.permissions_for(route)
    classes = [p.metadata["class"] for p in perms]

    assert classes == ["Allow", "Deny"]


def test_explain_returns_structural_data(test_client_factory):
    app = Lilya(middleware=[MiddlewareA], routes=[Path("/ping", handler)])

    info = app.graph.explain("/ping")

    assert info["route"]["path"] == "/ping"
    assert info["middlewares"] == ("MiddlewareA",)
