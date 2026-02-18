"""Unit tests for domain models: value objects, entities, and request/response types."""

import pytest

from src.domain.enums import EquipmentCategory, InventoryCategory
from src.domain.models import (
    AirBase,
    AirForce,
    ComparisonResult,
    Country,
    Decade,
    Equipment,
    IdentificationMatch,
    IdentificationResult,
    Navy,
    NuclearArsenal,
    PageInfo,
    RankEntry,
    RankStructure,
    SearchQuery,
    SearchResult,
)


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


class TestCountry:
    """T008: Country value object tests."""

    def test_valid_country(self):
        c = Country(iso3="usa", name="United States")
        assert c.iso3 == "usa"
        assert c.name == "United States"
        assert c.flag_emoji is None

    def test_with_flag(self):
        c = Country(iso3="usa", name="United States", flag_emoji="🇺🇸")
        assert c.flag_emoji == "🇺🇸"

    def test_iso3_must_be_lowercase(self):
        with pytest.raises(ValueError):
            Country(iso3="USA", name="United States")

    def test_iso3_must_be_3_chars(self):
        with pytest.raises(ValueError):
            Country(iso3="us", name="United States")
        with pytest.raises(ValueError):
            Country(iso3="usaa", name="United States")

    def test_iso3_must_be_alpha(self):
        with pytest.raises(ValueError):
            Country(iso3="u1a", name="United States")

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValueError):
            Country(iso3="usa", name="")


class TestPageInfo:
    """T008: PageInfo value object tests."""

    def test_valid_page_info(self):
        pi = PageInfo(current_page=1, total_pages=10, has_next=True, has_previous=False)
        assert pi.current_page == 1
        assert pi.total_pages == 10

    def test_current_page_must_be_lte_total(self):
        with pytest.raises(ValueError):
            PageInfo(current_page=11, total_pages=10, has_next=False, has_previous=True)

    def test_has_next_invariant(self):
        with pytest.raises(ValueError, match="has_next"):
            PageInfo(current_page=10, total_pages=10, has_next=True, has_previous=True)

    def test_has_previous_invariant(self):
        with pytest.raises(ValueError, match="has_previous"):
            PageInfo(current_page=1, total_pages=10, has_next=True, has_previous=True)

    def test_single_page(self):
        pi = PageInfo(current_page=1, total_pages=1, has_next=False, has_previous=False)
        assert pi.has_next is False
        assert pi.has_previous is False

    def test_middle_page(self):
        pi = PageInfo(current_page=5, total_pages=10, has_next=True, has_previous=True)
        assert pi.has_next is True
        assert pi.has_previous is True


class TestDecade:
    """T008: Decade value object tests."""

    def test_valid_decade(self):
        d = Decade(year=1980)
        assert d.year == 1980

    def test_must_be_multiple_of_10(self):
        with pytest.raises(ValueError, match="multiple of 10"):
            Decade(year=1985)

    def test_min_year(self):
        d = Decade(year=1900)
        assert d.year == 1900

    def test_max_year(self):
        d = Decade(year=2030)
        assert d.year == 2030

    def test_below_min(self):
        with pytest.raises(ValueError):
            Decade(year=1890)

    def test_above_max(self):
        with pytest.raises(ValueError):
            Decade(year=2040)


# ---------------------------------------------------------------------------
# Equipment Entity
# ---------------------------------------------------------------------------


