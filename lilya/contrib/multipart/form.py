from __future__ import annotations

import io
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from lilya.contrib.multipart.exceptions import FormParserError
from lilya.contrib.multipart.parsers import MultipartParser, OctetStreamParser, QuerystringParser
from lilya.contrib.multipart.utils import decode_rfc5987_param, parse_options_header

# ---------------------------------------------------------------------
# Callback Protocols
# ---------------------------------------------------------------------


class OnFieldCallback(Protocol):
    """Typing protocol for field callbacks."""

    def __call__(self, field: Field) -> None: ...


class OnFileCallback(Protocol):
    """Typing protocol for file callbacks."""

    def __call__(self, file: File) -> None: ...


class SupportsRead(Protocol):
    """Typing protocol for readable input streams."""

    def read(self, n: int) -> bytes: ...


# ---------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------


@dataclass
class File:
    """
    Represents an uploaded file produced by ``FormParser``.

    Provides a minimal file-like API with ``write()``, ``finalize()``, and
    ``close()``.

    Attributes:
        filename: Original filename from Content-Disposition.
        field_name: Name of the associated form field.
        content_type: Optional MIME type.
        headers: Original headers from the part.
        size: Total number of bytes written.
    """

    filename: str
    field_name: str
    content_type: str | None = None
    headers: dict[str, str] | None = None

    _spool: tempfile.SpooledTemporaryFile | None = None
    _size: int = 0

    def __post_init__(self) -> None:
        """Initialize an in-memory spool file with 1 MiB threshold."""
        self._spool = tempfile.SpooledTemporaryFile(max_size=1 * 1024 * 1024)

    def write(self, data: bytes) -> None:
        """Write a chunk of bytes to the spool file and update size."""
        assert self._spool is not None
        self._spool.write(data)
        self._size += len(data)

    def finalize(self) -> None:
        """Flush and rewind the file so it can be read from the beginning."""
        assert self._spool is not None
        self._spool.flush()
        try:
            self._spool.seek(0)
        except Exception:  # noqa
            pass

    def close(self) -> None:
        """Close the spool file and release resources."""
        try:
            if self._spool is not None:
                self._spool.close()
        finally:
            self._spool = None

    @property
    def size(self) -> int:
        """Return the total number of bytes written to this file."""
        return self._size

    def read(self) -> bytes | Any:
        """Read the full contents of the file, restoring cursor position."""
        assert self._spool is not None
        pos = self._spool.tell()
        try:
            self._spool.seek(0)
            return self._spool.read()
        finally:
            self._spool.seek(pos)


@dataclass
class Field:
    """
    Represents a non-file form field produced by ``FormParser``.

    Attributes:
        name: Field name.
        value: Final decoded string value.
    """

    name: str
    value: str | None = None
    _buffer: io.BytesIO | None = None

    def write(self, data: bytes) -> None:
        """Append raw bytes to the internal buffer."""
        if self._buffer is None:
            self._buffer = io.BytesIO()
        self._buffer.write(data)

    def finalize(self) -> None:
        """Decode buffered data into a UTF-8 string with replacement."""
        if self._buffer is None:
            self.value = ""
        else:
            self.value = self._buffer.getvalue().decode("utf-8", "replace")

    def close(self) -> None:
        """Close the internal buffer and release resources."""
        if self._buffer is not None:
            try:
                self._buffer.close()
            finally:
                self._buffer = None

    def set_none(self) -> None:
        """Explicitly mark this field as having no value."""
        self.value = None


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

FormParserConfig = dict[str, Any]

DEFAULT_CONFIG: FormParserConfig = {
    "MAX_BODY_SIZE": float("inf"),
    "MAX_MEMORY_FILE_SIZE": 1 * 1024 * 1024,
    "UPLOAD_DIR": None,
    "UPLOAD_KEEP_FILENAME": False,
    "UPLOAD_KEEP_EXTENSIONS": False,
    "UPLOAD_ERROR_ON_BAD_CTE": False,
}


# ---------------------------------------------------------------------
# FormParser Orchestrator
# ---------------------------------------------------------------------


