from collections import deque
from dataclasses import dataclass
from datetime import date, datetime

import orjson
import pytest
from pydantic import BaseModel

from lilya._internal._encoders import DataclassEncoder
from lilya.encoders import ENCODER_TYPES, apply_structure, json_encode, register_encoder


def test_overwrite():
    _new_encoders = deque(ENCODER_TYPES.get())

    class NewDataclassEncoder(DataclassEncoder):
        def serialize(self, value):
            return {"new": super().DataclassEncoder()}

    assert all(not isinstance(encoder, NewDataclassEncoder) for encoder in _new_encoders)
    assert any(
        not isinstance(encoder, NewDataclassEncoder) and isinstance(encoder, DataclassEncoder)
        for encoder in _new_encoders
    )
    token = ENCODER_TYPES.set(_new_encoders)
    try:
        register_encoder(NewDataclassEncoder)
        assert not any(
            not isinstance(encoder, NewDataclassEncoder) and isinstance(encoder, DataclassEncoder)
            for encoder in _new_encoders
        )

    finally:
        ENCODER_TYPES.reset(token)

    assert any(
        not isinstance(encoder, NewDataclassEncoder) and isinstance(encoder, DataclassEncoder)
        for encoder in ENCODER_TYPES.get()
    )


@dataclass
class FooDataclass:
    a: int


class FooModel(BaseModel):
    a: int


class FooSimple:
    # Credits to tarsil for this test
    def __init__(self, name: str) -> None:
        self.name = name

    def model_dump(self) -> dict[str, str]:
        return self.__dict__

    def __eq__(self, other):
        return isinstance(other, type(self)) and other.name == self.name


@pytest.mark.parametrize(
    "json_encode_kwargs", [{}, {"json_encode_fn": orjson.dumps, "post_transform_fn": orjson.loads}]
)
@pytest.mark.parametrize(
    "value",
    [
        date(2024, 1, 1),
        datetime(2024, 1, 1, 10, 0),
        2.4,
        FooDataclass(a=1),
        FooModel(a=1),
        {"a": 5},
        FooSimple(name="hello"),
        b"ctdsjdsxxxpng",
    ],
)
def test_idempotence(value, json_encode_kwargs):
    value_type = type(value)
    assert apply_structure(value_type, json_encode(value, **json_encode_kwargs)) == value


@pytest.mark.parametrize(
    "json_encode_kwargs", [{}, {"json_encode_fn": orjson.dumps, "post_transform_fn": orjson.loads}]
)
def test_memoryview(json_encode_kwargs):
    tmp = b"ctdsjdsxxxpng"
    assert apply_structure(bytes, json_encode(memoryview(tmp), **json_encode_kwargs)) == tmp


def test_dont_crash_on_strings():
    apply_structure("test", {})
