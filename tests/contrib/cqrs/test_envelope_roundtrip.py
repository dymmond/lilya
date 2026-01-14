from __future__ import annotations

from dataclasses import dataclass

from lilya.contrib.cqrs.messages import Envelope, MessageMeta


@dataclass
class DCmd:
    x: int
    y: str


class PydV1Like:
    def __init__(self, a: int, b: str) -> None:
        self.a = a
        self.b = b

    def dict(self) -> dict:
        return {"a": self.a, "b": self.b}


class PydV2Like:
    def __init__(self, a: int, b: str) -> None:
        self.a = a
        self.b = b

    def model_dump(self) -> dict:
        return {"a": self.a, "b": self.b}


def test_envelope_to_json_includes_meta_and_payload() -> None:
    env = Envelope(
        payload=DCmd(1, "z"),
        meta=MessageMeta(name="DCmd", version=3, headers={"h": "v"}),
    )
    data = env.to_json()

    assert "meta" in data
    assert "payload" in data
    assert data["meta"]["name"] == "DCmd"
    assert data["meta"]["version"] == 3
    assert data["meta"]["headers"] == {"h": "v"}

    assert data["payload"]["x"] == 1
    assert data["payload"]["y"] == "z"


def test_envelope_from_json_roundtrip_dataclass() -> None:
    env = Envelope(payload=DCmd(10, "abc"), meta=MessageMeta(name="DCmd", version=1))
    data = env.to_json()

    rebuilt = Envelope.from_json(data, DCmd)

    assert rebuilt.meta.name == "DCmd"
    assert rebuilt.payload == DCmd(10, "abc")


def test_envelope_payload_pydantic_v2_like_model_dump() -> None:
    env = Envelope(payload=PydV2Like(2, "y"), meta=MessageMeta(name="PydV2Like", version=1))
    data = env.to_json()
    assert data["payload"] == {"a": 2, "b": "y"}


def test_envelope_from_json_meta_defaults_to_payload_type_name_and_version_1() -> None:
    data = {"payload": {"x": 5, "y": "hi"}}
    rebuilt = Envelope.from_json(data, DCmd)

    assert rebuilt.meta.name == "DCmd"
    assert rebuilt.meta.version == 1
    assert rebuilt.meta.headers == {}
    assert rebuilt.payload == DCmd(5, "hi")
