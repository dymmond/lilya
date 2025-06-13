from json import loads

from pydantic import BaseModel, ValidationError

from lilya import status
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


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


class User(BaseModel):
    name: str
    age: int


async def process_body(user: User):
    return user


def test_infer_body_error(test_client_factory):
    with create_client(
        routes=[Path("/infer", handler=process_body, methods=["POST"])],
        settings_module=EncoderSettings,
        exception_handlers={ValidationError: validation_error_exception_handler},
    ) as client:
        response = client.post("/infer")

        assert response.status_code == 422
        assert "detail" in response.json()
