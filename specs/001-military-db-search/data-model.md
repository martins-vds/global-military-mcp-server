# Data Model: Global Military Database Search MCP Server

**Date**: 2026-02-17
**Branch**: `001-military-db-search`
**Spec**: [spec.md](spec.md)
**Research**: [research.md](research.md)

---

## Enums

### EquipmentCategory

Represents the 5 equipment data domains on GlobalMilitary.net.

| Value      | Label    | URL Segment  | Has Decade Filter         |
| ---------- | -------- | ------------ | ------------------------- |
| `aircraft` | Aircraft | `/aircraft/` | ✅                         |
| `missiles` | Missiles | `/missiles/` | ❌                         |
| `firearms` | Firearms | `/firearms/` | ❌                         |
| `vehicles` | Vehicles | `/vehicles/` | TBD — confirm during T006 |
| `ships`    | Ships    | `/ships/`    | ✅                         |

> **Note**: Vehicles decade filter is unresolved — the research phase (R1) did not cover the `/vehicles/` page. To be confirmed during T006 (HTML fixture capture).

**Sub-categories** (used in filter URLs):
- Aircraft: `combat`, `bomber`, `helicopter`, `training`, `transport`, `uav`, `other`
- Missiles: `aam`, `ashm`, `asm`, `atm`, `ballistic`, `cruise`, `sam`
- Ships: `submarine`, `frigate`, `corvette`, `amphibious`, `cruiser`, `destroyer`, `carrier`, `patrol`, `mine`
- Firearms: `matsniper`, `assault`, `bullassault`, `shotgun`, `lmg`, `mg`, `smg`, `smp`, `sniper`
- Vehicles: TBD — confirm during T006 (HTML fixture capture)

### InventoryCategory

Represents the 5 inventory data domains on GlobalMilitary.net.

| Value        | Label      | URL Segment    |
| ------------ | ---------- | -------------- |
| `air_forces` | Air Forces | `/air-forces/` |
| `air_bases`  | Air Bases  | `/airbases/`   |
| `navies`     | Navies     | `/navies/`     |
| `ranks`      | Ranks      | `/ranks/`      |
| `nuclear`    | Nuclear    | `/nuclear/`    |

---

## Value Objects

### Country

Immutable identifier for a nation-state. Used for filtering and display.

| Field        | Type          | Constraints                     | Example           |
| ------------ | ------------- | ------------------------------- | ----------------- |
| `iso3`       | `str`         | Exactly 3 lowercase alpha chars | `"usa"`           |
| `name`       | `str`         | Non-empty                       | `"United States"` |
| `flag_emoji` | `str \| None` | Unicode flag emoji or None      | `"🇺🇸"`             |

**Invariants**: `iso3` must be 3 lowercase alphabetic characters.

### PageInfo

Immutable pagination metadata attached to every search result.

| Field          | Type   | Constraints | Example |
| -------------- | ------ | ----------- | ------- |
| `current_page` | `int`  | >= 1        | `1`     |
| `total_pages`  | `int`  | >= 1        | `10`    |
| `has_next`     | `bool` | —           | `True`  |
| `has_previous` | `bool` | —           | `False` |

**Invariants**: `current_page <= total_pages`. `has_next == (current_page < total_pages)`. `has_previous == (current_page > 1)`.

### Decade

Immutable value representing a decade for temporal filtering.

| Field  | Type  | Constraints                     | Example |
| ------ | ----- | ------------------------------- | ------- |
| `year` | `int` | Multiple of 10, range 1900-2030 | `1980`  |

**Invariants**: `year % 10 == 0` and `1900 <= year <= 2030`.

---

## Entities

### Equipment

Aggregate root for a single piece of military hardware. Fields vary by category but share a common base.

#### Common Fields (all categories)

| Field          | Type                | Source                       | Example                             |
| -------------- | ------------------- | ---------------------------- | ----------------------------------- |
| `name`         | `str`               | Table column 2 (link text)   | `"F-16 Fighting Falcon"`            |
| `slug`         | `str`               | Extracted from detail URL    | `"f-16-fighting-falcon"`            |
| `country`      | `Country`           | Table column 1 (flag + text) | `Country(iso3="usa", ...)`          |
| `category`     | `EquipmentCategory` | Known from page context      | `EquipmentCategory.aircraft`        |
| `sub_category` | `str \| None`       | Table column (if present)    | `"Combat"`                          |
| `detail_url`   | `str`               | Constructed from slug        | `"/aircraft/f-16-fighting-falcon/"` |

