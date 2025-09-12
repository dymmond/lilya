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
    - `filename_or_fp`: path to file or file-like object
    - `mimetype`: optional MIME type
    - `as_attachment`: whether to force download
    - `attachment_filename`: custom filename for download
    - `max_age`: Cache-Control max-age in seconds
    """

    if isinstance(filename_or_fp, (str, Path)):
        path = Path(filename_or_fp)
        headers = {}

        if as_attachment:
            filename = attachment_filename or path.name
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'

        if max_age is not None:
            headers["Cache-Control"] = f"public, max-age={max_age}"

        return FileResponse(
            path,
            media_type=mimetype,
            headers=headers or None,
            filename=attachment_filename or (path.name if as_attachment else None),
        )

    # If file-like object
    headers = {}
    if as_attachment:
        filename = attachment_filename or "download"
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    if max_age is not None:
        headers["Cache-Control"] = f"public, max-age={max_age}"

    return StreamingResponse(
        filename_or_fp,
        media_type=mimetype or "application/octet-stream",
        headers=headers or None,
        background=Task(filename_or_fp.close),
    )
