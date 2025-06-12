from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast

from lilya._internal._module_loading import import_string
from lilya.exceptions import HTTPException
from lilya.requests import Request
from lilya.types import Scope

if TYPE_CHECKING:
    from lilya.apps import Lilya

try:
    from a2wsgi.wsgi import WSGIMiddleware as A2WSGIMiddleware  # noqa
    from a2wsgi.wsgi import WSGIResponder
    from a2wsgi.wsgi_typing import WSGIApp
    from a2wsgi.asgi_typing import HTTPScope, Receive, Send
except ModuleNotFoundError:
    raise RuntimeError(
        "You need to install the package `a2wsgi` to be able to use this middleware. "
        "Simply run `pip install a2wsgi`."
    ) from None


class BufferedWSGIResponder(WSGIResponder):
    """
    Like a2wsgi's WSGIResponder, but buffers *all* ASGI messages
    until the WSGI app has fully run (or errored), so we can
    either flush them to the client or drop them and handle the error in Lilya.
    """

    def __init__(
        self,
        wsgi_app: WSGIApp,
        executor: ThreadPoolExecutor,
        send_queue_size: int,
        scope: HTTPScope,
        receive: Receive,
        send: Send,
        app: Lilya,
    ):
        super().__init__(wsgi_app, executor, send_queue_size)
        self._buffer: list[Any] = []
        self._scope = scope
        self._receive = receive
        self._send = send
        self._asgi_app = app

    def send(self, message: Any) -> None:
        self._buffer.append(message)

    async def __call__(self, scope: HTTPScope, receive: Receive, send: Send) -> None:
        """
        Run the WSGI app to completion, then either:
          - flush the buffer (normal path), or
          - handle the exception in Lilya (error path).
        """
        await super().__call__(scope, receive, send)
        start = next(
            (msg for msg in self._buffer if msg["type"] == "http.response.start"),
            None,
        )
        body_bytes = b"".join(m["body"] for m in self._buffer if m["type"] == "http.response.body")

        if start and start["status"] >= 400:
            detail = body_bytes.decode("utf-8", errors="ignore")
            exc = HTTPException(status_code=start["status"], detail=detail)
            handler = self._asgi_app.exception_handlers.get(HTTPException)
            if handler:
                request = Request(scope, receive=receive)  # type: ignore
                response = await handler(request, exc)
                await response(scope, receive, send)
                return

        for msg in self._buffer:
            await send(msg)


class WSGIMiddleware(A2WSGIMiddleware):
    def __init__(
        self,
        app: WSGIApp | str,
        workers: int = 10,
        send_queue_size: int = 10,
        redirect_exceptions: bool = False,
    ) -> None:
        if isinstance(app, str):
            app = cast(WSGIApp, import_string(app))
        super().__init__(app, workers, send_queue_size)
        self.redirect_exceptions = redirect_exceptions

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        app: Lilya = scope["app"]

        if not self.redirect_exceptions:
            await super().__call__(scope, receive, send)  # type: ignore
        else:
            responder = BufferedWSGIResponder(
                self.app,
                self.executor,
                self.send_queue_size,
                cast(HTTPScope, scope),
                receive,
                send,
                app=app,
            )
            return await responder(cast(HTTPScope, scope), receive, send)
