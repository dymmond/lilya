from __future__ import annotations

import abc
from collections.abc import Sequence

from lilya.contrib.mail.message import EmailMessage


class BaseMailBackend(abc.ABC):
    """
    Abstract base class for all mail backends in Lilya.

    A backend defines *how* email messages are delivered.
    Subclasses must implement :meth:`send` at a minimum, and may
    override :meth:`open`, :meth:`close`, or :meth:`send_many`
    for efficiency or connection pooling.

    Examples of built-in backends:
        - SMTPBackend: Sends messages via SMTP.
        - ConsoleBackend: Prints messages to stdout (for debugging).
        - FileBackend: Writes messages to `.eml` files.
        - InMemoryBackend: Stores messages in memory (for testing).
    """

    async def open(self) -> None:
        """
        Prepare resources required for sending messages.

        Backends that manage persistent connections (e.g., SMTP)
        should override this method to open connections or initialize
        connection pools.

        Called automatically on application startup if lifecycle
        integration is enabled.
        """
        return None

    async def close(self) -> None:
        """
        Release resources allocated by the backend.

        Backends should override this to close persistent connections
        or clean up resources.

        Called automatically on application shutdown if lifecycle
        integration is enabled.
        """
        return None

    @abc.abstractmethod
    async def send(self, message: EmailMessage) -> None:
        """
        Send a single email message.

        Args:
            message: An :class:`EmailMessage` instance representing the
                email to be delivered.

        Raises:
            MailError: If the message cannot be sent.
        """
        raise NotImplementedError

    async def send_many(self, messages: Sequence[EmailMessage]) -> None:
        """
        Send multiple email messages in sequence.

        Subclasses may override this for performance, e.g. reusing
        an open SMTP connection. The default implementation simply
        iterates and calls :meth:`send`.

        Args:
            messages: A sequence of :class:`EmailMessage` objects.
        """
        for message in messages:
            await self.send(message)
