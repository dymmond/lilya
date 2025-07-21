from __future__ import annotations

import http.cookies
from collections.abc import AsyncGenerator, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, cast
from urllib.parse import unquote, unquote_plus

import anyio
from anyio import SpooledTemporaryFile

from lilya.datastructures import DataUpload, FormData, Header
from lilya.enums import FormMessage

try:
    import python_multipart as multipart
    from python_multipart.multipart import parse_options_header
except ModuleNotFoundError:  # pragma: nocover
    # old import name
    try:
        import multipart  # type: ignore[no-redef]
        from multipart.multipart import parse_options_header  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: nocover
        parse_options_header = None
        multipart = None


@lru_cache(1024)
def cookie_parser(cookie_string: str | bytes) -> dict[str, str]:
    """
    Parses a `Cookie` HTTP header into a dictionary of key/value pairs.
    This function has been adapted from Django 3.1.0.
    """
    if isinstance(cookie_string, bytes):
        cookie_string = cookie_string.decode()

    cookies = [
        cookie.split("=", 1) if "=" in cookie else ("", cookie)
        for cookie in cookie_string.split(";")
    ]

    cookie_dict: dict[str, str] = {
        cookie[0].strip(): unquote(http.cookies._unquote(cookie[1].strip())) for cookie in cookies
    }

    return cookie_dict


@dataclass
class MultipartPart:
    content_disposition: bytes | None = None
    field_name: str = ""
    data: bytes = b""
    file: DataUpload | None = None
    item_headers: list[tuple[bytes, bytes]] = field(default_factory=list)


def _user_safe_decode(src: bytes, codec: str) -> str:
    try:
        return src.decode(codec)
    except (UnicodeDecodeError, LookupError):
        return src.decode("utf-8")


class MultiPartException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class FormParser:
    """
    A class for parsing form data from an asynchronous stream.

    Args:
        headers (Header): The headers from the request.
        stream (AsyncGenerator[bytes, None]): Asynchronous generator stream of bytes.

    Raises:
        AssertionError: If the `python-multipart` library is not installed.

    Attributes:
        headers (Header): The headers from the request.
        stream (AsyncGenerator[bytes, None]): Asynchronous generator stream of bytes.
        messages (List[Tuple[FormMessage, bytes]]): List to store parsing messages.
    """

    def __init__(self, headers: Header, stream: AsyncGenerator[bytes, None]) -> None:
        """
        Initializes the FormParser with headers and stream.
        """
        assert multipart is not None, (
            "The `python-multipart` library must be installed to use form parsing."
        )
        self.headers = headers
        self.stream = stream
        self.messages: list[tuple[FormMessage, bytes]] = []

    def on_field_start(self) -> None:
        """
        Callback when a form field starts.
        """
        message = (FormMessage.FIELD_START, b"")
        self.messages.append(message)

    def on_field_name(self, data: bytes, start: int, end: int) -> None:
        """
        Callback when the name of a form field is encountered.

        Args:
            data (bytes): The data received.
            start (int): Start index of the data.
            end (int): End index of the data.
        """
        message = (FormMessage.FIELD_NAME, data[start:end])
        self.messages.append(message)

    def on_field_data(self, data: bytes, start: int, end: int) -> None:
        """
        Callback when data of a form field is encountered.

        Args:
            data (bytes): The data received.
            start (int): Start index of the data.
            end (int): End index of the data.
        """
        message = (FormMessage.FIELD_DATA, data[start:end])
        self.messages.append(message)

    def on_field_end(self) -> None:
        """
        Callback when a form field ends.
        """
        message = (FormMessage.FIELD_END, b"")
        self.messages.append(message)

    def on_end(self) -> None:
        """
        Callback when the form parsing is complete.
        """
        message = (FormMessage.END, b"")
        self.messages.append(message)

    async def parse(self) -> FormData:
        """
        Asynchronously parses the form data from the provided stream.

        Returns:
            FormData: Parsed form data.

        Note:
            The parser utilizes a dictionary of callbacks to process different stages of parsing.
        """
        callbacks: Any = {
            "on_field_start": self.on_field_start,
            "on_field_name": self.on_field_name,
            "on_field_data": self.on_field_data,
            "on_field_end": self.on_field_end,
            "on_end": self.on_end,
        }

        parser = multipart.QuerystringParser(callbacks)
        field_name = b""
        field_value = b""
        items: list[tuple[str, str | DataUpload]] = []

        async for chunk in self.stream:
            if chunk:
                parser.write(chunk)
            else:
                parser.finalize()
            messages = list(self.messages)
            self.messages.clear()
            for message_type, message_bytes in messages:
                if message_type == FormMessage.FIELD_START:
                    field_name = b""
                    field_value = b""
                elif message_type == FormMessage.FIELD_NAME:
                    field_name += message_bytes
                elif message_type == FormMessage.FIELD_DATA:
                    field_value += message_bytes
                elif message_type == FormMessage.FIELD_END:
                    name = unquote_plus(field_name.decode("utf-8"))
                    value = unquote_plus(field_value.decode("utf-8"))
                    items.append((name, value))

        return FormData(items)


