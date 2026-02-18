"""Contract tests for MCP resources.

T040 — Validates resource URIs and output shapes against contracts/resources.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain.enums import EquipmentCategory, InventoryCategory
from src.server import (
    get_categories as _cat_resource,
    get_sub_categories as _sub_resource,
)

# @mcp.resource wraps functions into FunctionResource objects;
# call .fn to invoke the underlying function.
get_categories = _cat_resource.fn
get_sub_categories = _sub_resource.fn

CONTRACTS_DIR = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "001-military-db-search"
    / "contracts"
)


@pytest.fixture
def resources_contract() -> dict:
    return json.loads((CONTRACTS_DIR / "resources.json").read_text())


class TestCategoriesResource:
    """Validate military://categories resource."""

    def test_returns_valid_json(self):
        data = json.loads(get_categories())
        assert isinstance(data, dict)

    def test_has_equipment_categories(self):
        data = json.loads(get_categories())
        assert "equipment_categories" in data
        assert len(data["equipment_categories"]) == len(EquipmentCategory)

    def test_has_inventory_categories(self):
        data = json.loads(get_categories())
        assert "inventory_categories" in data
        assert len(data["inventory_categories"]) == len(InventoryCategory)

    def test_equipment_category_required_fields(self, resources_contract):
        data = json.loads(get_categories())
        schema = resources_contract["resources"][0]["schema"]
        required = schema["properties"]["equipment_categories"]["items"]["required"]
        for cat in data["equipment_categories"]:
            for field in required:
                assert field in cat, f"Missing {field} in {cat['id']}"

    def test_inventory_category_required_fields(self, resources_contract):
        data = json.loads(get_categories())
        schema = resources_contract["resources"][0]["schema"]
        required = schema["properties"]["inventory_categories"]["items"]["required"]
        for cat in data["inventory_categories"]:
            for field in required:
                assert field in cat, f"Missing {field} in {cat['id']}"

    def test_aircraft_has_decade_filter(self):
        data = json.loads(get_categories())
        aircraft = next(
            c for c in data["equipment_categories"] if c["id"] == "aircraft"
        )
        assert "decade" in aircraft["supported_filters"]

    def test_missiles_no_decade_filter(self):
        data = json.loads(get_categories())
        missiles = next(
            c for c in data["equipment_categories"] if c["id"] == "missiles"
        )
        assert "decade" not in missiles["supported_filters"]

    def test_navies_has_country_filter(self):
        data = json.loads(get_categories())
        navies = next(c for c in data["inventory_categories"] if c["id"] == "navies")
        assert "country" in navies["supported_filters"]


class TestSubCategoriesResource:
    """Validate military://equipment/{category}/sub-categories resource."""

    def test_returns_valid_json(self):
        data = json.loads(get_sub_categories("aircraft"))
        assert isinstance(data, dict)

    def test_aircraft_sub_categories(self):
        data = json.loads(get_sub_categories("aircraft"))
        assert data["category"] == "aircraft"
        slugs = [s["slug"] for s in data["sub_categories"]]
        assert "combat" in slugs
        assert "bomber" in slugs

    def test_sub_category_has_slug_and_label(self, resources_contract):
        data = json.loads(get_sub_categories("aircraft"))
        schema = resources_contract["resources"][1]["schema"]
        required = schema["properties"]["sub_categories"]["items"]["required"]
        for sub in data["sub_categories"]:
            for field in required:
                assert field in sub, f"Missing {field} in {sub}"

    def test_missiles_sub_categories(self):
        data = json.loads(get_sub_categories("missiles"))
        slugs = [s["slug"] for s in data["sub_categories"]]
        assert "aam" in slugs
        assert "sam" in slugs

    def test_invalid_category_returns_error(self):
        data = json.loads(get_sub_categories("invalid"))
        assert "error" in data

    def test_all_equipment_categories_have_sub_categories(self):
        """Every equipment category should return valid sub-category data."""
        for cat in EquipmentCategory:
            data = json.loads(get_sub_categories(cat.value))
            assert data["category"] == cat.value
            assert isinstance(data["sub_categories"], list)
