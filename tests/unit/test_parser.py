"""Unit tests for HTML parser — equipment and inventory parsing from fixture HTML."""

from pathlib import Path

import pytest

from src.domain.enums import EquipmentCategory, InventoryCategory
from src.scraper.parser import (
    parse_equipment_html,
    parse_inventory_html,
    parse_pagination,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "html"


class TestParseEquipmentAircraft:
    """T018: Parse aircraft HTML table (6 columns)."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "aircraft.html").read_text()

    def test_extracts_all_items(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.aircraft)
        assert len(items) == 3

    def test_first_item_fields(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.aircraft)
        f16 = items[0]
        assert f16.name == "F-16 Fighting Falcon"
        assert f16.slug == "f-16-fighting-falcon"
        assert f16.country.name == "United States"
        assert f16.country.iso3 == "usa"
        assert f16.category == EquipmentCategory.aircraft
        assert f16.detail_url == "/aircraft/f-16-fighting-falcon/"
        assert f16.manufacturer == "Lockheed Martin"
        assert f16.produced == 4604
        assert f16.description == "Multirole combat aircraft"
        assert f16.thumbnail_url == "https://media.globalmilitary.net/f16.jpg"

    def test_russian_aircraft(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.aircraft)
        su57 = items[2]
        assert su57.name == "Su-57"
        assert su57.country.iso3 == "rus"
        assert su57.manufacturer == "Sukhoi"


class TestParseEquipmentMissiles:
    """T018: Parse missiles HTML table (5 columns)."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "missiles.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.missiles)
        assert len(items) == 2

    def test_missile_fields(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.missiles)
        amraam = items[0]
        assert amraam.name == "AIM-120 AMRAAM"
        assert amraam.slug == "aim-120-amraam"
        assert amraam.sub_category == "AAM"
        assert amraam.range_km == "180 km"
        assert amraam.max_speed == "Mach 4.0"


class TestParseEquipmentShips:
    """T018: Parse ships HTML table (4 columns)."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "ships.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.ships)
        assert len(items) == 2

    def test_ship_fields(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.ships)
        burke = items[0]
        assert burke.name == "Arleigh Burke"
        assert burke.ship_type == "Destroyer"
        assert burke.year == 1991


class TestParseEquipmentFirearms:
    """T018: Parse firearms HTML table (3 columns)."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "firearms.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.firearms)
        assert len(items) == 2

    def test_firearm_fields(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.firearms)
        m4 = items[0]
        assert m4.name == "M4 Carbine"
        assert m4.firearm_category == "Assault rifle"


class TestParseEquipmentVehicles:
    """T018: Parse vehicles HTML table (3 columns, same as firearms)."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "vehicles.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.vehicles)
        assert len(items) == 2

    def test_vehicle_fields(self, html: str):
        items = parse_equipment_html(html, EquipmentCategory.vehicles)
        abrams = items[0]
        assert abrams.name == "M1 Abrams"
        assert abrams.slug == "m1-abrams"


class TestParsePagination:
    """T018: Pagination detection from HTML."""

    def test_with_pagination(self):
        html = (FIXTURES_DIR / "aircraft.html").read_text()
        page_info = parse_pagination(html, current_page=1)
        assert page_info.current_page == 1
        assert page_info.total_pages == 3
        assert page_info.has_next is True
        assert page_info.has_previous is False

    def test_without_pagination(self):
        html = (FIXTURES_DIR / "firearms.html").read_text()
        page_info = parse_pagination(html, current_page=1)
        assert page_info.current_page == 1
        assert page_info.total_pages == 1
        assert page_info.has_next is False
        assert page_info.has_previous is False

    def test_middle_page(self):
        html = (FIXTURES_DIR / "aircraft.html").read_text()
        page_info = parse_pagination(html, current_page=2)
        assert page_info.current_page == 2
        assert page_info.total_pages == 3
        assert page_info.has_next is True
        assert page_info.has_previous is True


class TestParseInventoryNavies:
    """T025: Parse navies HTML table."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "navies.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.navies)
        assert len(items) == 3

    def test_navy_fields(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.navies)
        usa = items[0]
        assert usa.country.iso3 == "usa"
        assert usa.rank == 1
        assert usa.navy_index == 323.8
        assert usa.capital_ships == 24
        assert usa.major_combatants == 113
        assert usa.total_active == 490
        assert usa.detail_url == "/navies/usa/"


class TestParseInventoryAirBases:
    """T025: Parse air bases HTML table."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "air_bases.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.air_bases)
        assert len(items) == 2

    def test_air_base_fields(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.air_bases)
        aviano = items[0]
        assert aviano.name == "Aviano Air Base"
        assert aviano.operating_country.iso3 == "usa"
        assert aviano.host_country.iso3 == "ita"
        assert aviano.year_established == 1954


class TestParseInventoryNuclear:
    """T025: Parse nuclear HTML table."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "nuclear.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.nuclear)
        assert len(items) == 2

    def test_nuclear_fields(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.nuclear)
        usa = items[0]
        assert usa.country.iso3 == "usa"
        assert usa.total_warheads == 5550
        assert usa.deployed == 1744
        assert usa.stockpile == 2000
        assert usa.retired == 1806


class TestParseInventoryRanks:
    """T025: Parse ranks HTML table."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "ranks.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.ranks)
        # Ranks returns a single RankStructure with multiple entries
        assert len(items) == 1

    def test_rank_fields(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.ranks)
        structure = items[0]
        assert len(structure.ranks) == 3
        assert structure.ranks[0].name == "Private"
        assert structure.ranks[0].nato_code == "OR-1"
        assert structure.ranks[0].grade == "Enlisted"


class TestParseInventoryAirForces:
    """T025: Parse air forces HTML table."""

    @pytest.fixture
    def html(self) -> str:
        return (FIXTURES_DIR / "air_forces.html").read_text()

    def test_extracts_items(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.air_forces)
        assert len(items) == 2

    def test_air_force_fields(self, html: str):
        items = parse_inventory_html(html, InventoryCategory.air_forces)
        usa = items[0]
        assert usa.country.iso3 == "usa"
        assert usa.rank == 1
        assert usa.air_force_index == 242.5
        assert usa.total_aircraft == 5217
        assert usa.detail_url == "/air-forces/usa/"
