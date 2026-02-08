from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic_core import PydanticSerializationError

from lilya.encoders import Encoder, register_encoder


class PydanticEncoder(Encoder):
    """
    A custom Lilya Encoder for handling Pydantic models.

    This class registers `pydantic.BaseModel` with Lilya's encoding system, enabling
    automatic serialization of models into JSON-compatible dictionaries and deserialization
    of raw data into validated model instances.
    """

    __type__ = BaseModel

    def serialize(self, obj: BaseModel) -> dict[str, Any]:
        """
        Convert a Pydantic model instance into a standard dictionary.

        This method leverages Pydantic V2's `model_dump()` to produce a clean
        dictionary representation of the model's data.

        Args:
            obj (BaseModel): The Pydantic model instance to serialize.

        Returns:
            dict[str, Any]: The dictionary representation of the model.
        """
        try:
            return obj.model_dump(mode="json")
        except PydanticSerializationError:
            return obj.model_dump()

    def encode(self, structure: type[BaseModel], value: Any) -> BaseModel:
        """
        Reconstruct a Pydantic model instance from raw input data.

        This method is used when Lilya needs to cast a raw value (e.g., from a request
        body) into a specific Pydantic model type defined in a handler signature.

        Args:
            structure (type[BaseModel]): The concrete Pydantic model class to instantiate.
            value (Any): The raw input data, expected to be a dictionary of field values.

        Returns:
            BaseModel: An instance of the specified Pydantic model, validated and initialized.
        """
        if isinstance(value, BaseModel) or is_class_and_subclass(value, BaseModel):
            return value
        return structure(**value)


# A normal way
register_encoder(PydanticEncoder())

# As alternative
register_encoder(PydanticEncoder)
