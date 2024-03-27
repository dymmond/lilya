from __future__ import annotations

import ipaddress
from datetime import datetime
from typing import Callable, Iterator

import pytest

from lilya import transformers
from lilya.requests import Request
from lilya.responses import JSONResponse, make_response
from lilya.routing import Path, Router
from lilya.testclient import TestClient
from lilya.transformers import Transformer, register_path_transformer

TestClientFactory = Callable[..., TestClient]


class IPTransformer(Transformer[str]):
    regex = r"((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$"

    def transform(self, value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        return ipaddress.ip_address(value)

    def normalise(self, value: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
        return str(value)


class DateTimeTransformer(Transformer[datetime]):
    regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(.[0-9]+)?"

    def transform(self, value: str) -> datetime:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")

    def normalise(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S")


@pytest.fixture(scope="module", autouse=True)
def refresh_transformer_types() -> Iterator[None]:
    transformer_types = transformers.TRANSFORMER_TYPES.copy()
    yield
    transformers.TRANSFORMER_TYPES = transformer_types


@pytest.fixture(scope="function")
def app() -> Router:
    register_path_transformer("datetime", DateTimeTransformer)
    register_path_transformer("ip", IPTransformer)

    def datetime_transformer(request: Request) -> JSONResponse:
        param = request.path_params["param"]
        assert isinstance(param, datetime)
        return JSONResponse({"datetime": param.strftime("%Y-%m-%dT%H:%M:%S")})

    def ip_transformer(request: Request) -> JSONResponse:
        param = request.path_params["param"]
        assert isinstance(param, (ipaddress.IPv4Address, ipaddress.IPv6Address))
        return JSONResponse({"ip": str(param)})

    return Router(
        routes=[
            Path(
                "/datetime/{param:datetime}",
                handler=datetime_transformer,
                name="datetime-transformer",
            ),
            Path(
                "/ip/{param:ip}",
                handler=ip_transformer,
                name="ip-transformer",
            ),
        ]
    )


def test_datetime_transformer(test_client_factory: TestClientFactory, app: Router) -> None:
    client = test_client_factory(app)
    response = client.get("/datetime/2020-01-01T00:00:00")
    assert response.json() == {"datetime": "2020-01-01T00:00:00"}

    assert (
        app.path_for("datetime-transformer", param=datetime(1996, 1, 22, 23, 0, 0))
        == "/datetime/1996-01-22T23:00:00"
    )


def test_ip_transformer(test_client_factory: TestClientFactory, app: Router) -> None:
    client = test_client_factory(app)
    response = client.get("/ip/192.168.0.1")
    assert response.json() == {"ip": "192.168.0.1"}

    assert (
        app.path_for("ip-transformer", param=ipaddress.ip_address("192.168.0.1"))
        == "/ip/192.168.0.1"
    )


@pytest.mark.parametrize("param, status_code", [("1", 201), ("1", 404)])
def test_default_int_transformer(
    test_client_factory: TestClientFactory, param: str, status_code: int
) -> None:
    def int_transformer(request: Request) -> JSONResponse:
        param = request.path_params["param"]
        assert isinstance(param, int)
        return make_response({"int": param}, status_code=status_code)

    app = Router(routes=[Path("/{param:int}", handler=int_transformer)])

    client = test_client_factory(app)
    response = client.get(f"/{param}")
    assert response.status_code == status_code
