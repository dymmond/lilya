from __future__ import annotations

import io
import logging
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Dict, Protocol

from .exceptions import (
    FormParserError,
)
from .parsers import MultipartParser, OctetStreamParser, QuerystringParser
from .utils import decode_rfc5987_param, parse_options_header

log = logging.getLogger(__name__)


# Public callback protocols (typing aid only)
class OnFieldCallback(Protocol):
    def __call__(self, field: Field) -> None: ...


class OnFileCallback(Protocol):
    def __call__(self, file: File) -> None: ...


class SupportsRead(Protocol):
    def read(self, n: int) -> bytes: ...


@dataclass
class File:
    """Represents an uploaded file as produced by FormParser.

    Minimal API: write(bytes), finalize(), close().
    """

    filename: str
    field_name: str
    content_type: str | None = None
    headers: Dict[str, str] | None = None

    # internals
    _spool: tempfile.SpooledTemporaryFile | None = None
    _size: int = 0

    def __post_init__(self) -> None:
        # 1 MiB in-memory, then spill to disk
        self._spool = tempfile.SpooledTemporaryFile(max_size=1 * 1024 * 1024)

    def write(self, data: bytes) -> None:
        assert self._spool is not None
        self._spool.write(data)
        self._size += len(data)

    def finalize(self) -> None:
        assert self._spool is not None
        self._spool.flush()
        try:
            self._spool.seek(0)
        except Exception:  # pragma: no cover
            pass

    def close(self) -> None:
        try:
            if self._spool is not None:
                self._spool.close()
        finally:
            self._spool = None

    # Convenience accessors used by frameworks/tests
    @property
    def size(self) -> int:
        return self._size

    def read(self) -> bytes:
        assert self._spool is not None
        pos = self._spool.tell()
        try:
            self._spool.seek(0)
            return self._spool.read()
        finally:
            self._spool.seek(pos)


@dataclass
class Field:
    """Represents a non-file form field produced by FormParser."""

    name: str
    value: str | None = None
    _buf: io.BytesIO | None = None

    def write(self, data: bytes) -> None:
        if self._buf is None:
            self._buf = io.BytesIO()
        self._buf.write(data)

    def finalize(self) -> None:
        if self._buf is None:
            self.value = ""
        else:
            self.value = self._buf.getvalue().decode("utf-8", "replace")

    def close(self) -> None:
        if self._buf is not None:
            try:
                self._buf.close()
            finally:
                self._buf = None

    def set_none(self) -> None:
        self.value = None


# FormParser configuration keys (to mirror python-multipart)
FormParserConfig = Dict[str, Any]

DEFAULT_CONFIG: FormParserConfig = {
    "MAX_BODY_SIZE": float("inf"),
    "MAX_MEMORY_FILE_SIZE": 1 * 1024 * 1024,
    "UPLOAD_DIR": None,
    "UPLOAD_KEEP_FILENAME": False,
    "UPLOAD_KEEP_EXTENSIONS": False,
    "UPLOAD_ERROR_ON_BAD_CTE": False,
}