class TestEquipment:
    """T009: Equipment entity tests."""

    def _make_country(self, iso3: str = "usa") -> Country:
        return Country(iso3=iso3, name="United States")

    def test_aircraft_equipment(self):
        e = Equipment(
            name="F-16 Fighting Falcon",
            slug="f-16-fighting-falcon",
            country=self._make_country(),
            category=EquipmentCategory.aircraft,
            sub_category="Combat",
            detail_url="/aircraft/f-16-fighting-falcon/",
            manufacturer="Lockheed Martin",
            produced=4604,
            description="Multirole combat aircraft",
            thumbnail_url="https://media.globalmilitary.net/f16.jpg",
        )
        assert e.name == "F-16 Fighting Falcon"
        assert e.manufacturer == "Lockheed Martin"
        assert e.produced == 4604

    def test_missile_equipment(self):
        e = Equipment(
            name="AIM-120 AMRAAM",
            slug="aim-120-amraam",
            country=self._make_country(),
            category=EquipmentCategory.missiles,
            detail_url="/missiles/aim-120-amraam/",
            range_km="1000 km",
            max_speed="Mach 4.9",
        )
        assert e.range_km == "1000 km"
        assert e.max_speed == "Mach 4.9"

    def test_ship_equipment(self):
        e = Equipment(
            name="Arleigh Burke",
            slug="arleigh-burke",
            country=self._make_country(),
            category=EquipmentCategory.ships,
            detail_url="/ships/arleigh-burke/",
            ship_type="Destroyer",
            year=1991,
        )
        assert e.ship_type == "Destroyer"
        assert e.year == 1991

    def test_firearm_equipment(self):
        e = Equipment(
            name="M4 Carbine",
            slug="m4-carbine",
            country=self._make_country(),
            category=EquipmentCategory.firearms,
            detail_url="/firearms/m4-carbine/",
            firearm_category="Assault rifle",
        )
        assert e.firearm_category == "Assault rifle"

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            Equipment(
                name="",
                slug="test",
                country=self._make_country(),
                category=EquipmentCategory.aircraft,
                detail_url="/aircraft/test/",
            )

    def test_slug_must_be_url_safe(self):
        with pytest.raises(ValueError, match="URL-safe"):
            Equipment(
                name="Test",
                slug="Invalid Slug!",
                country=self._make_country(),
                category=EquipmentCategory.aircraft,
                detail_url="/aircraft/test/",
            )

    def test_slug_with_hyphens_and_numbers(self):
        e = Equipment(
            name="F-22 Raptor",
            slug="f-22-raptor",
            country=self._make_country(),
            category=EquipmentCategory.aircraft,
            detail_url="/aircraft/f-22-raptor/",
        )
        assert e.slug == "f-22-raptor"


# ---------------------------------------------------------------------------
# Inventory Entities
# ---------------------------------------------------------------------------


class TestNavy:
    """T010: Navy entity tests."""

    def test_valid_navy(self):
        n = Navy(
            country=Country(iso3="usa", name="United States"),
            rank=1,
            navy_index=323.8,
            capital_ships=24,
            major_combatants=113,
            total_active=490,
            detail_url="/navies/usa/",
        )
        assert n.rank == 1
        assert n.navy_index == 323.8
        assert n.capital_ships == 24
        assert n.major_combatants == 113


class TestAirBase:
    """T010: AirBase entity tests."""

    def test_valid_air_base(self):
        ab = AirBase(
            name="Aviano Air Base",
            operating_country=Country(iso3="usa", name="United States"),
            host_country=Country(iso3="ita", name="Italy"),
            year_established=1954,
        )
        assert ab.name == "Aviano Air Base"
        assert ab.year_established == 1954

    def test_optional_coordinates(self):
        ab = AirBase(
            name="Test Base",
            operating_country=Country(iso3="usa", name="United States"),
            host_country=Country(iso3="usa", name="United States"),
            latitude=46.0319,
            longitude=12.5965,
        )
        assert ab.latitude == 46.0319


class TestNuclearArsenal:
    """T010: NuclearArsenal entity tests."""

    def test_valid_nuclear(self):
        na = NuclearArsenal(
            country=Country(iso3="usa", name="United States"),
            total_warheads=5550,
            deployed=1744,
            stockpile=2000,
            retired=1806,
        )
        assert na.total_warheads == 5550
        assert na.deployed == 1744

    def test_optional_delivery_methods(self):
        na = NuclearArsenal(
            country=Country(iso3="usa", name="United States"),
            total_warheads=5550,
            deployed=1744,
            stockpile=2000,
            retired=1806,
            delivery_methods="ICBM, SLBM, bomber",
        )
        assert na.delivery_methods == "ICBM, SLBM, bomber"


class TestAirForce:
    """T010: AirForce entity tests."""

    def test_valid_air_force(self):
        af = AirForce(
            country=Country(iso3="usa", name="United States"),
            rank=1,
            air_force_index=242.5,
            total_aircraft=5217,
            detail_url="/air-forces/usa/",
        )
        assert af.rank == 1
        assert af.total_aircraft == 5217


