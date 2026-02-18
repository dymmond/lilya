"""
Routing dispatch benchmarks for Lilya.

Benchmarks measure routing dispatch performance: path matching, parameter extraction,
and handler resolution. These benchmarks test the compiled path matching system,
not HTTP overhead.
"""

from __future__ import annotations

import pytest

from lilya.enums import Match
from lilya.responses import JSONResponse, PlainText
from lilya.routing import Include, Path, Router


# Handler functions for benchmarks
async def simple_handler():
    """Static handler for simple route."""
    return PlainText("OK")


async def single_param_handler(user_id: str):
    """Handler with single path parameter."""
    return JSONResponse({"user_id": user_id})


async def multi_param_handler(org: str, repo: str, issue_id: int):
    """Handler with multiple path parameters."""
    return JSONResponse({"org": org, "repo": repo, "issue_id": issue_id})


async def nested_handler(resource: str):
    """Handler for nested Include scenario."""
    return JSONResponse({"resource": resource})


# Test fixtures for different routing scenarios


@pytest.fixture
def simple_router():
    """Router with single static path."""
    return Router(routes=[Path("/users", handler=simple_handler)])


@pytest.fixture
def single_param_router():
    """Router with single parameterized path."""
    return Router(routes=[Path("/users/{user_id}", handler=single_param_handler)])


@pytest.fixture
def multi_param_router():
    """Router with multiple path parameters."""
    return Router(
        routes=[
            Path(
                "/orgs/{org}/repos/{repo}/issues/{issue_id:int}",
                handler=multi_param_handler,
            )
        ]
    )


@pytest.fixture
def nested_include_router():
    """Router with 3 levels of nested Include."""
    return Router(
        routes=[
            Include(
                "/api",
                routes=[
                    Include(
                        "/v1",
                        routes=[
                            Include(
                                "/resources",
                                routes=[
                                    Path("/{resource}", handler=nested_handler),
                                ],
                            )
                        ],
                    )
                ],
            )
        ]
    )


@pytest.fixture
def large_router():
    """Router with 100 routes — worst-case match (last route)."""
    routes = []
    # Create 99 static routes
    for i in range(99):
        routes.append(Path(f"/route{i:03d}", handler=simple_handler))
    # Last route is the one we'll match
    routes.append(Path("/route099", handler=simple_handler))
    return Router(routes=routes)


# Benchmark tests


@pytest.mark.benchmark
def test_routing_simple_static_path(benchmark, simple_router):
    """Benchmark simple static path matching: /users"""

    def dispatch():
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/users",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "asgi": {"version": "3.0"},
            "state": {},
        }
        # Search through routes to find match
        for route in simple_router.routes:
            match, child_scope = route.search(scope)
            if match != Match.NONE:
                return match, child_scope
        return Match.NONE, {}

    # Benchmark the dispatch operation
    benchmark(dispatch)


@pytest.mark.benchmark
def test_routing_single_parameter(benchmark, single_param_router):
    """Benchmark path with single parameter: /users/{user_id}"""

    def dispatch():
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/users/abc123",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "asgi": {"version": "3.0"},
            "state": {},
        }
        # Search through routes to find match
        for route in single_param_router.routes:
            match, child_scope = route.search(scope)
            if match != Match.NONE:
                return match, child_scope
        return Match.NONE, {}

    # Benchmark the dispatch operation
    benchmark(dispatch)


@pytest.mark.benchmark
def test_routing_multiple_parameters(benchmark, multi_param_router):
    """Benchmark path with multiple parameters: /orgs/{org}/repos/{repo}/issues/{issue_id}"""

    def dispatch():
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/orgs/dymmond/repos/lilya/issues/42",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "asgi": {"version": "3.0"},
            "state": {},
        }
        # Search through routes to find match
        for route in multi_param_router.routes:
            match, child_scope = route.search(scope)
            if match != Match.NONE:
                return match, child_scope
        return Match.NONE, {}

    # Benchmark the dispatch operation
    benchmark(dispatch)


@pytest.mark.benchmark
def test_routing_nested_includes(benchmark, nested_include_router):
    """Benchmark nested Include resolution (3 levels deep): /api/v1/resources/{resource}"""

    def dispatch():
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/resources/users",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "asgi": {"version": "3.0"},
            "state": {},
        }
        # Search through routes (Include nesting will be resolved)
        for route in nested_include_router.routes:
            match, child_scope = route.search(scope)
            if match != Match.NONE:
                return match, child_scope
        return Match.NONE, {}

    # Benchmark the dispatch operation
    benchmark(dispatch)


@pytest.mark.benchmark
def test_routing_worst_case_100_routes(benchmark, large_router):
    """Benchmark worst-case scenario: 100 routes, match the last route."""

    def dispatch():
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/route099",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "asgi": {"version": "3.0"},
            "state": {},
        }
        # Search through all routes (worst case: match last one)
        for route in large_router.routes:
            match, child_scope = route.search(scope)
            if match != Match.NONE:
                return match, child_scope
        return Match.NONE, {}

    # Benchmark the dispatch operation
    benchmark(dispatch)
