from typing import Any

from attrs import asdict, has

from lilya.encoders import Encoder, register_encoder


class AttrsEncoder(Encoder):

    def is_type(self, value: Any) -> bool:
        """
        You can use this function instead of declaring
        the `__type__`.
        """
        return has(value)

    def serialize(self, obj: Any) -> Any:
        return asdict(obj)


register_encoder(AttrsEncoder())
