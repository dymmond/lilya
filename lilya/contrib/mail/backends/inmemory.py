from __future__ import annotations

from collections.abc import Sequence

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage


class InMemoryBackend(BaseMailBackend):
    """
    A mail backend that stores messages in memory.

    This backend is primarily intended for **unit tests**.
    Sent messages are appended to the public :attr:`outbox` list,
    which can be inspected by test code to verify delivery.

    Example:
        ```python
        backend = InMemoryBackend()
        mailer = Mailer(backend=backend)

        message = EmailMessage(subject="Test", to=["a@b.com"], body_text="hi")
        await mailer.send(message)

        assert backend.outbox[0].subject == "Test"
        ```
    """

    def __init__(self) -> None:
        """
        Initialize the backend with an empty outbox.
        """
        self.outbox: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        """
        Store a single email message in memory.

        Args:
            message: The :class:`EmailMessage` to store.
        """
        self.outbox.append(message)

    async def send_many(self, messages: Sequence[EmailMessage]) -> None:
        """
        Store multiple email messages in memory at once.

        Args:
            messages: A sequence of :class:`EmailMessage` instances to store.
        """
        self.outbox.extend(messages)
