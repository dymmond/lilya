from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import unquote

from lilya.logging import logger

from .exceptions import MultipartParseError, QuerystringParseError

Callback = Callable[..., Any]
CallbackName = str


# ---------------------------------------------------------------------
# Base Parser
# ---------------------------------------------------------------------


class BaseParser:
    """
    Common base class for streaming parsers.

    Provides callback plumbing so subclasses only need to implement
    ``write()``, ``finalize()``, and optional ``close()``.

    Callback styles supported:
        - Notification callbacks: ``on_event()`` (no args).
        - Data callbacks: ``on_event(data, start, end)`` where
          ``data[start:end]`` is the slice of interest.
    """

    def __init__(self) -> None:
        self.logger = logger
        self.callbacks: dict[str, Callback] = {}

    def callback(
        self,
        name: CallbackName,
        data: bytes | None = None,
        start: int | None = None,
        end: int | None = None,
    ) -> None:
        """
        Dispatch a callback by name.

        Args:
            name: Base event name (e.g. ``"field_data"``).
            data: Optional bytes buffer to pass.
            start: Start index into the buffer.
            end: End index into the buffer.
        """
        callback_name = "on_" + name
        func = self.callbacks.get(callback_name)
        if func is None:
            return

        if data is not None:
            if start is not None and start == end:
                return
            self.logger.debug("Calling %s with data[%s:%s]", callback_name, start, end)
            func(data, start, end)
        else:
            self.logger.debug("Calling %s with no data", callback_name)
            func()

    def set_callback(self, name: CallbackName, new_func: Callback | None) -> None:
        """
        Register or unregister a callback.

        Args:
            name: Base name (e.g. ``"field_data"``).
            new_func: Callable to register, or None to unregister.
        """
        if new_func is None:
            self.callbacks.pop("on_" + name, None)
        else:
            self.callbacks["on_" + name] = new_func

    # To be implemented by subclasses
    def write(self, data: bytes) -> int:  # pragma: no cover
        """Feed data into the parser."""
        return 0

    def finalize(self) -> None:  # pragma: no cover
        """Finalize the parse (flush remaining state)."""
        pass

    def close(self) -> None:  # pragma: no cover
        """Close the parser and release resources."""
        pass

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}()"


# ---------------------------------------------------------------------
# Octet Stream Parser
# ---------------------------------------------------------------------


class OctetStreamParser(BaseParser):
    """
    Streaming parser for ``application/octet-stream``.

    Callbacks:
        - ``on_start()``
        - ``on_data(data, start, end)``
        - ``on_end()``
    """

    def __init__(self, *, max_size: float = float("inf")) -> None:
        super().__init__()
        if not isinstance(max_size, (int, float)) or max_size < 1:
            raise ValueError("max_size must be a positive number")
        self._max_size = max_size
        self._consumed_size = 0
        self._started = False

    def write(self, data: bytes) -> int:
        """Consume a chunk of octet-stream data."""
        if not data:
            return 0
        if not self._started:
            self.callback("start")
            self._started = True
        num_bytes = len(data)
        if self._consumed_size + num_bytes > self._max_size:
            num_bytes = int(self._max_size - self._consumed_size)
        if num_bytes <= 0:
            return 0
        self._consumed_size += num_bytes
        self.callback("data", data, 0, num_bytes)
        return num_bytes

    def finalize(self) -> None:
        """Emit ``on_end()`` when parsing completes."""
        self.callback("end")


# ---------------------------------------------------------------------
# Querystring / x-www-form-urlencoded Parser
# ---------------------------------------------------------------------


class QuerystringParser(BaseParser):
    """
    Streaming parser for ``application/x-www-form-urlencoded`` and query strings.

    Callbacks:
        - ``on_field_start()``
        - ``on_field_name(data, start, end)``
        - ``on_field_data(data, start, end)``
        - ``on_field_end()``
        - ``on_end()``
    """

    def __init__(self, *, strict_parsing: bool = False, max_size: float = float("inf")) -> None:
        super().__init__()
        if not isinstance(max_size, (int, float)) or max_size < 1:
            raise ValueError("max_size must be a positive number")
        self._strict = strict_parsing
        self._max_size = max_size
        self._consumed_size = 0
        self._buffer = bytearray()
        self._field_buffer = bytearray()
        self._current_name: str | None = None

    def _flush_field(self) -> None:
        """Emit callbacks for the currently buffered key/value pair."""
        self.callback("field_start")
        if self._current_name is not None:
            name_bytes = self._current_name.encode("utf-8")
            self.callback("field_name", name_bytes, 0, len(name_bytes))
        data = bytes(self._field_buffer)
        if data:
            self.callback("field_data", data, 0, len(data))
        self.callback("field_end")
        self._field_buffer.clear()
        self._current_name = None

    def write(self, data: bytes) -> int:
        """Consume a chunk of urlencoded/querystring data."""
        if not data:
            return 0
        num_bytes = len(data)
        if self._consumed_size + num_bytes > self._max_size:
            num_bytes = int(self._max_size - self._consumed_size)
        if num_bytes <= 0:
            return 0
        self._consumed_size += num_bytes
        self._buffer += data[:num_bytes]

        index = 0
        while index < len(self._buffer):
            byte = self._buffer[index]
            if byte == 38:  # '&'
                raw = bytes(self._buffer[:index])
                self._buffer = self._buffer[index + 1 :]
                key, eq, val = raw.partition(b"=")
                if not eq and self._strict:
                    raise QuerystringParseError("strict_parsing: missing '=' in field")
                self._current_name = unquote(key.decode("utf-8", "replace"))
                self._field_buffer[:] = unquote(val.decode("utf-8", "replace")).encode("utf-8")
                self._flush_field()
                index = 0
                continue
            index += 1
        return num_bytes

    def finalize(self) -> None:
        """Flush the final field and emit ``on_end()``."""
        if self._buffer:
            raw = bytes(self._buffer)
            key, eq, val = raw.partition(b"=")
            if not eq and self._strict:
                raise QuerystringParseError("strict_parsing: missing '=' in field")
            self._current_name = unquote(key.decode("utf-8", "replace"))
            self._field_buffer[:] = unquote(val.decode("utf-8", "replace")).encode("utf-8")
            self._flush_field()
        self.callback("end")


