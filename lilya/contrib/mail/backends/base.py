from __future__ import annotations

import abc
from collections.abc import Sequence

from lilya.contrib.mail.message import EmailMessage


class BaseMailBackend(abc.ABC):
    """
    Base interface for mail backends.
    """

    async def open(self) -> None:
        """Prepare connection/pool if needed."""
        return None

    async def close(self) -> None:
        """Tear down connection/pool if needed."""
        return None

    @abc.abstractmethod
    async def send(self, message: EmailMessage) -> None:
        """Send a single message."""
        raise NotImplementedError

    async def send_many(self, messages: Sequence[EmailMessage]) -> None:
        """Efficiently send many messages (override for perf)."""
        for m in messages:
            await self.send(m)
