#!/usr/bin/env bash
#
# SiteSift — Superset entrypoint.
#
#   ./.superset/run.sh setup    Install frontend + backend dependencies
#   ./.superset/run.sh start    Run backend and frontend together (default)
#
# Ports are never hard-coded: BACKEND_PORT / FRONTEND_PORT win if set, otherwise
# the first free port at or above the base is chosen. Several worktrees can
# therefore run at the same time without colliding.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/backend/.venv"
BACKEND_PORT_BASE="${BACKEND_PORT_BASE:-8000}"
FRONTEND_PORT_BASE="${FRONTEND_PORT_BASE:-3000}"

log() { printf '\033[36m[sitesift]\033[0m %s\n' "$*"; }

# --- helpers ----------------------------------------------------------------

port_is_free() {
  ! (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

first_free_port() {
  local port=$1
  local limit=$((port + 50))
  while [ "$port" -lt "$limit" ]; do
    if port_is_free "$port"; then
      printf '%s' "$port"
      return 0
    fi
    port=$((port + 1))
  done
  echo "No free port found between $1 and $limit" >&2
  return 1
}

python_bin() {
  if command -v python3 >/dev/null 2>&1; then echo python3; else echo python; fi
}

ensure_env_file() {
  if [ ! -f "$ROOT_DIR/.env" ]; then
    log "No .env found — copying .env.example"
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  fi
}

# --- commands ---------------------------------------------------------------

setup() {
  ensure_env_file

  log "Creating Python virtual environment (backend/.venv)"
  [ -d "$VENV_DIR" ] || "$(python_bin)" -m venv "$VENV_DIR"

  log "Installing backend dependencies"
  "$VENV_DIR/bin/pip" install --upgrade pip --quiet
  "$VENV_DIR/bin/pip" install --quiet -r "$ROOT_DIR/backend/requirements.txt"

  log "Installing frontend dependencies"
  (cd "$ROOT_DIR/frontend" && npm install --no-audit --no-fund)

  log "Setup complete"
}

start() {
  ensure_env_file
  [ -d "$VENV_DIR" ] || setup

  local backend_port frontend_port
  backend_port="${BACKEND_PORT:-$(first_free_port "$BACKEND_PORT_BASE")}"
  frontend_port="${FRONTEND_PORT:-$(first_free_port "$FRONTEND_PORT_BASE")}"

  export BACKEND_PORT="$backend_port"
  export FRONTEND_PORT="$frontend_port"
  # The browser calls the backend directly, so the frontend must be told which
  # port this worktree's backend landed on.
  export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:$backend_port}"
  # ...and the backend must accept that frontend origin.
  export CORS_ORIGINS="[\"http://localhost:$frontend_port\",\"http://127.0.0.1:$frontend_port\"]"

  # Job control gives each child its own process group, so cleanup can take down
  # uvicorn's reloader and next's workers with it rather than orphaning them.
  set -m

  BACKEND_PID=""
  FRONTEND_PID=""

  cleanup() {
    trap - EXIT INT TERM
    log "Shutting down"
    for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
      [ -n "$pid" ] || continue
      kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  log "Backend  → http://localhost:$backend_port  (docs at /docs, health at /health)"
  (cd "$ROOT_DIR/backend" && exec "$VENV_DIR/bin/uvicorn" app.main:app \
    --host 0.0.0.0 --port "$backend_port" --reload) &
  BACKEND_PID=$!

  log "Frontend → http://localhost:$frontend_port"
  # next directly, not `npm run dev`: one less process between us and the signal.
  (cd "$ROOT_DIR/frontend" && exec ./node_modules/.bin/next dev --port "$frontend_port") &
  FRONTEND_PID=$!

  # `wait -n` is bash 4+; macOS ships bash 3.2. Poll instead, and exit as soon as
  # either process dies so a crashed backend does not hide behind a live frontend.
  while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
    sleep 1
  done
}

case "${1:-start}" in
  setup) setup ;;
  start) start ;;
  *)
    echo "Usage: $0 [setup|start]" >&2
    exit 1
    ;;
esac