class MultiPartParser:
    """
    Multipart form data parser.

    This class parses the multipart stream and provides a structured representation
    of form data, including files.

    Attributes:
        max_file_size (int): Maximum size for individual file parts.
    """

    max_file_size = 1024 * 1024

    def __init__(
        self,
        headers: Header,
        stream: AsyncGenerator[bytes, None],
        *,
        max_files: int | float = 1000,
        max_fields: int | float = 1000,
    ) -> None:
        """
        Initialize the MultiPartParser.

        Args:
            headers (Header): Headers of the request.
            stream (AsyncGenerator[bytes, None]): Async generator yielding byte chunks of the request body.
            max_files (Union[int, float]): Maximum number of allowed files.
            max_fields (Union[int, float]): Maximum number of allowed fields.
        """
        assert multipart is not None, (
            "The `python-multipart` library must be installed to use form parsing."
        )
        self.headers = headers
        self.stream = stream
        self.max_files = max_files
        self.max_fields = max_fields
        self.items: list[tuple[str, str | DataUpload]] = []
        self._current_files = 0
        self._current_fields = 0
        self._current_partial_header_name: bytes = b""
        self._current_partial_header_value: bytes = b""
        self._current_part = MultipartPart()
        self._charset = ""
        self._file_parts_to_write: list[tuple[MultipartPart, bytes]] = []
        self._file_parts_to_finish: list[MultipartPart] = []
        self._files_to_close_on_error: AsyncExitStack = AsyncExitStack()

    def on_part_begin(self) -> None:
        """
        Callback when starting a new part.
        """
        self._current_part = MultipartPart()

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        """
        Callback when receiving part data.

        Args:
            data (bytes): Data chunk.
            start (int): Start index of the data in the chunk.
            end (int): End index of the data in the chunk.
        """
        message_bytes = data[start:end]
        if self._current_part.file is None:
            self._current_part.data += message_bytes
        else:
            self._file_parts_to_write.append((self._current_part, message_bytes))

    def on_part_end(self) -> None:
        """
        Callback when a part ends.
        """
        if self._current_part.file is None:
            self.items.append(
                (
                    self._current_part.field_name,
                    _user_safe_decode(self._current_part.data, self._charset),
                )
            )
        else:
            self._file_parts_to_finish.append(self._current_part)
            self.items.append((self._current_part.field_name, self._current_part.file))

    def on_header_field(self, data: bytes, start: int, end: int) -> None:
        """
        Callback when receiving header field data.

        Args:
            data (bytes): Data chunk.
            start (int): Start index of the data in the chunk.
            end (int): End index of the data in the chunk.
        """
        self._current_partial_header_name += data[start:end]

    def on_header_value(self, data: bytes, start: int, end: int) -> None:
        """
        Callback when receiving header value data.

        Args:
            data (bytes): Data chunk.
            start (int): Start index of the data in the chunk.
            end (int): End index of the data in the chunk.
        """
        self._current_partial_header_value += data[start:end]

    def on_header_end(self) -> None:
        """
        Callback when a header ends.
        """
        field = self._current_partial_header_name.lower()
        if field == b"content-disposition":
            self._current_part.content_disposition = self._current_partial_header_value
        self._current_part.item_headers.append((field, self._current_partial_header_value))
        self._current_partial_header_name = b""
        self._current_partial_header_value = b""

    def on_headers_finished(self) -> None:
        """
        Handle the completion of parsing headers for a part.
        """
        _, options = parse_options_header(self._current_part.content_disposition)

        self._set_field_name(options)

        if b"filename" in options:
            self._handle_filename(options)
        else:
            self._handle_no_filename()

    def _set_field_name(self, options: dict[bytes, bytes]) -> None:
        """
        Set the field name based on options in Content-Disposition header.

        Args:
            options (Dict[bytes, bytes]): Parsed options from the Content-Disposition header.
        """
        try:
            self._current_part.field_name = _user_safe_decode(options[b"name"], self._charset)
        except KeyError:
            raise MultiPartException(
                'The Content-Disposition header field "name" must be provided.'
            ) from None

    def _handle_filename(self, options: dict[bytes, bytes]) -> None:
        """
        Handle the case when the part has a filename.

        Args:
            options (Dict[bytes, bytes]): Parsed options from the Content-Disposition header.
        """
        self._current_files += 1
        self._validate_files_count()

        filename = _user_safe_decode(options[b"filename"], self._charset)
        tempfile = self._create_temp_file()
        self._current_part.file = self._create_upload_file(filename, tempfile)

    def _handle_no_filename(self) -> None:
        """
        Handle the case when the part does not have a filename.
        """
        self._current_fields += 1
        self._validate_fields_count()

        self._current_part.file = None

    def _validate_files_count(self) -> None:
        """
        Validate the maximum number of files allowed.
        """
        if self._current_files > self.max_files:
            raise MultiPartException(
                f"Too many files. Maximum number of files is {self.max_files}."
            )

    def _create_temp_file(self) -> SpooledTemporaryFile[bytes]:
        """
        Create a temporary file and add it to the cleanup list.

        Returns:
            SpooledTemporaryFile[bytes]: Created temporary file.
        """
        tempfile = SpooledTemporaryFile(max_size=self.max_file_size)
        self._files_to_close_on_error.push_async_callback(tempfile.aclose)
        return tempfile

    def _create_upload_file(
        self, filename: str, tempfile: SpooledTemporaryFile[bytes]
    ) -> DataUpload:
        """
        Create an DataUpload instance for a file part.

        Args:
            filename (str): Name of the file.
            tempfile (SpooledTemporaryFile[bytes]): Temporary file.

        Returns:
            DataUpload: Created DataUpload instance.
        """
        return DataUpload(
            file=cast(anyio.SpooledTemporaryFile, tempfile),
            size=0,
            filename=filename,
            headers=Header(self._current_part.item_headers),
        )

    def _validate_fields_count(self) -> None:
        """
        Validate the maximum number of fields allowed.
        """
        if self._current_fields > self.max_fields:
            raise MultiPartException(
                f"Too many fields. Maximum number of fields is {self.max_fields}."
            )

    def on_end(self) -> None:
        """
        Callback when the parsing ends.
        """
        pass

    async def parse(self) -> FormData:
        """
        Parse the multipart data and return a FormData object.

        Returns:
            FormData: Parsed form data.
        """
        _, params = parse_options_header(self.headers["Content-Type"])
        self._parse_content_type_header(params)
        boundary = self._get_multipart_boundary(params)

        callbacks = self._create_callbacks_dictionary()
        parser = self._create_multipart_parser(boundary, callbacks)

        try:
            async for chunk in self.stream:
                parser.write(chunk)
                await self._write_file_data()
        except BaseException as exc:
            await self._close_files_on_error()
            raise exc

        parser.finalize()
        return FormData(self.items)

    def _parse_content_type_header(self, params: Any) -> None:
        """
        Parse the Content-Type header to get the multipart boundary.

        Args:
            params (Any): Parameters from the Content-Type header.
        """
        charset = params.get(b"charset", "utf-8")
        self._charset = charset.decode("utf-8") if isinstance(charset, bytes) else charset

    def _get_multipart_boundary(self, params: dict[bytes, bytes]) -> bytes:
        """
        Get the multipart boundary from the parsed Content-Type header.

        Args:
            params (Any): Parameters from the Content-Type header.

        Returns:
            bytes: Multipart boundary.
        """
        try:
            return params[b"boundary"]
        except KeyError:
            raise MultiPartException("Missing boundary in multipart.") from None

    def _create_callbacks_dictionary(self) -> dict[str, Callable]:
        """
        Create the callbacks dictionary for the multipart parser.

        Returns:
            Dict[str, Callable]: Callbacks dictionary.
        """
        return {
            "on_part_begin": self.on_part_begin,
            "on_part_data": self.on_part_data,
            "on_part_end": self.on_part_end,
            "on_header_field": self.on_header_field,
            "on_header_value": self.on_header_value,
            "on_header_end": self.on_header_end,
            "on_headers_finished": self.on_headers_finished,
            "on_end": self.on_end,
        }

    def _create_multipart_parser(
        self, boundary: bytes, callbacks: dict[str, Callable]
    ) -> multipart.MultipartParser:
        """
        Create the multipart parser with the specified boundary and callbacks.

        Args:
            boundary (bytes): Multipart boundary.
            callbacks (Dict[str, Callable]): Callbacks dictionary.

        Returns:
            multipart.MultipartParser: Created multipart parser.
        """
        return multipart.MultipartParser(boundary, cast(Any, callbacks))

    async def _write_file_data(self) -> None:
        """
        Write file data asynchronously using DataUpload methods.
        """
        for part, data in self._file_parts_to_write:
            assert part.file
            await part.file.write(data)

        for part in self._file_parts_to_finish:
            assert part.file
            await part.file.seek(0)

        self._file_parts_to_write.clear()
        self._file_parts_to_finish.clear()

    async def _close_files_on_error(self) -> None:
        """
        Close all files if there was an error during parsing.
        """
        await self._files_to_close_on_error.aclose()