#### Category-Specific Fields

**Aircraft** (extends common):
| Field           | Type          | Source                   | Example                                  |
| --------------- | ------------- | ------------------------ | ---------------------------------------- |
| `manufacturer`  | `str \| None` | "Manufacturer" column    | `"Lockheed Martin"`                      |
| `produced`      | `int \| None` | "Produced" column        | `4604`                                   |
| `description`   | `str \| None` | "Description" column     | `"Multirole combat aircraft..."`         |
| `thumbnail_url` | `str \| None` | `<img>` src in table row | `"https://media.globalmilitary.net/..."` |

**Missiles** (extends common):
| Field       | Type          | Source                    | Example      |
| ----------- | ------------- | ------------------------- | ------------ |
| `range_km`  | `str \| None` | "Range" column (text)     | `"1000 km"`  |
| `max_speed` | `str \| None` | "Max Speed" column (text) | `"Mach 4.9"` |

**Ships** (extends common):
| Field       | Type          | Source        | Example     |
| ----------- | ------------- | ------------- | ----------- |
| `ship_type` | `str \| None` | "Type" column | `"Frigate"` |
| `year`      | `int \| None` | "Year" column | `2014`      |

**Firearms** (extends common):
| Field              | Type          | Source            | Example           |
| ------------------ | ------------- | ----------------- | ----------------- |
| `firearm_category` | `str \| None` | "Category" column | `"Assault rifle"` |

**Invariants**: `name` is non-empty. `slug` is non-empty and URL-safe. `detail_url` is constructable from category + slug.

### Inventory

Aggregate root for country-level military force composition. Sub-types represent different inventory domains.

#### Navy

| Field              | Type      | Source                      | Example                    |
| ------------------ | --------- | --------------------------- | -------------------------- |
| `country`          | `Country` | Column 2 (link text + flag) | `Country(iso3="usa", ...)` |
| `rank`             | `int`     | Column 1 ("#")              | `1`                        |
| `navy_index`       | `float`   | "Global Navy Index" column  | `323.8`                    |
| `capital_ships`    | `int`     | "Capital" column            | `24`                       |
| `major_combatants` | `int`     | "Major" column              | `113`                      |
| `total_active`     | `int`     | "Total" column              | `490`                      |
| `detail_url`       | `str`     | Constructed from ISO3       | `"/navies/usa/"`           |

#### AirBase

| Field               | Type            | Source           | Example                    |
| ------------------- | --------------- | ---------------- | -------------------------- |
| `name`              | `str`           | Base name        | `"Aviano Air Base"`        |
| `operating_country` | `Country`       | Operating nation | `Country(iso3="usa", ...)` |
| `host_country`      | `Country`       | Host nation      | `Country(iso3="ita", ...)` |
| `year_established`  | `int \| None`   | Year             | `1954`                     |
| `latitude`          | `float \| None` | Latitude (TBD)   | `46.0319`                  |
| `longitude`         | `float \| None` | Longitude (TBD)  | `12.5965`                  |

> **Note**: `latitude` and `longitude` are mentioned in spec.md Key Entities but not confirmed in research HTML columns. To be validated during T006 — if the air bases page does not include coordinates, these fields will be removed.

#### NuclearArsenal

| Field              | Type          | Source                 | Example                    |
| ------------------ | ------------- | ---------------------- | -------------------------- |
| `country`          | `Country`     | Nation                 | `Country(iso3="usa", ...)` |
| `total_warheads`   | `int`         | Total inventory        | `5550`                     |
| `deployed`         | `int`         | Deployed warheads      | `1744`                     |
| `stockpile`        | `int`         | Reserve stockpile      | `2000`                     |
| `retired`          | `int`         | Awaiting dismantlement | `1806`                     |
| `delivery_methods` | `str \| None` | Delivery systems (TBD) | `"ICBM, SLBM, bomber"`     |

