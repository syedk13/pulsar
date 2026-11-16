# Architecture

> Status: scaffold only. No features are implemented.

Pulsar is a **decision-support** concept that helps an astronaut notice and review changes in their own health patterns. It is not a diagnostic or treatment system.

## Components

```
                    ┌──────────────────────────┐
                    │  apps/web                │
                    │  React + TS + Vite       │
                    │  Tailwind, Recharts      │
                    └──────┬─────────────┬─────┘
       publishable key     │             │  HTTPS (VITE_API_BASE_URL)
       + user JWT (RLS)    │             │
                           ▼             ▼
            ┌────────────────────┐   ┌───────────────────────────┐
            │ Supabase           │◀──│ apps/api (FastAPI)        │
            │ PostgreSQL + Auth  │   │ future analysis service   │
            │ Row Level Security │   │ scikit-learn/pandas/NumPy │
            └────────────────────┘   └─────────────┬─────────────┘
                     secret key (server-only)       │ future, isolated
                                                    ▼
                                      NASA provider adapters (not built)
```

### Path 1 — React/Vite → Supabase (data + auth)
The browser uses `@supabase/supabase-js` with the **publishable key only**. All access is governed by RLS policies (`supabase/migrations/`). Planned use: sign-in, writing check-ins, reading own history and shared mission-context readings.

### Path 2 — React/Vite → FastAPI → Supabase (analysis)
The browser calls the FastAPI service for analysis (`POST /analyze`, currently 501). FastAPI uses the Supabase **secret/service key server-side** to read a profile's history and write `anomaly_results`. No ML code exists yet.

### Supabase Edge Functions
Not used. Edge Functions are TypeScript/Deno; Pulsar's server logic lives in the Python FastAPI service instead.

## Data-source isolation
Two modes, chosen by `DEMO_MODE`:

- **Demo mode (default):** every metric comes from the local generator (`app/synthetic/`) plus saved samples. No keys, no network.
- **Live mode:** adds two optional hooks in `app/providers/`: NOAA SWPC GOES proton flux (S-scale level) and DONKI space weather events. Everything else stays generated.

Adapters normalise records into `environment_readings` or `mission_events` with source, unit, timestamp, freshness and simulated flags. Mission-context data is always kept separate from personal check-in data and is never presented as an individual's dose.

Two flag layers, never merged: crew health flags from `/analyze` use personal baselines only; environment status labels (ppCO2 vs NASA-STD-3001 V2 6004, NOAA S-level) are computed from telemetry and shown on the mission-context panel. Full metric-by-source table: `data-sources.md`. Limits and generator: `synthetic-data.md`.

## Deployment options (not deployed)
- **Frontend:** Vercel — root directory `apps/web`, build `npm run build`, output `dist`, set `VITE_*` env vars.
- **API:** Render web service — root `apps/api`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, set server env vars and `CORS_ALLOWED_ORIGINS` to the Vercel URL.
- **Database:** Supabase hosted project (no separate DB server).
