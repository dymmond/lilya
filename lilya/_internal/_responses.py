from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Coroutine
from typing import TYPE_CHECKING, Any, cast

from lilya._internal._encoders import apply_structure, json_encode
from lilya._internal._exception_handlers import wrap_app_handling_exceptions
from lilya.compat import is_async_callable
from lilya.concurrency import run_in_threadpool
from lilya.conf import _monkay
from lilya.context import Context
from lilya.dependencies import Provide, Provides, Resolve, Security, async_resolve_dependencies
from lilya.enums import SignatureDefault
from lilya.exceptions import ImproperlyConfigured, UnprocessableEntity, WebSocketException
from lilya.params import Cookie, Header, Query
from lilya.requests import Request
from lilya.responses import Ok, Response
from lilya.types import ASGIApp, Receive, Scope, Send
from lilya.websockets import WebSocket

if TYPE_CHECKING:
    from lilya.routing import BasePath as BasePath  # noqa

SIGNATURE_TO_LIST = SignatureDefault.to_list()


class BaseHandler:
    """
    Utils to manage the responses of the handlers.
    """

    __body_params__: dict[str, Any] | None = None
    __query_params__: dict[str, Any] | None = None
    __path_params__: dict[str, Any] | None = None
    __header_params__: dict[str, Any] | None = None
    __cookie_params__: dict[str, Any] | None = None
    __reserved_data__: dict[str, Any] | None = None
    signature: inspect.Signature | None = None

    async def extract_request_information(
        self, request: Request, signature: inspect.Signature
    ) -> None:
        """
        Extracts the information and flattens the request dictionaries in the handler.
        """
        self.__query_params__ = dict(request.query_params.items())
        self.__path_params__ = dict(request.path_params.items())
        self.__header_params__ = dict(request.headers.items())
        self.__cookie_params__ = dict(request.cookies.items())

        reserved_keys = set(self.__path_params__.keys())
        reserved_keys.update(self.__query_params__.keys())
        reserved_keys.update(self.__header_params__.keys())
        reserved_keys.update(self.__cookie_params__.keys())

        self.__reserved_data__ = {
            "path_params": self.__path_params__,
            "header_params": self.__header_params__,
            "cookie_params": self.__cookie_params__,
            "query_params": self.__query_params__,
        }

        # Store the body params in the handler variable
        self.__body_params__ = {
            k: v.annotation for k, v in signature.parameters.items() if k not in reserved_keys
        }

    def handle_response(
        self,
        func: Callable[[Request], Awaitable[Response] | Response]
        | Callable[[], Coroutine[Any, Any, Response]],
        other_signature: inspect.Signature | None = None,
    ) -> ASGIApp:
        """
        Decorator for creating a request-response ASGI application.

        Args:
            func (Callable): The function to be wrapped.
            other_signature (inspect.Signature): Another passed signature

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
                signature: inspect.Signature = other_signature or self.signature
                await self.extract_request_information(request=request, signature=signature)

                params_from_request = await self._extract_params_from_request(
                    request=request,
                    signature=signature,
                )

                request_information = await self.extract_request_params_information(
                    request=request, signature=signature
                )

                func_params: dict[str, Any] = {
                    **params_from_request,
                    **self._extract_context(request=request, signature=signature),
                    **request_information,
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
                app = json_encode(app)

            response = Ok(app)
            await response(scope, receive, send)

    async def extract_request_params_information(
        self, request: Request, signature: inspect.Signature
    ) -> dict[str, Any]:
        """
        Extracts the request information from the request and populates the
        request information.
        """

        request_params: dict[str, Any] = {}
        parameters = signature.parameters

        for name, parameter in parameters.items():
            field = parameter.default
            if field is inspect._empty:
                continue

            if isinstance(field, Query):
                source = request.query_params
                key = field.alias or name
            elif isinstance(field, Header):
                source = request.headers  # type: ignore
                key = field.value
            elif isinstance(field, Cookie):
                source = request.cookies  # type: ignore
                key = field.value
            else:
                continue

            try:
                if not isinstance(field, Cookie):
                    raw_value = (
                        source.get(key, None)
                        if len(source.getall(key)) == 1
                        else source.getall(key, None)
                    )
                else:
                    raw_value = source.get(key)
            except (KeyError, TypeError):
                raw_value = None

            if field.required and raw_value is None:
                raise UnprocessableEntity(f"Missing mandatory query parameter '{key}'") from None

            # Fallback to default
            if raw_value is None:
                request_params[name] = field.default if hasattr(field, "default") else None
                continue

            # Apply casting if defined
            try:
                if field.cast and isinstance(raw_value, list):
                    request_params[name] = [raw_value]
                elif field.cast:
                    request_params[name] = field.resolve(raw_value, field.cast)
                else:
                    if isinstance(raw_value, list) and len(raw_value) == 1:
                        request_params[name] = raw_value[0]
                    else:
                        request_params[name] = raw_value
            except (TypeError, ValueError):
                raise UnprocessableEntity(
                    f"Invalid value for query parameter '{key}': expected {field.cast.__name__}"
                ) from None

        return request_params

    def is_explicitly_bound(self, param: inspect.Parameter) -> bool:
        """
        Checks for explicitly bound parameter from the default.
        """
        default = None
        if hasattr(param, "default"):
            default = param.default
        if hasattr(param, "value"):
            default = param.value
        return isinstance(default, (Query, Header, Cookie))

    async def _parse_inferred_body(
        self,
        request: Request,
        dependencies: dict[str, Any],
        signature: inspect.Signature,
    ) -> Any:
        """
        Parses only the parameters inferred to come from the request body.

        Automatically skips parameters present in path, query, headers, or cookies.
        Supports:

        - Multi-param style: {"user": {...}, "item": {...}}
        - Single-param style: {"name": "...", "age": ...} -> into a single structured param
        """
        json_data = await request.json() or {}
        parameters = signature.parameters

        # Determine which parameters are already accounted for
        reserved_keys = set(request.path_params.keys())
        reserved_keys.update(request.query_params.keys())
        reserved_keys.update(request.headers.keys())
        reserved_keys.update(request.cookies.keys())

        # The remaining parameters are inferred as body-bound
        body_param_names = [
            name
            for name, value in parameters.items()
            if name not in reserved_keys
            and not isinstance(value.default, (Provides, Resolve))
            and not self.is_explicitly_bound(value)
            and name not in dependencies
            and name not in SIGNATURE_TO_LIST
        ]
        payload: dict[str, Any] = {}

        if len(body_param_names) == 1:
            name = body_param_names[0]
            encoder_object = parameters[name].annotation

            if name in SIGNATURE_TO_LIST:
                return payload

            if name in dependencies:
                return payload

            try:
                payload[name] = apply_structure(structure=encoder_object, value=json_data)
            except Exception as exc:  # noqa
                if name in json_data:
                    payload[name] = apply_structure(
                        structure=encoder_object, value=json_data[name]
                    )
                else:
                    raise exc
        else:
            for name in body_param_names:
                if name in SIGNATURE_TO_LIST:
                    continue

                if name in dependencies:
                    continue

                if name not in json_data:
                    raise ValueError(f"Missing expected body key and/or payload for '{name}'.")
                encoder_object = parameters[name].annotation
                payload[name] = apply_structure(structure=encoder_object, value=json_data[name])

        return payload

    async def _extract_params_from_request(
        self,
        request: Request,
        signature: inspect.Signature,
    ) -> dict[str, Any]:
        """
        Extracts and resolves parameters for a function from an incoming request.

        This asynchronous method is responsible for gathering data from various
        sources within an HTTP request (path parameters, request body, and
        dependency injection system) and preparing them as arguments suitable
        for a target function based on its signature. It handles body inference,
        merging of dependencies from application, scope, and handler levels,
        and resolves `Provides` dependencies.

        Args:
            request: The incoming `Request` object, containing details about the
                HTTP request.
            signature: An `inspect.Signature` object representing the callable's
                parameters, used to determine what arguments are needed and their
                default values.

        Returns:
            A dictionary where keys are parameter names and values are the
            corresponding extracted or resolved arguments.

        Raises:
            ImproperlyConfigured: If a registered dependency does not correspond
                to a `Provides` parameter in the function signature, or if a
                `Provides` parameter is defined but no corresponding dependency
                is registered.
        """
        # 1) COLLECT ALL PROVIDE(...) mappings
        merged: dict[str, Provide] = {}

        # from the app
        app_obj = getattr(request, "app", None) or request.scope.get("app")
        if app_obj is not None and (app_deps := getattr(app_obj, "dependencies", None)):
            merged.update(app_deps)

        # from any Include scopes
        for inc_map in request.scope.get("dependencies", []):
            merged.update(inc_map)

        # from the route handler itself
        handler = request.scope.get("handler")
        if handler and (route_deps := getattr(handler, "_lilya_dependencies", None)):
            merged.update(route_deps)

        # 2) FILTER to only the ones the handler signature actually names as Provides()
        requested: dict[str, Provide | Resolve | Security] = {}
        for name, param in signature.parameters.items():
            if isinstance(param.default, Provides):
                # we want to inject “name” if the handler did `foo = Provides()`
                requested[name] = merged.get(name)

            elif isinstance(param.default, (Resolve, Security)):
                requested[name] = param.default

            elif param.name in merged and param.default is inspect.Parameter.empty:
                requested[name] = merged.get(name)

        # 3) Determine if the request body should be inferred and parsed.
        is_body_inferred: bool = _monkay.settings.infer_body
        json_data: dict[str, Any] = {}
        if is_body_inferred:
            # If body inference is enabled, attempt to parse the request body.
            json_data = await self._parse_inferred_body(request, requested, signature)

        # 3.1) Extract path parameters that are present in the function's signature.
        data = {
            name: val for name, val in request.path_params.items() if name in signature.parameters
        }
        # Merge the extracted JSON body data into the parameters dictionary.
        data.update(json_data)

        # 4) RESOLVE exactly those—and error if any are missing
        for name, provider in requested.items():
            if provider is None:
                hname = handler.__name__ if handler else "<unknown>"
                raise ImproperlyConfigured(f"Missing dependency '{name}' for handler '{hname}'")

            if isinstance(provider, (Resolve, Security)):
                data[name] = await async_resolve_dependencies(
                    request=request,
                    func=provider.dependency,
                )
                continue
            data[name] = await provider.resolve(request, merged)

        # Return the dictionary of all extracted and resolved parameters.
        return data

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
            existing = list(scope.get("dependencies", []))
            scope["dependencies"] = existing + [getattr(self, "dependencies", {})]

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
                signature = inspect.signature(func)
                kwargs: dict[str, Any] = {}

                # merge app/include/route deps exactly like HTTP does:
                merged: dict[str, Any] = {}

                # app-level
                app_obj = getattr(scope.get("app", None), "dependencies", {}) or {}
                merged.update(app_obj)

                # include-level
                for inc in scope.get("dependencies", []):
                    merged.update(inc)

                # route-level
                route_map = getattr(func, "_lilya_dependencies", {}) or {}
                merged.update(route_map)

                websocket = WebSocket(scope, receive, send)
                # now for each Provides() param, resolve it
                for name, param in signature.parameters.items():
                    if isinstance(param.default, Provides):
                        if name not in merged:
                            raise WebSocketException(
                                code=1011,
                                reason=f"Missing dependency '{name}' for websocket handler '{func.__name__}'",
                            )
                        provider = merged[name]

                        if isinstance(provider, (Resolve, Security)):
                            kwargs[name] = await async_resolve_dependencies(
                                request=websocket,
                                func=provider.dependency,
                            )
                            continue
                        data = await provider.resolve(websocket, merged)
                        kwargs[name] = data

                    elif isinstance(param.default, (Resolve, Security)):
                        kwargs[name] = await async_resolve_dependencies(
                            request=websocket,
                            func=param.default.dependency,
                        )

                    elif param.name in merged and param.default is inspect.Parameter.empty:
                        provider = merged[name]
                        kwargs[name] = await provider.resolve(websocket, merged)

                await self._execute_function(func, session, **kwargs)

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