# ---------------------------------------------------------------------
# Multipart Parser
# ---------------------------------------------------------------------


class MultipartParser(BaseParser):
    """
    Streaming parser for ``multipart/form-data``.

    Callbacks:
        - ``on_part_begin()``
        - ``on_header_begin()``
        - ``on_header_field(data, start, end)``
        - ``on_header_value(data, start, end)``
        - ``on_header_end()``
        - ``on_headers_finished()``
        - ``on_part_data(data, start, end)``
        - ``on_part_end()``
        - ``on_end()``
    """

    CRLF = b"\r\n"

    def __init__(self, boundary: bytes, *, max_size: float = float("inf")) -> None:
        super().__init__()
        if not boundary:
            raise MultipartParseError("Boundary required")
        if not isinstance(max_size, (int, float)) or max_size < 1:
            raise ValueError("max_size must be a positive number")

        self._boundary = b"--" + boundary
        self._terminal_boundary = self._boundary + b"--"
        self._max_size = max_size
        self._consumed_size = 0
        self._buffer = bytearray()
        self._started = False
        self._in_headers = False
        self._headers: dict[str, str] = {}

    def _emit_headers(self) -> None:
        """Emit callbacks for all collected headers."""
        for key, value in self._headers.items():
            self.callback("header_begin")
            key_bytes = key.encode("latin-1")
            value_bytes = value.encode("latin-1")
            self.callback("header_field", key_bytes, 0, len(key_bytes))
            self.callback("header_value", value_bytes, 0, len(value_bytes))
            self.callback("header_end")
        self.callback("headers_finished")

    def write(self, data: bytes) -> int:
        """Consume a chunk of multipart body data."""
        if not data:
            return 0
        num_bytes = len(data)
        if self._consumed_size + num_bytes > self._max_size:
            num_bytes = int(self._max_size - self._consumed_size)
        if num_bytes <= 0:
            return 0
        self._consumed_size += num_bytes
        self._buffer += data[:num_bytes]

        # Initial boundary search
        while not self._started:
            index = self._buffer.find(self.CRLF)
            if index == -1:
                return num_bytes
            line = bytes(self._buffer[: index + 2])
            del self._buffer[: index + 2]
            if line.startswith(self._boundary):
                if line.startswith(self._terminal_boundary):
                    self.callback("end")
                    return num_bytes
                self._started = True
                self._in_headers = True
                self.callback("part_begin")
                break

        # Main parsing loop
        while True:
            if self._in_headers:
                index = self._buffer.find(self.CRLF)
                if index == -1:
                    return num_bytes
                line = bytes(self._buffer[: index + 2])
                del self._buffer[: index + 2]
                if line == self.CRLF:
                    self._emit_headers()
                    self._in_headers = False
                else:
                    try:
                        name, val = line.decode("latin-1").split(":", 1)
                    except ValueError:
                        raise MultipartParseError("Invalid header line") from None
                    self._headers[name.strip().lower()] = val.strip()
                continue

            # Body mode
            boundary_index = self._buffer.find(self.CRLF + self._boundary)
            if boundary_index == -1:
                if self._buffer:
                    self.callback("part_data", bytes(self._buffer), 0, len(self._buffer))
                    self._buffer.clear()
                return num_bytes

            if boundary_index:
                self.callback("part_data", bytes(self._buffer[:boundary_index]), 0, boundary_index)
            del self._buffer[: boundary_index + 2]

            if self._buffer.startswith(self._terminal_boundary):
                self.callback("part_end")
                del self._buffer[: len(self._terminal_boundary)]
                if self._buffer.startswith(self.CRLF):
                    del self._buffer[:2]
                self.callback("end")
                return num_bytes

            if self._buffer.startswith(self._boundary):
                self.callback("part_end")
                del self._buffer[: len(self._boundary)]
                if self._buffer.startswith(self.CRLF):
                    del self._buffer[:2]
                self._headers.clear()
                self._in_headers = True
                self.callback("part_begin")
                continue

    def finalize(self) -> None:
        """Flush any remaining buffered body data and clear state."""
        if self._buffer:
            self.callback("part_data", bytes(self._buffer), 0, len(self._buffer))
            self._buffer.clear()
