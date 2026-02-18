"""FastMCP server with lifespan management and dependency injection."""

from __future__ import annotations

import json
from typing import Any

from src.app import mcp, READ_ONLY_ANNOTATIONS  # noqa: F401 — re-exported for back-compat
from src.domain.enums import EquipmentCategory, InventoryCategory


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
