from __future__ import annotations

import http
from typing import Annotated, Any, cast

from typing_extensions import Doc

from lilya import status
from lilya._internal._encoding import force_str  # noqa


def _get_error_details(data: Any) -> Any:
    if isinstance(data, (list, tuple)):
        return [_get_error_details(item) for item in data]

    elif isinstance(data, dict):
        return {key: _get_error_details(value) for key, value in data.items()}

    text = force_str(data)
    return ErrorDetail(text)


class ErrorDetail(str):
    def __new__(cls, string: str) -> ErrorDetail:
        self = super().__new__(cls, string)
        return self

    def __repr__(self) -> str:
        return f"ErrorDetail(string={str(self)})"

    def __hash__(self) -> int:
        return hash(str(self))


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


class ValidationError(HTTPException):
    """
    Provides a more detailed error message for validation errors
    when thrown by the application.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Validation error."

    def __init__(
        self,
        detail: str | list[str] | dict[str, Any] | tuple[str] = None,
        status_code: Annotated[
            int | None,
            Doc(
                """
                An integer with the status code to be raised.
                """
            ),
        ] = None,
        headers: Annotated[
            dict[str, Any] | None,
            Doc(
                """
                Any python dictionary containing headers.
                """
            ),
        ] = None,
        **extra: Annotated[
            Any,
            Doc(
                """
                Any extra information used by the exception.
                """
            ),
        ],
    ) -> None:
        if isinstance(detail, tuple):
            detail = list(detail)
        elif not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        detail = _get_error_details(detail)
        super().__init__(
            status_code=status_code, detail=cast(str, detail), headers=headers, **extra
        )


# The EnvironmentError name is bad, it clashes with a builtin exception
EnvironmentError = EnvError
