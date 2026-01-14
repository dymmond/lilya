import pytest
from pydantic import BaseModel

from lilya.contrib.cqrs import (
    Envelope,
    MessageMeta,
    command,
    query,
)
from lilya.contrib.cqrs.decorators import default_command_bus, default_query_bus

pytestmark = pytest.mark.anyio


class AddUser(BaseModel):
    email: str


class GetGreeting(BaseModel):
    name: str


TEST_STATE = {}


@command(AddUser)
def _handle_add_user(cmd: AddUser) -> None:
    TEST_STATE["email"] = cmd.email


@query(GetGreeting)
async def _handle_get_greeting(q: GetGreeting) -> str:
    return f"Hello {q.name}"


async def test_command_and_query():
    await default_command_bus.dispatch(AddUser(email="x@y.com"))
    assert TEST_STATE["email"] == "x@y.com"

    res = await default_query_bus.ask(GetGreeting(name="Tiago"))
    assert res == "Hello Tiago"


def test_envelope_roundtrip():
    env = Envelope(payload=AddUser(email="a@b.com"), meta=MessageMeta(name="AddUser", version=2))

    data = env.to_json()
    again = Envelope.from_json(data, AddUser)

    assert again.meta.version == 2
    assert again.payload.email == "a@b.com"
