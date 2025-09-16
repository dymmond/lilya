from pathlib import Path

import pytest

from lilya.contrib.mail import EmailMessage, Mailer
from lilya.contrib.mail.backends.file import FileBackend

pytestmark = pytest.mark.anyio


async def test_file_backend_writes_eml(tmp_path):
    backend = FileBackend(directory=str(tmp_path))
    mailer = Mailer(backend=backend)
    msg = EmailMessage(subject="filetest", to=["x@test"], body_text="body")
    await mailer.send(msg)

    files = list(Path(tmp_path).glob("*.eml"))
    assert files, "Expected .eml file"
    content = files[0].read_text()
    assert "filetest" in content
    assert "body" in content
