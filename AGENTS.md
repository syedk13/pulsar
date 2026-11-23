# Pulsar: context for coding agents

Read this first, then [docs/STATUS.md](docs/STATUS.md) for what is done, what is in progress, and what is next. Deeper references: [architecture](docs/architecture.md), [data model](docs/data-model.md), [API contract](docs/api-contract.md), [data sources](docs/data-sources.md), [README](README.md) for setup.

## What we're building

NASA Space Apps Challenge 2026, challenge "Create Health Monitoring Software for Astronauts on Space Missions" ([brief](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/)).

Pulsar lets a crew member log a few daily health indicators (sleep, mood, resting heart rate), compares each reading with their own past pattern, flags changes worth reviewing, explains why in plain language, and shows microgravity and radiation readings next to the trends as mission context.

Pulsar is a **decision-support prototype, not a diagnostic tool.** A flag means "this differs from this profile's recent pattern," never "this person has a medical problem." All crew data is fictional or synthetic.

## Ground rules (product)

These apply to every change: code, copy, docs, demo script.

1. **Personal baselines, not universal norms.** Compare a profile to its own history. No medical thresholds, no "normal range" labels.
2. **No diagnosis language.** Use "worth reviewing," "differs from your usual," "collecting baseline." Never "risk," "condition," "disease," or "predicts."
3. **Explain every flag.** Show which indicators changed, the observed value, the baseline value, the unit and the period. A model score alone is not an explanation.
4. **Missing data is explicit.** Too little history returns `insufficient_data` ("collecting baseline"), never a silent `within_baseline`.
5. **Label provenance everywhere.** Every reading shows source, unit, timestamp and freshness, and whether it is measured, self-reported, simulated, missing or stale.
6. **Mission context is context.** Radiation and acceleration live in their own table and their own UI panel, aligned by timestamp. Never imply they caused a health change, never present them as a person's dose, and do not feed them into the anomaly model in the MVP.
7. **Simulated first.** The core demo must run with no external API keys and no live NASA data.

## Repo map

| Path | What | State |
|---|---|---|
| `apps/web/` | React 19 + TypeScript + Vite 8, Tailwind 4, Recharts | Sign-in + Daily Check-in (M3); no router yet |
| `apps/web/src/lib/supabase.ts` | Browser Supabase client (publishable key); `null` + `supabaseConfigError` when env is missing | Done |
| `apps/web/src/data/` | Supabase reads/writes (`getOwnProfile`, `listCheckins`, `createCheckin`); components never query Supabase directly | Done |
| `apps/web/src/checkin/validation.ts` | Form validation + `buildFormCheckin` (always `source: 'self_report'`, `is_simulated: false`) | Done |
| `apps/web/src/pages/CheckinPage.tsx` | Resolves the signed-in user's crew profile (loading / unlinked / error states), form + recent history | Done |
| `apps/api/app/main.py` | FastAPI app: `GET /health`, `POST /analyze` | `/health` works, `/analyze` returns 501 |
| `apps/api/app/config.py` | Settings from root `.env` (pydantic-settings) | Done |
| `apps/api/app/schemas.py` | Request/response models for the API contract | Done |
| `apps/api/app/limits.py` | Official environment reference values + `s_scale_level()` (shared by generator and future providers) | Done |
| `apps/api/app/synthetic/` | Deterministic generator (`synth-0.2.0`): `npm run synth` → CSVs + manifest in `app/synthetic/out/` (git-ignored) | Done, loaded with `supabase/load_synthetic.psql` |
| `apps/api/tests/` | pytest (`npm run test:api`) | Generator tests only |
| `supabase/migrations/` | Schema + RLS (5 tables), measurement types, form check-in protection | Applied to the Supabase project (migration 3: confirm) |
| `docs/` | Architecture, data model, API contract, data sources, STATUS | Current |

Proposed homes for new code (create when the task starts, then update this table):