class FormParser:
    """All-in-one form parser orchestrator (multipart, urlencoded, octet-stream).

    Signatures and behavior mirror python-multipart’s FormParser.
    """

    def __init__(
        self,
        *,
        content_type: str,
        on_field: OnFieldCallback | None,
        on_file: OnFileCallback | None,
        on_end: Callable[[], None] | None = None,
        boundary: bytes | None = None,
        file_name: str | None = None,
        FileClass: type[File] = File,
        FieldClass: type[Field] = Field,
        config: FormParserConfig | None = None,
    ) -> None:
        self.content_type = content_type or ""
        self.on_field = on_field
        self.on_file = on_file
        self.on_end = on_end
        self.boundary = boundary
        self.file_name = file_name
        self.FileClass = FileClass
        self.FieldClass = FieldClass
        self.config = {**DEFAULT_CONFIG, **(config or {})}

        ctype, params = parse_options_header(self.content_type)
        self._ctype = ctype
        self._params = params
        if self._ctype == "multipart/form-data":
            if boundary is None:
                b = params.get("boundary")
                if not b:
                    raise FormParserError("Missing boundary for multipart/form-data")
                self.boundary = b.encode("ascii", "strict")
        elif self._ctype == "application/octet-stream":
            # boundary not needed
            pass
        elif self._ctype in ("application/x-www-form-urlencoded", "text/plain"):
            # handled by QuerystringParser
            pass
        else:
            raise FormParserError(f"Unsupported Content-Type: {self.content_type}")

        # runtime state
        self._current_field: Field | None = None
        self._current_file: File | None = None
        self._multipart: MultipartParser | None = None
        self._urlencoded: QuerystringParser | None = None
        self._octets: OctetStreamParser | None = None

        # Build sub-parser now so write() can just feed
        if self._ctype == "multipart/form-data":
            self._multipart = self._build_multipart()
        elif self._ctype == "application/octet-stream":
            self._octets = self._build_octets()
        else:
            self._urlencoded = self._build_urlencoded()

    # ---- parser builders
    def _build_multipart(self) -> MultipartParser:
        assert self.boundary is not None
        mp = MultipartParser(self.boundary, max_size=self.config["MAX_BODY_SIZE"])

        def header_capture() -> None:
            # decide file vs field after headers_finished
            pass

        def on_headers_finished() -> None:
            nonlocal mp
            # Inspect headers to determine disposition
            cd = mp._headers.get("content-disposition", "")
            _, params = parse_options_header(cd)
            name = params.get("name") or params.get("name*")
            if name and name.endswith("*"):
                name = decode_rfc5987_param(params["name*"], "utf-8")

            filename = params.get("filename")
            if not filename and "filename*" in params:
                filename = decode_rfc5987_param(params["filename*"], "utf-8")

            ctype = mp._headers.get("content-type")

            if filename is not None:
                self._current_file = self.FileClass(filename=filename, field_name=name or "", content_type=ctype, headers=mp._headers.copy())
                if self.on_file is not None:
                    # Defer callback until finalize so consumers get size/content
                    pass
            else:
                self._current_field = self.FieldClass(name=name or "")

        mp.set_callback("header_begin", header_capture)
        mp.set_callback("headers_finished", on_headers_finished)

        def on_data(data: bytes, start: int, end: int) -> None:
            chunk = data[start:end]
            if self._current_file is not None:
                self._current_file.write(chunk)
            elif self._current_field is not None:
                self._current_field.write(chunk)

        def on_part_begin() -> None:
            self._current_field = None
            self._current_file = None

        def on_part_end() -> None:
            if self._current_file is not None:
                self._current_file.finalize()
                if self.on_file is not None:
                    self.on_file(self._current_file)
                self._current_file = None
            elif self._current_field is not None:
                self._current_field.finalize()
                if self.on_field is not None:
                    self.on_field(self._current_field)
                self._current_field = None

        def on_end() -> None:
            if self.on_end is not None:
                self.on_end()

        mp.set_callback("part_begin", on_part_begin)
        mp.set_callback("part_data", on_data)
        mp.set_callback("part_end", on_part_end)
        mp.set_callback("end", on_end)
        return mp

    def _build_urlencoded(self) -> QuerystringParser:
        qp = QuerystringParser(max_size=self.config["MAX_BODY_SIZE"])

        key_buf: bytearray | None = None
        val_buf: bytearray | None = None

        def on_field_start() -> None:
            nonlocal key_buf, val_buf
            key_buf = bytearray()
            val_buf = bytearray()

        def on_field_name(data: bytes, s: int, e: int) -> None:
            assert key_buf is not None
            key_buf.extend(data[s:e])

        def on_field_data(data: bytes, s: int, e: int) -> None:
            assert val_buf is not None
            val_buf.extend(data[s:e])

        def on_field_end() -> None:
            assert key_buf is not None and val_buf is not None
            name = key_buf.decode("utf-8", "replace")
            value = val_buf.decode("utf-8", "replace")
            f = self.FieldClass(name=name)
            f.write(value.encode("utf-8"))
            f.finalize()
            if self.on_field is not None:
                self.on_field(f)

        def on_end() -> None:
            if self.on_end is not None:
                self.on_end()

        qp.set_callback("field_start", on_field_start)
        qp.set_callback("field_name", on_field_name)
        qp.set_callback("field_data", on_field_data)
        qp.set_callback("field_end", on_field_end)
        qp.set_callback("end", on_end)
        return qp

    def _build_octets(self) -> OctetStreamParser:
        if not self.file_name:
            # Anonymous single part – treat as a file named "upload"
            self.file_name = "upload"
        op = OctetStreamParser(max_size=self.config["MAX_BODY_SIZE"])

        # Create file on first data
        def on_start() -> None:
            self._current_file = self.FileClass(filename=self.file_name or "upload", field_name="file")

        def on_data(data: bytes, s: int, e: int) -> None:
            assert self._current_file is not None
            self._current_file.write(data[s:e])

        def on_end() -> None:
            assert self._current_file is not None
            self._current_file.finalize()
            if self.on_file is not None:
                self.on_file(self._current_file)
            if self.on_end is not None:
                self.on_end()

        op.set_callback("start", on_start)
        op.set_callback("data", on_data)
        op.set_callback("end", on_end)
        return op

    # ---- streaming API
    def write(self, data: bytes) -> int:
        if self._multipart is not None:
            return self._multipart.write(data)
        if self._urlencoded is not None:
            return self._urlencoded.write(data)
        if self._octets is not None:
            return self._octets.write(data)
        return 0

    def finalize(self) -> None:
        if self._multipart is not None:
            self._multipart.finalize()
        if self._urlencoded is not None:
            self._urlencoded.finalize()
        if self._octets is not None:
            self._octets.finalize()

    def close(self) -> None:
        # Nothing special to close – sub-parsers are in-memory
        pass


# --------- convenience functions (match python-multipart) ---------

def create_form_parser(
    headers: Dict[str, bytes | str],
    on_field: OnFieldCallback | None,
    on_file: OnFileCallback | None,
    on_end: Callable[[], None] | None = None,
    *,
    file_name: str | None = None,
    config: FormParserConfig | None = None,
) -> FormParser:
    # headers keys must be case-insensitive
    norm = {k.lower(): (v.decode() if isinstance(v, (bytes, bytearray)) else str(v)) for k, v in headers.items()}
    ctype = norm.get("content-type", "")
    boundary: bytes | None = None
    mtype, params = parse_options_header(ctype)
    if mtype == "multipart/form-data":
        b = params.get("boundary")
        if not b:
            raise FormParserError("Missing boundary in Content-Type")
        boundary = b.encode("ascii", "strict")
    return FormParser(
        content_type=ctype,
        on_field=on_field,
        on_file=on_file,
        on_end=on_end,
        boundary=boundary,
        file_name=file_name,
        config=config,
    )


def parse_form(
    headers: Dict[str, bytes | str],
    input_stream: SupportsRead,
    on_field: OnFieldCallback | None,
    on_file: OnFileCallback | None,
    chunk_size: int = 1024 * 1024,
) -> None:
    """Read from a file-like `input_stream` and emit fields/files via callbacks.

    Mirrors python-multipart’s `parse_form` function signature and semantics.
    """
    fp = create_form_parser(headers, on_field, on_file)
    while True:
        chunk = input_stream.read(chunk_size)
        if not chunk:
            break
        fp.write(chunk)
    fp.finalize()
