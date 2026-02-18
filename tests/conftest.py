"""Shared test fixtures for FastMCP Client, temp cache, and mock HTTP transport."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cache.store import FileCache
from src.scraper.client import CircuitBreaker, RateLimiter


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    """Temporary cache directory for tests."""
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def file_cache(tmp_cache_dir: Path) -> FileCache:
    """FileCache instance with temporary directory and short TTL."""
    return FileCache(cache_dir=tmp_cache_dir, default_ttl=3600.0, max_entries=100)


@pytest.fixture
def rate_limiter() -> RateLimiter:
    """RateLimiter with short interval for fast tests."""
    return RateLimiter(min_interval=0.01, backoff_base=1.1, max_retries=2)


@pytest.fixture
def circuit_breaker() -> CircuitBreaker:
    """CircuitBreaker with low threshold for fast tests."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
