import pytest

from lilya._internal._scopes import scope_manager
from lilya.dependencies import Depends, Provide, PureScope
from lilya.enums import Scope

pytestmark = pytest.mark.anyio


class DummyRequest:
    """Simple dummy request object to simulate Lilya's Request for Provide."""

    def __init__(self):
        self._cleanups = []
        self.query_params = {}
        self.data_called = False

    async def data(self):
        self.data_called = True
        return {}

    def add_cleanup(self, fn):
        self._cleanups.append(fn)


async def test_provide_request_scope_runs_every_time():
    called = 0

    async def make_resource():
        nonlocal called
        called += 1
        return f"instance-{called}"

    p = Provide(make_resource, scope=Scope.REQUEST)

    req = DummyRequest()
    res1 = await p.resolve(req, {})
    res2 = await p.resolve(req, {})

    # REQUEST scope -> runs every time
    assert res1 != res2
    assert called == 2


async def test_provide_app_scope_reuses_instance():
    called = 0

    async def make_resource():
        nonlocal called
        called += 1
        return f"app-instance-{called}"

    p = Provide(make_resource, scope=Scope.APP)

    req = DummyRequest()
    res1 = await p.resolve(req, {})
    res2 = await p.resolve(req, {})
    # APP scope -> cached via scope_manager
    assert res1 == res2
    assert called == 1


async def test_provide_global_scope_reuses_across_calls():
    called = 0

    async def make_resource():
        nonlocal called
        called += 1
        return f"global-instance-{called}"

    p = Provide(make_resource, scope=Scope.GLOBAL)

    req1, req2 = DummyRequest(), DummyRequest()
    res1 = await p.resolve(req1, {})
    res2 = await p.resolve(req2, {})

    # GLOBAL scope -> cached globally
    assert res1 == res2
    assert called == 1


async def test_depends_request_scope_runs_every_time():
    called = 0

    async def get_value():
        nonlocal called
        called += 1
        return f"dep-{called}"

    dep = Depends(get_value, scope=Scope.REQUEST)

    async with PureScope() as scope:
        v1 = await dep.resolve(scope=scope)
        v2 = await dep.resolve(scope=scope)

        assert v1 != v2
        assert called == 2


async def test_depends_app_scope_reuses_instance():
    called = 0

    async def get_value():
        nonlocal called
        called += 1
        return f"app-{called}"

    dep = Depends(get_value, scope=Scope.APP)

    async with PureScope() as scope:
        v1 = await dep.resolve(scope=scope)
        v2 = await dep.resolve(scope=scope)
        assert v1 == v2
        assert called == 1


async def test_depends_global_scope_reuses_across_instances():
    called = 0

    async def get_value():
        nonlocal called
        called += 1
        return f"global-{called}"

    dep = Depends(get_value, scope=Scope.GLOBAL)

    async with PureScope() as scope1, PureScope() as scope2:
        v1 = await dep.resolve(scope=scope1)
        v2 = await dep.resolve(scope=scope2)

        assert v1 == v2
        assert called == 1


async def test_scope_manager_clearing_resets_instances():
    called = 0

    async def make_resource():
        nonlocal called
        called += 1
        return f"r-{called}"

    dep = Provide(make_resource, scope=Scope.APP)
    req = DummyRequest()

    first = await dep.resolve(req, {})
    second = await dep.resolve(req, {})

    assert first == second
    assert called == 1

    # Clear scope cache manually
    scope_manager.clear(Scope.APP)

    third = await dep.resolve(req, {})

    assert third != first
    assert called == 2
