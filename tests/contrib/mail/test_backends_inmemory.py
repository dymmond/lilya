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


async def test_send_many_accumulates_outbox():
    backend = InMemoryBackend()
    mailer = Mailer(backend=backend)

    msgs = [
        EmailMessage(subject="a", to=["a@test"], body_text="a"),
        EmailMessage(subject="b", to=["b@test"], body_text="b"),
    ]
    await mailer.send_many(msgs)

    assert len(backend.outbox) == 2
    assert backend.outbox[0].subject == "a"
    assert backend.outbox[1].subject == "b"


async def test_outbox_isolated_per_instance():
    b1 = InMemoryBackend()
    b2 = InMemoryBackend()

    msg = EmailMessage(subject="hi", to=["x@test"], body_text="x")
    await b1.send(msg)

    assert len(b1.outbox) == 1
    assert len(b2.outbox) == 0
