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
