import pytest

from lilya.contrib.cqrs.bus import CommandBus
from lilya.contrib.cqrs.exceptions import HandlerNotFound, InvalidMessage


class CreateUser:
    def __init__(self, email: str) -> None:
        self.email = email


pytestmark = pytest.mark.anyio


async def test_command_bus_dispatch_sync_handler() -> None:
    state: dict[str, str] = {}

    def handle(cmd: CreateUser) -> None:
        state["email"] = cmd.email

    bus = CommandBus()
    bus.register(CreateUser, handle)

    await bus.dispatch(CreateUser("a@b.com"))

    assert state["email"] == "a@b.com"


async def test_command_bus_dispatch_async_handler() -> None:
    state: dict[str, str] = {}

    async def handle(cmd: CreateUser) -> None:
        state["email"] = cmd.email

    bus = CommandBus()
    bus.register(CreateUser, handle)

    await bus.dispatch(CreateUser("x@y.com"))

    assert state["email"] == "x@y.com"


async def test_command_bus_missing_handler_raises() -> None:
    bus = CommandBus()

    with pytest.raises(HandlerNotFound):
        await bus.dispatch(CreateUser("no@handler"))


async def test_command_bus_none_message_raises() -> None:
    bus = CommandBus()

    with pytest.raises(InvalidMessage):
        await bus.dispatch(None)  # type: ignore[arg-type]


async def test_command_bus_handler_exception_bubbles() -> None:
    def handle(_: CreateUser) -> None:
        raise RuntimeError("boom")

    bus = CommandBus()
    bus.register(CreateUser, handle)

    with pytest.raises(RuntimeError, match="boom"):
        await bus.dispatch(CreateUser("a@b.com"))
