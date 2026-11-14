# Pulsar

Astronaut health self-monitoring concept for the NASA Space Apps Challenge. Pulsar is meant to help astronauts on long-duration missions notice and review changes in their own sleep, mood, and heart-rate patterns, with microgravity and radiation telemetry shown alongside as mission context.

Pulsar is a **decision-support concept, not a diagnostic or treatment system.** All crew data is fictional or synthetic.

> **Status: scaffold only.** There are no screens, no ML, no check-in workflow, and no NASA integrations yet. The API answers `GET /health`; `POST /analyze` returns `501`.

## Stack
| Layer | Tech |
|---|---|
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4, Recharts, supabase-js |
| Database / auth | Supabase (hosted PostgreSQL, Auth, RLS) |
| API | Python FastAPI, Uvicorn, pydantic-settings, supabase-py, HTTPX |
| Future ML | scikit-learn, pandas, NumPy (installed, unused) |

## Prerequisites
- Node.js ≥ 22.12 (npm 11)
- Python ≥ 3.11

## Layout
```
apps/web/            React + Vite foundation (minimal entrypoint)
apps/api/            FastAPI service (app/main.py, config.py, schemas.py) + .venv
supabase/migrations/ SQL schema + RLS scaffolding
docs/                architecture, data model, API contract, data sources
.cache/npm, .cache/pip  project-local package caches (git-ignored)
```

## Setup
Run all commands from the repo root. The root `.npmrc` points npm's cache to `.cache/npm`.

```bash
cp .env.example .env          # then fill in values

npm install                   # frontend deps (npm workspace: apps/web)
npm run setup:api             # creates apps/api/.venv and installs requirements.txt
                              # (dev tooling: apps/api/.venv/bin/pip install -r apps/api/requirements-dev.txt)
```

## Run
```bash
npm run dev:web               # http://localhost:5173
npm run dev:api               # http://localhost:8000/health, docs at /docs
npm run build:web             # typecheck + production build
```

Lint the API: `cd apps/api && .venv/bin/ruff check . && .venv/bin/ruff format .`

## Environment variables
See `.env.example`. One root `.env` is read by both apps.

| Variable | Used by | Notes |
|---|---|---|
| `VITE_SUPABASE_URL` | web | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | web | Publishable/anon key — safe for the browser |
| `VITE_API_BASE_URL` | web | FastAPI base URL |
| `SUPABASE_URL` | api | Supabase project URL |
| `SUPABASE_SECRET_KEY` | api | **Server only.** Never prefix with `VITE_` |
| `CORS_ALLOWED_ORIGINS` | api | Comma-separated origins |
| `DEMO_MODE` | api | `true` for the synthetic-data demo |

## Manual Supabase setup (not done)
1. Create a Supabase project.
2. Copy the project URL, publishable key, and secret key into `.env`.
3. Apply `supabase/migrations/20261114000000_initial_schema.sql` (SQL editor, or `npx supabase db push` after `supabase link`).
4. Decide whether to enable Auth accounts; if not, add the narrowly-scoped `anon` read policies noted at the end of the migration.

## Deployment (later, not set up)
- **Vercel** (frontend): root `apps/web`, build `npm run build`, output `dist`, set `VITE_*` vars.
- **Render** (API): root `apps/api`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, set server vars.

## Dependency pins
- Frontend: exact versions in `apps/web/package.json`, locked by the root `package-lock.json`.
- API: direct pins in `apps/api/requirements.txt`, full transitive lock in `apps/api/requirements.lock.txt`.

## Docs
[architecture](docs/architecture.md) · [data model](docs/data-model.md) · [API contract](docs/api-contract.md) · [data sources](docs/data-sources.md)
