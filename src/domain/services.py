"""Domain services: SearchService, IdentificationService, ComparisonService.

T022 — SearchService equipment orchestration
T028 — SearchService inventory orchestration
T032 — IdentificationService matching logic
T036 — ComparisonService comparison with shared fields
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

from src.cache.store import FileCache
from src.domain.enums import EquipmentCategory, InventoryCategory
from src.domain.models import (
    ComparisonResult,
    Country,
    Equipment,
    IdentificationMatch,
    IdentificationResult,
    PageInfo,
    SearchResult,
)
from src.scraper.client import CircuitBreaker, RateLimiter, fetch_with_resilience
from src.scraper.parser import (
    InventoryItem,
    parse_equipment_html,
    parse_inventory_html,
    parse_pagination,
)
from src.scraper.urls import build_equipment_url, build_inventory_url


class SearchService:
    """Orchestrates equipment and inventory searches.

    Pipeline: build URL → check cache → circuit breaker →
    rate limiter → fetch → parse HTML → cache result → return.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        cache: FileCache,
        rate_limiter: RateLimiter,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        self._client = http_client
        self._cache = cache
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker

    async def search_equipment(
        self,
        category: EquipmentCategory,
        *,
        query: str | None = None,
        country: str | None = None,
        sub_category: str | None = None,
        decade: int | None = None,
        page: int = 1,
    ) -> SearchResult:
        """Search equipment with full pipeline."""
        url = build_equipment_url(
            category,
            query=query,
            country=country,
            sub_category=sub_category,
            decade=decade,
            page=page,
        )

        # Build cache key from all parameters
        cache_key = f"equipment:{category.value}:{query}:{country}:{sub_category}:{decade}:{page}"

        # Check cache
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info(
                "cache_hit",
                extra={"cache_key": cache_key, "category": category.value},
            )
            return SearchResult(**cached)

        # Fetch with resilience
        logger.info(
            "fetch_start",
            extra={"url": url, "category": category.value},
        )
        t0 = time.monotonic()
        html = await self._fetch(url)
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "fetch_done",
            extra={"url": url, "elapsed_ms": round(elapsed_ms, 1)},
        )

        # Parse
        items = parse_equipment_html(html, category)
        page_info = parse_pagination(html, current_page=page)

        # Build filters_applied
        filters: dict[str, str] = {}
        if query:
            filters["query"] = query
        if country:
            filters["country"] = country
        if sub_category:
            filters["sub_category"] = sub_category
        if decade:
            filters["decade"] = str(decade)

        # Build query notes
        notes = self._build_equipment_notes(category, filters, page_info)

        result = SearchResult(
            items=items,
            total_count=len(items),
            page_info=page_info,
            query_notes=notes,
            category=category.value,
            filters_applied=filters,
        )

        # Cache the result
        self._cache.set(cache_key, result.model_dump())

        logger.info(
            "search_equipment_done",
            extra={
                "category": category.value,
                "result_count": len(items),
                "page": page,
                "cache_miss": True,
            },
        )

        return result

    async def search_inventory(
        self,
        category: InventoryCategory,
        *,
        query: str | None = None,
        country: str | None = None,
        page: int = 1,
    ) -> SearchResult:
        """Search inventory with full pipeline."""
        url = build_inventory_url(category, query=query, country=country, page=page)

        cache_key = f"inventory:{category.value}:{query}:{country}:{page}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info(
                "cache_hit",
                extra={"cache_key": cache_key, "category": category.value},
            )
            return SearchResult(**cached)

        logger.info(
            "fetch_start",
            extra={"url": url, "category": category.value},
        )
        t0 = time.monotonic()
        html = await self._fetch(url)
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "fetch_done",
            extra={"url": url, "elapsed_ms": round(elapsed_ms, 1)},
        )

        items = parse_inventory_html(html, category)
        page_info = parse_pagination(html, current_page=page)

        filters: dict[str, str] = {}
        if query:
            filters["query"] = query
        if country:
            filters["country"] = country

        notes = self._build_inventory_notes(category, filters, page_info)

        result = SearchResult(
            items=items,
            total_count=len(items),
            page_info=page_info,
            query_notes=notes,
            category=category.value,
            filters_applied=filters,
        )

        self._cache.set(cache_key, result.model_dump())

        logger.info(
            "search_inventory_done",
            extra={
                "category": category.value,
                "result_count": len(items),
                "page": page,
                "cache_miss": True,
            },
        )

        return result

    async def _fetch(self, url: str) -> str:
        """Fetch HTML with rate limiting and circuit breaking."""
        response = await fetch_with_resilience(
            self._client, url, self._rate_limiter, self._circuit_breaker
        )
        return response.text

    def _build_equipment_notes(
        self,
        category: EquipmentCategory,
        filters: dict[str, str],
        page_info: PageInfo,
    ) -> str:
        parts = []
        if "query" in filters:
            parts.append(f"Searched {category.value} by name: {filters['query']}")
        else:
            parts.append(f"Browsing {category.value}")

        filter_parts = []
        if "country" in filters:
            filter_parts.append(f"country: {filters['country']}")
        if "decade" in filters:
            filter_parts.append(f"decade: {filters['decade']}")
        if "sub_category" in filters:
            filter_parts.append(f"sub-category: {filters['sub_category']}")

        if filter_parts:
            parts.append(f"filtered by {', '.join(filter_parts)}")

        if page_info.total_pages > 1:
            parts.append(f"page {page_info.current_page} of {page_info.total_pages}")

        return ", ".join(parts)

    def _build_inventory_notes(
        self,
        category: InventoryCategory,
        filters: dict[str, str],
        page_info: PageInfo,
    ) -> str:
        parts = [f"{category.value.replace('_', ' ').title()} listing"]

        if not category.has_pagination:
            parts.append("all results on single page (no pagination)")
        elif page_info.total_pages > 1:
            parts.append(f"page {page_info.current_page} of {page_info.total_pages}")

        if "country" in filters:
            parts.append(f"country: {filters['country']}")

        return ": ".join(parts[:1]) + (
            ", " + ", ".join(parts[1:]) if len(parts) > 1 else ""
        )


