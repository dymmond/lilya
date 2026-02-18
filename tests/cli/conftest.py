import asyncio
import warnings
from collections.abc import Generator

import pytest
from sayer.testing import SayerTestClient

from lilya.cli.cli import lilya_cli


@pytest.fixture(scope="module")
def anyio_backend():
    return ("asyncio", {"debug": True})


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    """Fixture to provide a test client for the Lilya CLI."""
    warnings.filterwarnings(
        "ignore",
        message=".*protected_args.*",
        category=DeprecationWarning,
        module="sayer.*",
    )
    return SayerTestClient(lilya_cli)
