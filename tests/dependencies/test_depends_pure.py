import asyncio

import pytest

from lilya.dependencies import Depends, inject

pytestmark = pytest.mark.anyio


def run(coro):
    return asyncio.run(coro)


def make_counter():
    state = {"count": 0}

    def increment():
        state["count"] += 1
        return state["count"]

    increment.__name__ = "increment"
    return increment, state


def make_async_counter():
    state = {"count": 0}

    async def increment():
        state["count"] += 1
        return state["count"]

    increment.__name__ = "increment"
    return increment, state


def make_sync_gen(flag):
    def generator():
        try:
            yield 99
        finally:
            flag["closed"] = True

    generator.__name__ = "generator"
    return generator


def make_async_gen(flag):
    async def agenerator():
        try:
            yield 123
        finally:
            flag["closed"] = True

    agenerator.__name__ = "agenerator"
    return agenerator


def test_depends_on_constant_value():
    dep = Depends(42)

    result = run(dep.resolve())
    assert result == 42


def test_depends_factory_on_constant_value():
    dependency = Depends({"answer": 42})

    result = run(dependency.resolve())
    assert result == {"answer": 42}


def test_depends_sync_callable_with_dependencies_map_value_and_callable():
    def add(a: int, b: int) -> int:
        return a + b

    def make_a():
        return 3

    dependency = Depends(add)
    result = run(dependency.resolve(dependencies_map={"a": make_a, "b": 2}))

    assert result == 5


def test_depends_async_callable_with_dependencies_map():
    async def mul(a: int, b: int) -> int:
        return a * b

    def provide_a():
        return 4

    dependency = Depends(mul)
    result = run(dependency.resolve(dependencies_map={"a": provide_a, "b": 3}))
    assert result == 12


def test_nested_depends_three_levels():
    def one() -> int:
        return 1

    def two(x=Depends(one)) -> int:
        return x + 1

    def three(y=Depends(two)) -> int:
        return y + 1

    dependency = Depends(three)
    result = run(dependency.resolve())

    assert result == 3


def test_use_cache_true_caches_per_instance():
    func, state = make_counter()
    dependency = Depends(func, use_cache=True)

    value1 = run(dependency.resolve())
    value2 = run(dependency.resolve())

    assert value1 == 1
    assert value2 == 1
    assert state["count"] == 1  # called only once


def test_use_cache_false_does_not_cache():
    func, state = make_counter()
    dependency = Depends(func, use_cache=False)

    value1 = run(dependency.resolve())
    value2 = run(dependency.resolve())

    assert value1 == 1
    assert value2 == 2
    assert state["count"] == 2


def test_depends_factory_lru_returns_same_instance_for_same_signature():
    def source():
        return "x"

    dependency1 = Depends(source, use_cache=True)
    dependency2 = Depends(source, use_cache=True)

    assert dependency1 is dependency2


def test_class_dependency_called_directly_when_provided_args_kwargs():
    class Service:
        def __init__(self, x: int) -> None:
            self.x = x

    dependency = Depends(Service, x=5)
    result = run(dependency.resolve())

    assert isinstance(result, Service)
    assert result.x == 5


def test_varargs_and_kwargs_are_skipped():
    def func(a: int, *args, **kwargs) -> int:
        # Ensure only 'a' is relevant; *args/**kwargs are ignored by resolution
        return a

    dependency = Depends(func)
    out = run(dependency.resolve(dependencies_map={"a": 7}))
    assert out == 7


def test_default_is_used_when_unmapped():
    def func(a: int = 10) -> int:
        return a

    dependency = Depends(func)
    out = run(dependency.resolve())
    assert out == 10


def test_unresolvable_parameter_raises():
    def func(a):
        return a

    dependency = Depends(func)
    with pytest.raises(RuntimeError) as exc:
        run(dependency.resolve())

    msg = str(exc.value)

    assert "Could not resolve parameter 'a'" in msg


def test_provided_kwargs_trigger_direct_call():
    def greet(name: str, suffix: str) -> str:
        return f"hello {name}{suffix}"

    dependency = Depends(greet, name="lilya", suffix="!")
    out = run(dependency.resolve())

    assert out == "hello lilya!"


def test_provided_args_trigger_direct_call():
    def add(a: int, b: int) -> int:
        return a + b

    dependency = Depends(add, 2, 3)
    out = run(dependency.resolve())

    assert out == 5


def test_depends_repr_includes_dependency_name():
    def do_stuff():
        return 1

    dependency = Depends(do_stuff)

    assert "Depends(do_stuff)" in repr(dependency)


async def test_scope_keeps_session_open_until_exit():
    class FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    def get_db():
        session = FakeSession()
        try:
            yield session
        finally:
            session.close()

    @inject
    async def get_conn(conn=Depends(get_db)):
        return conn

    sess = await get_conn()
    assert isinstance(sess, FakeSession)


def test_inject_resolves_sync_function_parameter():
    def provide_value():
        return 7

    @inject
    def compute(x=Depends(provide_value)):
        return x * 3

    assert compute() == 21


def test_inject_does_not_override_explicit_argument():
    def provide_value():
        return 1

    @inject
    def add_one(x=Depends(provide_value)):
        return x + 1

    assert add_one(10) == 11


def test_inject_supports_overrides():
    def base():
        return 2

    def override():
        return 5

    @inject(overrides={base: override})
    def calc(x=Depends(base)):
        return x * 2

    assert calc() == 10  # override applied


def test_inject_raises_when_missing_required_param_without_default():
    @inject
    def f(x):  # no default, no Depends
        return x

    with pytest.raises(RuntimeError):
        f()