class IdentificationService:
    """Identify equipment from text descriptions.

    Strategies:
      1. name_search — direct name search across all/specified categories
      2. category_country_browse — browse category with country filter
      3. global_search — fallback search across all categories
    """

    def __init__(self, search_service: SearchService) -> None:
        self._search = search_service

    async def identify(
        self,
        *,
        equipment_name: str | None = None,
        category: EquipmentCategory | None = None,
        characteristics: str | None = None,
        country_of_origin: str | None = None,
    ) -> IdentificationResult:
        """Identify equipment from provided parameters."""
        if not equipment_name and not (category and characteristics):
            raise ValueError(
                "Please provide at least an equipment name or a category with "
                "visual characteristics."
            )

        matches: list[IdentificationMatch] = []
        strategy: str

        if equipment_name:
            strategy = "name_search"
            matches = await self._search_by_name(
                equipment_name, category, country_of_origin
            )
        else:
            strategy = "category_country_browse"
            assert category is not None  # validated above
            matches = await self._browse_category(
                category, characteristics, country_of_origin
            )

        notes = self._build_notes(equipment_name, matches, strategy)

        return IdentificationResult(
            matches=matches,
            identification_notes=notes,
            search_strategy=strategy,
        )

    async def _search_by_name(
        self,
        name: str,
        category: EquipmentCategory | None,
        country: str | None,
    ) -> list[IdentificationMatch]:
        """Search by name across specified or all categories."""
        matches: list[IdentificationMatch] = []

        categories = [category] if category else list(EquipmentCategory)

        for cat in categories:
            result = await self._search.search_equipment(
                category=cat,
                query=name,
                country=country,
            )
            for item in result.items:
                if isinstance(item, Equipment):
                    reason = f"Name match: '{name}' found in {cat.value} database"
                    if name.lower() in item.name.lower():
                        reason = f"Direct name match: {item.name}"
                    matches.append(
                        IdentificationMatch(equipment=item, match_reason=reason)
                    )

        return matches

    async def _browse_category(
        self,
        category: EquipmentCategory,
        characteristics: str | None,
        country: str | None,
    ) -> list[IdentificationMatch]:
        """Browse category with optional country filter."""
        result = await self._search.search_equipment(
            category=category,
            country=country,
        )
        matches: list[IdentificationMatch] = []
        for item in result.items:
            if isinstance(item, Equipment):
                reason = f"Category match: {category.value}." + (
                    f" Visual characteristics: {characteristics}"
                    if characteristics
                    else ""
                )
                matches.append(IdentificationMatch(equipment=item, match_reason=reason))
        return matches

    def _build_notes(
        self,
        name: str | None,
        matches: list[IdentificationMatch],
        strategy: str,
    ) -> str:
        if not matches:
            return (
                f"No matching equipment found"
                + (f" for '{name}'" if name else "")
                + ". Try providing more specific details."
            )
        if name and any(name.lower() in m.equipment.name.lower() for m in matches):
            return f"Exact match found for {name}."
        return f"Found {len(matches)} potential match(es) using {strategy} strategy."


