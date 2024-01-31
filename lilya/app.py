from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Sequence, Union

from typing_extensions import Annotated, Doc

from lilya._utils import is_class_and_subclass
from lilya.conf.exceptions import FieldException
from lilya.conf.global_settings import Settings
from lilya.datastructures import State
from lilya.permissions.base import Permission
from lilya.routing import Router
from lilya.types import ApplicationType, ASGIApp, ExceptionHandler, Lifespan


class Lilya:
    """
    Initialize the Lilya ASGI framework.

    **Example**:

    ```python
    from lilya import Lilya

    app = Lilya(debug=True, routes=[...], middleware=[...], ...)
    ```
    """

    def __init__(
        self,
        debug: Annotated[bool, Doc("Enable or disable debug mode. Defaults to False.")] = False,
        routes: Annotated[
            Union[Sequence[Any], None],
            Doc("A sequence of routes for the application."),
        ] = None,
        middleware: Annotated[
            Union[Sequence[Any], None],
            Doc("A sequence of middleware components for the application."),
        ] = None,
        exception_handlers: Annotated[
            Union[Mapping[Any, ExceptionHandler], None],
            Doc("A mapping of exception types to handlers for the application."),
        ] = None,
        permissions: Annotated[
            Union[Sequence[Permission], None],
            Doc("A sequence of permission components for the application."),
        ] = None,
        on_startup: Annotated[
            Union[Sequence[Callable[[], Any]], None],
            Doc("A sequence of startup functions to be called when the application starts."),
        ] = None,
        on_shutdown: Annotated[
            Union[Sequence[Callable[[], Any]], None],
            Doc("A sequence of shutdown functions to be called when the application stops."),
        ] = None,
        redirect_slashes: Annotated[
            bool,
            Doc("Enable or disable automatic trailing slash redirection for HTTP routes."),
        ] = True,
        lifespan: Annotated[
            Optional[Lifespan[ApplicationType]],
            Doc("An optional lifespan handler for managing startup and shutdown events."),
        ] = None,
        include_in_schema: Annotated[
            bool,
            Doc("Enable or disable inclusion of the application in the OpenAPI schema."),
        ] = True,
        settings_config: Annotated[
            Optional[Settings],
            Doc(
                """
                Alternative settings parameter. This parameter is an alternative to
                `SETTINGS_MODULE` way of loading your settings into an Esmerald application.

                When the `settings_config` is provided, it will make sure it takes priority over
                any other settings provided for the instance.
                """
            ),
        ] = None,
    ) -> None:
        self.settings_config = None

        if settings_config:
            if not isinstance(settings_config, Settings) and not is_class_and_subclass(
                settings_config, Settings
            ):  # type: ignore
                raise FieldException("'settings_config' must be a subclass of Settings")
            elif isinstance(settings_config, Settings):
                self.settings_config = settings_config
            elif is_class_and_subclass(settings_config, Settings):  # type: ignore
                self.settings_config = settings_config()

        self.debug = debug
        self.state = State()
        self.exception_handlers = {} if exception_handlers is None else dict(exception_handlers)
        self.permissions = [] if permissions is None else list(permissions)
        self.middleware_stack: Union[ASGIApp, None] = None
        self.custom_middleware = [] if middleware is None else list(middleware)
        self.router: Router = Router(
            routes=routes,
            redirect_slashes=redirect_slashes,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            middleware=middleware,
            permissions=permissions,
            include_in_schema=include_in_schema,
        )

    # def build_middleware_stack(self) -> ASGIApp:
    #     debug = self.debug
    #     error_handler = None
    #     exception_handlers: Dict[Any, Callable[[Request, Exception], Response]] = {}

    #     for key, value in self.exception_handlers.items():
    #         if key in (500, Exception):
    #             error_handler = value
    #         else:
    #             exception_handlers[key] = value

    #     middleware = (
    #         [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
    #         + self.custom_middleware
    #         + [Middleware(ExceptionMiddleware, handlers=exception_handlers, debug=debug)]
    #     )

    #     app = self.router
    #     for cls, options in reversed(middleware):
    #         app = cls(app=app, **options)
    #     return app
