import anyio
import pytest

from lilya.contrib.cqrs.bus import CommandBus

pytestmark = pytest.mark.anyio


class Inc:
    def __init__(self, n: int) -> None:
        self.n = n


async def test_command_bus_concurrent_dispatches() -> None:
    bus = CommandBus()
    total = {"v": 0}

    async def handle(cmd: Inc) -> None:
        # simulate async work
        await anyio.sleep(0)
        total["v"] += cmd.n

    bus.register(Inc, handle)

    async with anyio.create_task_group() as tg:
        for _ in range(50):
            tg.start_soon(bus.dispatch, Inc(1))

    assert total["v"] == 50
