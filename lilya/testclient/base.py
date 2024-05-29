from __future__ import annotations

import contextlib
import io
import math
import typing
from concurrent.futures import Future
from types import GeneratorType
from urllib.parse import unquote, urljoin

import anyio
import anyio.from_thread
import httpx
from anyio.abc import ObjectReceiveStream, ObjectSendStream
from anyio.streams.stapled import StapledObjectStream
from httpx._types import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    QueryParamTypes,
    RequestContent,
    RequestFiles,
    TimeoutTypes,
    URLTypes,
)

from lilya.testclient.exceptions import UpgradeException
from lilya.testclient.types import ASGI2App, ASGI3App, PortalFactoryType, RequestData
from lilya.testclient.utils import AsyncBackend, WrapASGI2, is_asgi3
from lilya.testclient.websockets import WebSocketTestSession
from lilya.types import ASGIApp, Message

try:
    import httpx

except ModuleNotFoundError:  # pragma: no cover
    raise RuntimeError(
        "The lilya.testclient module requires the httpx package to be installed.\n"
        "You can install this with:\n"
        "    $ pip install httpx\n"
    ) from None


class _TestClientTransport(httpx.BaseTransport):
    def __init__(
        self,
        app: ASGI3App,
        portal_factory: PortalFactoryType,
        raise_server_exceptions: bool = True,
        root_path: str = "",
        *,
        app_state: dict[str, typing.Any],
    ) -> None:
        """
        Initialize the _TestClientTransport.

        Args:
            app: The ASGI3App instance.
            portal_factory: The PortalFactoryType instance.
            raise_server_exceptions: Whether to raise server exceptions.
            root_path: The root path.
            app_state: The application state.
        """
        self.app = app
        self.raise_server_exceptions = raise_server_exceptions
        self.root_path = root_path
        self.portal_factory = portal_factory
        self.app_state = app_state

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """
        Handle the HTTP request.

        Args:
            request: The httpx.Request instance.

        Returns:
            The httpx.Response instance.
        """
        scheme = request.url.scheme
        netloc = request.url.netloc.decode(encoding="ascii")
        path = request.url.path
        raw_path = request.url.raw_path
        query = request.url.query.decode(encoding="ascii")

        default_port = {"http": 80, "ws": 80, "https": 443, "wss": 443}[scheme]

        if ":" in netloc:
            host, port_string = netloc.split(":", 1)
            port = int(port_string)
        else:
            host = netloc
            port = default_port

        # Include the 'host' header.
        if "host" in request.headers:
            headers: list[tuple[bytes, bytes]] = []
        elif port == default_port:  # pragma: no cover
            headers = [(b"host", host.encode())]
        else:  # pragma: no cover
            headers = [(b"host", (f"{host}:{port}").encode())]

        # Include other request headers.
        headers += [
            (key.lower().encode(), value.encode()) for key, value in request.headers.multi_items()
        ]

        scope: dict[str, typing.Any]

        if scheme in {"ws", "wss"}:
            subprotocol = request.headers.get("sec-websocket-protocol", None)
            if subprotocol is None:
                subprotocols: typing.Sequence[str] = []
            else:
                subprotocols = [value.strip() for value in subprotocol.split(",")]
            scope = {
                "type": "websocket",
                "path": unquote(path),
                "raw_path": raw_path,
                "root_path": self.root_path,
                "scheme": scheme,
                "query_string": query.encode(),
                "headers": headers,
                "client": None,
                "server": [host, port],
                "subprotocols": subprotocols,
                "state": self.app_state.copy(),
                "extensions": {"websocket.http.response": {}},
            }
            session = WebSocketTestSession(self.app, scope, self.portal_factory)
            raise UpgradeException(session)

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": request.method,
            "path": unquote(path),
            "raw_path": raw_path,
            "root_path": self.root_path,
            "scheme": scheme,
            "query_string": query.encode(),
            "headers": headers,
            "client": None,
            "server": [host, port],
            "extensions": {"http.response.debug": {}},
            "state": self.app_state.copy(),
        }

        request_complete = False
        response_started = False
        response_complete: anyio.Event
        raw_kwargs: dict[str, typing.Any] = {"stream": io.BytesIO()}
        template = None
        context = None

        async def receive() -> Message:
            nonlocal request_complete

            if request_complete:
                if not response_complete.is_set():
                    await response_complete.wait()
                return {"type": "http.disconnect"}

            body = request.read()
            if isinstance(body, str):  # type: ignore
                body_bytes: bytes = body.encode("utf-8")  # type: ignore
            elif body is None:
                body_bytes = b""  # pragma: no cover
            elif isinstance(body, GeneratorType):  # type: ignore
                try:  # type: ignore
                    chunk = body.send(None)
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    return {"type": "http.request", "body": chunk, "more_body": True}
                except StopIteration:  # pragma: no cover
                    request_complete = True
                    return {"type": "http.request", "body": b""}
            else:
                body_bytes = body

            request_complete = True
            return {"type": "http.request", "body": body_bytes}

        async def send(message: Message) -> None:
            nonlocal raw_kwargs, response_started, template, context

            if message["type"] == "http.response.start":
                assert not response_started, 'Received multiple "http.response.start" messages.'
                raw_kwargs["status_code"] = message["status"]
                raw_kwargs["headers"] = list(message.get("headers", []))
                response_started = True
            elif message["type"] == "http.response.body":
                assert (
                    response_started
                ), 'Received "http.response.body" without "http.response.start".'
                assert (
                    not response_complete.is_set()
                ), 'Received "http.response.body" after response completed.'
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if request.method != "HEAD":
                    raw_kwargs["stream"].write(body)
                if not more_body:
                    raw_kwargs["stream"].seek(0)
                    response_complete.set()
            elif message["type"] == "http.response.debug":
                template = message["info"]["template"]
                context = message["info"]["context"]

        try:
            with self.portal_factory() as portal:
                response_complete = portal.call(anyio.Event)
                portal.call(self.app, scope, receive, send)
        except BaseException as exc:
            if self.raise_server_exceptions:
                raise exc

        if self.raise_server_exceptions:
            assert response_started, "TestClient did not receive any response."
        elif not response_started:
            raw_kwargs = {
                "status_code": 500,
                "headers": [],
                "stream": io.BytesIO(),
            }

        raw_kwargs["stream"] = httpx.ByteStream(raw_kwargs["stream"].read())

        response = httpx.Response(**raw_kwargs, request=request)
        if template is not None:
            response.template = template  # type: ignore[attr-defined]
            response.context = context  # type: ignore[attr-defined]
        return response


