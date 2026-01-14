from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from lilya.encoders import apply_structure, json_encode

T = TypeVar("T")


@dataclass(frozen=True)
class MessageMeta:
    """
    Standard metadata container for CQRS messages.

    This class encapsulates context usually required by middleware or infrastructure
    handlers, such as routing information, protocol versions, or tracing headers.

    Attributes:
        name (str): The logical name of the message (e.g., "UserCreated").
        version (int): The schema version of the payload. Defaults to 1.
        headers (dict[str, Any]): Arbitrary key-value pairs for infrastructure use
            (e.g., correlation IDs, timestamps, user context).
    """

    name: str
    version: int = 1
    headers: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Envelope(Generic[T]):
    """
    A unified transport container for CQRS payloads (Commands or Queries).

    The Envelope wraps the actual business intent (the payload) with the necessary
    metadata (`MessageMeta`) required for processing. It leverages `lilya.encoders`
    to ensure that complex types (like Pydantic models or dataclasses) are
    consistently serialized and deserialized across the wire.

    Type Parameters:
        T: The type of the payload (e.g., a specific Command or Query class).
    """

    payload: T
    meta: MessageMeta

    def to_json(self) -> dict[str, Any]:
        """
        Serialize the envelope into a standard dictionary format suitable for JSON transport.

        This method attempts to intelligently convert the payload:
        1. If it's a Pydantic V2 model, uses `model_dump()`.
        2. If it's a Pydantic V1 model, uses `dict()`.
        3. Otherwise, falls back to `lilya.encoders.apply_structure`.

        Returns:
            dict[str, Any]: A dictionary with 'meta' and 'payload' keys.
        """
        payload_obj = self._to_plain(self.payload)
        meta_obj = {
            "name": self.meta.name,
            "version": self.meta.version,
            "headers": json_encode(self.meta.headers),
        }
        # json_encode ensures that types like UUIDs or datetimes in the payload
        # are converted to primitives (strings, ints)
        return {"meta": meta_obj, "payload": json_encode(payload_obj)}

    @staticmethod
    def _to_plain(obj: Any) -> Any:
        """
        Helper to convert a strongly-typed object into a plain dictionary or primitive.
        """
        return json_encode(value=obj)

    @classmethod
    def from_json(cls, data: dict[str, Any], payload_type: type[T]) -> Envelope[T]:
        """
        Reconstruct an Envelope from a raw dictionary.

        This method deserializes the 'payload' field back into the specific `payload_type`
        class (e.g., a Dataclass or Pydantic model) using `lilya.apply_structure`.

        Args:
            data (dict[str, Any]): The raw JSON dictionary containing 'meta' and 'payload'.
            payload_type (type[T]): The class to cast the payload into.

        Returns:
            Envelope[T]: A fully typed envelope instance.
        """
        meta_raw = data.get("meta") or {}
        payload_raw = data.get("payload")

        meta = MessageMeta(
            name=meta_raw.get("name") or payload_type.__name__,
            version=int(meta_raw.get("version") or 1),
            headers=meta_raw.get("headers") or {},
        )

        # Rehydrate the payload into the target domain class
        payload = apply_structure(payload_type, payload_raw)
        return cls(payload=payload, meta=meta)


class Command:
    """
    Marker base class for Command objects (Write operations).
    Inheritance is optional but useful for type checking.
    """

    ...


class Query(Generic[T]):
    """
    Marker base class for Query objects (Read operations).
    The generic type T represents the expected return type of the query.
    """

    ...
