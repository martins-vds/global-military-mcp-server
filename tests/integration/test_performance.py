"""Performance smoke tests.

T044 — Measure p95 response times, verify rate limiter serialization,
confirm circuit breaker behavior.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from pathlib import Path

import httpx
import pytest
import respx

from src.cache.store import FileCache
from src.domain.enums import EquipmentCategory
from src.domain.services import SearchService
from src.scraper.client import CircuitBreaker, RateLimiter

FIXTURES = Path(__file__).parent.parent / "fixtures" / "html"
AIRCRAFT_HTML = FIXTURES / "aircraft.html"


@pytest.fixture
def perf_cache(tmp_path):
    return FileCache(
        cache_dir=tmp_path / ".cache", default_ttl=86400.0, max_entries=500
    )


@pytest.fixture
def rate_limiter():
    return RateLimiter(min_interval=0.0, backoff_base=2.0, max_retries=3)


@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)


def _make_service(client, cache, rl, cb):
    return SearchService(
        http_client=client,
        cache=cache,
        rate_limiter=rl,
        circuit_breaker=cb,
    )


class TestCachedResponseTime:
    """Cached queries should complete in < 200 ms (p95)."""

    async def test_cached_p95_under_200ms(
        self, perf_cache, rate_limiter, circuit_breaker
    ):
        html = AIRCRAFT_HTML.read_text()

        async with httpx.AsyncClient() as client:
            with respx.mock:
                respx.get(url__startswith="https://www.globalmilitary.net/").mock(
                    return_value=httpx.Response(200, text=html)
                )
                svc = _make_service(client, perf_cache, rate_limiter, circuit_breaker)

                # Prime the cache
                await svc.search_equipment(category=EquipmentCategory.aircraft)

            # Now measure cached reads (no HTTP needed)
            timings: list[float] = []
            for _ in range(50):
                t0 = time.monotonic()
                result = await svc.search_equipment(category=EquipmentCategory.aircraft)
                elapsed_ms = (time.monotonic() - t0) * 1000
                timings.append(elapsed_ms)
                assert result.total_count > 0

        p95 = sorted(timings)[int(len(timings) * 0.95)]
        print(f"\nCached p95: {p95:.1f} ms  (mean: {statistics.mean(timings):.1f} ms)")
        assert p95 < 200, f"Cached p95 {p95:.1f} ms exceeds 200 ms target"


class TestUncachedResponseTime:
    """Uncached queries with mocked HTTP should complete in < 3 s (p95)."""

    async def test_uncached_p95_under_3s(self, tmp_path, circuit_breaker):
        html = AIRCRAFT_HTML.read_text()
        timings: list[float] = []

        async with httpx.AsyncClient() as client:
            with respx.mock:
                respx.get(url__startswith="https://www.globalmilitary.net/").mock(
                    return_value=httpx.Response(200, text=html)
                )

                for i in range(10):
                    # Fresh cache each iteration to force uncached path
                    cache = FileCache(
                        cache_dir=tmp_path / f".cache_{i}",
                        default_ttl=86400.0,
                        max_entries=500,
                    )
                    rl = RateLimiter(min_interval=0.0, backoff_base=2.0, max_retries=3)
                    svc = _make_service(client, cache, rl, circuit_breaker)

                    t0 = time.monotonic()
                    result = await svc.search_equipment(
                        category=EquipmentCategory.aircraft
                    )
                    elapsed_ms = (time.monotonic() - t0) * 1000
                    timings.append(elapsed_ms)
                    assert result.total_count > 0

        p95 = sorted(timings)[int(len(timings) * 0.95)]
        print(
            f"\nUncached p95: {p95:.1f} ms  (mean: {statistics.mean(timings):.1f} ms)"
        )
        assert p95 < 3000, f"Uncached p95 {p95:.1f} ms exceeds 3000 ms target"


class TestRateLimiterSerialization:
    """Rate limiter should serialize concurrent requests."""

    async def test_concurrent_requests_serialized(self, perf_cache, circuit_breaker):
        html = AIRCRAFT_HTML.read_text()
        rl = RateLimiter(min_interval=0.05, backoff_base=2.0, max_retries=3)

        async with httpx.AsyncClient() as client:
            with respx.mock:
                respx.get(url__startswith="https://www.globalmilitary.net/").mock(
                    return_value=httpx.Response(200, text=html)
                )

                # Use different cache keys by varying the query parameter
                categories = [EquipmentCategory.aircraft] * 3
                queries = ["alpha", "beta", "gamma"]

                svc = _make_service(client, perf_cache, rl, circuit_breaker)

                t0 = time.monotonic()
                tasks = [
                    svc.search_equipment(category=cat, query=q)
                    for cat, q in zip(categories, queries)
                ]
                results = await asyncio.gather(*tasks)
                total_ms = (time.monotonic() - t0) * 1000

                assert all(r.total_count > 0 for r in results)

                # 3 requests at 50ms min_interval ⇒ should take ≥ 100ms total
                # (first runs immediately, 2nd waits ~50ms, 3rd waits ~50ms)
                print(f"\n3 concurrent requests: {total_ms:.1f} ms total")
                assert total_ms >= 80, (
                    f"Concurrent requests completed too fast ({total_ms:.1f}ms); "
                    "rate limiter may not be serializing"
                )


class TestCircuitBreakerOpens:
    """Circuit breaker should open after 5 consecutive failures."""

    async def test_opens_after_five_failures(self, perf_cache, rate_limiter):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

        async with httpx.AsyncClient() as client:
            with respx.mock:
                respx.get(url__startswith="https://www.globalmilitary.net/").mock(
                    return_value=httpx.Response(500, text="Internal Server Error")
                )

                svc = _make_service(client, perf_cache, rate_limiter, cb)

                # Trigger 5 failures (rate_limiter will retry, but all will 5xx)
                failure_count = 0
                for _ in range(5):
                    try:
                        await svc.search_equipment(category=EquipmentCategory.aircraft)
                    except (RuntimeError, Exception):
                        failure_count += 1

                assert failure_count == 5

                # 6th call should fail immediately with circuit breaker open
                with pytest.raises(RuntimeError, match="(?i)circuit breaker"):
                    await svc.search_equipment(
                        category=EquipmentCategory.aircraft, query="should-fail-fast"
                    )
