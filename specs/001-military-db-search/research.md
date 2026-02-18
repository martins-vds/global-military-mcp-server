# Phase 0 Research: Global Military Database Search MCP Server

**Date**: 2026-02-17
**Branch**: `001-military-db-search`
**Spec**: [spec.md](spec.md)

This document resolves all NEEDS CLARIFICATION items from the Technical Context and documents technology/integration decisions.

---

## R1: GlobalMilitary.net HTML Structure & Scraping Strategy

### Decision: BeautifulSoup4 with CSS selectors targeting `table.table` blocks

### Rationale
The site uses a consistent HTML structure across all equipment categories: multiple `<div class="card card-table">` blocks per page, each containing a `<table class="table">` with `thead`/`tbody`. This regularity makes CSS selector-based parsing reliable and maintainable.

### Key Findings

**Page Layout**: All category pages share: `div#content > div.card.card-table > div.scrollable-table > table.table`. Each page has 4-5 table blocks (items spread across them), so the parser must iterate ALL `table.table` elements.

**Search**: Equipment pages have GET forms at `/{section}/?name={query}`. Navies has no search input. Global search at `/search/?q={query}`.

**Filters**: Link-based, not form-based. URL patterns:
- Category: `/{section}/category/{slug}/` (e.g., `/aircraft/category/combat/`)
- Country: `/{section}/country/{iso3}/` (e.g., `/aircraft/country/usa/`)
- Decade: `/{section}/decade/{year}/` (e.g., `/aircraft/decade/1980/`)

**Filter Availability**:
| Section    | Category | Decade | Country | Name Search |
| ---------- | -------- | ------ | ------- | ----------- |
| Aircraft   | ✅        | ✅      | ✅       | ✅           |
| Missiles   | ✅        | ❌      | ✅       | ✅           |
| Ships      | ✅        | ✅      | ✅       | ✅           |
| Firearms   | ✅        | ❌      | ✅       | ✅           |
| Navies     | ❌        | ❌      | ❌       | ❌           |
| Vehicles   | TBD      | TBD    | TBD     | TBD         |
| Air Bases  | ❌        | ❌      | TBD     | TBD         |
| Nuclear    | ❌        | ❌      | ❌       | ❌           |
| Ranks      | ❌        | ❌      | TBD     | ❌           |
| Air Forces | ❌        | ❌      | ❌       | ❌           |

> **Note**: Rows marked TBD were not researched during Phase 0. To be confirmed during T006 (HTML fixture capture). Inventory sections (Air Bases, Nuclear, Ranks, Air Forces) generally have simpler browsing with fewer filter options than equipment sections.

**Pagination**: `<ul class="pagination">` with `?page=N` query params (1-indexed). Navies has no pagination (single page). Other sections: 6-10 pages.

**Data Columns Per Section**:
- Aircraft: Country, Model (link), Thumbnail, Manufacturer, Produced, Description
- Missiles: Country, Model (link), Category, Range, Max Speed
- Ships: Country, Class (link), Type, Year
- Firearms: Country, Model (link), Category
- Navies: Rank, Country (link), Navy Index, Capital ships, Major combatants, Total active

**Detail Pages**: `/{section}/{slug}/` for equipment, `/navies/{iso3}/` for navies.

**Sorting**: `?sort=field` (ascending), `?sort=-field` (descending).

### URL Construction Patterns

```python
URL_PATTERNS = {
    "list":            "https://www.globalmilitary.net/{section}/",
    "search":          "https://www.globalmilitary.net/{section}/?name={query}",
    "paginate":        "https://www.globalmilitary.net/{section}/?page={n}",
    "filter_category": "https://www.globalmilitary.net/{section}/category/{slug}/",
    "filter_country":  "https://www.globalmilitary.net/{section}/country/{iso3}/",
    "filter_decade":   "https://www.globalmilitary.net/{section}/decade/{year}/",
    "detail":          "https://www.globalmilitary.net/{section}/{item_slug}/",
    "global_search":   "https://www.globalmilitary.net/search/?q={query}",
}
```

### CSS Selectors

```python
SELECTORS = {
    "tables":       "table.table",
    "rows":         "table.table > tbody > tr",
    "detail_link":  "td:nth-child(2) > a",
    "pagination":   "ul.pagination",
    "page_links":   "ul.pagination > li > a",
    "current_page": "ul.pagination > li.active",
}
```

### Alternatives Considered
- **Selenium/Playwright**: Rejected — site is server-rendered HTML, no JavaScript required for data extraction.
- **Scrapy**: Rejected — adds heavy dependency for what is a simple request-parse-cache pipeline. httpx + BS4 is sufficient.
- **regex-based parsing**: Rejected — fragile, harder to maintain than CSS selectors.

---

## R2: FastMCP v2 Server Patterns

### Decision: FastMCP v2 stable (`fastmcp<3`) with lifespan, dependency injection, and ToolError

### Rationale
FastMCP v2 is the stable release (v2.14.5 latest). v3.0.0 is a release candidate — not appropriate for production. v2 provides all required features: lifespan management, dependency injection, tool annotations, structured output, and error handling.

### Key Patterns

**Lifespan for Shared Resources**: Use `@lifespan` to create/teardown httpx.AsyncClient and FileCache. Yield a dict; always wrap in `try/finally`.

```python
@lifespan
async def app_lifespan(server):
    client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
    cache = FileCache(cache_dir=Path(".cache"), default_ttl=86400)
    try:
        yield {"http_client": client, "cache": cache}
    finally:
        await client.aclose()
```

**Dependency Injection**: Use `Depends()` to inject httpx client and cache into tools. Injected params are auto-hidden from MCP schema.

