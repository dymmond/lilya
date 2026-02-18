"""Benchmark test configuration and markers."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register benchmark marker."""
    config.addinivalue_line(
        "markers", "benchmark: mark test as a benchmark test (use pytest-benchmark fixture)"
    )
