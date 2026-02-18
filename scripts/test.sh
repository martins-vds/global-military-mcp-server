#!/usr/bin/env bash
# Run the test suite.
# Usage:
#   ./scripts/test.sh                  # all tests
#   ./scripts/test.sh unit             # unit tests only
#   ./scripts/test.sh integration      # integration tests only
#   ./scripts/test.sh contract         # contract tests only
#   ./scripts/test.sh --coverage       # all tests with coverage report
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Activate venv if not already active
if [[ -z "${VIRTUAL_ENV:-}" && -d .venv ]]; then
    source .venv/bin/activate
fi

case "${1:-all}" in
    unit)
        echo "Running unit tests ..."
        exec python -m pytest tests/unit/ -v "${@:2}"
        ;;
    integration)
        echo "Running integration tests ..."
        exec python -m pytest tests/integration/ -v "${@:2}"
        ;;
    contract)
        echo "Running contract tests ..."
        exec python -m pytest tests/contract/ -v "${@:2}"
        ;;
    --coverage)
        echo "Running all tests with coverage ..."
        exec python -m pytest tests/ -v --cov=src --cov-report=term-missing "${@:2}"
        ;;
    all)
        echo "Running all tests ..."
        exec python -m pytest tests/ -v "${@:2}"
        ;;
    *)
        echo "Usage: $0 [unit|integration|contract|--coverage|all]"
        exit 1
        ;;
esac
