# Lilya Benchmarks (Palfrey-backed)

All benchmarks run every framework behind Palfrey for apples-to-apples server behavior.

## Install

```bash
pip install -e ".[benchmarks]"
```

## Run everything (HTTP + WebSocket)

```bash
python -m benchmarks.run --http-requests 50000 --concurrency 200
```

## Run a subset

```bash
python -m benchmarks.run --only lilya fastapi --scenarios plaintext json
python -m benchmarks.run --only litestar --ws-requests 20000 --ws-concurrency 200
```

## What gets benchmarked

HTTP:

- /plaintext
- /json
- /params/123
- /query?a=1&b=two
- /headers
- /cookies (sets + reads)
- /stream (chunked streaming)
- /upload (multipart)

WebSocket:

- /ws-echo (echo round-trip)


Outputs:

- benchmarks/out/results.json
- benchmarks/out/results.md
