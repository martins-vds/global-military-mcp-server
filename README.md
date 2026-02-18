# Global Military MCP Server

An MCP (Model Context Protocol) server that provides structured access to military equipment and force-composition data from [GlobalMilitary.net](https://www.globalmilitary.net/). Built with [FastMCP v2](https://github.com/jlowin/fastmcp) for seamless integration with Claude Desktop, Copilot, and other MCP-compatible clients.

## Architecture

```text
┌──────────────────────────────────────────────┐
│  MCP Client (Claude Desktop / Copilot / …)   │
└──────────────────┬───────────────────────────┘
                   │ stdio / HTTP
┌──────────────────▼───────────────────────────┐
│  FastMCP Server (src/server.py)              │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Tools (4) │  │ Resources│  │ Lifespan   │ │
│  └────┬─────┘  └──────────┘  │ (DI ctx)   │ │
│       │                      └────────────┘ │
├───────▼──────────────────────────────────────┤
│  Domain Services                             │
│  SearchService · IdentificationService       │
│  ComparisonService                           │
├──────────────────────────────────────────────┤
│  Infrastructure                              │
│  ┌────────────┐ ┌────────┐ ┌──────────────┐ │
│  │ HTTP Client│ │ Parser │ │ File Cache   │ │
│  │ + Rate     │ │ (BS4)  │ │ (24h TTL,    │ │
│  │   Limiter  │ │        │ │  LRU 500)    │ │
│  │ + Circuit  │ │        │ │              │ │
│  │   Breaker  │ │        │ │              │ │
│  └────────────┘ └────────┘ └──────────────┘ │
└──────────────────────────────────────────────┘
                   │
                   ▼
         GlobalMilitary.net
```

## Setup

### Prerequisites

- Python 3.12+

### Install

```bash
# Clone
git clone <repo-url> global-military-mcp-server
cd global-military-mcp-server

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run

```bash
# stdio mode (Claude Desktop / local)
fastmcp run src/server.py

# HTTP mode
fastmcp run src/server.py --transport http --port 8000
```

## Tools

| Tool                  | Description                                                   | Required Parameters                                |
| --------------------- | ------------------------------------------------------------- | -------------------------------------------------- |
| `search_equipment`    | Search aircraft, missiles, firearms, vehicles, ships          | `category`                                         |
| `search_inventory`    | Search air forces, air bases, navies, ranks, nuclear arsenals | `category`                                         |
| `identify_from_image` | Identify equipment from an LLM's image description            | `equipment_name` or `category` + `characteristics` |
| `compare_equipment`   | Compare 2–5 items side-by-side within a category              | `category`, `slugs`                                |

### Equipment Categories & Filters

| Category   | Sub-categories                                                                      | Decade filter | Country | Query |
| ---------- | ----------------------------------------------------------------------------------- | ------------- | ------- | ----- |
| `aircraft` | combat, bomber, helicopter, training, transport, uav, other                         | ✓             | ✓       | ✓     |
| `missiles` | aam, ashm, asm, atm, ballistic, cruise, sam                                         | ✗             | ✓       | ✓     |
| `ships`    | submarine, frigate, corvette, amphibious, cruiser, destroyer, carrier, patrol, mine | ✓             | ✓       | ✓     |
| `firearms` | matsniper, assault, bullassault, shotgun, lmg, mg, smg, smp, sniper                 | ✗             | ✓       | ✓     |
| `vehicles` | —                                                                                   | ✗             | ✓       | ✓     |

### Inventory Categories

| Category     | Description                      |
| ------------ | -------------------------------- |
| `air_forces` | Air force composition by country |
| `air_bases`  | Military air bases worldwide     |
| `navies`     | Naval fleet composition          |
| `ranks`      | Military rank structures         |
| `nuclear`    | Nuclear arsenal data             |

## Resources

| URI                                              | Description                                                   |
| ------------------------------------------------ | ------------------------------------------------------------- |
| `military://categories`                          | All equipment and inventory categories with supported filters |
| `military://equipment/{category}/sub-categories` | Sub-category slugs and labels for a given category            |

## Claude Desktop Configuration

Add to your Claude Desktop config (`~/.config/claude/claude_desktop_config.json` on Linux):

```json
{
  "mcpServers": {
    "global-military": {
      "command": "fastmcp",
      "args": ["run", "/absolute/path/to/src/server.py"]
    }
  }
}
```

## Development

### Run Tests

```bash
# All tests
pytest

# By layer
pytest tests/unit/          # Domain logic, parser, cache (fast)
pytest tests/integration/   # Mocked HTTP, filesystem
pytest tests/contract/      # MCP schema validation

# With coverage
pytest --cov=src --cov-report=term-missing
```

### Project Structure

```text
src/
├── server.py              # FastMCP server, lifespan, resources
├── domain/
│   ├── enums.py           # EquipmentCategory, InventoryCategory
│   ├── models.py          # Equipment, Inventory, SearchResult, etc.
│   └── services.py        # SearchService, IdentificationService, ComparisonService
├── scraper/
│   ├── client.py          # RateLimiter, CircuitBreaker, fetch_with_resilience
│   ├── urls.py            # URL builders for equipment and inventory
│   └── parser.py          # HTML → domain model parsers (BeautifulSoup)
├── cache/
│   └── store.py           # FileCache with SHA-256 keys, TTL, LRU eviction
└── tools/
    ├── equipment.py       # search_equipment, identify_from_image, compare_equipment
    └── inventory.py       # search_inventory

tests/
├── unit/                  # 130+ unit tests
├── integration/           # Mocked HTTP pipelines, filesystem cache
├── contract/              # MCP tool & resource schema validation
└── fixtures/html/         # Saved HTML samples for deterministic parsing
```

### Design Decisions

- **No NLP** — All parameters are structured. The calling LLM interprets natural language.
- **Image delegation** — `identify_from_image` accepts text descriptions; the LLM analyzes images first.
- **Rate limiting** — 1 req/sec to GlobalMilitary.net, exponential backoff on 429/5xx.
- **Circuit breaker** — Opens after 5 consecutive failures, 60s recovery timeout.
- **File cache** — 24h TTL, LRU (max 500 entries), atomic writes, stdlib-only.
- **Read-only** — Every tool is annotated `readOnlyHint: true`, `idempotentHint: true`.

## License

MIT
