import pytest

from lilya.contrib.cqrs.bus import QueryBus
from lilya.contrib.cqrs.exceptions import HandlerNotFound, InvalidMessage

pytestmark = pytest.mark.anyio


class GetUserEmail:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id


async def test_query_bus_ask_sync_handler_returns_value() -> None:
    def handle(q: GetUserEmail) -> str:
        return f"{q.user_id}@example.com"

    bus: QueryBus[str] = QueryBus()
    bus.register(GetUserEmail, handle)

    res = await bus.ask(GetUserEmail("u1"))

    assert res == "u1@example.com"


async def test_query_bus_ask_async_handler_returns_value() -> None:
    async def handle(q: GetUserEmail) -> str:
        return f"{q.user_id}@example.com"

    bus: QueryBus[str] = QueryBus()
    bus.register(GetUserEmail, handle)

    res = await bus.ask(GetUserEmail("u2"))

    assert res == "u2@example.com"


async def test_query_bus_missing_handler_raises() -> None:
    bus: QueryBus[str] = QueryBus()
    with pytest.raises(HandlerNotFound):
        await bus.ask(GetUserEmail("u3"))


async def test_query_bus_none_message_raises() -> None:
    bus: QueryBus[str] = QueryBus()

    with pytest.raises(InvalidMessage):
        await bus.ask(None)  # type: ignore[arg-type]


async def test_query_bus_handler_exception_bubbles() -> None:
    def handle(_: GetUserEmail) -> str:
        raise ValueError("bad")

    bus: QueryBus[str] = QueryBus()
    bus.register(GetUserEmail, handle)

    with pytest.raises(ValueError, match="bad"):
        await bus.ask(GetUserEmail("u4"))
