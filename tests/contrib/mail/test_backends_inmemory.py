import pytest

from lilya.contrib.mail import EmailMessage, Mailer
from lilya.contrib.mail.backends.inmemory import InMemoryBackend

pytestmark = pytest.mark.anyio


async def test_inmemory_backend_outbox():
    backend = InMemoryBackend()
    mailer = Mailer(backend=backend)
    msg = EmailMessage(subject="memo", to=["mem@test"], body_text="memo")
    await mailer.send(msg)
    assert backend.outbox[0].subject == "memo"
