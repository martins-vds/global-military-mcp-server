"""FastMCP application instance — single source of truth.

Extracted to its own module to avoid circular imports between
server.py (lifespan / resources) and tools/*.py (tool handlers).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastmcp import FastMCP

from src.cache.store import FileCache
from src.scraper.client import CircuitBreaker, RateLimiter

# All tools are read-only scrapers
READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "idempotentHint": True,
    "openWorldHint": True,
}


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Create and teardown shared resources."""
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        headers={"User-Agent": "GlobalMilitaryMCP/0.1.0"},
        follow_redirects=True,
    )
    cache = FileCache(
        cache_dir=Path(".cache"),
        default_ttl=86400.0,  # 24 hours
        max_entries=500,
    )
    rate_limiter = RateLimiter(
        min_interval=1.0,
        backoff_base=2.0,
        max_retries=5,
    )
    circuit_breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60.0,
    )
    try:
        yield {
            "http_client": client,
            "cache": cache,
            "rate_limiter": rate_limiter,
            "circuit_breaker": circuit_breaker,
        }
    finally:
        await client.aclose()


mcp = FastMCP(
    "Global Military Database",
    instructions=(
        "Search military equipment and inventory data from GlobalMilitary.net. "
        "Use search_equipment for hardware (aircraft, missiles, ships, firearms, vehicles). "
        "Use search_inventory for force composition (navies, air forces, air bases, nuclear, ranks). "
        "Use compare_equipment to compare 2-5 items side-by-side. "
        "Use identify_from_image to identify equipment from descriptions."
    ),
    lifespan=app_lifespan,
)
