"""BeautifulSoup HTML parsing for GlobalMilitary.net pages."""

from __future__ import annotations

import re
from typing import Union

from bs4 import BeautifulSoup, Tag

from src.domain.enums import EquipmentCategory, InventoryCategory
from src.domain.models import (
    AirBase,
    AirForce,
    Country,
    Equipment,
    Navy,
    NuclearArsenal,
    PageInfo,
    RankEntry,
    RankStructure,
)

# Type alias for all inventory entity types
InventoryItem = Union[Navy, AirBase, NuclearArsenal, AirForce, RankStructure]


def parse_equipment_html(html: str, category: EquipmentCategory) -> list[Equipment]:
    """Parse equipment items from an HTML page.

    Extracts data from all `table.table` elements on the page.
    Column layout varies by category (see research.md R1).
    """
    soup = BeautifulSoup(html, "html.parser")
    items: list[Equipment] = []

    for table in soup.select("table.table"):
        tbody = table.find("tbody")
        if not tbody or not isinstance(tbody, Tag):
            continue
        for row in tbody.find_all("tr"):
            cols = row.find_all("td")
            if not cols:
                continue
            item = _parse_equipment_row(cols, category)
            if item:
                items.append(item)

    return items


def _parse_equipment_row(
    cols: list[Tag], category: EquipmentCategory
) -> Equipment | None:
    """Parse a single equipment table row based on category column layout."""
    try:
        country = _extract_country(cols[0])

        # Column 2 always has the name link
        link_tag = cols[1].find("a")
        if not link_tag:
            return None
        name = link_tag.get_text(strip=True)
        href = link_tag.get("href", "")
        slug = _extract_slug(href)
        detail_url = href

        kwargs: dict = {
            "name": name,
            "slug": slug,
            "country": country,
            "category": category,
            "detail_url": detail_url,
        }

        if category == EquipmentCategory.aircraft:
            # Cols: Country, Model, Thumbnail, Manufacturer, Produced, Description
            if len(cols) >= 6:
                img = cols[2].find("img")
                kwargs["thumbnail_url"] = img["src"] if img else None
                kwargs["manufacturer"] = cols[3].get_text(strip=True) or None
                produced_text = cols[4].get_text(strip=True)
                kwargs["produced"] = (
                    int(produced_text) if produced_text.isdigit() else None
                )
                kwargs["description"] = cols[5].get_text(strip=True) or None

        elif category == EquipmentCategory.missiles:
            # Cols: Country, Model, Category, Range, Max Speed
            if len(cols) >= 5:
                kwargs["sub_category"] = cols[2].get_text(strip=True) or None
                kwargs["range_km"] = cols[3].get_text(strip=True) or None
                kwargs["max_speed"] = cols[4].get_text(strip=True) or None

        elif category == EquipmentCategory.ships:
            # Cols: Country, Class, Type, Year
            if len(cols) >= 4:
                kwargs["ship_type"] = cols[2].get_text(strip=True) or None
                year_text = cols[3].get_text(strip=True)
                kwargs["year"] = int(year_text) if year_text.isdigit() else None

        elif category == EquipmentCategory.firearms:
            # Cols: Country, Model, Category
            if len(cols) >= 3:
                kwargs["firearm_category"] = cols[2].get_text(strip=True) or None

        elif category == EquipmentCategory.vehicles:
            # Cols: Country, Model, Category (same layout as firearms)
            if len(cols) >= 3:
                kwargs["sub_category"] = cols[2].get_text(strip=True) or None

        return Equipment(**kwargs)
    except (IndexError, ValueError, KeyError):
        return None


