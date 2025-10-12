from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncGenerator, Iterable
from dataclasses import dataclass
from typing import Any

import anyio
from anyio import ClosedResourceError, EndOfStream
from anyio.abc import ObjectReceiveStream, ObjectSendStream

# Define the type for the dictionary format expected by the channel/listener streams
Eventdict = dict[str, Any]

# Define the exact stream type used internally
ChannelSendStream = ObjectSendStream[Eventdict]
ChannelReceiveStream = ObjectReceiveStream[Eventdict]


@dataclass(slots=True)
class SSEMessage:
    """
    A typed structure for representing a single Server-Sent Event (SSE) message.
    The fields map directly to the SSE wire protocol format.
    """

    data: Any
    event: str | None = None
    id: str | None = None
    retry: int | None = None

    def to_wire(self) -> str:
        """
        Converts the SSEMessage instance into its string representation conforming
        to the SSE wire protocol (i.e., lines prefixed with field names and terminated
        by a double newline `\n\n`).

        Returns:
            The fully formatted SSE string chunk ready for transmission.
        """
        lines: list[str] = []
        if self.event:
            lines.append(f"event: {self.event}")
        if self.id:
            lines.append(f"id: {self.id}")
        if self.retry is not None:
            # The 'retry' field must be an integer, typically representing milliseconds
            lines.append(f"retry: {int(self.retry)}")

        # Data serialization: must handle multiline strings and non-string types
        payload: Any = self.data
        if not isinstance(payload, str):
            # Non-string data is automatically serialized to a compact JSON string
            payload = json.dumps(payload, separators=(",", ":"))

        # The 'data' field can contain multiple lines, each prefixed with 'data: '
        for line in str(payload).splitlines() or [""]:
            lines.append(f"data: {line}")

        # Join lines and ensure the final terminating blank line
        return "".join(ln + "\n" for ln in lines) + "\n"


class SSEChannel:
    """
    An asynchronous publish/subscribe channel for managing Server-Sent Events.

    This channel uses `anyio` memory streams to fan-out messages to multiple listeners.
    It manages the lifecycle of these streams, including cleanup of disconnected subscribers,
    and supports automatic heartbeat logic driven by receive timeouts.
    """

    def __init__(self, name: str) -> None:
        """
        Initializes the SSE Channel.

        Args:
            name: A unique identifier for the channel (e.g., "global_updates").
        """
        self.name: str = name
        # set of send streams for all currently active subscribers.
        # The stream type is Eventdict, reflecting the internal data format.
        self._subscribers: set[ChannelSendStream] = set()
        # Lock to ensure thread-safe access to the _subscribers set
        self._lock: anyio.Lock = anyio.Lock()

    async def broadcast(self, message: str | dict[str, Any] | SSEMessage) -> None:
        """
        Broadcasts a message to all currently subscribed listeners.

        The message is first normalized into an `Eventdict` before being sent over
        the memory streams. Disconnected subscribers are automatically removed and closed.

        Args:
            message: The content to broadcast.
                     - str: Treated as the 'data' payload with 'event' set to "message".
                     - dict: Normalized to ensure 'event' and 'data' keys are handled.
                     - SSEMessage: Converted to a dictionary representation.
        """
        msg_dict: Eventdict

        if isinstance(message, SSEMessage):
            # Convert typed message to a dict for stream transmission
            msg_dict = {
                "id": message.id,
                "event": message.event,
                "data": message.data,
                "retry": message.retry,
            }
            # Remove None fields before sending
            msg_dict = {k: v for k, v in msg_dict.items() if v is not None}
        elif isinstance(message, str):
            # Plain string defaults to 'message' event
            msg_dict = {"event": "message", "data": message}
        elif isinstance(message, dict):
            # Normalize dicts to ensure an 'event' key is present
            msg_dict = {
                "event": message.get("event", "message"),
                "data": message.get("data"),
                **{k: v for k, v in message.items() if k not in ("event", "data")},
            }
        else:
            raise TypeError(f"Unsupported message type: {type(message)}")

        async with self._lock:
            dead: list[ChannelSendStream] = []
            # Iterate over a copy to allow safe mutation of the main set outside the loop
            for q in list(self._subscribers):
                try:
                    await q.send(msg_dict)
                except (BrokenPipeError, ClosedResourceError, EndOfStream):
                    # Connection error: mark subscriber for removal
                    dead.append(q)

            # Cleanup disconnected subscribers
            for q in dead:
                self._subscribers.discard(q)
                with anyio.move_on_after(0):
                    await q.aclose()

    async def listen(
        self,
        *,
        heartbeat_interval: float | None = 15.0,
    ) -> AsyncGenerator[Eventdict, None]:
        """
        Subscribes a client to the channel, returning an asynchronous generator
        that yields `Eventdict` messages compatible with `EventStreamResponse`.

        This method implements heartbeats by using a receive timeout, which avoids
        spawning separate background tasks (nurseries) for simpler resource management.

        Args:
            heartbeat_interval: The interval in seconds for sending a synthetic
                                heartbeat event if no data is received. set to `None`
                                to disable heartbeats. Defaults to 15.0s.

        Yields:
            Eventdict: dictionary containing the SSE fields (e.g., {"event": "update", "data": ...}).
        """
        # Create a zero-buffer memory stream for the current subscriber
        send_stream: ChannelSendStream
        recv_stream: ChannelReceiveStream
        send_stream, recv_stream = anyio.create_memory_object_stream[Eventdict](max_buffer_size=0)

        # Register the subscriber's send stream. Note: Lock isn't used here but is crucial
        # in the original code's design for safety when removing streams in `broadcast`.
        self._subscribers.add(send_stream)

        try:
            # Handle the case where no heartbeats are needed (simple forwarding)
            if heartbeat_interval is None:
                async with recv_stream:
                    async for item in recv_stream:
                        yield item
                return

            # Handle heartbeats via receive timeout
            async with recv_stream:
                while True:
                    try:
                        # Wait up to heartbeat_interval for a message
                        with anyio.move_on_after(heartbeat_interval) as scope:
                            item = await recv_stream.receive()

                        if scope.cancelled_caught:
                            # Timeout occurred: emit a heartbeat event
                            yield {"event": "heartbeat", "data": "💓"}
                        else:
                            # Message received: yield the actual message
                            yield item

                    except (EndOfStream, ClosedResourceError, BrokenPipeError):
                        # Exit the loop on connection/stream errors
                        break

        finally:
            # Cleanup logic executed upon generator exit or cancellation
            self._subscribers.discard(send_stream)
            # Suppress exceptions during final close operations
            with contextlib.suppress(Exception):
                await send_stream.aclose()
                await recv_stream.aclose()


