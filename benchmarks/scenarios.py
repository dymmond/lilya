from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class HttpScenario:
    name: str
    method: str
    path: str
    headers: dict[str, str] | None = None
    query: str | None = None
    body: bytes | None = None
    expect_status: int = 200


@dataclass(frozen=True)
class WsScenario:
    name: str
    path: str
    message: bytes
    expect: Callable[[bytes], bool]


def http_scenarios(upload_bytes: int = 256_000) -> list[HttpScenario]:
    boundary = "----lilya-bench-boundary"
    file_content = b"x" * upload_bytes
    multipart = (
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="bench.bin"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + file_content
        + f"\r\n--{boundary}--\r\n".encode()
    )

    return [
        HttpScenario(name="plaintext", method="GET", path="/plaintext"),
        HttpScenario(name="json", method="GET", path="/json"),
        HttpScenario(name="params", method="GET", path="/params/123"),
        HttpScenario(name="query", method="GET", path="/query", query="a=1&b=two"),
        HttpScenario(name="headers", method="GET", path="/headers", headers={"x-bench": "1"}),
        HttpScenario(name="cookies", method="GET", path="/cookies"),
        HttpScenario(name="stream", method="GET", path="/stream"),
        HttpScenario(
            name="upload",
            method="POST",
            path="/upload",
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
            body=multipart,
        ),
    ]


def ws_scenarios() -> list[WsScenario]:
    payload = b"ping" * 8
    return [
        WsScenario(
            name="ws_echo",
            path="/ws-echo",
            message=payload,
            expect=lambda b: b == payload,
        )
    ]
