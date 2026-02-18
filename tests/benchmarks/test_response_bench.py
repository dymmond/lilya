"""
Response serialization benchmarks.

Benchmark response creation and serialization overhead across different response types
and payload sizes. These benchmarks measure in-memory operations only (no I/O).
"""

import pytest

from lilya.background import Task
from lilya.responses import JSONResponse, Ok, StreamingResponse


@pytest.mark.benchmark
def test_ok_small_dict(benchmark):
    """Benchmark Ok() response with small dict payload."""
    data = {"status": "ok", "count": 42, "message": "success"}

    result = benchmark(Ok, data)

    assert result.status_code == 200
    assert b"ok" in result.body


@pytest.mark.benchmark
def test_ok_large_dict(benchmark):
    """Benchmark Ok() response with large dict payload (100 keys)."""
    data = {f"key_{i}": f"value_{i}" for i in range(100)}

    result = benchmark(Ok, data)

    assert result.status_code == 200
    assert b"key_0" in result.body
    assert b"key_99" in result.body


@pytest.mark.benchmark
def test_json_response_nested_structure(benchmark):
    """Benchmark JSONResponse with deeply nested structures."""
    data = {
        "users": [
            {
                "id": i,
                "name": f"User {i}",
                "profile": {
                    "email": f"user{i}@example.com",
                    "settings": {"notifications": True, "theme": "dark"},
                },
                "posts": [{"id": j, "title": f"Post {j}"} for j in range(5)],
            }
            for i in range(10)
        ],
        "meta": {"total": 10, "page": 1, "per_page": 10},
    }

    result = benchmark(JSONResponse, data)

    assert result.status_code == 200
    assert b"users" in result.body


@pytest.mark.benchmark
def test_streaming_response_creation(benchmark):
    """Benchmark StreamingResponse creation (no actual streaming)."""

    def generate_chunks():
        for i in range(10):
            yield f"chunk_{i}\n"

    result = benchmark(StreamingResponse, generate_chunks())

    assert result.status_code == 200
    assert hasattr(result, "body_iterator")


@pytest.mark.benchmark
def test_response_with_custom_headers(benchmark):
    """Benchmark response creation with custom headers (10 headers)."""
    headers = {
        "X-Custom-Header-1": "value1",
        "X-Custom-Header-2": "value2",
        "X-Custom-Header-3": "value3",
        "X-Custom-Header-4": "value4",
        "X-Custom-Header-5": "value5",
        "X-Request-ID": "req-12345",
        "X-API-Version": "v1",
        "X-Rate-Limit": "100",
        "X-User-Agent": "BenchmarkClient/1.0",
        "X-Correlation-ID": "corr-67890",
    }
    data = {"status": "ok"}

    result = benchmark(Ok, data, headers=headers)

    assert result.status_code == 200
    assert "X-Custom-Header-1" in result.headers
    assert result.headers["X-Request-ID"] == "req-12345"


@pytest.mark.benchmark
def test_json_response_with_background_task(benchmark):
    """Benchmark JSONResponse creation with background task."""
    task_executed = []

    def background_fn():
        task_executed.append(True)

    task = Task(background_fn)
    data = {"status": "ok", "task": "queued"}

    result = benchmark(JSONResponse, data, background=task)

    assert result.status_code == 200
    assert result.background is task


@pytest.mark.benchmark
def test_ok_response_list_of_dicts(benchmark):
    """Benchmark Ok() response with list of dictionaries."""
    data = [
        {"id": i, "name": f"Item {i}", "value": i * 10, "active": i % 2 == 0} for i in range(50)
    ]

    result = benchmark(Ok, data)

    assert result.status_code == 200
    assert b"Item" in result.body


@pytest.mark.benchmark
def test_json_response_with_unicode(benchmark):
    """Benchmark JSONResponse with unicode characters."""
    data = {
        "message": "Hello 世界 🌍",
        "description": "Unicode test: Ñoño, café, naïve",
        "emoji": "🚀💻📊",
        "languages": ["English", "Español", "中文", "日本語", "العربية"],
    }

    result = benchmark(JSONResponse, data)

    assert result.status_code == 200
    # Check that unicode is encoded properly
    assert len(result.body) > 0


@pytest.mark.benchmark
def test_ok_response_mixed_types(benchmark):
    """Benchmark Ok() response with mixed data types."""
    data = {
        "string": "test",
        "integer": 42,
        "float": 3.14159,
        "boolean": True,
        "null": None,
        "list": [1, 2, 3, 4, 5],
        "nested": {"a": 1, "b": 2, "c": 3},
    }

    result = benchmark(Ok, data)

    assert result.status_code == 200
    assert b"test" in result.body
    assert b"3.14159" in result.body
