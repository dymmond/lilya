#!/usr/bin/env python
# type: ignore
from __future__ import annotations

import contextlib
import math
from collections.abc import Generator, MutableMapping, Sequence
from concurrent.futures import Future
from typing import Any, Literal, cast
from urllib.parse import urljoin

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

from lilya.testclient._internal.inputs import RequestInputsDefaultValues
from lilya.testclient._internal.transport import TestClientTransport
from lilya.testclient._internal.types import ASGI2App, RequestData
from lilya.testclient._internal.utils import AsyncBackend, WrapASGI2, is_asgi3
from lilya.testclient._internal.websockets import WebSocketTestSession
from lilya.testclient.exceptions import UpgradeException
from lilya.types import ASGIApp

try:
    import httpx

except ModuleNotFoundError:  # pragma: no cover
    raise RuntimeError(
        "The lilya.testclient module requires the httpx package to be installed.\n"
        "You can install this with:\n"
        "    $ pip install httpx\n"
    ) from None

_AUTH_USER_KEY = "__lilya_testclient_authenticated_user__"


class TestClient(httpx.Client):
    """
    A robust and flexible test client designed for making HTTP requests to an ASGI application.

    This client extends `httpx.Client` to provide a seamless testing experience for ASGI
    applications, handling the complexities of ASGI lifespan events, authentication state
    management, and asynchronous backend integration (supporting both asyncio and trio).

    It includes built-in support for WebSocket testing, allowing for comprehensive integration
    testing of modern web applications.
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
        backend: Literal["asyncio", "trio"] = "asyncio",
        backend_options: dict[str, Any] | None = None,
        cookies: CookieTypes | None = None,
        headers: HeaderTypes | None = None,
        follow_redirects: bool = True,
        check_asgi_conformance: bool = True,
    ) -> None:
        """
        Initialize the TestClient with the application and configuration settings.

        Args:
            app (ASGIApp): The ASGI application instance to be tested. This can be an
                ASGI3 application or an ASGI2 application (which will be automatically wrapped).
            base_url (str, optional): The base URL to use for all requests made by the client.
                Defaults to "http://testserver".
            raise_server_exceptions (bool, optional): A flag indicating whether exceptions
                occurring within the ASGI application should be raised by the client.
                Defaults to True.
            root_path (str, optional): The root path to be used for the requests, helpful
                when testing applications mounted under a sub-path. Defaults to "".
            backend (Literal["asyncio", "trio"], optional): The asynchronous backend to
                utilize for running the application. Defaults to "asyncio".
            backend_options (dict[str, Any] | None, optional): A dictionary of options to
                configure the specific asynchronous backend. Defaults to None.
            cookies (CookieTypes | None, optional): Initial cookies to be included in all
                requests made by the client. Defaults to None.
            headers (HeaderTypes | None, optional): Initial headers to be included in all
                requests made by the client. Defaults to None.
            follow_redirects (bool, optional): A flag indicating whether the client should
                automatically follow HTTP redirects. Defaults to True.
            check_asgi_conformance (bool, optional): Whether to enforce checks for strict
                adherence to the ASGI specification. Defaults to True.
        """
        self.async_backend = AsyncBackend(backend=backend, backend_options=backend_options or {})
        if is_asgi3(app):
            asgi_app = app
        else:
            app = cast(ASGI2App, app)  # type: ignore[assignment]
            asgi_app = WrapASGI2(app)  # type: ignore[arg-type]
        self.app = asgi_app
        self.app_state: dict[str, Any] = {}
        transport = TestClientTransport(
            app=self.app,
            portal_factory=self._portal_factory,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            app_state=self.app_state,
            check_asgi_conformance=check_asgi_conformance,
        )
        if headers is None:
            headers = {}
        headers.setdefault("user-agent", "testclient")
        super().__init__(
            base_url=base_url,
            headers=headers,
            transport=transport,
            follow_redirects=follow_redirects,
            cookies=cookies,
        )

    def authenticate(self, user: Any) -> TestClient:
        """
        Sets an authenticated user in the application state.

        This helper method injects a user object into the application's state, simulating
        a logged-in user session for subsequent requests.

        Args:
            user (Any): The user object to be set as authenticated.

        Returns:
            TestClient: The instance of the client, allowing for method chaining.
        """
        self.app_state[_AUTH_USER_KEY] = user
        return self

    def logout(self) -> TestClient:
        """
        Removes the authenticated user from the application state.

        This helper method clears any user object currently stored in the application's
        state, simulating a logout action.

        Returns:
            TestClient: The instance of the client, allowing for method chaining.
        """
        self.app_state.pop(_AUTH_USER_KEY, None)
        return self

    @contextlib.contextmanager
    def authenticated(self, user: Any) -> Generator[TestClient, None, None]:
        """
        A context manager that temporarily authenticates a user for the duration of the block.

        This is useful for testing protected endpoints without permanently altering the
        client's authentication state. The previous authentication state is restored
        when the context exits.

        Args:
            user (Any): The user object to be temporarily set as authenticated.

        Yields:
            TestClient: The authenticated client instance.

        Example:
            async with AsyncTestClient(app) as client:
                with client.authenticated(user):
                    response = await client.get("/protected")
        """
        previous = self.app_state.get(_AUTH_USER_KEY)
        self.app_state[_AUTH_USER_KEY] = user
        try:
            yield self
        finally:
            if previous is None:
                self.app_state.pop(_AUTH_USER_KEY, None)
            else:
                self.app_state[_AUTH_USER_KEY] = previous

    @property
    def routes(self) -> list[Any]:
        """
        Retrieves the list of routes defined in the underlying ASGI application.

        Returns:
            list[Any]: A list of route objects if available, otherwise an empty list.
        """
        return getattr(self.app, "routes", [])

    @contextlib.contextmanager
    def _portal_factory(self) -> Generator[anyio.abc.BlockingPortal, None, None]:
        """
        A context manager that provides a blocking portal for cross-thread async execution.

        If a portal is already active (e.g., within a `with TestClient(...)` block), it yields
        that portal. Otherwise, it creates and yields a new blocking portal using the configured
        async backend.

        Yields:
            anyio.abc.BlockingPortal: The blocking portal instance.
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
        json: Any = None,
        params: QueryParamTypes | None = None,
        headers: HeaderTypes | None = None,
        cookies: CookieTypes | None = None,
        auth: (AuthTypes | httpx._client.UseClientDefault) = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        timeout: (
            TimeoutTypes | httpx._client.UseClientDefault
        ) = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, Any] | None = None,
        stream: bool = False,
    ) -> httpx.Response:
        """
        Builds and sends a network request to the ASGI application.

        This method overrides the standard `httpx.Client.request` to provide specific
        handling for the TestClient, including URL merging and stream handling.

        Args:
            method (str): The HTTP method to use (e.g., 'GET', 'POST').
            url (URLTypes): The URL to send the request to.
            content (RequestContent | None, optional): Binary content to send in the body.
                Defaults to None.
            data (RequestData | None, optional): Form data to send in the body.
                Defaults to None.
            files (RequestFiles | None, optional): Files to upload. Defaults to None.
            json (Any, optional): JSON data to send in the body. Defaults to None.
            params (QueryParamTypes | None, optional): Query parameters to include in the URL.
                Defaults to None.
            headers (HeaderTypes | None, optional): Headers to include in the request.
                Defaults to None.
            cookies (CookieTypes | None, optional): Cookies to include in the request.
                Defaults to None.
            auth (AuthTypes | httpx._client.UseClientDefault, optional): Authentication
                credentials. Defaults to httpx._client.USE_CLIENT_DEFAULT.
            follow_redirects (bool | None, optional): Whether to follow redirects.
                Defaults to None.
            timeout (TimeoutTypes | httpx._client.UseClientDefault, optional): Timeout
                configuration. Defaults to httpx._client.USE_CLIENT_DEFAULT.
            extensions (dict[str, Any] | None, optional): Extensions to include in the request.
                Defaults to None.
            stream (bool, optional): Whether to stream the response content. Defaults to False.

        Returns:
            httpx.Response: The response received from the application.
        """
        url = self._merge_url(url)
        redirect: bool | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT
        if follow_redirects is not None:
            redirect = follow_redirects

        # httpx 0.28+ deprecated per-request cookies= parameter
        # Save current cookies, merge per-request cookies, then restore after request
        if cookies is not None:
            _saved_cookies = dict(self.cookies)
            self.cookies.update(cookies)
        else:
            _saved_cookies = None

        try:
            if stream:
                return self.stream(
                    method=method,
                    url=url,
                    content=content,
                    data=data,
                    files=files,
                    json=json,
                    params=params,
                    headers=headers,
                    auth=auth,
                    timeout=timeout,
                    extensions=extensions,
                    follow_redirects=follow_redirects,
                ).__enter__()

            return super().request(
                method,
                url,
                content=content,
                data=data,
                files=files,
                json=json,
                params=params,
                headers=headers,
                auth=auth,
                follow_redirects=redirect,
                timeout=timeout,
                extensions=extensions,
            )
        finally:
            if _saved_cookies is not None:
                self.cookies.clear()
                self.cookies.update(_saved_cookies)

    def _process_request(self, method: str, url: URLTypes, **kwargs: Any) -> httpx.Response:
        """
        Internal helper to process a request with default values.

        This ensures that necessary default arguments (like empty content or data dicts)
        are populated if not provided by the caller, before delegating to the main
        request method.

        Args:
            method (str): The HTTP method.
            url (URLTypes): The request URL.
            **kwargs (Any): Additional keyword arguments for the request.

        Returns:
            httpx.Response: The resulting response object.
        """
        if not kwargs:
            kwargs = RequestInputsDefaultValues  # type: ignore
        else:
            remaining_kwargs = {
                k: v for k, v in RequestInputsDefaultValues.items() if k not in kwargs
            }
            kwargs.update(remaining_kwargs)  # type: ignore

        return self.request(method=method, url=url, **kwargs)  # type: ignore

    def get(self, url: URLTypes, **kwargs: Any) -> httpx.Response:
        """
        Sends a GET request.

        Args:
            url (URLTypes): The URL to send the request to.
            **kwargs (Any): Additional arguments passed to `request`.

        Returns:
            httpx.Response: The response from the server.
        """
        return self._process_request(method="GET", url=url, **kwargs)  # type: ignore

    def head(self, url: URLTypes, **kwargs: Any) -> httpx.Response:
        """
        Sends a HEAD request.

        Args:
            url (URLTypes): The URL to send the request to.
            **kwargs (Any): Additional arguments passed to `request`.

        Returns:
            httpx.Response: The response from the server.
        """
        return self._process_request(method="HEAD", url=url, **kwargs)  # type: ignore

    def post(self, url: URLTypes, **kwargs: Any) -> httpx.Response:
        """
        Sends a POST request.

        Args:
            url (URLTypes): The URL to send the request to.
            **kwargs (Any): Additional arguments passed to `request`.

        Returns:
            httpx.Response: The response from the server.
        """
        return self._process_request(method="POST", url=url, **kwargs)  # type: ignore

    def put(self, url: URLTypes, **kwargs: Any) -> httpx.Response:
        """
        Sends a PUT request.

        Args:
            url (URLTypes): The URL to send the request to.
            **kwargs (Any): Additional arguments passed to `request`.

        Returns:
            httpx.Response: The response from the server.
        """
        return self._process_request(method="PUT", url=url, **kwargs)  # type: ignore

    def patch(self, url: URLTypes, **kwargs: Any) -> httpx.Response:
        """
        Sends a PATCH request.

        Args:
            url (URLTypes): The URL to send the request to.
            **kwargs (Any): Additional arguments passed to `request`.

        Returns:
            httpx.Response: The response from the server.
        """
        return self._process_request(method="PATCH", url=url, **kwargs)  # type: ignore

    def delete(self, url: URLTypes, **kwargs: Any) -> httpx.Response:
        """
        Sends a DELETE request.

        Args:
            url (URLTypes): The URL to send the request to.
            **kwargs (Any): Additional arguments passed to `request`.

        Returns:
            httpx.Response: The response from the server.
        """
        return self._process_request(method="DELETE", url=url, **kwargs)  # type: ignore

    def options(self, url: URLTypes, **kwargs: Any) -> httpx.Response:
        """
        Sends an OPTIONS request.

        Args:
            url (URLTypes): The URL to send the request to.
            **kwargs (Any): Additional arguments passed to `request`.

        Returns:
            httpx.Response: The response from the server.
        """
        return self._process_request(method="OPTIONS", url=url, **kwargs)  # type: ignore

    def websocket_connect(
        self,
        url: str,
        subprotocols: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> WebSocketTestSession:
        """
        Initiates a WebSocket connection to the application.

        This method constructs the necessary headers for a WebSocket upgrade request and
        establishes a session if the upgrade is successful.

        Args:
            url (str): The URL path for the WebSocket connection (relative to base_url).
            subprotocols (Sequence[str] | None, optional): A list of WebSocket subprotocols
                to request. Defaults to None.
            **kwargs (Any): Additional arguments passed to the request.

        Returns:
            WebSocketTestSession: An active WebSocket session object.

        Raises:
            RuntimeError: If the server does not upgrade the connection to a WebSocket.
        """
        url = urljoin("ws://testserver", url)
        headers = self._prepare_websocket_headers(subprotocols, **kwargs)
        kwargs["headers"] = headers
        try:
            super().request("GET", url, **kwargs)
        except UpgradeException as exc:
            session = exc.session
        else:
            raise RuntimeError("Expected WebSocket upgrade")

        return session

    def _prepare_websocket_headers(
        self,
        subprotocols: Sequence[str] | None = None,
        **kwargs: dict[str, Any],
    ) -> dict[str, str]:
        """
        Prepares the HTTP headers required for a WebSocket handshake.

        Args:
            subprotocols (Sequence[str] | None, optional): The subprotocols to include in
                the handshake. Defaults to None.
            **kwargs (dict[str, Any]): Additional keyword arguments containing existing headers.

        Returns:
            dict[str, str]: The dictionary of headers including WebSocket specific ones.
        """
        headers = kwargs.get("headers", {})
        headers.setdefault("connection", "upgrade")
        headers.setdefault("sec-websocket-key", "testserver==")
        headers.setdefault("sec-websocket-version", "13")
        if subprotocols is not None:
            headers.setdefault("sec-websocket-protocol", ", ".join(subprotocols))
        kwargs["headers"] = headers
        return headers

    def __enter__(self) -> TestClient:
        """
        Context manager entry point for synchronous usage.

        Starts a blocking portal, sets up communication streams, and triggers the
        lifespan startup event of the ASGI application.

        Returns:
            TestClient: The initialized client instance.
        """
        with contextlib.ExitStack() as stack:
            self.portal = portal = stack.enter_context(
                anyio.from_thread.start_blocking_portal(**self.async_backend)
            )

            @stack.callback
            def reset_portal() -> None:
                self.portal = None

            send1: ObjectSendStream[MutableMapping[str, Any] | None]
            receive1: ObjectReceiveStream[MutableMapping[str, Any] | None]
            send2: ObjectSendStream[MutableMapping[str, Any]]
            receive2: ObjectReceiveStream[MutableMapping[str, Any]]
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

    async def __aenter__(self) -> TestClient:
        """
        Context manager entry point for asynchronous usage.

        Creates a task group, sets up communication streams, and triggers the
        lifespan startup event of the ASGI application asynchronously.

        Returns:
            TestClient: The initialized client instance.
        """
        self._tg = anyio.create_task_group()
        await self._tg.__aenter__()

        send1, receive1 = anyio.create_memory_object_stream(math.inf)
        send2, receive2 = anyio.create_memory_object_stream(math.inf)
        self.stream_send = StapledObjectStream(send1, receive1)
        self.stream_receive = StapledObjectStream(send2, receive2)

        self.task = await self._tg.start(self._lifespan_runner)
        await self.wait_startup()
        return self

    def __exit__(self, *args: Any) -> None:
        """
        Context manager exit point for synchronous usage.

        Closes the exit stack, which triggers the lifespan shutdown event and
        cleans up the blocking portal.

        Args:
            *args (Any): Exception arguments if an exception occurred.
        """
        self.exit_stack.close()

    async def __aexit__(self, *args: Any) -> None:
        """
        Context manager exit point for asynchronous usage.

        Waits for the lifespan shutdown event and closes the task group.

        Args:
            *args (Any): Exception arguments if an exception occurred.
        """
        await self.wait_shutdown()
        await self._tg.__aexit__(None, None, None)

    async def _lifespan_runner(
        self, *, task_status: anyio.abc.TaskStatus = anyio.TASK_STATUS_IGNORED
    ) -> None:
        """
        Runs the lifespan protocol.

        Args:
            task_status (anyio.abc.TaskStatus, optional): Status object to signal when
                the lifespan has started. Defaults to anyio.TASK_STATUS_IGNORED.
        """
        task_status.started()
        await self.lifespan()

    async def lifespan(self) -> None:
        """
        Manages the ASGI lifespan protocol loop.

        This method sends the lifespan context to the app and handles the receive/send
        channels for lifespan events.
        """
        scope = {"type": "lifespan", "state": self.app_state}
        try:
            await self.app(scope, self.stream_receive.receive, self.stream_send.send)
        finally:
            with contextlib.suppress(anyio.ClosedResourceError):
                await self.stream_send.send(None)

    async def wait_startup(self) -> None:
        """
        Waits for the ASGI application to complete its startup sequence.

        Sends the 'lifespan.startup' event and awaits the confirmation message.

        Raises:
            AssertionError: If the received message type is not a valid startup response.
        """
        await self.stream_receive.send({"type": "lifespan.startup"})

        async def receive() -> Any:
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
        Waits for the ASGI application to complete its shutdown sequence.

        Sends the 'lifespan.shutdown' event and awaits the confirmation message.
        Handles both sync (portal) and async (task group) modes.

        Raises:
            AssertionError: If the received message type is not a valid shutdown response.
        """

        async def receive() -> Any:
            message = await self.stream_send.receive()
            if message is None:
                self.task.result()
            return message

        async_mode = hasattr(self, "_tg")

        if async_mode:
            await self.stream_receive.send({"type": "lifespan.shutdown"})
            message = await receive()
            assert message["type"] in (
                "lifespan.shutdown.complete",
                "lifespan.shutdown.failed",
            )
            if message["type"] == "lifespan.shutdown.failed":
                await receive()
        else:
            async with self.stream_send:
                await self.stream_receive.send({"type": "lifespan.shutdown"})
                message = await receive()
                assert message["type"] in (
                    "lifespan.shutdown.complete",
                    "lifespan.shutdown.failed",
                )
                if message["type"] == "lifespan.shutdown.failed":
                    await receive()
