# Feature Specification: Global Military Database Search MCP Server

**Feature Branch**: `001-military-db-search`  
**Created**: 2026-02-17  
**Status**: Draft  
**Input**: User description: "build an mcp server that can interact with the website https://www.globalmilitary.net/. This is a Global Military Forces Database & Intelligence Platform. The server must be able to search equipments (air craft, missiles, firearms, vehicles, ships and aircraft) and inventories (air forces, air bases, navies, ranks, nuclear). search queries will be provided to this mcp server in text or image format"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search Equipment by Text Query (Priority: P1)

A user (human or AI agent) sends a plain-text query describing military equipment they want to find — for example, "stealth fighter jets made by China" or "anti-tank missiles with range over 5km." The MCP server interprets the query, searches the appropriate equipment category (aircraft, missiles, firearms, vehicles, or ships) on GlobalMilitary.net, and returns structured results including the equipment name, country of origin, category/type, and key specifications.

**Why this priority**: Text-based equipment search is the core value proposition of the server. It covers the largest surface area of the database (450+ aircraft, 220+ missiles, 300+ firearms, 120+ vehicles, 470+ ships) and represents the most common use case. Without this, the server provides no value.

**Independent Test**: Can be fully tested by invoking `search_equipment(category="missiles", sub_category="cruise", country="rus")` and verifying structured results are returned containing matching entries (e.g., 3M14 Kalibr). Delivers immediate research value.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** a user invokes `search_equipment(category="aircraft", query="F-35")`, **Then** the server returns structured results containing the F-35 Lightning II with its country, sub_category (Combat), manufacturer, production count, and description.
2. **Given** the MCP server is running, **When** a user invokes `search_equipment(category="missiles", sub_category="ashm")`, **Then** the server returns all missiles in the Anti-Ship sub-category (e.g., 3M22 Zircon, AGM-158C LRASM) with range and max speed fields.
3. **Given** the MCP server is running, **When** a user invokes `search_equipment(category="vehicles", country="deu")`, **Then** the server returns vehicles filtered by country Germany, including Leopard 1, Leopard 2, etc.
4. **Given** the MCP server is running, **When** a user invokes `search_equipment(category="firearms", sub_category="mg")`, **Then** the server returns firearms in the Machine Gun sub-category with country and firearm_category fields.

---

### User Story 2 - Browse Inventory Data (Priority: P2)

A user queries inventory-level data: air force rankings, navy fleet compositions, air base locations, military rank structures, or nuclear arsenal information. For example, "What ships does the Indian Navy operate?" or "List all US air bases in Japan." The server retrieves the relevant inventory page from GlobalMilitary.net and returns structured data.

**Why this priority**: Inventory data provides strategic-level intelligence that complements equipment-level searches. It answers "who has what" and "where is it" questions that are essential for defense analysis. This is the second most requested type of query after equipment search.

**Independent Test**: Can be tested by querying "Indian Navy fleet" and verifying the response includes the navy name, score/ranking, and ship counts (e.g., Indian Navy: score 51.5, 2 carriers, 41 submarines, 290 other vessels). Delivers standalone strategic intelligence.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** a user queries "top 5 navies in the world", **Then** the server returns the top 5 entries from the navies inventory, ranked by score, with carrier count, submarine count, and total vessel count.
2. **Given** the MCP server is running, **When** a user queries "US air bases in Italy", **Then** the server returns air bases located in Italy operated by the United States (e.g., Aviano Air Base).
3. **Given** the MCP server is running, **When** a user queries "military ranks in France", **Then** the server returns the rank structure for France, organized by enlisted and officer categories with rank names and NATO equivalents.
4. **Given** the MCP server is running, **When** a user queries "nuclear arsenals", **Then** the server returns the nuclear arsenal data for all nine nuclear-armed states including total warheads, deployed count, stockpile count, and delivery methods (if available on source page).

---

### User Story 3 - Search Equipment by Image (Priority: P3)

A user provides an image (photograph, screenshot, diagram, or insignia) of military equipment and asks the server to identify it. The server analyzes the image to extract visual features (silhouette, markings, configuration), matches them against known equipment in the database, and returns the most likely identification along with the equipment's full details from GlobalMilitary.net.

**Why this priority**: Image-based identification is a powerful differentiator but depends on visual recognition capabilities. It builds on top of the text search infrastructure (Story 1) since once the equipment is identified from the image, the same search and retrieval pipeline is used. It is a more advanced feature with higher complexity.

