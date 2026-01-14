import pytest

from lilya.contrib.cqrs.bus import CommandBus, QueryBus

pytestmark = pytest.mark.anyio


class CreateThing:
    def __init__(self, thing_id: str) -> None:
        self.thing_id = thing_id


class GetThing:
    def __init__(self, thing_id: str) -> None:
        self.thing_id = thing_id


async def test_command_then_query_with_shared_state() -> None:
    store: set[str] = set()

    async def auditing_mw(msg, nxt):
        # middleware sees both commands and queries when used on both buses
        return await nxt(msg)

    cmd_bus = CommandBus(middleware=[auditing_mw])
    qry_bus: QueryBus[bool] = QueryBus(middleware=[auditing_mw])

    async def handle_create(cmd: CreateThing) -> None:
        store.add(cmd.thing_id)

    def handle_get(q: GetThing) -> bool:
        return q.thing_id in store

    cmd_bus.register(CreateThing, handle_create)
    qry_bus.register(GetThing, handle_get)

    assert await qry_bus.ask(GetThing("a")) is False
    await cmd_bus.dispatch(CreateThing("a"))
    assert await qry_bus.ask(GetThing("a")) is True
