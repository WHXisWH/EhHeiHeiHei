# ParalleLife MVP Demo (Web Observer + Python + GCP)

This repo scaffolds a workable MVP demo based on `ParalleLife_MVP_PRD_v1.1_CN.md`.

## What you get (MVP demo)

- **Web observer (React)**: map view + agent list/detail + send message + live updates via WebSocket.
- **Backend (FastAPI)**: REST APIs + WebSocket broadcast + tick runner (world engine) + agent runtime.
- **Real GCP adapters**: Vertex AI Gemini (agent decision), Cloud STT/TTS (non-realtime demo endpoints).
- **Clear layering**: domain/usecases/ports/adapters split for maintainability.
- **Tests**: unit + API contract + end-to-end (in-memory) with high coverage.

## Local quickstart

### 1) Start PostGIS (optional for local DB mode)

```bash
docker compose up -d db
```

### 2) Backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate  # (WSL/macOS) / On Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
cp .env.example .env
uvicorn parallelife.apps.api_gateway:app --reload --port 8000
```

Seed demo agents:

```bash
curl -X POST http://localhost:8000/internal/seed-demo
```

Run a tick once:

```bash
curl -X POST http://localhost:8000/internal/tick
```

### 3) World tick (local loop)

In another terminal:

```bash
cd backend
. .venv/bin/activate
python -m parallelife.apps.world_engine_loop
```

### 4) Web

```bash
cd web
npm i
```

Optional:

```bash
cp .env.example .env
npm run dev
```

Open the web UI:

- `http://localhost:5173`

## Required env (GCP)

Backend reads `.env`:

- `GOOGLE_APPLICATION_CREDENTIALS` (service account json)
- `GCP_PROJECT_ID`, `GCP_LOCATION`
- `VERTEX_GEMINI_MODEL` (default `gemini-1.5-flash`)

## Notes

- Real-time **WebRTC voice call** is not implemented in this MVP demo yet; the demo includes **STT/TTS HTTP endpoints** to validate the GCP pipeline.

## Tests

```bash
cd backend
python -m pytest
```
