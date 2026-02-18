"""Unit tests for URL construction patterns."""

import pytest

from src.domain.enums import EquipmentCategory, InventoryCategory
from src.scraper.urls import (
    BASE_URL,
    build_equipment_url,
    build_inventory_url,
    equipment_detail_url,
    equipment_filter_category_url,
    equipment_filter_country_url,
    equipment_filter_decade_url,
    equipment_list_url,
    equipment_paginate_url,
    equipment_search_url,
    global_search_url,
    inventory_list_url,
    inventory_paginate_url,
)


class TestEquipmentURLs:
    """T014: Equipment URL pattern tests."""

    def test_list_url(self):
        url = equipment_list_url(EquipmentCategory.aircraft)
        assert url == f"{BASE_URL}/aircraft/"

    def test_search_url(self):
        url = equipment_search_url(EquipmentCategory.aircraft, "F-35")
        assert url == f"{BASE_URL}/aircraft/?name=F-35"

    def test_paginate_url(self):
        url = equipment_paginate_url(EquipmentCategory.missiles, 3)
        assert url == f"{BASE_URL}/missiles/?page=3"

    def test_filter_category_url(self):
        url = equipment_filter_category_url(EquipmentCategory.aircraft, "combat")
        assert url == f"{BASE_URL}/aircraft/category/combat/"

    def test_filter_country_url(self):
        url = equipment_filter_country_url(EquipmentCategory.aircraft, "usa")
        assert url == f"{BASE_URL}/aircraft/country/usa/"

    def test_filter_decade_url(self):
        url = equipment_filter_decade_url(EquipmentCategory.aircraft, 1980)
        assert url == f"{BASE_URL}/aircraft/decade/1980/"

    def test_detail_url(self):
        url = equipment_detail_url(EquipmentCategory.aircraft, "f-16-fighting-falcon")
        assert url == f"{BASE_URL}/aircraft/f-16-fighting-falcon/"

    def test_global_search_url(self):
        url = global_search_url("stealth fighter")
        assert url == f"{BASE_URL}/search/?q=stealth fighter"


class TestBuildEquipmentURL:
    """T014: build_equipment_url composite URL builder tests."""

    def test_no_filters(self):
        url = build_equipment_url(EquipmentCategory.aircraft)
        assert url == f"{BASE_URL}/aircraft/"

    def test_sub_category_only(self):
        url = build_equipment_url(EquipmentCategory.aircraft, sub_category="combat")
        assert url == f"{BASE_URL}/aircraft/category/combat/"

    def test_sub_category_with_page(self):
        url = build_equipment_url(
            EquipmentCategory.aircraft, sub_category="combat", page=2
        )
        assert url == f"{BASE_URL}/aircraft/category/combat/?page=2"

    def test_country_only(self):
        url = build_equipment_url(EquipmentCategory.aircraft, country="usa")
        assert url == f"{BASE_URL}/aircraft/country/usa/"

    def test_country_with_page(self):
        url = build_equipment_url(EquipmentCategory.aircraft, country="usa", page=3)
        assert url == f"{BASE_URL}/aircraft/country/usa/?page=3"

    def test_decade_only(self):
        url = build_equipment_url(EquipmentCategory.aircraft, decade=1980)
        assert url == f"{BASE_URL}/aircraft/decade/1980/"

    def test_query_only(self):
        url = build_equipment_url(EquipmentCategory.aircraft, query="F-35")
        assert url == f"{BASE_URL}/aircraft/?name=F-35"

    def test_query_with_page(self):
        url = build_equipment_url(EquipmentCategory.aircraft, query="F-35", page=2)
        assert url == f"{BASE_URL}/aircraft/?name=F-35&page=2"

    def test_page_only(self):
        url = build_equipment_url(EquipmentCategory.aircraft, page=5)
        assert url == f"{BASE_URL}/aircraft/?page=5"

    def test_priority_sub_category_over_country(self):
        """sub_category takes priority over country."""
        url = build_equipment_url(
            EquipmentCategory.aircraft, sub_category="combat", country="usa"
        )
        assert "category/combat" in url
        assert "country/usa" not in url

    def test_priority_country_over_decade(self):
        """country takes priority over decade."""
        url = build_equipment_url(
            EquipmentCategory.aircraft, country="usa", decade=1980
        )
        assert "country/usa" in url
        assert "decade/1980" not in url


class TestInventoryURLs:
    """T014: Inventory URL pattern tests."""

    def test_list_url(self):
        url = inventory_list_url(InventoryCategory.navies)
        assert url == f"{BASE_URL}/navies/"

    def test_list_url_air_forces(self):
        url = inventory_list_url(InventoryCategory.air_forces)
        assert url == f"{BASE_URL}/air_forces/"

    def test_list_url_air_bases(self):
        url = inventory_list_url(InventoryCategory.air_bases)
        assert url == f"{BASE_URL}/airbases/"

    def test_paginate_url(self):
        url = inventory_paginate_url(InventoryCategory.air_bases, 2)
        assert url == f"{BASE_URL}/airbases/?page=2"

    def test_build_inventory_url_no_pagination(self):
        url = build_inventory_url(InventoryCategory.navies, page=2)
        # Navies has no pagination, should return base URL
        assert url == f"{BASE_URL}/navies/"

    def test_build_inventory_url_with_pagination(self):
        url = build_inventory_url(InventoryCategory.air_bases, page=3)
        assert url == f"{BASE_URL}/airbases/?page=3"

    def test_build_inventory_url_page_1(self):
        url = build_inventory_url(InventoryCategory.air_bases, page=1)
        # Page 1 is the default, no ?page= needed
        assert url == f"{BASE_URL}/airbases/"
