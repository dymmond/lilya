from __future__ import annotations

import asyncio
import statistics
import time
from dataclasses import dataclass

import httpx
import websockets


@dataclass(frozen=True)
class LatencySummary:
    count: int
    ok: int
    errors: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    ops_per_s: float


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


def _summarize(lat_ms: list[float], ok: int, errors: int, wall_s: float) -> LatencySummary:
    lat_ms_sorted = sorted(lat_ms)
    count = len(lat_ms_sorted)
    mean = statistics.fmean(lat_ms_sorted) if lat_ms_sorted else 0.0
    return LatencySummary(
        count=count,
        ok=ok,
        errors=errors,
        p50_ms=_percentile(lat_ms_sorted, 0.50),
        p95_ms=_percentile(lat_ms_sorted, 0.95),
        p99_ms=_percentile(lat_ms_sorted, 0.99),
        min_ms=(lat_ms_sorted[0] if lat_ms_sorted else 0.0),
        max_ms=(lat_ms_sorted[-1] if lat_ms_sorted else 0.0),
        mean_ms=mean,
        ops_per_s=(ok / wall_s if wall_s > 0 else 0.0),
    )


async def run_http_scenario(
    base_url: str,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None,
    query: str | None,
    body: bytes | None,
    expect_status: int,
    requests: int,
    concurrency: int,
    timeout_s: float = 30.0,
) -> LatencySummary:
    url = f"{base_url}{path}"
    if query:
        url = f"{url}?{query}"

    sem = asyncio.Semaphore(concurrency)
    lat_ms: list[float] = []
    ok = 0
    errors = 0

    async with httpx.AsyncClient(timeout=timeout_s) as client:

        async def one() -> None:
            nonlocal ok, errors
            async with sem:
                t0 = time.perf_counter_ns()
                try:
                    resp = await client.request(method, url, headers=headers, content=body)
                    t1 = time.perf_counter_ns()
                    lat_ms.append((t1 - t0) / 1_000_000.0)
                    if resp.status_code == expect_status:
                        ok += 1
                    else:
                        errors += 1
                except Exception:
                    t1 = time.perf_counter_ns()
                    lat_ms.append((t1 - t0) / 1_000_000.0)
                    errors += 1

        wall0 = time.perf_counter()
        await asyncio.gather(*[one() for _ in range(requests)])
        wall1 = time.perf_counter()

    return _summarize(lat_ms, ok, errors, wall1 - wall0)


async def run_ws_echo(
    ws_url: str,
    path: str,
    *,
    message: bytes,
    requests: int,
    concurrency: int,
    timeout_s: float = 30.0,
) -> LatencySummary:
    url = f"{ws_url}{path}"

    sem = asyncio.Semaphore(concurrency)
    lat_ms: list[float] = []
    ok = 0
    errors = 0

    async def one() -> None:
        nonlocal ok, errors
        async with sem:
            t0 = time.perf_counter_ns()
            try:
                async with websockets.connect(
                    url, open_timeout=timeout_s, close_timeout=timeout_s
                ) as ws:
                    await ws.send(message)
                    resp = await ws.recv()
                t1 = time.perf_counter_ns()
                lat_ms.append((t1 - t0) / 1_000_000.0)
                if isinstance(resp, str):
                    resp_b = resp.encode()
                else:
                    resp_b = resp
                if resp_b == message:
                    ok += 1
                else:
                    errors += 1
            except Exception:
                t1 = time.perf_counter_ns()
                lat_ms.append((t1 - t0) / 1_000_000.0)
                errors += 1

    wall0 = time.perf_counter()
    await asyncio.gather(*[one() for _ in range(requests)])
    wall1 = time.perf_counter()

    return _summarize(lat_ms, ok, errors, wall1 - wall0)
