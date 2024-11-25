from typing import Any

import msgspec
from msgspec import Struct

from lilya.encoders import Encoder, register_encoder


class MsgSpecEncoder(Encoder):
    __type__ = Struct

    def serialize(self, obj: Any) -> Any:
        """
        When a `msgspec.Struct` is serialised,
        it will call this function.
        """
        return msgspec.json.decode(msgspec.json.encode(obj))

    def encode(
        self,
        structure: Any,
        obj: Any,
    ) -> Any:
        return msgspec.json.decode(obj, type=structure)


# A normal way
register_encoder(MsgSpecEncoder())

# As alternative
register_encoder(MsgSpecEncoder)