**Independent Test**: Can be tested by providing an image of a well-known aircraft (e.g., F-22 Raptor) and verifying the server identifies it correctly and returns the matching equipment record from the database. Delivers unique identification capability.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** a user provides an image of an aircraft, **Then** the server identifies the aircraft model and returns its full details from the aircraft database including specifications, manufacturer, and operators.
2. **Given** the MCP server is running, **When** a user provides a blurry or low-quality image, **Then** the server returns a ranked list of possible matches with match reasons explaining why each result was identified as a potential match, rather than a single definitive answer.
3. **Given** the MCP server is running, **When** a user provides an image that does not match any military equipment in the database, **Then** the server returns a clear message indicating no match was found, along with its best guess of what the image depicts.

---

### User Story 4 - Compare Equipment Side-by-Side (Priority: P4)

A user asks the server to compare two or more pieces of equipment — for example, "Compare the F-35 vs Su-57" or "Compare Leopard 2 vs M1 Abrams vs T-14 Armata." The server fetches detailed specifications for each item and presents them in a structured comparison format highlighting differences and similarities.

**Why this priority**: The website already offers comparison tools (aircraft comparison tool noted on the site). This extends that capability through MCP, enabling agents to programmatically compare equipment. It depends on equipment search (Story 1) being functional first.

**Independent Test**: Can be tested by requesting "Compare AIM-120 AMRAAM vs AIM-9 Sidewinder" and verifying the response includes both missiles' specifications in a comparison format with range, speed, category, and country of origin.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** a user requests a comparison of "F-22 vs J-20", **Then** the server returns both aircraft's specifications side-by-side including category, country, manufacturer, production count, and description.
2. **Given** the MCP server is running, **When** a user requests a comparison of items from different categories (e.g., a missile vs a ship), **Then** the server returns an error message explaining that comparisons are only meaningful within the same equipment category.

---

### Edge Cases

