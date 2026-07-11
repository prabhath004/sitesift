#!/usr/bin/env bash
# Every quality gate, in one command. Run this before claiming work is done.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT_DIR/backend/.venv/bin"

if [ ! -x "$VENV/pytest" ]; then
  echo "Backend venv missing — run ./scripts/setup.sh first" >&2
  exit 1
fi

echo "── backend: format ──"
(cd "$ROOT_DIR/backend" && "$VENV/ruff" format --check .)
echo "── backend: lint ──"
(cd "$ROOT_DIR/backend" && "$VENV/ruff" check .)
echo "── backend: types ──"
(cd "$ROOT_DIR/backend" && "$VENV/mypy")
echo "── backend: tests ──"
(cd "$ROOT_DIR/backend" && "$VENV/pytest")

echo "── frontend: lint ──"
(cd "$ROOT_DIR/frontend" && npm run lint)
echo "── frontend: types ──"
(cd "$ROOT_DIR/frontend" && npm run typecheck)
echo "── frontend: tests ──"
(cd "$ROOT_DIR/frontend" && npm test)
echo "── frontend: build ──"
(cd "$ROOT_DIR/frontend" && npm run build)

echo "All checks passed."
