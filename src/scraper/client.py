"""HTTP client wrapper with rate limiting and circuit breaker."""

from __future__ import annotations

import asyncio
import time

import httpx


class RateLimiter:
    """Serializes HTTP requests with a minimum interval and exponential backoff.

    Uses asyncio.Lock to ensure only one request is in-flight at a time,
    plus a minimum interval between requests (default 1 second).
    """

    def __init__(
        self,
        min_interval: float = 1.0,
        backoff_base: float = 2.0,
        max_retries: int = 5,
    ) -> None:
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._min_interval = min_interval
        self._backoff_base = backoff_base
        self._max_retries = max_retries

    async def acquire(self) -> None:
        """Acquire the rate limiter — waits for min_interval since last request."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

    def backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for a retry attempt."""
        return self._backoff_base**attempt

    @property
    def max_retries(self) -> int:
        return self._max_retries


class CircuitBreaker:
    """Circuit breaker pattern for upstream service protection.

    States:
      - closed: Normal operation. Tracks consecutive failures.
      - open: After failure_threshold consecutive failures, rejects all
        requests immediately for recovery_timeout seconds.
      - half-open: After recovery_timeout elapses, allows one probe request.
        Success → closed. Failure → open again.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._consecutive_failures = 0
        self._state = "closed"
        self._opened_at: float = 0.0

    @property
    def state(self) -> str:
        """Current circuit breaker state: closed, open, or half_open."""
        if self._state == "open":
            if time.monotonic() - self._opened_at >= self._recovery_timeout:
                self._state = "half_open"
        return self._state

    def allow_request(self) -> bool:
        """Check if a request is allowed through the circuit."""
        current = self.state
        if current == "closed":
            return True
        if current == "half_open":
            return True  # Allow one probe request
        return False  # open

    def record_success(self) -> None:
        """Record a successful request — resets the circuit to closed."""
        self._consecutive_failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """Record a failed request — may trip the circuit to open."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self._state = "open"
            self._opened_at = time.monotonic()

    @property
    def failure_count(self) -> int:
        return self._consecutive_failures


async def fetch_with_resilience(
    client: httpx.AsyncClient,
    url: str,
    rate_limiter: RateLimiter,
    circuit_breaker: CircuitBreaker,
) -> httpx.Response:
    """Fetch a URL with rate limiting, circuit breaking, and retry logic.

    Raises:
        RuntimeError: If the circuit breaker is open.
        httpx.HTTPStatusError: After max retries exhausted.
    """
    if not circuit_breaker.allow_request():
        raise RuntimeError(
            "Circuit breaker is open — upstream service is unavailable. "
            "Please try again later."
        )

    last_error: Exception | None = None
    for attempt in range(rate_limiter.max_retries + 1):
        await rate_limiter.acquire()
        try:
            response = await client.get(url)
            response.raise_for_status()
            circuit_breaker.record_success()
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 or exc.response.status_code >= 500:
                circuit_breaker.record_failure()
                last_error = exc
                if attempt < rate_limiter.max_retries:
                    delay = rate_limiter.backoff_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
            raise
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            circuit_breaker.record_failure()
            last_error = exc
            if attempt < rate_limiter.max_retries:
                delay = rate_limiter.backoff_delay(attempt)
                await asyncio.sleep(delay)
                continue
            raise

    raise last_error  # type: ignore[misc]
