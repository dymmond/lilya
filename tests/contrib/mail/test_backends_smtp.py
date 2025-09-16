import smtplib

import pytest

from lilya.contrib.mail import EmailMessage, Mailer
from lilya.contrib.mail.backends.smtp import SMTPBackend

pytestmark = pytest.mark.anyio


class DummySMTP:
    def __init__(self, *a, **kw):
        pass

    def ehlo(self):
        pass

    def starttls(self):
        pass

    def login(self, user, pwd):
        self.logged_in = (user, pwd)

    def send_message(self, msg, to_addrs=None):
        self.sent = (msg, to_addrs)

    def quit(self):
        pass

    def close(self):
        pass


async def test_smtp_backend_sends(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)

    backend = SMTPBackend(host="smtp.test", port=25, username="user", password="pass")
    mailer = Mailer(backend=backend)
    await mailer.open()
    msg = EmailMessage(subject="smtp", to=["a@test"], body_text="hello")
    await mailer.send(msg)

    # Ensure DummySMTP recorded the send
    client = backend._conn._client
    assert client.sent
    assert "smtp" in str(client.sent[0])