| Path | For |
|---|---|
| `apps/api/app/ml/` | Feature prep, baselines, anomaly model, explanations |
| `apps/api/app/providers/` | NASA source adapters (PIMS, RadLab, ...), one module each |
| `apps/web/src/api/` | One function per FastAPI endpoint; components never call `fetch` directly |
| `apps/web/src/pages/` | Mission Overview, Health Trends (+ Flag Details panel) |

## Work areas

There are no fixed owners yet. Claim a task in `docs/STATUS.md` before starting, and stay inside the area that task belongs to. Ask before editing another area's files when someone else has an active claim there.

| Area | Folders | Suggested branch prefix |
|---|---|---|
| Web | `apps/web/` | `web/` |
| API | `apps/api/app/` (except `ml/`, `synthetic/`, `providers/`) | `api/` |
| ML + data | `apps/api/app/ml/`, `apps/api/app/synthetic/` | `ml/` |
| Mission context | `apps/api/app/providers/` | `context/` |
| Database | `supabase/migrations/` | `db/` |

Shared by everyone: `docs/`, root config. Branch names look like `ml/isolation-forest`. Merge to `main` through PRs.

## Architecture in one picture

```
React/Vite  --publishable key + user JWT (RLS)-->  Supabase (Postgres, Auth, RLS)
     |                                                   ^
     +--HTTPS (VITE_API_BASE_URL)--> FastAPI --secret key-+
                                       |
                                       +--> ml/ (baselines, anomaly score, explanation)
                                       +--> providers/ (future NASA adapters)
```

Planned analysis flow: web saves a check-in to Supabase, calls `POST /analyze`, FastAPI loads recent history, scores it, writes a row to `anomaly_results`, returns the result, web shows it.

- Supabase is the only database. Do not add another DB server.
- The ML model runs in the Python API, never in a Supabase Edge Function.

## Setup and commands

Run everything from the repo root (`.npmrc` puts the npm cache at `.cache/npm`, relative to the root).

```bash
cp .env.example .env        # fill in values; never commit .env
npm install                 # web deps (npm workspace)
npm run setup:api           # creates apps/api/.venv, installs requirements.txt
apps/api/.venv/bin/pip install -r apps/api/requirements-dev.txt   # ruff

npm run dev:web             # http://localhost:5173
npm run dev:api             # http://localhost:8000/health, docs at /docs
npm run build:web           # typecheck + production build
cd apps/api && .venv/bin/ruff check . && .venv/bin/ruff format .
```

Before you say a task is done, run the checks that apply to the files you touched: `npm run build:web` for web, `ruff check` (and tests, once they exist) for the API. Say in your summary which ones you ran.

## Data model cheat sheet

Authoritative source: `supabase/migrations/20261114000000_initial_schema.sql`. Read it before writing queries.

| Table | Key columns | Notes |
|---|---|---|
| `crew_profiles` | `profile_code`, `display_name`, `baseline_metadata` jsonb, `is_fictional`, `user_id` (nullable) | One row per fictional crew member |
| `health_checkins` | `profile_id`, `recorded_at`, `sleep_duration_hours` (0 to 24), `mood_rating` (1 to 5), `resting_heart_rate` (20 to 250 bpm), `source` (`self_report`/`wearable`/`synthetic`), `is_simulated`, `data_quality` jsonb | Indexed by profile + time |
| `environment_readings` | `recorded_at`, `source`, `instrument`, `measurement_type` (`acceleration`/`radiation`), `value`, `unit`, `location_context`, `is_simulated`, `is_stale`, `source_retrieved_at` | Never personal data |
| `anomaly_results` | `profile_id`, `checkin_id`, `score`, `review_label` (`within_baseline`/`worth_reviewing`/`insufficient_data`), `explanation` jsonb, `model_version` | Written only by the API |

RLS: signed-in users see only their own profile, check-ins and results; telemetry is read-only for signed-in users; `anon` has no access. If the demo runs without sign-in, add narrow `anon` SELECT policies limited to `is_fictional = true`, never anon writes. Schema changes go in a **new** migration file (`YYYYMMDDHHMMSS_description.sql`); never edit an applied migration. Update `docs/data-model.md` in the same commit.

