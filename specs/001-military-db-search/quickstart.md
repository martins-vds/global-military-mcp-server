# Quickstart: Global Military Database Search MCP Server

**Branch**: `001-military-db-search` | **Python**: 3.13 | **Framework**: FastMCP v2

---

## Prerequisites

- Docker Desktop (for devcontainer)
- VS Code with Dev Containers extension
- OR: Python 3.13+ installed locally

---

## 1. Open in Devcontainer (Recommended)

```bash
# Clone and open in VS Code
git clone <repo-url> global-military-mcp-server
cd global-military-mcp-server
code .
# VS Code will prompt: "Reopen in Container" → click Yes
```

The devcontainer automatically installs Python 3.13 and all dependencies.

## 2. Local Setup (Alternative)

```bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

---

## 3. Run the Server

### stdio mode (local dev / Claude Desktop)

```bash
# From repo root
fastmcp run src/server.py
```

### HTTP mode (remote access / testing)

```bash
fastmcp run src/server.py --transport http --port 8000
```

### Programmatic (in Python)

```python
from src.server import mcp

if __name__ == "__main__":
    mcp.run()  # stdio by default
```

---

## 4. Test with FastMCP Client

### Interactive (CLI)

```bash
# List available tools
fastmcp dev src/server.py
```

### Programmatic Test

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("src/server.py") as client:
        # List tools
        tools = await client.list_tools()
        print([t.name for t in tools])
        # → ['search_equipment', 'search_inventory', 'compare_equipment', 'identify_from_image']

        # Search for F-16 aircraft
        result = await client.call_tool("search_equipment", {
            "category": "aircraft",
            "query": "F-16"
        })
        print(result)

        # Browse navies
        result = await client.call_tool("search_inventory", {
            "category": "navies"
        })
        print(result)

        # Compare two fighters
        result = await client.call_tool("compare_equipment", {
            "category": "aircraft",
            "slugs": ["f-22-raptor", "su-57"]
        })
        print(result)

        # List resources
        resources = await client.list_resources()
        print([r.uri for r in resources])
        # → ['military://categories']

asyncio.run(main())
```

---

## 5. Run Tests

```bash
# All tests
pytest

# Unit tests only (fast, no network)
pytest tests/unit/

# Integration tests (mocked HTTP)
pytest tests/integration/

# Contract tests (MCP schema validation)
pytest tests/contract/

# With coverage
pytest --cov=src --cov-report=term-missing
```

---

## 6. Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `~/.config/claude/claude_desktop_config.json` (Linux):

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

Restart Claude Desktop. The server tools will appear in the tools panel.

---

## 7. Available Tools

| Tool                  | Description                                          | Required Params                                    |
| --------------------- | ---------------------------------------------------- | -------------------------------------------------- |
| `search_equipment`    | Search aircraft, missiles, firearms, vehicles, ships | `category`                                         |
| `search_inventory`    | Search air forces, air bases, navies, ranks, nuclear | `category`                                         |
| `compare_equipment`   | Compare 2-5 items side-by-side                       | `category`, `slugs`                                |
| `identify_from_image` | Identify equipment from LLM's image description      | `equipment_name` or `category` + `characteristics` |

## 8. Available Resources

| URI                                              | Description                                                   |
| ------------------------------------------------ | ------------------------------------------------------------- |
| `military://categories`                          | All equipment and inventory categories with supported filters |
| `military://equipment/{category}/sub-categories` | Sub-category slugs for a given equipment category             |

---

## 9. Project Structure

```text
src/
├── server.py                # FastMCP server entry point
├── domain/                  # Entities, value objects, enums, services
├── scraper/                 # HTTP client, HTML parser, URL builder
├── cache/                   # TTL-based file cache (stdlib)
└── tools/                   # MCP tool handlers

tests/
├── unit/                    # Domain logic, parser, cache
├── integration/             # Mocked HTTP, real filesystem
├── contract/                # MCP tool schema validation
└── fixtures/html/           # Saved HTML samples for testing
```

---

## 10. Key Design Decisions

- **No NLP**: All parameters are structured (category, country, decade, page). The calling LLM interprets natural language.
- **Image delegation**: `identify_from_image` accepts text descriptions, not images. The LLM analyzes the image first.
- **Rate limiting**: 1 request/sec to GlobalMilitary.net with exponential backoff on 429/5xx.
- **Cache**: 24-hour TTL, file-based JSON (stdlib only, zero dependencies).
- **Read-only**: All tools are annotated as read-only, idempotent, and open-world.

See [research.md](research.md) for detailed rationale and [data-model.md](data-model.md) for entity definitions.
