"""
Dependency Injection benchmarks for Lilya's DI system.

Measures DI resolution overhead across different scenarios:
- Single dependency resolution
- Nested dependency chains
- Wide dependency resolution (multiple parameters)
- Scoped dependency lifecycle (APP vs REQUEST)
- Dependency caching behavior
"""

import pytest

from lilya.dependencies import Provide
from lilya.enums import Scope


class DummyRequest:
    """Minimal request object for DI benchmarking."""

    def __init__(self):
        self._cleanups = []
        self.query_params = {}

    async def data(self):
        return {}

    def add_cleanup(self, fn):
        self._cleanups.append(fn)


@pytest.mark.benchmark
def test_di_single_dependency(benchmark):
    """Benchmark single dependency resolution with one Inject parameter."""

    async def simple_factory():
        return {"value": 42}

    provide = Provide(simple_factory, scope=Scope.REQUEST)
    req = DummyRequest()

    async def resolve_once():
        return await provide.resolve(req, {})

    result = benchmark.pedantic(
        lambda: pytest.importorskip("anyio").run(resolve_once),
        rounds=100,
        iterations=10,
    )

    assert result == {"value": 42}


@pytest.mark.benchmark
def test_di_nested_dependency_chain(benchmark):
    """Benchmark nested dependency chain (3 levels: A → B → C)."""

    async def dep_c():
        return "C"

    async def dep_b(c: str):
        return f"B-{c}"

    async def dep_a(b: str):
        return f"A-{b}"

    # Build dependency map: A depends on B, B depends on C
    deps_map = {
        "c": Provide(dep_c, scope=Scope.REQUEST),
        "b": Provide(dep_b, scope=Scope.REQUEST),
    }

    provide_a = Provide(dep_a, scope=Scope.REQUEST)
    req = DummyRequest()

    async def resolve_chain():
        # Manually resolve chain: C first, then B, then A
        c_val = await deps_map["c"].resolve(req, deps_map)
        deps_map_with_c = {**deps_map, "c": c_val}

        b_val = await deps_map["b"].resolve(req, deps_map_with_c)
        deps_map_with_b = {**deps_map_with_c, "b": b_val}

        return await provide_a.resolve(req, deps_map_with_b)

    result = benchmark.pedantic(
        lambda: pytest.importorskip("anyio").run(resolve_chain),
        rounds=100,
        iterations=10,
    )

    assert result == "A-B-C"


@pytest.mark.benchmark
def test_di_wide_dependency_resolution(benchmark):
    """Benchmark handler with 5 Inject parameters (wide dependency resolution)."""

    async def dep_1():
        return 1

    async def dep_2():
        return 2

    async def dep_3():
        return 3

    async def dep_4():
        return 4

    async def dep_5():
        return 5

    deps_map = {
        "d1": Provide(dep_1, scope=Scope.REQUEST),
        "d2": Provide(dep_2, scope=Scope.REQUEST),
        "d3": Provide(dep_3, scope=Scope.REQUEST),
        "d4": Provide(dep_4, scope=Scope.REQUEST),
        "d5": Provide(dep_5, scope=Scope.REQUEST),
    }

    req = DummyRequest()

    async def resolve_all_wide():
        results = {}
        for name, provide in deps_map.items():
            results[name] = await provide.resolve(req, deps_map)
        return results

    result = benchmark.pedantic(
        lambda: pytest.importorskip("anyio").run(resolve_all_wide),
        rounds=100,
        iterations=10,
    )

    assert result == {"d1": 1, "d2": 2, "d3": 3, "d4": 4, "d5": 5}


@pytest.mark.benchmark
def test_di_app_scope_vs_request_scope(benchmark):
    """Benchmark scoped dependency lifecycle (APP scope vs REQUEST scope)."""

    async def counting_factory():
        # Return a unique value each time called
        import random

        return random.random()

    # APP scope should cache, REQUEST scope should not
    provide_app = Provide(counting_factory, scope=Scope.APP)
    req = DummyRequest()

    async def resolve_app_scoped():
        # Resolve twice - APP scope should reuse same instance
        first = await provide_app.resolve(req, {})
        second = await provide_app.resolve(req, {})
        # APP scope: both should be identical
        return first, second

    first, second = benchmark.pedantic(
        lambda: pytest.importorskip("anyio").run(resolve_app_scoped),
        rounds=100,
        iterations=5,
    )

    # APP scope: both resolves return the same cached value
    assert first == second


@pytest.mark.benchmark
def test_di_dependency_caching(benchmark):
    """Benchmark dependency resolution with caching (same dependency used twice)."""

    async def expensive_factory():
        # Return unique mutable object each time called
        import random

        return {"data": "expensive", "random": random.random()}

    # use_cache=True should cache within single resolution call
    provide_cached = Provide(expensive_factory, use_cache=True, scope=Scope.REQUEST)
    req = DummyRequest()

    async def resolve_with_cache():
        # First resolution
        result1 = await provide_cached.resolve(req, {})

        # Second resolution - should use cache (same object)
        result2 = await provide_cached.resolve(req, {})

        return result1, result2

    r1, r2 = benchmark.pedantic(
        lambda: pytest.importorskip("anyio").run(resolve_with_cache),
        rounds=100,
        iterations=5,
    )

    # Cache enabled: both resolves return the same cached object
    assert r1 is r2
    assert r1 == r2


@pytest.mark.benchmark
def test_di_class_instantiation(benchmark):
    """Benchmark DI with class instantiation (common pattern)."""

    class Service:
        def __init__(self):
            self.name = "TestService"

        def get_name(self):
            return self.name

    provide = Provide(Service, scope=Scope.REQUEST)
    req = DummyRequest()

    async def resolve_class():
        instance = await provide.resolve(req, {})
        return instance.get_name()

    result = benchmark.pedantic(
        lambda: pytest.importorskip("anyio").run(resolve_class),
        rounds=100,
        iterations=10,
    )

    assert result == "TestService"


@pytest.mark.benchmark
def test_di_with_provided_args(benchmark):
    """Benchmark DI with pre-provided arguments (direct call optimization path)."""

    def factory_with_args(a: int, b: int, c: int = 10):
        return a + b + c

    # When args/kwargs are provided, DI takes optimized direct-call path
    provide = Provide(factory_with_args, 5, 15, c=20, scope=Scope.REQUEST)
    req = DummyRequest()

    async def resolve_with_args():
        return await provide.resolve(req, {})

    result = benchmark.pedantic(
        lambda: pytest.importorskip("anyio").run(resolve_with_args),
        rounds=100,
        iterations=10,
    )

    assert result == 40  # 5 + 15 + 20
