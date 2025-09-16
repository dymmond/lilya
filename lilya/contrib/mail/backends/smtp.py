from __future__ import annotations

import smtplib
from collections.abc import Sequence
from email.message import EmailMessage as PyEmailMessage
from email.utils import make_msgid
from typing import Any

import anyio

from lilya.contrib.mail.backends.base import BaseMailBackend
from lilya.contrib.mail.message import EmailMessage as LilyaEmailMessage


def _add_alternative(
    msg: PyEmailMessage, content: bytes, subtype: str, maintype: str = "text"
) -> None:
    msg.add_alternative(content, subtype=subtype)


async def build_email_message(m: LilyaEmailMessage) -> PyEmailMessage:
    """
    Build a fully-formed RFC-5322 email.message.EmailMessage
    with multipart/alternative and attachments.
    """
    em = PyEmailMessage()
    em["Subject"] = m.subject
    if m.from_email:
        em["From"] = m.from_email
    if m.to:
        em["To"] = ", ".join(m.to)
    if m.cc:
        em["Cc"] = ", ".join(m.cc)
    if m.reply_to:
        em["Reply-To"] = ", ".join(m.reply_to)
    for k, v in m.headers.items():
        em[k] = v

    # Build body parts:
    # Prefer multipart/alternative when text+html are present
    if m.body_text and m.body_html:
        em.set_content(m.body_text)
        _add_alternative(em, m.body_html.encode("utf-8"), "html")
    elif m.body_html:
        em.add_alternative(m.body_html, subtype="html")
    elif m.body_text:
        em.set_content(m.body_text)
    else:
        # Ensure at least something is present
        em.set_content("")

    # Extra alternatives (e.g. text/calendar)
    for media_type, content in m.alternatives:
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        maintype, _, subtype = media_type.partition("/")
        if not subtype:
            # malformed; default to octet-stream
            maintype, subtype = "application", "octet-stream"
        if maintype == "text":
            _add_alternative(em, content_bytes, subtype=subtype)
        else:
            # Attach as separate non-text part
            em.add_attachment(content_bytes, maintype=maintype, subtype=subtype)

    # Attachments: in-memory
    for filename, blob, mimetype in m.attachments:
        maintype, subtype = (
            mimetype.split("/", 1)
            if mimetype and "/" in mimetype
            else ("application", "octet-stream")
        )
        em.add_attachment(bytes(blob), maintype=maintype, subtype=subtype, filename=filename)

    # Attachments: file paths
    for path in m.attachment_paths:
        with open(path, "rb") as fp:
            data = fp.read()
        # naive guess by extension; keep simple here
        em.add_attachment(
            data, maintype="application", subtype="octet-stream", filename=path.split("/")[-1]
        )

    if "Message-Id" not in em:
        em["Message-Id"] = make_msgid()

    return em


class _SMTPConnection:
    """
    Thin wrapper to reuse a single blocking smtplib.SMTP connection
    from async code via anyio.to_thread.
    """

    def __init__(
        self, host: str, port: int, use_tls: bool, username: str | None, password: str | None
    ) -> None:
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.username = username
        self.password = password
        self._client: smtplib.SMTP | None = None
        self._lock = anyio.Lock()

    async def open(self) -> None:
        async with self._lock:
            if self._client is not None:
                return

            def _connect() -> Any:
                client = smtplib.SMTP(self.host, self.port, timeout=30)
                client.ehlo()
                if self.use_tls:
                    client.starttls()
                    client.ehlo()
                if self.username:
                    client.login(self.username, self.password or "")
                return client

            self._client = await anyio.to_thread.run_sync(_connect)

    async def close(self) -> None:
        async with self._lock:
            if self._client is None:
                return

            def _quit(c: smtplib.SMTP) -> None:
                try:
                    c.quit()
                finally:
                    try:
                        c.close()
                    except Exception:
                        ...

            await anyio.to_thread.run_sync(_quit, self._client)
            self._client = None

    async def send(self, em: PyEmailMessage, recipients: Sequence[str]) -> None:
        async with self._lock:
            client = self._client

            def _sendmail(c: smtplib.SMTP) -> None:
                c.send_message(em, to_addrs=list(recipients))

            if client is None:
                raise RuntimeError("SMTP connection is not open")
            await anyio.to_thread.run_sync(_sendmail, client)


class SMTPBackend(BaseMailBackend):
    """
    Async-friendly SMTP backend with connection reuse.
    """

    def __init__(
        self,
        host: str,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        default_from_email: str | None = None,
    ) -> None:
        self.default_from_email = default_from_email or username
        self._conn = _SMTPConnection(host, port, use_tls, username, password)

    async def open(self) -> None:
        await self._conn.open()

    async def close(self) -> None:
        await self._conn.close()

    async def send(self, message: LilyaEmailMessage) -> None:
        if not message.from_email and self.default_from_email:
            message.from_email = self.default_from_email
        em = await build_email_message(message)
        await self._conn.send(em, message.all_recipients())

    async def send_many(self, messages: Sequence[LilyaEmailMessage]) -> None:
        # One connection for all messages (already open)
        for m in messages:
            if not m.from_email and self.default_from_email:
                m.from_email = self.default_from_email
            em = await build_email_message(m)
            await self._conn.send(em, m.all_recipients())
