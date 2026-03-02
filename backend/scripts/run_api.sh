#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created backend/.env from backend/.env.example"
fi

python -m uvicorn parallelife.apps.api_gateway:app --reload --port "$PORT"

