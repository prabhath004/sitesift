#!/usr/bin/env bash
# Install backend and frontend dependencies. Thin wrapper so that the plain
# local workflow and the Superset workflow cannot drift apart.
set -euo pipefail
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.superset/run.sh" setup
