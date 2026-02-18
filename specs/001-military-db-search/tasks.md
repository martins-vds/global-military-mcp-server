# Tasks: Global Military Database Search MCP Server

**Input**: Design documents from `/specs/001-military-db-search/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included per Constitution Principle II (TDD — NON-NEGOTIABLE). Tests are written FIRST (Red), implementation follows (Green), then Refactor.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, and dependency configuration

- [x] T001 Create project directory structure per plan.md: src/, src/domain/, src/scraper/, src/cache/, src/tools/, tests/, tests/unit/, tests/integration/, tests/contract/, tests/fixtures/html/, .devcontainer/
- [x] T002 Create pyproject.toml with runtime dependencies (fastmcp<3, httpx>=0.27, beautifulsoup4>=4.12) and dev dependencies (pytest, pytest-asyncio, respx, inline-snapshot), project metadata, and scripts
- [x] T003 [P] Configure devcontainer with Python 3.13 base image in .devcontainer/devcontainer.json and .devcontainer/Dockerfile
- [x] T004 [P] Create __init__.py files for all packages (src/, src/domain/, src/scraper/, src/cache/, src/tools/) and configure pytest settings in pyproject.toml (asyncio_mode="auto", testpaths, coverage)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain primitives, infrastructure, and test harness that MUST complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create shared test fixtures (FastMCP Client factory via `Client(transport=mcp)`, temp cache directory with `tmp_path`, mock HTTP transport) in tests/conftest.py
- [x] T006 [P] Save representative HTML fixture samples for each category (aircraft, missiles, ships, firearms, vehicles, navies, air_bases, nuclear, ranks) from GlobalMilitary.net to tests/fixtures/html/{category}.html
- [x] T007 [P] Implement EquipmentCategory and InventoryCategory enums with URL segments, sub-category mappings, and filter availability flags in src/domain/enums.py with unit tests in tests/unit/test_enums.py
- [x] T008 [P] Implement Country, PageInfo, and Decade value objects with Pydantic validation and invariants (iso3=3 lowercase alpha, decade % 10 == 0, current_page <= total_pages) in src/domain/models.py with unit tests in tests/unit/test_models.py
- [x] T009 Implement Equipment entity with common fields (name, slug, country, category, sub_category, detail_url) and category-specific variants (Aircraft: manufacturer/produced/description/thumbnail_url, Missiles: range_km/max_speed, Ships: ship_type/year, Firearms: firearm_category) in src/domain/models.py
- [x] T010 Implement Inventory entity subtypes (Navy: rank/navy_index/capital_ships/major_combatants/total_active, AirBase: name/operating_country/host_country/year_established, NuclearArsenal: total_warheads/deployed/stockpile/retired, RankStructure: country/branch/ranks with RankEntry) in src/domain/models.py
- [x] T011 Implement SearchQuery (category + query/country/sub_category/decade/page), SearchResult (items/total_count/page_info/query_notes/category/filters_applied), ComparisonResult (items/category/shared_fields/comparison_notes), and IdentificationResult (matches with IdentificationMatch[equipment+match_reason], identification_notes, search_strategy) request/response models in src/domain/models.py
- [x] T012 [P] Implement FileCache with SHA-256 key hashing, JSON storage, configurable TTL (default 24h), atomic POSIX rename writes, lazy TTL eviction on get(), delete(), and clear() in src/cache/store.py with unit tests in tests/unit/test_cache.py
- [x] T013 [P] Implement RateLimiter with asyncio.Lock, 1 req/sec min_interval enforcement, exponential backoff (base=2.0, max_retries=5), and timestamp tracking in src/scraper/client.py with unit tests in tests/unit/test_client.py
- [x] T013b [P] Implement CircuitBreaker (closed→open→half-open states, consecutive failure counter, configurable failure_threshold=5, recovery_timeout=60s) in src/scraper/client.py — opens circuit after N consecutive upstream failures, returns ToolError immediately while open, allows one probe request in half-open state. Unit tests in tests/unit/test_client.py
- [x] T014 [P] Implement URL builder for all GlobalMilitary.net patterns (list, search by name, paginate, filter_category, filter_country, filter_decade, detail, global_search) per research.md R1 in src/scraper/urls.py with unit tests in tests/unit/test_urls.py
- [x] T015 Implement FastMCP server skeleton with @lifespan (create/teardown httpx.AsyncClient + FileCache + RateLimiter + CircuitBreaker), Depends() helpers for dependency injection, and READ_ONLY_ANNOTATIONS constant in src/server.py
- [x] T016 [P] Integration test for FileCache filesystem operations (atomic write safety, TTL expiry with time mocking, concurrent get/set, clear cleanup) in tests/integration/test_cache_fs.py

**Checkpoint**: Foundation ready — domain models defined, cache operational, rate limiter enforcing 1 req/sec, URL patterns validated, server skeleton running. User story implementation can now begin.

---

## Phase 3: User Story 1 — Search Equipment by Text Query (Priority: P1) 🎯 MVP

**Goal**: Expose `search_equipment` MCP tool that accepts category + structured params, scrapes GlobalMilitary.net equipment pages, parses HTML tables, caches results, and returns structured Equipment entities with pagination

**Independent Test**: Invoke `search_equipment(category="aircraft", query="F-35")` → verify structured results containing F-35 Lightning II with country (USA), sub_category (Combat), manufacturer (Lockheed Martin), produced count, and description

**Covers**: FR-001, FR-003, FR-005, FR-006, FR-007, FR-008, FR-012, FR-013, FR-014, FR-015

### Tests for User Story 1 ⚠️

> **Write these tests FIRST — ensure they FAIL before implementation (Red phase)**

- [x] T017 [P] [US1] Contract test for search_equipment tool schema (input params: category/query/country/sub_category/decade/page, output shape: items/total_count/page_info, READ_ONLY annotations, 5 error cases) against contracts/search-equipment.json in tests/contract/test_tools_schema.py
- [x] T018 [P] [US1] Unit tests for equipment HTML parser — parse aircraft (6 cols), missiles (5 cols), ships (4 cols), firearms (3 cols) tables from fixture HTML, verify Equipment entity extraction and pagination detection in tests/unit/test_parser.py
- [x] T019 [P] [US1] Unit tests for SearchService equipment orchestration (cache hit returns cached, cache miss triggers fetch+parse+cache, pagination forwarding, country/decade/sub_category filtering, ToolError on invalid category) in tests/unit/test_services.py
- [x] T020 [P] [US1] Integration test for equipment scraper — full pipeline with mocked HTTP responses via respx (success, 429 retry with backoff, 5xx error, empty results, paginated response) in tests/integration/test_scraper.py

### Implementation for User Story 1

- [x] T021 [US1] Implement equipment HTML parser — extract Equipment entities from all `table.table` elements using CSS selectors (rows: `table.table > tbody > tr`, detail_link: `td:nth-child(2) > a`), handle per-category column layout, detect pagination from `ul.pagination` in src/scraper/parser.py
- [x] T022 [US1] Implement SearchService with equipment search orchestration (build URL via urls.py → check FileCache → check CircuitBreaker → acquire RateLimiter → httpx.get() → parse HTML → cache SearchResult → return; record success/failure in CircuitBreaker) in src/domain/services.py
- [x] T023 [US1] Implement search_equipment tool handler with @mcp.tool(annotations=READ_ONLY_ANNOTATIONS) decorator, parameter validation (category enum, optional query/country/sub_category/decade/page), ToolError mapping for domain errors, and register on server in src/tools/equipment.py

**Checkpoint**: `search_equipment` tool functional — `fastmcp run src/server.py` → tool discoverable via MCP, returns structured equipment data with pagination. **MVP deliverable.**

---

## Phase 4: User Story 2 — Browse Inventory Data (Priority: P2)

**Goal**: Expose `search_inventory` MCP tool for querying country-level military force data (navies fleet composition, air base locations, nuclear arsenals, rank structures, air forces)

**Independent Test**: Invoke `search_inventory(category="navies")` → verify structured results with Navy entities containing rank, country, navy_index, capital_ships, major_combatants, total_active

**Covers**: FR-002, FR-003, FR-005, FR-007

### Tests for User Story 2 ⚠️

> **Write these tests FIRST — ensure they FAIL before implementation (Red phase)**

- [x] T024 [P] [US2] Contract test for search_inventory tool schema (input params: category/query/country/page, output shape: oneOf Navy/AirBase/NuclearArsenal/RankStructure items, 3 error cases) against contracts/search-inventory.json in tests/contract/test_tools_schema.py
- [x] T025 [P] [US2] Unit tests for inventory HTML parser — parse navies (6 cols, single page, no pagination), air_bases (name/country/year), nuclear (warhead counts), ranks (name/NATO code/grade) tables from fixture HTML in tests/unit/test_parser.py
- [x] T026 [P] [US2] Integration test for inventory scraper — full pipeline with mocked HTTP (navies single-page, air_bases paginated, nuclear data, ranks by country) via respx in tests/integration/test_scraper.py

### Implementation for User Story 2

- [x] T027 [US2] Extend HTML parser for inventory categories — navies (6 cols, no pagination), air_bases (name/operating_country/host_country/year), nuclear (warhead breakdown), ranks (hierarchical name/NATO code/grade) in src/scraper/parser.py
- [x] T028 [US2] Extend SearchService for inventory search — reuse cache/rate-limiter pipeline, handle navies single-page case (no pagination), build inventory-specific URLs in src/domain/services.py
- [x] T029 [US2] Implement search_inventory tool handler with @mcp.tool(annotations=READ_ONLY_ANNOTATIONS) decorator, category enum validation (InventoryCategory), ToolError mapping, and register on server in src/tools/inventory.py

**Checkpoint**: `search_inventory` tool functional — both `search_equipment` and `search_inventory` independently testable and working.

---

## Phase 5: User Story 3 — Search Equipment by Image (Priority: P3)

**Goal**: Expose `identify_from_image` MCP tool that accepts equipment description text (from LLM vision) or category + characteristics, and searches the equipment database for matching entries

**Independent Test**: Invoke `identify_from_image(equipment_name="F-22 Raptor")` → verify response includes matches from aircraft category with match_reason explaining how identification was made

**Covers**: FR-004, FR-010

**Depends on**: User Story 1 (reuses equipment search pipeline and parser)

### Tests for User Story 3 ⚠️

> **Write these tests FIRST — ensure they FAIL before implementation (Red phase)**

- [x] T030 [P] [US3] Contract test for identify_from_image tool schema (input: anyOf equipment_name OR category+characteristics, output: matches with match_reason/search_strategy) against contracts/identify-from-image.json in tests/contract/test_tools_schema.py
- [x] T031 [P] [US3] Unit tests for identification matching logic (exact name match across categories, category+characteristics filtered search, no match returns empty with suggestion, ambiguous input searches multiple categories) in tests/unit/test_services.py

### Implementation for User Story 3

- [x] T032 [US3] Implement identification matching logic — name-based search across all equipment categories, characteristic-based filtering within specified category, ranked results with confidence scoring and match_reason in src/domain/services.py
- [x] T033 [US3] Implement identify_from_image tool handler with @mcp.tool(annotations=READ_ONLY_ANNOTATIONS) — accept equipment_name (str|null) OR category+characteristics, return matches with match_reason and search_strategy, register on server in src/tools/equipment.py

**Checkpoint**: `identify_from_image` tool functional — US1, US2, US3 all independently testable.

---

## Phase 6: User Story 4 — Compare Equipment Side-by-Side (Priority: P4)

**Goal**: Expose `compare_equipment` MCP tool that fetches 2-5 equipment items from the same category and presents them in a structured comparison with shared/differing fields

**Independent Test**: Invoke `compare_equipment(category="missiles", slugs=["aim-120-amraam", "aim-9-sidewinder"])` → verify ComparisonResult with both items, shared_fields list, and comparison_notes

**Covers**: FR-009

**Depends on**: User Story 1 (reuses equipment fetch-by-slug and parser)

### Tests for User Story 4 ⚠️

> **Write these tests FIRST — ensure they FAIL before implementation (Red phase)**

- [x] T034 [P] [US4] Contract test for compare_equipment tool schema (input: category + slugs[2-5], output: ComparisonResult with items/shared_fields/comparison_notes, 5 error cases) against contracts/compare-equipment.json in tests/contract/test_tools_schema.py
- [x] T035 [P] [US4] Unit tests for ComparisonService (compare 2 items, compare 5 items, reject cross-category comparison, reject <2 or >5 items, detect shared specification fields, handle missing item slug) in tests/unit/test_services.py

### Implementation for User Story 4

- [x] T036 [US4] Implement ComparisonService — fetch N equipment items by slug via SearchService, validate same category, detect shared specification fields across items, build ComparisonResult in src/domain/services.py
- [x] T037 [US4] Implement compare_equipment tool handler with @mcp.tool(annotations=READ_ONLY_ANNOTATIONS) — validate 2-5 slugs, same EquipmentCategory, ToolError for cross-category/invalid count, register on server in src/tools/equipment.py

**Checkpoint**: All 4 MCP tools functional — full feature set implemented. Every user story independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: MCP resources, observability, documentation, and end-to-end validation

- [x] T038 [P] Implement `military://categories` MCP resource listing all equipment and inventory categories with supported filters (category/decade/country/name_search flags per section) in src/server.py
- [x] T039 [P] Implement `military://equipment/{category}/sub-categories` MCP resource returning sub-category slugs and labels for a given equipment category in src/server.py
- [x] T040 [P] Contract tests for MCP resources (list resources, read military://categories, read sub-categories for each equipment category) against contracts/resources.json in tests/contract/test_resources.py
- [x] T041 Add structured logging with FastMCP Context across all tools — log tool name, parameters, timestamp, cache hit/miss, upstream response time, result count in src/tools/equipment.py, src/tools/inventory.py, and src/domain/services.py
- [x] T042 Run quickstart.md validation — end-to-end smoke test following specs/001-military-db-search/quickstart.md (devcontainer setup, server start, tool invocation via FastMCP Client, all 4 tools + 2 resources)
- [x] T043 Create README.md with project overview, architecture diagram, setup instructions, tool reference table (4 tools), resource reference (2 URIs), and development guide
- [x] T044 Performance smoke test — measure p95 response times for cached (<200ms target) and uncached (<3s target) search_equipment queries, verify rate limiter serializes concurrent requests, confirm circuit breaker opens after 5 failures. Document results in test output. Located in tests/integration/test_performance.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **User Story 1 (Phase 3)**: Depends on Foundational — no other story dependencies
- **User Story 2 (Phase 4)**: Depends on Foundational — no dependency on US1 (independent domain)
- **User Story 3 (Phase 5)**: Depends on Foundational + **US1** (reuses equipment search pipeline)
- **User Story 4 (Phase 6)**: Depends on Foundational + **US1** (reuses equipment fetch-by-slug)
- **Polish (Phase 7)**: Depends on US1 + US2 minimum (resources reference all categories)

### User Story Dependency Graph

```
Phase 1 (Setup)
  └──▶ Phase 2 (Foundational) ──BLOCKS──┐
                                         ├──▶ Phase 3 (US1 - P1 MVP) ──┬──▶ Phase 5 (US3 - P3)
                                         │                              ├──▶ Phase 6 (US4 - P4)
                                         │                              └──▶ Phase 7 (Polish)
                                         └──▶ Phase 4 (US2 - P2) ──────────▶ Phase 7 (Polish)
```

### Within Each User Story (TDD Order)

1. Contract tests MUST be written and FAIL before implementation
2. Unit tests MUST be written and FAIL before implementation
3. Integration tests MUST be written and FAIL before implementation
4. Implementation makes tests pass (Green)
5. Refactor while keeping tests green
6. Story complete and validated before moving to next priority

### Parallel Opportunities

| Phase       | Parallel Tasks                           | Reason                     |
| ----------- | ---------------------------------------- | -------------------------- |
| Phase 1     | T003, T004                               | Different files            |
| Phase 2     | T006, T007, T008, T012, T013, T014, T016 | Independent infrastructure |
| Phase 3 (R) | T017, T018, T019, T020                   | Different test files       |
| Phase 4 (R) | T024, T025, T026                         | Different test files       |
| Phase 5 (R) | T030, T031                               | Different test files       |
| Phase 6 (R) | T034, T035                               | Different test files       |
| Phase 7     | T038, T039, T040                         | Independent features       |

---

## Parallel Example: User Story 1

```bash
# Red phase — launch all US1 tests in parallel (all should FAIL):
T017: Contract test for search_equipment schema    → tests/contract/test_tools_schema.py
T018: Unit tests for equipment HTML parser         → tests/unit/test_parser.py
T019: Unit tests for SearchService                 → tests/unit/test_services.py
T020: Integration test for equipment scraper       → tests/integration/test_scraper.py

# Green phase — sequential implementation (makes tests pass):
T021: Equipment HTML parser                        → src/scraper/parser.py
T022: SearchService orchestration                  → src/domain/services.py
T023: search_equipment tool handler                → src/tools/equipment.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T016) — **CRITICAL, blocks all stories**
3. Complete Phase 3: User Story 1 (T017–T023)
4. **STOP and VALIDATE**: Test `search_equipment` independently with FastMCP Client
5. Deploy/demo if ready — single tool delivers core equipment search capability

### Incremental Delivery

| Increment  | Tasks     | Deliverable                                | Cumulative Tools |
| ---------- | --------- | ------------------------------------------ | ---------------- |
| Foundation | T001–T016 | Infrastructure ready, no user-facing tools | 0                |
| **MVP**    | T017–T023 | Equipment text search                      | 1                |
| +US2       | T024–T029 | Inventory browsing                         | 2                |
| +US3       | T030–T033 | Image identification                       | 3                |
| +US4       | T034–T037 | Equipment comparison                       | 4                |
| Polish     | T038–T043 | Resources, logging, docs                   | 4 + 2 resources  |

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

- **Developer A**: US1 (T017–T023) → US3 (T030–T033, depends on US1)
- **Developer B**: US2 (T024–T029) → US4 (T034–T037, waits for US1 or starts tests early)

---

## FR → Task Traceability

| FR     | Description                    | Tasks                     |
| ------ | ------------------------------ | ------------------------- |
| FR-001 | search_equipment tool          | T017–T023                 |
| FR-002 | search_inventory tool          | T024–T029                 |
| FR-003 | Structured parameters          | T011, T017, T024          |
| FR-004 | Image input delegation         | T030–T033                 |
| FR-005 | Consistent response format     | T011 (SearchResult model) |
| FR-006 | Filtering (country/decade/sub) | T014, T021, T022          |
| FR-007 | Pagination                     | T008, T014, T021          |
| FR-008 | Upstream error handling        | T013, T013b, T020, T022   |
| FR-009 | compare_equipment tool         | T034–T037                 |
| FR-010 | identify_from_image tool       | T030–T033                 |
| FR-011 | MCP resources                  | T038–T040                 |
| FR-012 | HTML parsing                   | T018, T021, T025, T027    |
| FR-013 | Search forwarding (?name=)     | T014, T022                |
| FR-014 | Cache with TTL                 | T012, T016                |
| FR-015 | Rate limiting (1 req/sec)      | T013                      |

---

## Notes

- TDD is NON-NEGOTIABLE (Constitution Principle II) — all test tasks produce failing tests BEFORE implementation
- [P] tasks = different files, no dependencies on incomplete tasks
- All tools use `READ_ONLY_ANNOTATIONS = {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True}`
- Error handling uses FastMCP `ToolError` for user-facing errors throughout
- Cache key should incorporate: category + query + country + sub_category + decade + page for uniqueness
- Rate limiter serializes ALL upstream requests (equipment + inventory) through single asyncio.Lock
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Known consistency issues (from checklists/consistency.md) to resolve during implementation:
  - CHK011: Add `sub_category` field to SearchQuery model ✅ fixed (added to spec.md FR-003 + data-model.md SearchQuery)
  - CHK012: IdentificationResult model ✅ fixed (added to data-model.md + T011 updated)
  - CHK005/006: Use `asyncio.Lock` (not Semaphore) per research.md ✅ fixed; CircuitBreaker added as T013b ✅ fixed
  - CHK013/014: AirForce entity added to data-model.md ✅ fixed (tentative fields, confirm during T006)
  - CHK036/037: Confirm Vehicles filter availability and decade filter during HTML fixture capture (T006)
