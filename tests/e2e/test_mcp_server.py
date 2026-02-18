"""End-to-end smoke tests — real MCP server, real network calls.

Spins up the MCP server via the in-process FastMCP ``Client`` and calls every
tool and resource against the live GlobalMilitary.net site.  Assertions are
intentionally loose (non-empty results, correct shape) so the suite stays
green even when site content changes.

Each test that hits the network uses a single ``Client`` session and spaces
out requests with ``asyncio.sleep`` to avoid triggering server-side
rate limiting.

Run:
    pytest tests/e2e -m e2e -v          # run only e2e
    pytest -m "not e2e"                 # skip e2e in CI
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastmcp import Client

from src.server import mcp

pytestmark = [
    pytest.mark.e2e,
]

# Pause between live requests inside a single test to stay polite.
_REQUEST_GAP = 3.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_tool_result(result) -> dict:
    """Extract the dict payload from a ``call_tool`` return value."""
    if isinstance(result, dict):
        return result
    # FastMCP 2.x CallToolResult — try .data first, then .content list
    if hasattr(result, "data") and result.data is not None:
        return result.data if isinstance(result.data, dict) else json.loads(result.data)
    if hasattr(result, "content"):
        for item in result.content:
            text = getattr(item, "text", None)
            if text:
                return json.loads(text)
    if isinstance(result, list):
        for item in result:
            text = getattr(item, "text", None)
            if text:
                return json.loads(text)
    text = getattr(result, "text", None)
    if text:
        return json.loads(text)
    raise AssertionError(f"Unexpected tool result type: {type(result)}")


# ---------------------------------------------------------------------------
# Resource smoke tests (no network — instant)
# ---------------------------------------------------------------------------


class TestResources:
    """Smoke tests for MCP resources (purely local, no HTTP)."""

    async def test_list_resources(self):
        async with Client(mcp) as client:
            resources = await client.list_resources()
        uris = [str(r.uri) for r in resources]
        assert any("categories" in u for u in uris)

    async def test_categories_resource_shape(self):
        async with Client(mcp) as client:
            result = await client.read_resource("military://categories")
        data = json.loads(result[0].text)
        assert len(data["equipment_categories"]) == 5
        assert len(data["inventory_categories"]) == 5
        for cat in data["equipment_categories"]:
            assert {"id", "supported_filters"} <= cat.keys()

    async def test_sub_categories_aircraft(self):
        async with Client(mcp) as client:
            result = await client.read_resource(
                "military://equipment/aircraft/sub-categories"
            )
        data = json.loads(result[0].text)
        assert data["category"] == "aircraft"
        assert "combat" in [s["slug"] for s in data["sub_categories"]]

    async def test_sub_categories_invalid(self):
        async with Client(mcp) as client:
            result = await client.read_resource(
                "military://equipment/bogus/sub-categories"
            )
        data = json.loads(result[0].text)
        assert "error" in data


# ---------------------------------------------------------------------------
# Tool discovery (no network — instant)
# ---------------------------------------------------------------------------


class TestToolDiscovery:
    async def test_all_tools_visible(self):
        async with Client(mcp) as client:
            tools = await client.list_tools()
        names = {t.name for t in tools}
        assert names == {
            "search_equipment",
            "search_inventory",
            "compare_equipment",
            "identify_from_image",
        }

    async def test_tools_have_descriptions_and_schemas(self):
        async with Client(mcp) as client:
            tools = await client.list_tools()
        for t in tools:
            assert t.description, f"{t.name} missing description"
            assert "properties" in (t.inputSchema or {}), f"{t.name} missing schema"

    async def test_annotations_read_only(self):
        async with Client(mcp) as client:
            tools = await client.list_tools()
        for t in tools:
            ann = t.annotations
            assert ann is not None, f"{t.name} missing annotations"
            d = ann.model_dump() if hasattr(ann, "model_dump") else {}
            assert d.get("readOnlyHint") is True
            assert d.get("idempotentHint") is True


# ---------------------------------------------------------------------------
# Validation-only tests (no network — instant)
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Validation logic that rejects bad input before any HTTP call."""

    async def test_equipment_invalid_category(self):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="Invalid equipment category"):
                await client.call_tool("search_equipment", {"category": "tanks"})

    async def test_equipment_invalid_country_code(self):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="3 letters"):
                await client.call_tool(
                    "search_equipment",
                    {"category": "aircraft", "country": "us"},
                )

    async def test_equipment_decade_on_unsupported(self):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="Decade filter is not available"):
                await client.call_tool(
                    "search_equipment",
                    {"category": "firearms", "decade": 2000},
                )

    async def test_inventory_invalid_category(self):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="Invalid inventory category"):
                await client.call_tool(
                    "search_inventory", {"category": "spaceforce"}
                )

    async def test_inventory_invalid_country_code(self):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="3 letters"):
                await client.call_tool(
                    "search_inventory",
                    {"category": "navies", "country": "US"},
                )

    async def test_identify_missing_inputs(self):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="provide at least"):
                await client.call_tool("identify_from_image", {})

    async def test_compare_too_few(self):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="2 to 5"):
                await client.call_tool(
                    "compare_equipment",
                    {"category": "aircraft", "slugs": ["one"]},
                )

    async def test_compare_too_many(self):
        async with Client(mcp) as client:
            with pytest.raises(Exception, match="2 to 5"):
                await client.call_tool(
                    "compare_equipment",
                    {"category": "aircraft", "slugs": list("abcdef")},
                )


