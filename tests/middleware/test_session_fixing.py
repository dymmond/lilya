from collections.abc import Callable
from typing import Any

from lilya.apps import Lilya
from lilya.middleware import DefineMiddleware
from lilya.middleware.clientip import ClientIPScopeOnlyMiddleware
from lilya.middleware.session_fixing import SessionFixingMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path
from lilya.testclient import TestClient

TestClientFactory = Callable[..., TestClient]


def view_session(request: Request) -> JSONResponse:
    return JSONResponse({"session": request.session})


async def update_session(request: Request) -> JSONResponse:
    data = await request.json()
    request.session.update(data)
    return JSONResponse({"session": request.session})


async def clear_session(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"session": request.session})


def notify_fn(old_ip: str | None, new_ip: str, old_session: dict, new_session: dict) -> None:
    if old_ip is None:
        print(f'New session for ip: "{new_ip}".')
    else:
        print(f'Replace session for ip: "{old_ip}". Has new ip "{new_ip}".')


def test_session_fixing(test_client_factory: TestClientFactory, capsys: Any) -> None:
    app = Lilya(
        routes=[
            Path("/view_session", handler=view_session),
            Path("/update_session", handler=update_session, methods=["POST"]),
            Path("/clear_session", handler=clear_session, methods=["POST"]),
        ],
        middleware=[
            DefineMiddleware(ClientIPScopeOnlyMiddleware, trusted_proxies=["unix"]),
            DefineMiddleware(SessionMiddleware, secret_key="example"),
            DefineMiddleware(SessionFixingMiddleware, notify_fn=notify_fn),
        ],
    )

    client = test_client_factory(app)
    # clear
    capsys.readouterr()
    response = client.get(
        "/view_session", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"}
    )
    assert response.json() == {"session": {"real-clientip": "8.193.38.177"}}
    captured = capsys.readouterr()
    assert captured.out == 'New session for ip: "8.193.38.177".\n'

    response = client.post(
        "/update_session",
        json={"some": "data"},
        headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"},
    )
    assert response.json() == {"session": {"some": "data", "real-clientip": "8.193.38.177"}}
    captured = capsys.readouterr()
    assert captured.out == ""

    response = client.get(
        "/view_session", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"}
    )
    assert response.json() == {"session": {"some": "data", "real-clientip": "8.193.38.177"}}
    captured = capsys.readouterr()
    assert captured.out == ""

    response = client.get(
        "/view_session", headers={"forwarded": "for=8.193.38.1,for=8.193.38.177"}
    )
    assert response.json() == {"session": {"real-clientip": "8.193.38.1"}}
    captured = capsys.readouterr()
    assert captured.out == 'Replace session for ip: "8.193.38.177". Has new ip "8.193.38.1".\n'

    response = client.get(
        "/view_session", headers={"forwarded": "for=8.193.38.177,for=8.193.38.176"}
    )
    assert response.json() == {"session": {"real-clientip": "8.193.38.177"}}