def parse_inventory_html(html: str, category: InventoryCategory) -> list[InventoryItem]:
    """Parse inventory items from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[InventoryItem] = []

    for table in soup.select("table.table"):
        tbody = table.find("tbody")
        if not tbody or not isinstance(tbody, Tag):
            continue
        rows = tbody.find_all("tr")
        if not rows:
            continue

        if category == InventoryCategory.navies:
            items.extend(_parse_navy_rows(rows))
        elif category == InventoryCategory.air_bases:
            items.extend(_parse_air_base_rows(rows))
        elif category == InventoryCategory.nuclear:
            items.extend(_parse_nuclear_rows(rows))
        elif category == InventoryCategory.ranks:
            items.extend(_parse_rank_rows(rows))
        elif category == InventoryCategory.air_forces:
            items.extend(_parse_air_force_rows(rows))

    return items


def _parse_navy_rows(rows: list[Tag]) -> list[Navy]:
    """Parse navy table rows: Rank, Country, Navy Index, Capital, Major, Total."""
    items: list[Navy] = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 6:
            continue
        try:
            rank = int(cols[0].get_text(strip=True))
            link = cols[1].find("a")
            if not link:
                continue
            country_name = link.get_text(strip=True)
            href = link.get("href", "")
            iso3 = _extract_iso3_from_url(href)
            country = Country(iso3=iso3, name=country_name)
            navy_index = float(cols[2].get_text(strip=True))
            capital_ships = int(cols[3].get_text(strip=True))
            major_combatants = int(cols[4].get_text(strip=True))
            total_active = int(cols[5].get_text(strip=True))
            items.append(
                Navy(
                    country=country,
                    rank=rank,
                    navy_index=navy_index,
                    capital_ships=capital_ships,
                    major_combatants=major_combatants,
                    total_active=total_active,
                    detail_url=href,
                )
            )
        except (ValueError, IndexError):
            continue
    return items


def _parse_air_base_rows(rows: list[Tag]) -> list[AirBase]:
    """Parse air base rows: Name, Operating Country, Host Country, Year."""
    items: list[AirBase] = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        try:
            name = cols[0].get_text(strip=True)
            operating_country = _extract_country(cols[1])
            host_country = _extract_country(cols[2])
            year_text = cols[3].get_text(strip=True)
            year = int(year_text) if year_text.isdigit() else None
            items.append(
                AirBase(
                    name=name,
                    operating_country=operating_country,
                    host_country=host_country,
                    year_established=year,
                )
            )
        except (ValueError, IndexError):
            continue
    return items


def _parse_nuclear_rows(rows: list[Tag]) -> list[NuclearArsenal]:
    """Parse nuclear rows: Country, Total, Deployed, Stockpile, Retired."""
    items: list[NuclearArsenal] = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        try:
            country = _extract_country(cols[0])
            total_warheads = int(cols[1].get_text(strip=True))
            deployed = int(cols[2].get_text(strip=True))
            stockpile = int(cols[3].get_text(strip=True))
            retired = int(cols[4].get_text(strip=True))
            items.append(
                NuclearArsenal(
                    country=country,
                    total_warheads=total_warheads,
                    deployed=deployed,
                    stockpile=stockpile,
                    retired=retired,
                )
            )
        except (ValueError, IndexError):
            continue
    return items


def _parse_rank_rows(rows: list[Tag]) -> list[RankStructure]:
    """Parse rank rows: Name, NATO Code, Grade. Returns a single RankStructure."""
    entries: list[RankEntry] = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        try:
            name = cols[0].get_text(strip=True)
            nato_code = cols[1].get_text(strip=True) or None
            grade = cols[2].get_text(strip=True)
            entries.append(RankEntry(name=name, nato_code=nato_code, grade=grade))
        except (ValueError, IndexError):
            continue
    if entries:
        # Default country — will be set by the caller based on URL context
        return [
            RankStructure(
                country=Country(iso3="unk", name="Unknown"),
                branch="General",
                ranks=entries,
            )
        ]
    return []


def _parse_air_force_rows(rows: list[Tag]) -> list[AirForce]:
    """Parse air force rows: Rank, Country, Air Force Index, Total Aircraft."""
    items: list[AirForce] = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        try:
            rank = int(cols[0].get_text(strip=True))
            link = cols[1].find("a")
            if not link:
                continue
            country_name = link.get_text(strip=True)
            href = link.get("href", "")
            iso3 = _extract_iso3_from_url(href)
            country = Country(iso3=iso3, name=country_name)
            air_force_index = float(cols[2].get_text(strip=True))
            total_aircraft = int(cols[3].get_text(strip=True))
            items.append(
                AirForce(
                    country=country,
                    rank=rank,
                    air_force_index=air_force_index,
                    total_aircraft=total_aircraft,
                    detail_url=href,
                )
            )
        except (ValueError, IndexError):
            continue
    return items


def parse_pagination(html: str, current_page: int = 1) -> PageInfo:
    """Extract pagination info from HTML.

    Looks for `ul.pagination` and counts page links to determine total pages.
    """
    soup = BeautifulSoup(html, "html.parser")
    pagination = soup.select_one("ul.pagination")

    if not pagination:
        return PageInfo(
            current_page=current_page,
            total_pages=1,
            has_next=False,
            has_previous=current_page > 1,
        )

    page_links = pagination.find_all("a")
    max_page = 1
    for link in page_links:
        href = link.get("href", "")
        match = re.search(r"page=(\d+)", href)
        if match:
            page_num = int(match.group(1))
            max_page = max(max_page, page_num)

    total_pages = max(max_page, current_page)
    return PageInfo(
        current_page=current_page,
        total_pages=total_pages,
        has_next=current_page < total_pages,
        has_previous=current_page > 1,
    )


# ---- Helper Functions ----


def _extract_country(td: Tag) -> Country:
    """Extract Country from a table cell containing flag image + text."""
    img = td.find("img")
    iso3 = "unk"
    if img:
        alt = img.get("alt", "")
        if alt and len(alt) == 3 and alt.isalpha():
            iso3 = alt.lower()
        else:
            # Try to extract from src path
            src = img.get("src", "")
            match = re.search(r"/flags?/(\w{3})", src)
            if match:
                iso3 = match.group(1).lower()

    # Get country name — text content minus the image
    name = td.get_text(strip=True)
    return Country(iso3=iso3, name=name)


def _extract_slug(href: str) -> str:
    """Extract slug from a detail URL like '/aircraft/f-16-fighting-falcon/'."""
    parts = href.strip("/").split("/")
    return parts[-1] if parts else ""


def _extract_iso3_from_url(href: str) -> str:
    """Extract ISO-3 country code from URLs like '/navies/usa/'."""
    parts = href.strip("/").split("/")
    if parts:
        candidate = parts[-1].lower()
        if len(candidate) == 3 and candidate.isalpha():
            return candidate
    return "unk"
