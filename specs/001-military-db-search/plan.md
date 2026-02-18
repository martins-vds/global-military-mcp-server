# Implementation Plan: Global Military Database Search MCP Server

**Branch**: `001-military-db-search` | **Date**: 2026-02-17 | **Spec**: [spec.md](specs/001-military-db-search/spec.md)
**Input**: Feature specification from `/specs/001-military-db-search/spec.md`

## Summary

Build an MCP server that exposes tools for searching military equipment and inventory data from GlobalMilitary.net. The server scrapes the website, caches results locally with a 24-hour TTL, and exposes 4 MCP tools (`search_equipment`, `search_inventory`, `compare_equipment`, `identify_from_image`) plus MCP resources for browsing data categories. Built with Python 3.13 and the FastMCP library, using structured parameters (no NLP), delegating image recognition to the calling LLM, and enforcing a 1 req/sec rate limit to the upstream site.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: FastMCP v2 (stable, `fastmcp<3`), httpx (async HTTP client), beautifulsoup4 (HTML parsing), pydantic (data validation, bundled with FastMCP)  
**Storage**: Local file-based cache (JSON files with TTL metadata, default 24h). No database required.  
**Testing**: pytest + pytest-asyncio, FastMCP Client test fixtures (`Client(transport=mcp)`), inline-snapshot for schema assertions  
**Target Platform**: Linux server (devcontainer), stdio transport for local dev, HTTP transport for remote  
**Project Type**: single  
**Performance Goals**: <3s p95 for first (uncached) query including upstream fetch; <200ms p95 for cached responses (see Complexity Tracking for Principle IV I/O budget justification)  
**Constraints**: 1 req/sec max to GlobalMilitary.net, exponential backoff on 429/5xx, 24h default cache TTL (configurable)  
**Scale/Scope**: 10 data categories (~1600+ total entries), single-server deployment, concurrent clients serialized through rate limiter

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Domain-Driven Design

| Requirement                               | Status | Evidence                                                                                                                                                                                                                                  |
| ----------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bounded contexts with explicit boundaries | ✅ PASS | 4 bounded contexts identified: `domain` (entities, value objects), `scraper` (HTTP fetching, HTML parsing), `cache` (TTL storage, eviction), `mcp_tools` (FastMCP tool handlers). Cross-context communication via domain interfaces only. |
| Ubiquitous language mirrors domain        | ✅ PASS | Entities: Equipment, Inventory, SearchQuery, SearchResult, Comparison — match spec and domain expert terminology. No generic names.                                                                                                       |
| Aggregates enforce invariants             | ✅ PASS | Equipment and Inventory are aggregate roots. SearchResult is a read-only projection.                                                                                                                                                      |
| Value objects for identity-less concepts  | ✅ PASS | EquipmentCategory (enum), InventoryCategory (enum), Country, Decade, PageInfo — all immutable value objects.                                                                                                                              |
| Infrastructure separation                 | ✅ PASS | Domain layer has zero imports from httpx, beautifulsoup4, FastMCP, or filesystem. Dependency arrow points inward.                                                                                                                         |

### Principle II — Test-Driven Development (NON-NEGOTIABLE)

| Requirement                             | Status | Evidence                                                                                                       |
| --------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------- |
| Red-Green-Refactor cycle                | ✅ PASS | Task breakdown will enforce test-first for every feature slice.                                                |
| Test-first contract                     | ✅ PASS | Contract tests for all 4 MCP tools + resources defined before implementation.                                  |
| Unit tests: 100% domain branch coverage | ✅ PASS | Domain models, parsers, cache logic all unit-testable with no external dependencies.                           |
| Integration tests: boundary crossings   | ✅ PASS | Scraper ↔ httpx, cache ↔ filesystem, MCP tools ↔ FastMCP server — all integration tested with mocked upstream. |
| Contract tests: MCP compliance          | ✅ PASS | FastMCP Client fixtures verify tool schemas, parameter validation, and response formats.                       |
| Test independence                       | ✅ PASS | No shared mutable state; each test gets fresh server instance via pytest fixtures.                             |

