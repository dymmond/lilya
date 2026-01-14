# Server-Sent Events (SSE) Channels

Real-time applications often need to push updates from the server to connected clients, for example,
live dashboards, notification systems, or background job progress.

**SSE Channels** in Lilya provide a clean, async-native abstraction for this using the standard
**Server-Sent Events** protocol (`text/event-stream`).

### What Are SSE Channels?

`SSEChannel` lets you create a named, in-memory channel where multiple subscribers can listen for new events while
the server broadcasts messages asynchronously.

This pattern is lightweight, built on `anyio`, and integrates seamlessly
with Lilya's [EventStreamResponse](../responses.md#eventstreamresponse).

### Why Use SSE Channels?

| Problem                                          | SSE Channels Solution                      |
| ------------------------------------------------ | ------------------------------------------ |
| Need to send real-time updates without polling   | Persistent event stream over HTTP          |
| Need to broadcast to many clients                | Built-in fan-out via shared channel        |
| Want async support without WebSockets complexity | Simple async generators + HTTP             |
| Need automatic cleanup of disconnected clients   | Graceful unsubscribe and memory management |

## Basic Example

```python
from lilya.apps import Lilya
from lilya.routing import Path
from lilya.contrib.security.signed_urls import SignedURLGenerator
from lilya.contrib.sse.channels import SSEChannel, sse_manager
from lilya.responses import EventStreamResponse

# Create or get a named SSE channel
notifications = SSEChannel("notifications")

async def events():
    # Stream messages to connected clients
    async def stream():
        async for event in notifications.listen(heartbeat_interval=10):
            yield event

    return EventStreamResponse(stream())

async def send():
    # Broadcast to all connected clients
    await notifications.broadcast({"event": "notice", "data": "Hello, world!"})
    return {"sent": True}

app = Lilya(routes=[
    Path("/events", events),
    Path("/send", send),
])
```

✅ Open `/events` in your browser and then call `/send` in another tab, you will instantly see the message arrive.

## Understanding the Pieces

### 1. `SSEChannel`

The core class for managing subscribers and messages.

```python
from lilya.contrib.sse.channels import SSEChannel

ch = SSEChannel("demo")
await ch.broadcast({"event": "message", "data": "New update!"})
async for event in ch.listen():
    yield event
```

Each `SSEChannel` instance:

* Keeps a list of subscribers (`asyncio.Queue`s).
* Allows multiple concurrent listeners.
* Cleans up disconnected subscribers automatically.
* Optionally sends **heartbeat** events to keep the connection alive.

### 2. `EventStreamResponse`

A specialized response for streaming events in SSE format.

```python
from lilya.responses import EventStreamResponse

async def stream():
    for i in range(3):
        yield {"event": "tick", "data": i}

return EventStreamResponse(stream())
```

* Converts Python dicts into properly formatted SSE frames.
* Supports optional `retry`, `id`, and `event` fields.
* Encodes JSON automatically for dict/list `data`.

### 3. `sse_manager`

A global helper that manages multiple channels by name.

```python
from lilya.contrib.sse.channels import sse_manager

# Get or create a channel
ch = await sse_manager.get_or_create("chat")

# Retrieve existing channels
print(await sse_manager.list_channels())
```

This allows you to coordinate multiple named channels — e.g., one per topic or tenant.

## Practical Use Cases

### Live Notifications

```python
from lilya.apps import Lilya
from lilya.contrib.sse.channels import sse_manager

app = Lilya()

@app.get("/notify")
async def notify():
    ch = await sse_manager.get_or_create("user_notifications")
    await ch.broadcast({"event": "alert", "data": "You have a new message"})
    return {"status": "notified"}
```

Clients subscribe to `/events`, and your server pushes alerts as they happen.

### Real-Time Job Progress

```python
import anyio

from lilya.contrib.sse.channels import SSEChannel
from lilya.responses import EventStreamResponse

progress = SSEChannel("tasks")

async def run_job():
    for i in range(100):
        await progress.broadcast({"event": "progress", "data": i})
        await anyio.sleep(0.1)

@app.get("/job/status")
async def job_status():
    async def stream():
        async for event in progress.listen(heartbeat_interval=5):
            yield event
    return EventStreamResponse(stream())
```

### Multi-Channel Communication

You can dynamically create channels per user, tenant, or topic:

```python
from lilya.apps import Lilya
from lilya.contrib.sse.channels import sse_manager
from lilya.responses import EventStreamResponse

app = Lilya()

@app.get("/events/{room_id}")
async def room_events(room_id: str):
    room = await sse_manager.get_or_create(room_id)
    async def stream():
        async for ev in room.listen():
            yield ev
    return EventStreamResponse(stream())
```

## Advanced Features

### Heartbeats

To prevent idle connections from timing out, `listen()` can send heartbeat messages automatically:

```python
async for event in ch.listen(heartbeat_interval=10):
    yield event
```

This sends:

```
: heartbeat
\n\n
```

every 10 seconds.

### Automatic Cleanup

When a subscriber disconnects (e.g., browser tab closes), it's removed automatically.
You can manually trigger cleanup if needed:

```python
await ch.cleanup()
```

This ensures no stale connections remain.

### Thread & Async Safety

* Built on `anyio`, compatible with both `asyncio` and `trio`.
* Safe for concurrent broadcast and listen operations.
* Designed for long-lived event streams.

### Integration with Dependencies

Because channels are async and injectable, you can combine them with Lilya's dependency system:

```python
from lilya.apps import Lilya
from lilya.contrib.sse.channels import SSEChannel, sse_manager
from lilya.responses import EventStreamResponse
from lilya.dependencies import Depends, inject

@inject
async def get_channel() -> SSEChannel:
    return await sse_manager.get_or_create("chat")

@app.get("/stream")
async def stream(ch: SSEChannel = Depends(get_channel)):
    async def events():
        async for ev in ch.listen():
            yield ev
    return EventStreamResponse(events())
```

## Best Practices

| Tip                          | Description                                                      |
| ---------------------------- | ---------------------------------------------------------------- |
| **Use heartbeats**           | Prevents timeouts on long-lived connections.                     |
| **Keep payloads small**      | SSE is text-based; avoid heavy binary data.                      |
| **Avoid per-user channels**  | Use shared channels and filter on the client side when possible. |
| **Use `sse_manager`**        | Reuse channels across routes or events.                          |
| **Combine with async tasks** | Perfect for background jobs or progress updates.                 |

## Summary

| Concept               | Description                              |
| --------------------- | ---------------------------------------- |
| `SSEChannel`          | Handles subscriptions and broadcasting.  |
| `EventStreamResponse` | Converts async streams into SSE output.  |
| `sse_manager`         | Global manager for named channels.       |
| Heartbeats            | Keeps connections alive.                 |
| Auto-cleanup          | Removes stale subscribers automatically. |

SSE Channels make Lilya **a first-class framework for reactive, async-native real-time APIs**, without the overhead of WebSockets.
