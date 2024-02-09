import pytest

from lilya._internal._urls import include
from lilya.exceptions import ImproperlyConfigured
from lilya.routing import Path


async def home() -> None:
    """"""


route_patterns = [Path(path="/home", handler=home)]


def test_default_include_router_patterns():
    include_routes = include("tests.test_urls_include")

    assert len(include_routes) == 1


my_urls = [Path(path="/home", handler=home)]


def test_pattern_include():
    include_routes = include("tests.test_urls_include", pattern="my_urls")

    assert len(include_routes) == 1


def test_raises_improperly_configured_for_arg():
    with pytest.raises(ImproperlyConfigured):
        include(1, pattern="my_urls")


def test_raises_assertation_error_for_patterns():
    with pytest.raises(AssertionError):
        include("tests.test_urls_include", pattern="my_url_routes")


my_url_routes_tuple = Path(path="/home", handler=home)


def test_raises_assertation_error_for_patterns_not_list():
    with pytest.raises(AssertionError):
        include("tests.test_urls_include", pattern="my_url_routes_tuple")
