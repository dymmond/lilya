from __future__ import annotations

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage


class InMemoryBackend(BaseMailBackend):
    """
    Stores messages in memory for testing.
    """

    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)

    async def send_many(self, messages: list[EmailMessage]) -> None:
        self.outbox.extend(messages)