```python
def get_http_client(ctx: Context = CurrentContext()) -> httpx.AsyncClient:
    return ctx.lifespan_context["http_client"]

@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def search_equipment(
    category: EquipmentCategory,
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> SearchResult:
    ...
```

**Error Handling**: `ToolError` for user-facing errors (always reaches client). `mask_error_details=True` in production to hide internal exceptions.

**Annotations**: All tools are read-only scrapers:
```python
READ_ONLY_ANNOTATIONS = {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True}
```

**Transport**: stdio by default for local dev / Claude Desktop. HTTP transport for remote access. CLI: `fastmcp run server.py --transport http --port 8000`.

### v2 vs v3 Compatibility
Avoid v3-only APIs: `ctx.get_state`/`set_state`, `mcp.enable`/`disable`, `ctx.transport`, tool `timeout=`, `--reload`. Use lifespan context for shared state instead.

---

## R3: TTL-Based File Cache

### Decision: `pathlib` + `json` (stdlib only — zero dependencies)

### Rationale
1. **Async safety through synchronous atomicity**: Sync `path.read_text()` + `json.loads()` has no `await` points, so cannot be interleaved by another coroutine. Naturally atomic under asyncio.
2. **Negligible blocking**: Cache entries are 1-50 KB. Sync I/O completes in <1ms — invisible in a <200ms budget.
3. **Atomic writes via POSIX rename**: `write_text(tmp) → tmp.rename(target)` is atomic on Linux.
4. **Zero dependencies**: pathlib, json, hashlib, time — all stdlib.
5. **Debuggable**: Human-readable JSON files, inspectable with standard tools.

### Implementation Sketch

```python
class FileCache:
    def __init__(self, cache_dir: Path, default_ttl: float = 86400.0):
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._default_ttl = default_ttl

    def _key_path(self, key: str) -> Path:
        return self._dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"

    def get(self, key: str) -> dict | None:
        path = self._key_path(key)
        if not path.exists(): return None
        raw = json.loads(path.read_text())
        if raw["expires_at"] < time.time():
            path.unlink(missing_ok=True)
            return None
        return raw["data"]

    def set(self, key: str, value: dict, ttl: float | None = None) -> None:
        path = self._key_path(key)
        tmp = path.with_suffix(".tmp")
        payload = {"data": value, "expires_at": time.time() + (ttl or self._default_ttl)}
        tmp.write_text(json.dumps(payload))
        tmp.rename(path)

    def delete(self, key: str) -> bool: ...
    def clear(self) -> int: ...
```

### Alternatives Considered
| Option            | Verdict | Why Rejected                                                                      |
| ----------------- | ------- | --------------------------------------------------------------------------------- |
| `aiofiles` + JSON | ❌       | Adds dependency; async I/O introduces await points that create interleaving risks |
| `shelve`          | ❌       | Platform-dependent dbm backend; pickle serialization security risk; no TTL        |
| `diskcache`       | ❌       | CVE-2025-69872; dropped from FastMCP; pickle-based                                |
| `aiosqlite`       | ❌       | Overkill for point lookups; adds dependency for simple key-value-with-TTL         |

---

## R4: Rate Limiting

### Decision: `asyncio.Lock` + `asyncio.sleep` (stdlib only — zero dependencies)

### Rationale
1. **Correct by construction**: Lock serializes access; timestamp + sleep enforces 1 req/sec interval.
2. **Backoff is orthogonal**: No library handles retries — custom code needed regardless.
3. **~20 lines**: Adding `aiolimiter` (1.2K lines) to save 20 lines is not worthwhile.

### Implementation Sketch

```python
class RateLimiter:
    def __init__(self, min_interval: float = 1.0, backoff_base: float = 2.0, max_retries: int = 5):
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0
        self._min_interval = min_interval
        self._backoff_base = backoff_base
        self._max_retries = max_retries

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

    def backoff_delay(self, attempt: int) -> float:
        return self._backoff_base ** attempt
```

### Alternatives Considered
| Option              | Verdict | Why Rejected                                                               |
| ------------------- | ------- | -------------------------------------------------------------------------- |
| `aiolimiter`        | ❌       | Leaky bucket is wrong abstraction for strict 1/sec; doesn't handle backoff |
| `asyncio.Semaphore` | ❌       | Semantically "N concurrent" not "1 per interval"; Lock reads better        |
| Token bucket        | ❌       | Designed for burst allowances; overkill for strict 1/sec                   |

---

## R5: Dependency Summary

| Package          | Purpose                                | Version Constraint |
| ---------------- | -------------------------------------- | ------------------ |
| `fastmcp`        | MCP server framework                   | `<3` (v2 stable)   |
| `httpx`          | Async HTTP client for scraping         | `>=0.27`           |
| `beautifulsoup4` | HTML parsing                           | `>=4.12`           |
| `pydantic`       | Data validation (bundled with FastMCP) | —                  |

**Dev dependencies**:
| Package           | Purpose                             |
| ----------------- | ----------------------------------- |
| `pytest`          | Test framework                      |
| `pytest-asyncio`  | Async test support                  |
| `respx`           | httpx mocking for integration tests |
| `inline-snapshot` | Schema assertion snapshots          |

**Total new runtime dependencies**: 2 (httpx, beautifulsoup4) — pydantic is already a FastMCP transitive dep.

**Total infra code with zero new dependencies**: ~100 lines (cache + rate limiter, stdlib only).

---

## Revisit Triggers

- Cache entries grow >1 MB → consider aiosqlite for streaming reads
- Burst rate limiting needed → consider token bucket or aiolimiter
- Multiple server instances share cache → consider Redis or shared SQLite with WAL
- Site adds JavaScript rendering → consider Playwright (unlikely — site is SSR)
- FastMCP v3 reaches stable → evaluate migration for session state, built-in timeouts, --reload