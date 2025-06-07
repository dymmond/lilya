from typing import Any

import msgspec
from msgspec import Struct

from lilya._utils import is_class_and_subclass
from lilya.encoders import Encoder, register_encoder


class MsgSpecEncoder(Encoder):

    def is_type(self, value: Any) -> bool:
        """
        Check if the value is an instance of msgspec.Struct.

        Args:
            value (Any): The value to check.

        Returns:
            bool: True if the value is an instance of msgspec.Struct, False otherwise.
        """
        return isinstance(value, Struct) or is_class_and_subclass(value, Struct)

    def serialize(self, obj: Any) -> Any:
        return msgspec.json.decode(msgspec.json.encode(obj))

    def encode(
        self,
        structure: Any,
        obj: Any,
    ) -> Any:
        return msgspec.json.decode(msgspec.json.encode(obj), type=structure)

# A normal way
register_encoder(MsgSpecEncoder())

# As alternative
register_encoder(MsgSpecEncoder)
