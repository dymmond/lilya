import smtplib

import pytest

from lilya.contrib.mail import EmailMessage, Mailer
from lilya.contrib.mail.backends.smtp import SMTPBackend

pytestmark = pytest.mark.anyio


class DummySMTP:
    def __init__(self, *a, **kw):
        self.actions = []

    def ehlo(self):
        self.actions.append("ehlo")

    def starttls(self):
        self.actions.append("tls")

    def login(self, user, pwd):
        self.actions.append(("login", user))

    def send_message(self, msg, to_addrs=None):
        self.actions.append(("send", to_addrs))

    def quit(self):
        self.actions.append("quit")

    def close(self):
        self.actions.append("close")


class FailingSMTP(DummySMTP):
    def send_message(self, msg, to_addrs=None):
        raise smtplib.SMTPException("Simulated failure")


async def test_smtp_backend_sends(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)

    backend = SMTPBackend(host="smtp.test", port=25, username="user", password="pass")
    mailer = Mailer(backend=backend)
    await mailer.open()

    msg = EmailMessage(subject="smtp", to=["a@test"], body_text="hello")
    await mailer.send(msg)

    # Ensure DummySMTP recorded the send
    client = backend._conn._client

    assert any(action[0] == "send" for action in client.actions if isinstance(action, tuple))


async def test_smtp_connection_and_send(monkeypatch):
    dummy = DummySMTP()
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **kw: dummy)

    backend = SMTPBackend(host="smtp.test", port=25, username="user", password="pass")
    mailer = Mailer(backend=backend)

    await mailer.open()
    msg = EmailMessage(subject="smtp", to=["a@test"], body_text="hello")

    await mailer.send(msg)
    await mailer.close()

    # Ensure login and send occurred
    assert ("login", "user") in dummy.actions
    assert any(action[0] == "send" for action in dummy.actions if isinstance(action, tuple))


async def test_send_without_open_raises(monkeypatch):
    dummy = DummySMTP()
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **kw: dummy)

    backend = SMTPBackend(host="smtp.test", port=25)
    mailer = Mailer(backend=backend)

    msg = EmailMessage(subject="x", to=["a@test"], body_text="body")

    with pytest.raises(RuntimeError):
        await mailer.send(msg)


async def test_smtp_applies_default_from(monkeypatch):
    dummy = DummySMTP()
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **kw: dummy)

    backend = SMTPBackend(host="smtp.test", port=25, username="user", password="pass")
    mailer = Mailer(backend=backend)
    await mailer.open()

    msg = EmailMessage(subject="smtp", to=["a@test"], body_text="hello")

    assert msg.from_email is None

    await mailer.send(msg)

    assert msg.from_email == "user"  # default_from_email applied


async def test_smtp_error_propagates(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **kw: FailingSMTP())

    backend = SMTPBackend(host="smtp.test", port=25)
    mailer = Mailer(backend=backend)
    await mailer.open()

    msg = EmailMessage(subject="smtp", to=["a@test"], body_text="hello")

    with pytest.raises(smtplib.SMTPException):
        await mailer.send(msg)
