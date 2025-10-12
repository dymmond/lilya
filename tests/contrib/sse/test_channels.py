import anyio
import pytest

from lilya.apps import Lilya
from lilya.contrib.sse.channels import SSEChannel, SSEChannelManager, sse_manager
from lilya.responses import EventStreamResponse
from lilya.routing import Path
from lilya.testclient import TestClient

pytestmark = pytest.mark.anyio


async def test_broadcast_reaches_single_listener():
    """
    When a message is broadcast, an active listener receives it as a dict event.
    """
    channel = SSEChannel("demo")

    async def listener():
        async for msg in channel.listen(heartbeat_interval=None):
            assert isinstance(msg, dict)
            assert msg["event"] == "ping"
            assert msg["data"] == {"msg": "hello"}
            break

    async with anyio.create_task_group() as tg:
        tg.start_soon(listener)
        await anyio.sleep(0.01)
        await channel.broadcast({"event": "ping", "data": {"msg": "hello"}})
        tg.cancel_scope.cancel()


async def test_multiple_subscribers_receive_same_message():
    """
    Multiple subscribers should all receive the same event.
    """
    channel = SSEChannel("shared")
    received = []

    async def listener(name):
        async for msg in channel.listen(heartbeat_interval=None):
            received.append((name, msg))
            break

    async with anyio.create_task_group() as tg:
        tg.start_soon(listener, "A")
        tg.start_soon(listener, "B")
        await anyio.sleep(0.01)
        await channel.broadcast({"event": "update", "data": 1})
        tg.cancel_scope.cancel()

    assert len(received) == 2

    events = [m for _, m in received]

    assert all(m["event"] == "update" for m in events)
    assert all(m["data"] == 1 for m in events)


async def test_broadcast_accepts_ssemessage_and_str():
    """
    Broadcast() should accept both SSEMessage and string inputs.
    """
    from lilya.contrib.sse.channels import SSEMessage

    ch = SSEChannel("mixed")

    messages = []

    async def listener():
        async for ev in ch.listen(heartbeat_interval=None):
            messages.append(ev)
            if len(messages) == 3:
                break

    async with anyio.create_task_group() as tg:
        tg.start_soon(listener)
        await anyio.sleep(0.01)
        await ch.broadcast(SSEMessage(data={"a": 1}, event="msg"))
        await ch.broadcast("hello world")
        await ch.broadcast({"event": "custom", "data": 5})
        tg.cancel_scope.cancel()

    # verify all types produced valid dicts
    assert any(ev["event"] == "msg" for ev in messages)
    assert any(ev["data"] == "hello world" for ev in messages)
    assert any(ev["event"] == "custom" for ev in messages)


async def test_heartbeat_sends_periodic_events():
    """
    Heartbeats should arrive as dicts with event='heartbeat'.
    """
    ch = SSEChannel("heartbeat")
    heartbeats = 0

    async with anyio.create_task_group() as tg:

        async def listener():
            nonlocal heartbeats
            async for msg in ch.listen(heartbeat_interval=0.05):
                if msg["event"] == "heartbeat":
                    heartbeats += 1
                    if heartbeats >= 3:
                        break

        tg.start_soon(listener)
        await anyio.sleep(0.2)
        tg.cancel_scope.cancel()

    assert heartbeats >= 2


async def test_cleanup_removes_disconnected_subscribers():
    """
    Ensure disconnected subscribers are removed cleanly.
    """
    ch = SSEChannel("cleanup")

    async def subscriber():
        async for _ in ch.listen(heartbeat_interval=None):
            break

    async with anyio.create_task_group() as tg:
        tg.start_soon(subscriber)
        # Give listener time to register
        await anyio.sleep(0.05)

        # Broadcast something to unblock listener
        await ch.broadcast({"event": "ping", "data": "ok"})

        # Give the listener time to consume and exit
        await anyio.sleep(0.05)

        # Manually trigger cleanup if it's an explicit method
        if hasattr(ch, "cleanup"):
            await ch.cleanup()

    # At this point the subscriber should have been removed
    assert len(ch._subscribers) == 0


async def test_manager_get_or_create_returns_same_instance():
    manager = SSEChannelManager()
    a = await manager.get_or_create("x")
    b = await manager.get_or_create("x")
    c = await manager.get_or_create("y")

    assert a is b
    assert a is not c
    assert set(manager._channels.keys()) == {"x", "y"}


async def test_manager_clear_removes_channels():
    manager = SSEChannelManager()
    await manager.get_or_create("demo")
    await manager.get_or_create("news")
    await manager.clear()
    assert manager._channels == {}


def test_eventstreamresponse_integration(monkeypatch):
    async def endpoint():
        channel = await sse_manager.get_or_create("integration")

        async def stream():
            async with anyio.create_task_group() as tg:
                # send after listener is attached
                async def send_later():
                    await anyio.sleep(0)  # let listen() start
                    await channel.broadcast({"event": "notice", "data": "ok"})

                tg.start_soon(send_later)

                async for ev in channel.listen(heartbeat_interval=None):
                    yield ev
                    break  # only one event

        return EventStreamResponse(stream())

    app = Lilya(routes=[Path("/events", endpoint)])
    client = TestClient(app)

    # Use the streaming context so the connection is closed cleanly
    with client.stream("GET", "/events") as resp:
        # read just one chunk so we don’t hang
        chunk = next(resp.iter_bytes())
        text = chunk.decode()

    assert "event: notice" in text
    assert "data: ok" in text
    assert "text/event-stream" in resp.headers["content-type"]


def test_broadcast_reaches_client_stream(tmp_path):
    """
    Spin up a mini Lilya app and confirm the /send endpoint broadcasts
    events that the /events endpoint yields to the client.
    """

    async def events_endpoint():
        ch = await sse_manager.get_or_create("demo")

        async def stream():
            # Spawn a background task that sends a message shortly after listen() starts
            async with anyio.create_task_group() as tg:

                async def send_later():
                    await anyio.sleep(0.05)
                    await ch.broadcast({"event": "notice", "data": "works"})

                tg.start_soon(send_later)

                async for ev in ch.listen(heartbeat_interval=None):
                    yield ev
                    break  # only yield one event

        return EventStreamResponse(stream())

    app = Lilya(routes=[Path("/events", events_endpoint)])
    client = TestClient(app)

    with client.stream("GET", "/events") as resp:
        # read a single SSE event from the stream
        chunk = next(resp.iter_bytes())
        text = chunk.decode()

    assert "event: notice" in text
    assert "data: works" in text
    assert "text/event-stream" in resp.headers["content-type"]