# ---------------------------------------------------------------------------
# Live network smoke tests — ONE session to avoid server-side rate bans
# ---------------------------------------------------------------------------


class TestLiveSmoke:
    """All live-network tool calls in a SINGLE Client session.

    Opens one Client(mcp) to avoid the connection churn that triggers
    server-side rate limiting.  Keeps total requests low (~10) with
    generous inter-request pauses. Full category coverage is handled by
    unit/integration tests with fixture HTML — this suite only proves the
    end-to-end path works against the real site.
    """

    async def test_all_tools_live(self):  # noqa: C901
        """Smoke-test every tool against the live site."""
        async with Client(mcp) as client:
            # ── search_equipment: two categories ────────────────────
            for cat in ("aircraft", "ships"):
                result = await client.call_tool(
                    "search_equipment", {"category": cat}
                )
                data = _parse_tool_result(result)
                assert data["total_count"] > 0, f"No results for {cat}"
                assert len(data["items"]) > 0
                item = data["items"][0]
                assert "name" in item and "slug" in item
                pi = data.get("page_info", {})
                assert "current_page" in pi and "total_pages" in pi
                await asyncio.sleep(_REQUEST_GAP)

            # ── search_equipment: query + country filters ───────────
            result = await client.call_tool(
                "search_equipment",
                {"category": "aircraft", "query": "F-16"},
            )
            assert "items" in _parse_tool_result(result)
            await asyncio.sleep(_REQUEST_GAP)

            result = await client.call_tool(
                "search_equipment",
                {"category": "aircraft", "country": "usa"},
            )
            assert "items" in _parse_tool_result(result)
            await asyncio.sleep(_REQUEST_GAP)

            # ── search_inventory: one category + country filter ─────
            result = await client.call_tool(
                "search_inventory", {"category": "navies"}
            )
            inv_data = _parse_tool_result(result)
            assert inv_data["total_count"] > 0
            assert len(inv_data["items"]) > 0
            await asyncio.sleep(_REQUEST_GAP)

            result = await client.call_tool(
                "search_inventory",
                {"category": "navies", "country": "usa"},
            )
            assert "items" in _parse_tool_result(result)
            await asyncio.sleep(_REQUEST_GAP)

            # ── identify_from_image: by name ────────────────────────
            result = await client.call_tool(
                "identify_from_image",
                {"equipment_name": "F-22 Raptor"},
            )
            id_data = _parse_tool_result(result)
            assert "matches" in id_data
            assert "search_strategy" in id_data
            await asyncio.sleep(_REQUEST_GAP)

            # ── compare_equipment: fetch slugs then compare ─────────
            search = await client.call_tool(
                "search_equipment", {"category": "aircraft"}
            )
            items = _parse_tool_result(search)["items"]
            assert len(items) >= 2, "Need ≥2 aircraft on live site to compare"
            await asyncio.sleep(_REQUEST_GAP)

            slugs = [items[0]["slug"], items[1]["slug"]]
            result = await client.call_tool(
                "compare_equipment",
                {"category": "aircraft", "slugs": slugs},
            )
            cmp_data = _parse_tool_result(result)
            assert "items" in cmp_data
            assert len(cmp_data["items"]) == 2
            await asyncio.sleep(_REQUEST_GAP)

            # ── cross-cutting: resource → tool in same session ──────
            res = await client.read_resource("military://categories")
            cats = json.loads(res[0].text)
            assert len(cats["equipment_categories"]) == 5

            result = await client.call_tool(
                "search_equipment", {"category": "aircraft"}
            )
            assert _parse_tool_result(result)["total_count"] > 0


# ---------------------------------------------------------------------------
# Cross-cutting (no network)
# ---------------------------------------------------------------------------


class TestCrossCutting:
    async def test_tools_and_resources_in_same_session(self):
        async with Client(mcp) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            assert len(tools) == 4
            assert len(resources) >= 1
