from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import msgspec
import pytest
from attrs import asdict, has
from msgspec import Struct

from lilya.encoders import Encoder, register_encoder
from lilya.testclient import TestClient


@pytest.fixture
def test_client_factory(anyio_backend_name, anyio_backend_options):
    return functools.partial(
        TestClient,
        backend=anyio_backend_name,
        backend_options=anyio_backend_options,
    )


class MsgSpecEncoder(Encoder):
    __type__ = Struct

    def serialize(self, obj: Any) -> Any:
        return msgspec.json.decode(msgspec.json.encode(obj))

    def encode(
        self,
        structure: Any,
        obj: Any,
    ) -> Any:
        return msgspec.json.decode(msgspec.json.encode(obj), type=structure)


register_encoder(MsgSpecEncoder())


class AttrsEncoder(Encoder):
    def is_type(self, value: Any) -> bool:
        return has(value)

    def serialize(self, obj: Any) -> Any:
        return asdict(obj)


register_encoder(AttrsEncoder())


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    tests_root = Path(__file__).resolve().parent
    cli_root = tests_root / "cli"
    benchmarks_root = tests_root / "benchmarks"

    for item in items:
        path = Path(str(item.path)).resolve()

        if _is_relative_to(path, cli_root):
            item.add_marker(pytest.mark.cli)

        if _is_relative_to(path, benchmarks_root):
            item.add_marker(pytest.mark.slow)

        if "/integration/" in path.as_posix() or _is_relative_to(path, tests_root / "caches"):
            item.add_marker(pytest.mark.integration)

        if path == tests_root / "test_observable.py":
            item.add_marker(pytest.mark.serial)
