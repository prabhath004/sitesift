#!/usr/bin/env bash
# Run backend and frontend together, without Docker.
#
#   ./scripts/dev.sh                        # first free ports from 8000 / 3000
#   BACKEND_PORT=8010 FRONTEND_PORT=3010 ./scripts/dev.sh
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.superset/run.sh" start
