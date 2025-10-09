from __future__ import annotations

from pathlib import Path
from typing import IO

from lilya.background import Task
from lilya.responses import FileResponse, StreamingResponse


def send_file(
    filename_or_fp: str | Path | IO[bytes],
    mimetype: str | None = None,
    as_attachment: bool = False,
    attachment_filename: str | None = None,
    max_age: int | None = None,
) -> FileResponse | StreamingResponse:
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

        if as_attachment:
            filename = attachment_filename or path.name
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        return FileResponse(
            path,
            media_type=mimetype,
            headers=headers or None,
            filename=attachment_filename if as_attachment else None,
        )

    if as_attachment:
        filename = attachment_filename or "download"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    return StreamingResponse(
        filename_or_fp,
        media_type=mimetype or "application/octet-stream",
        headers=headers or None,
        background=Task(filename_or_fp.close),
    )