class TestClient(httpx.Client):
    """
    A test client for making HTTP requests to an ASGI application.

    Args:
        app (ASGIApp): The ASGI application to test.
        base_url (str, optional): The base URL for the requests. Defaults to "http://testserver".
        raise_server_exceptions (bool, optional): Whether to raise exceptions for server errors. Defaults to True.
        root_path (str, optional): The root path for the requests. Defaults to "".
        backend (typing.Literal["asyncio", "trio"], optional): The async backend to use. Defaults to "asyncio".
        backend_options (dict[str, typing.Any] | None, optional): Options for the async backend. Defaults to None.
        cookies (httpx._types.CookieTypes | None, optional): Cookies to include in the requests. Defaults to None.
        headers (dict[str, str] | None, optional): Headers to include in the requests. Defaults to None.
        follow_redirects (bool, optional): Whether to follow redirects. Defaults to True.
    """

    __test__ = False
    task: Future[None]
    portal: anyio.abc.BlockingPortal | None = None

    def __init__(
        self,
        app: ASGIApp,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: typing.Literal["asyncio", "trio"] = "asyncio",
        backend_options: dict[str, typing.Any] | None = None,
        cookies: CookieTypes | None = None,
        headers: HeaderTypes | None = None,
        follow_redirects: bool = True,
    ) -> None:
        self.async_backend = AsyncBackend(backend=backend, backend_options=backend_options or {})
        if is_asgi3(app):
            asgi_app = app
        else:
            app = typing.cast(ASGI2App, app)  # type: ignore[assignment]
            asgi_app = WrapASGI2(app)  # type: ignore[arg-type]
        self.app = asgi_app
        self.app_state: dict[str, typing.Any] = {}
        transport = _TestClientTransport(
            self.app,
            portal_factory=self._portal_factory,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            app_state=self.app_state,
        )
        if headers is None:
            headers = {}
        headers.setdefault("user-agent", "testclient")
        super().__init__(
            app=self.app,
            base_url=base_url,
            headers=headers,
            transport=transport,
            follow_redirects=follow_redirects,
            cookies=cookies,
        )

    @contextlib.contextmanager
    def _portal_factory(self) -> typing.Generator[anyio.abc.BlockingPortal, None, None]:
        """
        Context manager that creates a blocking portal for handling async tasks.

        Yields:
            anyio.abc.BlockingPortal: The blocking portal.
        """
        if self.portal is not None:
            yield self.portal
        else:
            with anyio.from_thread.start_blocking_portal(**self.async_backend) as portal:
                yield portal

    def request(
        self,
        method: str,
        url: URLTypes,
        *,
        content: RequestContent | None = None,
        data: RequestData | None = None,
        files: RequestFiles | None = None,
        json: typing.Any = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: AuthTypes | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        timeout: TimeoutTypes | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        """
        Sends an HTTP request.

        Args:
            method (str): The HTTP method.
            url (URLTypes): The URL to send the request to.
            content (RequestContent | None, optional): The request content. Defaults to None.
            data (RequestData | None, optional): The request data. Defaults to None.
            files (RequestFiles | None, optional): The request files. Defaults to None.
            json (typing.Any, optional): The request JSON. Defaults to None.
            params (QueryParamTypes | None, optional): The request query parameters. Defaults to None.
            headers (HeaderTypes | None, optional): The request headers. Defaults to None.
            cookies (CookieTypes | None, optional): The request cookies. Defaults to None.
            auth (AuthTypes | httpx._client.UseClientDefault, optional): The request authentication. Defaults to httpx._client.USE_CLIENT_DEFAULT.
            follow_redirects (bool | None, optional): Whether to follow redirects. Defaults to None.
            timeout (TimeoutTypes | httpx._client.UseClientDefault, optional): The request timeout. Defaults to httpx._client.USE_CLIENT_DEFAULT.
            extensions (dict[str, typing.Any] | None, optional): The request extensions. Defaults to None.

        Returns:
            httpx.Response: The HTTP response.
        """
        url = self._merge_url(url)
        redirect: bool | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT
        if follow_redirects is not None:
            redirect = follow_redirects

        return super().request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    # Implement other HTTP methods (get, post, put, patch, delete) with the same docstring and functionality as request()

    def websocket_connect(
        self,
        url: str,
        subprotocols: typing.Sequence[str] | None = None,
        **kwargs: typing.Any,
    ) -> WebSocketTestSession:
        """
        Establishes a WebSocket connection.

        Args:
            url (str): The WebSocket URL.
            subprotocols (typing.Sequence[str] | None, optional): The WebSocket subprotocols. Defaults to None.
            **kwargs (typing.Any): Additional keyword arguments.

        Returns:
            WebSocketTestSession: The WebSocket session.
        """
        url = urljoin("ws://testserver", url)
        headers = kwargs.get("headers", {})
        headers.setdefault("connection", "upgrade")
        headers.setdefault("sec-websocket-key", "testserver==")
        headers.setdefault("sec-websocket-version", "13")
        if subprotocols is not None:
            headers.setdefault("sec-websocket-protocol", ", ".join(subprotocols))
        kwargs["headers"] = headers
        try:
            super().request("GET", url, **kwargs)
        except UpgradeException as exc:
            session = exc.session
        else:
            raise RuntimeError("Expected WebSocket upgrade")

        return session

    def __enter__(self) -> TestClient:
        """
        Enters the context manager.

        Returns:
            TestClient: The test client.
        """
        with contextlib.ExitStack() as stack:
            self.portal = portal = stack.enter_context(
                anyio.from_thread.start_blocking_portal(**self.async_backend)
            )

            @stack.callback
            def reset_portal() -> None:
                self.portal = None

            send1: ObjectSendStream[typing.MutableMapping[str, typing.Any] | None]
            receive1: ObjectReceiveStream[typing.MutableMapping[str, typing.Any] | None]
            send2: ObjectSendStream[typing.MutableMapping[str, typing.Any]]
            receive2: ObjectReceiveStream[typing.MutableMapping[str, typing.Any]]
            send1, receive1 = anyio.create_memory_object_stream(math.inf)
            send2, receive2 = anyio.create_memory_object_stream(math.inf)
            self.stream_send = StapledObjectStream(send1, receive1)
            self.stream_receive = StapledObjectStream(send2, receive2)
            self.task = portal.start_task_soon(self.lifespan)
            portal.call(self.wait_startup)

            @stack.callback
            def wait_shutdown() -> None:
                portal.call(self.wait_shutdown)

            self.exit_stack = stack.pop_all()

        return self

    def __exit__(self, *args: typing.Any) -> None:
        """
        Exits the context manager.
        """
        self.exit_stack.close()

    async def lifespan(self) -> None:
        """
        Handles the lifespan of the ASGI application.
        """
        scope = {"type": "lifespan", "state": self.app_state}
        try:
            await self.app(scope, self.stream_receive.receive, self.stream_send.send)
        finally:
            await self.stream_send.send(None)

    async def wait_startup(self) -> None:
        """
        Waits for the ASGI application to start up.
        """
        await self.stream_receive.send({"type": "lifespan.startup"})

        async def receive() -> typing.Any:
            message = await self.stream_send.receive()
            if message is None:
                self.task.result()
            return message

        message = await receive()
        assert message["type"] in (
            "lifespan.startup.complete",
            "lifespan.startup.failed",
        )
        if message["type"] == "lifespan.startup.failed":
            await receive()

    async def wait_shutdown(self) -> None:
        """
        Waits for the ASGI application to shut down.
        """

        async def receive() -> typing.Any:
            message = await self.stream_send.receive()
            if message is None:
                self.task.result()
            return message

        async with self.stream_send:
            await self.stream_receive.send({"type": "lifespan.shutdown"})
            message = await receive()
            assert message["type"] in (
                "lifespan.shutdown.complete",
                "lifespan.shutdown.failed",
            )
            if message["type"] == "lifespan.shutdown.failed":
                await receive()
