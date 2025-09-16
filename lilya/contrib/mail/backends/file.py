from __future__ import annotations

from datetime import datetime
from email.generator import BytesGenerator
from email.policy import default as default_policy
from pathlib import Path

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.backends.smtp import build_email_message
from lilya.contrib.mail.message import EmailMessage


class FileBackend(BaseMailBackend):
    """
    A mail backend that writes messages to disk as `.eml` files.

    This backend is useful for **development, debugging, or archiving**,
    when you want to inspect the raw RFC-822 email output without
    actually sending it.

    Files are written in standard MIME format, so they can be opened by
    email clients like Thunderbird or Outlook.
    """

    def __init__(self, directory: str, create: bool = True) -> None:
        """
        Initialize the file backend.

        Args:
            directory: Path to the directory where `.eml` files will be stored.
            create: Whether to automatically create the directory if it does not exist.
        """
        self.directory = Path(directory)
        self.create = create

    async def open(self) -> None:
        """
        Ensure the target directory exists if `create=True`.
        """
        if self.create:
            self.directory.mkdir(parents=True, exist_ok=True)

    async def send(self, message: EmailMessage) -> None:
        """
        Write an email message to a `.eml` file.

        Filenames are prefixed with a UTC timestamp to avoid collisions,
        followed by a sanitized subject line.

        Args:
            message: The :class:`EmailMessage` to serialize.
        """
        email_message = await build_email_message(message)

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        safe_subject = "".join(
            char for char in (message.subject or "no-subject") if char.isalnum() or char in "-_"
        )[:60]

        file_path = self.directory / f"{timestamp}-{safe_subject}.eml"

        with open(file_path, "wb") as file:
            BytesGenerator(file, policy=default_policy).flatten(email_message)
