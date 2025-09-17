import pytest

from lilya.contrib.mail import EmailMessage, Mailer
from lilya.contrib.mail.backends.console import ConsoleBackend

pytestmark = pytest.mark.anyio


async def test_console_backend_output(capsys):
    backend = ConsoleBackend()
    mailer = Mailer(backend=backend)
    msg = EmailMessage(subject="console", to=["a@test"], body_text="hi")

    await mailer.send(msg)
    captured = capsys.readouterr()

    assert "console" in captured.out
    assert "hi" in captured.out


async def test_multiple_messages_console_output(capsys):
    backend = ConsoleBackend()
    mailer = Mailer(backend=backend)

    msg1 = EmailMessage(subject="one", to=["a@x.com"], body_text="hi1")
    msg2 = EmailMessage(subject="two", to=["b@x.com"], body_text="hi2")

    await mailer.send(msg1)
    await mailer.send(msg2)

    output = capsys.readouterr().out

    assert "one" in output
    assert "two" in output


async def test_headers_show_in_console(capsys):
    backend = ConsoleBackend()
    mailer = Mailer(backend=backend)

    msg = EmailMessage(
        subject="hdr",
        to=["a@x.com"],
        body_text="hi",
        headers={"X-Debug": "on"},
    )
    await mailer.send(msg)

    output = capsys.readouterr().out

    assert "X-Debug: on" in output
