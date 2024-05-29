from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lilya.testclient.websockets import WebSocketTestSession


class UpgradeException(Exception):
    def __init__(self, session: WebSocketTestSession) -> None:
        self.session = session
