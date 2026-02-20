from __future__ import annotations

import argparse
import asyncio
import http.client
import os
import signal
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .load import run_http_scenario, run_ws_echo
from .report import write_json, write_markdown
from .scenarios import http_scenarios, ws_scenarios

FRAMEWORK_APPS: dict[str, str] = {
    "lilya": "benchmarks.apps.lilya_app:app",
    "starlette": "benchmarks.apps.starlette_app:app",
    "fastapi": "benchmarks.apps.fastapi_app:app",
    "litestar": "benchmarks.apps.litestar_app:app",
    "ravyn": "benchmarks.apps.ravyn_app:app",
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def _spawn_palfrey(
    app_path: str,
    host: str,
    port: int,
    *,
    framework: str,
    palfrey_logs: str,
    logs_dir: Path,
) -> subprocess.Popen:
    cmd = ["palfrey", app_path, "--host", host, "--port", str(port)]
    _log(f"[palfrey] starting: {' '.join(cmd)}")

    env = os.environ.copy()

    # Avoid per-request logging affecting benchmark results.
    if palfrey_logs == "discard":
        return subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if palfrey_logs == "file":
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"palfrey_{framework}_{port}.log"
        log_file = open(log_path, "wb")
        _log(f"[palfrey] logs -> {log_path}")
        proc = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=log_file)
        # Keep the file handle alive and close it on termination.
        proc._bench_log_file = log_file
        return proc

    # inherit
    return subprocess.Popen(cmd, env=env)


def _wait_ready(host: str, port: int, timeout_s: float = 10.0) -> None:
    """Wait until the server accepts connections and responds to a simple request."""
    t0 = time.time()
    last_err: Exception | None = None

    while time.time() - t0 < timeout_s:
        try:
            conn = http.client.HTTPConnection(host, port, timeout=1.0)
            conn.request("GET", "/plaintext")
            resp = conn.getresponse()
            # Any HTTP response means the server is up and routing.
            resp.read()
            conn.close()
            return
        except Exception as e:
            last_err = e
            time.sleep(0.05)

    raise RuntimeError(f"Server failed to become ready in time: {last_err}")


def _terminate(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    log_file = getattr(proc, "_bench_log_file", None)
    if log_file is not None:
        try:
            log_file.close()
        except Exception:
            pass


async def _run_one_framework(
    name: str,
    app_path: str,
    *,
    host: str,
    port: int,
    http_requests: int,
    concurrency: int,
    ws_requests: int,
    ws_concurrency: int,
    scenario_filter: set[str] | None,
    palfrey_logs: str,
    logs_dir: Path,
) -> dict[str, Any]:
    proc = _spawn_palfrey(
        app_path,
        host,
        port,
        framework=name,
        palfrey_logs=palfrey_logs,
        logs_dir=logs_dir,
    )
    try:
        # Give Palfrey a moment to fail fast if it is going to.
        time.sleep(0.05)
        if proc.poll() is not None:
            raise RuntimeError(f"Palfrey exited early with code {proc.returncode}")

        _wait_ready(host, port)
        base_url = f"http://{host}:{port}"
        ws_url = f"ws://{host}:{port}"

        fw_result: dict[str, Any] = {"http": {}, "ws": {}}
        _log(f"\n=== {name} ===")
        _log(f"[http] base_url={base_url} requests={http_requests} concurrency={concurrency}")

        http_index = 0
        for sc in http_scenarios():
            if scenario_filter and sc.name not in scenario_filter:
                continue
            http_index += 1
            _log(f"[http] ({http_index}) running scenario: {sc.name} {sc.method} {sc.path}")
            summary = await run_http_scenario(
                base_url,
                sc.method,
                sc.path,
                headers=sc.headers,
                query=sc.query,
                body=sc.body,
                expect_status=sc.expect_status,
                requests=http_requests,
                concurrency=concurrency,
            )
            fw_result["http"][sc.name] = asdict(summary)
            _log(
                f"[http] ({http_index}) done: {sc.name} "
                f"ok={summary.ok} err={summary.errors} "
                f"ops/s={summary.ops_per_s:.2f} p95={summary.p95_ms:.3f}ms"
            )

        _log(f"[ws] ws_url={ws_url} requests={ws_requests} concurrency={ws_concurrency}")

        ws_index = 0
        for sc in ws_scenarios():
            if scenario_filter and sc.name not in scenario_filter:
                continue
            ws_index += 1
            _log(f"[ws] ({ws_index}) running scenario: {sc.name} {sc.path}")
            summary = await run_ws_echo(
                ws_url,
                sc.path,
                message=sc.message,
                requests=ws_requests,
                concurrency=ws_concurrency,
            )
            fw_result["ws"][sc.name] = asdict(summary)
            _log(
                f"[ws] ({ws_index}) done: {sc.name} "
                f"ok={summary.ok} err={summary.errors} "
                f"ops/s={summary.ops_per_s:.2f} p95={summary.p95_ms:.3f}ms"
            )

        return fw_result
    finally:
        _terminate(proc)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--only", nargs="*", default=None, help="Frameworks to run (default: all)")
    p.add_argument(
        "--scenarios",
        nargs="*",
        default=None,
        help="Scenario names to run (default: all)",
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8010)
    p.add_argument("--http-requests", type=int, default=50_000)
    p.add_argument("--concurrency", type=int, default=200)
    p.add_argument("--ws-requests", type=int, default=20_000)
    p.add_argument("--ws-concurrency", type=int, default=200)
    p.add_argument(
        "--palfrey-logs",
        choices=["discard", "inherit", "file"],
        default="discard",
        help="Where to send Palfrey stdout/stderr. 'discard' is best for accurate benchmarks.",
    )
    p.add_argument(
        "--logs-dir",
        default="benchmarks/out",
        help="Directory for Palfrey logs when --palfrey-logs=file",
    )
    args = p.parse_args()

    selected = list(FRAMEWORK_APPS.keys()) if not args.only else args.only
    unknown = [x for x in selected if x not in FRAMEWORK_APPS]
    if unknown:
        raise SystemExit(f"Unknown frameworks: {unknown}. Known: {list(FRAMEWORK_APPS)}")

    scenario_filter = set(args.scenarios) if args.scenarios else None
    _log(f"Running frameworks: {selected}")
    _log(f"Palfrey logs: {args.palfrey_logs}")

    logs_dir = Path(args.logs_dir)

    results: dict[str, Any] = {
        "meta": {
            "server": "palfrey",
            "host": args.host,
            "base_port": args.port,
            "http_requests": args.http_requests,
            "concurrency": args.concurrency,
            "ws_requests": args.ws_requests,
            "ws_concurrency": args.ws_concurrency,
        },
        "frameworks": {},
    }

    async def runner() -> None:
        port = args.port
        for fw in selected:
            results["frameworks"][fw] = await _run_one_framework(
                fw,
                FRAMEWORK_APPS[fw],
                host=args.host,
                port=port,
                http_requests=args.http_requests,
                concurrency=args.concurrency,
                ws_requests=args.ws_requests,
                ws_concurrency=args.ws_concurrency,
                scenario_filter=scenario_filter,
                palfrey_logs=args.palfrey_logs,
                logs_dir=logs_dir,
            )
            port += 1

    asyncio.run(runner())

    j = write_json(results)
    m = write_markdown(results)
    _log(f"\nWrote: {j}")
    _log(f"Wrote: {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
