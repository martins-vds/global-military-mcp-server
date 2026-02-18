"""URL construction for GlobalMilitary.net pages."""

from __future__ import annotations

from src.domain.enums import EquipmentCategory, InventoryCategory

BASE_URL = "https://www.globalmilitary.net"


def equipment_list_url(category: EquipmentCategory) -> str:
    """Base listing URL for an equipment category."""
    return f"{BASE_URL}{category.url_segment}"


def equipment_search_url(category: EquipmentCategory, query: str) -> str:
    """Search URL using the ?name= parameter."""
    return f"{BASE_URL}{category.url_segment}?name={query}"


def equipment_paginate_url(category: EquipmentCategory, page: int) -> str:
    """Paginated listing URL."""
    return f"{BASE_URL}{category.url_segment}?page={page}"


def equipment_filter_category_url(
    category: EquipmentCategory, sub_category: str
) -> str:
    """Filter by sub-category slug."""
    return f"{BASE_URL}{category.url_segment}category/{sub_category}/"


def equipment_filter_country_url(category: EquipmentCategory, iso3: str) -> str:
    """Filter by country ISO-3 code."""
    return f"{BASE_URL}{category.url_segment}country/{iso3}/"


def equipment_filter_decade_url(category: EquipmentCategory, decade: int) -> str:
    """Filter by decade year."""
    return f"{BASE_URL}{category.url_segment}decade/{decade}/"


def equipment_detail_url(category: EquipmentCategory, slug: str) -> str:
    """Detail page URL for a specific equipment item."""
    return f"{BASE_URL}{category.url_segment}{slug}/"


def inventory_list_url(category: InventoryCategory) -> str:
    """Base listing URL for an inventory category."""
    return f"{BASE_URL}{category.url_segment}"


def inventory_paginate_url(category: InventoryCategory, page: int) -> str:
    """Paginated inventory listing URL."""
    return f"{BASE_URL}{category.url_segment}?page={page}"


def global_search_url(query: str) -> str:
    """Global search URL across all categories."""
    return f"{BASE_URL}/search/?q={query}"


def build_equipment_url(
    category: EquipmentCategory,
    *,
    query: str | None = None,
    country: str | None = None,
    sub_category: str | None = None,
    decade: int | None = None,
    page: int = 1,
) -> str:
    """Build the appropriate equipment URL based on provided filters.

    Priority order (only one filter type applies):
      1. sub_category → filter_category URL (can combine with page)
      2. country → filter_country URL (can combine with page)
      3. decade → filter_decade URL (can combine with page)
      4. query → search URL (can combine with page)
      5. page only → paginate URL
      6. none → list URL
    """
    if sub_category:
        base = equipment_filter_category_url(category, sub_category)
        if page > 1:
            return f"{base}?page={page}"
        return base

    if country:
        base = equipment_filter_country_url(category, country)
        if page > 1:
            return f"{base}?page={page}"
        return base

    if decade:
        base = equipment_filter_decade_url(category, decade)
        if page > 1:
            return f"{base}?page={page}"
        return base

    if query:
        base = equipment_search_url(category, query)
        if page > 1:
            return f"{base}&page={page}"
        return base

    if page > 1:
        return equipment_paginate_url(category, page)

    return equipment_list_url(category)


def build_inventory_url(
    category: InventoryCategory,
    *,
    query: str | None = None,
    country: str | None = None,
    page: int = 1,
) -> str:
    """Build the appropriate inventory URL based on provided filters.

    Inventory categories generally have fewer filter options.
    """
    base = inventory_list_url(category)

    if page > 1 and category.has_pagination:
        return f"{base}?page={page}"

    return base
