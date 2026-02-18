"""Unit tests for RateLimiter and CircuitBreaker."""

import asyncio
import time
from unittest.mock import patch

import pytest

from src.scraper.client import CircuitBreaker, RateLimiter


class TestRateLimiter:
    """T013: RateLimiter tests."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        return RateLimiter(min_interval=0.1, backoff_base=2.0, max_retries=3)

    async def test_first_acquire_immediate(self, limiter: RateLimiter):
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.05  # Should be near-instant

    async def test_second_acquire_waits(self, limiter: RateLimiter):
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.09  # Should wait ~0.1s

    async def test_backoff_delay_exponential(self, limiter: RateLimiter):
        assert limiter.backoff_delay(0) == 1.0  # 2^0
        assert limiter.backoff_delay(1) == 2.0  # 2^1
        assert limiter.backoff_delay(2) == 4.0  # 2^2
        assert limiter.backoff_delay(3) == 8.0  # 2^3

    async def test_max_retries(self, limiter: RateLimiter):
        assert limiter.max_retries == 3

    async def test_serializes_concurrent_access(self, limiter: RateLimiter):
        """Ensure concurrent acquire() calls are serialized."""
        timestamps: list[float] = []

        async def acquire_and_record():
            await limiter.acquire()
            timestamps.append(time.monotonic())

        await asyncio.gather(
            acquire_and_record(),
            acquire_and_record(),
            acquire_and_record(),
        )
        # Each successive acquire should be >= min_interval apart
        for i in range(1, len(timestamps)):
            diff = timestamps[i] - timestamps[i - 1]
            assert diff >= 0.09, f"Gap {i}: {diff:.3f}s < 0.1s"


class TestCircuitBreaker:
    """T013b: CircuitBreaker tests."""

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        return CircuitBreaker(failure_threshold=3, recovery_timeout=0.2)

    def test_initial_state_closed(self, breaker: CircuitBreaker):
        assert breaker.state == "closed"
        assert breaker.allow_request() is True

    def test_stays_closed_below_threshold(self, breaker: CircuitBreaker):
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "closed"
        assert breaker.allow_request() is True

    def test_opens_at_threshold(self, breaker: CircuitBreaker):
        for _ in range(3):
            breaker.record_failure()
        assert breaker.state == "open"
        assert breaker.allow_request() is False

    def test_success_resets_counter(self, breaker: CircuitBreaker):
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        assert breaker.failure_count == 0
        assert breaker.state == "closed"

    def test_half_open_after_timeout(self, breaker: CircuitBreaker):
        for _ in range(3):
            breaker.record_failure()
        assert breaker.state == "open"

        # Simulate timeout passing
        with patch("src.scraper.client.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 1.0
            assert breaker.state == "half_open"
            assert breaker.allow_request() is True

    def test_half_open_success_closes(self, breaker: CircuitBreaker):
        for _ in range(3):
            breaker.record_failure()
        # Force half-open
        breaker._state = "half_open"
        breaker.record_success()
        assert breaker.state == "closed"

    def test_half_open_failure_reopens(self, breaker: CircuitBreaker):
        for _ in range(3):
            breaker.record_failure()
        # Force half-open
        breaker._state = "half_open"
        breaker._consecutive_failures = 0  # Reset count for clean test
        for _ in range(3):
            breaker.record_failure()
        assert breaker.state == "open"

    def test_failure_count_property(self, breaker: CircuitBreaker):
        assert breaker.failure_count == 0
        breaker.record_failure()
        assert breaker.failure_count == 1
