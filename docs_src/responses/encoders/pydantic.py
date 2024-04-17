from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from lilya.encoders import Encoder, register_encoder


class PydanticEncoder(Encoder):
    __type__ = BaseModel

    def serialize(self, obj: BaseModel) -> dict[str, Any]:
        return obj.model_dump()


# A normal way
register_encoder(PydanticEncoder())

# As alternative
register_encoder(PydanticEncoder)
