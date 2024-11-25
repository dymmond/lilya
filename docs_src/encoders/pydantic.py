from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from lilya.encoders import Encoder, register_encoder


class PydanticEncoder(Encoder):
    __type__ = BaseModel
    # optional a name can be provided, so same named encoders are removed
    name = "ModelDumpEncoder"

    # is_type and is_type_structure are provided by Encoder.
    # checked is the type provided by __type__.

    def serialize(self, obj: BaseModel) -> dict[str, Any]:
        return obj.model_dump()

    def encode(self, structure: type[BaseModel], value: Any) -> Any:
        return structure(**value)


# A normal way
register_encoder(PydanticEncoder())

# As alternative
register_encoder(PydanticEncoder)
