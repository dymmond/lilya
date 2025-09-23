from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Dict, cast
from urllib.parse import unquote

from .exceptions import MultipartParseError, QuerystringParseError

Callback = Callable[..., Any]
CallbackName = str

logger = logging.getLogger(__name__)


class BaseParser:
    """Common callback plumbing used by all parsers.

    Two callback styles are supported:
      * notification callbacks: `on_foo()` (no args)
      * data callbacks:        `on_foo(data, start, end)` where `data[start:end]` is the slice of interest
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.callbacks: Dict[str, Callback] = {}

    def callback(self, name: CallbackName, data: bytes | None = None, start: int | None = None, end: int | None = None) -> None:
        on_name = "on_" + name
        func = self.callbacks.get(on_name)
        if func is None:
            return
        func = cast(Callable[..., Any], func)
        if data is not None:
            if start is not None and start == end:
                return
            self.logger.debug("Calling %s with data[%s:%s]", on_name, start, end)
            func(data, start, end)
        else:
            self.logger.debug("Calling %s with no data", on_name)
            func()

    def set_callback(self, name: CallbackName, new_func: Callback | None) -> None:
        if new_func is None:
            self.callbacks.pop("on_" + name, None)
        else:
            self.callbacks["on_" + name] = new_func

    # API completeness only – individual parsers implement these
    def write(self, data: bytes) -> int:  # pragma: no cover
        return 0

    def finalize(self) -> None:  # pragma: no cover
        pass

    def close(self) -> None:  # pragma: no cover
        pass

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}()"


class OctetStreamParser(BaseParser):
    """Streaming `application/octet-stream` parser.

    Callbacks:
      - on_start()
      - on_data(data, start, end)
      - on_end()
    """

    def __init__(self, *, max_size: float = float("inf")) -> None:
        super().__init__()
        if not isinstance(max_size, (int, float)) or max_size < 1:
            raise ValueError("max_size must be a positive number")
        self._max = max_size
        self._size = 0
        self._started = False

    def write(self, data: bytes) -> int:
        if not data:
            return 0
        if not self._started:
            self.callback("start")
            self._started = True
        n = len(data)
        if self._size + n > self._max:
            n = int(self._max - self._size)
        if n <= 0:
            return 0
        self._size += n
        self.callback("data", data, 0, n)
        return n

    def finalize(self) -> None:
        self.callback("end")


class QuerystringParser(BaseParser):
    """Streaming-ish parser for `application/x-www-form-urlencoded` and query strings.

    Callbacks:
      - on_field_start()
      - on_field_name(data, start, end)
      - on_field_data(data, start, end)
      - on_field_end()
      - on_end()
    """

    def __init__(self, *, strict_parsing: bool = False, max_size: float = float("inf")) -> None:
        super().__init__()
        if not isinstance(max_size, (int, float)) or max_size < 1:
            raise ValueError("max_size must be a positive number")
        self._strict = strict_parsing
        self._max = max_size
        self._size = 0
        self._buf = bytearray()
        self._field_buf = bytearray()
        self._name: str | None = None

    def _flush_field(self) -> None:
        # emit buffered pair
        self.callback("field_start")
        if self._name is not None:
            name_bytes = self._name.encode("utf-8")
            self.callback("field_name", name_bytes, 0, len(name_bytes))
        data = bytes(self._field_buf)
        if data:
            self.callback("field_data", data, 0, len(data))
        self.callback("field_end")
        self._field_buf.clear()
        self._name = None

    def write(self, data: bytes) -> int:
        if not data:
            return 0
        n = len(data)
        if self._size + n > self._max:
            n = int(self._max - self._size)
        if n <= 0:
            return 0
        self._size += n
        self._buf += data[:n]
        # Stream over separators '&' and first '=' per field
        i = 0
        while i < len(self._buf):
            b = self._buf[i]
            if b == 38:  # '&'
                # End of current field
                raw = bytes(self._buf[:i])
                self._buf = self._buf[i + 1 :]
                key, eq, val = raw.partition(b"=")
                if not eq and self._strict:
                    raise QuerystringParseError("strict_parsing: missing '=' in field")
                self._name = unquote(key.decode("utf-8", "replace"))
                self._field_buf[:] = unquote(val.decode("utf-8", "replace")).encode("utf-8")
                self._flush_field()
                i = 0
                continue
            i += 1
        return n

    def finalize(self) -> None:
        if self._buf:
            raw = bytes(self._buf)
            key, eq, val = raw.partition(b"=")
            if not eq and self._strict:
                raise QuerystringParseError("strict_parsing: missing '=' in field")
            self._name = unquote(key.decode("utf-8", "replace"))
            self._field_buf[:] = unquote(val.decode("utf-8", "replace")).encode("utf-8")
            self._flush_field()
        self.callback("end")


class MultipartParser(BaseParser):
    """Streaming `multipart/form-data` parser with header events.

    Callbacks:
      - on_part_begin()
      - on_header_begin(); on_header_field(data,s,e); on_header_value(data,s,e); on_header_end()
      - on_headers_finished()
      - on_part_data(data, start, end)
      - on_part_end()
      - on_end()
    """

    CRLF = b"\r\n"

    def __init__(self, boundary: bytes, *, max_size: float = float("inf")) -> None:
        super().__init__()
        if not boundary:
            raise MultipartParseError("Boundary required")
        if not isinstance(max_size, (int, float)) or max_size < 1:
            raise ValueError("max_size must be a positive number")
        self._boundary = b"--" + boundary
        self._terminal = self._boundary + b"--"
        self._max = max_size
        self._size = 0
        self._buf = bytearray()
        self._started = False
        self._in_headers = False
        self._cur_header_name = bytearray()
        self._cur_header_val = bytearray()
        self._headers: Dict[str, str] = {}

    def _emit_headers(self) -> None:
        # Emit header callbacks for collected headers
        for k, v in self._headers.items():
            self.callback("header_begin")
            kb = k.encode("latin-1")
            vb = v.encode("latin-1")
            self.callback("header_field", kb, 0, len(kb))
            self.callback("header_value", vb, 0, len(vb))
            self.callback("header_end")
        self.callback("headers_finished")

    def write(self, data: bytes) -> int:
        if not data:
            return 0
        n = len(data)
        if self._size + n > self._max:
            n = int(self._max - self._size)
        if n <= 0:
            return 0
        self._size += n
        self._buf += data[:n]

        # If not started, look for first boundary line
        while not self._started:
            idx = self._buf.find(self.CRLF)
            if idx == -1:
                return n
            line = bytes(self._buf[: idx + 2])
            del self._buf[: idx + 2]
            if line.startswith(self._boundary):
                if line.startswith(self._terminal):
                    self.callback("end")
                    return n
                self._started = True
                self._in_headers = True
                self.callback("part_begin")
                break

        # Parse loop: headers then part data until next boundary
        while True:
            if self._in_headers:
                # Read headers until blank line
                idx = self._buf.find(self.CRLF)
                if idx == -1:
                    return n
                line = bytes(self._buf[: idx + 2])
                del self._buf[: idx + 2]
                if line == self.CRLF:
                    # end of headers
                    self._emit_headers()
                    self._in_headers = False
                else:
                    try:
                        name, val = line.decode("latin-1").split(":", 1)
                    except ValueError:
                        raise MultipartParseError("Invalid header line")
                    self._headers[name.strip().lower()] = val.strip()
                continue

            # We are in part body – search for boundary sequences
            bidx = self._buf.find(self.CRLF + self._boundary)
            if bidx == -1:
                # emit chunk
                if self._buf:
                    self.callback("part_data", bytes(self._buf), 0, len(self._buf))
                    self._buf.clear()
                return n

            # emit body up to CRLF before boundary
            if bidx:
                self.callback("part_data", bytes(self._buf[:bidx]), 0, bidx)
            del self._buf[: bidx + 2]  # drop data and CRLF

            # Now buffer starts with boundary or terminal
            if self._buf.startswith(self._terminal):
                # end current part
                self.callback("part_end")
                del self._buf[: len(self._terminal)]
                # consume trailing CRLF if present
                if self._buf.startswith(self.CRLF):
                    del self._buf[:2]
                self.callback("end")
                return n

            if self._buf.startswith(self._boundary):
                # end current part, next headers
                self.callback("part_end")
                del self._buf[: len(self._boundary)]
                # consume trailing CRLF
                if self._buf.startswith(self.CRLF):
                    del self._buf[:2]
                # reset state for next part
                self._headers.clear()
                self._in_headers = True
                self.callback("part_begin")
                continue

    def finalize(self) -> None:
        # Flush any remaining body as data (should be empty if boundaries align)
        if self._buf:
            self.callback("part_data", bytes(self._buf), 0, len(self._buf))
            self._buf.clear()