- What happens when the query matches no results in any category? The server returns an empty result set with a message suggesting alternative search terms or broader category selections.
- What happens when GlobalMilitary.net is unreachable or returns errors? The server returns a descriptive error indicating the upstream data source is unavailable and suggests retrying later.
- What happens when a query is ambiguous across categories (e.g., "Tomahawk" could be a missile or a search term for other items)? The server searches across all relevant categories and returns results grouped by category.
- What happens when the user searches in a language other than English? The server accepts queries in any language but notes that the database content is in English; results are returned in English.
- What happens when paginated data is needed (e.g., "list all aircraft")? The server supports pagination parameters allowing callers to request specific pages of results.
- What happens when an image is provided but is not a photograph of equipment (e.g., a map, a chart, or random text)? The server returns a clear message that no military equipment could be identified in the image.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a `search_equipment` MCP tool that accepts a category parameter (aircraft, missiles, firearms, vehicles, ships) and a text query, returning matching equipment from the specified category.
- **FR-002**: System MUST expose a `search_inventory` MCP tool that accepts a category parameter (air_forces, air_bases, navies, ranks, nuclear) and a text query, returning matching inventory data from the specified category.
- **FR-003**: System MUST accept structured parameters for search tools: `category` (required enum), `query` (optional text for name/keyword matching), `country` (optional country filter), `sub_category` (optional sub-type filter, e.g., 'combat' for aircraft, 'aam' for missiles), `decade` (optional era filter), and `page` (optional pagination). The server does NOT perform natural-language parsing — the calling MCP client/agent is responsible for decomposing user intent into these structured parameters.
- **FR-004**: System MUST accept image inputs via MCP's image content type. The server delegates visual recognition to the calling LLM/agent — it expects the client to describe the image and pass the description as a text query. The server then searches the database using that text description. The server itself does NOT call any external vision API.
- **FR-005**: System MUST return results in a consistent, structured format including at minimum: item name, country of origin, category/type, and a summary description.
- **FR-006**: System MUST support filtering results by country, category/sub-type, and decade/era where the source data provides these facets.
- **FR-007**: System MUST support pagination for result sets that exceed a single page, exposing page number and total page count to callers.
- **FR-008**: System MUST handle upstream errors from GlobalMilitary.net gracefully, returning descriptive error messages without crashing or hanging. On 429 (rate limited) or 5xx responses, the system MUST apply exponential backoff before retrying.
- **FR-009**: System MUST expose a `compare_equipment` MCP tool that accepts a category and two or more equipment slugs (URL-safe identifiers, e.g., "f-16-fighting-falcon") within that category, returning their specifications side-by-side.
- **FR-010**: System MUST expose an `identify_from_image` MCP tool that accepts a text description of an image (provided by the calling LLM's vision) and searches the equipment database for matches.
- **FR-011**: System MUST expose MCP resources for the GlobalMilitary.net data categories, allowing clients to browse available data domains.
- **FR-012**: System MUST parse and extract structured data from GlobalMilitary.net HTML pages, handling the site's table-based layout for equipment listings.
- **FR-013**: System MUST support the search functionality available on each equipment page (the "Find a [X] in our Database" search boxes), forwarding user queries to the site's search mechanism.
- **FR-014**: System MUST implement a local cache with a configurable TTL (default 24 hours). Cached responses MUST be served for repeated queries within the TTL window. Cache entries MUST be invalidatable on demand. First requests for uncached data fetch live from GlobalMilitary.net; subsequent requests within TTL serve from cache.
- **FR-015**: System MUST enforce a maximum rate of 1 request per second to GlobalMilitary.net. Concurrent requests to the upstream site MUST be serialized through a rate limiter.

### Key Entities

- **Equipment**: A military hardware item (aircraft, missile, firearm, vehicle, or ship). Key attributes: name, country of origin, category/sub-type, manufacturer, production count, decade/year, description, and technical specifications (category-specific: range, speed, payload for missiles; caliber, rate of fire for firearms; displacement, armament for ships; etc.).
- **Inventory**: A country-level military force composition. Sub-types include: Air Force (aircraft counts by type, air force index score), Navy (fleet composition by ship type, navy index score), Air Base (name, operating country, host country, year established, coordinates), Rank Structure (rank name, NATO code, branch), Nuclear Arsenal (total warheads, deployed, stockpile, retired, delivery methods).
- **Search Query**: A structured request from the MCP client. Attributes: category (required enum), query text (optional keyword/name filter), country (optional ISO filter), sub_category (optional sub-type filter), decade (optional era filter), page number (optional, default 1). The calling agent decomposes user natural language into these structured fields before invoking the tool.
- **Search Result**: A structured response containing matched entities. Attributes: list of matching Equipment or Inventory items, total result count, current page, total pages, query interpretation notes.
- **Comparison**: A side-by-side view of two or more Equipment entities from the same category. Attributes: list of equipment items, shared specification fields, differing values.

## Clarifications

### Session 2026-02-17

- Q: Should the server fetch data live from GlobalMilitary.net on every request, use a local cache with TTL, or build a full offline index? → A: Scrape with local cache (TTL-based) — fetch from site, cache results locally, serve from cache until TTL expires (e.g., 24h).
- Q: How should image-based search work — server calls an external vision API, delegate to the calling LLM, or both? → A: Delegate to the calling LLM — accept image via MCP, rely on the MCP client's own vision to describe it, then text-search the description. No external vision API dependency on the server.
- Q: Should each data domain (10 categories) get its own MCP tool, or use fewer broad tools with a category parameter? → A: Broad tools with category parameter — ~3-4 tools (search_equipment, search_inventory, compare_equipment, identify_from_image) with category as a parameter.
- Q: What rate limit should the server enforce when scraping GlobalMilitary.net? → A: 1 request/second max to GlobalMilitary.net, with exponential backoff on 429/5xx responses.
- Q: Should the server parse natural language internally or expect the calling agent to provide structured parameters? → A: Structured parameters only — server expects category, country, query, decade, page as explicit params; the calling agent handles NLP decomposition.

## Assumptions

- GlobalMilitary.net is a publicly accessible website and scraping its content for personal/research use via an MCP server is permitted under its terms of service. The server will respect standard rate limiting and robots.txt directives.
- The website structure (URL patterns, HTML table layouts, pagination via `?page=N` query parameters) will remain stable. If the site changes structure, the scraping logic will need to be updated.
- The site's built-in search functionality (the "Search" boxes on each equipment page) submits queries that can be replicated programmatically.
- Image-based identification is delegated to the calling MCP client's own vision capabilities (e.g., Claude, GPT). The MCP server receives a text description of the image from the client and performs a standard text search. The server does NOT host, train, or call any external computer vision model or API.
- Equipment categories and inventory categories match those currently available on the site: Aircraft, Missiles, Firearms, Vehicles, Ships (equipment) and Air Forces, Air Bases, Navies, Ranks, Nuclear (inventory).
- Multi-language support (Spanish, French, Portuguese) is available on the site but the primary interface will be English. Localized results may be added as a future enhancement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can search any of the 5 equipment categories by text and receive relevant results within 3 seconds for the first query, including data retrieval from GlobalMilitary.net.
- **SC-002**: Users can query all 5 inventory categories and receive structured data within 3 seconds.
- **SC-003**: Image-based equipment identification returns the correct equipment in its top-3 suggestions at least 80% of the time for clear, well-lit photographs of common military equipment.
- **SC-004**: 100% of MCP tools are discoverable via the MCP tool listing mechanism, with complete parameter schemas and descriptions.
- **SC-005**: The server gracefully handles GlobalMilitary.net downtime, returning a user-friendly error within 5 seconds rather than hanging or crashing.
- **SC-006**: Equipment comparisons return side-by-side specifications for 2-5 items within 5 seconds.
- **SC-007**: Pagination works correctly for all equipment categories, allowing users to retrieve any page of results without data duplication or missing entries.