class TestRankStructure:
    """T010: RankStructure entity tests."""

    def test_valid_rank_structure(self):
        rs = RankStructure(
            country=Country(iso3="usa", name="United States"),
            branch="Army",
            ranks=[
                RankEntry(name="Private", nato_code="OR-1", grade="Enlisted"),
                RankEntry(name="General", nato_code="OF-10", grade="Officer"),
            ],
        )
        assert rs.branch == "Army"
        assert len(rs.ranks) == 2
        assert rs.ranks[0].nato_code == "OR-1"


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class TestSearchQuery:
    """T011: SearchQuery request model tests."""

    def test_minimal_query(self):
        q = SearchQuery(category=EquipmentCategory.aircraft)
        assert q.page == 1
        assert q.query is None

    def test_full_equipment_query(self):
        q = SearchQuery(
            category=EquipmentCategory.aircraft,
            query="F-35",
            country="usa",
            sub_category="combat",
            decade=1980,
            page=2,
        )
        assert q.query == "F-35"
        assert q.country == "usa"
        assert q.decade == 1980

    def test_inventory_query(self):
        q = SearchQuery(category=InventoryCategory.navies)
        assert q.category == InventoryCategory.navies

    def test_invalid_decade(self):
        with pytest.raises(ValueError, match="multiple of 10"):
            SearchQuery(category=EquipmentCategory.aircraft, decade=1985)

    def test_invalid_country_code(self):
        with pytest.raises(ValueError):
            SearchQuery(category=EquipmentCategory.aircraft, country="US")

    def test_invalid_page(self):
        with pytest.raises(ValueError):
            SearchQuery(category=EquipmentCategory.aircraft, page=0)


class TestSearchResult:
    """T011: SearchResult response model tests."""

    def test_with_equipment_items(self):
        item = Equipment(
            name="F-16",
            slug="f-16",
            country=Country(iso3="usa", name="United States"),
            category=EquipmentCategory.aircraft,
            detail_url="/aircraft/f-16/",
        )
        result = SearchResult(
            items=[item],
            total_count=1,
            page_info=PageInfo(
                current_page=1, total_pages=1, has_next=False, has_previous=False
            ),
            category="aircraft",
            query_notes="Searched aircraft by name 'F-16'",
        )
        assert result.total_count == 1
        assert len(result.items) == 1

    def test_with_navy_items(self):
        item = Navy(
            country=Country(iso3="usa", name="United States"),
            rank=1,
            navy_index=323.8,
            capital_ships=24,
            major_combatants=113,
            total_active=490,
            detail_url="/navies/usa/",
        )
        result = SearchResult(
            items=[item],
            total_count=1,
            page_info=PageInfo(
                current_page=1, total_pages=1, has_next=False, has_previous=False
            ),
            category="navies",
        )
        assert result.total_count == 1


class TestComparisonResult:
    """T011: ComparisonResult response model tests."""

    def test_valid_comparison(self):
        items = [
            Equipment(
                name="F-16",
                slug="f-16",
                country=Country(iso3="usa", name="United States"),
                category=EquipmentCategory.aircraft,
                detail_url="/aircraft/f-16/",
                manufacturer="Lockheed Martin",
            ),
            Equipment(
                name="F-22",
                slug="f-22",
                country=Country(iso3="usa", name="United States"),
                category=EquipmentCategory.aircraft,
                detail_url="/aircraft/f-22/",
                manufacturer="Lockheed Martin",
            ),
        ]
        result = ComparisonResult(
            items=items,
            category=EquipmentCategory.aircraft,
            shared_fields=["manufacturer", "country"],
            comparison_notes="Both built by Lockheed Martin",
        )
        assert len(result.items) == 2
        assert "manufacturer" in result.shared_fields


class TestIdentificationResult:
    """T011: IdentificationResult response model tests."""

    def test_valid_identification(self):
        match = IdentificationMatch(
            equipment=Equipment(
                name="F-22 Raptor",
                slug="f-22-raptor",
                country=Country(iso3="usa", name="United States"),
                category=EquipmentCategory.aircraft,
                detail_url="/aircraft/f-22-raptor/",
            ),
            match_reason="Direct name match: 'F-22 Raptor' found in aircraft database.",
        )
        result = IdentificationResult(
            matches=[match],
            identification_notes="Direct name match found",
            search_strategy="name_search",
        )
        assert len(result.matches) == 1
        assert result.search_strategy == "name_search"

    def test_empty_matches(self):
        result = IdentificationResult(
            matches=[],
            identification_notes="No matches found",
            search_strategy="global_search",
        )
        assert len(result.matches) == 0

    def test_invalid_search_strategy(self):
        with pytest.raises(ValueError, match="search_strategy"):
            IdentificationResult(
                matches=[],
                search_strategy="invalid_strategy",
            )