## API contract

Types live in `apps/api/app/schemas.py`; prose in `docs/api-contract.md`. Change both together, plus the web client function, plus a test.

| Endpoint | State | Shape |
|---|---|---|
| `GET /health` | Implemented | `{status: "ok", service, demo_mode}` |
| `POST /analyze` | 501 | Request `{profile_id, checkin_id?}`. Planned response `{score, label, explanation, contributing_changes: [{feature, observed, baseline, unit}], model_version}` |

Planned auth: the browser forwards the user's Supabase JWT; the API verifies it and checks the caller owns `profile_id`.

## ML guidance (planned, not built)

1. **Synthetic data first.** Fixed random seed, several fictional profiles, each with a stable pattern and normal day-to-day noise. Include scripted scenarios: gradual sleep decline, unusual resting heart rate trend. Mark every row `source = 'synthetic'`, `is_simulated = true`.
2. **Features relative to self.** Deviation from the profile's rolling median plus a short-term trend per indicator. Keep raw values for the explanation.
3. **Model.** scikit-learn Isolation Forest is the current candidate for unusual combinations. Keep it simple and deterministic (`random_state` set).
4. **Explanation.** Build it from per-indicator comparisons to the baseline (that is what fills `contributing_changes`), not from the model internals.
5. **Minimum history.** Below the threshold, return `insufficient_data`. Pick the threshold once, document it in `docs/api-contract.md`.
6. **Version everything.** Bump `model_version` whenever features, thresholds or the model change.
7. **No claims.** Not trained or validated on astronaut medical data. Say so wherever results are shown.

## Data quirks and gotchas

- One root `.env` feeds both apps: Vite via `envDir: '../..'`, the API via pydantic-settings reading `../../.env`.
- `apps/web/src/lib/supabase.ts` exports `supabase: SupabaseClient | null`; it is `null` when the `VITE_SUPABASE_*` vars are missing, and `App.tsx` shows a configuration message instead of crashing.
- Web check-ins always send `source` and `is_simulated` explicitly. Do not rely on column defaults, and never send `synthetic` from the browser (RLS rejects it too).
- The migration has not been applied anywhere and there is no remote Supabase project yet. Code that needs the DB must degrade gracefully (or use local synthetic data) until it is.
- `POST /analyze` currently validates the body before returning 501, so a bad body gives 422, not 501.
- The local machine has a parent Git repo at `/Users/syedk`. Always run Git from `/Users/syedk/pulsar` and check `git rev-parse --show-toplevel` before committing.

## Security rules

- Never commit `.env`, keys or tokens. `.gitignore` covers `.env` and `.env.*` except `.env.example`.
- `SUPABASE_SECRET_KEY` is server-side only. Never prefix it with `VITE_`, never import it in `apps/web`.
- The browser uses the publishable key and relies on RLS. Do not loosen RLS to make a feature work; add a scoped policy in a new migration.
- Future NASA API keys are server env vars, read in `providers/` only.
- No real health records, ever.

## How to work here (agent workflow)

1. **Before starting:** read `docs/STATUS.md`. Pick a task from *Next up*, move it to *Active* with your name/agent and branch.
2. **Scope:** only do what the task says. Do not implement screens, ML or integrations that were not asked for. If you find extra work, add it to *Next up* or *Open issues* instead of doing it.
3. **Verify, don't assume:** read the current code and migration before claiming how something works. Never invent schema columns, endpoint behavior, NASA data access or validation results.
4. **When done, in the same commit:** move the task to *Done* in `docs/STATUS.md`, update any milestone checkbox, add a changelog line, and update the docs your change affects (API contract, data model, this file's repo map).
5. **When blocked:** mark the task *Blocked* in STATUS with what you need and from whom, then stop or switch tasks.
6. **Commits:** conventional style (`feat(api): ...`, `fix(web): ...`, `docs: ...`, `chore: ...`), one logical change per commit.
