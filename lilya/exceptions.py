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


class ImproperlyConfigured(HTTPException, ValueError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class InternalServerError(ImproperlyConfigured):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class NotAuthorized(HTTPException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "You do not have authorization to perform this action."


class NotFound(HTTPException, ValueError):
    detail = "The resource cannot be found."
    status_code = status.HTTP_404_NOT_FOUND


class MethodNotAllowed(HTTPException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED


class PermissionDenied(HTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


class MissingDependency(LilyaException, ImportError): ...


class TemplateNotFound(HTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, *args: Any, name: str):
        """Template could not be found."""
        super().__init__(*args, detail=f"Template {name} not found.")


class WebSocketRuntimeError(RuntimeError): ...


class AuthenticationError(Exception): ...
