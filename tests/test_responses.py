import datetime as dt
import os
import sys
import time
import typing
from asyncio import Queue
from http.cookies import SimpleCookie

import anyio
import pytest

from lilya import status
from lilya.apps import Lilya
from lilya.background import Task
from lilya.encoders import Encoder
from lilya.middleware import DefineMiddleware
from lilya.middleware.sessions import SessionMiddleware
from lilya.requests import Request
from lilya.responses import (
    Error,
    FileResponse,
    JSONResponse,
    Ok,
    RedirectResponse,
    Response,
    StreamingResponse,
    redirect,
)
from lilya.routing import Path
from lilya.testclient import TestClient


class Foo: ...


# check that encoders are saved as instances on responses
class FooEncoder(Encoder):
    __type__ = Foo

    def serialize(self, obj: Foo) -> bool:
        return True

    def encode(
        self,
        structure: type[Foo],
        obj,
    ):
        return True


def test_text_response(test_client_factory):
    async def app(scope, receive, send):
        response = Response("hello, world", media_type="text/plain", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "hello, world"


def test_async_text_response(test_client_factory):
    async def create_hello_world():
        return "hello, world"

    async def app(scope, receive, send):
        response = Response(create_hello_world(), media_type="text/plain", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "hello, world"


def test_ok_response(test_client_factory):
    async def app(scope, receive, send):
        response = Ok("hello, world", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.json() == "hello, world"


def test_error_response(test_client_factory):
    async def app(scope, receive, send):
        response = Error("hello, world", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.text == "hello, world"


def test_bytes_response(test_client_factory):
    async def app(scope, receive, send):
        response = Response(b"xxxxx", media_type="image/png", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.content == b"xxxxx"


def test_json_none_response(test_client_factory):
    async def app(scope, receive, send):
        response = JSONResponse(None, encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.json() is None
    assert response.content == b"null"


def test_redirect_response(test_client_factory):
    async def app(scope, receive, send):
        if scope["path"] == "/":
            response = Response("hello, world", media_type="text/plain", encoders=[FooEncoder])
        else:
            response = RedirectResponse("/", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/redirect")
    assert response.text == "hello, world"
    assert response.url == "http://testserver/"


def test_redirect_func(test_client_factory):
    async def app(scope, receive, send):
        if scope["path"] == "/":
            response = Response("hello, world", media_type="text/plain", encoders=[FooEncoder])
        else:
            response = redirect("/", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/redirect")
    assert response.text == "hello, world"
    assert response.url == "http://testserver/"


def test_streaming_response(test_client_factory):
    filled_by_bg_task = ""

    async def app(scope, receive, send):
        async def numbers(minimum, maximum):
            for i in range(minimum, maximum + 1):
                yield str(i)
                if i != maximum:
                    yield ", "
                await anyio.sleep(0)

        async def numbers_for_cleanup(start=1, stop=5):
            nonlocal filled_by_bg_task
            async for thing in numbers(start, stop):
                filled_by_bg_task = filled_by_bg_task + thing

        cleanup_task = Task(numbers_for_cleanup, start=6, stop=9)
        generator = numbers(1, 5)
        response = StreamingResponse(
            generator, media_type="text/plain", background=cleanup_task, encoders=[FooEncoder]
        )
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    assert filled_by_bg_task == ""
    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "1, 2, 3, 4, 5"
    assert filled_by_bg_task == "6, 7, 8, 9"


def test_streaming_response_custom_iterator(test_client_factory):
    async def app(scope, receive, send):
        class CustomAsyncIterator:
            def __init__(self):
                self._called = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._called == 5:
                    raise StopAsyncIteration()
                self._called += 1
                return str(self._called)

        response = StreamingResponse(
            CustomAsyncIterator(), media_type="text/plain", encoders=[FooEncoder]
        )
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "12345"


def test_streaming_response_custom_iterable(test_client_factory):
    async def app(scope, receive, send):
        class CustomAsyncIterable:
            async def __aiter__(self):
                for i in range(5):
                    yield str(i + 1)

        response = StreamingResponse(
            CustomAsyncIterable(), media_type="text/plain", encoders=[FooEncoder]
        )
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "12345"


def test_sync_streaming_response(test_client_factory):
    async def app(scope, receive, send):
        def numbers(minimum, maximum):
            for i in range(minimum, maximum + 1):
                yield str(i)
                if i != maximum:
                    yield ", "

        generator = numbers(1, 5)
        response = StreamingResponse(generator, media_type="text/plain", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "1, 2, 3, 4, 5"


def test_response_headers(test_client_factory):
    async def app(scope, receive, send):
        headers = {"x-header-1": "123", "x-header-2": "456"}
        response = Response("hello, world", media_type="text/plain", headers=headers)
        response.headers["x-header-2"] = "789"
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.headers["x-header-1"] == "123"
    assert response.headers["x-header-2"] == "789"


def test_response_phrase(test_client_factory):
    app = Response(status_code=204)
    client = test_client_factory(app)
    response = client.get("/")
    assert response.reason_phrase == "No Content"

    app = Response(b"", status_code=123)
    client = test_client_factory(app)
    response = client.get("/")
    assert response.reason_phrase == ""


def test_file_response(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "xyz")
    content = b"<file content>" * 1000
    with open(path, "wb") as file:
        file.write(content)

    filled_by_bg_task = ""

    async def numbers(minimum, maximum):
        for i in range(minimum, maximum + 1):
            yield str(i)
            if i != maximum:
                yield ", "
            await anyio.sleep(0)

    async def numbers_for_cleanup(start=1, stop=5):
        nonlocal filled_by_bg_task
        async for thing in numbers(start, stop):
            filled_by_bg_task = filled_by_bg_task + thing

    cleanup_task = Task(numbers_for_cleanup, start=6, stop=9)

    async def app(scope, receive, send):
        response = FileResponse(
            path=path, filename="example.png", background=cleanup_task, encoders=[FooEncoder]
        )
        assert isinstance(response.encoders[0], FooEncoder)
        await response(scope, receive, send)

    assert filled_by_bg_task == ""
    client = test_client_factory(app)
    response = client.get("/")
    expected_disposition = 'attachment; filename="example.png"'
    assert response.status_code == status.HTTP_200_OK
    assert response.content == content
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"] == expected_disposition
    assert "content-length" in response.headers
    assert "last-modified" in response.headers
    assert "etag" in response.headers
    assert filled_by_bg_task == "6, 7, 8, 9"


@pytest.mark.parametrize(
    "extensions,result",
    [
        ({"http.response.pathsend": {}}, "http.response.pathsend"),
        ({"http.response.zerocopysend": {}}, "http.response.zerocopysend"),
    ],
)
async def test_file_response_optimizations(tmpdir, extensions, result, anyio_backend):
    if sys.version_info < (3, 10) and anyio_backend == "trio":
        pytest.skip("Not supported combination of trio, python  < 3.10 and asyncio.Queue")
    path = os.path.join(tmpdir, "xyz")
    content = b"<file content>" * 1000
    with open(path, "wb") as file:
        file.write(content)

    fresponse = FileResponse(path=path, filename="example.png")
    fresponse.chunk_size = 10
    responses = Queue()
    await fresponse({"extensions": extensions, "type": "response"}, None, responses.put)
    response1 = await responses.get()
    response2 = await responses.get()

    expected_disposition = 'attachment; filename="example.png"'
    assert response1["headers"]["content-type"] == "image/png"
    assert response1["headers"]["content-disposition"] == expected_disposition
    assert response2["type"] == result
    if result == "http.response.pathsend":
        assert response2["path"] == path
    else:
        assert response2["count"] == fresponse.chunk_size
        assert response2["file"] > 0
        assert response2["more_body"]
        while response2["more_body"]:
            response2 = await responses.get()
        assert not response2["more_body"]


def test_file_response_with_directory_raises_error(tmpdir, test_client_factory):
    app = FileResponse(path=tmpdir, filename="example.png")
    client = test_client_factory(app)
    with pytest.raises(RuntimeError) as exc_info:
        client.get("/")
    assert "is not a file" in str(exc_info.value)


def test_file_response_with_missing_file_raises_error(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "404.txt")
    app = FileResponse(path=path, filename="404.txt")
    client = test_client_factory(app)
    with pytest.raises(RuntimeError) as exc_info:
        client.get("/")
    assert "does not exist" in str(exc_info.value)


def test_file_response_with_chinese_filename(tmpdir, test_client_factory):
    content = b"file content"
    filename = "你好.txt"  # probably "Hello.txt" in Chinese
    path = os.path.join(tmpdir, filename)
    with open(path, "wb") as f:
        f.write(content)
    app = FileResponse(path=path, filename=filename)
    client = test_client_factory(app)
    response = client.get("/")
    expected_disposition = "attachment; filename*=utf-8''%E4%BD%A0%E5%A5%BD.txt"
    assert response.status_code == status.HTTP_200_OK
    assert response.content == content
    assert response.headers["content-disposition"] == expected_disposition


def test_file_response_with_inline_disposition(tmpdir, test_client_factory):
    content = b"file content"
    filename = "hello.txt"
    path = os.path.join(tmpdir, filename)
    with open(path, "wb") as f:
        f.write(content)
    app = FileResponse(path=path, filename=filename, content_disposition_type="inline")
    client = test_client_factory(app)
    response = client.get("/")
    expected_disposition = 'inline; filename="hello.txt"'
    assert response.status_code == status.HTTP_200_OK
    assert response.content == content
    assert response.headers["content-disposition"] == expected_disposition


def test_set_cookie(test_client_factory, monkeypatch):
    # Mock time used as a reference for `Expires` by stdlib `SimpleCookie`.
    mocked_now = dt.datetime(2037, 1, 22, 12, 0, 0, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(time, "time", lambda: mocked_now.timestamp())

    async def app(scope, receive, send):
        response = Response("Hello, world!", media_type="text/plain", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        response.set_cookie(
            "mycookie",
            "myvalue",
            max_age=10,
            expires=10,
            path="/",
            domain="localhost",
            secure=True,
            httponly=True,
            samesite="none",
        )
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "Hello, world!"
    assert (
        response.headers["set-cookie"]
        == "mycookie=myvalue; Domain=localhost; expires=Thu, 22 Jan 2037 12:00:10 GMT; "
        "HttpOnly; Max-Age=10; Path=/; SameSite=none; Secure"
    )


def test_set_cookie_multiple(test_client_factory, monkeypatch):
    # Mock time used as a reference for `Expires` by stdlib `SimpleCookie`.
    mocked_now = dt.datetime(2037, 1, 22, 12, 0, 0, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(time, "time", lambda: mocked_now.timestamp())

    async def app(scope, receive, send):
        response = Response("Hello, world!", media_type="text/plain", encoders=[FooEncoder])
        assert isinstance(response.encoders[0], FooEncoder)
        response.set_cookie(
            "access_cookie",
            "myvalue",
            max_age=10,
            expires=10,
            path="/",
            domain="localhost",
            secure=True,
            httponly=True,
            samesite="none",
        )
        response.set_cookie(
            "refresh_cookie",
            "myvalue",
            max_age=10,
            expires=10,
            path="/",
            domain="localhost",
            secure=True,
            httponly=True,
            samesite="none",
        )
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "Hello, world!"

    assert (
        response.headers["set-cookie"]
        == "access_cookie=myvalue; Domain=localhost; expires=Thu, 22 Jan 2037 12:00:10 GMT; HttpOnly; Max-Age=10; Path=/; SameSite=none; Secure, refresh_cookie=myvalue; Domain=localhost; expires=Thu, 22 Jan 2037 12:00:10 GMT; HttpOnly; Max-Age=10; Path=/; SameSite=none; Secure"
    )


def test_set_cookie_multiple_with_session(test_client_factory, monkeypatch):
    # Mock time used as a reference for `Expires` by stdlib `SimpleCookie`.
    mocked_now = dt.datetime(2037, 1, 22, 12, 0, 0, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(time, "time", lambda: mocked_now.timestamp())

    async def home():
        response = Response("Hello, world!", media_type="text/plain", encoders=[FooEncoder])
        response.set_cookie(
            "access_cookie",
            "myvalue",
            max_age=10,
            expires=10,
            path="/",
            domain="localhost",
            secure=True,
            httponly=True,
            samesite="none",
        )
        response.set_cookie(
            "refresh_cookie",
            "myvalue",
            max_age=10,
            expires=10,
            path="/",
            domain="localhost",
            secure=True,
            httponly=True,
            samesite="none",
        )
        return response

    async def update_session(request: Request) -> JSONResponse:
        data = await request.json()
        request.session.update(data)
        return JSONResponse({"session": request.session})

    lilya_app = Lilya(
        routes=[
            Path("/session", update_session, methods=["POST"]),
            Path("/", home),
        ],
        middleware=[
            DefineMiddleware(SessionMiddleware, secret_key="your-secret-key"),
        ],
    )

    client = test_client_factory(lilya_app)

    response = client.post("/session", json={"some": "data"})
    assert response.json() == {"session": {"some": "data"}}

    response = client.get("/")
    assert response.text == "Hello, world!"

    assert (
        response.headers["set-cookie"]
        == "access_cookie=myvalue; Domain=localhost; expires=Thu, 22 Jan 2037 12:00:10 GMT; HttpOnly; Max-Age=10; Path=/; SameSite=none; Secure, refresh_cookie=myvalue; Domain=localhost; expires=Thu, 22 Jan 2037 12:00:10 GMT; HttpOnly; Max-Age=10; Path=/; SameSite=none; Secure"
    )


@pytest.mark.parametrize(
    "expires",
    [
        pytest.param(dt.datetime(2037, 1, 22, 12, 0, 10, tzinfo=dt.timezone.utc), id="datetime"),
        pytest.param("Thu, 22 Jan 2037 12:00:10 GMT", id="str"),
        pytest.param(10, id="int"),
    ],
)
def test_expires_on_set_cookie(test_client_factory, monkeypatch, expires):
    # Mock time used as a reference for `Expires` by stdlib `SimpleCookie`.
    mocked_now = dt.datetime(2037, 1, 22, 12, 0, 0, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(time, "time", lambda: mocked_now.timestamp())

    async def app(scope, receive, send):
        response = Response("Hello, world!", media_type="text/plain")
        response.set_cookie("mycookie", "myvalue", expires=expires)
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    cookie: SimpleCookie[typing.Any] = SimpleCookie(response.headers.get("set-cookie"))
    assert cookie["mycookie"]["expires"] == "Thu, 22 Jan 2037 12:00:10 GMT"


def test_delete_cookie(test_client_factory):
    async def app(scope, receive, send):
        request = Request(scope, receive)
        response = Response("Hello, world!", media_type="text/plain")
        if request.cookies.get("mycookie"):
            response.delete_cookie("mycookie")
        else:
            response.set_cookie("mycookie", "myvalue")
        await response(scope, receive, send)

    client = test_client_factory(app)
    response = client.get("/")
    assert response.cookies["mycookie"]
    response = client.get("/")
    assert not response.cookies.get("mycookie")


def test_populate_headers(test_client_factory):
    app = Response(content="hi", headers={}, media_type="text/html")
    client = test_client_factory(app)
    response = client.get("/")
    assert response.text == "hi"
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.headers["content-length"] == "2"


def test_head_method(test_client_factory):
    app = Response("hello, world", media_type="text/plain")
    client = test_client_factory(app)
    response = client.head("/")
    assert response.text == ""


def test_empty_response(test_client_factory):
    app = Response()
    client: TestClient = test_client_factory(app)
    response = client.get("/")
    assert response.content == b""
    assert response.headers["content-length"] == "0"
    assert "content-type" not in response.headers


def test_empty_204_response(test_client_factory):
    app = Response(status_code=204)
    client: TestClient = test_client_factory(app)
    response = client.get("/")
    assert "content-length" not in response.headers


def test_non_empty_response(test_client_factory):
    app = Response(content="hi")
    client: TestClient = test_client_factory(app)
    response = client.get("/")
    assert response.headers["content-length"] == "2"


def test_file_response_known_size(tmpdir, test_client_factory):
    path = os.path.join(tmpdir, "xyz")
    content = b"<file content>" * 1000
    with open(path, "wb") as file:
        file.write(content)

    app = FileResponse(path=path, filename="example.png")
    client: TestClient = test_client_factory(app)
    response = client.get("/")
    assert response.headers["content-length"] == str(len(content))


def test_streaming_response_unknown_size(test_client_factory):
    app = StreamingResponse(content=iter(["hello", "world"]))
    client: TestClient = test_client_factory(app)
    response = client.get("/")
    assert "content-length" not in response.headers


def test_streaming_response_known_size(test_client_factory):
    app = StreamingResponse(content=iter(["hello", "world"]), headers={"content-length": "10"})
    client: TestClient = test_client_factory(app)
    response = client.get("/")
    assert response.headers["content-length"] == "10"


@pytest.mark.anyio
async def test_streaming_response_stops_if_receiving_http_disconnect():
    streamed = 0

    disconnected = anyio.Event()

    async def receive_disconnect():
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        nonlocal streamed
        if message["type"] == "http.response.body":
            streamed += len(message.get("body", b""))
            # Simulate disconnection after download has started
            if streamed >= 16:
                disconnected.set()

    async def stream_indefinitely():
        while True:
            # Need a sleep for the event loop to switch to another task
            await anyio.sleep(0)
            yield b"chunk "

    response = StreamingResponse(content=stream_indefinitely())

    with anyio.move_on_after(1) as cancel_scope:
        await response({}, receive_disconnect, send)
    assert not cancel_scope.cancel_called, "Content streaming should stop itself."
