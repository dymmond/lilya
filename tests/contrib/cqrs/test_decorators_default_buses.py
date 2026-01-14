import pytest

from lilya.contrib.cqrs.bus import CommandBus, QueryBus
from lilya.contrib.cqrs.decorators import (
    command,
    default_command_bus,
    default_query_bus,
    query,
)
from lilya.contrib.cqrs.registry import HandlerRegistry

pytestmark = pytest.mark.anyio


class CmdX:
    def __init__(self, value: str) -> None:
        self.value = value


class QryX:
    def __init__(self, value: str) -> None:
        self.value = value


@pytest.fixture(autouse=True)
def reset_default_buses() -> None:
    """
    Important: decorators use module-level singletons.
    Reset their registries between tests to avoid cross-test leakage.
    """
    # Reach into internals safely for tests
    default_command_bus._registry = HandlerRegistry()  # type: ignore[attr-defined]
    default_query_bus._registry = HandlerRegistry()  # type: ignore[attr-defined]


async def test_command_handler_decorator_registers_on_default_bus() -> None:
    state: dict[str, str] = {}

    @command(CmdX)
    def handle(cmd: CmdX) -> None:
        state["v"] = cmd.value

    await default_command_bus.dispatch(CmdX("ok"))

    assert state["v"] == "ok"


async def test_query_handler_decorator_registers_on_default_bus() -> None:
    @query(QryX)
    async def handle(q: QryX) -> str:
        return f"hello:{q.value}"

    res = await default_query_bus.ask(QryX("world"))

    assert res == "hello:world"


async def test_decorators_can_target_custom_bus_instances() -> None:
    cmd_bus = CommandBus()
    qry_bus: QueryBus[str] = QueryBus()

    state: dict[str, str] = {}

    @command(CmdX, bus=cmd_bus)
    def handle_cmd(cmd: CmdX) -> None:
        state["v"] = cmd.value

    @query(QryX, bus=qry_bus)
    def handle_qry(q: QryX) -> str:
        return f"v={q.value}"

    await cmd_bus.dispatch(CmdX("abc"))

    assert state["v"] == "abc"

    res = await qry_bus.ask(QryX("123"))

    assert res == "v=123"