> **Note**: `delivery_methods` is mentioned in spec.md Key Entities and US2 acceptance scenario 4 but not confirmed in research HTML columns. To be validated during T006 — if the nuclear page does not include delivery method data, this field will be removed and spec/scenarios updated.

#### AirForce

| Field             | Type      | Source                    | Example                    |
| ----------------- | --------- | ------------------------- | -------------------------- |
| `country`         | `Country` | Column (link text + flag) | `Country(iso3="usa", ...)` |
| `rank`            | `int`     | Ranking column            | `1`                        |
| `air_force_index` | `float`   | "Air Force Index" column  | `242.5`                    |
| `total_aircraft`  | `int`     | "Total Aircraft" column   | `5217`                     |
| `detail_url`      | `str`     | Constructed from ISO3     | `"/air-forces/usa/"`       |

> **Note**: Exact field names and availability TBD — to be confirmed during T006 (HTML fixture capture) when the air_forces page structure is researched. If the page structure differs significantly, this entity will be updated accordingly.

#### RankStructure

| Field     | Type              | Source          | Example                    |
| --------- | ----------------- | --------------- | -------------------------- |
| `country` | `Country`         | —               | `Country(iso3="usa", ...)` |
| `branch`  | `str`             | Military branch | `"Army"`                   |
| `ranks`   | `list[RankEntry]` | —               | See below                  |

**RankEntry** (value object):
| Field       | Type          | Example      |
| ----------- | ------------- | ------------ |
| `name`      | `str`         | `"Private"`  |
| `nato_code` | `str \| None` | `"OR-1"`     |
| `grade`     | `str`         | `"Enlisted"` |

---

## Request/Response Models

### SearchQuery

Structured request from the MCP client. Immutable value object.

| Field          | Type                                     | Required | Default | Constraints                                      |
| -------------- | ---------------------------------------- | -------- | ------- | ------------------------------------------------ |
| `category`     | `EquipmentCategory \| InventoryCategory` | ✅        | —       | Must be valid enum value                         |
| `query`        | `str \| None`                            | ❌        | `None`  | Name/keyword search text                         |
| `country`      | `str \| None`                            | ❌        | `None`  | ISO-3 country code                               |
| `sub_category` | `str \| None`                            | ❌        | `None`  | Sub-type slug (e.g., 'combat', 'aam', 'frigate') |
| `decade`       | `int \| None`                            | ❌        | `None`  | Multiple of 10, 1900-2030                        |
| `page`         | `int`                                    | ❌        | `1`     | >= 1                                             |

**Invariants**: At least one filtering parameter (`query`, `country`, `sub_category`, `decade`) should be provided, OR `page=1` for browsing. `decade` is only valid for categories that support it (aircraft, ships). `sub_category` must be a valid slug for the given category (see EquipmentCategory sub-categories).

### SearchResult

Structured response returned by search tools.

| Field             | Type                                 | Description                                                     |
| ----------------- | ------------------------------------ | --------------------------------------------------------------- |
| `items`           | `list[Equipment] \| list[Inventory]` | Matching entities                                               |
| `total_count`     | `int`                                | Estimated total across all pages                                |
| `page_info`       | `PageInfo`                           | Pagination metadata                                             |
| `query_notes`     | `str \| None`                        | Interpretation notes (e.g., "Searched aircraft by name 'F-16'") |
| `category`        | `str`                                | The category that was searched                                  |
| `filters_applied` | `dict[str, str]`                     | Active filters (country, decade, etc.)                          |

### ComparisonResult

Structured response from the compare_equipment tool.

| Field              | Type                | Description                        |
| ------------------ | ------------------- | ---------------------------------- |
| `items`            | `list[Equipment]`   | The compared equipment items (2-5) |
| `category`         | `EquipmentCategory` | Common category                    |
| `shared_fields`    | `list[str]`         | Field names present in all items   |
| `comparison_notes` | `str \| None`       | Any notes about the comparison     |

### IdentificationResult

Structured response from the identify_from_image tool. Differs from SearchResult — returns ranked matches with explanations rather than paginated listings.

