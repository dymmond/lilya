from __future__ import annotations

import http
from typing import Any

from lilya import status

__all__ = ("HTTPException", "WebSocketException")


class LilyaException(Exception):
    def __init__(self, *args: Any, detail: str = ""):
        self.detail = detail
        super().__init__(*(str(arg) for arg in args if arg), self.detail)

    def __repr__(self) -> str:  # pragma: no cover
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__

    def __str__(self) -> str:
        return "".join(self.args).strip()


class HTTPException(LilyaException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        *args: Any,
        status_code: int | None = None,
        detail: str | None = None,
        headers: dict[str, str] | None = None,
        **extra: Any,
    ) -> None:
        detail = detail or getattr(self, "detail", None)
        status_code = status_code or getattr(self, "status_code", None)
        if not detail:
            detail = args[0] if args else http.HTTPStatus(status_code or self.status_code).phrase
            args = args[1:]
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        self.args = (f"{self.status_code}: {self.detail}", *args)
        self.extra = extra

    def __str__(self) -> str:
        return f"{self.status_code}: {self.detail}"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"


class WebSocketException(Exception):
    def __init__(self, code: int, reason: str | None = None) -> None:
        self.code = code
        self.reason = reason or ""

    def __str__(self) -> str:
        return f"{self.code}: {self.reason}"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(code={self.code!r}, reason={self.reason!r})"


class ContinueRouting(BaseException):
    """
    Signals that the route handling should continue and not stop with the current route.
    Instead of signalling instantly a 404 the default handler of the router is used when the last route.
    """


class ImproperlyConfigured(HTTPException, ValueError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class InternalServerError(ImproperlyConfigured):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class NotAuthorized(HTTPException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Not Authorized."


class NotFound(HTTPException, ValueError):
    detail = "The resource cannot be found."
    status_code = status.HTTP_404_NOT_FOUND


class MethodNotAllowed(HTTPException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED


class PermissionDenied(HTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


class MissingDependency(LilyaException, ImportError): ...


class UnprocessableEntity(HTTPException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class TemplateNotFound(HTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, *args: Any, name: str):
        """Template could not be found."""
        super().__init__(*args, detail=f"Template {name} not found.")


class ContentRangeNotSatisfiable(HTTPException):
    status_code = status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE

    def __init__(self, *args: Any, range_def: tuple[int, int] | None = None, size: int, unit: str):
        """Requested range out of bounds."""
        self.unit = unit
        self.size = size
        detail = (
            "Requested range ({range_def[0]}-{range_def[1]}) is not satisfiable."
            if range_def
            else "Requested range is not satisfiable."
        )
        super().__init__(
            *args,
            detail=detail,
            headers={"content-range": f"{unit} */{size}"},
        )


class WebSocketRuntimeError(RuntimeError): ...


class AuthenticationError(Exception): ...


class EnvError(Exception): ...


# The EnvironmentError name is bad, it clashes with a builtin exception
EnvironmentError = EnvError
