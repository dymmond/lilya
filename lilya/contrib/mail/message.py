from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

AttachmentContent = bytes | memoryview
Attachmenttuple = tuple[str, AttachmentContent, str | None]  # (filename, content, mimetype)


@dataclass
class EmailMessage:
    """
    Framework-agnostic email message.

    - Supports multipart (text + html) via 'alternatives'
    - Supports attachments either by in-memory bytes or file paths
    - 'headers' allows arbitrary extra headers
    """

    subject: str
    to: list[str]
    from_email: str | None = None

    # Primary bodies (at least one should be provided)
    body_text: str | None = None
    body_html: str | None = None

    # Extra bodies (media-type, content) e.g. [("text/calendar", bytes_ics)]
    alternatives: list[tuple[str, str | bytes]] = field(default_factory=list)

    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    reply_to: list[str] = field(default_factory=list)

    # Attachments:
    # - in_memory: list of (filename, content_bytes, mimetype?)
    # - file_paths: list of absolute/relative paths
    attachments: list[Attachmenttuple] = field(default_factory=list)
    attachment_paths: list[str] = field(default_factory=list)

    headers: Mapping[str, str] = field(default_factory=dict)

    # Arbitrary metadata (not sent over the wire)
    meta: dict[str, Any] = field(default_factory=dict)

    def all_recipients(self) -> list[str]:
        r = list(self.to)
        if self.cc:
            r.extend(self.cc)
        if self.bcc:
            r.extend(self.bcc)
        return r
