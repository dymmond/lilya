from json import loads
from typing import Any

from pydantic import ValidationError

from lilya import status
from lilya.exceptions import HTTPException
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.types import ExceptionHandler
from tests.settings import AppTestSettings


async def validation_error_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:  # pragma: no cover
    """
    This handler is to be used when a pydantic validation error is triggered during the logic
    of a code block and not the definition of a handler.

    This is different from validation_error_exception_handler
    """
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse({"detail": loads(exc.json())}, status_code=status_code)


async def http_exception(request, exc):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


class EncoderSettings(AppTestSettings):
    infer_body: bool = True

    @property
    def exception_handlers(self) -> ExceptionHandler | dict[Any, Any]:
        return {
            ValidationError: validation_error_exception_handler,
            HTTPException: http_exception,
        }
