import pytest

from lilya.contrib.cqrs.exceptions import HandlerAlreadyRegistered, HandlerNotFound
from lilya.contrib.cqrs.registry import HandlerRegistry


class MsgA: ...


class MsgB: ...


def handler_a(_: MsgA) -> None:
    return None


def handler_b(_: MsgB) -> None:
    return None


def test_registry_register_and_get() -> None:
    reg = HandlerRegistry()
    reg.register(MsgA, handler_a)

    got = reg.get(MsgA)

    assert got is handler_a
    assert MsgA in reg
    assert MsgB not in reg


def test_registry_register_duplicate_raises() -> None:
    reg = HandlerRegistry()
    reg.register(MsgA, handler_a)

    with pytest.raises(HandlerAlreadyRegistered):
        reg.register(MsgA, handler_b)


def test_registry_get_missing_raises() -> None:
    reg = HandlerRegistry()

    with pytest.raises(HandlerNotFound):
        reg.get(MsgA)


def test_registry_clear() -> None:
    reg = HandlerRegistry()
    reg.register(MsgA, handler_a)

    assert MsgA in reg

    reg.clear()

    assert MsgA not in reg

    with pytest.raises(HandlerNotFound):
        reg.get(MsgA)