### Principle III — UX Consistency

| Requirement                              | Status | Evidence                                                                                                                                             |
| ---------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Uniform response structure               | ✅ PASS | All tools return `SearchResult` schema: items list, total_count, page, total_pages, query_notes.                                                     |
| Naming conventions (snake_case)          | ✅ PASS | Tools: `search_equipment`, `search_inventory`, `compare_equipment`, `identify_from_image`. Params: `category`, `query`, `country`, `decade`, `page`. |
| Input validation with descriptive errors | ✅ PASS | Pydantic + FastMCP auto-validation. Custom ToolError for domain-specific validation (e.g., invalid category).                                        |
| Progressive disclosure                   | ✅ PASS | Only `category` required; `query`, `country`, `decade`, `page` all optional with sensible defaults.                                                  |
| Documentation parity                     | ✅ PASS | Tool descriptions generated from docstrings, updated in same PR as behavior changes.                                                                 |

### Principle IV — Performance & Reliability

| Requirement           | Status     | Evidence                                                                                                                                                     |
| --------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Response time budgets | ⚠️ ADJUSTED | Cached: <200ms p95. Uncached: <3s p95 (see Complexity Tracking — 1 req/sec rate limit makes <2s impossible for cache-miss). Comparison (2-5 items): <5s p95. |
| Resource efficiency   | ✅ PASS     | Cache has configurable max size. Rate limiter bounds concurrent requests to 1/sec.                                                                           |
| Graceful degradation  | ✅ PASS     | CircuitBreaker on upstream (consecutive-failure counter in scraper client: closed→open→half-open). ToolError with descriptive message on failure. No hangs.  |
| Concurrency safety    | ✅ PASS     | asyncio.Lock for rate limiting (per research.md R4). Cache reads/writes via atomic file operations.                                                          |
| Observability         | ✅ PASS     | Structured logging via FastMCP Context. Correlation IDs from MCP request context.                                                                            |

### Principle V — Security & Access Control (NON-NEGOTIABLE)

| Requirement                    | Status     | Evidence                                                                                                                                                      |
| ------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authentication & Authorization | ⚠️ DEFERRED | Initial release targets local stdio transport (no network exposure). Auth will be enforced when HTTP transport is enabled. Documented as Phase 2 enhancement. |
| Principle of Least Privilege   | ✅ PASS     | Tools return only requested data. No over-fetching. readOnlyHint=True on all tools.                                                                           |
| Audit Trail                    | ✅ PASS     | Structured logging for every tool invocation: tool name, parameters, timestamp, outcome.                                                                      |
| Data Classification            | ✅ PASS     | All data sourced from public website. No classification levels required for public domain data.                                                               |
| Defense in Depth               | ✅ PASS     | Input validation at transport (FastMCP), application (Pydantic), and domain layers.                                                                           |
| Secure Defaults                | ✅ PASS     | Rate limiting on by default. Cache isolation per-instance. No secrets in initial scope (public website scraping).                                             |
| Secret Management              | ✅ PASS     | No secrets required — public website, no API keys. Configuration via environment variables for future extensibility.                                          |

**Gate Result: ✅ PASS** — All principles satisfied. Principle V Auth deferred with justification (stdio-only initial deployment).

### Post-Design Re-Evaluation (Phase 1 Complete)

| Principle            | Status | Post-Design Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| -------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I — DDD              | ✅ PASS | data-model.md defines clean aggregates (Equipment, Inventory), value objects (Country, PageInfo, Decade), and enums. Contracts reference domain types only — no infrastructure leakage. 4 bounded contexts preserved in contracts.                                                                                                                                                                                                                                                |
| II — TDD             | ✅ PASS | Contract JSON schemas in contracts/ define the exact tool input/output schemas that contract tests will validate. Error cases documented per tool for negative test coverage.                                                                                                                                                                                                                                                                                                     |
| III — UX Consistency | ✅ PASS | `search_equipment` and `search_inventory` share identical response shape (items, total_count, page_info, query_notes, category, filters_applied). `compare_equipment` uses ComparisonResult (items, shared_fields, comparison_notes). `identify_from_image` uses a distinct identification shape (matches with match_reason) — intentional divergence for a different operation type. All tools use snake_case naming, descriptive ToolError messages, and READ_ONLY_ANNOTATIONS. |
| IV — Performance     | ✅ PASS | No new performance concerns. Cache and rate limiter designs from research.md integrated. Resource endpoints serve static config (no scraping).                                                                                                                                                                                                                                                                                                                                    |
| V — Security         | ✅ PASS | Auth still deferred (stdio-only). All tool inputs validated via JSON Schema constraints (pattern, enum, min/max). readOnlyHint=true on all 4 tools. No secrets in scope.                                                                                                                                                                                                                                                                                                          |

