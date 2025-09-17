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


async def test_creates_directory_if_missing(tmp_path):
    new_dir = tmp_path / "mails"
    backend = FileBackend(directory=str(new_dir), create=True)
    await backend.open()
    assert new_dir.exists()


async def test_does_not_create_directory_if_create_false(tmp_path):
    new_dir = tmp_path / "mails"
    backend = FileBackend(directory=str(new_dir), create=False)

    # calling open should not create directory
    await backend.open()
    assert not new_dir.exists()


async def test_subject_sanitization(tmp_path):
    backend = FileBackend(directory=str(tmp_path))
    await backend.open()

    msg = EmailMessage(subject="Weird/Subject*", to=["a@test"], body_text="hi")
    await backend.send(msg)

    files = list(Path(tmp_path).glob("*.eml"))

    assert files
    assert "Weird" in files[0].name


async def test_file_backend_serializes_attachments(tmp_path):
    # create a file to attach
    f = tmp_path / "hello.txt"
    f.write_text("hello")

    backend = FileBackend(directory=str(tmp_path))
    await backend.open()

    mailer = Mailer(backend=backend)
    msg = EmailMessage(
        subject="attach",
        to=["a@test"],
        body_text="see attached",
        attachment_paths=[str(f)],
    )
    await mailer.send(msg)

    files = list(Path(tmp_path).glob("*.eml"))

    assert files

    content = files[0].read_text()

    assert "hello.txt" in content
    assert "see attached" in content
