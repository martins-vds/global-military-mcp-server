"""Domain models: value objects, entities, and request/response types."""

from __future__ import annotations

import re
from typing import Union

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.enums import EquipmentCategory, InventoryCategory


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


class Country(BaseModel):
    """Immutable identifier for a nation-state."""

    iso3: str = Field(..., pattern=r"^[a-z]{3}$", description="3 lowercase alpha chars")
    name: str = Field(..., min_length=1)
    flag_emoji: str | None = None


class PageInfo(BaseModel):
    """Immutable pagination metadata."""

    current_page: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=1)
    has_next: bool
    has_previous: bool

    @model_validator(mode="after")
    def _check_invariants(self) -> PageInfo:
        if self.current_page > self.total_pages:
            raise ValueError(
                f"current_page ({self.current_page}) must be <= total_pages ({self.total_pages})"
            )
        if self.has_next != (self.current_page < self.total_pages):
            raise ValueError("has_next must equal (current_page < total_pages)")
        if self.has_previous != (self.current_page > 1):
            raise ValueError("has_previous must equal (current_page > 1)")
        return self


class Decade(BaseModel):
    """Immutable decade value for temporal filtering."""

    year: int = Field(..., ge=1900, le=2030)

    @field_validator("year")
    @classmethod
    def _must_be_multiple_of_ten(cls, v: int) -> int:
        if v % 10 != 0:
            raise ValueError(f"Decade must be a multiple of 10, got {v}")
        return v


# ---------------------------------------------------------------------------
# Entities — Equipment
# ---------------------------------------------------------------------------


class Equipment(BaseModel):
    """Aggregate root for a single piece of military hardware."""

    # Common fields
    name: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1)
    country: Country
    category: EquipmentCategory
    sub_category: str | None = None
    detail_url: str

    # Aircraft-specific
    manufacturer: str | None = None
    produced: int | None = None
    description: str | None = None
    thumbnail_url: str | None = None

    # Missiles-specific
    range_km: str | None = None
    max_speed: str | None = None

    # Ships-specific
    ship_type: str | None = None
    year: int | None = None

    # Firearms-specific
    firearm_category: str | None = None

    @field_validator("slug")
    @classmethod
    def _slug_must_be_url_safe(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", v):
            raise ValueError(f"slug must be URL-safe, got '{v}'")
        return v


# ---------------------------------------------------------------------------
# Entities — Inventory
# ---------------------------------------------------------------------------


class Navy(BaseModel):
    """Navy fleet composition for a country."""

    country: Country
    rank: int
    navy_index: float
    capital_ships: int
    major_combatants: int
    total_active: int
    detail_url: str


class AirBase(BaseModel):
    """Military air base."""

    name: str = Field(..., min_length=1)
    operating_country: Country
    host_country: Country
    year_established: int | None = None
    latitude: float | None = None
    longitude: float | None = None


class NuclearArsenal(BaseModel):
    """Nuclear arsenal inventory for a country."""

    country: Country
    total_warheads: int
    deployed: int
    stockpile: int
    retired: int
    delivery_methods: str | None = None


class AirForce(BaseModel):
    """Air force composition for a country."""

    country: Country
    rank: int
    air_force_index: float
    total_aircraft: int
    detail_url: str


class RankEntry(BaseModel):
    """Single rank within a military branch."""

    name: str = Field(..., min_length=1)
    nato_code: str | None = None
    grade: str


class RankStructure(BaseModel):
    """Rank hierarchy for a country's military branch."""

    country: Country
    branch: str
    ranks: list[RankEntry]


# Union type for all inventory entities
Inventory = Union[Navy, AirBase, NuclearArsenal, AirForce, RankStructure]


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class SearchQuery(BaseModel):
    """Structured request from the MCP client."""

    category: EquipmentCategory | InventoryCategory
    query: str | None = None
    country: str | None = Field(None, pattern=r"^[a-z]{3}$")
    sub_category: str | None = None
    decade: int | None = None
    page: int = Field(1, ge=1)

    @field_validator("decade")
    @classmethod
    def _validate_decade(cls, v: int | None) -> int | None:
        if v is not None:
            if v % 10 != 0:
                raise ValueError(
                    "Decade must be a multiple of 10 between 1900 and 2030"
                )
            if not (1900 <= v <= 2030):
                raise ValueError(
                    "Decade must be a multiple of 10 between 1900 and 2030"
                )
        return v


class SearchResult(BaseModel):
    """Structured response from search tools."""

    items: (
        list[Equipment]
        | list[Navy]
        | list[AirBase]
        | list[NuclearArsenal]
        | list[AirForce]
        | list[RankStructure]
    )
    total_count: int
    page_info: PageInfo
    query_notes: str | None = None
    category: str
    filters_applied: dict[str, str] = Field(default_factory=dict)


class ComparisonResult(BaseModel):
    """Structured response from compare_equipment tool."""

    items: list[Equipment]
    category: EquipmentCategory
    shared_fields: list[str]
    comparison_notes: str | None = None


class IdentificationMatch(BaseModel):
    """A single match in equipment identification."""

    equipment: Equipment
    match_reason: str


class IdentificationResult(BaseModel):
    """Structured response from identify_from_image tool."""

    matches: list[IdentificationMatch]
    identification_notes: str | None = None
    search_strategy: str = Field(
        ...,
        description="Strategy used: name_search, category_country_browse, or global_search",
    )

    @field_validator("search_strategy")
    @classmethod
    def _validate_strategy(cls, v: str) -> str:
        valid = {"name_search", "category_country_browse", "global_search"}
        if v not in valid:
            raise ValueError(f"search_strategy must be one of {valid}, got '{v}'")
        return v