class ComparisonService:
    """Compare 2-5 equipment items side-by-side.

    Fetches all items in the category, finds matches by slug,
    and computes shared fields across the matched items.
    """

    def __init__(self, search_service: SearchService) -> None:
        self._search = search_service

    async def compare(
        self,
        category: EquipmentCategory,
        slugs: list[str],
    ) -> ComparisonResult:
        """Compare equipment items by slug within a category."""
        if len(slugs) < 2 or len(slugs) > 5:
            raise ValueError(
                f"Please provide 2 to 5 items to compare. Received {len(slugs)}."
            )

        # Fetch category listing to find items by slug
        result = await self._search.search_equipment(category=category)

        # Build slug lookup
        slug_map: dict[str, Equipment] = {}
        for item in result.items:
            if isinstance(item, Equipment):
                slug_map[item.slug] = item

        matched_items: list[Equipment] = []
        for slug in slugs:
            if slug in slug_map:
                matched_items.append(slug_map[slug])
            else:
                # Item not found in first page — could need pagination
                # For now, create a placeholder
                matched_items.append(
                    Equipment(
                        name=slug.replace("-", " ").title(),
                        slug=slug,
                        country=Country(iso3="unk", name="Unknown"),
                        category=category,
                        detail_url=f"/{category.value}/{slug}/",
                    )
                )

        shared_fields = self._compute_shared_fields(matched_items)
        notes = self._build_notes(matched_items, category)

        return ComparisonResult(
            items=matched_items,
            category=category,
            shared_fields=shared_fields,
            comparison_notes=notes,
        )

    def _compute_shared_fields(self, items: list[Equipment]) -> list[str]:
        """Find fields that have non-None values in ALL items."""
        if not items:
            return []

        # Check each field across all items
        candidate_fields = [
            "name",
            "slug",
            "country",
            "category",
            "sub_category",
            "detail_url",
            "manufacturer",
            "produced",
            "description",
            "thumbnail_url",
            "range_km",
            "max_speed",
            "ship_type",
            "year",
            "firearm_category",
        ]

        shared = []
        for field in candidate_fields:
            if all(getattr(item, field, None) is not None for item in items):
                shared.append(field)

        return shared

    def _build_notes(self, items: list[Equipment], category: EquipmentCategory) -> str:
        countries = [item.country.name for item in items]
        names = [item.name for item in items]
        return f"Comparing {len(items)} {category.value}: " + " vs ".join(
            f"{n} ({c})" for n, c in zip(names, countries)
        )
