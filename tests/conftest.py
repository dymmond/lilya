import functools
import sys
from typing import Any

import msgspec
import pytest
from attrs import asdict, has
from msgspec import Struct
from pydantic import BaseModel

from lilya.encoders import Encoder, register_encoder
from lilya.testclient import TestClient


@pytest.fixture
def test_client_factory(anyio_backend_name, anyio_backend_options):
    return functools.partial(
        TestClient,
        backend=anyio_backend_name,
        backend_options=anyio_backend_options,
    )


if sys.version_info <= (3, 9):  # pragma: no cover
    dont_run = True
else:  # pragma: no cover
    dont_run = False

    class PydanticEncoder(Encoder):

        def is_type(self, value: Any) -> bool:
            return isinstance(value, BaseModel)

        def serialize(self, obj: BaseModel) -> dict[str, Any]:
            return obj.model_dump()

    register_encoder(PydanticEncoder())


class MsgSpecEncoder(Encoder):
    __type__ = Struct

    def serialize(self, obj: Any) -> Any:
        return msgspec.json.decode(msgspec.json.encode(obj))


register_encoder(MsgSpecEncoder())


class AttrsEncoder(Encoder):

    def is_type(self, value: Any) -> bool:
        return has(value)

    def serialize(self, obj: Any) -> Any:
        return asdict(obj)


register_encoder(AttrsEncoder())