async def _stream_recv(
    recv: ChannelReceiveStream,
) -> AsyncGenerator[Eventdict, None]:
    """
    Internal helper to asynchronously iterate over an object stream and handle disconnection errors.

    Args:
        recv: The receive stream of the memory channel.

    Yields:
        Eventdict: Messages received from the stream.
    """
    try:
        # The async with statement handles closing the stream on successful iteration completion
        async with recv:
            async for item in recv:
                yield item
    except (BrokenPipeError, ClosedResourceError, EndOfStream):  # pragma: no cover
        # Catch expected stream termination errors and exit gracefully
        return


class SSEChannelManager:
    """
    A thread-safe, concurrent registry that manages and provides access to multiple
    named `SSEChannel` instances.

    The manager ensures that only one instance exists per name and uses a lock to
    guarantee safe access across concurrent operations. Channels live in the registry
    until explicitly cleared.
    """

    def __init__(self) -> None:
        """
        Initializes the manager with an empty dictionary for channels and an `anyio.Lock`.
        """
        self._channels: dict[str, SSEChannel] = {}
        self._lock: anyio.Lock = anyio.Lock()

    async def get_or_create(self, name: str) -> SSEChannel:
        """
        Retrieves an existing channel by name or creates a new one if it doesn't exist.

        Args:
            name: The unique name of the channel to retrieve or create.

        Returns:
            The requested `SSEChannel` instance.
        """
        async with self._lock:
            ch: SSEChannel | None = self._channels.get(name)
            if ch is None:
                ch = SSEChannel(name)
                self._channels[name] = ch
            return ch

    async def get_many(self, names: Iterable[str]) -> list[SSEChannel]:
        """
        Retrieves or creates multiple channels specified by a list of names.

        This method leverages `get_or_create` for each name, ensuring thread-safety
        for each retrieval/creation.

        Args:
            names: An iterable of channel names (strings).

        Returns:
            A list of corresponding `SSEChannel` instances.
        """
        return [await self.get_or_create(n) for n in names]

    async def clear(self) -> None:
        """
        Clears all channel instances from the registry.

        This method frees the manager's memory used to store channels. Note that it
        does **not** forcibly disconnect any existing subscribers; those streams will
        eventually be closed when the application shuts down or the clients disconnect.
        """
        async with self._lock:
            self._channels.clear()

    async def list_channels(self) -> list[str]:
        """Return a list of active channel names."""
        return list(self._channels.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._channels


# Default global manager instance. It can be used directly or injected via DI.
sse_manager: SSEChannelManager = SSEChannelManager()
