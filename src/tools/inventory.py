"""MCP tool handler for inventory search.

T029 — search_inventory tool handler
"""

from __future__ import annotations

import logging
import time

from fastmcp import Context
from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)

from src.app import mcp, READ_ONLY_ANNOTATIONS
from src.domain.enums import InventoryCategory
from src.domain.services import SearchService


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def search_inventory(
    category: str,
    ctx: Context,
    query: str | None = None,
    country: str | None = None,
    page: int = 1,
) -> dict:
    """Search military inventory data (air forces, air bases, navies, ranks, nuclear arsenals).

    Returns country-level force composition and strategic data with pagination.

    Args:
        category: Inventory category — air_forces, air_bases, navies, ranks, nuclear
        query: Search text. Not available for all categories (navies has no search). Optional.
        country: ISO 3166-1 alpha-3 country code (e.g., 'usa'). Optional.
        page: Page number (1-indexed). Navies has no pagination. Default: 1.
    """
    # Validate category
    try:
        cat = InventoryCategory(category)
    except ValueError:
        valid = ", ".join(c.value for c in InventoryCategory)
        raise ToolError(
            f"Invalid inventory category '{category}'. Valid categories: {valid}"
        )

    # Validate country format
    if country is not None:
        country = country.lower()
        if len(country) != 3 or not country.isalpha():
            raise ToolError(
                f"Country code must be 3 letters (ISO 3166-1 alpha-3), got '{country}'"
            )

    lc = ctx.fastmcp._lifespan_result
    svc = SearchService(
        http_client=lc["http_client"],
        cache=lc["cache"],
        rate_limiter=lc["rate_limiter"],
        circuit_breaker=lc["circuit_breaker"],
    )

    logger.info(
        "tool_call:search_inventory",
        extra={"category": category, "query": query, "country": country, "page": page},
    )
    t0 = time.monotonic()
    try:
        result = await svc.search_inventory(
            category=cat,
            query=query,
            country=country,
            page=page,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "tool_done:search_inventory",
            extra={
                "result_count": result.total_count,
                "elapsed_ms": round(elapsed_ms, 1),
            },
        )
        return result.model_dump()
    except RuntimeError as exc:
        raise ToolError(
            "Unable to reach GlobalMilitary.net. "
            "The data source is temporarily unavailable. Please try again later."
        ) from exc
    except Exception as exc:
        raise ToolError(str(exc)) from exc
