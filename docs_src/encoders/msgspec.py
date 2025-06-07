from typing import Any

import msgspec
from msgspec import Struct

from lilya._utils import is_class_and_subclass
from lilya.encoders import Encoder, register_encoder


class MsgSpecEncoder(Encoder):
    """
    Encoder for msgspec.Struct objects.
    """

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
        """
        Serialize a msgspec.Struct object.

        Args:
            obj (Any): The object to serialize.

        Returns:
            Any: The serialized object.
        """
        return msgspec.json.decode(msgspec.json.encode(obj))

    def encode(self, annotation: Any, value: Any) -> Any:
        """
        Encode a value into a msgspec.Struct.

        Args:
            annotation (Any): The annotation type.
            value (Any): The value to encode.

        Returns:
            Any: The encoded value.
        """
        return msgspec.json.decode(msgspec.json.encode(value), type=annotation)


# A normal way
register_encoder(MsgSpecEncoder())

# As alternative
register_encoder(MsgSpecEncoder)