**Post-Design Gate: ✅ PASS** — No new violations introduced by Phase 1 design artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/001-military-db-search/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── server.py                # FastMCP server instantiation and tool registration
├── domain/
│   ├── __init__.py
│   ├── models.py            # Equipment, Inventory, SearchQuery, SearchResult, Comparison
│   ├── enums.py             # EquipmentCategory, InventoryCategory
│   └── services.py          # SearchService, ComparisonService (orchestration)
├── scraper/
│   ├── __init__.py
│   ├── client.py            # HTTP client wrapper (httpx) with rate limiting
│   ├── parser.py            # BeautifulSoup HTML parsing per category
│   └── urls.py              # URL construction for GlobalMilitary.net
├── cache/
│   ├── __init__.py
│   └── store.py             # TTL-based file cache (read, write, invalidate, evict)
└── tools/
    ├── __init__.py
    ├── equipment.py         # search_equipment, compare_equipment, identify_from_image tools
    └── inventory.py         # search_inventory tool

tests/
├── conftest.py              # Shared fixtures (FastMCP Client, mock scraper, temp cache)
├── unit/
│   ├── test_models.py       # Domain model validation, invariants
│   ├── test_enums.py        # Category enum coverage
│   ├── test_parser.py       # HTML parsing with fixture HTML files
│   ├── test_cache.py        # Cache TTL, eviction, invalidation
│   └── test_services.py     # Search and comparison orchestration
├── integration/
│   ├── test_scraper.py      # HTTP client with mocked responses (respx)
│   └── test_cache_fs.py     # Cache with real filesystem (tmp_path)
├── contract/
│   ├── test_tools_schema.py # MCP tool schema validation via FastMCP Client
│   └── test_resources.py    # MCP resource listing and read validation
└── fixtures/
    └── html/                # Saved HTML samples from GlobalMilitary.net categories

.devcontainer/
├── devcontainer.json        # Devcontainer configuration
└── Dockerfile               # Python 3.13 base image

pyproject.toml               # Project metadata, dependencies, pytest config
```

**Structure Decision**: Single project layout selected. This is a standalone MCP server with no frontend/backend split. The 4 bounded contexts (domain, scraper, cache, tools) are organized as Python packages under `src/`. Tests mirror the source structure with unit/integration/contract separation per Constitution Principle II.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation                       | Why Needed                                                                                                                                                                                                                                                                                              | Simpler Alternative Rejected Because                                                                                                                                                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Principle V Auth deferred       | Initial release uses stdio transport only (local process communication, no network exposure). Auth has zero security benefit for stdio.                                                                                                                                                                 | Implementing full RBAC for stdio-only adds complexity without security gain. Will be implemented when HTTP transport is enabled.                                                                                                                         |
| Principle IV I/O budget >2000ms | Constitution mandates <2000ms p95 for external I/O. Uncached queries require: rate limiter wait (up to 1000ms) + upstream HTTP fetch (~500-1500ms) + HTML parse (~50ms). Total realistic floor is ~1500-2500ms. Strict 1 req/sec rate limit (FR-015) makes sub-2s p95 impossible under concurrent load. | Removing rate limit would meet 2s but violates FR-015 and risks upstream blocking. Cache-first architecture ensures >95% of requests hit cache (<200ms). Only first-touch cold queries exceed 2s. Budget set to <3s p95 for uncached, <200ms for cached. |
