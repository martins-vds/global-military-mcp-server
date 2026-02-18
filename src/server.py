"""FastMCP server with lifespan management and dependency injection."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastmcp import Context, FastMCP

from src.cache.store import FileCache
from src.domain.enums import EquipmentCategory, InventoryCategory
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


# ---- MCP Resources (T038 + T039) ----

# Human-readable labels for sub-categories
_SUB_CATEGORY_LABELS: dict[str, str] = {
    "combat": "Combat Aircraft",
    "bomber": "Bombers",
    "helicopter": "Helicopters",
    "training": "Training Aircraft",
    "transport": "Transport Aircraft",
    "uav": "UAVs / Drones",
    "other": "Other",
    "aam": "Air-to-Air Missiles",
    "ashm": "Anti-Ship Missiles",
    "asm": "Air-to-Surface Missiles",
    "atm": "Anti-Tank Missiles",
    "ballistic": "Ballistic Missiles",
    "cruise": "Cruise Missiles",
    "sam": "Surface-to-Air Missiles",
    "submarine": "Submarines",
    "frigate": "Frigates",
    "corvette": "Corvettes",
    "amphibious": "Amphibious Vessels",
    "cruiser": "Cruisers",
    "destroyer": "Destroyers",
    "carrier": "Aircraft Carriers",
    "patrol": "Patrol Vessels",
    "mine": "Mine Warfare",
    "matsniper": "Anti-Material / Sniper",
    "assault": "Assault Rifles",
    "bullassault": "Bullpup Assault Rifles",
    "shotgun": "Shotguns",
    "lmg": "Light Machine Guns",
    "mg": "Machine Guns",
    "smg": "Submachine Guns",
    "smp": "Semi-Auto Pistols",
    "sniper": "Sniper Rifles",
}

# Human-readable labels for inventory categories
_INVENTORY_LABELS: dict[str, str] = {
    "air_forces": "Air Forces",
    "air_bases": "Air Bases",
    "navies": "Navies",
    "ranks": "Military Ranks",
    "nuclear": "Nuclear Arsenals",
}


@mcp.resource("military://categories")
def get_categories() -> str:
    """Lists all equipment and inventory categories available for search."""
    equipment_cats = []
    for cat in EquipmentCategory:
        filters = ["query", "country"]
        if cat.sub_categories:
            filters.append("sub_category")
        if cat.has_decade_filter:
            filters.append("decade")
        equipment_cats.append(
            {
                "id": cat.value,
                "label": cat.value.title(),
                "url_segment": cat.url_segment,
                "supported_filters": filters,
                "sub_categories": cat.sub_categories,
            }
        )

    inventory_cats = []
    for cat in InventoryCategory:
        filters = ["country"]
        # Some categories also support query
        if cat in (InventoryCategory.air_forces, InventoryCategory.air_bases):
            filters.insert(0, "query")
        inventory_cats.append(
            {
                "id": cat.value,
                "label": _INVENTORY_LABELS.get(cat.value, cat.value.title()),
                "url_segment": cat.url_segment,
                "supported_filters": filters,
            }
        )

    return json.dumps(
        {
            "equipment_categories": equipment_cats,
            "inventory_categories": inventory_cats,
        }
    )


@mcp.resource("military://equipment/{category}/sub-categories")
def get_sub_categories(category: str) -> str:
    """Lists valid sub-category slugs for a given equipment category."""
    try:
        cat = EquipmentCategory(category)
    except ValueError:
        return json.dumps(
            {
                "error": f"Invalid category: {category}",
                "category": category,
                "sub_categories": [],
            }
        )

    subs = []
    for slug in cat.sub_categories:
        subs.append(
            {
                "slug": slug,
                "label": _SUB_CATEGORY_LABELS.get(slug, slug.title()),
            }
        )

    return json.dumps(
        {
            "category": cat.value,
            "sub_categories": subs,
        }
    )


def _register_tools():
    """Import tool modules to register @mcp.tool handlers."""
    import src.tools.equipment  # noqa: F401
    import src.tools.inventory  # noqa: F401


_register_tools()


def main():
    """Entry point for `global-military` CLI command."""
    mcp.run()


if __name__ == "__main__":
    main()
