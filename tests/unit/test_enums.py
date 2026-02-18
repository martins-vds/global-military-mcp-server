"""Unit tests for EquipmentCategory and InventoryCategory enums."""

import pytest

from src.domain.enums import EquipmentCategory, InventoryCategory


class TestEquipmentCategory:
    """T007: EquipmentCategory enum tests."""

    def test_all_values(self):
        assert set(EquipmentCategory) == {
            EquipmentCategory.aircraft,
            EquipmentCategory.missiles,
            EquipmentCategory.firearms,
            EquipmentCategory.vehicles,
            EquipmentCategory.ships,
        }

    def test_string_values(self):
        assert EquipmentCategory.aircraft.value == "aircraft"
        assert EquipmentCategory.missiles.value == "missiles"
        assert EquipmentCategory.firearms.value == "firearms"
        assert EquipmentCategory.vehicles.value == "vehicles"
        assert EquipmentCategory.ships.value == "ships"

    def test_url_segments(self):
        assert EquipmentCategory.aircraft.url_segment == "/aircraft/"
        assert EquipmentCategory.missiles.url_segment == "/missiles/"
        assert EquipmentCategory.firearms.url_segment == "/firearms/"
        assert EquipmentCategory.vehicles.url_segment == "/vehicles/"
        assert EquipmentCategory.ships.url_segment == "/ships/"

    def test_decade_filter_support(self):
        assert EquipmentCategory.aircraft.has_decade_filter is True
        assert EquipmentCategory.ships.has_decade_filter is True
        assert EquipmentCategory.missiles.has_decade_filter is False
        assert EquipmentCategory.firearms.has_decade_filter is False
        # vehicles is TBD — currently defaults to False
        assert EquipmentCategory.vehicles.has_decade_filter is False

    def test_sub_categories_aircraft(self):
        subs = EquipmentCategory.aircraft.sub_categories
        assert "combat" in subs
        assert "bomber" in subs
        assert "helicopter" in subs
        assert "uav" in subs
        assert len(subs) == 7

    def test_sub_categories_missiles(self):
        subs = EquipmentCategory.missiles.sub_categories
        assert "aam" in subs
        assert "sam" in subs
        assert len(subs) == 7

    def test_sub_categories_ships(self):
        subs = EquipmentCategory.ships.sub_categories
        assert "submarine" in subs
        assert "frigate" in subs
        assert len(subs) == 9

    def test_sub_categories_firearms(self):
        subs = EquipmentCategory.firearms.sub_categories
        assert "assault" in subs
        assert "sniper" in subs
        assert len(subs) == 9

    def test_sub_categories_vehicles_tbd(self):
        # Vehicles sub-categories are TBD
        assert EquipmentCategory.vehicles.sub_categories == []

    def test_has_name_search(self):
        for cat in EquipmentCategory:
            assert cat.has_name_search is True

    def test_has_country_filter(self):
        for cat in EquipmentCategory:
            assert cat.has_country_filter is True

    def test_from_string(self):
        assert EquipmentCategory("aircraft") == EquipmentCategory.aircraft
        with pytest.raises(ValueError):
            EquipmentCategory("invalid")


class TestInventoryCategory:
    """T007: InventoryCategory enum tests."""

    def test_all_values(self):
        assert set(InventoryCategory) == {
            InventoryCategory.air_forces,
            InventoryCategory.air_bases,
            InventoryCategory.navies,
            InventoryCategory.ranks,
            InventoryCategory.nuclear,
        }

    def test_url_segments(self):
        assert InventoryCategory.air_forces.url_segment == "/air-forces/"
        assert InventoryCategory.air_bases.url_segment == "/airbases/"
        assert InventoryCategory.navies.url_segment == "/navies/"
        assert InventoryCategory.ranks.url_segment == "/ranks/"
        assert InventoryCategory.nuclear.url_segment == "/nuclear/"

    def test_has_pagination(self):
        assert InventoryCategory.navies.has_pagination is False
        assert InventoryCategory.air_forces.has_pagination is True
        assert InventoryCategory.air_bases.has_pagination is True
        assert InventoryCategory.ranks.has_pagination is True
        assert InventoryCategory.nuclear.has_pagination is True

    def test_from_string(self):
        assert InventoryCategory("navies") == InventoryCategory.navies
        with pytest.raises(ValueError):
            InventoryCategory("invalid")
