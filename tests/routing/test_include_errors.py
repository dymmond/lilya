import pytest

from lilya.exceptions import ImproperlyConfigured
from lilya.routing import Include, Path


async def home() -> None:
    """"""


path = Path("/", handler=home)


route_patterns = [Path("/", handler=home)]


def test_raise_error_namespace_and_routes():
    with pytest.raises(AssertionError):
        Include("/", namespace="test", routes=[path])


@pytest.mark.parametrize("arg", [path, 2, Path])
def test_raise_error_namespace(arg):
    with pytest.raises(ImproperlyConfigured):
        Include("/", namespace=arg)


@pytest.mark.parametrize("arg", [path, 2, Path])
def test_raise_error_pattern(arg):
    with pytest.raises(ImproperlyConfigured):
        Include("/", pattern=arg, routes=[path])


def test_raise_error_pattern_and_routes():
    with pytest.raises(ImproperlyConfigured):
        Include("/", pattern="test", routes=[path])


def test_namespace_include_routes():
    include = Include("/", namespace="tests.routing.test_include_errors")

    assert len(include.routes) == 1
