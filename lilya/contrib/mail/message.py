from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# Type aliases for readability
AttachmentContent = bytes | memoryview
AttachmentTuple = tuple[str, AttachmentContent, str | None]  # (filename, content, mimetype)


@dataclass
class EmailMessage:
    """
    A framework-agnostic representation of an email message.

    This class is used internally by Lilya's mail system to describe
    the structure of an outgoing email, regardless of which backend
    actually sends it.

    Features:
        - **Multipart support**: send both text and HTML versions.
        - **Alternatives**: add extra MIME bodies (e.g., iCalendar).
        - **Attachments**: add binary attachments (in-memory or file paths).
        - **Headers**: add custom RFC-822 headers.
        - **Metadata**: arbitrary extra data not sent to recipients.
    """

    subject: str
    to: list[str]
    from_email: str | None = None

    # Primary bodies (at least one should be provided)
    body_text: str | None = None
    body_html: str | None = None

    # Extra MIME bodies, e.g., [("text/calendar", ics_bytes)]
    alternatives: list[tuple[str, str | bytes]] = field(default_factory=list)

    # Recipient lists
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    reply_to: list[str] = field(default_factory=list)

    # Attachments
    attachments: list[AttachmentTuple] = field(default_factory=list)
    attachment_paths: list[str] = field(default_factory=list)

    # Extra headers (e.g., {"X-Campaign": "welcome"})
    headers: Mapping[str, str] = field(default_factory=dict)

    # Arbitrary metadata (not transmitted)
    meta: dict[str, Any] = field(default_factory=dict)

    def all_recipients(self) -> list[str]:
        """
        Collect all recipients of the email (To + Cc + Bcc).

        Returns:
            A combined list of all recipient addresses.
        """
        recipients: list[str] = list(self.to)
        if self.cc:
            recipients.extend(self.cc)
        if self.bcc:
            recipients.extend(self.bcc)
        return recipients
