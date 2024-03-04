from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Awaitable, Callable, cast

from lilya._internal._encoders import json_encoder
from lilya._internal._exception_handlers import wrap_app_handling_exceptions
from lilya.compat import is_async_callable
from lilya.concurrency import run_in_threadpool
from lilya.context import Context
from lilya.enums import SignatureDefault
from lilya.requests import Request
from lilya.responses import Ok, Response
from lilya.types import ASGIApp, Receive, Scope, Send
from lilya.websockets import WebSocket

if TYPE_CHECKING:
    from lilya.routing import BasePath


class BaseHandler:
    """
    Utils to manage the responses of the handlers.
    """

    def handle_response(
        self, func: Callable[[Request], Awaitable[Response] | Response]
    ) -> ASGIApp:
        """
        Decorator for creating a request-response ASGI application.

        Args:
            func (Callable): The function to be wrapped.

        Returns:
            ASGIApp: The ASGI application.
        """

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            """
            ASGI application handling request-response.

            Args:
                scope (Scope): The request scope.
                receive (Receive): The receive channel.
                send (Send): The send channel.

            Returns:
                None
            """
            request = Request(scope=scope, receive=receive, send=send)

            async def inner_app(scope: Scope, receive: Receive, send: Send) -> None:
                """
                Inner ASGI application handling request-response.

                Sometimes the handler does not need the request to be passed
                in the handler and we can avoid it by ignoring the request
                object in the arguments.

                Args:
                    scope (Scope): The request scope.
                    receive (Receive): The receive channel.
                    send (Send): The send channel.

                Returns:
                    None
                """

                signature: inspect.Signature = self.signature
                func_params: dict[str, Any] = {
                    **self._extract_params_from_request(request=request, signature=signature),
                    **self._extract_context(request=request, signature=signature),
                }
                if signature.parameters:
                    if SignatureDefault.REQUEST in signature.parameters:
                        func_params.update({"request": request})
                        response = await self._execute_function(func, **func_params)
                    else:
                        response = await self._execute_function(func, **func_params)
                else:
                    response = await self._execute_function(func, **func_params)

                await self._handle_response_content(response, scope, receive, send)

            await wrap_app_handling_exceptions(inner_app, request)(scope, receive, send)

        return app

    async def _handle_response_content(
        self, app: ASGIApp, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """
        Generates the app response, ensuring it is in the form of an ASGI application.
        When a special type is passed, it tries to convert to a json format and generate
        the response.

        Args:
            app (Union[ASGIApp, Any]): The response content.
            scope (Scope): The ASGI scope.
            receive (Receive): The receive channel.
            send (Send): The send channel.
        """
        if is_async_callable(app) or isinstance(app, Response):
            # If response is an ASGI application or an async callable, directly await it.
            await app(scope, receive, send)
        else:
            # If response is not an async callable, wrap it in an ASGI application and then await.
            if app is not None:
                app = json_encoder(app)

            response = Ok(app)
            await response(scope, receive, send)

    def _extract_params_from_request(
        self, request: Request, signature: inspect.Signature
    ) -> dict[str, Any]:
        """
        Extracts parameters from the request and injects them into the function if needed.

        Args:
            request (Request): The incoming request.
            signature (inspect.Signature): The signature of the target function.

        Returns:
            Dict[str, Any]: A dictionary containing parameters extracted from the request.
        """
        return {
            param: value
            for param, value in request.path_params.items()
            if param in signature.parameters
        }

    def _extract_context(self, request: Request, signature: inspect.Signature) -> dict[str, Any]:
        """
        Extracts the context from the signature and injects them into the function if needed.

        Args:
            request (Request): The incoming request.
            signature (inspect.Signature): The signature of the target function.

        Returns:
            Dict[str, Any]: A dictionary containing parameters extracted from the signature.
        """
        params: dict[str, Any] = {}
        for param, _ in signature.parameters.items():
            if param in ("context",):
                value = Context(__handler__=cast("BasePath", self), __request__=request)
                params[param] = value
                break
        return params

    def handle_websocket_session(self, func: Callable[[WebSocket], Awaitable[None]]) -> ASGIApp:
        """
        Decorator for creating a WebSocket session ASGI application.

        Args:
            func (Callable): The function to be wrapped.

        Returns:
            ASGIApp: The ASGI application.
        """

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            """
            ASGI application handling WebSocket session.

            Args:
                scope (Scope): The request scope.
                receive (Receive): The receive channel.
                send (Send): The send channel.

            Returns:
                None
            """
            session = WebSocket(scope=scope, receive=receive, send=send)

            async def inner_app(scope: Scope, receive: Receive, send: Send) -> None:
                """
                Inner ASGI application handling WebSocket session.

                Args:
                    scope (Scope): The request scope.
                    receive (Receive): The receive channel.
                    send (Send): The send channel.

                Returns:
                    None
                """
                await self._execute_function(func, session)

            await wrap_app_handling_exceptions(inner_app, session)(scope, receive, send)

        return app

    async def _execute_function(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Executes the given function, handling both synchronous and asynchronous functions.

        Args:
            func (Callable): The function to execute.
            args (Any): Positional arguments for the function.
            kwargs (Any): Keyword arguments for the function.

        Returns:
            Any: The result of the function execution.
        """
        if is_async_callable(func):
            return await func(*args, **kwargs)
        else:
            return await run_in_threadpool(func, *args, **kwargs)
