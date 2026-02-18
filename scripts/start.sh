#!/usr/bin/env bash
# Start the Global Military MCP Server (stdio mode by default).
# Usage:
#   ./scripts/start.sh              # stdio (Claude Desktop / local)
#   ./scripts/start.sh --http       # HTTP on port 8000
#   ./scripts/start.sh --http 3000  # HTTP on custom port
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Activate venv if not already active
if [[ -z "${VIRTUAL_ENV:-}" && -d .venv ]]; then
    source .venv/bin/activate
fi

if [[ "${1:-}" == "--http" ]]; then
    PORT="${2:-8000}"
    echo "Starting server in HTTP mode on port $PORT ..."
    exec fastmcp run src/server.py --transport http --port "$PORT"
else
    echo "Starting server in stdio mode ..."
    exec fastmcp run src/server.py
fi
