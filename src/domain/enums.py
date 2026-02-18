"""Domain enums for equipment and inventory categories."""

from __future__ import annotations

from enum import Enum


class EquipmentCategory(str, Enum):
    """Equipment data domains on GlobalMilitary.net."""

    aircraft = "aircraft"
    missiles = "missiles"
    firearms = "firearms"
    vehicles = "vehicles"
    ships = "ships"

    @property
    def url_segment(self) -> str:
        """URL path segment for this category."""
        return f"/{self.value}/"

    @property
    def has_decade_filter(self) -> bool:
        """Whether this category supports decade-based filtering."""
        return self in (EquipmentCategory.aircraft, EquipmentCategory.ships)

    @property
    def sub_categories(self) -> list[str]:
        """Valid sub-category slugs for this category."""
        return _SUB_CATEGORIES.get(self, [])

    @property
    def has_name_search(self) -> bool:
        """Whether this category supports ?name= search."""
        return True  # All equipment categories support name search

    @property
    def has_country_filter(self) -> bool:
        """Whether this category supports country filtering."""
        return True  # All equipment categories support country filter


class InventoryCategory(str, Enum):
    """Inventory data domains on GlobalMilitary.net."""

    air_forces = "air_forces"
    air_bases = "air_bases"
    navies = "navies"
    ranks = "ranks"
    nuclear = "nuclear"

    @property
    def url_segment(self) -> str:
        """URL path segment for this category."""
        return _INVENTORY_URL_SEGMENTS[self]

    @property
    def has_pagination(self) -> bool:
        """Whether this category has paginated results."""
        # Navies is a single-page listing
        return self != InventoryCategory.navies


_SUB_CATEGORIES: dict[EquipmentCategory, list[str]] = {
    EquipmentCategory.aircraft: [
        "combat",
        "bomber",
        "helicopter",
        "training",
        "transport",
        "uav",
        "other",
    ],
    EquipmentCategory.missiles: [
        "aam",
        "ashm",
        "asm",
        "atm",
        "ballistic",
        "cruise",
        "sam",
    ],
    EquipmentCategory.ships: [
        "submarine",
        "frigate",
        "corvette",
        "amphibious",
        "cruiser",
        "destroyer",
        "carrier",
        "patrol",
        "mine",
    ],
    EquipmentCategory.firearms: [
        "matsniper",
        "assault",
        "bullassault",
        "shotgun",
        "lmg",
        "mg",
        "smg",
        "smp",
        "sniper",
    ],
    # Vehicles: TBD — confirm during T006 (HTML fixture capture)
}

_INVENTORY_URL_SEGMENTS: dict[InventoryCategory, str] = {
    InventoryCategory.air_forces: "/air-forces/",
    InventoryCategory.air_bases: "/airbases/",
    InventoryCategory.navies: "/navies/",
    InventoryCategory.ranks: "/ranks/",
    InventoryCategory.nuclear: "/nuclear/",
}