| Field                  | Type                        | Description                                                                 |
| ---------------------- | --------------------------- | --------------------------------------------------------------------------- |
| `matches`              | `list[IdentificationMatch]` | Ordered list of matching equipment, best matches first                      |
| `identification_notes` | `str \| None`               | Notes about the identification process (e.g., "Direct name match found")    |
| `search_strategy`      | `str`                       | Strategy used: `name_search`, `category_country_browse`, or `global_search` |

**IdentificationMatch** (value object):

| Field          | Type        | Description                                                                                  |
| -------------- | ----------- | -------------------------------------------------------------------------------------------- |
| `equipment`    | `Equipment` | Full Equipment entity matching the description                                               |
| `match_reason` | `str`       | Why this item matched (e.g., "Direct name match: 'F-22 Raptor' found in aircraft database.") |

**Invariants**: `matches` may be empty (no match found). `search_strategy` must be one of the 3 defined values. `match_reason` is always a human-readable string (no numeric confidence — ranking is implicit via list order).

---

## State Transitions

### Cache Entry Lifecycle

```
[NOT_CACHED] ──fetch──> [CACHED] ──ttl_expires──> [EXPIRED] ──lazy_evict──> [NOT_CACHED]
                          │                                                       ▲
                          └──────invalidate────────────────────────────────────────┘
```

- **NOT_CACHED → CACHED**: First request triggers upstream fetch, result written to cache.
- **CACHED → EXPIRED**: TTL elapses (configurable, default 24h). Detected lazily on next `get()`.
- **EXPIRED → NOT_CACHED**: Expired entry deleted on access. Next request re-fetches.
- **CACHED → NOT_CACHED**: On-demand invalidation via `delete(key)` or `clear()`.

**Size Limit**: Maximum 500 entries (configurable via `max_entries`). When the cache exceeds `max_entries`, the oldest entries by write timestamp are evicted (LRU-style) on the next `set()` call. This prevents unbounded disk usage across categories × countries × pages.

### Rate Limiter State Machine

```
[IDLE] ──acquire()──> [WAITING] ──interval_elapsed──> [ACQUIRED] ──request_done──> [IDLE]
                         │                                  │
                         └──sleep(remaining)────────────────┘
```

- **IDLE**: No pending request. Lock available.
- **WAITING**: Lock acquired; checking if min_interval has passed since last request.
- **ACQUIRED**: Interval satisfied; request proceeds. Timestamp updated.

---

## Relationships

```
SearchQuery ──validates──> EquipmentCategory | InventoryCategory
    │
    ├──[equipment search]──> Scraper ──fetches──> GlobalMilitary.net
    │                           │
    │                           ├──[cache miss]──> RateLimiter ──acquire──> httpx.get()
    │                           │                                              │
    │                           │                  Parser ──parse──> list[Equipment]
    │                           │                     │
    │                           └──[cache hit]──> FileCache ──get──> list[Equipment]
    │
    └──[build response]──> SearchResult (items + PageInfo + query_notes)

ComparisonRequest ──fetches N items──> SearchResult[] ──merges──> ComparisonResult
```

---

## Validation Rules Summary

| Entity                  | Rule                                                          | Error                                                                   |
| ----------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------- |
| EquipmentCategory       | Must be one of: aircraft, missiles, firearms, vehicles, ships | `ToolError("Invalid equipment category '{value}'. Valid: ...")`         |
| InventoryCategory       | Must be one of: air_forces, air_bases, navies, ranks, nuclear | `ToolError("Invalid inventory category '{value}'. Valid: ...")`         |
| Country (iso3)          | 3 lowercase alpha chars                                       | `ToolError("Country code must be 3 letters (ISO 3166-1 alpha-3)")`      |
| Decade                  | Multiple of 10, 1900-2030                                     | `ToolError("Decade must be a multiple of 10 between 1900 and 2030")`    |
| Page                    | Integer >= 1                                                  | `ToolError("Page must be a positive integer")`                          |
| Compare: category match | All items must be same EquipmentCategory                      | `ToolError("Comparisons are only meaningful within the same category")` |
| Compare: item count     | 2-5 items                                                     | `ToolError("Please provide 2 to 5 items to compare")`                   |
