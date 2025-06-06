from __future__ import annotations

import functools
from typing import Any

import msgspec
import pytest
from attrs import asdict, has
from msgspec import Struct

from lilya.encoders import Encoder, register_encoder
from lilya.testclient import TestClient


@pytest.fixture
def test_client_factory(anyio_backend_name, anyio_backend_options):
    return functools.partial(
        TestClient,
        backend=anyio_backend_name,
        backend_options=anyio_backend_options,
    )


class MsgSpecEncoder(Encoder):
    __type__ = Struct

    def serialize(self, obj: Any) -> Any:
        return msgspec.json.decode(msgspec.json.encode(obj))

    def encode(
        self,
        structure: Any,
        obj: Any,
    ) -> Any:
        return msgspec.json.decode(msgspec.json.encode(obj), type=structure)


register_encoder(MsgSpecEncoder())


class AttrsEncoder(Encoder):
    def is_type(self, value: Any) -> bool:
        return has(value)

    def serialize(self, obj: Any) -> Any:
        return asdict(obj)


register_encoder(AttrsEncoder())
