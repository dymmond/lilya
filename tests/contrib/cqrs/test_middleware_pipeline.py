import pytest

from lilya.contrib.cqrs.bus import CommandBus, QueryBus

pytestmark = pytest.mark.anyio


class Cmd:
    def __init__(self, value: int) -> None:
        self.value = value


class Qry:
    def __init__(self, value: int) -> None:
        self.value = value


async def test_middleware_runs_in_order_and_wraps_command() -> None:
    calls: list[str] = []

    async def mw1(msg, nxt):
        calls.append("mw1:before")
        res = await nxt(msg)
        calls.append("mw1:after")
        return res

    async def mw2(msg, nxt):
        calls.append("mw2:before")
        res = await nxt(msg)
        calls.append("mw2:after")
        return res

    def handler(cmd: Cmd) -> None:
        calls.append(f"handler:{cmd.value}")

    bus = CommandBus(middleware=[mw1, mw2])
    bus.register(Cmd, handler)

    await bus.dispatch(Cmd(7))

    assert calls == [
        "mw1:before",
        "mw2:before",
        "handler:7",
        "mw2:after",
        "mw1:after",
    ]


async def test_middleware_can_mutate_message_for_handler() -> None:
    calls: list[str] = []

    async def bump(msg: Cmd, nxt):
        msg.value += 1
        return await nxt(msg)

    def handler(cmd: Cmd) -> None:
        calls.append(f"handler:{cmd.value}")

    bus = CommandBus(middleware=[bump])
    bus.register(Cmd, handler)

    await bus.dispatch(Cmd(1))

    assert calls == ["handler:2"]


async def test_middleware_can_short_circuit_query() -> None:
    calls: list[str] = []

    async def short_circuit(msg: Qry, nxt):
        calls.append("mw:short")
        if msg.value == 0:
            return "cached"
        return await nxt(msg)

    async def handler(q: Qry) -> str:
        calls.append(f"handler:{q.value}")
        return f"db:{q.value}"

    bus: QueryBus[str] = QueryBus(middleware=[short_circuit])
    bus.register(Qry, handler)

    res1 = await bus.ask(Qry(0))
    res2 = await bus.ask(Qry(5))

    assert res1 == "cached"
    assert res2 == "db:5"
    assert calls == ["mw:short", "mw:short", "handler:5"]


async def test_middleware_exception_bubbles() -> None:
    async def mw_raise(msg, nxt):
        raise RuntimeError("mw boom")

    def handler(_: Cmd) -> None:
        return None

    bus = CommandBus(middleware=[mw_raise])
    bus.register(Cmd, handler)

    with pytest.raises(RuntimeError, match="mw boom"):
        await bus.dispatch(Cmd(1))
