#!/usr/bin/env bash
set -euo pipefail

export API_BASE_URL="${1:-http://localhost:8000}"
export TICK_INTERVAL_SECONDS="${2:-60}"

python -m parallelife.apps.world_engine_loop

