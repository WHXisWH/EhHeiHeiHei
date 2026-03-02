param(
  [string]$ApiBaseUrl = "http://localhost:8000",
  [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"

$env:API_BASE_URL = $ApiBaseUrl
$env:TICK_INTERVAL_SECONDS = "$IntervalSeconds"

python -m parallelife.apps.world_engine_loop

