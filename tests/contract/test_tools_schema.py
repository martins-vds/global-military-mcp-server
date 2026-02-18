"""Contract tests: validate tool schemas against JSON contract files.

T017 — search_equipment contract
T024 — search_inventory contract
T030 — identify_from_image contract
T034 — compare_equipment contract
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain.enums import EquipmentCategory, InventoryCategory
from src.domain.models import (
    AirBase,
    AirForce,
    ComparisonResult,
    Country,
    Equipment,
    IdentificationMatch,
    IdentificationResult,
    Navy,
    NuclearArsenal,
    PageInfo,
    RankEntry,
    RankStructure,
    SearchResult,
)

CONTRACTS_DIR = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "001-military-db-search"
    / "contracts"
)


def _load_contract(name: str) -> dict:
    return json.loads((CONTRACTS_DIR / f"{name}.json").read_text())


# ═══════════════════════════════════════════════════════════════════════════
# T017 — search_equipment contract tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchEquipmentContract:
    """Validate search_equipment against contracts/search-equipment.json."""

    @pytest.fixture
    def contract(self) -> dict:
        return _load_contract("search-equipment")

    def test_tool_name(self, contract: dict):
        assert contract["properties"]["tool"]["const"] == "search_equipment"

    def test_annotations_read_only(self, contract: dict):
        ann = contract["properties"]["annotations"]["properties"]
        assert ann["readOnlyHint"]["const"] is True
        assert ann["idempotentHint"]["const"] is True
        assert ann["openWorldHint"]["const"] is True

    def test_input_requires_category(self, contract: dict):
        schema = contract["properties"]["inputSchema"]
        assert "category" in schema["required"]
        assert schema["properties"]["category"]["enum"] == [
            "aircraft",
            "missiles",
            "firearms",
            "vehicles",
            "ships",
        ]

    def test_input_optional_params(self, contract: dict):
        props = contract["properties"]["inputSchema"]["properties"]
        for field in ("query", "country", "sub_category", "decade"):
            assert field in props
            # Optional: default is null
            assert props[field].get("default") is None

    def test_output_required_fields(self, contract: dict):
        out = contract["properties"]["outputSchema"]
        assert set(out["required"]) == {
            "items",
            "total_count",
            "page_info",
            "category",
            "filters_applied",
        }

    def test_output_item_required_fields(self, contract: dict):
        item = contract["properties"]["outputSchema"]["properties"]["items"]["items"]
        assert set(item["required"]) == {
            "name",
            "slug",
            "country",
            "category",
            "detail_url",
        }

    def test_page_info_shape(self, contract: dict):
        pi = contract["properties"]["outputSchema"]["properties"]["page_info"]
        assert set(pi["required"]) == {
            "current_page",
            "total_pages",
            "has_next",
            "has_previous",
        }

    def test_error_cases_defined(self, contract: dict):
        errors = contract["errorCases"]
        conditions = {e["condition"] for e in errors}
        assert "Invalid category value" in conditions
        assert "Decade filter on unsupported category" in conditions
        assert "Invalid country code format" in conditions
        assert "Upstream site unreachable" in conditions
        assert "Rate limited by upstream (429)" in conditions

    def test_model_conforms_to_contract(self, contract: dict):
        """Verify actual SearchResult serialization matches contract output shape."""
        result = SearchResult(
            items=[
                Equipment(
                    name="F-16 Fighting Falcon",
                    slug="f-16-fighting-falcon",
                    country=Country(iso3="usa", name="United States"),
                    category=EquipmentCategory.aircraft,
                    sub_category="Combat",
                    detail_url="/aircraft/f-16-fighting-falcon/",
                    manufacturer="General Dynamics",
                    produced=4604,
                )
            ],
            total_count=1,
            page_info=PageInfo(
                current_page=1, total_pages=1, has_next=False, has_previous=False
            ),
            category="aircraft",
            filters_applied={"query": "F-16"},
        )
        data = result.model_dump()
        out_required = contract["properties"]["outputSchema"]["required"]
        for field in out_required:
            assert field in data, f"Missing required output field: {field}"

    def test_equipment_enum_matches_category(self):
        """EquipmentCategory values must match contract enum."""
        expected = {"aircraft", "missiles", "firearms", "vehicles", "ships"}
        actual = {c.value for c in EquipmentCategory}
        assert actual == expected


# ═══════════════════════════════════════════════════════════════════════════
# T024 — search_inventory contract tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSearchInventoryContract:
    """Validate search_inventory against contracts/search-inventory.json."""

    @pytest.fixture
    def contract(self) -> dict:
        return _load_contract("search-inventory")

    def test_tool_name(self, contract: dict):
        assert contract["properties"]["tool"]["const"] == "search_inventory"

    def test_annotations_read_only(self, contract: dict):
        ann = contract["properties"]["annotations"]["properties"]
        assert ann["readOnlyHint"]["const"] is True

    def test_input_requires_category(self, contract: dict):
        schema = contract["properties"]["inputSchema"]
        assert "category" in schema["required"]
        assert schema["properties"]["category"]["enum"] == [
            "air_forces",
            "air_bases",
            "navies",
            "ranks",
            "nuclear",
        ]

    def test_output_required_fields(self, contract: dict):
        out = contract["properties"]["outputSchema"]
        assert set(out["required"]) == {
            "items",
            "total_count",
            "page_info",
            "category",
            "filters_applied",
        }

    def test_inventory_items_one_of(self, contract: dict):
        """Output items should use oneOf with multiple inventory types."""
        items_schema = contract["properties"]["outputSchema"]["properties"]["items"][
            "items"
        ]
        assert "oneOf" in items_schema
        titles = {schema["title"] for schema in items_schema["oneOf"]}
        assert titles == {
            "Navy",
            "AirBase",
            "NuclearArsenal",
            "RankStructure",
            "AirForce",
        }

    def test_navy_required_fields(self, contract: dict):
        items_schema = contract["properties"]["outputSchema"]["properties"]["items"][
            "items"
        ]
        navy = next(s for s in items_schema["oneOf"] if s["title"] == "Navy")
        assert set(navy["required"]) == {
            "country",
            "rank",
            "navy_index",
            "capital_ships",
            "major_combatants",
            "total_active",
            "detail_url",
        }

    def test_error_cases_defined(self, contract: dict):
        errors = contract["errorCases"]
        conditions = {e["condition"] for e in errors}
        assert "Invalid inventory category" in conditions

    def test_model_conforms_navy(self):
        """Verify Navy model serialization matches contract."""
        result = SearchResult(
            items=[
                Navy(
                    country=Country(iso3="usa", name="United States"),
                    rank=1,
                    navy_index=323.8,
                    capital_ships=24,
                    major_combatants=113,
                    total_active=490,
                    detail_url="/navies/usa/",
                )
            ],
            total_count=1,
            page_info=PageInfo(
                current_page=1, total_pages=1, has_next=False, has_previous=False
            ),
            category="navies",
            filters_applied={},
        )
        data = result.model_dump()
        item = data["items"][0]
        assert "country" in item
        assert "navy_index" in item
        assert "detail_url" in item

    def test_inventory_enum_matches_category(self):
        """InventoryCategory values must match contract enum."""
        expected = {"air_forces", "air_bases", "navies", "ranks", "nuclear"}
        actual = {c.value for c in InventoryCategory}
        assert actual == expected


# ═══════════════════════════════════════════════════════════════════════════
# T030 — identify_from_image contract tests
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentifyFromImageContract:
    """Validate identify_from_image against contracts/identify-from-image.json."""

    @pytest.fixture
    def contract(self) -> dict:
        return _load_contract("identify-from-image")

    def test_tool_name(self, contract: dict):
        assert contract["properties"]["tool"]["const"] == "identify_from_image"

    def test_annotations_read_only(self, contract: dict):
        ann = contract["properties"]["annotations"]["properties"]
        assert ann["readOnlyHint"]["const"] is True

    def test_input_any_of_constraint(self, contract: dict):
        """Either equipment_name OR category+characteristics required."""
        schema = contract["properties"]["inputSchema"]
        assert "anyOf" in schema
        options = schema["anyOf"]
        reqs = [set(o["required"]) for o in options]
        assert {"equipment_name"} in reqs
        assert {"category", "characteristics"} in reqs

    def test_output_required_fields(self, contract: dict):
        out = contract["properties"]["outputSchema"]
        assert set(out["required"]) == {"matches", "search_strategy"}

    def test_match_required_fields(self, contract: dict):
        out = contract["properties"]["outputSchema"]
        match_item = out["properties"]["matches"]["items"]
        assert set(match_item["required"]) == {"equipment", "match_reason"}

    def test_error_cases_defined(self, contract: dict):
        errors = contract["errorCases"]
        conditions = {e["condition"] for e in errors}
        assert "No identifying information provided" in conditions

    def test_model_conforms(self):
        """Verify IdentificationResult serialization matches contract."""
        result = IdentificationResult(
            matches=[
                IdentificationMatch(
                    equipment=Equipment(
                        name="F-22 Raptor",
                        slug="f-22-raptor",
                        country=Country(iso3="usa", name="United States"),
                        category=EquipmentCategory.aircraft,
                        detail_url="/aircraft/f-22-raptor/",
                    ),
                    match_reason="Direct name match: F-22 Raptor",
                )
            ],
            identification_notes="Exact match found.",
            search_strategy="name_search",
        )
        data = result.model_dump()
        assert "matches" in data
        assert "search_strategy" in data
        assert data["matches"][0]["match_reason"]


# ═══════════════════════════════════════════════════════════════════════════
# T034 — compare_equipment contract tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCompareEquipmentContract:
    """Validate compare_equipment against contracts/compare-equipment.json."""

    @pytest.fixture
    def contract(self) -> dict:
        return _load_contract("compare-equipment")

    def test_tool_name(self, contract: dict):
        assert contract["properties"]["tool"]["const"] == "compare_equipment"

    def test_annotations_read_only(self, contract: dict):
        ann = contract["properties"]["annotations"]["properties"]
        assert ann["readOnlyHint"]["const"] is True

    def test_input_requires_category_and_slugs(self, contract: dict):
        schema = contract["properties"]["inputSchema"]
        assert set(schema["required"]) == {"category", "slugs"}

    def test_slugs_min_max(self, contract: dict):
        slugs = contract["properties"]["inputSchema"]["properties"]["slugs"]
        assert slugs["minItems"] == 2
        assert slugs["maxItems"] == 5

    def test_output_required_fields(self, contract: dict):
        out = contract["properties"]["outputSchema"]
        assert set(out["required"]) == {"items", "category", "shared_fields"}

    def test_error_cases_defined(self, contract: dict):
        errors = contract["errorCases"]
        conditions = {e["condition"] for e in errors}
        assert "Fewer than 2 slugs" in conditions
        assert "More than 5 slugs" in conditions
        assert "Slug not found in category" in conditions

    def test_model_conforms(self):
        """Verify ComparisonResult serialization matches contract."""
        items = [
            Equipment(
                name="F-22 Raptor",
                slug="f-22-raptor",
                country=Country(iso3="usa", name="United States"),
                category=EquipmentCategory.aircraft,
                detail_url="/aircraft/f-22-raptor/",
                manufacturer="Lockheed Martin",
            ),
            Equipment(
                name="Su-57",
                slug="su-57",
                country=Country(iso3="rus", name="Russia"),
                category=EquipmentCategory.aircraft,
                detail_url="/aircraft/su-57/",
                manufacturer="Sukhoi",
            ),
        ]
        result = ComparisonResult(
            items=items,
            category=EquipmentCategory.aircraft,
            shared_fields=[
                "name",
                "slug",
                "country",
                "category",
                "detail_url",
                "manufacturer",
            ],
            comparison_notes="Comparing 2 aircraft",
        )
        data = result.model_dump()
        assert "items" in data
        assert "category" in data
        assert "shared_fields" in data
        assert len(data["items"]) == 2
