from json import loads

from msgspec import Struct, ValidationError as MSpecValidation
from pydantic import BaseModel, ValidationError

from lilya import status
from lilya.controllers import Controller
from lilya.requests import Request
from lilya.responses import JSONResponse
from lilya.routing import Path
from lilya.testclient import create_client
from tests.encoders.settings import EncoderSettings


async def pydantic_validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:  # pragma: no cover
    """
    This handler is to be used when a pydantic validation error is triggered during the logic
    of a code block and not the definition of a handler.

    This is different from validation_error_exception_handler
    """
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse({"detail": loads(exc.json())}, status_code=status_code)


async def msgspec_validation_error_handler(
    request: Request, exc: MSpecValidation
) -> JSONResponse:  # pragma: no cover
    """
    This handler is to be used when a pydantic validation error is triggered during the logic
    of a code block and not the definition of a handler.

    This is different from validation_error_exception_handler
    """
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse({"detail": str(exc)}, status_code=status_code)


class User(BaseModel):
    name: str
    age: int


class Item(Struct):
    sku: str


class Test(Controller):
    async def post(self, user: User, item: Item):
        return {**user.model_dump(), "sku": item.sku}


def test_infer_body_pydantic():
    data = {"user": {"name": "lilya"}, "item": {"sku": "test"}}

    with create_client(
        routes=[Path("/infer", handler=Test, methods=["POST"])],
        settings_module=EncoderSettings,
        exception_handlers={
            ValidationError: pydantic_validation_error_handler,
        },
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 422
        assert "detail" in response.json()


def test_infer_body_msgspec():
    data = {"user": {"name": "lilya", "age": 10}, "item": {"sku": 2}}

    with create_client(
        routes=[Path("/infer", handler=Test, methods=["POST"])],
        settings_module=EncoderSettings,
        exception_handlers={
            MSpecValidation: msgspec_validation_error_handler,
        },
    ) as client:
        response = client.post("/infer", json=data)

        assert response.status_code == 422
        assert response.json() == {"detail": "Expected `str`, got `int` - at `$.sku`"}
