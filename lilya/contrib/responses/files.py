from __future__ import annotations

from pathlib import Path
from typing import IO

from lilya.responses import Response, SimpleFileResponse


def send_file(
    filename_or_fp: str | Path | IO[bytes],
    mimetype: str | None = None,
    as_attachment: bool = False,
    attachment_filename: str | None = None,
    max_age: int | None = None,
    deduce_media_type_from_body: None | bool = None,
) -> Response:
    """
    Sends a file or file-like object as a response.

    - `filename_or_fp`: Path to the file or a file-like object (e.g. BytesIO)
    - `mimetype`: Optional MIME type
    - `as_attachment`: Whether to force browser download
    - `attachment_filename`: Custom filename for the download
    - `max_age`: Cache-Control max-age in seconds
    """

    headers: dict[str, str] = {}

    if max_age is not None:
        headers["Cache-Control"] = f"public, max-age={max_age}"

    if isinstance(filename_or_fp, (str, Path)):
        path = Path(filename_or_fp)
        filename = attachment_filename or path.name
    else:
        filename = attachment_filename or "download"

    return SimpleFileResponse(
        filename_or_fp,
        media_type=mimetype,
        filename=filename,
        headers=headers,
        content_disposition_type="attachment" if as_attachment else "inline",
        deduce_media_type_from_body=deduce_media_type_from_body,
    )
