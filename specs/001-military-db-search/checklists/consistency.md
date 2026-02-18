# Cross-Artifact Consistency Checklist: Global Military Database Search MCP Server

**Purpose**: Validate naming/terminology alignment, data-model ↔ contract fidelity, and spec FR traceability across all design artifacts (spec.md, plan.md, data-model.md, contracts/*.json, research.md, quickstart.md).
**Created**: 2026-02-17
**Feature**: [spec.md](../spec.md)
**Depth**: Standard | **Focus**: Naming alignment, Schema fidelity, FR coverage

## Naming & Terminology Alignment

- [ ] CHK001 - Are the 4 MCP tool names (`search_equipment`, `search_inventory`, `compare_equipment`, `identify_from_image`) spelled identically across spec.md FRs, plan.md summary, all contract JSON files, and quickstart.md tools table? [Consistency, Spec §FR-001/002/009/010]
- [ ] CHK002 - Are the EquipmentCategory enum values (`aircraft`, `missiles`, `firearms`, `vehicles`, `ships`) identical across data-model.md, search-equipment.json `inputSchema.category.enum`, compare-equipment.json `inputSchema.category.enum`, identify-from-image.json `category.enum`, and resources.json `equipment_categories[].id`? [Consistency]
- [ ] CHK003 - Are the InventoryCategory enum values (`air_forces`, `air_bases`, `navies`, `ranks`, `nuclear`) identical across data-model.md, search-inventory.json `inputSchema.category.enum`, and resources.json `inventory_categories[].id`? [Consistency]
- [ ] CHK004 - Does plan.md Principle III evidence ("items list, total_count, page, total_pages, query_notes") match the actual SearchResult field names in data-model.md (`items`, `total_count`, `page_info`, `query_notes`, `category`, `filters_applied`)? The plan uses `page`/`total_pages` but the model nests these inside `page_info`. [Consistency, plan.md §Principle III]
- [ ] CHK005 - Does plan.md Principle IV evidence mention "asyncio.Semaphore for rate limiting" while research.md R4 specifies "asyncio.Lock"? These are different concurrency primitives — is the plan aligned with the research decision? [Conflict, plan.md §Principle IV vs research.md §R4]
- [ ] CHK006 - Does plan.md Principle IV evidence mention "CircuitBreaker on upstream" while no circuit breaker pattern appears in research.md, data-model.md state transitions, or any contract? Is this term defined or is it aspirational? [Ambiguity, plan.md §Principle IV]
- [ ] CHK007 - Does spec.md FR-009 say `compare_equipment` accepts "two or more equipment names" while compare-equipment.json uses `slugs` (URL-safe identifiers, not names)? Is the spec's terminology aligned with the contract's input parameter? [Conflict, Spec §FR-009 vs compare-equipment.json]
- [ ] CHK008 - Are sub-category slugs listed in data-model.md (e.g., `combat`, `aam`, `submarine`, `matsniper`) identical to the slugs in resources.json `equipment_categories[].sub_categories`? [Consistency, data-model.md §Enums vs resources.json]
- [ ] CHK009 - Does quickstart.md Section 7 "Available Tools" accurately reflect the required params and descriptions defined in each contract's `inputSchema.required`? [Consistency, quickstart.md §7 vs contracts/]
- [ ] CHK010 - Are resource URIs (`military://categories`, `military://equipment/{category}/sub-categories`) spelled identically in resources.json and quickstart.md Section 8? [Consistency, quickstart.md §8 vs resources.json]

## Schema / Data-Model ↔ Contract Fidelity

- [ ] CHK011 - Does data-model.md SearchQuery define a `sub_category` field? The search-equipment.json contract includes `sub_category` as an input param and spec.md FR-006 requires "filtering by category/sub-type", but SearchQuery in data-model.md only has: `category`, `query`, `country`, `decade`, `page`. [Gap, data-model.md §SearchQuery vs search-equipment.json]
- [ ] CHK012 - Is the `identify_from_image` response model (matches, identification_notes, search_strategy) defined in data-model.md? Currently data-model.md defines SearchResult and ComparisonResult but has no IdentificationResult model. [Gap, data-model.md §Response Models]
- [ ] CHK013 - Is an AirForce entity defined in data-model.md? The `air_forces` InventoryCategory is a valid enum value and appears in search-inventory.json, but data-model.md §Inventory only defines Navy, AirBase, NuclearArsenal, and RankStructure sub-types — no AirForce. [Gap, data-model.md §Inventory]
- [ ] CHK014 - Does search-inventory.json's `oneOf` output schema include a variant for AirForce inventory items? Currently it has Navy, AirBase, NuclearArsenal, and RankStructure — missing AirForce. [Gap, search-inventory.json §outputSchema]
- [ ] CHK015 - Are the `required` fields in search-inventory.json's Navy schema (`country`, `rank`, `navy_index`, `total_active`, `detail_url`) consistent with data-model.md's Navy entity where all 7 fields (`country`, `rank`, `navy_index`, `capital_ships`, `major_combatants`, `total_active`, `detail_url`) appear non-optional? [Consistency, data-model.md §Navy vs search-inventory.json]
- [ ] CHK016 - Are the `required` fields in search-inventory.json's NuclearArsenal schema (`country`, `total_warheads`) consistent with data-model.md where `deployed`, `stockpile`, and `retired` also appear as non-optional int fields? [Consistency, data-model.md §NuclearArsenal vs search-inventory.json]
- [ ] CHK017 - Does compare-equipment.json's Country output schema include a `pattern` constraint on `iso3` matching data-model.md's invariant ("3 lowercase alpha chars")? search-equipment.json has `"pattern": "^[a-z]{3}$"` on output Country but compare-equipment.json omits it. [Consistency, compare-equipment.json §outputSchema.items.country]
- [ ] CHK018 - Does the Equipment entity in compare-equipment.json's output include the same category-specific fields (manufacturer, produced, range_km, etc.) that search-equipment.json includes, given the description says "Full Equipment entity (same schema)"? [Consistency, compare-equipment.json §outputSchema]
- [ ] CHK019 - Is the `detail_url` format consistently specified across all contract output schemas? search-equipment.json uses `"format": "uri-reference"` but compare-equipment.json and search-inventory.json use plain `"type": "string"`. [Consistency]
- [ ] CHK020 - Are the error messages in search-equipment.json `errorCases` (e.g., "Invalid equipment category", "Country code must be 3 letters") word-for-word consistent with data-model.md's Validation Rules Summary table? [Consistency, data-model.md §Validation Rules vs search-equipment.json §errorCases]

## Spec FR Coverage in Contracts

- [ ] CHK021 - Is FR-001 (`search_equipment` with category + text query) traceable to search-equipment.json's inputSchema (`category` required, `query` optional)? [Traceability, Spec §FR-001]
- [ ] CHK022 - Is FR-002 (`search_inventory` with category + text query) traceable to search-inventory.json's inputSchema (`category` required, `query` optional)? [Traceability, Spec §FR-002]
- [ ] CHK023 - Is FR-003 (structured params: category, query, country, decade, page) fully represented in the tool input schemas? Does each applicable contract include all 5 specified params? [Traceability, Spec §FR-003]
- [ ] CHK024 - Is FR-004 (image input delegated to calling LLM) traceable to identify-from-image.json's design — accepting text descriptions rather than raw images? Does the contract's `designNotes.imageDelegation` align with spec.md's clarification? [Traceability, Spec §FR-004]
- [ ] CHK025 - Is FR-005 (consistent response format: name, country, category/type, summary) traceable to the output schemas of search-equipment.json and search-inventory.json? Are those minimum fields present in `required` output arrays? [Traceability, Spec §FR-005]
- [ ] CHK026 - Is FR-006 (filtering by country, sub-type, decade) traceable to search-equipment.json's `country`, `sub_category`, and `decade` input params AND to resources.json's `supported_filters` per category? [Traceability, Spec §FR-006]
- [ ] CHK027 - Is FR-007 (pagination with page number and total page count) traceable to the `page` input param and `page_info` output object across search-equipment.json and search-inventory.json? [Traceability, Spec §FR-007]
- [ ] CHK028 - Is FR-008 (graceful upstream error handling with exponential backoff) traceable to `errorCases` in search-equipment.json (429, 5xx scenarios) and research.md R4's backoff design? [Traceability, Spec §FR-008]
- [ ] CHK029 - Is FR-009 (`compare_equipment` with category + 2+ equipment) traceable to compare-equipment.json's `category` + `slugs` (minItems 2, maxItems 5) input? [Traceability, Spec §FR-009]
- [ ] CHK030 - Is FR-010 (`identify_from_image` accepting text description) traceable to identify-from-image.json's `equipment_name`/`characteristics` input params? [Traceability, Spec §FR-010]
- [ ] CHK031 - Is FR-011 (MCP resources for data categories) traceable to resources.json defining `military://categories` and `military://equipment/{category}/sub-categories`? [Traceability, Spec §FR-011]
- [ ] CHK032 - Is FR-012 (HTML parsing of table-based layout) covered by research.md R1's CSS selectors and plan.md's `scraper/parser.py` in project structure? (Infrastructure — no contract needed, but design must exist.) [Traceability, Spec §FR-012]
- [ ] CHK033 - Is FR-013 (site search forwarding via "Find a [X]" search boxes) traceable to search-equipment.json's `query` param description ("Maps to ?name= parameter on the site") and research.md's URL patterns (`"search": ".../?name={query}"`)? [Traceability, Spec §FR-013]
- [ ] CHK034 - Is FR-014 (local cache with 24h TTL, invalidation) covered by research.md R3's FileCache design and plan.md's `cache/store.py` in project structure? (Infrastructure — no contract.) [Traceability, Spec §FR-014]
- [ ] CHK035 - Is FR-015 (1 req/sec rate limit, serialized requests) covered by research.md R4's RateLimiter design and plan.md's `scraper/client.py` in project structure? (Infrastructure — no contract.) [Traceability, Spec §FR-015]

## Cross-Artifact Gap Detection

- [ ] CHK036 - Is the Vehicles category (`vehicles`) fully represented in research.md's Filter Availability table? Currently the table lists Aircraft, Missiles, Ships, Firearms, Navies — Vehicles is missing entirely. [Gap, research.md §R1 Filter Availability]
- [ ] CHK037 - Is the Vehicles category's decade filter support resolved? data-model.md EquipmentCategory shows "Has Decade Filter: TBD" for vehicles, but search-equipment.json's decade description says "Only valid for aircraft and ships" — implying vehicles does NOT support it. Is the TBD resolved? [Ambiguity, data-model.md §EquipmentCategory]
- [ ] CHK038 - Does plan.md Principle III original evidence ("All tools return SearchResult schema") account for `identify_from_image` returning a different schema (matches/identification_notes/search_strategy)? The Post-Design Re-Evaluation acknowledges this as "intentional divergence" but the original Principle III row is stale. [Consistency, plan.md §Principle III]
- [ ] CHK039 - Does resources.json list Vehicles sub-categories? All other equipment categories include `sub_categories` arrays, but the Vehicles entry has no `sub_categories` field. Is this intentional or a gap? [Gap, resources.json §equipment_categories]

## Notes

- Check items off as completed: `[x]`
- Items marked [Gap] indicate missing requirements that should be added
- Items marked [Conflict] indicate contradictions between artifacts that must be resolved
- Items marked [Ambiguity] indicate unclear specifications needing clarification
- Items marked [Consistency] indicate alignment checks across documents
- Items marked [Traceability] verify FR → contract mapping
