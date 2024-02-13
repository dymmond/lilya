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


register_encoder(MsgSpecEncoder())
