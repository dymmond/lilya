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
    Writes RFC-822 .eml files to a directory (like Django's file backend).
    """

    def __init__(self, directory: str, create: bool = True) -> None:
        self.dir = Path(directory)
        self.create = create

    async def open(self) -> None:
        if self.create:
            self.dir.mkdir(parents=True, exist_ok=True)

    async def send(self, message: EmailMessage) -> None:
        em = await build_email_message(message)
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        safe_subj = "".join(
            c for c in (message.subject or "no-subject") if c.isalnum() or c in "-_"
        )[:60]
        fname = self.dir / f"{ts}-{safe_subj}.eml"
        with open(fname, "wb") as f:
            BytesGenerator(f, policy=default_policy).flatten(em)
