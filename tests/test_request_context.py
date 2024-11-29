import pytest  # type: ignore

from lilya.context import request_context
from lilya.exceptions import ImproperlyConfigured
from lilya.middleware import DefineMiddleware
from lilya.middleware.request_context import RequestContextMiddleware
from lilya.routing import Path
from lilya.testclient import create_client


async def show_request_context() -> dict[str, str]:
    return {"url": str(request_context.url)}


def test_global_context():
    with create_client(
        routes=[Path("/show", show_request_context)],
        middleware=[DefineMiddleware(RequestContextMiddleware)],
    ) as client:
        response = client.get("/show")

        assert response.status_code == 200
        assert response.json() == {"url": "http://testserver/show"}


def test_raises_ImproperlyConfigured():
    with create_client(
        routes=[Path("/show", show_request_context)],
    ):
        with pytest.raises(ImproperlyConfigured):
            breakpoint()
            url = request_context.url  # noqa
