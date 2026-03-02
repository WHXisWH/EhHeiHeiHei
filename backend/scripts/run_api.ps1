param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created backend/.env from backend/.env.example"
}

python -m uvicorn parallelife.apps.api_gateway:app --reload --port $Port

