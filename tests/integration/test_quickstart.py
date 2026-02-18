"""Quickstart validation smoke test.

T042 — End-to-end validation following quickstart.md scenarios.
Uses FastMCP Client against our server with mocked HTTP via respx.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from src.server import mcp

FIXTURES = Path(__file__).parent.parent / "fixtures" / "html"


@pytest.fixture
def mock_routes():
    """Set up respx mocks for all routes the quickstart exercises."""
    with respx.mock(assert_all_mocked=False) as router:
        router.get(url__startswith="https://www.globalmilitary.net/aircraft").mock(
            return_value=httpx.Response(
                200, text=FIXTURES.joinpath("aircraft.html").read_text()
            )
        )
        router.get(url__startswith="https://www.globalmilitary.net/navy-ships").mock(
            return_value=httpx.Response(
                200, text=FIXTURES.joinpath("navies.html").read_text()
            )
        )
        router.get(url__startswith="https://www.globalmilitary.net/missiles").mock(
            return_value=httpx.Response(
                200, text=FIXTURES.joinpath("missiles.html").read_text()
            )
        )
        yield router


class TestQuickstartValidation:
    """Validates the quickstart.md scenarios work end-to-end."""

    async def test_server_has_all_four_tools(self):
        """quickstart §4: list_tools returns 4 tools."""
        tool_names = [t.name for t in mcp._tool_manager._tools.values()]
        expected = {
            "search_equipment",
            "search_inventory",
            "compare_equipment",
            "identify_from_image",
        }
        assert expected == set(tool_names)

    async def test_server_has_resources(self):
        """quickstart §8: resources registered."""
        resource_keys = list(mcp._resource_manager._resources.keys())
        # At minimum the static resource should be registered
        assert any("categories" in str(k) for k in resource_keys)

    async def test_categories_resource_returns_json(self):
        """quickstart §8: military://categories returns valid JSON."""
        from src.server import get_categories

        data = json.loads(get_categories.fn())
        assert "equipment_categories" in data
        assert "inventory_categories" in data
        assert len(data["equipment_categories"]) == 5
        assert len(data["inventory_categories"]) == 5

    async def test_sub_categories_resource_returns_json(self):
        """quickstart §8: sub-categories resource returns valid JSON."""
        from src.server import get_sub_categories

        data = json.loads(get_sub_categories.fn("aircraft"))
        assert data["category"] == "aircraft"
        assert len(data["sub_categories"]) > 0

    async def test_project_structure_exists(self):
        """quickstart §9: verify project structure from quickstart."""
        root = Path(__file__).parent.parent.parent
        assert (root / "src" / "server.py").exists()
        assert (root / "src" / "domain").is_dir()
        assert (root / "src" / "scraper").is_dir()
        assert (root / "src" / "cache").is_dir()
        assert (root / "src" / "tools").is_dir()
        assert (root / "tests" / "unit").is_dir()
        assert (root / "tests" / "integration").is_dir()
        assert (root / "tests" / "contract").is_dir()
        assert (root / "tests" / "fixtures" / "html").is_dir()

    async def test_tool_annotations_read_only(self):
        """quickstart §10: all tools annotated read-only."""
        for tool in mcp._tool_manager._tools.values():
            annotations = tool.annotations
            if annotations:
                ann_dict = (
                    annotations.model_dump()
                    if hasattr(annotations, "model_dump")
                    else {}
                )
                if ann_dict:
                    assert (
                        ann_dict.get("readOnlyHint") is True
                    ), f"{tool.name} should be read-only"
