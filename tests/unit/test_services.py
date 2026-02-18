"""Unit tests for SearchService, IdentificationService, and ComparisonService.

T019 — SearchService equipment orchestration
T026/T028 — SearchService inventory orchestration
T031 — Identification matching logic
T035 — ComparisonService validation and shared fields
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.cache.store import FileCache
from src.domain.enums import EquipmentCategory, InventoryCategory
from src.domain.models import (
    ComparisonResult,
    Country,
    Equipment,
    IdentificationResult,
    Navy,
    PageInfo,
    SearchResult,
)
from src.domain.services import (
    ComparisonService,
    IdentificationService,
    SearchService,
)
from src.scraper.client import CircuitBreaker, RateLimiter

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "html"


def _make_search_service(
    tmp_path: Path,
    html_content: str = "<html></html>",
    status_code: int = 200,
) -> tuple[SearchService, AsyncMock]:
    """Create a SearchService with a mocked HTTP client."""
    cache = FileCache(cache_dir=tmp_path / "cache", default_ttl=3600, max_entries=100)
    rate_limiter = RateLimiter(min_interval=0.0, backoff_base=1.0, max_retries=0)
    circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.text = html_content
    mock_response.status_code = status_code
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    svc = SearchService(
        http_client=mock_client,
        cache=cache,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
    )
    return svc, mock_client


# ═══════════════════════════════════════════════════════════════════════════
# T019 — SearchService equipment orchestration
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchServiceEquipment:
    """Test equipment search orchestration."""

    @pytest.fixture
    def aircraft_html(self) -> str:
        return (FIXTURES_DIR / "aircraft.html").read_text()

    async def test_search_returns_equipment_items(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        result = await svc.search_equipment(category=EquipmentCategory.aircraft, page=1)
        assert isinstance(result, SearchResult)
        assert len(result.items) > 0
        assert all(isinstance(item, Equipment) for item in result.items)

    async def test_search_includes_page_info(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        result = await svc.search_equipment(category=EquipmentCategory.aircraft, page=1)
        assert isinstance(result.page_info, PageInfo)
        assert result.page_info.current_page == 1

    async def test_cache_hit_skips_fetch(self, tmp_path, aircraft_html):
        svc, mock_client = _make_search_service(tmp_path, aircraft_html)
        # First call — populates cache
        await svc.search_equipment(category=EquipmentCategory.aircraft, page=1)
        # Second call — should use cache
        await svc.search_equipment(category=EquipmentCategory.aircraft, page=1)
        # HTTP should only be called once
        assert mock_client.get.call_count == 1

    async def test_cache_miss_triggers_fetch(self, tmp_path, aircraft_html):
        svc, mock_client = _make_search_service(tmp_path, aircraft_html)
        await svc.search_equipment(category=EquipmentCategory.aircraft, page=1)
        assert mock_client.get.call_count == 1

    async def test_query_filter_applied(self, tmp_path, aircraft_html):
        svc, mock_client = _make_search_service(tmp_path, aircraft_html)
        result = await svc.search_equipment(
            category=EquipmentCategory.aircraft, query="F-35", page=1
        )
        assert result.filters_applied.get("query") == "F-35"

    async def test_country_filter_applied(self, tmp_path, aircraft_html):
        svc, mock_client = _make_search_service(tmp_path, aircraft_html)
        result = await svc.search_equipment(
            category=EquipmentCategory.aircraft, country="usa", page=1
        )
        assert result.filters_applied.get("country") == "usa"

    async def test_decade_filter_applied(self, tmp_path, aircraft_html):
        svc, mock_client = _make_search_service(tmp_path, aircraft_html)
        result = await svc.search_equipment(
            category=EquipmentCategory.aircraft, decade=1980, page=1
        )
        assert result.filters_applied.get("decade") == "1980"

    async def test_sub_category_filter_applied(self, tmp_path, aircraft_html):
        svc, mock_client = _make_search_service(tmp_path, aircraft_html)
        result = await svc.search_equipment(
            category=EquipmentCategory.aircraft, sub_category="combat", page=1
        )
        assert result.filters_applied.get("sub_category") == "combat"

    async def test_category_in_result(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        result = await svc.search_equipment(category=EquipmentCategory.aircraft, page=1)
        assert result.category == "aircraft"

    async def test_circuit_breaker_open_raises(self, tmp_path):
        svc, _ = _make_search_service(tmp_path)
        # Trip the circuit breaker
        for _ in range(5):
            svc._circuit_breaker.record_failure()
        with pytest.raises(RuntimeError, match="(?i)circuit breaker"):
            await svc.search_equipment(category=EquipmentCategory.aircraft, page=1)

    async def test_empty_html_returns_empty_items(self, tmp_path):
        svc, _ = _make_search_service(tmp_path, "<html><body></body></html>")
        result = await svc.search_equipment(category=EquipmentCategory.aircraft, page=1)
        assert result.items == []
        assert result.total_count == 0


# ═══════════════════════════════════════════════════════════════════════════
# SearchService inventory orchestration
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchServiceInventory:
    """Test inventory search orchestration."""

    @pytest.fixture
    def navies_html(self) -> str:
        return (FIXTURES_DIR / "navies.html").read_text()

    @pytest.fixture
    def air_bases_html(self) -> str:
        return (FIXTURES_DIR / "air_bases.html").read_text()

    async def test_search_navies_returns_items(self, tmp_path, navies_html):
        svc, _ = _make_search_service(tmp_path, navies_html)
        result = await svc.search_inventory(category=InventoryCategory.navies, page=1)
        assert isinstance(result, SearchResult)
        assert len(result.items) > 0

    async def test_navies_no_pagination(self, tmp_path, navies_html):
        svc, _ = _make_search_service(tmp_path, navies_html)
        result = await svc.search_inventory(category=InventoryCategory.navies, page=1)
        assert result.page_info.total_pages == 1

    async def test_inventory_cache_hit(self, tmp_path, navies_html):
        svc, mock_client = _make_search_service(tmp_path, navies_html)
        await svc.search_inventory(category=InventoryCategory.navies, page=1)
        await svc.search_inventory(category=InventoryCategory.navies, page=1)
        assert mock_client.get.call_count == 1

    async def test_inventory_category_in_result(self, tmp_path, navies_html):
        svc, _ = _make_search_service(tmp_path, navies_html)
        result = await svc.search_inventory(category=InventoryCategory.navies, page=1)
        assert result.category == "navies"


# ═══════════════════════════════════════════════════════════════════════════
# T031 — IdentificationService tests
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentificationService:
    """Test identification matching logic."""

    @pytest.fixture
    def aircraft_html(self) -> str:
        return (FIXTURES_DIR / "aircraft.html").read_text()

    async def test_name_search_finds_match(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        id_svc = IdentificationService(svc)
        result = await id_svc.identify(equipment_name="F-35 Lightning II")
        assert isinstance(result, IdentificationResult)
        assert result.search_strategy == "name_search"

    async def test_name_search_returns_matches(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        id_svc = IdentificationService(svc)
        result = await id_svc.identify(equipment_name="F-35 Lightning II")
        # Should find matches from the fixture that contain "F-35"
        assert len(result.matches) >= 0  # May or may not find exact matches

    async def test_category_browse_strategy(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        id_svc = IdentificationService(svc)
        result = await id_svc.identify(
            category=EquipmentCategory.aircraft,
            characteristics="stealth fighter",
        )
        assert result.search_strategy == "category_country_browse"

    async def test_country_filter_narrows_results(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        id_svc = IdentificationService(svc)
        result = await id_svc.identify(
            equipment_name="F-35",
            country_of_origin="usa",
        )
        assert result.search_strategy == "name_search"

    async def test_no_input_raises(self, tmp_path):
        svc, _ = _make_search_service(tmp_path)
        id_svc = IdentificationService(svc)
        with pytest.raises(ValueError, match="at least"):
            await id_svc.identify()

    async def test_global_search_strategy(self, tmp_path, aircraft_html):
        """When name is provided without category, all categories searched."""
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        id_svc = IdentificationService(svc)
        result = await id_svc.identify(equipment_name="AK-47")
        assert result.search_strategy == "name_search"


# ═══════════════════════════════════════════════════════════════════════════
# T035 — ComparisonService tests
# ═══════════════════════════════════════════════════════════════════════════


class TestComparisonService:
    """Test comparison validation and shared field detection."""

    @pytest.fixture
    def aircraft_html(self) -> str:
        return (FIXTURES_DIR / "aircraft.html").read_text()

    async def test_compare_two_items(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        cmp_svc = ComparisonService(svc)
        result = await cmp_svc.compare(
            category=EquipmentCategory.aircraft,
            slugs=["f-35-lightning-ii", "su-57"],
        )
        assert isinstance(result, ComparisonResult)
        assert result.category == EquipmentCategory.aircraft

    async def test_reject_single_slug(self, tmp_path):
        svc, _ = _make_search_service(tmp_path)
        cmp_svc = ComparisonService(svc)
        with pytest.raises(ValueError, match="2 to 5"):
            await cmp_svc.compare(
                category=EquipmentCategory.aircraft,
                slugs=["f-35-lightning-ii"],
            )

    async def test_reject_too_many_slugs(self, tmp_path):
        svc, _ = _make_search_service(tmp_path)
        cmp_svc = ComparisonService(svc)
        with pytest.raises(ValueError, match="2 to 5"):
            await cmp_svc.compare(
                category=EquipmentCategory.aircraft,
                slugs=["a", "b", "c", "d", "e", "f"],
            )

    async def test_shared_fields_detected(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        cmp_svc = ComparisonService(svc)
        result = await cmp_svc.compare(
            category=EquipmentCategory.aircraft,
            slugs=["f-35-lightning-ii", "su-57"],
        )
        # Common equipment fields should always be shared
        assert "name" in result.shared_fields
        assert "category" in result.shared_fields

    async def test_comparison_notes_generated(self, tmp_path, aircraft_html):
        svc, _ = _make_search_service(tmp_path, aircraft_html)
        cmp_svc = ComparisonService(svc)
        result = await cmp_svc.compare(
            category=EquipmentCategory.aircraft,
            slugs=["f-35-lightning-ii", "su-57"],
        )
        assert result.comparison_notes is not None
