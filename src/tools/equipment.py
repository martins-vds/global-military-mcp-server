"""MCP tool handlers for equipment search, identification, and comparison.

T023 — search_equipment tool handler
T033 — identify_from_image tool handler
T037 — compare_equipment tool handler
"""

from __future__ import annotations

import logging
import time

from fastmcp import Context
from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)

from src.domain.enums import EquipmentCategory
from src.domain.services import ComparisonService, IdentificationService, SearchService
from src.server import mcp, READ_ONLY_ANNOTATIONS


def _make_search_service(ctx: Context) -> SearchService:
    """Create SearchService from lifespan context."""
    lc = ctx.lifespan_context
    return SearchService(
        http_client=lc["http_client"],
        cache=lc["cache"],
        rate_limiter=lc["rate_limiter"],
        circuit_breaker=lc["circuit_breaker"],
    )


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def search_equipment(
    category: str,
    ctx: Context,
    query: str | None = None,
    country: str | None = None,
    sub_category: str | None = None,
    decade: int | None = None,
    page: int = 1,
) -> dict:
    """Search military equipment (aircraft, missiles, firearms, vehicles, ships).

    Returns structured results with pagination. All tools are read-only scrapers
    that do not modify any data.

    Args:
        category: Equipment category — aircraft, missiles, firearms, vehicles, ships
        query: Name or keyword search text (e.g., 'F-16', 'stealth'). Optional.
        country: ISO 3166-1 alpha-3 country code (e.g., 'usa', 'chn'). Optional.
        sub_category: Sub-category slug for finer filtering. Optional.
        decade: Decade filter (1900-2030, multiple of 10). Only aircraft and ships. Optional.
        page: Page number (1-indexed). Default: 1.
    """
    # Validate category
    try:
        cat = EquipmentCategory(category)
    except ValueError:
        valid = ", ".join(c.value for c in EquipmentCategory)
        raise ToolError(
            f"Invalid equipment category '{category}'. Valid categories: {valid}"
        )

    # Validate country format
    if country is not None:
        country = country.lower()
        if len(country) != 3 or not country.isalpha():
            raise ToolError(
                f"Country code must be 3 letters (ISO 3166-1 alpha-3), got '{country}'"
            )

    # Validate decade filter support
    if decade is not None and not cat.has_decade_filter:
        raise ToolError(
            f"Decade filter is not available for {cat.value}. "
            f"Only aircraft and ships support decade filtering."
        )

    # Validate decade value
    if decade is not None:
        if decade % 10 != 0 or not (1900 <= decade <= 2030):
            raise ToolError(
                f"Decade must be a multiple of 10 between 1900 and 2030, got {decade}"
            )

    svc = _make_search_service(ctx)

    logger.info(
        "tool_call:search_equipment",
        extra={
            "category": category,
            "query": query,
            "country": country,
            "sub_category": sub_category,
            "decade": decade,
            "page": page,
        },
    )
    t0 = time.monotonic()
    try:
        result = await svc.search_equipment(
            category=cat,
            query=query,
            country=country,
            sub_category=sub_category,
            decade=decade,
            page=page,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "tool_done:search_equipment",
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


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def identify_from_image(
    ctx: Context,
    equipment_name: str | None = None,
    category: str | None = None,
    characteristics: str | None = None,
    country_of_origin: str | None = None,
) -> dict:
    """Identify military equipment from an image description.

    The calling LLM analyzes the image and provides a text description;
    this tool searches the database for matching equipment.

    Args:
        equipment_name: Name of the equipment (e.g., 'F-22 Raptor'). Optional if category + characteristics provided.
        category: Equipment category determined from the image. Optional.
        characteristics: Free-text description of visual characteristics. Optional.
        country_of_origin: ISO-3 country code from markings. Optional.
    """
    # Validate input
    if not equipment_name and not (category and characteristics):
        raise ToolError(
            "Please provide at least an equipment name or a category with "
            "visual characteristics."
        )

    # Validate and convert category
    cat: EquipmentCategory | None = None
    if category is not None:
        try:
            cat = EquipmentCategory(category)
        except ValueError:
            valid = ", ".join(c.value for c in EquipmentCategory)
            raise ToolError(
                f"Invalid equipment category '{category}'. Valid categories: {valid}"
            )

    # Validate country
    if country_of_origin is not None:
        country_of_origin = country_of_origin.lower()
        if len(country_of_origin) != 3 or not country_of_origin.isalpha():
            raise ToolError(
                f"Country code must be 3 letters (ISO 3166-1 alpha-3), got '{country_of_origin}'"
            )

    svc = _make_search_service(ctx)
    id_svc = IdentificationService(svc)

    logger.info(
        "tool_call:identify_from_image",
        extra={
            "equipment_name": equipment_name,
            "category": category,
            "characteristics": characteristics,
            "country_of_origin": country_of_origin,
        },
    )
    t0 = time.monotonic()
    try:
        result = await id_svc.identify(
            equipment_name=equipment_name,
            category=cat,
            characteristics=characteristics,
            country_of_origin=country_of_origin,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "tool_done:identify_from_image",
            extra={
                "match_count": len(result.matches),
                "strategy": result.search_strategy,
                "elapsed_ms": round(elapsed_ms, 1),
            },
        )
        return result.model_dump()
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except RuntimeError as exc:
        raise ToolError(
            "Unable to reach GlobalMilitary.net. "
            "The data source is temporarily unavailable. Please try again later."
        ) from exc
    except Exception as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def compare_equipment(
    category: str,
    slugs: list[str],
    ctx: Context,
) -> dict:
    """Compare 2-5 military equipment items side-by-side within the same category.

    Args:
        category: Equipment category — all items must belong to this category.
        slugs: List of 2-5 equipment slugs to compare (e.g., ['f-22-raptor', 'su-57']).
    """
    # Validate category
    try:
        cat = EquipmentCategory(category)
    except ValueError:
        valid = ", ".join(c.value for c in EquipmentCategory)
        raise ToolError(
            f"Invalid equipment category '{category}'. Valid categories: {valid}"
        )

    # Validate slug count
    if len(slugs) < 2 or len(slugs) > 5:
        raise ToolError(
            f"Please provide 2 to 5 items to compare. Received {len(slugs)}."
        )

    svc = _make_search_service(ctx)
    cmp_svc = ComparisonService(svc)

    logger.info(
        "tool_call:compare_equipment",
        extra={"category": category, "slugs": slugs},
    )
    t0 = time.monotonic()
    try:
        result = await cmp_svc.compare(category=cat, slugs=slugs)
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "tool_done:compare_equipment",
            extra={
                "item_count": len(result.items),
                "shared_fields": result.shared_fields,
                "elapsed_ms": round(elapsed_ms, 1),
            },
        )
        return result.model_dump()
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except RuntimeError as exc:
        raise ToolError(
            "Unable to reach GlobalMilitary.net. "
            "The data source is temporarily unavailable. Please try again later."
        ) from exc
    except Exception as exc:
        raise ToolError(str(exc)) from exc