class FormParser:
    """
    High-level orchestrator for parsing form submissions.

    Supported Content-Types:
        - ``multipart/form-data``
        - ``application/x-www-form-urlencoded``
        - ``application/octet-stream``

    Call sequence:
        - Feed bytes via ``write(data)``.
        - Call ``finalize()`` when done.
        - Registered callbacks will be invoked for fields, files, and completion.
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
        """Initialize a FormParser with callbacks and configuration."""
        self.content_type = content_type or ""
        self.on_field = on_field
        self.on_file = on_file
        self.on_end = on_end
        self.boundary = boundary
        self.file_name = file_name
        self.FileClass = FileClass
        self.FieldClass = FieldClass
        self.config = {**DEFAULT_CONFIG, **(config or {})}

        # Normalize content type and parameters
        ctype, params = parse_options_header(self.content_type)
        self._ctype = ctype
        self._params = params

        if self._ctype == "multipart/form-data":
            if boundary is None:
                boundary_param = params.get("boundary")  # type: ignore
                if not boundary_param:
                    raise FormParserError("Missing boundary for multipart/form-data")
                self.boundary = boundary_param.encode("ascii", "strict")
        elif self._ctype in (
            "application/octet-stream",
            "application/x-www-form-urlencoded",
            "text/plain",
        ):
            pass
        else:
            raise FormParserError(f"Unsupported Content-Type: {self.content_type}")

        # Runtime state
        self._current_field: Field | None = None
        self._current_file: File | None = None
        self._multipart_parser: MultipartParser | None = None
        self._urlencoded_parser: QuerystringParser | None = None
        self._octet_stream_parser: OctetStreamParser | None = None

        # Build the sub-parser immediately
        if self._ctype == "multipart/form-data":
            self._multipart_parser = self._build_multipart_parser()
        elif self._ctype == "application/octet-stream":
            self._octet_stream_parser = self._build_octet_stream_parser()
        else:
            self._urlencoded_parser = self._build_urlencoded_parser()

    # -----------------------------------------------------------------
    # Sub-parser builders
    # -----------------------------------------------------------------

    def _build_multipart_parser(self) -> MultipartParser:
        """
        Construct and configure a ``MultipartParser`` with callbacks.
        """
        assert self.boundary is not None
        parser = MultipartParser(self.boundary, max_size=self.config["MAX_BODY_SIZE"])

        def on_headers_finished() -> None:
            """Decide whether this part is a file or a field."""
            content_disposition = parser._headers.get("content-disposition", "")
            _, params = parse_options_header(content_disposition)

            field_name = params.get("name") or params.get("name*")  # type: ignore
            if field_name and field_name.endswith("*"):
                field_name = decode_rfc5987_param(params["name*"], "utf-8")  # type: ignore

            filename = params.get("filename")  # type: ignore
            if not filename and "filename*" in params:
                filename = decode_rfc5987_param(params["filename*"], "utf-8")  # type: ignore

            content_type = parser._headers.get("content-type")

            if filename is not None:
                self._current_file = self.FileClass(
                    filename=filename,
                    field_name=field_name or "",
                    content_type=content_type,
                    headers=parser._headers.copy(),
                )
            else:
                self._current_field = self.FieldClass(name=field_name or "")

        def on_part_data(data: bytes, start: int, end: int) -> None:
            """Write data chunks into current file or field."""
            chunk = data[start:end]
            if self._current_file is not None:
                self._current_file.write(chunk)
            elif self._current_field is not None:
                self._current_field.write(chunk)

        def on_part_begin() -> None:
            """Reset current field and file before a new part begins."""
            self._current_field = None
            self._current_file = None

        def on_part_end() -> None:
            """Finalize current part and trigger callbacks."""
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
            """Notify when multipart parsing is complete."""
            if self.on_end is not None:
                self.on_end()

        parser.set_callback("headers_finished", on_headers_finished)
        parser.set_callback("part_begin", on_part_begin)
        parser.set_callback("part_data", on_part_data)
        parser.set_callback("part_end", on_part_end)
        parser.set_callback("end", on_end)
        return parser

    def _build_urlencoded_parser(self) -> QuerystringParser:
        """
        Construct and configure a ``QuerystringParser`` with callbacks.
        """
        parser = QuerystringParser(max_size=self.config["MAX_BODY_SIZE"])

        key_buffer: bytearray | None = None
        value_buffer: bytearray | None = None

        def on_field_start() -> None:
            """Initialize buffers for a new key=value pair."""
            nonlocal key_buffer, value_buffer
            key_buffer = bytearray()
            value_buffer = bytearray()

        def on_field_name(data: bytes, start: int, end: int) -> None:
            """Accumulate raw key bytes."""
            assert key_buffer is not None
            key_buffer.extend(data[start:end])

        def on_field_data(data: bytes, start: int, end: int) -> None:
            """Accumulate raw value bytes."""
            assert value_buffer is not None
            value_buffer.extend(data[start:end])

        def on_field_end() -> None:
            """Finalize a field and trigger callback."""
            assert key_buffer is not None and value_buffer is not None
            name = key_buffer.decode("utf-8", "replace")
            value = value_buffer.decode("utf-8", "replace")
            field = self.FieldClass(name=name)
            field.write(value.encode("utf-8"))
            field.finalize()
            if self.on_field is not None:
                self.on_field(field)

        def on_end() -> None:
            """Notify when urlencoded parsing is complete."""
            if self.on_end is not None:
                self.on_end()

        parser.set_callback("field_start", on_field_start)
        parser.set_callback("field_name", on_field_name)
        parser.set_callback("field_data", on_field_data)
        parser.set_callback("field_end", on_field_end)
        parser.set_callback("end", on_end)
        return parser

    def _build_octet_stream_parser(self) -> OctetStreamParser:
        """
        Construct and configure an ``OctetStreamParser`` with callbacks.
        """
        if not self.file_name:
            self.file_name = "upload"
        parser = OctetStreamParser(max_size=self.config["MAX_BODY_SIZE"])

        def on_start() -> None:
            """Create file representation when octet stream begins."""
            self._current_file = self.FileClass(
                filename=self.file_name or "upload",
                field_name="file",
            )

        def on_data(data: bytes, start: int, end: int) -> None:
            """Write raw data into the file object."""
            assert self._current_file is not None
            self._current_file.write(data[start:end])

        def on_end() -> None:
            """Finalize the file and trigger callbacks."""
            assert self._current_file is not None
            self._current_file.finalize()
            if self.on_file is not None:
                self.on_file(self._current_file)
            if self.on_end is not None:
                self.on_end()

        parser.set_callback("start", on_start)
        parser.set_callback("data", on_data)
        parser.set_callback("end", on_end)
        return parser

    # -----------------------------------------------------------------
    # Streaming API
    # -----------------------------------------------------------------

    def write(self, data: bytes) -> int:
        """Feed a chunk of bytes into the active parser."""
        if self._multipart_parser is not None:
            return self._multipart_parser.write(data)
        if self._urlencoded_parser is not None:
            return self._urlencoded_parser.write(data)
        if self._octet_stream_parser is not None:
            return self._octet_stream_parser.write(data)
        return 0

    def finalize(self) -> None:
        """Finalize parsing, flushing any remaining state."""
        if self._multipart_parser is not None:
            self._multipart_parser.finalize()
        if self._urlencoded_parser is not None:
            self._urlencoded_parser.finalize()
        if self._octet_stream_parser is not None:
            self._octet_stream_parser.finalize()

    def close(self) -> None:
        """Close the parser. Currently a no-op for in-memory parsers."""
        pass


# ---------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------


def create_form_parser(
    headers: dict[str, bytes | str],
    on_field: OnFieldCallback | None,
    on_file: OnFileCallback | None,
    on_end: Callable[[], None] | None = None,
    *,
    file_name: str | None = None,
    config: FormParserConfig | None = None,
) -> FormParser:
    """
    Build a ``FormParser`` from HTTP headers and callbacks.

    Args:
        headers: Case-insensitive mapping of HTTP headers.
        on_field: Callback for each parsed field.
        on_file: Callback for each parsed file.
        on_end: Callback when parsing completes.
        file_name: Filename to assign for octet-stream uploads.
        config: Optional parser configuration.

    Returns:
        A configured ``FormParser`` instance.
    """
    normalized_headers = {
        k.lower(): (v.decode() if isinstance(v, (bytes, bytearray)) else str(v))
        for k, v in headers.items()
    }
    content_type = normalized_headers.get("content-type", "")
    boundary: bytes | None = None
    media_type, params = parse_options_header(content_type)
    if media_type == "multipart/form-data":
        boundary_param = params.get("boundary")  # type: ignore
        if not boundary_param:
            raise FormParserError("Missing boundary in Content-Type")
        boundary = boundary_param.encode("ascii", "strict")

    return FormParser(
        content_type=content_type,
        on_field=on_field,
        on_file=on_file,
        on_end=on_end,
        boundary=boundary,
        file_name=file_name,
        config=config,
    )


def parse_form(
    headers: dict[str, bytes | str],
    input_stream: SupportsRead,
    on_field: OnFieldCallback | None,
    on_file: OnFileCallback | None,
    chunk_size: int = 1024 * 1024,
) -> None:
    """
    Read from a file-like ``input_stream`` and emit fields/files via callbacks.

    Mirrors python-multipart’s ``parse_form`` function.

    Args:
        headers: Case-insensitive HTTP headers.
        input_stream: File-like object with a ``read()`` method.
        on_field: Callback invoked with ``Field`` for each parsed field.
        on_file: Callback invoked with ``File`` for each parsed file.
        chunk_size: Number of bytes to read per iteration.
    """
    form_parser = create_form_parser(headers, on_field, on_file)
    while True:
        chunk = input_stream.read(chunk_size)
        if not chunk:
            break
        form_parser.write(chunk)
    form_parser.finalize()
