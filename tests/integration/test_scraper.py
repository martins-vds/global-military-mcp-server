"""Integration tests for scraper pipeline with mocked HTTP via respx.

T020 — Equipment scraper full pipeline
T026 — Inventory scraper full pipeline
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from src.cache.store import FileCache
from src.domain.enums import EquipmentCategory, InventoryCategory
from src.domain.models import Equipment, Navy, SearchResult
from src.domain.services import SearchService
from src.scraper.client import CircuitBreaker, RateLimiter
from src.scraper.urls import BASE_URL

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "html"


def _make_service(tmp_path: Path) -> tuple[SearchService, httpx.AsyncClient]:
    """Create a SearchService with a real httpx.AsyncClient (for respx mocking)."""
    client = httpx.AsyncClient()
    cache = FileCache(cache_dir=tmp_path / "cache", default_ttl=3600, max_entries=100)
    rate_limiter = RateLimiter(min_interval=0.0, backoff_base=1.0, max_retries=2)
    circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
    svc = SearchService(
        http_client=client,
        cache=cache,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
    )
    return svc, client


class TestEquipmentScraperIntegration:
    """Full pipeline tests for equipment scraping with mocked HTTP."""

    @respx.mock
    async def test_success_aircraft_search(self, tmp_path):
        html = (FIXTURES_DIR / "aircraft.html").read_text()
        respx.get(f"{BASE_URL}/aircraft/").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_equipment(
                category=EquipmentCategory.aircraft, page=1
            )

        assert isinstance(result, SearchResult)
        assert len(result.items) == 3
        assert all(isinstance(i, Equipment) for i in result.items)

    @respx.mock
    async def test_paginated_response(self, tmp_path):
        html = (FIXTURES_DIR / "aircraft.html").read_text()
        respx.get(f"{BASE_URL}/aircraft/?page=2").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_equipment(
                category=EquipmentCategory.aircraft, page=2
            )

        assert result.page_info.current_page == 2

    @respx.mock
    async def test_empty_results(self, tmp_path):
        respx.get(f"{BASE_URL}/aircraft/?name=nonexistent").respond(
            200,
            text="<html><body><table class='table'><tbody></tbody></table></body></html>",
        )

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_equipment(
                category=EquipmentCategory.aircraft, query="nonexistent", page=1
            )

        assert result.items == []
        assert result.total_count == 0

    @respx.mock
    async def test_5xx_error_retries(self, tmp_path):
        html = (FIXTURES_DIR / "aircraft.html").read_text()
        route = respx.get(f"{BASE_URL}/aircraft/").mock(
            side_effect=[
                httpx.Response(500, text="Server Error"),
                httpx.Response(200, text=html),
            ]
        )

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_equipment(
                category=EquipmentCategory.aircraft, page=1
            )

        assert len(result.items) == 3
        assert route.call_count == 2

    @respx.mock
    async def test_missiles_search(self, tmp_path):
        html = (FIXTURES_DIR / "missiles.html").read_text()
        respx.get(f"{BASE_URL}/missiles/").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_equipment(
                category=EquipmentCategory.missiles, page=1
            )

        assert len(result.items) == 2
        assert result.category == "missiles"

    @respx.mock
    async def test_ships_search(self, tmp_path):
        html = (FIXTURES_DIR / "ships.html").read_text()
        respx.get(f"{BASE_URL}/ships/").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_equipment(
                category=EquipmentCategory.ships, page=1
            )

        assert len(result.items) == 2
        assert result.category == "ships"


class TestInventoryScraperIntegration:
    """Full pipeline tests for inventory scraping with mocked HTTP."""

    @respx.mock
    async def test_navies_full_pipeline(self, tmp_path):
        html = (FIXTURES_DIR / "navies.html").read_text()
        respx.get(f"{BASE_URL}/navies/").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_inventory(
                category=InventoryCategory.navies, page=1
            )

        assert isinstance(result, SearchResult)
        assert len(result.items) == 3
        assert result.category == "navies"

    @respx.mock
    async def test_air_bases_paginated(self, tmp_path):
        html = (FIXTURES_DIR / "air_bases.html").read_text()
        respx.get(f"{BASE_URL}/airbases/").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_inventory(
                category=InventoryCategory.air_bases, page=1
            )

        assert len(result.items) == 2
        assert result.category == "air_bases"

    @respx.mock
    async def test_nuclear_data(self, tmp_path):
        html = (FIXTURES_DIR / "nuclear.html").read_text()
        respx.get(f"{BASE_URL}/nuclear/").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_inventory(
                category=InventoryCategory.nuclear, page=1
            )

        assert len(result.items) == 2
        assert result.category == "nuclear"

    @respx.mock
    async def test_ranks_data(self, tmp_path):
        html = (FIXTURES_DIR / "ranks.html").read_text()
        respx.get(f"{BASE_URL}/ranks/").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_inventory(
                category=InventoryCategory.ranks, page=1
            )

        assert len(result.items) > 0
        assert result.category == "ranks"

    @respx.mock
    async def test_air_forces_data(self, tmp_path):
        html = (FIXTURES_DIR / "air_forces.html").read_text()
        respx.get(f"{BASE_URL}/air_forces/").respond(200, text=html)

        svc, client = _make_service(tmp_path)
        async with client:
            result = await svc.search_inventory(
                category=InventoryCategory.air_forces, page=1
            )

        assert len(result.items) == 2
        assert result.category == "air_forces"
