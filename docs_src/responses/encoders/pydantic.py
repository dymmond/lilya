from typing import Any

from pydantic import BaseModel

from lilya.encoders import Encoder, register_encoder


class PydanticEncoder(Encoder):
    __type__: BaseModel

    def serialize(self, obj: BaseModel) -> dict[str, Any]:
        return obj.model_dump()


register_encoder(PydanticEncoder())
