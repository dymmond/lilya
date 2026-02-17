"""
Test media-type escaping in FileResponse multipart range handling.

Per RFC 7230, HTTP headers must not contain line folding (line breaks).
This test ensures media types are properly sanitized when used in
multipart range response subheaders (the content-type lines inside
the multipart/byteranges body).

IMPORTANT: These tests use raw ASGI invocation (scope/receive/send)
instead of TestClient because TestClient enforces ASGI spec conformance
and would reject malformed media types before the FileResponse multipart
code path executes.
"""

import os
import tempfile
import typing
from asyncio import Queue

import anyio
import pytest

from lilya.responses import FileResponse


@pytest.mark.anyio
async def test_multipart_subheader_media_type_is_escaped():
    """
    Test that media_type with spaces/newlines is escaped in multipart subheaders.

    This is the core test for the RFC 7230 compliance fix at responses.py:1143-1144.
    The FileResponse multipart code strips whitespace/newlines from media_type
    when building the content-type line inside each multipart part's subheader.
    """
    # Create temp file with enough bytes for multi-range request
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
        f.write(b"0123456789" * 100)  # 1000 bytes
        temp_path = f.name

    try:
        # CRITICAL: Must set range_multipart_boundary=True to reach multipart code path
        # Without it, max_ranges=1 and multi-range requests are collapsed to single-range
        fresponse = FileResponse(
            path=temp_path,
            filename="test.txt",
            media_type="text/plain; \n charset=utf-8",  # Intentional spaces/newlines
            range_multipart_boundary=True,
        )
        responses: Queue[typing.Any] = Queue()

        # Custom send coroutine (raw ASGI pattern from test_responses.py:497-501)
        async def put(message: typing.Any) -> None:
            if "file" in message:
                rob = await anyio.open_file(message["file"], "rb", closefd=False)
                message["body"] = await rob.read(message["count"])
            await responses.put(message)

        # Invoke FileResponse directly with raw ASGI scope/receive/send
        # This bypasses TestClient's conformance checker
        await fresponse(
            {
                "extensions": {},
                "type": "http.request",
                "headers": [("range", b"bytes=0-99,200-299")],  # Multi-range request
            },
            None,  # receive not needed for FileResponse
            put,  # send = our custom put coroutine
        )

        # Collect response start message
        response_start = await responses.get()
        assert response_start["status"] == 206

        # Collect all body chunks
        body_chunks = []
        while True:
            message = await responses.get()
            if message["type"] == "http.response.body":
                body_chunks.append(message["body"])
                if not message.get("more_body", False):
                    break

        # Combine body chunks
        body = b"".join(body_chunks).decode("utf-8", errors="ignore")

        # Verify the multipart subheaders have NO literal newlines in content-type lines
        # The media_type should be sanitized: "text/plain;charset=utf-8" (no spaces, no \n)
        for line in body.split("\n"):
            if line.lower().startswith("content-type:"):
                # Line should not have extra newlines embedded (would break HTTP)
                assert "\r" not in line  # No carriage returns
                # Sanitized media type should have no spaces: "text/plain;charset=utf-8"
                assert "charset=utf-8" in line
                # Verify no double spaces or literal newlines remain
                assert " \n " not in line
                assert "  " not in line

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.anyio
async def test_multipart_subheader_clean_media_type():
    """
    Test that clean media types work correctly in multipart subheaders.

    This is a sanity check that the multipart code path works for normal
    (non-malformed) media types.
    """
    # Create temp file with enough bytes for multi-range request
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".bin") as f:
        f.write(b"X" * 1000)
        temp_path = f.name

    try:
        fresponse = FileResponse(
            path=temp_path,
            filename="test.bin",
            media_type="application/octet-stream",  # Clean media type
            range_multipart_boundary=True,
        )
        responses: Queue[typing.Any] = Queue()

        async def put(message: typing.Any) -> None:
            if "file" in message:
                rob = await anyio.open_file(message["file"], "rb", closefd=False)
                message["body"] = await rob.read(message["count"])
            await responses.put(message)

        await fresponse(
            {
                "extensions": {},
                "type": "http.request",
                "headers": [("range", b"bytes=0-99,500-599")],
            },
            None,
            put,
        )

        response_start = await responses.get()
        assert response_start["status"] == 206

        # Collect body
        body_chunks = []
        while True:
            message = await responses.get()
            if message["type"] == "http.response.body":
                body_chunks.append(message["body"])
                if not message.get("more_body", False):
                    break

        body = b"".join(body_chunks).decode("utf-8", errors="ignore")

        # Verify the multipart subheader contains the expected content-type
        assert "content-type: application/octet-stream" in body.lower()
        # Verify boundary is present (multipart/byteranges response)
        assert f"--{fresponse.range_multipart_boundary}" in body

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
